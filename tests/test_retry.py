from __future__ import annotations

import json

import httpx
import pytest

from llm_toolkit.exceptions import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConfigError,
    LLMRateLimitError,
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.retry import RETRYABLE_STATUS, is_retryable_exception


def _make_status_error(status_code: int) -> httpx.HTTPStatusError:
    """构造一个指定状态码的 HTTPStatusError,用于测试。"""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)



class TestIsRetryableException:
    @pytest.mark.parametrize("status_code", [200, 201, 204, 301, 418])
    def test_non_5xx_non_retryable_status(self, status_code: int) -> None:
        """200/201/204(成功)和 301(重定向)、418(I'm a teapot)都不该重试。"""
        exc = _make_status_error(status_code)
        assert not is_retryable_exception(exc)

    def test_timeout_exception_is_retryable(self) -> None:
        """httpx.TimeoutException(读/连接超时)应该重试。"""
        exc = httpx.TimeoutException("Timeout")
        assert is_retryable_exception(exc)

    def test_connect_error_is_retryable(self) -> None:
        """httpx.ConnectError(连不上)应该重试。"""
        exc = httpx.ConnectError("ConnectError")
        assert is_retryable_exception(exc)

    # 应该重试的(HTTP 5xx 和 429)

    @pytest.mark.parametrize("status_code", RETRYABLE_STATUS)
    def test_retryable_status_codes(self, status_code: int) -> None:
        """RETRYABLE_STATUS 里的状态码都应该重试。
        
        用 parametrize 一次测完所有可重试状态码——你不必每个写一个 def。
        ⚠️ 这是 pytest 的高级特性。
        """
        exc = _make_status_error(status_code)
        assert is_retryable_exception(exc)

    # 不应该重试的(HTTP 4xx 除 429)

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
    def test_non_retryable_4xx(self, status_code: int) -> None:
        """4xx(除 429)是请求本身的错,重试无意义。"""
        exc = _make_status_error(status_code)
        assert not is_retryable_exception(exc)

    # 不应该重试的(协议层 / 未知异常)

    def test_value_error_is_not_retryable(self) -> None:
        """ValueError(参数错、解析错)不重试。"""
        exc = ValueError("参数错误")
        assert not is_retryable_exception(exc)

    def test_json_decode_error_is_not_retryable(self) -> None:
        """JSON 解析失败不重试——response 内容有问题,重试还是错。"""
        exc = json.JSONDecodeError(msg="解析错误", doc="doc", pos=2)
        assert not is_retryable_exception(exc)

    def test_random_exception_is_not_retryable(self) -> None:
        """兜底:任意 Exception 默认不重试(保守策略)。"""
        exc = Exception("其他错误")
        assert not is_retryable_exception(exc)



class TestIsRetryableExceptionCustom:

    @pytest.mark.parametrize("exc_class", [
        LLMRateLimitError,
        LLMServerError,
        LLMTimeoutError,
    ])
    def test_retryable_llm_exceptions(self, exc_class: type[Exception]) -> None:
        """LLM 体系内的临时性异常应该重试。"""
        exc = exc_class("error")
        assert is_retryable_exception(exc)

    @pytest.mark.parametrize("exc_class", [
        LLMConfigError,
        LLMBadRequestError,
        LLMAuthError,
        LLMResponseError,
    ])
    def test_non_retryable_llm_exceptions(self, exc_class: type[Exception]) -> None:
        """LLM 体系内的配置错/请求错/响应解析错都不应该重试。"""
        exc = exc_class("error")
        assert not is_retryable_exception(exc)