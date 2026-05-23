"""
LLM Provider Configuration for AI Business Flow.

Mirrors hermes-agent's provider registry (30 providers) with full configuration
options: transport types, auth, base URLs, env vars, and aggregator flags.

Provider IDs (slug):
  openrouter, anthropic, openai-codex, gemini, google-gemini-cli, nous,
  zai, deepseek, xai, nvidia, minimax, minimax-cn, kimi-coding,
  kimi-coding-cn, alibaba, huggingface, xiaomi, arcee, ollama-cloud,
  kilocode, opencode-zen, opencode-go, ai-gateway, bedrock, copilot,
  copilot-acp, qwen-oauth, custom, gmi, stepfun, novita,
  alibaba-coding-plan

Transport → API mode mapping:
  openai_chat       → chat_completions
  anthropic_messages → anthropic_messages
  codex_responses   → codex_responses
  bedrock_converse  → bedrock_converse
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# ─────────────────────────────────────────────────────────────────────────────
# Transport / API Mode
# ─────────────────────────────────────────────────────────────────────────────

class Transport:
    OPENAI_CHAT = "openai_chat"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    CODEX_RESPONSES = "codex_responses"
    BEDROCK_CONVERSE = "bedrock_converse"


TRANSPORT_TO_API_MODE = {
    Transport.OPENAI_CHAT: "chat_completions",
    Transport.ANTHROPIC_MESSAGES: "anthropic_messages",
    Transport.CODEX_RESPONSES: "codex_responses",
    Transport.BEDROCK_CONVERSE: "bedrock_converse",
}


# ─────────────────────────────────────────────────────────────────────────────
# Auth Types
# ─────────────────────────────────────────────────────────────────────────────

AUTH_API_KEY = "api_key"
AUTH_OAUTH_DEVICE_CODE = "oauth_device_code"
AUTH_OAUTH_EXTERNAL = "oauth_external"
AUTH_AWS_SDK = "aws_sdk"


# ─────────────────────────────────────────────────────────────────────────────
# Provider Profile
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProviderProfile:
    """Declarative provider description (mirrors hermes-agent's ProviderProfile)."""

    # Identity
    name: str                          # canonical slug, e.g. "openrouter"
    transport: str = Transport.OPENAI_CHAT
    aliases: tuple = ()

    # Display
    display_name: str = ""
    description: str = ""
    signup_url: str = ""

    # Auth & endpoints
    env_vars: tuple = ()
    base_url: str = ""
    models_url: str = ""
    auth_type: str = AUTH_API_KEY
    supports_health_check: bool = True

    # Model catalog
    fallback_models: tuple = ()
    hostname: str = ""

    # Request-level quirks
    fixed_temperature: Any = None
    default_max_tokens: int | None = None
    default_aux_model: str = ""

    # Extra
    extra: dict = field(default_factory=dict)
    is_aggregator: bool = False  # True = provider routes to multiple sub-providers (OpenRouter, HF, etc.)
    base_url_env_var: str = ""   # Env var name that overrides base_url at runtime


# ─────────────────────────────────────────────────────────────────────────────
# Provider Registry
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS: dict[str, ProviderProfile] = {}


def _p(**kwargs) -> ProviderProfile:
    """Shorthand to build a ProviderProfile and register it."""
    p = ProviderProfile(**kwargs)
    PROVIDERS[p.name] = p
    for alias in p.aliases:
        # Aliases are resolved at lookup time; store reverse mapping
        _ALIASES[alias] = p.name
    return p


_ALIASES: dict[str, str] = {}


def register_provider(profile: ProviderProfile) -> None:
    PROVIDERS[profile.name] = profile
    for alias in profile.aliases:
        _ALIASES[alias] = profile.name


def get_provider(name: str) -> Optional[ProviderProfile]:
    """Look up by name or alias (case-insensitive)."""
    key = name.strip().lower()
    canonical = _ALIASES.get(key, key)
    return PROVIDERS.get(canonical)


def list_providers() -> list[ProviderProfile]:
    seen: set[int] = set()
    result: list[ProviderProfile] = []
    for p in PROVIDERS.values():
        if id(p) not in seen:
            seen.add(id(p))
            result.append(p)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Provider Definitions — mirrors hermes-agent exactly
# ─────────────────────────────────────────────────────────────────────────────

_p(
    name="openrouter",
    transport=Transport.OPENAI_CHAT,
    aliases=("or",),
    display_name="OpenRouter",
    description="OpenRouter — unified API for 200+ models",
    signup_url="https://openrouter.ai/keys",
    env_vars=("OPENROUTER_API_KEY",),
    base_url="https://openrouter.ai/api/v1",
    models_url="https://openrouter.ai/api/v1/models",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
    fallback_models=(
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.4",
        "deepseek/deepseek-chat",
        "google/gemini-3-flash-preview",
        "qwen/qwen3-plus",
    ),
    extra={"supports_reasoning": True},
)

_p(
    name="anthropic",
    transport=Transport.ANTHROPIC_MESSAGES,
    aliases=("claude", "claude-oauth", "claude-code"),
    display_name="Anthropic",
    description="Anthropic (Claude models — API key or Claude Code OAuth)",
    signup_url="https://console.anthropic.com/",
    env_vars=("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"),
    base_url="https://api.anthropic.com",
    auth_type=AUTH_API_KEY,
    default_aux_model="claude-haiku-4-5-20251001",
    extra={"api_mode": "anthropic_messages"},
)

_p(
    name="openai-codex",
    transport=Transport.CODEX_RESPONSES,
    aliases=("codex",),
    display_name="OpenAI Codex",
    description="OpenAI Codex (uses codex_responses transport)",
    signup_url="https://platform.openai.com/",
    env_vars=("OPENAI_API_KEY",),
    base_url="https://chatgpt.com/backend-api/codex",
    auth_type=AUTH_OAUTH_EXTERNAL,
    extra={"api_mode": "codex_responses"},
)

_p(
    name="gemini",
    transport=Transport.OPENAI_CHAT,
    aliases=("google", "google-gemini", "google-ai-studio"),
    display_name="Google AI Studio",
    description="Google AI Studio (Gemini models — native Gemini API)",
    signup_url="https://aistudio.google.com/",
    env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta",
    auth_type=AUTH_API_KEY,
    extra={"supports_reasoning": False},
)

_p(
    name="google-gemini-cli",
    transport=Transport.OPENAI_CHAT,
    aliases=("gemini-cli", "gemini-oauth"),
    display_name="Google Gemini (OAuth)",
    description="Google Gemini via OAuth + Code Assist (free tier supported)",
    signup_url="https://aistudio.google.com/",
    env_vars=(),
    base_url="cloudcode-pa://google",
    auth_type=AUTH_OAUTH_EXTERNAL,
    extra={"auth_type": "oauth_external"},
)

_p(
    name="nous",
    transport=Transport.OPENAI_CHAT,
    auth_type=AUTH_OAUTH_DEVICE_CODE,
    base_url="https://inference-api.nousresearch.com/v1",
    env_vars=(),
    display_name="Nous Portal",
    description="Nous Portal (Nous Research subscription)",
    signup_url="https://nousresearch.com/",
)

_p(
    name="zai",
    transport=Transport.OPENAI_CHAT,
    aliases=("glm", "z-ai", "z.ai", "zhipu"),
    display_name="Z.AI / GLM",
    description="Z.AI / GLM (Zhipu AI direct API)",
    signup_url="https://www.z.ai/",
    env_vars=("GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"),
    base_url="",
    base_url_env_var="GLM_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="deepseek",
    transport=Transport.OPENAI_CHAT,
    aliases=("deep-seek",),
    display_name="DeepSeek",
    description="DeepSeek (DeepSeek-V3, R1, coder — direct API)",
    signup_url="https://platform.deepseek.com/",
    env_vars=("DEEPSEEK_API_KEY",),
    base_url="https://api.deepseek.com/v1",
    base_url_env_var="DEEPSEEK_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="xai",
    transport=Transport.CODEX_RESPONSES,
    aliases=("x-ai", "x.ai", "grok"),
    display_name="xAI",
    description="xAI (Grok models — direct API)",
    signup_url="https://console.x.ai/",
    env_vars=("XAI_API_KEY",),
    base_url="https://api.x.ai/v1",
    base_url_env_var="XAI_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="nvidia",
    transport=Transport.OPENAI_CHAT,
    aliases=("nim", "nvidia-nim", "build-nvidia", "nemotron"),
    display_name="NVIDIA NIM",
    description="NVIDIA NIM (Nemotron models — build.nvidia.com or local NIM)",
    signup_url="https://build.nvidia.com/",
    env_vars=("NVIDIA_API_KEY",),
    base_url="https://integrate.api.nvidia.com/v1",
    base_url_env_var="NVIDIA_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="minimax",
    transport=Transport.ANTHROPIC_MESSAGES,
    display_name="MiniMax (Global)",
    description="MiniMax (global direct API — MiniMax-M2.7 / M2.5)",
    signup_url="https://platform.minimax.io/",
    env_vars=("MINIMAX_API_KEY",),
    base_url="https://api.minimax.io/anthropic",
    base_url_env_var="MINIMAX_BASE_URL",
    auth_type=AUTH_API_KEY,
    fallback_models=("MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"),
)

_p(
    name="minimax-cn",
    transport=Transport.ANTHROPIC_MESSAGES,
    aliases=("minimax-china", "minimax_cn"),
    display_name="MiniMax (China)",
    description="MiniMax China (domestic direct API — MiniMax-M2.7 / M2.5)",
    signup_url="https://platform.minimax.cn/",
    env_vars=("MINIMAX_CN_API_KEY",),
    base_url="https://api.minimaxi.com/anthropic",
    base_url_env_var="MINIMAX_CN_BASE_URL",
    auth_type=AUTH_API_KEY,
    fallback_models=("MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"),
)

_p(
    name="kimi-coding",
    transport=Transport.OPENAI_CHAT,
    aliases=("kimi", "moonshot"),
    display_name="Kimi / Moonshot",
    description="Kimi / Moonshot AI（国际版 api.moonshot.ai）",
    signup_url="https://platform.moonshot.cn/",
    env_vars=("KIMI_API_KEY",),
    base_url="https://api.moonshot.ai/v1",
    base_url_env_var="KIMI_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="kimi-coding-cn",
    transport=Transport.OPENAI_CHAT,
    display_name="Kimi / Moonshot (China)",
    description="Kimi / Moonshot 国内版（api.moonshot.cn）",
    signup_url="https://platform.moonshot.cn/",
    env_vars=("KIMI_API_KEY",),
    base_url="https://api.moonshot.cn/v1",
    base_url_env_var="KIMI_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="alibaba",
    transport=Transport.OPENAI_CHAT,
    aliases=("dashscope", "aliyun", "qwen", "alibaba-cloud"),
    display_name="Alibaba Cloud (DashScope)",
    description="Alibaba Cloud / DashScope (Qwen + multi-provider — 国际版)",
    signup_url="https://dashscope.console.aliyun.com/",
    env_vars=("DASHSCOPE_API_KEY", "ALIBABA_DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    base_url_env_var="DASHSCOPE_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="huggingface",
    transport=Transport.OPENAI_CHAT,
    aliases=("hf", "hugging-face", "huggingface-hub"),
    display_name="Hugging Face",
    description="Hugging Face Inference Providers (20+ open models)",
    signup_url="https://huggingface.co/settings/inference",
    env_vars=("HF_TOKEN",),
    base_url="https://huggingface.co/api/v1",
    base_url_env_var="HF_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="xiaomi",
    transport=Transport.OPENAI_CHAT,
    aliases=("mimo", "xiaomi-mimo"),
    display_name="Xiaomi MiMo",
    description="Xiaomi MiMo (MiMo-V2 models — mimo-v2-pro/omni/flash)",
    signup_url="https://github.com/XiaomiMiMo/MiMo",
    env_vars=("XIAOMI_API_KEY",),
    base_url="https://api.xiaomimimo.com/v1",
    base_url_env_var="XIAOMI_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="arcee",
    transport=Transport.OPENAI_CHAT,
    aliases=("arcee-ai", "arceeai"),
    display_name="Arcee AI",
    description="Arcee AI (Trinity models — direct API)",
    signup_url="https://www.arcee.ai/",
    env_vars=("ARCEEAI_API_KEY",),
    base_url="https://api.arcee.ai/api/v1",
    base_url_env_var="ARCEE_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="ollama-cloud",
    transport=Transport.OPENAI_CHAT,
    aliases=("ollama",),
    display_name="Ollama Cloud",
    description="Ollama Cloud (cloud-hosted open models — ollama.com)",
    signup_url="https://ollama.com/settings",
    env_vars=("OLLAMA_API_KEY",),
    base_url="",
    base_url_env_var="OLLAMA_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="kilocode",
    transport=Transport.OPENAI_CHAT,
    aliases=("kilo", "kilo-code", "kilo-gateway"),
    display_name="Kilo Code",
    description="Kilo Code (Kilo Gateway API)",
    signup_url="https://kilocode.ai/",
    env_vars=("KILOCODE_API_KEY",),
    base_url="",
    base_url_env_var="KILOCODE_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="opencode-zen",
    transport=Transport.OPENAI_CHAT,
    aliases=("opencode", "zen"),
    display_name="OpenCode Zen",
    description="OpenCode Zen (35+ curated models, pay-as-you-go)",
    signup_url="https://opencode.ai/",
    env_vars=("OPENCODE_ZEN_API_KEY",),
    base_url="",
    base_url_env_var="OPENCODE_ZEN_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="opencode-go",
    transport=Transport.OPENAI_CHAT,
    aliases=("go", "opencode-go-sub"),
    display_name="OpenCode Go",
    description="OpenCode Go (open models, $10/month subscription)",
    signup_url="https://opencode.ai/",
    env_vars=("OPENCODE_GO_API_KEY",),
    base_url="",
    base_url_env_var="OPENCODE_GO_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="ai-gateway",
    transport=Transport.OPENAI_CHAT,
    aliases=("vercel", "aigateway", "vercel-ai-gateway"),
    display_name="Vercel AI Gateway",
    description="Vercel AI Gateway (200+ models, pay-per-use)",
    signup_url="https://vercel.com/",
    env_vars=("AI_GATEWAY_API_KEY", "VERCEL_API_KEY"),
    base_url="",
    base_url_env_var="AI_GATEWAY_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="bedrock",
    transport=Transport.BEDROCK_CONVERSE,
    aliases=("aws", "aws-bedrock", "amazon-bedrock", "amazon"),
    display_name="AWS Bedrock",
    description="AWS Bedrock (Claude, Nova, Llama, DeepSeek — IAM or API key)",
    signup_url="https://aws.amazon.com/bedrock/",
    env_vars=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
    base_url="",
    auth_type=AUTH_AWS_SDK,
    extra={"api_mode": "bedrock_converse"},
)

_p(
    name="copilot",
    transport=Transport.OPENAI_CHAT,
    aliases=("github", "github-copilot", "github-models", "github-model"),
    display_name="GitHub Copilot",
    description="GitHub Copilot (uses GITHUB_TOKEN or gh auth token)",
    signup_url="https://github.com/features/copilot",
    env_vars=("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"),
    base_url="",
    auth_type=AUTH_API_KEY,
)

_p(
    name="copilot-acp",
    transport=Transport.CODEX_RESPONSES,
    aliases=("github-copilot-acp", "copilot-acp-agent"),
    display_name="GitHub Copilot ACP",
    description="GitHub Copilot ACP (spawns copilot --acp --stdio)",
    signup_url="https://github.com/features/copilot",
    env_vars=(),
    base_url="acp://copilot",
    base_url_env_var="COPILOT_ACP_BASE_URL",
    auth_type=AUTH_OAUTH_EXTERNAL,
    supports_health_check=False,
    extra={"api_mode": "codex_responses"},
)

_p(
    name="qwen-oauth",
    transport=Transport.OPENAI_CHAT,
    aliases=(),
    display_name="Qwen OAuth (Portal)",
    description="Qwen OAuth (reuses local Qwen CLI login)",
    signup_url="https://portal.qwen.ai/",
    env_vars=(),
    base_url="https://portal.qwen.ai/v1",
    base_url_env_var="HERMES_QWEN_BASE_URL",
    auth_type=AUTH_OAUTH_EXTERNAL,
)

_p(
    name="gmi",
    transport=Transport.OPENAI_CHAT,
    aliases=(),
    display_name="GMI Cloud",
    description="GMI Cloud (multi-model direct API)",
    signup_url="https://www.gmicloud.ai/",
    env_vars=("GMI_API_KEY",),
    base_url="",
    base_url_env_var="GMI_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="stepfun",
    transport=Transport.OPENAI_CHAT,
    aliases=(),
    display_name="Stepfun",
    description="Stepfun (Step series models)",
    signup_url="https://platform.stepfun.com/",
    env_vars=("STEPFUN_API_KEY",),
    base_url="",
    base_url_env_var="STEPFUN_BASE_URL",
    auth_type=AUTH_API_KEY,
)

_p(
    name="novita",
    transport=Transport.OPENAI_CHAT,
    aliases=(),
    display_name="Novita",
    description="Novita AI (Variety of models)",
    signup_url="https://novita.ai/",
    env_vars=("NOVITA_API_KEY",),
    base_url="",
    base_url_env_var="NOVITA_BASE_URL",
    auth_type=AUTH_API_KEY,
    is_aggregator=True,
)

_p(
    name="alibaba-coding-plan",
    transport=Transport.OPENAI_CHAT,
    aliases=(),
    display_name="Alibaba Coding Plan",
    description="Alibaba Cloud Coding Plan (Qwen + multi-provider coding)",
    signup_url="https://dashscope.console.aliyun.com/",
    env_vars=("DASHSCOPE_API_KEY",),
    base_url="",
    base_url_env_var="DASHSCOPE_BASE_URL",
    auth_type=AUTH_API_KEY,
)

# Custom / local server — catch-all for any OpenAI-compatible endpoint
_p(
    name="custom",
    transport=Transport.OPENAI_CHAT,
    aliases=("local", "vllm", "llamacpp", "llama.cpp", "llama-cpp", "lmstudio"),
    display_name="Custom Endpoint",
    description="Custom OpenAI-compatible endpoint (LM Studio, Ollama, vLLM, etc.)",
    signup_url="",
    env_vars=(),
    base_url="",
    auth_type=AUTH_API_KEY,
    supports_health_check=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Alias resolution
# ─────────────────────────────────────────────────────────────────────────────

def normalize_provider(name: str) -> str:
    """Resolve alias → canonical name."""
    key = name.strip().lower()
    return _ALIASES.get(key, key)


def get_label(name: str) -> str:
    """Human-readable display name."""
    p = get_provider(name)
    return p.display_name if p else name


# ─────────────────────────────────────────────────────────────────────────────
# Provider → transport → api_mode
# ─────────────────────────────────────────────────────────────────────────────

def determine_api_mode(provider: str, base_url: str = "") -> str:
    """Resolve provider + optional base_url → api_mode string."""
    p = get_provider(provider)
    if p:
        return TRANSPORT_TO_API_MODE.get(p.transport, "chat_completions")

    # URL heuristics for unknown/custom providers
    if base_url:
        url = base_url.lower()
        if "api.anthropic.com" in url:
            return "anthropic_messages"
        if "bedrock-runtime" in url and "amazonaws.com" in url:
            return "bedrock_converse"
        if "chatgpt.com/backend-api/codex" in url:
            return "codex_responses"

    return "chat_completions"


# ─────────────────────────────────────────────────────────────────────────────
# Environment variable helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_api_key(provider: str) -> Optional[str]:
    """Check all known env vars for a provider's API key."""
    p = get_provider(provider)
    if not p:
        return os.environ.get(provider.upper() + "_API_KEY")

    for env_var in p.env_vars:
        if env_var in os.environ:
            return os.environ[env_var]

    # Also check base_url_env_var
    if p.base_url_env_var and p.base_url_env_var in os.environ:
        return os.environ[p.base_url_env_var]

    return None


def get_base_url(provider: str) -> Optional[str]:
    """Get configured or env-based base URL for provider."""
    p = get_provider(provider)
    if not p:
        return None

    if p.base_url:
        return p.base_url

    if p.base_url_env_var:
        return os.environ.get(p.base_url_env_var)

    return None