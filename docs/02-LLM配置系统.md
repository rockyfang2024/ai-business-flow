# 02 · LLM 配置系统

> 参考实现：[hermes-agent](https://github.com/NousResearch/hermes-agent) LLM Provider Registry

## 一、设计目标

LLM 配置系统要实现：**用户在前端界面直接选择 Provider、填入 API Key，无需环境变量即可运行**。

核心原则：
- **零代码暴露 credentials** — API Key 只存在于 YAML 配置或环境变量
- **镜像 hermes-agent** — 32 个 Provider 的配置结构与 hermes-agent 完全一致
- **运行时覆盖** — YAML 配置可被环境变量覆盖（API Key / Base URL）

## 二、配置三层优先级

```
┌─────────────────────────────────────────────┐
│  第1层：用户界面配置（SettingsDialog）      │
│  → 写入 llm_config.yaml                    │
├─────────────────────────────────────────────┤
│  第2层：环境变量覆盖                        │
│  → API_KEY / BASE_URL 环境变量             │
├─────────────────────────────────────────────┤
│  第3层：代码默认值（llm_config.py）          │
│  → ProviderProfile 的 hardcoded 值         │
└─────────────────────────────────────────────┘
```

**resolve_api_key(provider)** 的实际调用顺序：
```python
# 优先级：YAML配置 > 环境变量 > ProviderProfile默认值
config_yaml.get("api_key")  # 第1层
↓ (若无)
os.environ[env_var]        # 第2层
↓ (若无)
None                       # 第3层兜底
```

## 三、Provider 注册表

### 3.1 支持的 32 个 Provider

| 类别 | Provider | Transport | Auth 类型 |
|------|----------|-----------|-----------|
| **聚合类** | `openrouter` | openai_chat | API Key |
| | `huggingface` | openai_chat | API Key |
| | `kilocode` | openai_chat | API Key |
| | `opencode-zen` | openai_chat | API Key |
| | `opencode-go` | openai_chat | API Key |
| | `ai-gateway` | openai_chat | API Key |
| | `gmi` | openai_chat | API Key |
| | `novita` | openai_chat | API Key |
| **Anthropic/AWS** | `anthropic` | anthropic_messages | API Key |
| | `bedrock` | bedrock_converse | AWS SDK |
| | `copilot` | openai_chat | API Key |
| | `copilot-acp` | codex_responses | OAuth External |
| **Google** | `gemini` | openai_chat | API Key |
| | `google-gemini-cli` | openai_chat | OAuth External |
| **中国大模型** | `deepseek` | openai_chat | API Key |
| | `xai` | codex_responses | API Key |
| | `minimax` | anthropic_messages | API Key |
| | `minimax-cn` | anthropic_messages | API Key |
| | `kimi-coding` | openai_chat | API Key |
| | `kimi-coding-cn` | openai_chat | API Key |
| | `alibaba` | openai_chat | API Key |
| | `alibaba-coding-plan` | openai_chat | API Key |
| | `xiaomi` | openai_chat | API Key |
| | `stepfun` | openai_chat | API Key |
| **开源/本地** | `ollama-cloud` | openai_chat | API Key |
| | `custom` | openai_chat | API Key |
| **其他** | `nvidia` | openai_chat | API Key |
| | `nous` | openai_chat | OAuth Device Code |
| | `zai` | openai_chat | API Key |
| | `arcee` | openai_chat | API Key |
| | `qwen-oauth` | openai_chat | OAuth External |

### 3.2 数据结构：ProviderProfile

```python
@dataclass
class ProviderProfile:
    # 身份
    name: str                    # 唯一标识符，如 "openrouter"
    transport: str                # 四种 transport 之一
    aliases: tuple = ()           # 别名列表，用于快速查找

    # 显示信息
    display_name: str             # 展示名称，如 "OpenRouter"
    description: str              # 描述文本
    signup_url: str               # 注册链接

    # 认证与端点
    env_vars: tuple               # 对应的环境变量名列表
    base_url: str                 # 默认 base URL
    models_url: str               # 模型列表查询 URL
    auth_type: str                # AUTH_API_KEY / AUTH_OAUTH_*

    # 模型目录
    fallback_models: tuple        # 兜底模型列表
    hostname: str                 # 主机名（用于健康检查）

    # 请求级配置
    fixed_temperature: Any = None # 固定 temperature
    default_max_tokens: int | None = None
    default_aux_model: str = ""

    # 额外元数据
    extra: dict                   # 扩展字段（如 supports_reasoning）
    is_aggregator: bool = False   # 是否为聚合类 Provider
    base_url_env_var: str = ""    # 可覆盖 base_url 的环境变量名
```

### 3.3 别名机制

每个 Provider 可配置多个别名，**查找时自动解析为规范名**：

```python
# aliases 示例
"anthropic"   → aliases=("claude", "claude-oauth", "claude-code")
"deepseek"    → aliases=("deep-seek",)
"zai"         → aliases=("glm", "z-ai", "z.ai", "zhipu")

# 解析过程
normalize_provider("claude")  # → "anthropic"
normalize_provider("deep-seek") # → "deepseek"
```

### 3.4 环境变量自动发现

每个 Provider 声明自己需要的环境变量列表，运行时自动从 `os.environ` 读取：

```python
# 示例：deepseek provider 的 env_vars
env_vars=("DEEPSEEK_API_KEY",)

# 示例：anthropic provider 支持多个 env var
env_vars=("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")

# get_api_key() 会按顺序检查第一个命中的环境变量
```

## 四、Transport 与 API Mode 映射

Transport 决定使用哪种 HTTP 协议与 LLM 提供商通信：

```
Transport               API Mode             说明
─────────────────────────────────────────────────────────────
openai_chat        →   chat_completions    OpenAI 兼容接口（最常见）
anthropic_messages →   anthropic_messages  Anthropic 原生接口
codex_responses   →   codex_responses     OpenAI Codex 接口
bedrock_converse   →   bedrock_converse    AWS Bedrock Converse API
```

## 五、YAML 配置文件结构

`llm_config.yaml` 文件格式（由 SettingsDialog 写入）：

```yaml
# 当前选中的 provider
provider: openrouter

# provider 级别配置
api_key: "sk-or-v2-..."      # 可选，未填则用环境变量
base_url: ""                 # 可选，填了则覆盖默认值
model: "anthropic/claude-sonnet-4.6"
temperature: 0.3
max_tokens: 4096

# provider 覆盖配置（针对特定 provider 的 env var 名）
env_var_overrides:
  OPENROUTER_API_KEY: "sk-or-v2-..."
```

## 六、关键函数

| 函数 | 文件 | 作用 |
|------|------|------|
| `get_provider(name)` | `llm_config.py` | 按名称或别名查找 ProviderProfile |
| `normalize_provider(name)` | `llm_config.py` | 别名解析为规范名 |
| `determine_api_mode(provider, base_url)` | `llm_config.py` | 从 provider + base_url 推断 API mode |
| `get_api_key(provider)` | `llm_config.py` | 获取 API Key（优先级：env var > YAML） |
| `get_base_url(provider)` | `llm_config.py` | 获取 Base URL（优先级：env var > 默认） |
| `load_llm_config()` | `config.py` | 从 YAML 文件加载配置 |
| `save_llm_config(cfg)` | `config.py` | 将配置写入 YAML 文件 |
| `resolve_api_key(provider)` | `config.py` | 三层优先级解析 API Key |
| `resolve_base_url(provider, default)` | `config.py` | 三层优先级解析 Base URL |

## 七、与 hermes-agent 的差异

本实现镜像了 hermes-agent 的核心设计思路，但有以下差异：

| 差异点 | hermes-agent | ai-business-flow |
|--------|-------------|-------------------|
| 配置存储 | 环境变量为主 | YAML 文件为主（界面可改） |
| 前端配置 | 无 | SettingsDialog 完整 UI |
| Provider 数量 | 30 个 | 32 个（新增 minimax-cn, kimi-coding-cn） |
| Transport 数量 | 4 种 | 4 种（一致） |
| 自定义 Provider | 不支持 | `custom` provider 支持任意 OpenAI 兼容端点 |