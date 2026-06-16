
import pytest

from llm_toolkit.models import ToolCall, tool
from llm_toolkit.stream_toolcall import _ToolCallAccumulator
from llm_toolkit.tool_transform import dispatch_all


def test_tool_generates_schema() -> None:
    """tool 装饰器正常解析"""
    @tool
    def sample(name: str, age: int = 18) -> str:
        """一个示例工具。"""
        return name

    assert sample.name == "sample"
    assert sample.description == "一个示例工具。"
    assert sample.input_schema["properties"]["name"]["type"] == "string"
    assert sample.input_schema["properties"]["age"]["type"] == "integer"
    assert "name" in sample.input_schema["required"]      # 无默认值 -> 必填
    assert "age" not in sample.input_schema["required"]   # 有默认值 -> 非必填

def test_tool_without_docstring_raises() -> None:
    """tool 函数缺失描述 -> 报错"""
    with pytest.raises(ValueError):
        @tool
        def no_doc(x: str) -> str:
            return x
        
async def test_dispatch_all_pairs_by_id() -> None:
    """dispatch_all 结果按照id匹配"""
    @tool
    def echo(x: str) -> str:
        """回声。"""
        return f"echo:{x}"
    tool_map = {echo.name: echo}
    calls = [
        ToolCall(id="id_A", name="echo", arguments={"x": "a"}),
        ToolCall(id="id_B", name="echo", arguments={"x": "b"}),
    ]

    results = await dispatch_all(calls, tool_map)
    # 配对必须靠 id, 不靠顺序
    by_id = {r.id: r for r in results}
    assert by_id["id_A"].content == "echo:a"
    assert by_id["id_B"].content == "echo:b"

async def test_dispatch_unknown_tool_returns_error() -> None:
    """模型调了一个不存在的 tool call 工具 -> tool result 的 is_error 是 true"""
    calls = [ToolCall(id="x", name="不存在", arguments={})]
    results = await dispatch_all(calls, {})
    assert results[0].is_error is True

def test_finalize_broken_json_returns_error() -> None:
    """tool 收集器 遇到不规则的json str格式 -> 返回错误结果 ToolCall"""
    acc = _ToolCallAccumulator(id="x", name="t")
    acc.add_json_fragment('{"user')   # 截断的半个 JSON
    result = acc.finalize()
    assert result.is_error is True     # 不崩, 标记错误