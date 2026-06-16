from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

import httpx
from dotenv import load_dotenv
from loguru import logger

from llm_toolkit.exceptions import (
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.providers.base import BaseProvider, generate_params, translate_http_error
from llm_toolkit.retry import make_retrying
from llm_toolkit.stream_parse import parse_anthropic_sse
from llm_toolkit.stream_toolcall import StreamAccumulator
from llm_toolkit.tool_transform import parse_anthropic_tool_calls, tool_generate_message_to_anthropic, tool_result_to_anthropic, tool_to_anthropic
from llm_toolkit.types import ChatResponse, EnvApiKeyName, LLMUrl, Message, Role, StreamChunk, Tool, ToolResult, Usage

load_dotenv()
        

class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        
        self.url = f"{LLMUrl.ANTHROPIC.base_url}{LLMUrl.ANTHROPIC.end_point}"

        if "Authorization" in self.headers:
            self.headers.pop("Authorization")
        self.headers["anthropic-version"] = "2023-06-01"
        key: str | None = os.getenv(EnvApiKeyName.ANTHROPIC_API_KEY)
        if key:
            self.headers["x-api-key"] = key

    async def chat(
        self, 
        messages: list[Message], 
        tools: list[Tool] | None = None, 
        model: str ="claude-sonnet-4-6"
    ) -> ChatResponse:
        params = generate_params(
            messages=[m for m in messages if m.role != Role.SYSTEM],        
            model=model, stream=False
        )
        params["max_tokens"] = 2048
        
        system: list[str] | None = [m.content for m in messages if m.role == Role.SYSTEM]
        if system is not None and len(system) > 0:
            params["system"] = system[0]
        
        if tools is not None:
            params["tools"] = [tool_to_anthropic(t) for t in tools]
        logger.debug(f"claude 参数：{json.dumps(params, indent=4, ensure_ascii=False)}")
        
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            # 重试逻辑
            async for attempt in make_retrying():
                with attempt:
                    try:
                        response = await client.post(url=self.url, json=params)
                        response.raise_for_status()
                        res_json = response.json()
                        # print(f"calude响应：{json.dumps(res_json, indent=4, ensure_ascii=False)}")
                        contents: list[dict[str, Any]] = res_json["content"]
                        content: dict[str, Any] = contents[0]
                        usage: dict[str, Any] = res_json["usage"]
                        res = ChatResponse(
                            content=content["text"],
                            tool_calls=parse_anthropic_tool_calls(res_json),
                            usage=Usage(
                                input_tokens=usage["input_tokens"], 
                                output_tokens=usage["output_tokens"], 
                                # 通过 dict.get(key, 默认值) 安全取值
                                cached_tokens=usage.get("cache_read_input_tokens", 0)
                            ),
                            model=res_json["model"],
                            content_tools=contents,
                            raw=res_json
                        )
                        return res
                    except httpx.HTTPStatusError as e:
                        raise translate_http_error(e=e, provider=self.name) from e
                    except httpx.TimeoutException as e:
                        raise LLMTimeoutError(
                             f"request timeout: {e}",
                            provider=self.name,
                        ) from e
                    except httpx.TransportError as e:
                        raise LLMServerError(
                            f"transport error: {e}",
                            provider=self.name,
                        ) from e
                    except (KeyError, ValueError) as e:
                        raise LLMResponseError(
                            f"failed to parse response: {type(e).__name__}: {e}",
                            raw_body=response.text if 'response' in locals() else None,
                            provider=self.name,
                        ) from e
                    # from e 的作用，自动设置 __cause__
        raise RuntimeError("重试循环已用尽且无返回结果——无法访问。")
    
    async def stream_chat(
        self, 
        messages: list[Message], 
        model: str,
        tools: list[Tool] | None,
        _usage_out: list[Usage] | None = None
    ) -> AsyncIterator[StreamChunk]:
        params = generate_params(
            messages=[m for m in messages if m.role != Role.SYSTEM],        
            model=model, stream=True
        )
        params["max_tokens"] = 2048
        
        system: list[str] | None = [m.content for m in messages if m.role == Role.SYSTEM]
        if system is not None and len(system) > 0:
            params["system"] = system[0]
        
        if tools is not None:
            params["tools"] = [tool_to_anthropic(t) for t in tools]
        logger.debug(f"claude 参数：{json.dumps(params, indent=4, ensure_ascii=False)}")
        
        # 必须用临时变量，要不然会一直往里拼接脏数据
        stream_accumulator = StreamAccumulator()

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            try:
                async with client.stream("POST", url=self.url, json=params) as response:
                    response.raise_for_status()
                    # 这里流 chunk 经过两道管线
                    # 1. 解析管线层，过滤没用的 data，统计 usage
                    # 2. 收集管线层：收集完整的 流 text、流 tools，
                    async for chunk in parse_anthropic_sse(response.aiter_lines(), usage_out=_usage_out):
                        stream_accumulator.feed_anthropic_event(chunk)
                        sc = stream_accumulator.chunk()
                        if sc.kind == "done": # 提前生成好需要拼回去的tool msg
                            sc = replace(sc, assistant_content=tool_generate_message_to_anthropic(stream_accumulator))
                        yield sc
            except httpx.HTTPStatusError as e:
                raise translate_http_error(e=e, provider=self.name) from e
            except httpx.TimeoutException as e:
                raise LLMTimeoutError(
                    f"stream timeout: {e}",
                    provider=self.name,
                ) from e
            except httpx.TransportError as e:
                raise LLMServerError(
                    f"stream transport error: {e}",
                    provider=self.name,
                ) from e 
            
    def append_tool_round(
        self, 
        res: ChatResponse, 
        messages: list[Message], 
        tool_results: list[ToolResult]
    ) -> None:
        messages.append(Message(role=Role.ASSISTANT, content=res.content_tools))
        messages.append(Message(role=Role.USER, content=[tool_result_to_anthropic(r) for r in tool_results]))

    def append_tool_round_stream(
        self,
        messages: list[Message], 
        tool_results: list[ToolResult],
        content: Any
    ) -> None:
        messages.append(Message(role=Role.ASSISTANT, content=content))
        messages.append(Message(role=Role.USER, content=[tool_result_to_anthropic(r) for r in tool_results]))