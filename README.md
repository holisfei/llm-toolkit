# llm-toolkit

一个轻量级 LLM 统一调用 SDK,一行切换不同模型，传入具体的模型名称就行

封装了 `anthropic / deepseek / glm` 三家 LLM 的统一 API,带流式、`CLI`

## 特性

- 统一抽象层:同一接口调用 `anthropic / deepseek / glm` 三家
- `Pydantic v2` 类型完整, `mypy strict` 全绿
- 流式输出(`SSE`),两家协议格式(`openai`系和`anthropic`系)统一处理
- 交互式 `CLI`(多轮对话 / 流式打输出 / 优雅退出)
- 单元测试覆盖 `SSE` 解析核心逻辑

## 支持的模型

统计时间`2026-06-01`

| Provider | 示例 model | 备注 |
| --- | --- | --- |
| DeepSeek | deepseek-v4-flash | 性价比高 |
| Anthropic | claude-sonnet-4-6 | Agent 场景强 |
| Zhipu (GLM) | glm-4.7 | 国产大模型top |
     
⚠️ 重要: "模型 ID 和价格以官方文档为准,本仓库不保证及时性"

## 快速开始

### 安装

```bash
git clone https://github.com/holisfei/llm-toolkit.git
cd llm-toolkit
uv sync
```

### 配置 API key

复制 `.env.example` 并填上你要用的那家的 API key:

```bash
cp .env.example .env
# 编辑 .env,填入对应 API key(三家任选其一即可)
```

⚠️注意：`.env` 文件，本地管理环境变量，不要提交到git

### Python 使用

```python
import asyncio
from llm_toolkit.client import LLM

async def main():
    llm = LLM("deepseek-v4-flash")
    resp = await llm.chat("用一句话解释什么是 async/await")
    print(resp.content)

asyncio.run(main())
```

### CLI 使用

```bash
uv run llm-toolkit chat -m deepseek-v4-flash
uv run llm-toolkit chat -m claude-sonnet-4-6 -s "你是一个文言文助手"
```

输入 `/exit` 退出或者快捷键 `Ctrl-C / Ctrl-D` 退出。

## 项目结构

```
src
└── llm_toolkit
    ├── __init__.py
    ├── cli.py
    ├── client.py
    ├── providers
    │   ├── __init__.py
    │   ├── anthropic.py
    │   ├── base.py
    │   ├── deepseek.py
    │   └── glm.py
    ├── streaming.py
    └── types.py
tests
└── test_streaming.py
```

## 开发

```bash
uv run ruff check src/ tests/
uv run mypy src/ tests/
uv run pytest tests/
```

## Roadmap

- [ ] 重试策略(指数退避)
- [ ] Token 计数 + 成本统计
- [ ] 请求缓存
- [ ] 并发批量调用
- [ ] LiteLLM 集成对比

## License

MIT