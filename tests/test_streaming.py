from collections.abc import AsyncIterator

from llm_toolkit.streaming import parse_anthropic_sse, parse_openai_sse

# 测试工具

async def fake_lines(lines: list[str]) -> AsyncIterator[str]:
    for line in lines:
        yield line

async def collect(stream: AsyncIterator[str]) -> list[str]:
    return [line async for line in stream]

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
        result = await collect(lines_iterrator)
        assert result == ["你", "好"]

    async def test_empty_lines_are_skipped(self) -> None:
        """空白行"""
        lines = ["", "  ", "\t", 'data: {"choices":[{"delta":{"content":"hi"}}]}', 'data: [DONE]']
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
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
        result = await collect(lines_iterrator)
        assert result == ["你", "好"]

    async def test_delta_without_content_is_skipped(self) -> None:
        """delta 里没有 content 字段(比如首个 chunk 只有 role),不该 yield 空串。"""
        lines = [
            'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}',
            'data: [DONE]',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
        assert result == ["你好"]

    async def test_empty_choices_chunk_not_yielded(self) -> None:
        """最后那个 usage chunk(choices=[])不该 yield 任何内容。"""
        lines = [
            'data: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":162,"total_tokens":169},"id":"ieyrhdfh"}',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
        assert result == ["你","好"]
    
    async def test_non_data_lines_are_skipped(self) -> None:
        """不以 'data: ' 开头的行应该跳过(SSE 里可能有其它字段如 event: / id:)。"""
        lines = [
            'json: {"choices":[{"delta":{"content":"你"},"finish_reason":null}]}, id: "9h669ehh',
            'data: {"choices":[{"delta":{"content":"好"},"finish_reason":null}]}',
            'data: [DONE]',
        ]
        lines_iterrator = parse_openai_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
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
        result = await collect(lines_iterrator)
        assert result == ["你","好"]
    
    async def test_non_content_block_delta_events_skipped(self) -> None:
        """message_start / message_stop / ping 等事件应该全部跳过,不 yield。"""
        lines = [
            'data: {"type":"message_start","message":{"id":"msg_01"}}',
            'data: {"type":"ping"}',
            'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hi"}}',
            'data: {"type":"message_stop"}',
        ]
        lines_iterrator = parse_anthropic_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
        assert result == ["hi"]

    async def test_non_text_delta_in_content_block_delta_skipped(self) -> None:
        """content_block_delta 里 delta.type 不是 text_delta(比如 input_json_delta、
        thinking_delta、signature_delta)应该跳过——这是 Claude 的核心坑。"""
        lines = [
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"a\\":"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"hmm"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"answer"}}',
        ]
        lines_iterrator = parse_anthropic_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
        assert result == ["answer"]

    async def test_text_delta_with_usage_yields_text_and_records_usage(self) -> None:
        """带 usage 的 message_delta 事件不应该被当作文本 yield(usage 是元信息,不是回复)。"""
        lines = [
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"好"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"。"},"usage":{"input_tokens":10,"output_tokens":12,"cache_read_input_tokens":18}}',
        ]
        lines_iterrator = parse_anthropic_sse(fake_lines(lines))
        result = await collect(lines_iterrator)
        assert result == ["你","好","。"]