from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, get_type_hints

import docstring_parser
from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class EnvApiKeyName(StrEnum):
    TRANSIT_API_KEY = "TRANSIT_API_KEY"
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
    ZAI_API_KEY = "ZAI_API_KEY"
    DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"

@dataclass
class ApiUrl:
    base_url: str
    end_point: str

class LLMUrl(str, ApiUrl):
    TRANSIT = ApiUrl(base_url="https://api.highwayapi.ai/openai", end_point="/chat/completions")
    ANTHROPIC = ApiUrl(base_url="https://api.anthropic.com", end_point="/v1/messages")
    DEEPSEEK = ApiUrl(base_url="https://api.deepseek.com", end_point="/chat/completions")
    GLM = ApiUrl(base_url="https://open.bigmodel.cn", end_point="/api/paas/v4/chat/completions")
    QWEN = ApiUrl(base_url="https://ws-ly70qjwnoyegh3bs.ap-southeast-1.maas.aliyuncs.com", end_point="/compatible-mode/v1/chat/completions")

class Message(BaseModel):
    role: Role
    content: Any
    tool_calls: list[dict[str, Any]] | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    
class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    def __str__(self) -> str:
        return f"提示词:{self.input_tokens} 回复内容:{self.output_tokens} 缓存:{self.cached_tokens}"

class Cost(BaseModel):
    """单次调用的成本细分。所有金额单位:美元。"""
    input_usd: float
    output_usd: float
    cached_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd + self.cached_usd

    def __str__(self) -> str:
        return f"${self.total_usd:.4f}"

class ChatResponse(BaseModel):
    content: str        # 模型回复的文本
    tool_calls: list[ToolCall] = []  # 需要工具调用
    usage: Usage        # token用量 Usage 模型
    cost: Cost | None = None        # 转化为成本
    model: str          # 实际使用的模型名（便于 debug 和成本归因）
    content_tools: Any  # 模型回复的完整内容，用于后续的message的tools后续拼接
    raw: Any # 原始响应（保底：万一统一字段没覆盖到，还能从这里捞）

############# 工具调用 ############# 

@dataclass(frozen=True)
class Tool:
    """统一的工具定义. 发给模型, 告诉它有哪些工具可用."""
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Any]
    async def run(self, arguments: dict[str, Any]) -> Any:
        # 如果是个异步函数，则需要 await
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**arguments)
        return self.func(**arguments)

def tool(func: Callable[..., Any]) -> Tool:
    """装饰器: 把一个普通函数变成 Tool.
    从函数自动提取:
    - name: 函数名
    - description: docstring (第一行/整体, 你决定)
    - input_schema: 从参数 + 类型注解生成 JSON Schema
    """
    # 1. 获取函数 name
    name = func.__name__

    # 2. 获取函数 description（从 docstring 的第一行）
    description = ""

    # 参数的描述信息
    param_descriptions = {}
    if func.__doc__:
        parsed_doc = docstring_parser.parse(func.__doc__)
        # 提取函数的整体描述（通常是第一行或 Summary）
        description = parsed_doc.short_description or ""
        # 将参数的描述存入字典，方便后续查找
        for param_descr in parsed_doc.params:
            param_descriptions[param_descr.arg_name] = param_descr.description

    if len(description) == 0:
        raise ValueError("函数缺少描述信息，请补全描述信息")

    # 3. 获取函数签名信息
    signature = inspect.signature(func)
    # 获取函数参数和参数类型的映射
    type_hints = get_type_hints(func)
    
    properties = {}
    required_params = []
    # 定义 python type 和 json_schema type 映射关系
    json_type_map = {
        str: "string", 
        int: "integer", 
        float: "number", 
        bool: "boolean"
    }

    # 4. 遍历函数参数
    for param_name, param in signature.parameters.items():
        # 获取参数类型
        py_type = type_hints.get(param_name, str)
        if py_type not in json_type_map:
            raise ValueError(f"工具 {name} 的参数 {param_name} 类型 {py_type} 暂不支持")
        prop_schema = {
            "type": json_type_map.get(py_type, "string")
        }

        # 获取参数 描述
        if param_name in param_descriptions:
            para_descr: str | None = param_descriptions[param_name]
            if para_descr is not None:
                prop_schema["description"] = para_descr

        properties[param_name] = prop_schema

        # 设置 required
        # 如果参数值没有默认值，则任务是必填参数
        if param.default is inspect.Parameter.empty:
            required_params.append(param_name)
    
    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required_params
    }
    return Tool(
        name=name, 
        description=description, 
        input_schema=input_schema, 
        func=func
    )


@dataclass(frozen=True)
class ToolCall:
    """统一表示"模型请求调用某个工具"."""
    name: str
    id: str
    arguments: dict[str, Any]
    is_error: bool = False # 工具收集是否异常，如果异常，不去执行工具


@dataclass(frozen=True)
class ToolResult:
    """统一表示"工具执行完的结果, 要还给模型"."""
    id: str
    content: Any
    is_error: bool = False # 工具是否出错
    def __str__(self) -> str:
        return f"ToolResult: {self.id} {self.content}"

@dataclass(frozen=True) # frozen 不能改变已经生成的实例属性
class StreamChunk:
    """流式输出的一个片段.
    """
    kind: Literal["text_delta", "tool_call", "done", "start"]
    chunk: str = ""    # kind==text_delta 时有, 流式文字
    text: str | None = None          # kind==text_delta 时有, 完整的文字
    tool_call: list[ToolCall] | None = None  # kind==tool_call 时有, 完整的tools
    assistant_content: Any = None   # done 时携带: 拼下一轮 assistant 消息的原生结构