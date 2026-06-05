from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from llm_toolkit.exceptions import (
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.providers.base import BaseProvider, generate_params, translate_http_error
from llm_toolkit.retry import make_retrying
from llm_toolkit.streaming import parse_openai_sse
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Usage


class GlmProvider(BaseProvider): 
    name = "glm"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        self.url = f"{LLMUrl.GLM.base_url}{LLMUrl.GLM.end_point}"

    async def chat(self, messages: list[Message], model: str = "glm-4.7") -> ChatResponse:
        params = generate_params(messages=messages, model=model)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            # 重试函数
            async for attempt in make_retrying():
                with attempt:
                    try:
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
                                # get安全取值
                                cached_tokens=usage.get("prompt_tokens_details",{}).get("cached_tokens", 0)
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

        raise RuntimeError("重试循环已用尽且无返回结果——无法访问。")
    
    async def stream_chat(
        self, 
        messages: list[Message], 
        model: str,
        _usage_out: list[Usage] | None = None
    ) -> AsyncIterator[str]:
        stream_options = {"stream_options": {"include_usage": True}}
        params = generate_params(messages=messages, model=model, stream=True, extra=stream_options)

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            async with client.stream("POST", url=self.url, json=params) as response:
                response.raise_for_status()
                async for text in parse_openai_sse(response.aiter_lines(), usage_out=_usage_out):
                    yield text