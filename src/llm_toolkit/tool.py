from __future__ import annotations

import json
from typing import Any

from llm_toolkit.stream_toolcall import StreamAccumulator
from llm_toolkit.types import Tool, ToolCall, ToolResult

# ============ 方向① 发出去: Tool -> 两家请求格式 ============

def tool_to_anthropic(tool: Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }

def tool_to_openai(tool: Tool) -> dict[str, Any]:
   return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema
        }
    }

# ============ 方向② 收回来: 两家响应 -> 统一 ToolCall ============

def parse_anthropic_tool_calls(raw: dict) -> list[ToolCall]:
    """从 Anthropic 响应的 content 数组里, 提取所有 tool_use block, 转成 ToolCall.
    """
    contents: list[dict[str, Any]] = raw["content"]
    tool_uses = [c for c in contents if c.get("type") == "tool_use"]
    return [ToolCall(name=t["name"], id=t["id"], arguments=t["input"]) 
            for t in tool_uses]

def parse_openai_tool_calls(raw: dict) -> list[ToolCall]:
    """从 OpenAI/DeepSeek 响应的 message.tool_calls 里提取, 转成 ToolCall.
    """
    tool_calls: list[dict[str, Any]] = raw["choices"][0]["message"].get("tool_calls", [])
    return [ToolCall(name=t["function"]["name"], id=t["id"], arguments=json.loads(t["function"]["arguments"])) 
            for t in tool_calls]

# ============ 方向③ 回传: ToolResult -> 两家消息格式 ============

def tool_result_to_anthropic(result: ToolResult) -> dict[str, Any]:
    block = {
        "type": "tool_result",
        "tool_use_id": result.id,
        "content": result.content,
    }
    if result.is_error:
        block["is_error"] = True      # Anthropic 原生支持
    return block


def tool_result_to_openai(result: ToolResult) -> dict[str, Any]:
    content = result.content
    if result.is_error:
        content = f"[ERROR] {content}"   # OpenAI 没这字段, 写进 content
    return {
        "role": "tool",
        "tool_call_id": result.id,
        "content": content,
    }

# stream 拼接tools到message中 

def tool_generate_message_to_anthropic(stream_accumulator: StreamAccumulator) -> list[dict]:
    content = [
        {
            "type": "text",
            "text": stream_accumulator._text_buffer
        }
    ]
    for t in stream_accumulator._tool_accs.values():
        tool: ToolCall = t.finalize()
        content.append(
            {
                "type": "tool_use",
                "id": tool.id,
                "name": tool.name,
                "input": tool.arguments
            }
        )
    return content

def tool_generate_message_to_openai(stream_accumulator: StreamAccumulator) -> list[dict]:
    tool_calls: list[dict] = []
    for i, t in stream_accumulator._tool_accs.items():    
        tool_calls.append(
            {
                "index": i,
                "id": t.id,
                "type": "function",
                "function": {
                    "name": t.name,
                    "arguments": t._arguments_buffer
                }
            }
        )
    return tool_calls