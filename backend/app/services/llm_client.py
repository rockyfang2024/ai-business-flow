"""
Unified LLM Client — multi-transport, multi-provider LLM calls.

Handles:
  - chat_completions (OpenAI-compatible)
  - anthropic_messages (Anthropic native)
  - codex_responses (OpenAI Codex)
  - bedrock_converse (AWS Bedrock)

Mirrors hermes-agent's transport layer and provider profile hooks.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import boto3
from botocore.config import Config as BotoConfig

from ..llm_config import (
    PROVIDERS,
    get_provider,
    normalize_provider,
    determine_api_mode,
    get_api_key,
    get_base_url,
    Transport,
    TRANSPORT_TO_API_MODE,
)
from ..config import get_llm_config, resolve_api_key, resolve_base_url

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# API Mode → transport class mapping
# ─────────────────────────────────────────────────────────────────────────────

class LLMCallFailed(Exception):
    """Raised when LLM call fails after retries."""
    def __init__(self, provider: str, model: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.model = model
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{provider}/{model}] {message}")


class LLMResponse:
    """Normalized LLM response — always has .content."""
    def __init__(self, content: str, raw: Any = None, provider: str = "", model: str = ""):
        self.content = content
        self.raw = raw
        self.provider = provider
        self.model = model


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible (chat_completions) — most providers
# ─────────────────────────────────────────────────────────────────────────────

class OpenAIChatClient:
    """OpenAI-compatible chat completions client."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        extra_headers: dict | None = None,
        extra_body: dict | None = None,
        timeout: float = 120.0,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or resolve_api_key(provider) or ""
        self.base_url = base_url or resolve_base_url(provider, "") or ""
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}
        self.timeout = timeout

        # Lazy-load openai to avoid import overhead when not needed
        from openai import OpenAI as _OpenAI
        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        if self.extra_headers:
            kwargs["default_headers"] = self.extra_headers
        self._client = _OpenAI(**kwargs)

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_config: dict | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Call chat completions API."""
        extra = dict(self.extra_body)
        if reasoning_config:
            extra["reasoning"] = reasoning_config

        chat_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            chat_kwargs["temperature"] = temperature
        if max_tokens is not None:
            chat_kwargs["max_tokens"] = max_tokens
        if extra:
            chat_kwargs["extra_body"] = extra

        try:
            response = self._client.chat.completions.create(**chat_kwargs)
            content = response.choices[0].message.content or ""
            return LLMResponse(content=content, raw=response, provider=self.provider, model=self.model)
        except Exception as exc:
            raise LLMCallFailed(self.provider, self.model, str(exc)) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic Messages API
# ─────────────────────────────────────────────────────────────────────────────

class AnthropicMessagesClient:
    """Anthropic Messages API client (Claude direct)."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or resolve_api_key("anthropic") or ""

        # Build base URL
        self.base_url = base_url or "https://api.anthropic.com"
        self.timeout = timeout

        try:
            from anthropic import Anthropic as _Anthropic
            kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
            if self.base_url and self.base_url != "https://api.anthropic.com":
                kwargs["base_url"] = self.base_url
            self._client = _Anthropic(**kwargs)
        except ImportError:
            logger.warning("Anthropic SDK not installed. Install with: pip install anthropic")
            raise

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_config: dict | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Call Anthropic Messages API."""
        # Build body
        body: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        # Handle reasoning/thinking config
        if reasoning_config:
            body["thinking"] = reasoning_config

        try:
            response = self._client.messages.create(**body)
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
            return LLMResponse(content=content, raw=response, provider=self.provider, model=self.model)
        except Exception as exc:
            raise LLMCallFailed(self.provider, self.model, str(exc)) from exc

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-format messages to Anthropic format."""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                role = "user"  # Anthropic doesn't have system role
            result.append({"role": role, "content": msg.get("content", "")})
        return result


# ─────────────────────────────────────────────────────────────────────────────
# AWS Bedrock Converse API
# ─────────────────────────────────────────────────────────────────────────────

class BedrockConverseClient:
    """AWS Bedrock Converse API client."""

    def __init__(
        self,
        provider: str,
        model: str,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        aws_region: str | None = None,
        timeout: float = 120.0,
    ):
        self.provider = provider
        self.model = model

        # Resolve AWS credentials
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        self.aws_region = aws_region or os.environ.get("AWS_REGION", "us-east-1")

        # Build boto3 client
        boto_config = BotoConfig(
            connect_timeout=self.timeout,
            read_timeout=self.timeout,
            retries={"max_attempts": 3, "mode": "standard"},
        )
        self._client = boto3.session.Session(
            aws_access_key_id=self.aws_access_key or None,
            aws_secret_access_key=self.aws_secret_key or None,
            region_name=self.aws_region,
        ).client("bedrock-runtime", config=boto_config)

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Call Bedrock Converse API."""
        # Convert messages to Bedrock format
        bedrock_messages = [self._to_bedrock_message(m) for m in messages]

        inference_params: dict[str, Any] = {}
        if temperature is not None:
            inference_params["temperature"] = temperature
        if max_tokens is not None:
            inference_params["maxTokens"] = max_tokens

        body = {
            "modelId": self.model,
            "messages": bedrock_messages,
            "inferenceConfig": inference_params,
        }

        try:
            response = self._client.converse(modelId=self.model, messages=bedrock_messages, inferenceConfig=inference_params)
            content = ""
            for block in response["output"]["message"]["content"]:
                if "text" in block:
                    content += block["text"]
            return LLMResponse(content=content, raw=response, provider=self.provider, model=self.model)
        except Exception as exc:
            raise LLMCallFailed(self.provider, self.model, str(exc)) from exc

    def _to_bedrock_message(self, msg: dict) -> dict:
        role = msg.get("role", "user")
        if role not in ("user", "assistant"):
            role = "user"
        content = msg.get("content", "")
        if isinstance(content, str):
            content = [{"text": content}]
        elif isinstance(content, list):
            content = [{"text": c.get("text", "")} for c in content if isinstance(c, dict)]
        return {"role": role, "content": content}


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Codex Responses API
# ─────────────────────────────────────────────────────────────────────────────

class CodexResponsesClient:
    """OpenAI Codex Responses API client."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or resolve_api_key("openai-codex") or ""
        self.base_url = base_url or "https://chatgpt.com/backend-api/codex"
        self.timeout = timeout

        from openai import OpenAI as _OpenAI
        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = _OpenAI(**kwargs)

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Call Codex Responses API."""
        chat_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            chat_kwargs["temperature"] = temperature
        if max_tokens is not None:
            chat_kwargs["max_tokens"] = max_tokens

        try:
            response = self._client.responses.create(**chat_kwargs)
            # Responses API returns different format
            content = ""
            if hasattr(response, "output") and response.output:
                for item in response.output:
                    if hasattr(item, "content") and item.content:
                        for block in item.content:
                            if hasattr(block, "text"):
                                content += block.text
                    elif hasattr(item, "text"):
                        content += item.text
            elif hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content or ""
            elif hasattr(response, "body"):
                # Raw response object
                content = str(response)
            return LLMResponse(content=content, raw=response, provider=self.provider, model=self.model)
        except Exception as exc:
            raise LLMCallFailed(self.provider, self.model, str(exc)) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Factory — build the right client from (provider, model, overrides)
# ─────────────────────────────────────────────────────────────────────────────

def create_llm_client(
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    reasoning_effort: str | None = None,
    **kwargs,
) -> (
    OpenAIChatClient
    | AnthropicMessagesClient
    | BedrockConverseClient
    | CodexResponsesClient
):
    """
    Factory: create the right LLM client based on provider + model + overrides.

    Resolution order for credentials & URL:
      1. Explicit api_key / base_url overrides (from LLMConfigOverride)
      2. LLM config (llm_config.yaml)
      3. Provider default (from llm_config.py PROVIDERS)
      4. Environment variables

    Args:
        provider: Provider ID (e.g. "openrouter", "anthropic", "gemini")
        model: Model ID (e.g. "anthropic/claude-sonnet-4.6", "gpt-4o")
        api_key: Override API key
        base_url: Override base URL
        reasoning_effort: thinking/reasoning effort (xhigh|high|medium|low|minimal|none)
        **kwargs: Extra client options
    """
    # Normalize provider
    canonical = normalize_provider(provider)
    api_mode = determine_api_mode(canonical, base_url or "")

    # Build extra_headers / extra_body from provider profile hooks
    p = get_provider(canonical)
    extra_body = {}
    extra_headers = {}

    if p and p.extra:
        extra_body.update(p.extra)

    # Handle reasoning config
    reasoning_config = None
    if reasoning_effort and reasoning_effort != "none":
        reasoning_config = {"enabled": True, "effort": reasoning_effort}
        if p and p.transport == Transport.OPENAI_CHAT:
            extra_body["reasoning"] = reasoning_config

    # Route by API mode
    if api_mode == "anthropic_messages":
        # Some providers (minimax, etc.) use anthropic_messages transport
        if canonical in ("minimax", "minimax-cn"):
            return AnthropicMessagesClient(
                provider=canonical,
                model=model,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )
        # Default to Anthropic native
        return AnthropicMessagesClient(
            provider=canonical,
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    elif api_mode == "codex_responses":
        return CodexResponsesClient(
            provider=canonical,
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    elif api_mode == "bedrock_converse":
        return BedrockConverseClient(
            provider=canonical,
            model=model,
            aws_access_key=api_key,  # reuse api_key param for AWS key
            **kwargs,
        )

    else:  # chat_completions (default)
        return OpenAIChatClient(
            provider=canonical,
            model=model,
            api_key=api_key,
            base_url=base_url,
            extra_headers=extra_headers,
            extra_body=extra_body,
            **kwargs,
        )


# ─────────────────────────────────────────────────────────────────────────────
# High-level convenience wrappers
# ─────────────────────────────────────────────────────────────────────────────

def chat_complete(
    provider: str,
    model: str,
    messages: list[dict],
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    **kwargs,
) -> LLMResponse:
    """
    One-shot chat completion — resolves provider, builds client, calls API.

    Mirrors hermes-agent's transport-level chat completion flow.
    """
    # Apply reasoning effort from agent config if not overridden
    cfg = get_llm_config()
    if reasoning_effort is None and cfg.get("agent", {}).get("reasoning_effort"):
        reasoning_effort = cfg["agent"]["reasoning_effort"]

    client = create_llm_client(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        reasoning_effort=reasoning_effort,
        **kwargs,
    )

    return client.chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_config={"enabled": True, "effort": reasoning_effort} if reasoning_effort else None,
    )


def resolve_model_from_alias(model_alias: str) -> tuple[str, str]:
    """
    Resolve a model alias to (provider, model).
    E.g. "opus" → ("anthropic", "claude-opus-4-6")
    """
    cfg = get_llm_config()
    aliases = cfg.get("model_aliases", {})
    entry = aliases.get(model_alias)
    if entry:
        return entry.get("provider", "openrouter"), entry.get("model", model_alias)
    # Also check built-in aliases
    if model_alias == "opus":
        return "anthropic", "claude-opus-4-6"
    return "openrouter", model_alias


def get_default_model() -> tuple[str, str]:
    """Return (provider, model) from global config."""
    cfg = get_llm_config()
    model_section = cfg.get("model", {})
    default = model_section.get("default", "anthropic/claude-sonnet-4.6")
    if "/" in default:
        parts = default.split("/", 1)
        return parts[0], parts[1]
    return model_section.get("provider", "openrouter"), default