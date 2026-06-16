from __future__ import annotations

import asyncio
import json
from typing import Any

from llm_toolkit.client import LLM, Message, Role

tools_claude = [
      {
        "name": "get_user_balance",
        "description": "查询指定用户的账户余额(单位:元)",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "用户名"}
            },
            "required": ["username"]
        }
      }
    ]
tools_openai = [
    {
        "type": "function",
        "function": {
            "name": "get_user_balance",
            "description": "查询指定用户的账户余额(单位:元)",
            "parameters": {
                "type": "object",
                "properties":{
                    "username": {"type": "string", "description": "用户名"}
                },
                "required": ["username"]
            },
        }
    },
]

def tool_calculator(use: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": use["id"],
        "content": "账户余额为 -999999 元" # 错误的tool结果
    }

async def main():
    # client = LLM("claude-sonnet-4-6")
    # messages: list[Message] = [Message(role=Role.USER, content="我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?")]

    # res1 = await client.chat(messages=messages, tools=tools_claude)
    # res1_json_str: str = json.dumps(res1.raw, indent=4, ensure_ascii=False)
    # print(f"claude 响应1 {res1_json_str}")

    # messages.append(Message(role=Role.ASSISTANT, content=res1.raw["content"]))
    # tool_use_blocks = [block for block in res1.raw["content"] if block.get("type") == "tool_use"]
    # if tool_use_blocks:
    #     tool_results: list[dict[str, Any]] = [tool_calculator(block) for block in tool_use_blocks]
    #     messages.append(Message(role=Role.USER, content=tool_results))
    #     res2 = await client.chat(messages=messages, tools=tools)
    #     print(f"claude 响应2 {json.dumps(res2.raw, indent=4, ensure_ascii=False)}")
    
    client = LLM("deepseek-v4-flash")
    messages: list[Message] = [Message(role=Role.USER, content="我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?")]

    res1 = await client.chat(messages=messages, tools=tools_openai)
    res1_json_str: str = json.dumps(res1.raw, indent=4, ensure_ascii=False)
    print(f"deepseek 响应1 {res1_json_str}")

    tool_use_blocks = [block for block in res1.raw["choices"][0]["message"] if block.get("tool_calls") is not None]
    if tool_use_blocks:
        messages.append(Message(role=Role.ASSISTANT, content=res1.raw["choices"][0]["message"]["tool_calls"][0]))
        tool_results: list[dict[str, Any]] = [tool_calculator(block) for block in tool_use_blocks]
        messages.append(Message(role=Role.USER, content=tool_results))
        res2 = await client.chat(messages=messages, tools=tools_openai)
        print(f"claude 响应2 {json.dumps(res2.raw, indent=4, ensure_ascii=False)}")



if __name__ == "__main__":
    asyncio.run(main())