## anthropic 系一次完整的tool调用流程：

请求1：参数带 tools：

```json
{
    "model": "claude-sonnet-4-6",
    "messages": [
        {
            "role": "user",
            "content": "123 乘以 456 等于多少?"
        }
    ],
    "stream": false,
    "max_tokens": 2048,
    "tools": [
        {
            "name": "calculator",
            "description": "由两个输入参数，计算最终结果",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "参数a"
                    },
                    "b": {
                        "type": "number",
                        "description": "参数b"
                    },
                    "op": {
                        "type": "string",
                        "enum": [
                            "add",
                            "subtract",
                            "multiply",
                            "divide"
                        ],
                        "description": "计算运算符"
                    }
                },
                "required": [
                    "a",
                    "b",
                    "op"
                ]
            }
        }
    ]
}
```

claude 响应1: 带tool_use回调参数

```json
{
    "model": "claude-sonnet-4-6",
    "id": "msg_01V12ouehLLsY698jxLPnK5o",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "我来帮你计算 123 × 456 的结果！"
        },
        {
            "type": "tool_use",
            "id": "toolu_01FKwWiyTDtftEFAxUxtSBgk",
            "name": "calculator",
            "input": {
                "a": 123,
                "b": 456,
                "op": "multiply"
            },
            "caller": {
                "type": "direct"
            }
        }
    ],
    "stop_reason": "tool_use",
    "stop_sequence": null,
    "stop_details": null,
    "usage": {
        "input_tokens": 645,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation": {
            "ephemeral_5m_input_tokens": 0,
            "ephemeral_1h_input_tokens": 0
        },
        "output_tokens": 105,
        "service_tier": "standard",
        "inference_geo": "global"
    }
}
```

claude 参数2：拿到响应1的tool参数，做tool逻辑，然后将结果和上一次的回复再次作为参数发出去

```json
{
    "model": "claude-sonnet-4-6",
    "messages": [
        {
            "role": "user",
            "content": "123 乘以 456 等于多少?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "我来帮你计算 123 × 456 的结果！"
                },
                {
                    "type": "tool_use",
                    "id": "toolu_01FKwWiyTDtftEFAxUxtSBgk",
                    "name": "calculator",
                    "input": {
                        "a": 123,
                        "b": 456,
                        "op": "multiply"
                    },
                    "caller": {
                        "type": "direct"
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01FKwWiyTDtftEFAxUxtSBgk",
                    "content": "111"
                }
            ]
        }
    ],
    "stream": false,
    "max_tokens": 2048,
    "tools": [
        {
            "name": "calculator",
            "description": "由两个输入参数，计算最终结果",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "参数a"
                    },
                    "b": {
                        "type": "number",
                        "description": "参数b"
                    },
                    "op": {
                        "type": "string",
                        "enum": [
                            "add",
                            "subtract",
                            "multiply",
                            "divide"
                        ],
                        "description": "计算运算符"
                    }
                },
                "required": [
                    "a",
                    "b",
                    "op"
                ]
            }
        }
    ]
}
```

claude 响应2：得到最终的回复

```json
{
    "model": "claude-sonnet-4-6",
    "id": "msg_01RFWgsv3hhUC5y1YbGJV269",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "123 乘以 456 的结果是 **56,088**。\n\n> 计算过程：123 × 456 = 56,088"
        }
    ],
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "stop_details": null,
    "usage": {
        "input_tokens": 763,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation": {
            "ephemeral_5m_input_tokens": 0,
            "ephemeral_1h_input_tokens": 0
        },
        "output_tokens": 41,
        "service_tier": "standard",
        "inference_geo": "global"
    }
}
```


## openai 系一次完整的tool调用流程：

参数1:

```json
{
    "model": "deepseek-v4-flash",
    "messages": [
        {
            "role": "user",
            "content": "我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?"
        }
    ],
    "stream": false,
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_user_balance",
                "description": "查询指定用户的账户余额(单位:元)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "用户名"
                        }
                    },
                    "required": [
                        "username"
                    ]
                }
            }
        }
    ]
}
```

响应1:

```json
 {
    "id": "559688c5-d097-4f34-bc49-39ec2f00e165",
    "object": "chat.completion",
    "created": 1781090394,
    "model": "deepseek-v4-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "好的，我来帮你查询账户余额！",
                "reasoning_content": "用户想查询账户余额，看看是否足够购买一台5000元的电脑。我需要先查询用户的余额。",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_00_1ijdp7TXJT7WpPRYWUdI8721",
                        "type": "function",
                        "function": {
                            "name": "get_user_balance",
                            "arguments": "{\"username\": \"holis\"}"
                        }
                    }
                ]
            },
            "logprobs": null,
            "finish_reason": "tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": 306,
        "completion_tokens": 76,
        "total_tokens": 382,
        "prompt_tokens_details": {
            "cached_tokens": 0
        },
        "completion_tokens_details": {
            "reasoning_tokens": 22
        },
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 306
    },
    "system_fingerprint": "fp_8b330d02d0_prod0820_fp8_kvcache_20260402"
}
```

参数2:

```json
{
    "model": "deepseek-v4-flash",
    "messages": [
        {
            "role": "user",
            "content": "我的用户名是 holis,我账户里还有多少钱?够买一台 5000 元的电脑吗?"
        },
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call_00_8FREAtP0yp4UoApFccg05752",
                    "type": "function",
                    "function": {
                        "name": "get_user_balance",
                        "arguments": "{\"username\": \"holis\"}"
                    }
                }
            ]
        },
        {
            "role": "tool",
            "content": "账户余额为 -999 元",
            "tool_call_id": "call_00_8FREAtP0yp4UoApFccg05752"
        }
    ],
    "stream": false,
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_user_balance",
                "description": "查询指定用户的账户余额(单位:元)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "用户名"
                        }
                    },
                    "required": [
                        "username"
                    ]
                }
            }
        }
    ]
}
```

响应3:

```json
{
    "id": "eae24ea0-45f7-44a2-8f18-e4745d4504cd",
    "object": "chat.completion",
    "created": 1781162055,
    "model": "deepseek-v4-flash",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "查询结果如下：\n\n您的账户余额为 **-999 元**（即欠费 999 元），所以目前 **不够** 购买一台 5000 元的电脑。😅\n\n您需要至少先充值 **5999 元**（补足欠费 999 元 + 电脑 5000 元）才能购买哦！",
                "reasoning_content": "用户的余额是 -999 元，这意味着账户欠费999元，显然不够买5000元的电脑。"
            },
            "logprobs": null,
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 394,
        "completion_tokens": 98,
        "total_tokens": 492,
        "prompt_tokens_details": {
            "cached_tokens": 256
        },
        "completion_tokens_details": {
            "reasoning_tokens": 23
        },
        "prompt_cache_hit_tokens": 256,
        "prompt_cache_miss_tokens": 138
    },
    "system_fingerprint": "fp_8b330d02d0_prod0820_fp8_kvcache_20260402"
}
```

## 模型对tool结果的采纳

模型对 tool_result 无条件信任,不做合理性校验。 

在模型自己有能力的领域(如简单算术),它可能用自身答案覆盖错误 tool 结果;

但在它无从判断的业务领域(余额、库存、用户数据),tool 返回什么,模型的"事实"就是什么。

因此 tool 的正确性、输入校验、脏数据防御,全是调用方(你的代码)的责任——模型不兜底。