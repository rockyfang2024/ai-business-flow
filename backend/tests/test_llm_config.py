# Tests for LLM config system
# Run with: python -m pytest tests/test_llm_config.py -v

import pytest
import os
import sys

# Ensure the backend module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_api_key(monkeypatch):
    """Set a fake API key so we don't hit real APIs without intent."""
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test-minimax-fake-key-for-unit-test")


# ─────────────────────────────────────────────────────────────────────────────
# Test: LLM Config Schema & Schemas
# ─────────────────────────────────────────────────────────────────────────────

def test_llm_config_schema_defaults():
    """LLMConfigSchema has sensible defaults when empty."""
    from app.models.schemas import LLMConfigSchema

    cfg = LLMConfigSchema()
    # The primary model is nested under cfg.model
    assert cfg.model is not None
    # The default model field is "default"
    assert cfg.model.default == "anthropic/claude-sonnet-4.6"  # Pydantic default value
    # The provider field defaults to 'auto'
    assert cfg.model.provider == "auto"


def test_llm_config_test_request_valid():
    """LLMConfigTestRequest accepts required fields."""
    from app.models.schemas import LLMConfigTestRequest

    req = LLMConfigTestRequest(provider="minimax-cn", model="MiniMax-M2.7")
    assert req.provider == "minimax-cn"
    assert req.model == "MiniMax-M2.7"
    assert req.api_key is None
    assert req.base_url is None


def test_llm_config_test_request_with_overrides():
    """LLMConfigTestRequest accepts optional overrides."""
    from app.models.schemas import LLMConfigTestRequest

    req = LLMConfigTestRequest(
        provider="deepseek",
        model="deepseek-chat",
        api_key="sk-my-key",
        base_url="https://api.deepseek.com/v1",
    )
    assert req.api_key == "sk-my-key"
    assert req.base_url == "https://api.deepseek.com/v1"


def test_llm_config_override():
    """LLMConfigOverride fields are all optional."""
    from app.models.schemas import LLMConfigOverride

    override = LLMConfigOverride()
    assert override.provider is None
    assert override.model is None
    assert override.api_key is None

    override = LLMConfigOverride(provider="openai", model="gpt-4o", temperature=0.7)
    assert override.provider == "openai"
    assert override.temperature == 0.7


# ─────────────────────────────────────────────────────────────────────────────
# Test: Provider Registry (llm_config.py)
# ─────────────────────────────────────────────────────────────────────────────

def test_all_providers_have_base_url():
    """Every provider in the registry has a non-empty base_url (except 'custom' which is user-defined)."""
    from app.llm_config import PROVIDERS, get_provider

    missing = []
    for name in PROVIDERS:
        p = get_provider(name)
        if not p.base_url and name != "custom":
            missing.append(name)

    assert not missing, f"Providers missing base_url: {missing}"


def test_all_providers_have_transport():
    """Every provider has a valid transport."""
    from app.llm_config import get_provider

    # Note: 'openai' is not a standalone provider in our registry
    # Use 'openai-codex' or other OpenAI-compatible providers instead
    for name in ["minimax", "minimax-cn", "deepseek", "anthropic", "openrouter", "openai-codex"]:
        p = get_provider(name)
        assert p is not None, f"{name} provider not found"
        assert p.transport is not None, f"{name} has no transport"


def test_minimax_transport_is_anthropic_messages():
    """MiniMax uses ANTHROPIC_MESSAGES transport."""
    from app.llm_config import get_provider

    p = get_provider("minimax")
    assert p.transport == "anthropic_messages"


def test_minimax_cn_base_url():
    """MiniMax-CN uses the correct Chinese endpoint."""
    from app.llm_config import get_provider

    p = get_provider("minimax-cn")
    assert p.base_url == "https://api.minimaxi.com/anthropic"


def test_deepseek_base_url():
    """DeepSeek has correct base_url with /v1."""
    from app.llm_config import get_provider

    p = get_provider("deepseek")
    assert p.base_url == "https://api.deepseek.com/v1"


def test_get_provider_normalization():
    """get_provider handles case normalization."""
    from app.llm_config import get_provider

    p1 = get_provider("MINIMAX")
    p2 = get_provider("minimax")
    assert p1 is not None
    assert p1.name == p2.name


def test_no_duplicate_provider_names():
    """No two providers share the same canonical name."""
    from app.llm_config import PROVIDERS, get_provider
    from app.llm_config import normalize_provider

    names = set()
    dups = []
    for name in PROVIDERS:
        canonical = normalize_provider(name)
        if canonical in names:
            dups.append(name)
        names.add(canonical)

    assert not dups, f"Duplicate provider names: {dups}"


# ─────────────────────────────────────────────────────────────────────────────
# Test: API Endpoints (main.py routes)
# ─────────────────────────────────────────────────────────────────────────────

def test_health_endpoint():
    """GET /health returns ok."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_providers():
    """GET /api/config/llm/providers returns a list."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/config/llm/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 30  # At least 30 providers

    # Check a known provider
    names = [p["id"] for p in data]
    assert "minimax" in names
    assert "deepseek" in names
    assert "anthropic" in names


def test_provider_info_includes_base_url():
    """Each provider info includes base_url field."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/config/llm/providers")
    data = resp.json()

    for p in data:
        assert "base_url" in p, f"{p['id']} missing base_url"
        # 'custom' is intentionally empty (user-defined endpoint)
        if p["id"] != "custom":
            assert p["base_url"], f"{p['id']} has empty base_url"


def test_llm_config_response_structure():
    """GET /api/config/llm returns config + providers."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/config/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "config" in data
    assert "available_providers" in data
    assert len(data["available_providers"]) >= 30


def test_test_endpoint_rejects_missing_body():
    """POST /api/config/llm/test returns 422 when body is missing."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/config/llm/test", content="{}")
    # Missing required fields → 422
    assert resp.status_code == 422


def test_test_endpoint_accepts_valid_body():
    """POST /api/config/llm/test accepts valid provider+model+api_key+base_url."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/config/llm/test", json={
        "provider": "minimax-cn",
        "model": "MiniMax-M2.7",
        "api_key": "sk-cp-test-fake-key",
        "base_url": "https://api.minimaxi.com/anthropic",
    })
    # Will fail auth but should NOT be 422 (body accepted)
    assert resp.status_code != 422, f"Got 422: {resp.text}"
    # 401 = auth failure (invalid key), 502 = provider error — both mean body was valid
    assert resp.status_code in (200, 401, 402, 403, 502), f"Unexpected status {resp.status_code}: {resp.text}"


def test_test_endpoint_deepseek():
    """POST /api/config/llm/test with deepseek provider."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/config/llm/test", json={
        "provider": "deepseek",
        "model": "deepseek-chat",
        "api_key": "sk-fake-deepseek-key",
        "base_url": "https://api.deepseek.com/v1",
    })
    # Same pattern: body valid → not 422
    assert resp.status_code != 422, f"Got 422: {resp.text}"


def test_test_endpoint_openai_compatible():
    """POST /api/config/llm/test with a custom openai-compatible provider."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/config/llm/test", json={
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "sk-fake-openai-key",
        "base_url": "https://api.openai.com/v1",
    })
    assert resp.status_code != 422


# ─────────────────────────────────────────────────────────────────────────────
# Test: LLM Client Factory
# ─────────────────────────────────────────────────────────────────────────────

def test_create_llm_client_minimax():
    """create_llm_client returns AnthropicMessagesClient for minimax."""
    from app.services.llm_client import create_llm_client
    from app.services.llm_client import AnthropicMessagesClient

    client = create_llm_client(
        provider="minimax",
        model="MiniMax-M2.7",
        api_key="fake-key",
        base_url="https://api.minimax.io/anthropic",
    )
    assert isinstance(client, AnthropicMessagesClient)


def test_create_llm_client_deepseek():
    """create_llm_client returns OpenAIChatClient for deepseek."""
    from app.services.llm_client import create_llm_client
    from app.services.llm_client import OpenAIChatClient

    client = create_llm_client(
        provider="deepseek",
        model="deepseek-chat",
        api_key="fake-key",
        base_url="https://api.deepseek.com/v1",
    )
    assert isinstance(client, OpenAIChatClient)


def test_create_llm_client_anthropic():
    """create_llm_client returns AnthropicMessagesClient for anthropic."""
    from app.services.llm_client import create_llm_client
    from app.services.llm_client import AnthropicMessagesClient

    client = create_llm_client(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        api_key="fake-key",
    )
    assert isinstance(client, AnthropicMessagesClient)


def test_create_llm_client_openai():
    """create_llm_client returns OpenAIChatClient for openai."""
    from app.services.llm_client import create_llm_client
    from app.services.llm_client import OpenAIChatClient

    client = create_llm_client(
        provider="openai",
        model="gpt-4o",
        api_key="fake-key",
    )
    assert isinstance(client, OpenAIChatClient)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Config persistence
# ─────────────────────────────────────────────────────────────────────────────

def test_llm_config_load_returns_dict():
    """get_llm_config returns a dict (from YAML or defaults)."""
    from app.config import get_llm_config

    cfg = get_llm_config()
    assert isinstance(cfg, dict)


def test_llm_config_update_returns_updated():
    """update_llm_config returns the updated config dict."""
    from app.config import get_llm_config, update_llm_config

    original = get_llm_config()
    updated = update_llm_config({"default_model": "test-model"})
    assert isinstance(updated, dict)
    assert updated.get("default_model") == "test-model"