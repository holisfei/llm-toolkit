from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from loguru import logger

from llm_toolkit.cost import CostTracker, compute_cost
from llm_toolkit.exceptions import LLMTimeoutError
from llm_toolkit.providers.anthropic import AnthropicProvider
from llm_toolkit.providers.base import BaseProvider
from llm_toolkit.providers.deepseek import DeepSeekProvider
from llm_toolkit.providers.glm import GlmProvider
from llm_toolkit.providers.qwen import QwenProvider
from llm_toolkit.types import ChatResponse, Cost, EnvApiKeyName, Message, Role

model_provider: dict[str, BaseProvider] = {
    "claude": AnthropicProvider(env_name=EnvApiKeyName.ANTHROPIC_API_KEY),
    "deepseek": DeepSeekProvider(env_name=EnvApiKeyName.DEEPSEEK_API_KEY),
    "glm": GlmProvider(env_name=EnvApiKeyName.ZAI_API_KEY),
    "qwen": QwenProvider(env_name=EnvApiKeyName.DASHSCOPE_API_KEY)
}

def cost_add(resp: ChatResponse) -> Cost | None:
    # 计算单词会话成本
    cost = compute_cost(usage=resp.usage, model=resp.model)
    if cost is None:
        logger.warning(f"模型 {resp.model} 不在价格表,cost 未计算")
    return cost

class LLM:
    """统一的 LLM 调用入口。"""

    def __init__(self, model: str) -> None:
        self.model = model
        self.cost_tracker = CostTracker()
        temp_provider: BaseProvider | None = None
        for model_prefix, provider in model_provider.items():
            if model.startswith(model_prefix):
                temp_provider = provider
                break
        
        if temp_provider is None:
            raise ValueError(f"当前model {model} 不支持")
        
        self.provider: BaseProvider = temp_provider
    
    async def chat(
        self,
        messages: list[Message] | str, 
        wait_timeout: float | None = None
    ) -> ChatResponse:
        msgs: list[Message] = []
        if isinstance(messages, str):
            if len(messages) == 0:
                raise ValueError("内容不能为空")
            msgs.append(Message(role=Role.USER, content=messages))
        else:
            msgs = messages

        provider_coro = self.provider.chat(messages=msgs, model=self.model)

        if wait_timeout is None:
            response = await provider_coro
            cost = cost_add(response)
            response.cost = cost
            # 会话成本累加
            self.cost_tracker.add(usage=response.usage, cost=cost)
            return response
        
        # 协程超时，和provider的请求超时区分开
        # 此处协程超时不重试
        try:
            res: ChatResponse = await asyncio.wait_for(provider_coro, timeout=wait_timeout)
            cost = cost_add(res)
            res.cost = cost
            # 会话成本累加
            self.cost_tracker.add(usage=res.usage, cost=cost)
            return response
        except TimeoutError as e:
            raise LLMTimeoutError(
                f"call exceeded wall-clock timeout of {wait_timeout}s",
                provider=self.provider.name,
            ) from e
    
    async def stream_chat(self, messages: list[Message] | str) -> AsyncIterator[str]:
        msgs: list[Message] = []
        if isinstance(messages, str):
            if len(messages) == 0:
                raise ValueError("内容不能为空")
            msgs.append(Message(role=Role.USER, content=messages))
        else:
            msgs = messages
        async for chunk in self.provider.stream_chat(messages=msgs, model=self.model):
            yield chunk