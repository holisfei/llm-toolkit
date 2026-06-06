from __future__ import annotations

from collections.abc import AsyncIterator

import litellm
from litellm import ModelResponse
from litellm import Usage as liteUsage

from llm_toolkit.providers.base import BaseProvider
from llm_toolkit.types import ChatResponse, Message, Usage


class LiteLLMProvider(BaseProvider):

    name = "litellm"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        pass

    @staticmethod
    def _strip_litellm_prefix(model: str) -> str:
        prefix = "litellm/"
        if len(model) == 0:
            raise ValueError("model 不能为空,LiteLLMProvider 需要明确的 model 字符串如 'litellm/deepseek/deepseek-chat'")
        if model.startswith(prefix):
            return model.removeprefix(prefix)
        return model

    async def chat(self, messages: list[Message], model: str) -> ChatResponse:
        message_list = [m.model_dump(mode="json") for m in messages]
        model_name = LiteLLMProvider._strip_litellm_prefix(model)
        response: ModelResponse = await litellm.acompletion(model=model_name, messages=message_list)
        return ChatResponse(
            content=response.choices[0].message.content,
            usage=Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                cached_tokens=0
            ),
            model=model_name,
            raw=response.model_dump()
        )

    async def stream_chat(self, messages: list[Message], model: str, _usage_out: list[Usage] | None = None) -> AsyncIterator[str]:
        message_list = [m.model_dump(mode="json") for m in messages]
        model_name = LiteLLMProvider._strip_litellm_prefix(model)
        response: ModelResponse = await litellm.acompletion(
            model=model_name,
            messages=message_list,
            stream=True,
            stream_options={"include_usage": True}
        )
        
        async for chunk in response:
            content: str | None = chunk.choices[0].delta.content
            
            usage: liteUsage | None = getattr(chunk, "usage", None)
            if usage is not None and usage.prompt_tokens and _usage_out is not None:
                _usage_out.append(Usage(input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens))
                continue

            if content is None:
                continue

            yield content
