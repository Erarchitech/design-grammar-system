"""LLM Gateway — provider-agnostic adapters, encrypted settings, model discovery, and error mapping.

Implements the Strategy pattern with LLMAdapter ABC and three concrete adapters
(AnthropicAdapter, OpenAIAdapter, OllamaAdapter). Encrypts API keys at rest using
cryptography.fernet.Fernet with a master secret derived from SHA-256. Persists
settings to a JSON file in DATA_DIR. Provides seed model lists, Ollama auto-discovery
at startup, and structured error mapping per LLMC-06.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel


# ── Pydantic Models ──


class GenerateRequest(BaseModel):
    """Request body for POST /llm/generate.

    Attributes:
        prompt: The user prompt text.
        system: Optional system prompt (provider-native placement).
        model: Optional model override. If null, resolved from settings.
        provider: Explicit provider tag per D-02 ('anthropic', 'openai', 'ollama').
            If null, resolved from saved settings.
    """

    prompt: str
    system: str | None = None
    model: str | None = None
    provider: str | None = None


class GenerateResponse(BaseModel):
    """Normalised response envelope per D-04.

    Attributes:
        text: Generated text from the provider.
        provider: Provider that served the request.
        model: Model that served the request.
        usage: Normalised token usage {prompt_tokens, completion_tokens, total_tokens}.
    """

    text: str
    provider: str
    model: str
    usage: dict


class LLMSettingsPayload(BaseModel):
    """Request body for PUT /llm/settings.

    Attributes:
        provider: Provider to use.
        model: Model ID to use.
        apiKey: Plaintext API key (encrypted on write, never stored raw).
        baseUrl: Optional base URL (OpenAI-compatible only per D-03).
    """

    provider: str | None = None
    model: str | None = None
    apiKey: str | None = None
    baseUrl: str | None = None


class LLMSettingsResponse(BaseModel):
    """Response body for GET /llm/settings.

    Attributes:
        provider: Currently configured provider, if any.
        model: Currently configured model, if any.
        apiKeyConfigured: Whether an API key is stored (encrypted).
        apiKeyPreview: Masked key preview (never full key per LLMC-03).
        baseUrl: Optional base URL for OpenAI-compatible APIs.
    """

    provider: str | None = None
    model: str | None = None
    apiKeyConfigured: bool = False
    apiKeyPreview: str = ""
    baseUrl: str | None = None


class TestResult(BaseModel):
    """Response body for POST /llm/settings/test.

    Attributes:
        success: Whether the connection test succeeded.
        latencyMs: Round-trip latency in milliseconds.
        models: Live model list returned on success.
        error: Error message on failure.
    """

    success: bool
    latencyMs: float | None = None
    models: list[str] = []
    error: str | None = None


# ── Seed Model Lists (D-14, D-15) ──

SEED_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-sonnet-5",
        "claude-opus-4-8",
        "claude-haiku-4-5-20251001",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
    ],
    "ollama": [],  # Populated via auto-discovery at startup per D-16
}


# ── LLMAdapter Abstract Base Class (Strategy Pattern) ──


class LLMAdapter(ABC):
    """Abstract base for provider adapters.

    Subclasses implement provider-specific HTTP calls using httpx.Client (sync).
    Exceptions propagate to the caller for structured error mapping.
    """

    @abstractmethod
    def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        """Send a prompt to the provider and return a normalised response."""
        ...

    @abstractmethod
    def list_models(self, api_key: str | None) -> list[str]:
        """Return list of available model IDs from the provider."""
        ...


# ── AnthropicAdapter ──


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude Messages API.

    Auth via x-api-key header per D-03. No custom base URL — hardcoded to
    https://api.anthropic.com/v1. System prompt placed as top-level field
    (not inside messages array).
    """

    def __init__(self, base_url: str = "https://api.anthropic.com/v1") -> None:
        self.base_url = base_url

    def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        headers = {
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": req.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if req.system:
            body["system"] = req.system

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{self.base_url}/messages", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        text = next(
            (b["text"] for b in data.get("content", []) if b.get("type") == "text"),
            "",
        )
        usage_input = data.get("usage", {}).get("input_tokens", 0)
        usage_output = data.get("usage", {}).get("output_tokens", 0)
        usage = {
            "prompt_tokens": usage_input,
            "completion_tokens": usage_output,
            "total_tokens": usage_input + usage_output,
        }
        return GenerateResponse(
            text=text,
            provider="anthropic",
            model=req.model or "",
            usage=usage,
        )

    def list_models(self, api_key: str | None) -> list[str]:
        headers = {"x-api-key": api_key or ""}
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [item["id"] for item in data.get("data", [])]


# ── OpenAIAdapter ──


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI Chat Completions API (and compatible providers).

    Auth via Authorization: Bearer header. Base URL is configurable for
    OpenAI-compatible APIs (e.g. Groq, Together, Azure OpenAI).
    """

    def __init__(self, base_url: str = "https://api.openai.com/v1") -> None:
        self.base_url = base_url

    def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        headers = {
            "Authorization": f"Bearer {api_key or ''}",
            "content-type": "application/json",
        }
        messages: list[dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        body = {"model": req.model, "messages": messages, "max_tokens": 4096}

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        text = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        raw_usage = data.get("usage", {})
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens", 0),
            "completion_tokens": raw_usage.get("completion_tokens", 0),
            "total_tokens": raw_usage.get("total_tokens", 0),
        }
        return GenerateResponse(
            text=text,
            provider="openai",
            model=req.model or "",
            usage=usage,
        )

    def list_models(self, api_key: str | None) -> list[str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [item["id"] for item in data.get("data", [])]


# ── OllamaAdapter ──


class OllamaAdapter(LLMAdapter):
    """Adapter for local Ollama Generate API.

    No auth header. Points to the Docker service by default (http://ollama:11434).
    Uses 300s timeout to handle first-load model pulls.
    """

    def __init__(self, base_url: str = "http://ollama:11434") -> None:
        self.base_url = base_url

    def generate(self, req: GenerateRequest, api_key: str | None = None) -> GenerateResponse:
        body: dict[str, Any] = {
            "model": req.model,
            "prompt": req.prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4096},
        }
        if req.system:
            body["system"] = req.system

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=body)
            resp.raise_for_status()
            data = resp.json()

        text = data.get("response", "")
        prompt_eval = data.get("prompt_eval_count", 0)
        eval_count = data.get("eval_count", 0)
        usage = {
            "prompt_tokens": prompt_eval,
            "completion_tokens": eval_count,
            "total_tokens": prompt_eval + eval_count,
        }
        return GenerateResponse(
            text=text,
            provider="ollama",
            model=req.model or "",
            usage=usage,
        )

    def list_models(self, api_key: str | None = None) -> list[str]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        return [item["name"] for item in data.get("models", [])]


# ── Adapter Factory ──


def get_adapter(provider: str, base_url: str | None = None) -> LLMAdapter:
    """Return the correct adapter instance for the given provider tag.

    Args:
        provider: One of 'anthropic', 'openai', 'ollama' (case-sensitive per D-02).
        base_url: Optional base URL override. Only used by OpenAIAdapter
            for OpenAI-compatible providers (e.g. DeepSeek, Groq).

    Returns:
        LLMAdapter instance.

    Raises:
        ValueError: If provider is unknown.
    """
    if provider == "anthropic":
        return AnthropicAdapter()
    elif provider == "openai":
        return OpenAIAdapter(base_url=base_url or "https://api.openai.com/v1")
    elif provider == "ollama":
        return OllamaAdapter()
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ── Encryption Utilities (Fernet AES-GCM) ──


def _derive_key(master_secret: str) -> bytes:
    """Deterministic Fernet key from a master secret string.

    SHA-256 produces exactly 32 bytes, which Fernet requires as a
    url-safe-base64-encoded key. Same secret always produces same key,
    ensuring encrypted keys survive container restarts (Pitfall 1).
    """
    digest = hashlib.sha256(master_secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str, master_secret: str) -> str:
    """Encrypt a plaintext string with Fernet AES-GCM.

    Args:
        plaintext: The value to encrypt (e.g. API key).
        master_secret: Master secret used for key derivation.

    Returns:
        Fernet token as a base64-encoded string.
    """
    cipher = Fernet(_derive_key(master_secret))
    return cipher.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str, master_secret: str) -> str:
    """Decrypt a Fernet token.

    Args:
        ciphertext: Fernet token string.
        master_secret: Master secret used for key derivation.

    Returns:
        Original plaintext.

    Raises:
        cryptography.fernet.InvalidToken: If key is wrong or data corrupted.
    """
    cipher = Fernet(_derive_key(master_secret))
    return cipher.decrypt(ciphertext.encode()).decode()


def mask_key(key: str) -> str:
    """Return a masked preview of an API key — never the full string.

    Rules:
      - Empty key → ""
      - Key length > 12 → first 6 + "..." + last 6
      - Key length 5-12 → first 2 + "..." + last 2
      - Key length <= 4 → "****"
    """
    if not key:
        return ""
    if len(key) > 12:
        return key[:6] + "..." + key[-6:]
    elif len(key) > 4:
        return key[:2] + "..." + key[-2:]
    else:
        return "****"


# ── Settings Persistence ──

DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
LLM_SETTINGS_FILE = DATA_DIR / "llm-settings.json"


def load_persisted_llm_settings() -> dict[str, str]:
    """Read LLM settings from the JSON settings file.

    Returns an empty dict if the file is missing, malformed, or empty.
    """
    if not LLM_SETTINGS_FILE.exists():
        return {}
    try:
        payload = json.loads(LLM_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    settings: dict[str, str] = {}
    for key in ("provider", "model", "apiKey", "baseUrl"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            settings[key] = value.strip()
    return settings


def save_persisted_llm_settings(settings: dict[str, str]) -> None:
    """Write LLM settings to the JSON settings file.

    Creates DATA_DIR if it does not exist. Strips empty values before writing.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in settings.items() if value}
    LLM_SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_llm_settings_response(
    settings: dict[str, str],
    master_secret: str,
) -> LLMSettingsResponse:
    """Build an LLMSettingsResponse from a raw settings dict.

    Decrypts and masks the API key. Never returns the raw key string.
    On decryption failure (wrong master secret), returns configured=False
    with empty preview.
    """
    provider = settings.get("provider")
    model = settings.get("model")
    base_url = settings.get("baseUrl")
    encrypted_key = settings.get("apiKey", "")

    if encrypted_key:
        try:
            decrypted = decrypt_value(encrypted_key, master_secret)
            preview = mask_key(decrypted)
            configured = True
        except InvalidToken:
            preview = ""
            configured = False
    else:
        preview = ""
        configured = False

    return LLMSettingsResponse(
        provider=provider,
        model=model,
        apiKeyConfigured=configured,
        apiKeyPreview=preview,
        baseUrl=base_url,
    )


# ── Active Provider Resolution (D-07) ──


def resolve_active_provider(
    settings: dict[str, str],
    master_secret: str,
) -> tuple[str, str | None, str | None]:
    """Resolve the active provider, model, and API key from settings.

    If settings contain a provider, model, and encrypted apiKey, decrypts
    the key and returns the triplet. Otherwise returns Ollama fallback:
    ("ollama", None, None).

    Returns:
        Tuple of (provider, model, api_key_or_none).
    """
    provider = settings.get("provider")
    model = settings.get("model")
    encrypted_key = settings.get("apiKey", "")

    if provider and model and encrypted_key:
        try:
            api_key = decrypt_value(encrypted_key, master_secret)
            return (provider, model, api_key)
        except InvalidToken:
            return ("ollama", None, None)

    return ("ollama", None, None)


# ── Model Discovery (D-13, D-14, D-16) ──

import threading

_ollama_models_cache: list[str] | None = None
_ollama_cache_lock = threading.Lock()


def init_ollama_models() -> None:
    """Auto-discover Ollama models at startup by calling /api/tags.

    Silently sets cache to empty list if Ollama is not running
    (no crash on first compose up before Ollama is ready).
    """
    global _ollama_models_cache
    try:
        adapter = OllamaAdapter()
        _ollama_models_cache = adapter.list_models(None)
    except Exception:
        _ollama_models_cache = []


def list_models_for_provider(
    provider: str,
    api_key: str | None,
    base_url: str | None = None,
) -> list[str]:
    """Return available model IDs for the given provider.

    For Ollama: returns cached models from auto-discovery (D-16).
    For Anthropic/OpenAI with valid key: queries the provider API live.
    For Anthropic/OpenAI without key: returns seed models (D-14).
    On any error: falls back to seed models.
    """
    try:
        if provider == "ollama":
            global _ollama_models_cache
            with _ollama_cache_lock:
                if _ollama_models_cache is None:
                    init_ollama_models()
                return _ollama_models_cache or []

        adapter = get_adapter(provider, base_url)
        if api_key:
            return adapter.list_models(api_key)
        return SEED_MODELS.get(provider, [])
    except Exception:
        return SEED_MODELS.get(provider, [])


def should_refresh_on_test(provider: str) -> bool:
    """Whether to replace seed models with live results after a successful test.

    Anthropic and OpenAI: yes (seed list replaced after key validation).
    Ollama: no (already auto-discovered at startup).
    """
    return provider in ("anthropic", "openai")


# ── Error Mapping (LLMC-06, D-08) ──


def map_provider_error(exc: Exception) -> tuple[str, str, str]:
    """Map a provider exception to a structured (error, hint, code) triple.

    Never includes raw API key, provider endpoint URL, or response body
    snippets in the error message (LLMC-06 security requirement).

    Returns:
        Tuple of (error_message, user_actionable_hint, error_code).
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return (
                "Provider authentication failed. Check your API key.",
                "Check your API key in LLM Settings.",
                "PROVIDER_AUTH_FAILED",
            )
        elif status == 429:
            return (
                "Provider quota exceeded. Your account has hit a rate or usage limit.",
                "Verify your provider account has available quota.",
                "PROVIDER_QUOTA_EXCEEDED",
            )
        elif status >= 500:
            return (
                "Provider service temporarily unavailable.",
                "The provider service is temporarily unavailable. Try again later.",
                "PROVIDER_UNAVAILABLE",
            )
        return (
            f"Provider returned HTTP {status}.",
            "Check your API key and provider status.",
            "PROVIDER_UNKNOWN_ERROR",
        )
    elif isinstance(exc, httpx.TimeoutException):
        return (
            "Provider request timed out.",
            "The provider service is slow or unreachable. Try again later.",
            "PROVIDER_TIMEOUT",
        )
    elif isinstance(exc, httpx.RequestError):
        return (
            "Could not connect to provider.",
            "Verify the provider URL is correct and the service is reachable.",
            "PROVIDER_UNAVAILABLE",
        )
    else:
        return (
            f"Unexpected provider error: {type(exc).__name__}",
            "Check data-service logs for details.",
            "PROVIDER_UNKNOWN_ERROR",
        )
