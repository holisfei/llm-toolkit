from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from llm_toolkit.providers.base import BaseProvider, generate_params
from llm_toolkit.retry import make_retrying
from llm_toolkit.streaming import parse_openai_sse
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Usage


class DeepSeekProvider(BaseProvider):

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        self.url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"

    async def chat(self, messages: list[Message], model: str = "deepseek-v4-flash") -> ChatResponse:
        params = generate_params(messages=messages, model=model)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            # ┌────────── 关键决策 1:client 在 retry 外 ──────────
            # │ 这样 3 次尝试复用同一个 client(同一个连接池)
            # │ 如果把 AsyncClient(...) 放 retry 里,每次重试都新建连接,白白丢性能
            # └─────────────────────────────────────────────────
            async for attempt in make_retrying():
                with attempt:
                    response = await client.post(url=self.url, json=params)
                    response.raise_for_status()
                    # ┌──── 关键决策 2:JSON 解析 + 翻译 也放 with attempt 里 ────
                    # │ JSON 解析失败(JSONDecodeError)不重试(你决策表里 False)
                    # │ 但它仍然要从 with 块向外冒出去——所以放在 with 里
                    # │ tenacity 看到这个异常,is_retryable→False,reraise 出来
                    # │ 调用方拿到一个清晰的 JSONDecodeError,而不是莫名其妙的"重试 3 次"
                    # └────────────────────────────────────────────────────
                    res_json = response.json()

                    message: dict[str, Any] = res_json["choices"][0]["message"]
                    usage: dict[str, Any] = res_json["usage"]
                    res = ChatResponse(
                        content=message["content"],
                        usage=Usage(
                            input_tokens=usage["prompt_tokens"], 
                            output_tokens=usage["completion_tokens"], 
                            cached_tokens=usage.get("prompt_cache_hit_tokens", 0) # get安全取值
                        ),
                        model=res_json["model"],
                        raw=res_json
                    )
                    return res # 返回的时候会退出重试
            
        # ┌────────── 关键决策 3:这行 raise unreachable ──────────
        # │ 因为 reraise=True,上面循环要么 return 要么向外抛异常
        # │ 物理上走不到这一行。但 mypy strict 要求所有路径有返回值
        # │ 写一个明确的 raise 表达"此处不可达",比 # type: ignore 优雅
        # └──────────────────────────────────────────────────────
        raise RuntimeError("重试循环已用尽且无返回结果——无法访问。")
    

    async def stream_chat(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        stream_options = {"stream_options": {"include_usage": True}}
        params = generate_params(messages=messages, model=model, stream=True, extra=stream_options)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            async with client.stream("POST", url=self.url, json=params) as response:
                response.raise_for_status()
                async for text in parse_openai_sse(response.aiter_lines()):
                    yield text




        
            