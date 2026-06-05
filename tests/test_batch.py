from __future__ import annotations

import asyncio
import time

import httpx
import pytest
import respx

from llm_toolkit.client import LLM
from llm_toolkit.exceptions import LLMBadRequestError
from llm_toolkit.types import ChatResponse, LLMUrl, Message, Role


@respx.mock
async def test_batch_chat_all_succeed() -> None:
    """5 条成功请求,batch 返回 5 个 ChatResponse,顺序对应。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        },
    ))
    
    llm = LLM("deepseek-v4-flash")
    batches_msg: list[list[Message] | str] = [[Message(role=Role.USER, content=f"q{i}")] for i in range(5)]
    results = await llm.batch_chat(batch_messages=batches_msg, concurrency=3)

    assert len(results) == 5
    for r in results:
        assert isinstance(r, ChatResponse)

@respx.mock
async def test_batch_chat_partial_failure() -> None:
    """5 条里第 3 条返回 400,batch 返回 5 项,其中第 3 项是 Exception,其余正常。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    
    # 用 side_effect 让第 3 次调用返回 400
    success_response = httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        },
    )
    fail_response = httpx.Response(status_code=400, text="bad request")
    
    respx.post(url).mock(side_effect=[
        success_response, 
        success_response, 
        fail_response,
        success_response,
        success_response,
    ])

    llm = LLM("deepseek-v4-flash")
    batches_msg: list[list[Message] | str] = [[Message(role=Role.USER, content=f"q{i}")] for i in range(5)]
    results: list[ChatResponse | BaseException] = await llm.batch_chat(batch_messages=batches_msg, concurrency=3)

    assert len(results) == 5
    assert llm.cost_tracker.call_count == 4
    for i, r in enumerate(results):
        if i == 2:
            assert isinstance(r, LLMBadRequestError)
        else:
            assert isinstance(r, ChatResponse)

@respx.mock
async def test_batch_chat_respects_max_concurrent() -> None:
    """并发上限真的生效——同时 in-flight 不超过 max_concurrent。
    
    ⚠️ 要在 mock 里加 sleep, 然后通过观察"同时有多少并发任务数量"来验证。
    最简单方式: 用 asyncio.sleep + counter 计数,
    在 mock 方法里 开始任务 +1, sleep 后-1, 
    断言 counter 最大值 == max_concurrent 
    """
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    current_concurrency = 0
    max_concurrency = 0

    success_response = httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        },
    )
    async def delayed_response(request: httpx.Request) -> httpx.Response:
        nonlocal current_concurrency, max_concurrency
        current_concurrency += 1
        max_concurrency = max(max_concurrency, current_concurrency)

        await asyncio.sleep(2.0)

        current_concurrency -= 1
        return success_response
    
    respx.post(url).mock(side_effect=delayed_response)
    
    start = time.perf_counter()
    llm = LLM("deepseek-v4-flash")
    batches_msg: list[list[Message] | str] = [[Message(role=Role.USER, content=f"q{i}")] for i in range(5)]
    results: list[ChatResponse | BaseException] = await llm.batch_chat(batch_messages=batches_msg, concurrency=3)

    duration = time.perf_counter() - start
    assert len(results) == 5
    assert llm.cost_tracker.call_count == 5
    assert duration == pytest.approx(4, abs=0.5)
    assert max_concurrency == 3
    
