"""
Pydantic models for Business Flow Skill Web
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Process（业务流程）
# ─────────────────────────────────────────────────────────────────────────────

class ProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="业务流程名称")
    description: Optional[str] = Field(None, max_length=500, description="业务流程描述")


class ProcessInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    skill_path: str  # 文件系统路径
    has_knowledge: bool = False  # 是否已有抽取出的知识文档


class ProcessListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    updated_at: datetime
    has_knowledge: bool


# ─────────────────────────────────────────────────────────────────────────────
# Document（文档）
# ─────────────────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    path: str


class DocumentItem(BaseModel):
    id: str
    filename: str
    size: int
    uploaded_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# LLM Configuration（LLM 配置 - mirrors hermes-agent）
# ─────────────────────────────────────────────────────────────────────────────

class LLMModelConfig(BaseModel):
    """LLM 模型配置选项"""
    default: str = Field(default="anthropic/claude-sonnet-4.6", description="默认模型 (provider/model)")
    provider: str = Field(default="auto", description="提供商标识 (openrouter|anthropic|gemini|...)")
    base_url: str = Field(default="", description="API 端点 (覆盖 provider 默认)")
    context_length: Optional[int] = Field(default=None, description="上下文长度 (0=自动检测)")
    max_tokens: Optional[int] = Field(default=None, description="最大输出 tokens")


class ProviderTimeoutConfig(BaseModel):
    """Per-provider timeout configuration"""
    request_timeout_seconds: Optional[int] = Field(default=None)
    stale_timeout_seconds: Optional[int] = Field(default=None)
    models: dict[str, dict] = Field(default_factory=dict)  # model → timeout overrides


class ProviderRoutingConfig(BaseModel):
    """OpenRouter provider routing options"""
    sort: Optional[str] = Field(default=None, description="price|throughput|latency[:nitro]")
    only: Optional[list[str]] = Field(default=None, description="Allowed provider slugs")
    ignore: Optional[list[str]] = Field(default=None, description="Ignored provider slugs")
    order: Optional[list[str]] = Field(default=None, description="Provider try order")
    require_parameters: Optional[bool] = Field(default=None)
    data_collection: Optional[str] = Field(default=None, description="allow|deny")


class OpenRouterConfig(BaseModel):
    """OpenRouter-specific settings"""
    response_cache: bool = Field(default=True)
    response_cache_ttl: int = Field(default=300, ge=1, le=86400)


class AgentConfig(BaseModel):
    """Agent behavior configuration"""
    reasoning_effort: str = Field(
        default="medium",
        description="xhigh|high|medium|low|minimal|none"
    )
    max_turns: int = Field(default=60)


class DelegationConfig(BaseModel):
    """Subagent delegation configuration"""
    model: str = Field(default="", description="Subagent model (empty = inherit)")
    provider: str = Field(default="", description="Subagent provider (empty = inherit)")


class AuxiliaryConfig(BaseModel):
    """Auxiliary model configuration (compression, vision, etc.)"""
    provider: str = Field(default="auto")
    model: str = Field(default="")


class DelegationSubagentConfig(BaseModel):
    """Subagent-specific LLM config"""
    model: str = Field(default="")
    provider: str = Field(default="")


class ModelAliasEntry(BaseModel):
    """Model alias definition"""
    model: str
    provider: Optional[str] = None
    base_url: Optional[str] = None


class LLMConfigSchema(BaseModel):
    """完整 LLM 配置结构 — mirrors hermes-agent's config.yaml model section"""
    # Core model config
    model: LLMModelConfig = Field(default_factory=LLMModelConfig)

    # Per-provider timeouts
    providers: dict[str, ProviderTimeoutConfig] = Field(default_factory=dict)

    # OpenRouter routing
    provider_routing: Optional[ProviderRoutingConfig] = None

    # OpenRouter-specific
    openrouter: Optional[OpenRouterConfig] = None

    # Agent behavior
    agent: AgentConfig = Field(default_factory=AgentConfig)

    # Subagent delegation
    delegation: DelegationConfig = Field(default_factory=DelegationConfig)

    # Auxiliary models
    auxiliary: AuxiliaryConfig = Field(default_factory=AuxiliaryConfig)

    # Model aliases
    model_aliases: dict[str, ModelAliasEntry] = Field(default_factory=dict)

    # Custom providers (user-defined endpoints)
    custom_providers: list[dict] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# LLM Config API（读写 LLM 配置）
# ──────────────────────────────────────────────────────────────

class LLMConfigUpdate(BaseModel):
    """Partial update to LLM config"""
    model: Optional[LLMModelConfig] = None
    providers: Optional[dict[str, ProviderTimeoutConfig]] = None
    provider_routing: Optional[ProviderRoutingConfig] = None
    openrouter: Optional[OpenRouterConfig] = None
    agent: Optional[AgentConfig] = None
    delegation: Optional[DelegationConfig] = None
    auxiliary: Optional[AuxiliaryConfig] = None
    model_aliases: Optional[dict[str, ModelAliasEntry]] = None
    custom_providers: Optional[list[dict]] = None


class LLMProviderInfo(BaseModel):
    """Provider info for API response"""
    id: str
    name: str
    description: str
    transport: str
    auth_type: str
    env_vars: list[str]
    base_url: str
    is_aggregator: bool
    supports_health_check: bool
    fallback_models: list[str]


class LLMConfigResponse(BaseModel):
    """Full LLM config + available providers"""
    config: LLMConfigSchema
    available_providers: list[LLMProviderInfo]


# ──────────────────────────────────────────────────────────────
# Extraction（抽取）- Updated to use full LLM config
# ──────────────────────────────────────────────────────────────

class LLMConfigOverride(BaseModel):
    """LLM 参数覆盖（可选）— 用于单次调用的临时配置"""
    provider: Optional[str] = Field(default=None, description="Provider ID (openrouter|anthropic|...)")
    model: Optional[str] = Field(default=None, description="Model ID (anthropic/claude-sonnet-4.6)")
    api_key: Optional[str] = Field(default=None, description="Override API key")
    base_url: Optional[str] = Field(default=None, description="Override base URL")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    reasoning_effort: Optional[str] = Field(default=None, description="xhigh|high|medium|low|minimal|none")


class LLMConfigTestRequest(BaseModel):
    """LLM 连接测试请求"""
    provider: str = Field(..., description="Provider ID (minimax-cn|deepseek|...)")
    model: str = Field(..., description="Model ID (MiniMax-M2.7|...)")
    api_key: Optional[str] = Field(default=None, description="Override API key")
    base_url: Optional[str] = Field(default=None, description="Override base URL")


class ExtractionRequest(BaseModel):
    process_id: str
    document_id: Optional[str] = Field(default=None, description="指定文档 ID；不指定则用全部")
    llm: Optional[LLMConfigOverride] = Field(default=None, description="LLM 配置覆盖")


class ExtractionStatus(BaseModel):
    process_id: str
    status: str  # idle | running | done | error
    progress: Optional[str] = None
    confidence_report: Optional[str] = None
    pending_items: Optional[str] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Query（查询）- Updated to use full LLM config
# ──────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    process_id: str
    question: str = Field(..., min_length=1)
    llm: Optional[LLMConfigOverride] = Field(default=None, description="LLM 配置覆盖")


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Dialogue（对话式梳理）- Updated to use full LLM config
# ──────────────────────────────────────────────────────────────

class DialogueTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class DialogueRequest(BaseModel):
    process_id: str
    message: str
    history: list[DialogueTurn] = Field(default_factory=list)
    llm: Optional[LLMConfigOverride] = Field(default=None, description="LLM 配置覆盖")


class DialogueResponse(BaseModel):
    reply: str
    is_complete: bool = False  # True = AI 已收集完所有必要信息，可以生成 YAML
    extracted_data: Optional[dict] = None  # 当 is_complete=True 时，返回已抽取的数据