from __future__ import annotations

import httpx
import pytest
import respx

from llm_toolkit.client import LLM
from llm_toolkit.types import LLMUrl, Message, Role


@respx.mock
async def test_chat_fills_cost_and_updates_tracker() -> None:
    """正常 chat 一次,resp.cost 非空,tracker 累加。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        },
    ))
    
    llm = LLM("deepseek-v4-flash")
    
    # 初始 tracker 是 0
    assert llm.cost_tracker.call_count == 0
    assert llm.cost_tracker.total_usd == 0.0
    
    resp = await llm.chat([Message(role=Role.USER, content="hi")])
   
    assert resp.cost is not None
    assert resp.cost.total_usd == pytest.approx(0.15*100/1_000_000 + 0.3*50/1_000_000)
    assert llm.cost_tracker.call_count == 1
    assert llm.cost_tracker.input_tokens == 100
    assert llm.cost_tracker.total_usd == resp.cost.total_usd