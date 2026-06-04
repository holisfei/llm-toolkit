from __future__ import annotations

import httpx
import pytest
import respx

from llm_toolkit.client import LLM
from llm_toolkit.exceptions import (
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMRequestError,
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.types import LLMUrl, Message, Role


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
def url_glm() -> str:
    return f"{LLMUrl.GLM.base_url}{LLMUrl.GLM.end_point}"

@pytest.fixture
def model_glm() -> str:
    return "glm-4.7"

@pytest.fixture
def url_anthropic() -> str:
    return f"{LLMUrl.ANTHROPIC.base_url}{LLMUrl.ANTHROPIC.end_point}"

@pytest.fixture
def model_anthropic() -> str:
    return "claude-sonnet-4-6"

# test case

@pytest.mark.parametrize("statu_code, expect_err", [
    pytest.param(400, LLMBadRequestError),
    pytest.param(401, LLMAuthError),
    pytest.param(403, LLMAuthError),
    pytest.param(422, LLMBadRequestError),
])
@respx.mock
async def test_translates_4xx_no_retry_error(
    messages: list[Message],
    url: str, 
    model: str,
    statu_code: int,
    expect_err: type[LLMRequestError]
) -> None:
    """400 401 403 422 应该翻译成对应的err 且不重试"""
    route = respx.post(url).mock(
        return_value=httpx.Response(statu_code)
    )
    with pytest.raises(expect_err) as exc_info:
        await LLM(model).chat(messages=messages)
    
    assert exc_info.value.status_code == statu_code
    assert exc_info.value.provider == "deepseek"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
    assert route.call_count == 1


@pytest.mark.parametrize("status_code, expect_err",[
    pytest.param(429, LLMRateLimitError),
    pytest.param(500, LLMServerError),
])
@respx.mock
async def test_translates_retry_to_error(
    messages: list[Message],
    url: str, 
    model: str,
    status_code: int,
    expect_err: type[LLMRequestError]
) -> None:
    """429 应该翻译成 LLMRateLimitError。"""
    route = respx.post(url).mock(
        return_value=httpx.Response(status_code)
    )
    with pytest.raises(expect_err) as exc_info:
        await LLM(model).chat(messages=messages)

    assert exc_info.value.status_code == status_code
    assert exc_info.value.provider == "deepseek"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
    assert route.call_count == 3


@respx.mock
async def test_translates_json_decode_failure_to_response_error(
    messages: list[Message],
    url: str, 
    model: str,
) -> None:
    """API 返回非法 JSON 应该翻译成 LLMResponseError。"""
    route = respx.post(url).mock(
        return_value=httpx.Response(status_code=200, text="not a json")
    )
    with pytest.raises(LLMResponseError) as exc_info:
        await LLM(model).chat(messages=messages)
    
    assert exc_info.value.raw_body is not None, "raw_body 不应为 None"
    assert exc_info.value.raw_body == "not a json"   # 注意是 ==,不是 in
    assert exc_info.value.provider == "deepseek"
    assert isinstance(exc_info.value.__cause__, (KeyError, ValueError))
    assert route.call_count == 1

@respx.mock
async def test_translates_timeout_to_timeout_error(
    messages: list[Message],
    url: str, 
    model: str,
) -> None:
    """httpx 超时应该翻译成 LLMTimeoutError。"""
    route = respx.post(url).mock(
        side_effect=httpx.ConnectTimeout("Connect Timeout")
    )
    with pytest.raises(LLMTimeoutError) as exc_info:
        await LLM(model).chat(messages=messages)
    
    assert exc_info.value.provider == "deepseek"
    assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)
    assert route.call_count == 3

# glm

@pytest.mark.parametrize("statu_code, expect_err", [
    pytest.param(400, LLMBadRequestError),
    pytest.param(401, LLMAuthError),
    pytest.param(403, LLMAuthError),
    pytest.param(422, LLMBadRequestError),
])
@respx.mock
async def test_translates_4xx_no_retry_error_glm(
    messages: list[Message],
    url_glm: str, 
    model_glm: str,
    statu_code: int,
    expect_err: type[LLMRequestError]
) -> None:
    """400 401 403 422 应该翻译成对应的err 且不重试"""
    route = respx.post(url_glm).mock(
        return_value=httpx.Response(statu_code)
    )
    with pytest.raises(expect_err) as exc_info:
        await LLM(model_glm).chat(messages=messages)
    
    assert exc_info.value.status_code == statu_code
    assert exc_info.value.provider == "glm"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
    assert route.call_count == 1

# anthropic

@pytest.mark.parametrize("statu_code, expect_err", [
    pytest.param(400, LLMBadRequestError),
    pytest.param(401, LLMAuthError),
    pytest.param(403, LLMAuthError),
    pytest.param(422, LLMBadRequestError),
])
@respx.mock
async def test_translates_4xx_no_retry_error_anthropic(
    messages: list[Message],
    url_anthropic: str, 
    model_anthropic: str,
    statu_code: int,
    expect_err: type[LLMRequestError]
) -> None:
    """400 401 403 422 应该翻译成对应的err 且不重试"""
    route = respx.post(url_anthropic).mock(
        return_value=httpx.Response(statu_code)
    )
    with pytest.raises(expect_err) as exc_info:
        await LLM(model_anthropic).chat(messages=messages)
    
    assert exc_info.value.status_code == statu_code
    assert exc_info.value.provider == "anthropic"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
    assert route.call_count == 1