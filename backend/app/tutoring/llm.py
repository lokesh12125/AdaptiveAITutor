"""Configurable model-provider adapter. Keys stay on the server.

Text generation is optional: every caller has a deterministic alternative, so a provider outage or
LLM_PROVIDER=none never blocks tutoring. Plain httpx is used to avoid a heavy SDK per provider.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from ..config import settings

log = logging.getLogger("csmasf.llm")


class LLMUnavailable(Exception):
    """The provider failed or is not configured. Callers fall back to built-in behaviour."""


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> LLMResult: ...


class NoProvider:
    name = "none"
    model = ""

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> LLMResult:
        raise LLMUnavailable("No model provider is configured.")


class OpenAICompatible:
    """OpenAI, and any server exposing the same API, including Ollama."""

    def __init__(self, name: str, base_url: str, api_key: str, model: str) -> None:
        self.name, self.model = name, model
        self._client = httpx.Client(
            base_url=base_url, timeout=settings.llm_timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> LLMResult:
        started = time.monotonic()
        try:
            response = self._client.post("/chat/completions", json={
                "model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            })
            response.raise_for_status()
            body = response.json()
            text = body["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable(type(exc).__name__) from exc
        return LLMResult(text, self.name, self.model, int((time.monotonic() - started) * 1000), body.get("usage") or {})


class Anthropic:
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = httpx.Client(
            base_url="https://api.anthropic.com", timeout=settings.llm_timeout_seconds,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> LLMResult:
        started = time.monotonic()
        try:
            response = self._client.post("/v1/messages", json={
                "model": self.model, "max_tokens": max_tokens, "temperature": temperature, "system": system,
                "messages": [{"role": "user", "content": user}],
            })
            response.raise_for_status()
            body = response.json()
            text = "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMUnavailable(type(exc).__name__) from exc
        return LLMResult(text, self.name, self.model, int((time.monotonic() - started) * 1000), body.get("usage") or {})


def build_provider() -> Provider:
    choice = settings.llm_provider.lower()
    if choice == "openai" and settings.openai_api_key:
        return OpenAICompatible("openai", settings.openai_base_url, settings.openai_api_key, settings.openai_model)
    if choice == "anthropic" and settings.anthropic_api_key:
        return Anthropic(settings.anthropic_api_key, settings.anthropic_model)
    if choice == "ollama":
        return OpenAICompatible("ollama", settings.ollama_base_url, "", settings.ollama_model)
    if choice not in ("none", "openai", "anthropic", "ollama"):
        log.warning("Unknown LLM_PROVIDER %r; using built-in tutoring text.", choice)
    return NoProvider()


class LLMGateway:
    """Single entry point, so tests can substitute a provider and each call records its metadata."""

    def __init__(self) -> None:
        self.provider: Provider = build_provider()

    @property
    def enabled(self) -> bool:
        return self.provider.name != "none"

    def describe(self) -> dict[str, Any]:
        return {"provider": self.provider.name, "model": self.provider.model or None, "enabled": self.enabled}

    def complete_json(self, system: str, user: str, max_tokens: int = 500, temperature: float = 0.2) -> tuple[dict[str, Any], LLMResult]:
        result = self.provider.complete(system + "\nRespond with one JSON object only.", user, max_tokens, temperature)
        parsed = parse_json_object(result.text)
        if parsed is None:
            raise LLMUnavailable("Model did not return valid JSON.")
        return parsed, result


def parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


gateway = LLMGateway()
