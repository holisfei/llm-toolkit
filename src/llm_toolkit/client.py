from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from llm_toolkit.cache import RequestCache
from llm_toolkit.cost import CostTracker, compute_cost
from llm_toolkit.exceptions import LLMTimeoutError
from llm_toolkit.providers.anthropic import AnthropicProvider
from llm_toolkit.providers.base import BaseProvider
from llm_toolkit.providers.deepseek import DeepSeekProvider
from llm_toolkit.providers.glm import GlmProvider
from llm_toolkit.providers.litellm import LiteLLMProvider
from llm_toolkit.types import ChatResponse, Cost, EnvApiKeyName, Message, Role, StreamChunk, Tool, ToolResult, Usage

model_provider: dict[str, BaseProvider] = {
    "claude": AnthropicProvider(env_name=EnvApiKeyName.ANTHROPIC_API_KEY),
    "deepseek": DeepSeekProvider(env_name=EnvApiKeyName.DEEPSEEK_API_KEY),
    "glm": GlmProvider(env_name=EnvApiKeyName.ZAI_API_KEY),
    "litellm": LiteLLMProvider()
}

def cost_add(resp: ChatResponse) -> Cost | None:
    # 计算单次会话成本
    cost = compute_cost(usage=resp.usage, model=resp.model)
    if cost is None:
        logger.warning(f"模型 {resp.model} 不在价格表,cost 未计算")
    return cost

class LLM:
    """统一的 LLM 调用入口。"""

    def __init__(self, model: str, *, cache: bool = False) -> None:
        self.model = model
        self.cost_tracker = CostTracker()
        self._cache = RequestCache() if cache else None

        temp_provider: BaseProvider | None = None
        for model_prefix, provider in model_provider.items():
            if model.startswith(model_prefix):
                temp_provider = provider
                break
        
        if temp_provider is None:
            raise ValueError(f"当前model {model} 不支持")
        
        self.provider: BaseProvider = temp_provider
    
# ========== helper ==========

    def _post_process(self, response: ChatResponse, cache_key: str | None) -> ChatResponse:
        """请求成功后:算 cost、累加 tracker、写 cache。两条分支共用。"""
        cost = cost_add(response)
        response.cost = cost
        self.cost_tracker.add(usage=response.usage, cost=cost)
        if self._cache is not None and cache_key is not None:
            self._cache.set(cache_key, response)
        return response
    
    def _normalize(self, messages: list[Message] | str) -> list[Message]:
        msgs: list[Message] = []
        if isinstance(messages, str):
            if len(messages) == 0:
                raise ValueError("内容不能为空")
            msgs.append(Message(role=Role.USER, content=messages))
        else:
            msgs = messages
        return msgs

# ========== chat ==========

    async def chat(
        self,
        messages: list[Message] | str, 
        tools: list[Tool] | None = None,
        wait_timeout: float | None = None
    ) -> ChatResponse:
        msgs: list[Message] = self._normalize(messages)

        # cache命中 不调用 LLM api
        cache_key: str | None = None
        if self._cache is not None:
            cache_key = RequestCache.make_key(self.model, msgs)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"cache hit: {cache_key[:12]}...")
                return cached    # 命中:直接返回,不累加 tracker,不算 cost

        # 调用 LLM api
        provider_coro = self.provider.chat(messages=msgs, tools=tools, model=self.model)

        # 没有协程超时
        if wait_timeout is None:
            response = await provider_coro
            return self._post_process(response=response, cache_key=cache_key)
        
        # 有协程超时，和provider的请求超时区分开，协程超时不需要重试
        try:
            res: ChatResponse = await asyncio.wait_for(provider_coro, timeout=wait_timeout)
            return self._post_process(response=res, cache_key=cache_key)
        except TimeoutError as e:
            raise LLMTimeoutError(
                f"call exceeded wall-clock timeout of {wait_timeout}s",
                provider=self.provider.name,
            ) from e

    # TODO: 重试逻辑 
    async def stream_chat(
        self,
        messages: list[Message] | str,
        tools: list[Tool] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        msgs: list[Message] = self._normalize(messages)
        
        # usage_holder 层层透传，最终在流结束后拿结果
        usage_holder: list[Usage] = []
        
        # 请求 LLM Api
        async for chunk in self.provider.stream_chat(messages=msgs, model=self.model, tools=tools, _usage_out=usage_holder):
            yield chunk
        
        # 计算本轮对话的成本
        if usage_holder:
            usage = usage_holder[0]
            cost = compute_cost(usage, self.model)
            self.cost_tracker.add(usage=usage, cost=cost)
        if not usage_holder:
            logger.warning("结束会话 没有 usage 信息")

    def append_tool_round(
        self, 
        res: ChatResponse, 
        messages: list[Message], 
        tool_results: list[ToolResult]
    ) -> None:
        self.provider.append_tool_round(res=res, messages=messages, tool_results=tool_results)

    def append_tool_round_stream(
        self, 
        messages: list[Message], 
        tool_results: list[ToolResult],
        content: Any
    ) -> None:
        self.provider.append_tool_round_stream(messages=messages, tool_results=tool_results, content=content)

# ========== 并发 chat ==========

    async def batch_chat(
        self,
        batch_messages: list[list[Message] | str], 
        concurrency: int = 5,
        wait_timeout: float | None = None
    ) -> list[ChatResponse | BaseException]:
        semaphore = asyncio.Semaphore(concurrency)
        async def _bounded_chat(messages: list[Message] | str) -> ChatResponse:
            async with semaphore:
                return await self.chat(messages=messages, wait_timeout=wait_timeout)
            
        results: list[ChatResponse | BaseException] = await asyncio.gather(
            *[_bounded_chat(msgs) for msgs in batch_messages],
            return_exceptions=True
        )
        return results
            
            


