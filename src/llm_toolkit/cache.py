"""请求级缓存 —— "完全相同的请求,只发一次"。
设计原则:
  - 进程内 dict,简单可靠;Redis / TTL / LRU 都不做(范围外)
  - cache key = (model, messages 的 JSON) 的 SHA-256
  - 命中时直接返回原 ChatResponse,但调用方应该自己处理 cost(命中不该累加)
  - 默认关闭,LLM(model, cache=True) 才启用

它不是给多轮对话用的，多轮对话的messages是累加的，所以每次key都不用，每次都不会命中缓存
满足这个前提的场景:
多个 Agent 协作
无状态批量任务
多用户共享 SDK

⚠️ 关于缓存语义的一个真实风险:
  即使 temperature=0,模型版本迭代可能改 response。所以"完全相同输入 → 缓存返回"
  在生产里其实是个【弱保证】。本 SDK 把这个权衡留给调用方:开启 cache 默认是 False,
  调用方必须显式开启才能享受缓存收益(同时承担"可能错过模型新版本"的风险)。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from llm_toolkit.types import ChatResponse, Message


class RequestCache:
    """简单进程内请求缓存。"""

    def __init__(self) -> None:
        self._store: dict[str, ChatResponse] = {}

    @staticmethod
    def make_key(model: str, messages: list[Message]) -> str:
        """生成稳定的 cache key。
        
        要求:
          - 同样的 (model, messages),无论调用多少次,生成同一个 key
          - 不同的 (model, messages),key 不同
          - 用 SHA-256 hash 序列化后的 JSON
        
        实现思路:
          1. 把 messages 转成 list[dict]:[m.model_dump(mode="json") for m in messages]
          2. 把整体 {"model": model, "messages": [...]} 序列化成 JSON(用 json.dumps,
             sort_keys=True 保证字段顺序稳定 —— 这是缓存稳定的核心)
          3. hashlib.sha256(json_bytes).hexdigest() 返回 hash 字符串
        """
        message_list: list[dict[str, Any]] = [m.model_dump(mode="json") for m in messages]
        model_msg: dict[str, Any] = {
            "model": model,
            "messages": message_list
        }
        sort_msg = json.dumps(model_msg, sort_keys=True)
        json_bytes = sort_msg.encode("utf-8")
        hash_key = hashlib.sha256(json_bytes).hexdigest()
        return hash_key

    def get(self, key: str) -> ChatResponse | None:
        """查询缓存。命中返回 ChatResponse,未命中返回 None。
        
        不抛异常,不 log warning —— 未命中是正常状况,不是错。
        """
        return self._store.get(key, None)

    def set(self, key: str, response: ChatResponse) -> None:
        """存入缓存。
        
        ⚠️ 注意 ChatResponse 是 Pydantic 模型,可变。如果调用方拿到 resp 之后修改它
           (比如 resp.cost = None),缓存里的副本会一起被改。
           
           这是个真实生产坑—— 我们【约定】调用方不修改
           ChatResponse 实例。如果将来要严格防护,可以 model_copy(deep=True)。
        """
        self._store[key] = response



