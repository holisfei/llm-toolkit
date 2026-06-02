from __future__ import annotations

import httpx
import pytest
import respx

from llm_toolkit.retry import make_retrying


async def test_retries_on_500_then_succeeds() -> None:
    """500 应该重试;前两次 500、第三次 200,最终应该返回 200。
    
    这条测试如果通过:证明 1) 决策函数判 500 可重试是 work 的;
                          2) AsyncRetrying 真的会重试;
                          3) reraise=True 在成功时不影响返回。
    """
    url = "https://api.example.com/chat"
    # 用 respx 拦截这个 url 的请求, 按调用次数依次返回不同响应
    # side_effect 给一个列表,respx 依次用这些响应回应每次调用
    with respx.mock:
        route = respx.post(url).mock(
            side_effect=[
                httpx.Response(500),  # 第 1 次:服务端错
                httpx.Response(500),  # 第 2 次:还错
                httpx.Response(200, json={"ok": True}),  # 第 3 次:好了
            ]
        )
        
        async with httpx.AsyncClient() as client:
            response_status: int | None = None
            # 整个重试逻辑测试
            async for attempt in make_retrying():
                with attempt:
                    res = await client.post(url)
                    res.raise_for_status()
                    response_status = res.status_code

        assert response_status == 200         
        assert route.call_count == 3
        

async def test_does_not_retry_on_400() -> None:
    """400 不该重试;只调一次就直接抛 HTTPStatusError。"""
    url = "https://api.example.com/chat"
    with respx.mock:
        route = respx.post(url).mock(
            return_value=httpx.Response(400, json={"error": "bad"})
        )
        
        async with httpx.AsyncClient() as client:
            response_status: int | None = None
            # pytest.raises(SomeException)
                # 1. 进入 with 块,等待异常发生
                # 2. 块结束时检查:
                    # - 如果块内正好抛了指定异常 → 测试通过,异常被"捕获"住不再向外冒;
                    # - 如果没抛或抛了别的异常 → 测试失败
            # pytest.raises期望:块里的这整段重试逻辑最终抛 HTTPStatusError(因为 reraise=True)
                # - 期望：第一次就抛出400的错误，不再进行重试
            with pytest.raises(httpx.HTTPStatusError):
                async for attempt in make_retrying():
                    with attempt:
                        res = await client.post(url)
                        response_status = res.status_code
                        res.raise_for_status()

        assert response_status == 400
        assert route.call_count == 1

async def test_retries_exhausted_reraises_original_exception() -> None:
    """所有重试都失败时,应该抛出【原始 HTTPStatusError】(因为 reraise=True),
    而不是 RetryError。
    """
    url = "https://api.example.com/chat"
    with respx.mock:
        route = respx.post(url).mock(
            return_value=httpx.Response(503)
        )

        async with httpx.AsyncClient() as client:
            response_status: int | None = None
            # pytest.raises 期望整个n次重试循环都跑完之后，最终得到HTTPStatusError的错误
            with pytest.raises(httpx.HTTPStatusError):
                async for attempt in make_retrying():
                    with attempt:
                        res = await client.post(url)
                        response_status = res.status_code
                        res.raise_for_status()
                        
        assert response_status == 503
        assert route.call_count == 3