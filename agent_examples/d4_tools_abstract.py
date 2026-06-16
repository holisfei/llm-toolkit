from __future__ import annotations

import asyncio
import json

from loguru import logger

from llm_toolkit.client import LLM, Message, Role
from llm_toolkit.tool_transform import dispatch_one
from llm_toolkit.types import Tool, ToolCall, ToolResult, tool


@tool # 装饰器返回了Tool对象
def get_user_balance(username: str) -> str:
    """查询指定用户的账户余额(单位:元)。
    Args:
        username: 用户名
    """
    return f"用户 {username} 的账户余额为 -999 元"
@tool
def get_game_coins(username: str) -> str:
    """查询用户的【游戏金币】数量。
    Args:
        username: 用户名
    """
    return f"{username} 游戏金币 300 个"

tools = [get_user_balance, get_game_coins]
tool_map = {t.name: t for t in tools}


async def chat(model: str, tools: list[Tool]):
    client = LLM(model)
    messages: list[Message] = [Message(role=Role.USER, content="我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?")]

    res1 = await client.chat(messages=messages, tools=tools)
    res1_json_str: str = json.dumps(res1.raw, indent=4, ensure_ascii=False)
    print(f"{model}响应1 {res1_json_str}")

    tool_use_blocks: list[ToolCall] = res1.tool_calls
    if len(tool_use_blocks) > 0:
        tool_results: list[ToolResult] = [dispatch_one(call=block, tool_map=tool_map) for block in tool_use_blocks]
        client.append_tool_round(res=res1, messages=messages, tool_results=tool_results)

        res2 = await client.chat(messages=messages, tools=tools)
        print(f"{model}响应2 {json.dumps(res2.raw, indent=4, ensure_ascii=False)}")

async def stream_chat(model: str, tools: list[Tool]):
    client = LLM(model)
    messages: list[Message] = [Message(role=Role.USER, content="我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?")]

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
                tool_results: list[ToolResult] = [dispatch_one(call=block, tool_map=tool_map) for block in tool_use_blocks]
                client.append_tool_round_stream(messages=messages, tool_results=tool_results, content=chunk.assistant_content)

                streams2 = client.stream_chat(messages=messages, tools=tools)
                async for chunk2 in streams2:
                    if chunk2.kind == "text_delta":
                        print(chunk2.chunk, end="", flush=True)
                    if chunk2.kind == "done":
                        print(chunk2.tool_call)
        
            
            

async def main():
    # await stream_chat(model="claude-sonnet-4-6", tools=tools)
    await stream_chat(model="deepseek-v4-flash", tools=tools)


if __name__ == "__main__":
    asyncio.run(main())