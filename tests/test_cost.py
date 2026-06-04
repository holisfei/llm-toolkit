from __future__ import annotations

import pytest

from llm_toolkit.cost import (
    MODEL_PRICING_MAP,
    Cost,
    CostTracker,
    ModelPrice,
    compute_cost,
    get_pricing,
)
from llm_toolkit.types import Usage


@pytest.fixture
def model_name_deepseek() -> str:
    return "deepseek-v4-flash"

class TestPricingLookup:
    """get_pricing —— 价格表查询。"""

    @pytest.mark.parametrize("model", list(MODEL_PRICING_MAP.keys()))
    def test_known_models_return_pricing(self, model: str) -> None:
        """收录的模型必须返回 ModelPrice 实例。"""
        assert isinstance(get_pricing(model), ModelPrice)

    def test_unknown_model_returns_none(self) -> None:
        """未收录的模型返回 None,不抛异常(SDK 不该因为没收录就崩)。"""
        assert get_pricing("gpt-9-fake-nonexistent") is None

class TestComputeCost:
    """compute_cost —— 核心计费函数。"""

    def test_basic_cost_calculation(self, model_name_deepseek: str) -> None:
        """1M input + 1M output @ DeepSeek V4 Flash = $0.15 + $0.3 = $0.45。"""
        usage: Usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cached_tokens=0)
        cost: Cost | None = compute_cost(usage, model_name_deepseek)
        assert cost is not None
        assert cost.input_usd == pytest.approx(0.15)
        assert cost.output_usd == pytest.approx(0.3)
        assert cost.total_usd == pytest.approx(0.45)

    def test_cost_with_cached_tokens_uses_cached_price(self, model_name_deepseek: str) -> None:
        """cached_tokens 部分用 cached 价计算,不应该按 input 价。
        
        例:DeepSeek V4 Flash,input=1000, cached=800
            按普通 input 计费的部分 = 1000 - 800 = 200 tokens
            input_usd  = 200 * 0.15 / 1M = 0.00003
            cached_usd = 800 * 0.003 / 1M = 0.0000024
        """
        usage: Usage = Usage(input_tokens=1000, output_tokens=2000, cached_tokens=800)
        cost: Cost | None = compute_cost(usage, model_name_deepseek)
        assert cost is not None
        assert cost.input_usd == pytest.approx(0.00003)
        assert cost.cached_usd == pytest.approx(0.0000024)

    def test_unknown_model_returns_none(self) -> None:
        """compute_cost 对未知模型返回 None,不崩。"""
        usage: Usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cached_tokens=0)
        cost: Cost | None = compute_cost(usage=usage, model="deeseek-un-pro")
        assert cost is None

class TestCostTracker:
    """CostTracker —— session 累计。"""

    def test_add_accumulates_tokens_and_cost(self, model_name_deepseek: str) -> None:
        """add 多次后,tokens 和 cost 都按预期累加。"""
        usage = Usage(input_tokens=1000, output_tokens=2000, cached_tokens=0)
        cost = Cost(input_usd=0.1, output_usd=0.2, cached_usd=0.0)
        
        tracker = CostTracker()
        tracker.add(usage=usage, cost=cost)
        assert tracker.total_usd == pytest.approx(0.3)
        
        tracker.add(usage=usage, cost=cost)
        assert tracker.total_usd == pytest.approx(0.6)
        assert tracker.call_count == 2 

    def test_add_with_none_cost_still_counts_tokens(self) -> None:
        """如果模型不在价格表,cost 是 None,但 token 数还是要累加。
        这条钉死"未知模型不崩"的兜底语义。
        """

        usage: Usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, cached_tokens=0)
        cost: Cost | None = compute_cost(usage=usage, model="deepseek-in-pro")
        
        tracker = CostTracker()
        tracker.add(usage=usage, cost=cost)
        assert tracker.total_usd == 0
        assert tracker.input_tokens == 1_000_000
        assert tracker.output_tokens == 1_000_000

        tracker.add(usage=usage, cost=cost)
        assert tracker.total_usd == 0
        assert tracker.input_tokens == 2_000_000
        assert tracker.output_tokens == 2_000_000
        assert tracker.call_count == 2