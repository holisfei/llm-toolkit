# 工具抽象 + Streaming

## anthropic 系流式tools

```json
data: {"type":"message_start","message":{"model":"claude-sonnet-4-6","id":"msg_01NKWtjM25t9yn6BJ9UtkorR","type":"message","role":"assistant","content":[],"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":616,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":0},"output_tokens":2,"service_tier":"standard","inference_geo":"global"}}            }

data:{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

data: {"type": "ping"}

data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"好"} }
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"的，我来帮您查询账户余额！"}}
data: {"type":"content_block_stop","index":0}

data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_019P977krRPooroJpExQiG64","name":"get_user_balance","input":{},"caller":{"type":"direct"}}}

data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":""}}

data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"u"}}
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"sern"}    }
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"ame"}              }
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"\": \"holis"}}
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"\"}"}   }
data: {"type":"content_block_stop","index":1  }

data: {"type":"message_delta","delta":{"stop_reason":"tool_use","stop_sequence":null,"stop_details":null},"usage":{"input_tokens":616,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":73} }
```

## openai 系流式tools

```json
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"role":"assistant","content":null,"reasoning_content":""},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"用户"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"想"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"查询"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"账户"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"余额"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"，"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"看看"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"是否"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"足够"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"购买"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"一台"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"500"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"0"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"元的"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"电脑"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"。"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"我需要"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"使用"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"get"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"_user"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"_"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"balance"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"工具"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"来"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"查询"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"用户"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"hol"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"is"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"的"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"余额"},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"。"},"logprobs":null,"finish_reason":null}],"usage":null}

data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"好的","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"！","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
！data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"我来","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"帮你","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"查询","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"账户","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"余额","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"。","reasoning_content":null},"logprobs":null,"finish_reason":null}],"usage":null}

data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_00_oNaYFdzFE2LrYatAn7252220","type":"function","function":{"name":"get_user_balance","arguments":""}}]},"logprobs":null,"finish_reason":null}],"usage":null}

data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{"}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\""}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"username"}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\""}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":": "}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\""}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"hol"}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"is"}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\""}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"}"}}]},"logprobs":null,"finish_reason":null}],"usage":null}
data: {"id":"23d01db0-7b76-413e-b4fd-b0bf3362f996","object":"chat.completion.chunk","created":1781233924,"model":"deepseek-v4-flash","system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402","choices":[{"index":0,"delta":{"content":"","reasoning_content":null},"logprobs":null,"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":306,"completion_tokens":85,"total_tokens":391,"prompt_tokens_details":{"cached_tokens":256},"completion_tokens_details":{"reasoning_tokens":31},"prompt_cache_hit_tokens":256,"prompt_cache_miss_tokens":50}}
```

## Anki

Q: 判断"抽象层漏了"的信号是什么?

A: 上层代码出现 if provider == "..." / model.startswith(...)。provider 差异泄漏到上层就是抽象边界画错了位置。脏东西(provider 原生格式)消不掉,但要关进越靠内的盒子越好(显式传参 > 隐式从 self 捞)。
Q: 流式下 tool 调用的参数,"什么时候算拼完整、可以执行"?信号谁给?

A: 靠协议的明确结束事件(Anthropic 的 content_block_stop / OpenAI 的 finish_reason),不靠中途 json.loads 试探——碎片不尊重 JSON 边界,会切在半个 key 中间,中途 parse 必失败。按 index 分桶累积,收到结束信号再 parse。
Q: frozen dataclass 想"改一个字段"怎么办?为什么不能直接赋值?

A: 不能 obj.x = v(抛 FrozenInstanceError)。frozen 对象不可变,要"改"就是造新的:dataclasses.replace(obj, x=v)。等价于 Swift 里 let struct 拷一份再改。
Q: 把 per-request 状态(如 StreamAccumulator)挂成 client 实例字段,有什么风险?reset() 能解决吗?

A: 并发下必然串台——两个并发请求共享同一个 accumulator,碎片交替写入同一状态。reset() 只能擦"上一次",挡不住"另一个正在并行跑的"。正解是局部变量:让状态生命周期(一次请求)和它的作用域对齐