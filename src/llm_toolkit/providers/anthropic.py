from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
from dotenv import load_dotenv

from llm_toolkit.exceptions import (
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.providers.base import BaseProvider, generate_params, translate_http_error
from llm_toolkit.retry import make_retrying
from llm_toolkit.streaming import parse_anthropic_sse
from llm_toolkit.types import ChatResponse, EnvApiKeyName, LLMUrl, Message, Usage

load_dotenv()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        
        self.url = f"{LLMUrl.ANTHROPIC.base_url}{LLMUrl.ANTHROPIC.end_point}"

        if "Authorization" in self.headers:
            self.headers.pop("Authorization")
        self.headers["anthropic-version"] = "2023-06-01"
        key: str | None = os.getenv(EnvApiKeyName.ANTHROPIC_API_KEY)
        if key:
            self.headers["x-api-key"] = key

    async def chat(self, messages: list[Message], model: str ="claude-sonnet-4-6") -> ChatResponse:
        params = generate_params(messages=messages, model=model, stream=False)
        params["max_tokens"] = 2048

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            # 重试逻辑
            async for attempt in make_retrying():
                with attempt:
                    try:
                        response = await client.post(url=self.url, json=params)
                        response.raise_for_status()
                        res_json = response.json()
                        # print(f"Anthropic响应：{res_json}")
                        content: dict[str, Any] = res_json["content"][0]
                        usage: dict[str, Any] = res_json["usage"]
                        res = ChatResponse(
                            content=content["text"],
                            usage=Usage(
                                input_tokens=usage["input_tokens"], 
                                output_tokens=usage["output_tokens"], 
                                # 通过 dict.get(key, 默认值) 安全取值
                                cached_tokens=usage.get("cache_read_input_tokens", 0)
                            ),
                            model=res_json["model"],
                            raw=res_json
                        )
                        return res
                    except httpx.HTTPStatusError as e:
                        raise translate_http_error(e=e, provider=self.name) from e
                    except httpx.TimeoutException as e:
                        raise LLMTimeoutError(
                             f"request timeout: {e}",
                            provider=self.name,
                        ) from e
                    except httpx.TransportError as e:
                        raise LLMServerError(
                            f"transport error: {e}",
                            provider=self.name,
                        ) from e
                    except (KeyError, ValueError) as e:
                        raise LLMResponseError(
                            f"failed to parse response: {type(e).__name__}: {e}",
                            raw_body=response.text if 'response' in locals() else None,
                            provider=self.name,
                        ) from e
                    # from e 的作用，自动设置 __cause__
        raise RuntimeError("重试循环已用尽且无返回结果——无法访问。")
    
    async def stream_chat(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        params = generate_params(messages=messages, model=model, stream=True)
        params["max_tokens"] = 2048

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            async with client.stream("POST", url=self.url, json=params) as response:
                response.raise_for_status()
                async for text in parse_anthropic_sse(response.aiter_lines()):
                    yield text