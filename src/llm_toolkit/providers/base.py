from __future__ import annotations

# import json
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import httpx
from dotenv import load_dotenv

# from loguru import logger
from llm_toolkit.types import ChatResponse, Message

load_dotenv()

class BaseProvider(ABC):
    """所有 provider 适配器的统一接口。"""

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
    async def chat(self, messages: list[Message], model: str) -> ChatResponse:
        """非流式对话。在各个子类里实现。"""
    
    @abstractmethod
    def stream_chat(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        """流式对话。在各个子类里实现。"""

def generate_params(
     messages: list[Message], 
     model: str, 
     stream: bool = False, 
     extra: dict[str, Any] | None  = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model,
        "messages": [m.model_dump(mode="json") for m in messages],
        "stream": stream
    }
    if extra is not None:
        params.update(extra)
    # logger.debug(f"参数: {json.dumps(params, indent=4, ensure_ascii=False)}")
    return params