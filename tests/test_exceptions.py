from __future__ import annotations

import pytest

from llm_toolkit.exceptions import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConfigError,
    LLMError,
    LLMRateLimitError,
    LLMRequestError,
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)


class TestExceptionHierarchy:
    """测试继承关系: 决定调用方的 except 子句行为。"""
    @pytest.mark.parametrize("error", [LLMAuthError,
                                       LLMBadRequestError,
                                       LLMConfigError,
                                       LLMRateLimitError,
                                       LLMRequestError,
                                       LLMResponseError,
                                       LLMServerError,
                                       LLMTimeoutError
                                       ]
    )
    def test_all_exceptions_inherit_from_llm_error(self, error: type[LLMError]) -> None:
        """每个具体异常都应该是 LLMError 的子类,这是统一 catch 的基础。"""
        assert issubclass(error, LLMError)
    
    @pytest.mark.parametrize("error", [LLMAuthError,
                                       LLMBadRequestError,
                                       LLMRateLimitError,
                                       LLMServerError,
                                       ]
    )
    def test_request_error_subclasses(self, error: type[LLMRequestError]) -> None:
        """LLMAuthError / LLMBadRequestError / LLMRateLimitError / LLMServerError
        都应该是 LLMRequestError 的子类——这样 `except LLMRequestError` 能一把抓。
        """
        assert issubclass(error, LLMRequestError)


class TestExceptionFields:
    """测试字段——调用方拿异常后能否取到诊断信息。"""
    def test_llm_error_basic_fields(self) -> None:
        """LLMError 携带 message 和可选 provider。"""
        exc = LLMError("test message", provider="deepseek")
        assert exc.message == "test message"
        assert exc.provider == "deepseek"

    def test_str_with_provider(self) -> None:
        """__str__ 应该是 '[provider] message' 格式。"""
        exc = LLMError("test message", provider="deepseek")
        assert str(exc) == "[deepseek] test message"
        
    def test_str_without_provider(self) -> None:
        """没有 provider 时,只显示 message。"""
        exc = LLMError("test message")
        assert str(exc) == "test message"
        
    def test_request_error_status_code(self) -> None:
        """LLMRequestError 及子类应该携带 status_code。"""
        exc = LLMBadRequestError("bad params", status_code=400, provider="glm")
        assert exc.status_code == 400
        assert exc.provider == "glm"
        
    def test_response_error_raw_body(self) -> None:
        """LLMResponseError 应该携带 raw_body 用于 debug。"""
        exc = LLMResponseError(
            "json decode failed",
            raw_body='{"not": "valid json',
            provider="deepseek",
        )
        assert exc.raw_body == '{"not": "valid json'

    def test_cause_chain(self) -> None:
        """如果传入 cause,__cause__ 应该被设置(异常链)。"""
        original = ValueError("original")
        exc = LLMError("wrapped", cause=original)
        assert exc.__cause__ is original