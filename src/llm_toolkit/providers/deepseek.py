from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from llm_toolkit.providers.base import BaseProvider, generate_params
from llm_toolkit.streaming import parse_openai_sse
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Usage


class DeepSeekProvider(BaseProvider):

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        self.url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"

    async def chat(self, messages: list[Message], model: str = "deepseek-v4-flash") -> ChatResponse:
        params = generate_params(messages=messages, model=model)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.post(url=self.url, json=params)
            response.raise_for_status()
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
            return res
    

    async def stream_chat(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        stream_options = {"stream_options": {"include_usage": True}}
        params = generate_params(messages=messages, model=model, stream=True, extra=stream_options)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            async with client.stream("POST", url=self.url, json=params) as response:
                response.raise_for_status()
                async for text in parse_openai_sse(response.aiter_lines()):
                    yield text




        
            