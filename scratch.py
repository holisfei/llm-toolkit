import asyncio

from llm_toolkit.client import LLM
from llm_toolkit.cost import compute_cost
from llm_toolkit.models import Message, Role, Usage


async def main() -> None:

    model_deepseek = "deepseek-v4-flash"
    model_claude = "claude-sonnet-4-6"
    model_glm = "glm-4.7"
    model_qwen = "qwen3.5-plus-2026-02-15"
    model_litellm = "litellm/deepseek/deepseek-chat"

    question = "简述LLM原理"
    msgs: list[Message] = [Message(role=Role.USER, content=question)]

    llm = LLM(model_litellm)

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

    # print(f"\n{'='*50}\n 并发 chat 输出:\n{'='*50}")
    # batch = [
    #     [Message(role=Role.USER, content=f"用一句话讲讲数字 {i}")] for i in range(1, 6)
    # ]
    # results = await llm.batch_chat(batch, concurrency=3)
    # for i, r in enumerate(results):
    #     if isinstance(r, Exception):
    #         print(f"{i+1}: ERROR {r}")
    #     else:
    #         print(f"{i+1}: {r.content[:50]}")
    # print()
    # print(llm.cost_tracker.summary())

    print(f"\n{'='*50}\n llmlite chat 输出:\n{'='*50}")
    resp = await llm.chat("用一句话讲讲什么是单元测试")
    print(resp.content)
    print(f"input={resp.usage.input_tokens}, output={resp.usage.output_tokens}")

    llm2 = LLM("litellm/anthropic/claude-haiku-4-5")
    print(f"\n{'='*50}\n llmlite stream 输出:\n{'='*50}")
    async for chunk in llm.stream_chat("用三句话讲讲 Python 的 GIL"):
        print(chunk, end="", flush=True)
    print()
    print(f"tracker: {llm.cost_tracker.summary()}")

if __name__ == "__main__":
    asyncio.run(main())
