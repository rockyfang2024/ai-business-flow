"""
Business Flow Skill Web - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .routers import processes, extraction, query
from .config import BASE_DATA_DIR, get_llm_config, update_llm_config, resolve_api_key
from .llm_config import PROVIDERS, get_provider, list_providers, normalize_provider
from .models.schemas import LLMConfigSchema, LLMConfigUpdate, LLMProviderInfo, LLMConfigResponse

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Business Flow Skill API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# 注册路由
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(processes.router, prefix="/api/processes", tags=["processes"])
app.include_router(extraction.router, prefix="/api/extraction", tags=["extraction"])
app.include_router(query.router, prefix="/api/query", tags=["query"])


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# LLM Config API
# ─────────────────────────────────────────────────────────────────────────────

def _provider_info(name: str) -> LLMProviderInfo:
    """Build LLMProviderInfo from a ProviderProfile name."""
    p = get_provider(name)
    if not p:
        # Build minimal entry for unregistered providers
        return LLMProviderInfo(
            id=name,
            name=name,
            description="",
            transport="openai_chat",
            auth_type="api_key",
            env_vars=[],
            base_url="",
            is_aggregator=False,
            supports_health_check=True,
            fallback_models=[],
        )
    return LLMProviderInfo(
        id=p.name,
        name=p.display_name or p.name,
        description=p.description,
        transport=p.transport,
        auth_type=p.auth_type,
        env_vars=list(p.env_vars),
        base_url=p.base_url,
        is_aggregator=bool(p.extra.get("is_aggregator")),
        supports_health_check=p.supports_health_check,
        fallback_models=list(p.fallback_models),
    )


@app.get("/api/config/llm", response_model=LLMConfigResponse)
def get_llm_config_handler():
    """
    获取完整 LLM 配置 + 所有可用 Provider 列表。

    返回结构：
      - config: 当前生效的 LLM 配置（来自 llm_config.yaml）
      - available_providers: 所有 30 个支持的 Provider 元信息
    """
    cfg = get_llm_config()

    # Convert raw dict → Pydantic model (fills defaults)
    try:
        config_model = LLMConfigSchema(**cfg)
    except Exception:
        # If there are unknown fields, still return the raw config
        config_model = LLMConfigSchema()

    providers = [_provider_info(name) for name in PROVIDERS]

    return LLMConfigResponse(config=config_model, available_providers=providers)


@app.patch("/api/config/llm")
def update_llm_config_handler(body: LLMConfigUpdate):
    """
    部分更新 LLM 配置。

    支持更新字段（均为可选）：
      - model (default, provider, base_url, context_length, max_tokens)
      - providers (per-provider timeout overrides)
      - provider_routing (OpenRouter 路由策略)
      - openrouter (response cache settings)
      - agent (reasoning_effort, max_turns)
      - delegation (subagent model/provider)
      - auxiliary (auxiliary model config)
      - model_aliases (模型别名映射)
      - custom_providers (用户自定义端点)
    """
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    updated = update_llm_config(updates)
    return {"status": "ok", "config": updated}


@app.get("/api/config/llm/providers", response_model=list[LLMProviderInfo])
def list_llm_providers():
    """列出所有 30 个支持的 LLM Provider。"""
    return [_provider_info(name) for name in PROVIDERS]


@app.get("/api/config/llm/providers/{provider_name}")
def get_llm_provider(provider_name: str):
    """获取指定 Provider 的详细信息。"""
    canonical = normalize_provider(provider_name)
    p = get_provider(canonical)
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
    return _provider_info(p.name)


@app.post("/api/config/llm/test")
def test_llm_connection(provider: str, model: str, api_key: str | None = None, base_url: str | None = None):
    """
    测试 LLM 连接是否可用。

    依次尝试：
      1. 显式传入的 api_key / base_url
      2. llm_config.yaml 中的配置
      3. 环境变量
    """
    from .services.llm_client import create_llm_client, LLMCallFailed

    # Resolve credentials
    resolved_api_key = api_key or resolve_api_key(provider)
    resolved_base_url = base_url

    try:
        client = create_llm_client(
            provider=provider,
            model=model,
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )
        # Simple test call
        response = client.chat(
            messages=[{"role": "user", "content": "Reply with exactly one word: ok"}],
            temperature=0.1,
            max_tokens=10,
        )
        return {"status": "ok", "response": response.content.strip()}
    except LLMCallFailed as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed [{exc.provider}]: {exc.message}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/config/llm/env-check")
def check_env_vars():
    """
    检查当前环境中的 LLM 相关环境变量。

    返回每个 Provider 的 API key 状态（是否已设置）。
    """
    from .llm_config import PROVIDERS

    results = {}
    for name, p in PROVIDERS.items():
        found = []
        missing = []
        for env_var in p.env_vars:
            if env_var in __import__("os").environ:
                found.append(env_var)
            else:
                missing.append(env_var)
        results[name] = {"found": found, "missing": missing}

    return {"providers": results}