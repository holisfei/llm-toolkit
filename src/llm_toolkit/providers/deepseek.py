from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

import httpx
from loguru import logger

from llm_toolkit.exceptions import (
    LLMResponseError,
    LLMServerError,
    LLMTimeoutError,
)
from llm_toolkit.models import ChatResponse, LLMUrl, Message, Role, StreamChunk, Tool, ToolResult, Usage
from llm_toolkit.providers.base import BaseProvider, generate_params, translate_http_error
from llm_toolkit.retry import make_retrying
from llm_toolkit.stream_parse import parse_openai_sse
from llm_toolkit.stream_toolcall import StreamAccumulator
from llm_toolkit.tool_transform import parse_openai_tool_calls, tool_generate_message_to_openai, tool_result_to_openai, tool_to_openai


class DeepSeekProvider(BaseProvider):
    name = "deepseek"

    def __init__(self, api_key: str | None = None, env_name: str = ""):
        super().__init__(api_key, env_name)
        self.url = f"{LLMUrl.DEEPSEEK.base_url}{LLMUrl.DEEPSEEK.end_point}"

    async def chat(
        self, 
        messages: list[Message], 
        tools: list[Tool] | None = None,  
        model: str = "deepseek-v4-flash"
    ) -> ChatResponse:
        params = generate_params(messages=messages, model=model)
        if tools is not None:
            params["tools"] = [tool_to_openai(t) for t in tools]
        logger.debug(f"deepseek 参数：{json.dumps(params, indent=4, ensure_ascii=False)}")

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            # ┌────────── 关键决策 1:client 在 retry 外 ──────────
            # │ 这样 3 次尝试复用同一个 client(同一个连接池)
            # │ 如果把 AsyncClient(...) 放 retry 里,每次重试都新建连接,白白丢性能
            # └─────────────────────────────────────────────────
            async for attempt in make_retrying():
                with attempt:
                    try: # try 捕获自定义的错误类型
                        response = await client.post(url=self.url, json=params)
                        response.raise_for_status()
                        # ┌──── 关键决策 2:JSON 解析 + 翻译 也放 with attempt 里 ────
                        # │ JSON 解析失败(JSONDecodeError)不重试(你决策表里 False)
                        # │ 但它仍然要从 with 块向外冒出去——所以放在 with 里
                        # │ tenacity 看到这个异常,is_retryable→False,reraise 出来
                        # │ 调用方拿到一个清晰的 JSONDecodeError,而不是莫名其妙的"重试 3 次"
                        # └────────────────────────────────────────────────────
                        res_json = response.json()

                        message: dict[str, Any] = res_json["choices"][0]["message"]
                        usage: dict[str, Any] = res_json["usage"]
                        res = ChatResponse(
                            content=message["content"],
                            tool_calls=parse_openai_tool_calls(res_json),
                            usage=Usage(
                                input_tokens=usage["prompt_tokens"], 
                                output_tokens=usage["completion_tokens"], 
                                cached_tokens=usage.get("prompt_cache_hit_tokens", 0) # get安全取值
                            ),
                            model=res_json["model"],
                            content_tools=message.get("tool_calls", None),
                            raw=res_json
                        )
                        return res # 返回的时候会退出重试
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
                                
        # ┌────────── 关键决策 3:这行 raise unreachable ──────────
        # │ 因为 reraise=True,上面循环要么 return 要么向外抛异常
        # │ 物理上走不到这一行。但 mypy strict 要求所有路径有返回值
        # │ 写一个明确的 raise 表达"此处不可达",比 # type: ignore 优雅
        # └──────────────────────────────────────────────────────
        raise RuntimeError("重试循环已用尽且无返回结果——无法访问。")
    

    async def stream_chat(
        self, 
        messages: list[Message], 
        model: str,
        tools: list[Tool] | None,
        _usage_out: list[Usage] | None = None
    ) -> AsyncIterator[StreamChunk]:
        stream_options = {"stream_options": {"include_usage": True}}
        params = generate_params(messages=messages, model=model, stream=True, extra=stream_options)
        if tools is not None:
            params["tools"] = [tool_to_openai(t) for t in tools]
        logger.debug(f"deepseek 参数：{json.dumps(params, indent=4, ensure_ascii=False)}")

        # 必须用临时变量，要不然会一直往里拼接脏数据
        stream_accumulator = StreamAccumulator()

        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            try: 
                async with client.stream("POST", url=self.url, json=params) as response:
                    response.raise_for_status()
                    # 这里流 chunk 经过两道管线
                    # 1. 解析管线层，过滤没用的 data，统计 usage
                    # 2. 收集管线层：收集完整的 流 text、流 tools，
                    async for chunk in parse_openai_sse(response.aiter_lines(), usage_out=_usage_out):
                        stream_accumulator.feed_openai_event(chunk)
                        sc = stream_accumulator.chunk()
                        if sc.kind == "done": # 提前生成好需要拼回去的tool msg
                            sc = replace(sc, assistant_content=tool_generate_message_to_openai(stream_accumulator))
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
        messages.append(Message(role=Role.ASSISTANT, content=None, tool_calls=res.content_tools))  
        messages.extend([Message.model_validate(tool_result_to_openai(r)) for r in tool_results])      

    def append_tool_round_stream(
        self,
        messages: list[Message], 
        tool_results: list[ToolResult],
        content: Any
    ) -> None:
        messages.append(Message(role=Role.ASSISTANT, content=None, tool_calls=content))
        messages.extend([Message.model_validate(tool_result_to_openai(r)) for r in tool_results])