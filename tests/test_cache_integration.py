from __future__ import annotations

import httpx
import respx

from llm_toolkit.client import LLM
from llm_toolkit.models import LLMUrl, Message, Role


@respx.mock
async def test_cache_hit_skips_http_and_tracker() -> None:
    """第二次相同请求应该命中 cache:不发 HTTP,tracker 不变。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    route = respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "first response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
    ))
    
    llm = LLM("deepseek-v4-flash", cache=True)
    messages = [Message(role=Role.USER, content="hello")]
    
    # 第一次:发请求,累加 tracker
    resp1 = await llm.chat(messages)
    assert route.call_count == 1
    assert llm.cost_tracker.call_count == 1
    first_total = llm.cost_tracker.total_usd
    
    # 第二次:相同请求,应该命中 cache
    resp2 = await llm.chat(messages)
    
    # 1. 断言 route.call_count 仍然是 1(没发第二次 HTTP)
    assert route.call_count == 1
    # 2. 断言 llm.cost_tracker.call_count 仍然是 1(没累加)
    assert llm.cost_tracker.call_count == 1
    # 3. 断言 llm.cost_tracker.total_usd == first_total(成本不变)
    assert llm.cost_tracker.total_usd == first_total
    # 4. 断言 resp2.content == resp1.content(内容一致)
    assert resp2.content == resp1.content
    # 5. 断言 resp2 == resp1(Pydantic 整对象相等)
    assert resp2 == resp1


@respx.mock
async def test_cache_disabled_by_default() -> None:
    """默认 cache=False,两次相同请求都会发 HTTP。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    route = respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "r"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
    ))
    
    llm = LLM("deepseek-v4-flash")    # ← 不传 cache,默认 False
    messages = [Message(role=Role.USER, content="hello")]
    
    await llm.chat(messages)
    await llm.chat(messages)
    
    # 断言 route.call_count == 2(两次都发了 HTTP,因为默认不缓存)
    assert route.call_count == 2
    # 断言 llm.cost_tracker.call_count == 2
    assert llm.cost_tracker.call_count == 2

@respx.mock
async def test_different_messages_dont_share_cache() -> None:
    """不同 messages 不应该错误地共享缓存(防 cache key 冲突)。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    # 两次不同的请求,分别返回不同内容
    route = respx.post(url).mock(side_effect=[
        httpx.Response(200, json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "answer_A"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }),
        httpx.Response(200, json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "answer_B"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }),
    ])
    
    llm = LLM("deepseek-v4-flash", cache=True)
    
    resp_a = await llm.chat([Message(role=Role.USER, content="question A")])
    resp_b = await llm.chat([Message(role=Role.USER, content="question B")])
    
    # 1. route.call_count == 2(两次都发了,因为不同 query 不同 key)
    assert route.call_count == 2
    # 2. resp_a.content == "answer_A"
    assert resp_a.content == "answer_A"
    # 3. resp_b.content == "answer_B"
    assert resp_b.content == "answer_B"