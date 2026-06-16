from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import litellm
from litellm import ModelResponse
from litellm import Usage as liteUsage

from llm_toolkit.models import ChatResponse, Message, StreamChunk, Tool, ToolResult, Usage
from llm_toolkit.providers.base import BaseProvider
from llm_toolkit.stream_toolcall import StreamAccumulator


class LiteLLMProvider(BaseProvider):

    name = "litellm"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        self._stream_accumulator = StreamAccumulator()

    @staticmethod
    def _strip_litellm_prefix(model: str) -> str:
        prefix = "litellm/"
        if len(model) == 0:
            raise ValueError("model 不能为空,LiteLLMProvider 需要明确的 model 字符串如 'litellm/deepseek/deepseek-chat'")
        if model.startswith(prefix):
            return model.removeprefix(prefix)
        return model

    async def chat(
        self, 
        messages: list[Message], 
        tools: list[Tool] | None = None, 
        model: str = ""
    ) -> ChatResponse:
        message_list = [m.model_dump(mode="json") for m in messages]
        model_name = LiteLLMProvider._strip_litellm_prefix(model)
        response: ModelResponse = await litellm.acompletion(
            model=model_name, 
            messages=message_list,
        )

        return ChatResponse(
            content=response.choices[0].message.content,
            tool_calls=[],
            usage=Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                cached_tokens=0
            ),
            model=model_name,
            content_tools="",
            raw=response.model_dump()
        )

    async def stream_chat(
        self,
        messages: list[Message], 
        model: str, 
        tools: list[Tool] | None,
        _usage_out: list[Usage] | None = None
    ) -> AsyncIterator[StreamChunk]:
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

            yield StreamChunk(
                kind="text_delta",
                chunk=content,
            )

    def append_tool_round(
        self, 
        res: ChatResponse, 
        messages: list[Message], 
        tool_results: list[ToolResult],
    ) -> None:
        pass

    def append_tool_round_stream(
        self,
        messages: list[Message], 
        tool_results: list[ToolResult],
        content: Any,
    ) -> None:
        pass