from __future__ import annotations


# 错误基类
class LLMError(Exception):
    """所有 llm-toolkit 异常的基类。"""

    def __init__(
        self,
        message: str,
        *, # keyword-only, * 之后的参数必须写明参数名
        provider: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        # Python 标准异常链机制
        # self.__cause__ = cause 是手动版本,provider 翻译时优先用 raise ... from ... 语法(更标准),
        self.__cause__ = cause

    def __str__(self) -> str: # 错误输出
        if self.provider is not None:
            return f"[{self.provider}] {self.message}"
        return f"{self.message}"

# 请求错误(带status_code) 基类
class LLMRequestError(LLMError):
    """请求本身的错——400/422/context too long 等。"""
    def __init__(
        self, 
        message: str, 
        *, 
        status_code: int | None = None, # 状态码
        provider: str | None = None, 
        cause: Exception | None = None,
    ):
        super().__init__(message, provider=provider, cause=cause)
        self.status_code = status_code


# 不需要重试的错误

class LLMConfigError(LLMError):
    """缺 key、未知 model、参数非法等。"""

class LLMAuthError(LLMRequestError):
    """401/403 — key 错、权限不够。"""

class LLMBadRequestError(LLMRequestError):
    """400/422 — 请求体本身有问题(参数错、context 超长等)。"""

class LLMResponseError(LLMError):
    """响应不符合预期 —— JSON 解析失败 / 关键字段缺失。"""
    def __init__(
        self,
        message: str, 
        *, 
        raw_body: str | None = None, # 用于debug
        provider: str | None  = None, 
        cause: Exception | None  = None
    ):
        super().__init__(message, provider=provider, cause=cause)
        self.raw_body = raw_body

# 需要重试的错误

class LLMRateLimitError(LLMRequestError):
    """429 — 调用频率超限。"""

class LLMServerError(LLMRequestError):
    """5xx/529 — 服务端临时崩溃。"""

class LLMTimeoutError(LLMError):
    """网络超时 / asyncio 墙钟超时 —— 不带 status_code,但带 provider。"""