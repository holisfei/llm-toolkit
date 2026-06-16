from __future__ import annotations

import pytest

from llm_toolkit.cache import RequestCache
from llm_toolkit.types import ChatResponse, Cost, Message, Role, Usage


@pytest.fixture
def messages() -> list[Message]:
    return [Message(role=Role.USER, content="hello")]

@pytest.fixture
def model() -> str:
    return "deepseek-v4-flash"

@pytest.fixture
def chat_response() -> ChatResponse:
    return ChatResponse(
        content="hi there",
        usage=Usage(input_tokens=10, output_tokens=20, cached_tokens=0),
        cost=Cost(input_usd=0.001, output_usd=0.002, cached_usd=0.0),
        model="deepseek-v4-flash",
        content_tools=None,
        raw={},
    )

class TestMakeKey:
    """key 生成的稳定性"""

    def test_same_input_same_key(self, model: str, messages: list[Message]) -> None:
        """完全相同的 (model, messages),两次生成同一个 key。"""
        key1: str = RequestCache.make_key(model=model, messages=messages)
        key2: str = RequestCache.make_key(model=model, messages=messages)
        print(key1)
        assert key1 == key2

    def test_different_model_different_key(self, model: str, messages: list[Message]) -> None:
        """不同 model, key 不同。"""
        key1: str = RequestCache.make_key(model=model, messages=messages)
        key2: str = RequestCache.make_key(model="deepseek-v4-pro", messages=messages)
        assert key1 != key2

    def test_different_messages_different_key(self, model: str, messages: list[Message]) -> None:
        """不同 messages 内容, key 必须不同。"""
        msg = [Message(role=Role.USER, content="hi")]
        key1: str = RequestCache.make_key(model=model, messages=msg)
        key2: str = RequestCache.make_key(model=model, messages=messages)
        assert key1 != key2

    def test_key_is_hex_string(self, model: str, messages: list[Message]) -> None:
        """key 应该是合法的十六进制字符串(SHA-256 输出 64 字符)。"""
        key: str = RequestCache.make_key(model=model, messages=messages)
        hex_chars = set("0123456789abcdef")           # ← 真实的 hex 字符集
        assert set(key).issubset(hex_chars)


class TestCacheGetSet:
    """get/set 的基本行为。"""

    def test_get_miss_returns_none(self) -> None:
        """未存的 key,get 返回 None,不抛异常。"""
        cache = RequestCache()
        assert cache.get(key="a34739478hhdf") is None

    def test_set_then_get_returns_response(
        self, 
        model: str,
        messages: list[Message], 
        chat_response: ChatResponse,
    ) -> None:
        """set 后立即 get,应该拿到原 response。"""
        key: str = RequestCache.make_key(model=model, messages=messages)
        cache = RequestCache()
        cache.set(key=key, response=chat_response)
        cache_resp: ChatResponse | None = cache.get(key=key)

        assert cache_resp == chat_response   # Pydantic 模型 __eq__ 默认按字段全等

    def test_set_overwrites_existing(
        self, 
        model: str,
        messages: list[Message], 
        chat_response: ChatResponse,
    ) -> None:
        """对同一 key set 两次,第二次覆盖第一次。
        
        这是个 dict 默认行为。
        """
        key: str = RequestCache.make_key(model=model, messages=messages)
        cache = RequestCache()
        cache.set(key=key, response=chat_response)
        #
        temp_res = ChatResponse(
            content="hi here",
            usage=Usage(input_tokens=20, output_tokens=20, cached_tokens=0),
            cost=Cost(input_usd=0.002, output_usd=0.002, cached_usd=0.0),
            model="deepseek-v4-flash",
            content_tools=None,
            raw={},
        )

        cache.set(key=key, response=temp_res)
        cache_resp: ChatResponse | None = cache.get(key=key)

        assert cache_resp is not None
        assert cache_resp.content == "hi here"
        assert cache_resp.model == "deepseek-v4-flash"
        assert cache_resp.usage.input_tokens == 20
        assert cache_resp.cost is not None
        assert cache_resp.cost.input_usd == 0.002