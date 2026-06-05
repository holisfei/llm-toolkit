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

@respx.mock
async def test_stream_chat_openai_accumulates_cost() -> None:
    """流式调用应该跟非流式一样累加 cost_tracker。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    # mock 一个 SSE 响应,以及末尾的 usage chunk
    sse_body = (
        'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}\n\n'
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
        '"usage":{"prompt_tokens":10,"completion_tokens":20}}\n\n'
        'data: [DONE]\n\n'
    )
    respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        text=sse_body,
        headers={"content-type": "text/event-stream"},
    ))
    
    llm = LLM("deepseek-v4-flash")
    chunks = []
    async for chunk in llm.stream_chat([Message(role=Role.USER, content="hello")]):
        chunks.append(chunk)
    
    assert "".join(chunks) == "hi"
    # 1. 断言 llm.cost_tracker.call_count == 1
    assert llm.cost_tracker.call_count == 1
    # 2. 断言 llm.cost_tracker.input_tokens == 10
    assert llm.cost_tracker.input_tokens == 10
    # 3. 断言 llm.cost_tracker.output_tokens == 20
    assert llm.cost_tracker.output_tokens == 20
    # 4. 断言 llm.cost_tracker.total_usd > 0
    assert llm.cost_tracker.total_usd > 0
    ...

@respx.mock
async def test_stream_chat_anthropic_accumulates_cost() -> None:
    """流式调用应该跟非流式一样累加 cost_tracker。"""
    url = f"{LLMUrl.ANTHROPIC.base_url}{LLMUrl.ANTHROPIC.end_point}"
    
    # mock 一个 SSE 响应,以及末尾的 usage chunk
    sse_body = (
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hi"}}\n\n'
        'data: {"type":"message_stop","usage":{"input_tokens":10,"output_tokens":12,"cache_read_input_tokens":18}}\n\n'
    )
    respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        text=sse_body,
        headers={"content-type": "text/event-stream"},
    ))
    
    llm = LLM("claude-sonnet-4-6")
    chunks = []
    async for chunk in llm.stream_chat([Message(role=Role.USER, content="hello")]):
        chunks.append(chunk)
    
    assert "".join(chunks) == "hi"
    # 1. 断言 llm.cost_tracker.call_count == 1
    assert llm.cost_tracker.call_count == 1
    # 2. 断言 llm.cost_tracker.input_tokens == 10
    assert llm.cost_tracker.input_tokens == 10
    # 3. 断言 llm.cost_tracker.output_tokens == 12
    assert llm.cost_tracker.output_tokens == 12
    # 4. 断言 llm.cost_tracker.total_usd > 0
    assert llm.cost_tracker.total_usd > 0
    ...