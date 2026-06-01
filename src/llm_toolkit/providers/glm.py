from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from llm_toolkit.providers.base import BaseProvider, generate_params
from llm_toolkit.streaming import parse_openai_sse
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Usage


class GlmProvider(BaseProvider): 
    async def chat(self, messages: list[Message], model: str = "glm-4.7") -> ChatResponse:
        url = f"{LLMUrl.GLM.base_url}{LLMUrl.GLM.end_point}"
        params = generate_params(messages=messages, model=model)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.post(url=url, json=params)
            response.raise_for_status()
            res_json = response.json()

            message: dict[str, Any] = res_json["choices"][0]["message"]
            usage: dict[str, Any] = res_json["usage"]
            res = ChatResponse(
                content=message["content"],
                usage=Usage(
                    input_tokens=usage["prompt_tokens"], 
                    output_tokens=usage["completion_tokens"], 
                    # get安全取值
                    cached_tokens=usage["prompt_tokens_details"].get("cached_tokens", 0)
                ),
                model=res_json["model"],
                raw=res_json
            )
            return res
    
    async def stream_chat(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        stream_options = {"stream_options": {"include_usage": True}}
        params = generate_params(messages=messages, model=model, stream=True, extra=stream_options)
        url = f"{LLMUrl.GLM.base_url}{LLMUrl.GLM.end_point}"

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            async with client.stream("POST", url=url, json=params) as response:
                response.raise_for_status()
                async for text in parse_openai_sse(response.aiter_lines()):
                    yield text