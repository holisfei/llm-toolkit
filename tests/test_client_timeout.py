from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import respx

from llm_toolkit.client import LLM
from llm_toolkit.exceptions import LLMTimeoutError
from llm_toolkit.models import LLMUrl, Message, Role


@pytest.fixture
def messages() -> list[Message]:
    return [Message(role=Role.USER, content="hi")]

@pytest.fixture
def url() -> str:
    return f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"

@pytest.fixture
def model() -> str:
    return "deepseek-v4-flash"

@pytest.fixture
def response() -> dict[str, Any]:
    return {
        "model": "deepseek-v4-flash",
        "choices": [{"message": {"content": "hello"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10}
    }

async def slow_response(request: httpx.Request) -> httpx.Response:
    """respx side_effect 接到的第一个参数是 Request,不是我们的 fixture。"""
    await asyncio.sleep(2.0)
    return httpx.Response(
        status_code=200, 
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "should never reach here"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    )

@respx.mock
async def test_chat_with_short_timeout_raises_llm_timeout(url: str, model: str, messages: list[Message]) -> None:
    """测试带超时参数 client层 协程超时"""
    respx.post(url).mock(
        side_effect=slow_response
    )
    with pytest.raises(LLMTimeoutError) as exc_info:
        await LLM(model).chat(messages=messages, wait_timeout=0.5)

    assert exc_info.value.provider == "deepseek"
    assert isinstance(exc_info.value.__cause__, asyncio.TimeoutError)

@respx.mock
async def test_chat_without_short_normal(
    url: str, 
    model: str, 
    messages: list[Message],
    response: dict[str, Any],
) -> None:
    """测试不带超时参数 正常返回"""
    respx.post(url).mock(
        return_value=httpx.Response(status_code=200, json=response)
    )
    resp = await LLM(model).chat(messages=messages)
    assert resp.content == "hello"

@respx.mock
async def test_wait_timeout_path_normal_completion() -> None:
    """wait_timeout 设了但请求很快完成,应该正常返回,不抛 LLMTimeoutError。
    """
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    respx.post(url).mock(return_value=httpx.Response(
        status_code=200,
        json={
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "fast response"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10},
        },
    ))
    
    llm = LLM("deepseek-v4-flash")
    # wait_timeout=30:很长,绝对来得及完成
    resp = await llm.chat([Message(role=Role.USER, content="hi")], wait_timeout=30)
    
    assert resp.content == "fast response"
    assert resp.cost is not None
    assert llm.cost_tracker.call_count == 1