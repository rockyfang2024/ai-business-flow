"""
Shared configuration for Business Flow Skill Web backend.
Avoids circular imports between routers and main.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# Project root data directory
BASE_DATA_DIR = Path(__file__).parent.parent.parent / "data"
BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# LLM Configuration
# ─────────────────────────────────────────────────────────────────────────────

LLM_CONFIG_PATH = Path(__file__).parent.parent.parent / "llm_config.yaml"


def _default_llm_config() -> dict:
    """Default LLM configuration matching hermes-agent structure."""
    return {
        "model": {
            "default": "anthropic/claude-sonnet-4.6",
            "provider": "auto",
            "base_url": "",
            # "api_key": ""           # stored in .env, not here
            # "context_length": 0,    # 0 = auto-detect
            # "max_tokens": 8192,
        },
        # Provider-specific timeouts
        "providers": {},
        # OpenRouter-specific routing
        "provider_routing": {},
        # OpenRouter response caching
        "openrouter": {
            "response_cache": True,
            "response_cache_ttl": 300,
        },
        # Reasoning/thinking effort
        "agent": {
            "reasoning_effort": "medium",
        },
        # Subagent delegation
        "delegation": {
            "model": "",
            "provider": "",
        },
        # Auxiliary models (compression, vision, etc.)
        "auxiliary": {
            "provider": "auto",
            "model": "",
        },
        # Model aliases
        "model_aliases": {},
        # Custom providers (user-defined endpoints)
        "custom_providers": [],
    }


def load_llm_config() -> dict:
    """Load LLM config from YAML file, merging with defaults."""
    defaults = _default_llm_config()

    if not LLM_CONFIG_PATH.exists():
        # Auto-create with defaults on first run
        save_llm_config(defaults)
        return defaults

    try:
        with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
    except Exception:
        user_cfg = {}

    # Deep merge: user values override defaults
    def _merge(defaults: dict, user: dict) -> dict:
        result = dict(defaults)
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _merge(result[key], value)
            else:
                result[key] = value
        return result

    return _merge(defaults, user_cfg)


def save_llm_config(cfg: dict) -> None:
    """Save LLM config to YAML file."""
    LLM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)


# Load once at startup
LLM_CONFIG = load_llm_config()


def get_llm_config() -> dict:
    """Get current LLM config (already loaded at import time)."""
    return LLM_CONFIG


def update_llm_config(updates: dict) -> dict:
    """Apply partial updates and save."""
    global LLM_CONFIG
    # Deep merge
    def _merge(base: dict, updates: dict) -> dict:
        result = dict(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _merge(result[key], value)
            else:
                result[key] = value
        return result
    LLM_CONFIG = _merge(LLM_CONFIG, updates)
    save_llm_config(LLM_CONFIG)
    return LLM_CONFIG


# ─────────────────────────────────────────────────────────────────────────────
# Environment variable resolution helpers
# ─────────────────────────────────────────────────────────────────────────────

def resolve_api_key(provider: str) -> str | None:
    """Resolve API key for a provider: config → env var → None."""
    # Config-level key (llm_config.yaml or .env)
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai-codex": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "google-gemini-cli": "GOOGLE_API_KEY",
        "nous": "NOUS_API_KEY",
        "zai": "ZAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "xai": "XAI_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "minimax-cn": "MINIMAX_CN_API_KEY",
        "kimi-coding": "KIMI_API_KEY",
        "kimi-coding-cn": "KIMI_API_KEY",
        "alibaba": "DASHSCOPE_API_KEY",
        "huggingface": "HF_TOKEN",
        "xiaomi": "XIAOMI_API_KEY",
        "arcee": "ARCEEAI_API_KEY",
        "ollama-cloud": "OLLAMA_API_KEY",
        "kilocode": "KILOCODE_API_KEY",
        "opencode-zen": "OPENCODE_ZEN_API_KEY",
        "opencode-go": "OPENCODE_GO_API_KEY",
        "ai-gateway": "AI_GATEWAY_API_KEY",
        "bedrock": "AWS_ACCESS_KEY_ID",
        "copilot": "GITHUB_TOKEN",
        "copilot-acp": "COPILOT_GITHUB_TOKEN",
        "qwen-oauth": "QWEN_API_KEY",
        "gmi": "GMI_API_KEY",
        "stepfun": "STEPFUN_API_KEY",
        "novita": "NOVITA_API_KEY",
        "alibaba-coding-plan": "DASHSCOPE_API_KEY",
        "custom": "OPENAI_API_KEY",
    }
    # Check env first
    if provider in env_map:
        key = env_map[provider]
        if key in os.environ:
            return os.environ[key]
    # Check generic fallback
    if f"{provider.upper()}_API_KEY" in os.environ:
        return os.environ[f"{provider.upper()}_API_KEY"]
    # Check openai key as fallback for aggregators
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    return None


def resolve_base_url(provider: str, explicit: str = "") -> str | None:
    """Resolve base URL: explicit override → config → provider default → env var."""
    from .llm_config import get_provider
    if explicit:
        return explicit
    p = get_provider(provider)
    if not p:
        return None
    if p.base_url:
        return p.base_url
    if p.base_url_env_var and p.base_url_env_var in os.environ:
        return os.environ[p.base_url_env_var]
    return None