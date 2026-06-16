from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger

from llm_toolkit.models import Tool, ToolCall, ToolResult
from llm_toolkit.stream_toolcall import StreamAccumulator

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

def parse_anthropic_tool_calls(raw: dict[str, Any]) -> list[ToolCall]:
    """从 Anthropic 响应的 content 数组里, 提取所有 tool_use block, 转成 ToolCall.
    """
    contents: list[dict[str, Any]] = raw["content"]
    tool_uses = [c for c in contents if c.get("type") == "tool_use"]
    return [ToolCall(name=t["name"], id=t["id"], arguments=t["input"]) 
            for t in tool_uses]

def parse_openai_tool_calls(raw: dict[str, Any]) -> list[ToolCall]:
    """从 OpenAI/DeepSeek 响应的 message.tool_calls 里提取, 转成 ToolCall.
    """
    tool_calls: list[dict[str, Any]] = raw["choices"][0]["message"].get("tool_calls", [])
    return [ToolCall(name=t["function"]["name"], id=t["id"], arguments=json.loads(t["function"]["arguments"])) 
            for t in tool_calls]

# ============ 方向③ 回传: ToolResult -> 两家消息格式 ============

# 3.1 stream 拼接 tools 到 message 中 

def tool_generate_message_to_anthropic(stream_accumulator: StreamAccumulator) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
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

def tool_generate_message_to_openai(stream_accumulator: StreamAccumulator) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    for i, t in stream_accumulator._tool_accs.items():    
        tool_calls.append(
            {
                "index": i,
                "id": t.id,
                "type": "function",
                "function": {
                    "name": t.name,
                    "arguments": t.full_arguments
                }
            }
        )
    return tool_calls

# 3.2 模型返回 ToolCall 后 - 并发执行返回 ToolResult

async def dispatch_one(call: ToolCall, tool_map: dict[str, Any]) -> ToolResult:
    """执行单个tool"""
    if call.is_error:
        return ToolResult(
            id=call.id,
            content="工具执行错误",
            is_error=True
        )
    
    tool: Tool | None = tool_map.get(call.name)
    if tool is None: # 模型调了一个不存在的工具
        logger.warning(f"模型调用了未知工具: {call.name}")
        return ToolResult(
            id=call.id, 
            content=f"未知工具 {call.name}", 
            is_error=True
        )
    
    try:
        # await 结果
        result = await tool.run(call.arguments)
        logger.debug(f"工具执行后 {tool.name} id:{call.id} 参数:{call.arguments} 执行结果:{result}")
        return ToolResult(id=call.id, content=result)
    except Exception as e:
        # 不猜原因, 如实把异常告诉模型, 让模型/日志自己判断
        logger.exception(f"工具 {tool.name} 执行失败")
        return ToolResult(
            id=call.id,
            content=f"工具执行失败: {type(e).__name__}: {e}",
            is_error=True,
        )

async def dispatch_all(calls: list[ToolCall],tool_map: dict[str, Tool]) -> list[ToolResult]:
    """并发执行多个工具调用, 返回结果列表"""
    if not calls:
        return []
    
    # 并发执行
    results: list[ToolResult | BaseException] = await asyncio.gather(
        *[dispatch_one(call=c, tool_map=tool_map) for c in calls],
        return_exceptions=True
    )

    # 防御性
    final_results:list[ToolResult]  = []
    for i, res in enumerate(results):
        if isinstance(res, BaseException):
            final_results.append(ToolResult(
                id=calls[i].id, 
                content=f"调度器发生严重异常: {res}", 
                is_error=True
            ))
        else:
            final_results.append(res)

    return final_results

# 3.3 将 ToolResult 结构化为 模型要求的格式

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