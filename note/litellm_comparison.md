# llm-toolkit vs LiteLLM 对比

## 背景

llm-toolkit 是一个手写的轻量 LLM SDK,集成 DeepSeek / Anthropic / GLM 三家。
引入 LiteLLM 做对比实验,让它成为 llm-toolkit 的【第 4 个 provider】,
验证抽象层的扩展性,同时逐项对比设计取舍。

## 维度 1:抽象边界

抽象层的核心目的是统一接口,让调用方用同一套 API 访问不同 provider。

**llm-toolkit**:`LLM → Provider → httpx → API`,3 层调用链,traceback 浅。
调试时栈帧少,问题定位快。

**LiteLLM**:`acompletion → router → provider handler → 各家官方 SDK 或 httpx → API`,
5+ 层调用链。功能多但 traceback 深,出错时需要在多层封装中翻找。

**取舍**:llm-toolkit 链短易调试,代价是功能边界小;LiteLLM 链长功能强,代价是
调试体验差。**短链更适合学习和小规模生产,长链更适合需要 100+ provider 的大规模场景**。

## 维度 2:provider 覆盖度

覆盖度决定了 LLM 选择的多样性,但够用就行,不需要为不需要的 provider 付出抽象成本。

**llm-toolkit**:支持 3 家手写适配器(DeepSeek/Anthropic/GLM)。新增一家
OpenAI/Gemini 的成本是手写 ~80 行 provider(含异常翻译、流式解析、字段映射)。
调用层确实无感,但 provider 层的工作量真实存在。

**LiteLLM**:开箱支持 100+ provider,新增一家成本为 0(已支持的话)。

**取舍**:**3 家手写 vs 100 家现成,选择题取决于你支持的实际是几家**。
如果业务上只需要 3-5 家固定 provider,手写更可控(每家行为你都看过);
如果将来要随业务接新 provider,LiteLLM 几乎是唯一合理选择。生产中绝大多数
Agent 项目倾向 LiteLLM。

## 维度 3:异常体系

异常体系的目的:让调用方写最少的 except 子句,捕获到语义最清晰的异常。

**llm-toolkit**:7 个语义化异常(LLMAuthError / LLMRateLimitError / LLMServerError /
LLMTimeoutError / LLMBadRequestError / LLMConfigError / LLMResponseError),
所有 httpx 层异常在 provider 内统一翻译,`raise ... from e` 保留 `__cause__` 链。
调用方写 `except LLMAuthError` 就能跨 provider 抓所有认证错。

**LiteLLM**:有 `litellm.exceptions.*`,但因为要兼容 100+ provider,**翻译不彻底**,
某些场景仍抛底层 SDK 原生异常(`openai.AuthenticationError` 等),调用方需要熟悉
LiteLLM 的异常映射或者用 `Exception` 兜底。

**取舍**:llm-toolkit 异常体系**更彻底也更扁平**;LiteLLM 因 provider 多样性付出了
**异常一致性的代价**。**这是 llm-toolkit 真正胜出 LiteLLM 的一个维度**。

## 维度 4:cost 计算

直观感受钱花在哪,以及做精细成本归因。

**llm-toolkit**:`MODEL_PRICING_MAP` 静态价格表,7 个模型,带 `last_verified`
日期戳。`Cost` 对象细分为 `input_usd / output_usd / cached_usd`,调用方可以
做精细成本分析(比如:"我的成本里有多少是 cache hit 省下来的")。

**LiteLLM**:内置 `model_prices_and_context_window` 表,100+ 模型,从 GitHub
自动同步。`response._hidden_params['response_cost']` 直接是 float total,**没有
input/output/cached 细分**。

**取舍**:**llm-toolkit cost 模型更细致**(这是 Day 11 你做缓存计费时埋下的设计
红利);**LiteLLM 数据覆盖更全且自动更新**。代价是 llm-toolkit 价格 3 个月不更新
就过期,需要人肉维护。

## 维度 5:retry 与 batch

**llm-toolkit**:
- retry 用 `tenacity` 实现指数退避,`is_retryable_exception` 决策表显式列举可重试状态码(429/500/502/503/504/529),16+ 测试 case 钉死每条决策路径
- `batch_chat` 用 `asyncio.Semaphore + asyncio.gather(return_exceptions=True)`,调用方显式控制 `concurrency` 参数
- 整套策略可审计、可单测、可在代码里直接读懂

**LiteLLM**:
- `num_retries=N` 参数,内部重试策略是黑盒(具体哪些异常重试需要看源码)
- SDK 层默认不限制并发(调用方仍然要自己写 Semaphore),但 Router 层支持
  `max_parallel_requests` 配置(需要单独启用 Router)
- 黑盒策略对快速集成友好,对 debug 不友好

**取舍**:**金融/医疗/Agent 容错重要的场景,可审计的 retry 决策表更值钱**;
**只想"重试 N 次能省事"的快速集成场景,LiteLLM `num_retries=3` 一行搞定**。

## 整体取舍:什么场景选哪个

| 场景 | 选择 | 理由 |
|---|---|---|
| 学习/理解 LLM SDK 工程化 | llm-toolkit | 短链可读,每层都自己写过,认知收益最大 |
| 3-5 家固定 provider 的稳定业务 | llm-toolkit | 控制力强,异常语义化,cost 可细分 |
| 需要 fallback 到任意 provider 的 Agent 系统 | LiteLLM | 100+ provider 覆盖,加新模型零成本 |
| 强可审计/合规要求(金融、医疗) | llm-toolkit | retry 决策可单测,异常翻译显式 |
| 快速原型/不关心底层细节 | LiteLLM | 一行 `acompletion` 直接跑,不用关心适配 |
| 已经在用 LangChain/LlamaIndex 等上层框架 | LiteLLM | 这些框架内置对 LiteLLM 支持 |

**一句话总结**:llm-toolkit 是"知道每一层在做什么的小而美 SDK",LiteLLM 是"功能
覆盖全但需要接受一定黑盒的工业级抽象层"。**没有谁绝对更好,只有场景匹配**。

## 从 LiteLLM 学到的

1. **Fallback 模型链**(`fallbacks=["claude-opus", "gpt-4o", "ollama/llama"]`):
   主模型挂了自动降级到备选。这是生产 Agent 系统的常见需求(主 API 限流时
   降级到备用 provider)。llm-toolkit 目前没有这个能力,但 BaseProvider 抽象
   下加一层 "FallbackProvider" 应该不难——后续可以补。

2. **Callbacks 机制**(success_callback / failure_callback 钩到 Langfuse 等
   可观测平台):生产里"每次调用都打点到监控系统"是刚需。llm-toolkit 目前的
   `cost_tracker` 只是 session 内累计,生产化需要类似的回调机制——这是
   llm-toolkit 演进到生产可用还要补的一块。