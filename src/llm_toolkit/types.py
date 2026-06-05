from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class EnvApiKeyName(StrEnum):
    TRANSIT_API_KEY = "TRANSIT_API_KEY"
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
    ZAI_API_KEY = "ZAI_API_KEY"
    DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"

@dataclass
class ApiUrl:
    base_url: str
    end_point: str

class LLMUrl(str, ApiUrl):
    TRANSIT = ApiUrl(base_url="https://api.highwayapi.ai/openai", end_point="/chat/completions")
    ANTHROPIC = ApiUrl(base_url="https://api.anthropic.com", end_point="/v1/messages")
    DEEPSEEK = ApiUrl(base_url="https://api.deepseek.com", end_point="/chat/completions")
    GLM = ApiUrl(base_url="https://open.bigmodel.cn", end_point="/api/paas/v4/chat/completions")
    QWEN = ApiUrl(base_url="https://ws-ly70qjwnoyegh3bs.ap-southeast-1.maas.aliyuncs.com", end_point="/compatible-mode/v1/chat/completions")

class Message(BaseModel):
    role: Role
    content: str
    
class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    def __str__(self) -> str:
        return f"提示词:{self.input_tokens} 回复内容:{self.output_tokens} 缓存:{self.cached_tokens}"

class Cost(BaseModel):
    """单次调用的成本细分。所有金额单位:美元。"""
    input_usd: float
    output_usd: float
    cached_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd + self.cached_usd

    def __str__(self) -> str:
        return f"${self.total_usd:.4f}"

class ChatResponse(BaseModel):
    content: str        # 模型回复的文本
    usage: Usage        # token用量 Usage 模型
    cost: Cost | None = None        # 转化为成本
    model: str          # 实际使用的模型名（便于 debug 和成本归因）
    raw: dict[str, Any] # 原始响应（保底：万一统一字段没覆盖到，还能从这里捞）

