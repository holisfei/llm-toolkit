from __future__ import annotations

# import json
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx
from dotenv import load_dotenv

# from loguru import logger
from llm_toolkit.exceptions import LLMAuthError, LLMBadRequestError, LLMRateLimitError, LLMRequestError, LLMServerError
from llm_toolkit.types import ChatResponse, Message, StreamChunk, Tool, ToolResult, Usage

load_dotenv()

class BaseProvider(ABC):
    """所有 provider 适配器的统一接口。"""

    # 子类必须定义, ClassVar明确标记某个属性是“类变量”，而不是实例变量
    name: ClassVar[str]

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        self.api_key = api_key
        if self.api_key is None:
            self.api_key = os.getenv(env_name)
        if self.api_key is None:
            raise ValueError(f"请设置环境变量{env_name}或在初始化时传入 api_key")
        
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        self.timeout = httpx.Timeout(connect=30, read=60, write=60, pool=60)
        
    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[Tool] | None, model: str) -> ChatResponse:
        """非流式对话。在各个子类里实现。"""
    
    @abstractmethod
    def stream_chat(self, messages: list[Message], model: str, tools: list[Tool] | None, _usage_out: list[Usage] | None = None) -> AsyncIterator[StreamChunk]:
        """流式对话。在各个子类里实现。"""

    @abstractmethod
    def append_tool_round(self, res: ChatResponse, messages: list[Message], tool_results: list[ToolResult]) -> None:
        """输入统一的 res1 + results,内部按自己是哪家 provider 拼好 messages"""
    
    @abstractmethod
    def append_tool_round_stream(self, messages: list[Message], tool_results: list[ToolResult], content: Any) -> None:
         """输入统一的 stream + results,内部按自己是哪家 provider 拼好 messages"""

# 辅助方法

def generate_params(
     messages: list[Message], 
     model: str, 
     stream: bool = False, 
     extra: dict[str, Any] | None  = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model,
        "messages": [m.model_dump(mode="json", exclude_none=True) for m in messages],
        "stream": stream
    }
    if extra is not None:
        params.update(extra)
    # logger.debug(f"参数: {json.dumps(params, indent=4, ensure_ascii=False)}")
    return params

def translate_http_error(e: httpx.HTTPStatusError, provider: str) -> LLMRequestError:
    """根据 HTTP 状态码翻译成对应的 LLM 异常子类。"""
    status = e.response.status_code
    # raw = e.response.text
    
    if status in (401, 403):
        return LLMAuthError(
            f"auth failed: HTTP {status}",
            status_code=status, provider=provider, cause=e,
        )
    if status == 429:
        return LLMRateLimitError(
            f"rate limit exceeded: HTTP {status}",
            status_code=status, provider=provider, cause=e,
        )
    if 500 <= status < 600 or status == 529:
        return LLMServerError(
            f"server error: HTTP {status}",
            status_code=status, provider=provider, cause=e,
        )
    # 400/422 等其它 4xx
    return LLMBadRequestError(
        f"bad request: HTTP {status}",
        status_code=status, provider=provider, cause=e,
    )