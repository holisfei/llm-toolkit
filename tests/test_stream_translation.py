"""验证 stream_chat 也把 httpx 异常翻译成 LLMError。"""

from __future__ import annotations

import httpx
import pytest
import respx

from llm_toolkit.client import LLM
from llm_toolkit.exceptions import LLMAuthError, LLMServerError
from llm_toolkit.types import LLMUrl, Message, Role


@respx.mock
async def test_stream_chat_translates_401_to_auth_error() -> None:
    """stream 在建连阶段拿到 401,应该抛 LLMAuthError,不是 httpx.HTTPStatusError。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    respx.post(url).mock(return_value=httpx.Response(401, text="auth error"))
    
    llm = LLM("deepseek-v4-flash")
    
    with pytest.raises(LLMAuthError) as exc_info:
        async for _ in llm.stream_chat([Message(role=Role.USER, content="hi")]):
            pass
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.provider == "deepseek"


@respx.mock
async def test_stream_chat_translates_connect_error_to_server_error() -> None:
    """stream 连不上,应该抛 LLMServerError。"""
    url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"
    respx.post(url).mock(side_effect=httpx.ConnectError("connection refused"))
    
    llm = LLM("deepseek-v4-flash")
    
    with pytest.raises(LLMServerError):
        async for _ in llm.stream_chat([Message(role=Role.USER, content="hi")]):
            pass