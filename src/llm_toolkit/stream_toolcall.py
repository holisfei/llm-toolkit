from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from loguru import logger

from llm_toolkit.models import StreamChunk, ToolCall


@dataclass
class _ToolCallAccumulator:
    """按 index 分桶, 累积一个流式 tool call 的碎片, 直到它结束."""
    id: str = ""
    name: str = ""
    _arguments_buffer: str = "" # tool参数 partial_json / arguments 碎片在这里攒

    def add_json_fragment(self, fragment: str) -> None:
        self._arguments_buffer += fragment

    @property
    def full_arguments(self) -> str:
        return self._arguments_buffer

    def finalize(self) -> ToolCall:
        """碎片攒完(收到结束信号)后, 一次性 parse 成完整 ToolCall.
        """
        try:
            json_buffer: dict[str, Any] = json.loads(self._arguments_buffer)
            return ToolCall(name=self.name, id=self.id, arguments=json_buffer)
        except Exception as e:
            logger.debug(f"ToolCall生成失败 {e}")
            return ToolCall(name=self.name, id=self.id, arguments={}, is_error=True)
        

@dataclass
class StreamAccumulator:
    """吃整个流式响应的所有事件, 吐最终的 (text, list[ToolCall]).
    """
    _current_kind: Literal["text_delta", "tool_call", "done", "start"] = "start" # 状态机，累加器正在执行的类型
    _text_chunk: str = "" # 文字流快
    _text_buffer: str = "" # 文字流累加
    _tool_accs: dict[int, _ToolCallAccumulator] = field(default_factory=dict) # 工具列表
    _stop_reason: str | None = None # 流是否结束

    def feed_anthropic_event(self, event: dict[str, Any]) -> None:
        """喂一个 Anthropic SSE 事件, 更新内部状态.

        按 event["type"] 分发:
        - "content_block_start": 若 content_block.type=="tool_use",
          按 event["index"] 建一个 _ToolCallAccumulator, 填 id/name
        - "content_block_delta":
          - delta.type=="text_delta": text_buffer += delta.text
          - delta.type=="input_json_delta": 对应 index 的 acc.add_json_fragment(delta.partial_json)
        - "content_block_stop": 这个 index 的 block 结束(可以但不必立刻 finalize)
        - "message_delta": 记 stop_reason
        - "message_stop" / "ping" / "error": 处理或忽略
        """
        data_type: str = event["type"]
        
        # print(event)

        self._current_kind = "start"
        if data_type == "content_block_start": # 开始 tool
            content_block: dict[str, Any] = event["content_block"]
            if content_block["type"] == "tool_use":
                index_tool_use: int = event["index"]
                self._tool_accs[index_tool_use] = _ToolCallAccumulator(
                    id=content_block["id"],
                    name=content_block["name"]
                )
        elif data_type == "content_block_delta": # 收集 text 和 tool
            delta_block: dict[str, Any] = event["delta"]
            if delta_block["type"] == "text_delta": # text 块
                self._current_kind = "text_delta"
                self._text_buffer += delta_block["text"]
                self._text_chunk = delta_block["text"]
            elif delta_block["type"] == "input_json_delta": # tool 块
                self._current_kind = "tool_call"
                index_tool: int = event["index"]
                partial_json: str = delta_block["partial_json"]
                self._tool_accs[index_tool].add_json_fragment(partial_json)
        elif data_type == "content_block_stop": # 本次会话 单个tool流结束
            pass
        elif data_type == "message_delta": # 本次会话 所有tools流结束
            self._current_kind = "done"
            delta_message: dict[str, Any] = event["delta"]
            stop_reason: str = delta_message.get("stop_reason", "")
            if stop_reason == "tool_use":
                self._stop_reason = stop_reason

    def feed_openai_event(self, event: dict[str, Any]) -> None:
        """喂一个 OpenAI/DeepSeek 流式 chunk.
        
        - choices[0].delta.content -> text_buffer
        - choices[0].delta.tool_calls -> 每个有 index, 按 index 分桶
          - 第一个碎片带 id 和 function.name
          - 后续碎片只有 function.arguments 片段, 往对应桶的 buffer 攒
        - choices[0].finish_reason 记 stop_reason
        """
        choice: dict[str, Any] = event["choices"][0]
        delta: dict[str, Any] | None = choice.get("delta", None)
        finish_reason: str | None = choice.get("finish_reason", None)
        
        self._current_kind = "start"
        if delta is not None:
            content: str | None = delta.get("content", None)
            tool_calls: list[dict[str, Any]] | None = delta.get("tool_calls", None)
            if content is not None: # text 块
                self._current_kind = "text_delta"
                self._text_buffer += content
                self._text_chunk = content
            elif tool_calls is not None: # tools 块
                self._current_kind = "tool_call"
                for tc in tool_calls:
                    index: int = tc["index"]
                    tool_id: str | None = tc.get("id", None)

                    function: dict[str, Any] = tc["function"]
                    tool_name: str | None = function.get("name", None)
                    tool_arguments: str = function.get("arguments", "")
                    
                    if tool_id is not None and tool_name is not None:
                        self._tool_accs[index] = _ToolCallAccumulator(
                            id=tool_id,
                            name=tool_name
                        )
                    elif len(tool_arguments) > 0 and index in self._tool_accs:
                        self._tool_accs[index].add_json_fragment(tool_arguments)
                        
        if finish_reason == "tool_calls": # 本次所有 tools 收集完成
            self._current_kind = "done"
            self._stop_reason = "stop_reason"

    def result_toll_call(self) -> list[ToolCall]:
        """流结束后, 吐完整结果.
        - tool_calls = [acc.finalize() for acc in 按 index 排序的 _tool_accs]
          (排序很重要 -- dict 顺序不保证, tool_use_id 配对靠的不是顺序但执行顺序你可能在意)
        """
        sorted_tool_accs: dict[int, _ToolCallAccumulator] = dict(sorted(self._tool_accs.items()))
        return [acc.finalize() for acc in sorted_tool_accs.values()]
    
    def chunk(self) -> StreamChunk:
        """tool流没结束的时候，正常展示流text，tool流结束后，进行工具调用"""
        if self._current_kind == "text_delta": # text 流
            return StreamChunk(
                kind=self._current_kind, 
                chunk=self._text_chunk, 
                text=self._text_buffer
            )
        elif self._current_kind == "done": # tool call
            return StreamChunk(
                kind=self._current_kind, 
                text=self._text_buffer, 
                tool_call=self.result_toll_call(),
            )
        return StreamChunk(kind=self._current_kind) # tool 执行

