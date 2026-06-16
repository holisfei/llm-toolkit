from collections.abc import AsyncIterator
from typing import Any

from llm_toolkit.stream_parse import parse_anthropic_sse, parse_openai_sse
from llm_toolkit.stream_toolcall import StreamAccumulator

# 测试工具

async def fake_lines(lines: list[str]) -> AsyncIterator[str]:
    for line in lines:
        yield line

async def collect_openai(stream: AsyncIterator[dict[str, Any]]) -> list[str]:
    results: list[str] = []
    async for line in stream:
        stream_accumulator = StreamAccumulator()
        stream_accumulator.feed_openai_event(line)
        sc = stream_accumulator.chunk()
        results.append(sc.chunk)
    return results

async def collect_anthropic(stream: AsyncIterator[dict[str, Any]]) -> list[str]:
    results: list[str] = []
    async for line in stream:
        stream_accumulator = StreamAccumulator()
        stream_accumulator.feed_anthropic_event(line)
        sc = stream_accumulator.chunk()
        results.append(sc.chunk)
    return results

# 测试用例 - openai系列

class TestParseOpenAISSE:

    async def test_normal_two_chunks(self) -> None:
        """正常"""
        lines = [
            'data: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: [DONE]',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["你", "好"]

    async def test_empty_lines_are_skipped(self) -> None:
        """空白行"""
        lines = ["", "  ", "\t", 'data: {"choices":[{"delta":{"content":"hi"}}]}', 'data: [DONE]']
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["hi"]

    async def test_done_terminates_stream(self) -> None:
        """[DONE] 哨兵之后,即使还有 data 行也不该再 yield(防御性)。"""
        lines = [
            'data: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: [DONE]',
            'data: {"choices":[{"delta":{"content":"。"},"finish_reason":null}]}',
        ]
        
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["你", "好"]

    async def test_delta_without_content_is_skipped(self) -> None:
        """delta 里没有 content 字段(比如首个 chunk 只有 role),不该 yield 空串。"""
        lines = [
            'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}',
            'data: [DONE]',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["你好"]

    async def test_empty_choices_chunk_not_yielded(self) -> None:
        """最后那个 usage chunk(choices=[])不该 yield 任何内容。"""
        lines = [
            'data: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":162,"total_tokens":169},"id":"ieyrhdfh"}',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["你","好"]
    
    async def test_non_data_lines_are_skipped(self) -> None:
        """不以 'data: ' 开头的行应该跳过(SSE 里可能有其它字段如 event: / id:)。"""
        lines = [
            'json: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}, id: "9h669ehh',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: [DONE]',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect_openai(lines_iterrator)
        assert result == ["好"]

# 测试用例 - claude系列

class TestParseAnthropicSSE:

    async def test_normal_text_deltas(self) -> None:
        """正常"""
        lines = [
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"好"}}',
        ]
        lines_iterrator = parse_anthropic_sse(fake_lines(lines))
        result = await collect_anthropic(lines_iterrator)
        assert result == ["你","好"]
    
    def test_accumulator_skips_non_text_events(self) -> None:
        """message_start / ping / message_stop 不影响 text 累积。"""
        acc = StreamAccumulator()
        events: list[dict[str, Any]] = [
            {"type": "message_start", "message": {"id": "msg_01"}},
            {"type": "ping"},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "hi"}},
            {"type": "message_stop"},
        ]
        for e in events:
            acc.feed_anthropic_event(e)
        assert acc._text_buffer == "hi"

    def test_accumulator_routes_text_vs_tool(self) -> None:
        """text_delta 进 text;input_json_delta 进 tool;thinking_delta 不进 text。"""
        acc = StreamAccumulator()
        events: list[dict[str, Any]] = [
            {"type": "content_block_start", "index": 0,
            "content_block": {"type": "tool_use", "id": "t1", "name": "f"}},
            {"type": "content_block_delta", "index": 0,
            "delta": {"type": "input_json_delta", "partial_json": '{"a":1}'}}, # tool
            {"type": "content_block_delta", "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "hmm"}},  # thinking_delta
            {"type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": "answer"}},
        ]
        for e in events:
            acc.feed_anthropic_event(e)
        assert acc._text_buffer == "answer"   # thinking 没混进 text
        # tool 那边:
        tool_calls = acc.result_toll_call()
        assert tool_calls[0].arguments == {"a": 1}

    async def test_text_delta_with_usage_yields_text_and_records_usage(self) -> None:
        """带 usage 的 message_delta 事件不应该被当作文本 yield(usage 是元信息,不是回复)。"""
        lines: list[str] = [
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"好"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"。"},"usage":{"input_tokens":10,"output_tokens":12,"cache_read_input_tokens":18}}',
        ]
        lines_iterrator = parse_anthropic_sse(fake_lines(lines))
        result = await collect_anthropic(lines_iterrator)
        assert result == ["你","好","。"]