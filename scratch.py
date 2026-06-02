import asyncio

from llm_toolkit.client import LLM
from llm_toolkit.types import Message, Role


async def main() -> None:

    model_deepseek = "deepseek-v4-flash"
    model_claude = "claude-sonnet-4-6"
    model_glm = "glm-4.7"
    model_qwen = "qwen3.5-plus-2026-02-15"

    question = "一句话说明你是谁"
    msgs: list[Message] = [Message(role=Role.USER, content=question)]

    print(f"\n{'='*50}\n输出:\n{'='*50}")

    llm = LLM(model_claude)

    # res = await llm.chat(messages=msgs)
    # print(res.content)
    
    full = ""
    async for chunk in llm.stream_chat(messages=msgs):
        print(chunk, end="", flush=True)
        full += chunk
    print(f"\n\n[累计收到 {len(full)} 字]")

if __name__ == "__main__":
    asyncio.run(main())
