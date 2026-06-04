"""token成本计算"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from llm_toolkit.types import Usage


class ModelPrice(BaseModel):
    """单个模型的价格规则。所有价格单位:美元 / 百万 token。"""
    provider: str
    input_per_mtok: float                       # 普通输入
    output_per_mtok: float                      # 输出
    cached_input_per_mtok: float = 0.0          # 命中缓存的输入(默认 0 表示不收录或不区分)
    last_verified: date                         # 价格核实日期,警示提醒

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

# ─── 具体的model对应的单价

MODEL_PRICING_MAP: dict[str, ModelPrice] = {
    "claude-sonnet-4-6": ModelPrice(
        provider="anthropic",
        input_per_mtok=3,
        output_per_mtok=15,
        cached_input_per_mtok=0.3,
        last_verified=date(2026,5,27)
    ),
    "claude-haiku-4-5": ModelPrice(
        provider="anthropic",
        input_per_mtok=1,
        output_per_mtok=5,
        cached_input_per_mtok=0.1,
        last_verified=date(2026,5,27)
    ),
    "claude-opus-4-7": ModelPrice(
        provider="anthropic",
        input_per_mtok=5,
        output_per_mtok=25,
        cached_input_per_mtok=0.5,
        last_verified=date(2026,5,27)
    ),
    "deepseek-v4-flash": ModelPrice(
        provider="deepseek",
        input_per_mtok=0.15,
        output_per_mtok=0.3,
        cached_input_per_mtok=0.003,
        last_verified=date(2026,5,27)
    ),
    "deepseek-v4-pro": ModelPrice(
        provider="deepseek",
        input_per_mtok=0.44,
        output_per_mtok=0.89,
        cached_input_per_mtok=0.0037,
        last_verified=date(2026,5,27)
    ),
    "glm-4.7": ModelPrice(
        provider="glm",
        input_per_mtok=0.3,
        output_per_mtok=1.18,
        cached_input_per_mtok=0.059,
        last_verified=date(2026,5,27)
    ),
}

# ─── 核心函数

def get_pricing(model: str) -> ModelPrice | None:
    """查询模型价格。找不到返回 None(调用方做兜底)。"""
    price: ModelPrice | None = MODEL_PRICING_MAP.get(model, None)
    return price

def compute_cost(usage: Usage, model: str) -> Cost | None:
    """根据 Usage 用量和模型单价,计算成本 Cost。
    
    返回 None 当且仅当模型不在价格表里——调用方应该 log warning。
    
    计算规则:
      input_usd  = (input_tokens - cached_tokens) * input_per_mtok / 1_000_000
      output_usd = output_tokens * output_per_mtok / 1_000_000
      cached_usd = cached_tokens * cached_input_per_mtok / 1_000_000
    """
    pricing: ModelPrice | None = get_pricing(model)
    if pricing is None:
        return None
    
    input_usd = (usage.input_tokens - usage.cached_tokens) * pricing.input_per_mtok / 1_000_000
    output_usd = usage.output_tokens * pricing.output_per_mtok / 1_000_000
    cached_usd = usage.cached_tokens * pricing.cached_input_per_mtok / 1_000_000
    return Cost(input_usd=input_usd, output_usd=output_usd, cached_usd=cached_usd)


# ─── Session 累计 

class CostTracker(BaseModel):
    """累计 session 内的所有 cost。
    
    用法:每次 chat 后调 add(cost),最后看 total_usd / call_count。
    """
    total_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    call_count: int = 0

    def add(self, usage: Usage, cost: Cost | None) -> None:
        """累加一次调用的 usage + cost。
        
        cost 为 None 时(模型不在价格表),只累加 token 数,不增加 total_usd。
        """
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cached_tokens += usage.cached_tokens
        
        if cost is not None:
            self.total_usd += cost.total_usd
        
        self.call_count += 1
    
    def summary(self) -> str:
        """友好字符串:供 CLI 退出时打印。"""
        return (
            f"本次会话累计: {self.call_count} 次调用,"
            f"输入 {self.input_tokens} tokens,输出 {self.output_tokens} tokens,"
            f"成本 ${self.total_usd:.4f}"
        )


