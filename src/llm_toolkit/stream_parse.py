from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

from llm_toolkit.models import Usage


async def parse_anthropic_sse(
     lines: AsyncIterator[str],
     usage_out: list[Usage] | None = None
) -> AsyncIterator[dict[str, Any]]:
     async for line in lines:
          if not line or not line.strip():
               continue
          if not line.startswith("data: "):
               continue
          res = line.replace("data: ", "", 1).strip()
          data: dict[str, Any] = json.loads(res)

          event_type: str = data.get("type", "")
          if event_type == "ping":
               continue
          if event_type == "message_start":
               continue
          # print(line)

          delta: dict[str, Any] = data.get("delta", {})
          delta_type: str = delta.get("type", "")
          text: str = delta.get("text", "")
          if delta_type == "text_delta" and len(text) == 0:
               continue

          if len(data) == 0:
               continue

          usage: dict[str, Any] | None = data.get("usage", None)
          if usage is not None and len(usage) > 0:
               input_tokens: int = usage.get("input_tokens", 0)
               output_tokens: int = usage.get("output_tokens", 0)
               cache_tokens: int = usage.get("cache_read_input_tokens", 0)
               cost = Usage(
                    input_tokens=input_tokens, 
                    output_tokens=output_tokens, 
                    cached_tokens=cache_tokens,
               )
               print()
               logger.debug(f"本次 stream 消耗token {str(cost)}")
               # out 参数，交给上层
               if usage_out is not None:
                    usage_out.append(cost)
          
          yield data

async def parse_openai_sse(
     lines: AsyncIterator[str], 
     usage_out: list[Usage] | None = None
) -> AsyncIterator[dict[str, Any]]:
     async for line in lines:
          if not line or not line.strip():
               continue
          if not line.startswith("data: "):
               continue
          if line.startswith("data: [DONE]"):
               return

          # print(line)

          res = line.replace("data: ", "", 1).strip()
          data: dict[str, Any] = json.loads(res)

          usage: dict[str, Any] = data.get("usage", {})
          choices_list: list[dict[str, Any]] = data.get("choices", [])

          if len(choices_list) == 0:
               continue

          choices: dict[str, Any] = choices_list[0]
          delta: dict[str, Any] = choices.get("delta", {})
          reasoning_content: str | None = delta.get("reasoning_content", None) # 思考过程
          content: str | None = delta.get("content", None)
          tool_calls: list[dict[str, Any]] | None = delta.get("tool_calls", None)

          if reasoning_content is not None:
               continue
          if tool_calls is None and content is None:
               continue
          
          if usage is not None and len(usage) > 0:
               input_tokens: int = usage.get("prompt_tokens", 0)
               output_tokens: int = usage.get("completion_tokens", 0)
               cache_tokens: int = usage.get("prompt_cache_hit_tokens", 0)
               cost = Usage(
                    input_tokens=input_tokens, 
                    output_tokens=output_tokens, 
                    cached_tokens=cache_tokens,
               )
               logger.debug(f"本次 stream 消耗token {str(cost)}")
               # out 参数，交给上层
               if usage_out is not None:
                    usage_out.append(cost)

          yield data






# 返回字段模版
temp_openai = {
    "id": "dd7ee78f-df8e-4c7d-a4e0-652187f74d6a",
    "object": "chat.completion.chunk",
    "created": 1780023448,
    "model": "deepseek-v4-flash",
    "system_fingerprint": "fp_8b330d02d0_prod0820_fp8_kvcache_20260402",
    "choices": [
        {
            "index": 0,
            "delta": {
                "content": "",
                "reasoning_content": "null"
            },
            "logprobs": "null",
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 7,
        "completion_tokens": 162,
        "total_tokens": 169,
        "prompt_tokens_details": {
            "cached_tokens": 0
        },
        "completion_tokens_details": {
            "reasoning_tokens": 123
        },
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 7
    }
}