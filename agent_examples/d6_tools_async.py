from __future__ import annotations

import asyncio

from loguru import logger

from llm_toolkit.client import LLM, Message, Role
from llm_toolkit.tool_transform import dispatch_all
from llm_toolkit.types import Tool, ToolCall, ToolResult, tool


@tool # 装饰器返回了Tool对象
def get_user_balance(username: str) -> str:
    """查询指定用户的账户余额(单位:元)。
    Args:
        username: 用户名
    """
    return f"用户 {username} 的账户余额为 {100 if username == "holis" else 1000} 元"

@tool
async def slow_tool(x: str) -> str:
    """一个慢工具。
    Args:
        x: 参数x
    """
    await asyncio.sleep(2)        # 慢
    return f"slow result for {x}"

@tool
async def fast_tool(x: str) -> str:
    """一个快工具。
    Args:
        x: 参数x
    """
    await asyncio.sleep(0.1)      # 快
    return f"fast result for {x}"

tools = [slow_tool, fast_tool, get_user_balance]
tool_map = {t.name: t for t in tools}

async def stream_chat(model: str, tools: list[Tool], prompt: str):
    client = LLM(model)
    messages: list[Message] = [Message(role=Role.USER, content=prompt)]

    streams = client.stream_chat(messages=messages, tools=tools)
    async for chunk in streams:
        if chunk.kind == "text_delta":
            print(chunk.chunk, end="", flush=True)
        if chunk.kind == "tool_call":
            logger.debug("tools 收集中...")
            pass
        if chunk.kind == "done":
            print("tools 执行中...")
            tool_use_blocks: list[ToolCall] = chunk.tool_call
            if len(tool_use_blocks) > 0:
                tool_results: list[ToolResult] = await dispatch_all(calls=tool_use_blocks, tool_map=tool_map)
                client.append_tool_round_stream(messages=messages, tool_results=tool_results, content=chunk.assistant_content)
                logger.debug([str(t) for t in tool_results])
                streams2 = client.stream_chat(messages=messages, tools=tools)
                async for chunk2 in streams2:
                    if chunk2.kind == "text_delta":
                        print(chunk2.chunk, end="", flush=True)
                    if chunk2.kind == "done":
                        print(chunk2.tool_call)

async def main():
    # await stream_chat(model="deepseek-v4-flash", tools=tools, prompt="验证异步tools调用，同时执行slow_tool和fast_tool")
    # await stream_chat(model="claude-sonnet-4-6", tools=tools, prompt="帮我查一下 holis 和 mike 两个人的账户余额。")
    await stream_chat(model="deepseek-v4-flash", tools=[], prompt="你是谁？")



if __name__ == "__main__":
    asyncio.run(main())
