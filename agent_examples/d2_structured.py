from __future__ import annotations

import asyncio
import json
import re

from pydantic import BaseModel, Field
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from llm_toolkit.client import LLM, Message, Role


class StructuredOutputError(Exception):
    """所有结构化输出失败的基类"""
    def __init__(self, message: str, raw_output: str, attempts: int) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.attempts = attempts

def strip_code_fence(text: str) -> str:
    """
    健壮的 LLM JSON 解析器，采用三级降级策略。
    """
    if not text:
        return None
        
    text = text.strip()
    
    # 尝试 1：直接解析（处理 LLM 乖乖输出纯 JSON 的情况）
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # 尝试 2：提取 ```json ... ``` 代码块（兼容各种换行和空格）
    # 使用 re.DOTALL 让 . 能够匹配换行符
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass
            
    # 尝试 3：提取文本中第一个 { ... } 块（处理 LLM 在段落中直接输出 JSON 的情况）
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
            
    # 全部失败
    return text

async def complete_structured[T: BaseModel](
    client: LLM,
    prompt_success: str,
    prompt_fail: str | None,
    schema: type[T],
    *,
    max_repairs: int = 2,
) -> T:
    """
    让 LLM 输出能解析为 schema 类型的结构化数据.
    
    流程:
    1. 构造 prompt: user prompt + schema 描述 (用 schema.model_json_schema())
    2. 调用 client.chat() 拿到 raw text
    3. strip_code_fence 剥皮
    4. json.loads 解析
    5. schema.model_validate(...) 验证
    6. 如果第 4/5 步失败:
       - 把错误信息塞回 prompt
       - 重试, 最多 max_repairs 次
       - 还失败就抛 StructuredOutputError
    
    - 重试时 prompt 怎么改? 把原 prompt + 上次错误一起发?
    - 失败信息要包含什么? raw_output? ValidationError 的具体内容?
    - 如何区分"格式失败"(json.loads 抛 JSONDecodeError) 和 "语义失败"(ValidationError)?
    """

    retrying = AsyncRetrying(
        stop=stop_after_attempt(max_repairs), # 最大重试次数，包含起始
        wait=wait_exponential(multiplier=0, min=1, max=30), #延迟重试 min(multiplier * 2^(n-1), max)
        retry=retry_if_exception_type(Exception), # 任何条件下都进行重试
        reraise=True # 重试耗尽后不抛RetryError，抛出原始异常
    )

    keys = schema.model_json_schema()
    append_str: str = ""

    try:
        async for attempt in retrying:
            with attempt:
                attempt_number = attempt.retry_state.attempt_number
                print(f"开始请求第{attempt_number}次")
                prompt: str = prompt_success
                if prompt_fail is not None:
                    if attempt_number == 1:
                        prompt = prompt_fail
                    else:
                        prompt = prompt_success

                content = f"{prompt} 返回可解析的JSON字符串格式，需要解析的字段为:{keys}" + append_str
                messages = [Message(role=Role.USER, content=content)]
                print(f"请求prompt: {content}")
                res = await client.chat(messages)
                res_json_str = strip_code_fence(res.content)
                print(f"第{attempt_number}次 正则结果为: {res_json_str}")
                try:
                    res_json = json.loads(res_json_str)
                except Exception as e:
                    append_str = f", 你上次的输出为: {res.content}, 但它有这个错误: {e}, 请修正后重新输出"
                    raise e
                
                try:
                    res = schema.model_validate(res_json)
                    return res
                except Exception as e:
                    append_str = f", 你上次的输出为: {res.content}, 但它有这个错误: {e}, 请修正后重新输出"
                    raise e
    except Exception as e:  # 只有当所有重试次数耗尽时，才会进入这里
        raise StructuredOutputError(
            message="无法正常解析结果", 
            raw_output=str(e), 
            attempts=max_repairs
        ) from e
    



# ---- 测试用 ----
class Person(BaseModel):
    name: str
    uid: int
    signature: str = Field(min_length=6)

class Person1(BaseModel):
    name: str
    uid: int
    signature: str
    contrycode: str = Field(min_length=2)

async def main() -> None:
    #client = LLM("claude-sonnet-4-6")
    client = LLM("deepseek-v4-flash")
    
    # 场景 1: 正常情况
    print("========== 场景 1 ========== ")
    person = await complete_structured(
        client,
        prompt_success="我是holis, uid 100000, 签名'生活不止眼前的苟且'. 提取信息.",
        prompt_fail=None,
        schema=Person,
    )
    print(f"成功: {person}")

    # 场景 2: 字段缺失 -- 让 prompt 里少一个字段, 看重试是否能拉回来
    print("========== 场景 2 ========== ")
    person2 = await complete_structured(
        client,
        prompt_success="我是holis, uid 100000. 签名'生活不止眼前的苟且'. 提取信息.",
        prompt_fail="我是holis, uid 100000. 提取信息. 严格从给定文本提取，不要自己加默认值",
        schema=Person,
    )
    print(f"成功: {person2}")

    # 场景 3: 完全没法满足 -- 你故意 schema 要 country_code, 但 prompt 里没国家信息
    # 验收 max_repairs 用尽后抛 StructuredOutputError
    print("========== 场景 3 ========== ")
    person3 = await complete_structured(
        client,
        prompt_success="我是holis, uid 100000, 签名'生活不止眼前的苟且'. 提取信息. 严格从给定文本提取，不要自己加默认值",
        prompt_fail=None,
        schema=Person1,
    )
    print(f"成功: {person3}")


if __name__ == "__main__":
    asyncio.run(main())