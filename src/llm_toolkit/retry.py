from __future__ import annotations

import httpx
from loguru import logger
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt, wait_exponential

# 需要重试的错误码
RETRYABLE_STATUS: list[int] = [
    429,        # rate limit
    500,        # internal server error
    502,        # bad gateway
    503,        # service unavailable
    504,        # gateway timeout
    529,        # anthropic overloaded(非标准,但 Anthropic 在用)
]

def is_retryable_exception(exc: BaseException) -> bool:
    """判断错误是否需要重试"""
    if isinstance(exc, httpx.TransportError): 
        # httpx.TimeoutException
        # httpx.ConnectError
        # httpx.RemoteProtocolError
        return True
    elif isinstance(exc, httpx.HTTPStatusError):
        # status_code error
        return exc.response.status_code in RETRYABLE_STATUS
    else:
        return False
    
def _log_before_sleep(retry_state: RetryCallState) -> None:
    "重试日志"
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    next_wait = retry_state.next_action.sleep if retry_state.next_action else 0
    logger.warning(
        f"第 {attempt} 次尝试失败: {type(exc).__name__}: {exc} ;"
        f"{next_wait:.1f}s 后重试"
    )

def make_retrying(max_attempts: int = 3) -> AsyncRetrying:
    """构造重试AsyncRetrying"""
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts), # 最大重试次数，包含起始
        wait=wait_exponential(multiplier=1, min=1, max=30), #延迟重试 min(multiplier * 2^(n-1), max)
        retry=retry_if_exception(is_retryable_exception), # 函数判断是否需要重试
        before_sleep=_log_before_sleep, # 重试之前的函数逻辑
        reraise=True # 重试耗尽后不抛RetryError，抛出原始异常
    )