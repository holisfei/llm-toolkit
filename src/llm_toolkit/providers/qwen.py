from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from llm_toolkit.providers.base import BaseProvider, generate_params
from llm_toolkit.streaming import parse_openai_sse
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Usage


class QwenProvider(BaseProvider):

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        self.url = f"{LLMUrl.QWEN.base_url}{LLMUrl.QWEN.end_point}"
        

    async def chat(self, messages: list[Message], model: str = "qwen3.5-plus-2026-02-15") -> ChatResponse:
        params = generate_params(messages=messages, model=model)
        print(self.headers)
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.post(url=self.url, json=params)
            response.raise_for_status()
            res_json = response.json()
            print(res_json)
            message: dict[str, Any] = res_json["choices"][0]["content"]
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
    def stream_chat(self, messages: list[Message], model: str = "qwen3.5-plus-2026-02-15") -> AsyncIterator[str]:
        pass