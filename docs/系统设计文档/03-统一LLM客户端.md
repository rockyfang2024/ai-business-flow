# 03 · 统一 LLM 客户端

> 核心实现：`backend/app/services/llm_client.py`

## 一、设计背景

不同的 LLM Provider 使用不同的 API 协议：

- **OpenAI 系**（OpenRouter、DeepSeek、Gemini...）用 `chat.completions` 接口
- **Anthropic**（含 MiniMax）用 `messages.create` 原生接口
- **AWS Bedrock** 用 `converse` API
- **OpenAI Codex / xAI** 用 `responses` 接口

如果每个 Router 各自裸调 SDK，就会出现大量重复代码（认证逻辑、超时处理、重试逻辑散落各处）。

**统一 LLM Client 的目标**：让所有后端调用只依赖 `chat_complete()` 一个函数，底层四种 transport 对调用方透明。

## 二、架构图

```
┌─────────────────────────────────────────────────────────────────┐
│  routers/extraction.py         routers/query.py                 │
│         │                            │                          │
└─────────┼────────────────────────────┼──────────────────────────┘
          │                            │
          ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    chat_complete()                               │
│              （高阶 convenience wrapper）                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   create_llm_client()                            │
│                    （工厂函数）                                   │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
          ┌───────────┼───────────┐           │
          ▼           ▼           ▼           ▼
┌────────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐
│OpenAIChat  │ │Anthropic  │ │CodexResp.  │ │BedrockConverse│
│Client      │ │Messages   │ │Client      │ │Client         │
│            │ │Client     │ │            │ │               │
└────────────┘ └───────────┘ └────────────┘ └───────────────┘
```

## 三、四种 Transport 客户端

### 3.1 OpenAIChatClient — chat_completions

**适用 Provider**：OpenRouter、DeepSeek、Gemini、HuggingFace、Ollama、Custom 等绝大多数 Provider

**调用方式**：
```python
client = OpenAIChatClient(
    provider="openrouter",
    model="anthropic/claude-sonnet-4.6",
    api_key="sk-or-v2-...",
    base_url="https://openrouter.ai/api/v1",
)
response = client.chat(messages=[...], temperature=0.3, max_tokens=4096)
```

**关键实现细节**：
- 底层使用 `openai` Python SDK 的 `OpenAI` 客户端
- `extra_body` 字段支持往请求体注入额外参数（如 `reasoning` 配置）
- `extra_headers` 支持自定义 HTTP 头

### 3.2 AnthropicMessagesClient — anthropic_messages

**适用 Provider**：Anthropic（直接）、MiniMax（含中国版）

**调用方式**：
```python
client = AnthropicMessagesClient(
    provider="anthropic",
    model="claude-opus-4-6",
    api_key="sk-ant-...",
)
response = client.chat(messages=[...], temperature=0.3, max_tokens=4096)
```

**消息格式转换**（OpenAI → Anthropic）：
```python
# OpenAI 格式
{"role": "system", "content": "..."}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "..."}

# Anthropic 格式（system role 不存在，合并到首条 user 消息）
{"role": "user", "content": "system prompt + first message"}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "..."}
```

**reasoning/thinking 配置**：注入 `body["thinking"] = {...}` 字段

### 3.3 BedrockConverseClient — bedrock_converse

**适用 Provider**：AWS Bedrock（含 Claude、 Nova、 Llama、 DeepSeek 模型）

**认证方式**：使用 `boto3` Session + AWS IAM 凭证（Access Key / Secret Key / Region）

```python
client = BedrockConverseClient(
    provider="bedrock",
    model="us.anthropic.claude-sonnet-4-6",
    aws_access_key="AKIA...",
    aws_secret_key="...",
    aws_region="us-east-1",
)
response = client.chat(messages=[...])
```

**消息格式转换**：
```python
# OpenAI格式 → Bedrock格式
{"role": "user", "content": "..."}
→ {"role": "user", "content": [{"text": "..."}]}
```

### 3.4 CodexResponsesClient — codex_responses

**适用 Provider**：OpenAI Codex、xAI（Grok）、GitHub Copilot ACP

**调用方式**：
```python
client = CodexResponsesClient(
    provider="codex",
    model="gpt-5.4",
)
response = client.chat(messages=[...])
```

**特殊处理**：Responses API 返回格式与 Chat Completions 不同，使用 `response.output` 字段

## 四、工厂函数：create_llm_client()

核心路由逻辑（`llm_client.py` 第 355-450 行）：

```python
def create_llm_client(provider, model, api_key, base_url, reasoning_effort, **kwargs):
    # 1. 别名解析
    canonical = normalize_provider(provider)

    # 2. 从 provider + base_url 推断 API mode
    api_mode = determine_api_mode(canonical, base_url or "")

    # 3. 处理 reasoning 配置
    extra_body = {}
    if reasoning_effort:
        if api_mode == "chat_completions":
            extra_body["reasoning"] = {"enabled": True, "effort": reasoning_effort}

    # 4. 按 api_mode 分发
    if api_mode == "anthropic_messages":
        return AnthropicMessagesClient(provider=canonical, model=model, ...)
    elif api_mode == "codex_responses":
        return CodexResponsesClient(provider=canonical, model=model, ...)
    elif api_mode == "bedrock_converse":
        return BedrockConverseClient(provider=canonical, model=model, ...)
    else:
        return OpenAIChatClient(provider=canonical, model=model, ...)
```

## 五、凭证解析优先级

`create_llm_client()` 内部调用 `resolve_api_key()` / `resolve_base_url()`，优先级顺序：

```
1. 显式参数 api_key / base_url        （调用方直接传入）
         ↓
2. LLM Config YAML 文件               （SettingsDialog 写入）
         ↓
3. ProviderProfile 默认值              （llm_config.py 硬编码）
         ↓
4. 环境变量                           （os.environ）
```

## 六、高阶封装：chat_complete()

调用方不需要知道用哪种 transport，直接调用：

```python
from backend.app.services.llm_client import chat_complete

response = chat_complete(
    provider="openrouter",
    model="anthropic/claude-sonnet-4.6",
    messages=[{"role": "user", "content": "解释什么是业务流程"}],
    temperature=0.3,
    max_tokens=4096,
)
print(response.content)  # ← LLM 返回的文本
```

**异常处理**：所有 transport 的异常统一包装为 `LLMCallFailed(provider, model, message, status_code)`

## 七、关键类和函数一览

| 名称 | 类型 | 说明 |
|------|------|------|
| `LLMResponse` | 类 | 统一响应格式：`.content`（文本）、`.raw`（原生响应）、`.provider`、`.model` |
| `LLMCallFailed` | 异常类 | 所有 LLM 调用异常的包装，包含 provider/model/status_code |
| `OpenAIChatClient` | 类 | OpenAI 兼容接口（chat.completions）|
| `AnthropicMessagesClient` | 类 | Anthropic 原生接口（messages.create）|
| `BedrockConverseClient` | 类 | AWS Bedrock Converse API |
| `CodexResponsesClient` | 类 | OpenAI Responses API（Codex、xAI 等）|
| `create_llm_client()` | 工厂函数 | 根据 provider + api_mode 路由到对应 Client |
| `chat_complete()` | 高阶函数 | 一行调用，封装工厂函数 + agent reasoning 配置 |
| `resolve_model_from_alias()` | 工具函数 | 模型别名解析（如 `"opus"` → `("anthropic", "claude-opus-4-6")`）|
| `get_default_model()` | 工具函数 | 从全局配置读取默认 provider/model |

## 八、使用示例

### Router 中的典型用法（extraction.py）

```python
from ..services.llm_client import chat_complete, LLMCallFailed

def extract_knowledge(process_id: str, ...):
    try:
        response = chat_complete(
            provider=cfg["provider"],
            model=cfg["model"],
            messages=[...],
            temperature=0.3,
            max_tokens=4096,
        )
        return response.content
    except LLMCallFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

### Router 中的典型用法（query.py — 对话）

```python
from ..services.llm_client import chat_complete

def dialogue(process_id: str, user_message: str, history: list):
    messages = history + [{"role": "user", "content": user_message}]
    response = chat_complete(
        provider=cfg["provider"],
        model=cfg["model"],
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
    )
    return response.content
```