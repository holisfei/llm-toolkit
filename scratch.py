import asyncio

from llm_toolkit.client import LLM
from llm_toolkit.cost import compute_cost
from llm_toolkit.types import Message, Role, Usage


async def main() -> None:

    model_deepseek = "deepseek-v4-flash"
    model_claude = "claude-sonnet-4-6"
    model_glm = "glm-4.7"
    model_qwen = "qwen3.5-plus-2026-02-15"

    question = "电影 孤独的生还者"
    msgs: list[Message] = [Message(role=Role.USER, content=question)]

    llm = LLM(model_deepseek)

    # print(f"\n{'='*50}\n chat 输出:\n{'='*50}")
    # res = await llm.chat(messages=msgs)
    # print(res.content)
    # print(llm.cost_tracker.summary())
    
    # print(f"\n{'='*50}\n stream 输出:\n{'='*50}")
    # full = ""
    # async for chunk in llm.stream_chat(messages=msgs):
    #     print(chunk, end="", flush=True)
    #     full += chunk
    # print(f"\n\n[累计收到 {len(full)} 字]")

    print(f"\n{'='*50}\n 并发 chat 输出:\n{'='*50}")
    batch = [
        [Message(role=Role.USER, content=f"用一句话讲讲数字 {i}")] for i in range(1, 6)
    ]
    results = await llm.batch_chat(batch, concurrency=3)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"{i+1}: ERROR {r}")
        else:
            print(f"{i+1}: {r.content[:50]}")
    print()
    print(llm.cost_tracker.summary())

if __name__ == "__main__":
    asyncio.run(main())
