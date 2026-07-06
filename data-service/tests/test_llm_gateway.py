"""Tests for LLM Gateway — adapter routing, fallback, key masking, encryption, error mapping.

Follows the existing test pattern from test_error_responses.py: FastAPI TestClient
with raise_server_exceptions=False, unittest.mock.patch for dependencies.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest
from cryptography.fernet import InvalidToken
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["LLM_MASTER_SECRET"] = "test-master-secret"

from app import app  # noqa: E402
from llm_gateway import (  # noqa: E402
    GenerateResponse,
    _derive_key,
    decrypt_value,
    encrypt_value,
    mask_key,
    resolve_active_provider,
)

client = TestClient(app, raise_server_exceptions=False)


# ── Key Masking ──


class TestKeyMasking:
    def test_long_key(self):
        """Key > 12 chars → first 6 + '...' + last 6."""
        assert mask_key("sk-ant-abcdefghijklmnop") == "sk-ant...klmnop"

    def test_medium_key(self):
        """Key 5-12 chars → first 2 + '...' + last 2."""
        assert mask_key("short") == "sh...rt"

    def test_short_key(self):
        """Key <= 4 chars → '****'."""
        assert mask_key("ab") == "****"

    def test_exactly_12_chars(self):
        """Exactly 12 chars → 5-12 rule applies (first 2 + '...' + last 2)."""
        assert mask_key("123456789abc") == "12...bc"

    def test_empty_key(self):
        """Empty key → ''."""
        assert mask_key("") == ""


# ── Fernet Encryption ──


class TestFernet:
    def test_roundtrip(self):
        """Encrypt then decrypt with same secret returns original."""
        assert decrypt_value(encrypt_value("test-key", "secret"), "secret") == "test-key"

    def test_wrong_key(self):
        """Decrypt with wrong secret raises InvalidToken."""
        encrypted = encrypt_value("test", "secret")
        with pytest.raises(InvalidToken):
            decrypt_value(encrypted, "wrong")

    def test_deterministic_key_derivation(self):
        """Same master secret produces same derived key."""
        assert _derive_key("hello") == _derive_key("hello")

    def test_different_secret_different_key(self):
        """Different master secrets produce different derived keys."""
        assert _derive_key("hello") != _derive_key("world")


# ── resolve_active_provider ──


class TestResolveActiveProvider:
    def test_full_settings(self):
        """Valid settings with provider, model, and encrypted key → returns decrypted triplet."""
        encrypted = encrypt_value("sk-ant-test-key", "test-master-secret")
        settings = {"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": encrypted}
        provider, model, api_key = resolve_active_provider(settings, "test-master-secret")
        assert provider == "anthropic"
        assert model == "claude-sonnet-5"
        assert api_key == "sk-ant-test-key"

    def test_empty_settings_returns_ollama_fallback(self):
        """Empty settings → ('ollama', None, None)."""
        provider, model, api_key = resolve_active_provider({}, "test-master-secret")
        assert provider == "ollama"
        assert model is None
        assert api_key is None

    def test_missing_api_key_returns_ollama_fallback(self):
        """Settings with provider+model but no apiKey → ('ollama', None, None)."""
        settings = {"provider": "anthropic", "model": "claude-sonnet-5"}
        provider, model, api_key = resolve_active_provider(settings, "test-master-secret")
        assert provider == "ollama"
        assert model is None
        assert api_key is None

    def test_wrong_master_secret_returns_ollama_fallback(self):
        """Settings with apiKey encrypted under different secret → ('ollama', None, None)."""
        encrypted = encrypt_value("sk-ant-test-key", "other-secret")
        settings = {"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": encrypted}
        provider, model, api_key = resolve_active_provider(settings, "test-master-secret")
        assert provider == "ollama"
        assert model is None
        assert api_key is None


# ── GET /llm/settings ──


class TestGetSettings:
    @patch("app.load_persisted_llm_settings", return_value={})
    def test_empty_state(self, mock_load):
        """GET /llm/settings with no persisted settings returns empty state."""
        response = client.get("/llm/settings")
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] is None
        assert body["model"] is None
        assert body["apiKeyConfigured"] is False
        assert body["apiKeyPreview"] == ""
        assert body["baseUrl"] is None

    @patch("app.load_persisted_llm_settings")
    def test_with_configured_settings(self, mock_load):
        """GET /llm/settings with saved settings returns masked key."""
        encrypted = encrypt_value("sk-ant-test-key-123456", "test-master-secret")
        mock_load.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "apiKey": encrypted,
            "baseUrl": "https://api.anthropic.com/v1",
        }
        response = client.get("/llm/settings")
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "anthropic"
        assert body["model"] == "claude-sonnet-5"
        assert body["apiKeyConfigured"] is True
        assert body["apiKeyPreview"] != ""  # Masked preview present
        assert "..." in body["apiKeyPreview"]  # Is actually masked
        assert "test-key" not in body["apiKeyPreview"]  # No raw key in response
        assert body["baseUrl"] == "https://api.anthropic.com/v1"


# ── PUT /llm/settings ──


class TestPutSettings:
    @patch("app.save_persisted_llm_settings")
    @patch("app.load_persisted_llm_settings")
    def test_save_settings(self, mock_load, mock_save):
        """PUT /llm/settings with valid body encrypts and persists."""
        encrypted = encrypt_value("sk-test", "test-master-secret")
        mock_load.side_effect = [
            {},  # First call: load existing (empty)
            {"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": encrypted},  # Second call: re-read
        ]
        response = client.put(
            "/llm/settings",
            json={"provider": "anthropic", "model": "claude-sonnet-5", "apiKey": "sk-test"},
        )
        # save was called with encrypted key
        saved = mock_save.call_args[0][0]
        assert saved["provider"] == "anthropic"
        assert saved["model"] == "claude-sonnet-5"
        assert saved["apiKey"] != "sk-test"  # Key was encrypted
        assert saved["apiKey"].startswith("g")  # Fernet base64 token
        assert len(saved["apiKey"]) > 20  # Substantial encrypted output
        # Response has apiKeyConfigured=True
        assert response.status_code == 200
        body = response.json()
        assert body["apiKeyConfigured"] is True

    @patch("app.save_persisted_llm_settings")
    @patch("app.load_persisted_llm_settings")
    def test_empty_api_key_does_not_overwrite(self, mock_load, mock_save):
        """PUT with apiKey=None keeps existing encrypted key."""
        encrypted = encrypt_value("existing-key", "test-master-secret")
        mock_load.side_effect = [
            {  # First call: load existing (has encrypted key)
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "apiKey": encrypted,
            },
            {  # Second call: re-read after save
                "provider": "openai",
                "model": "gpt-4o",
                "apiKey": encrypted,
            },
        ]
        response = client.put(
            "/llm/settings",
            json={"provider": "openai", "model": "gpt-4o"},
        )
        assert response.status_code == 200
        saved = mock_save.call_args[0][0]
        assert saved["apiKey"] == encrypted  # Existing key preserved
        assert saved["provider"] == "openai"
        assert saved["model"] == "gpt-4o"


# ── DELETE /llm/settings ──


class TestDeleteSettings:
    @patch("app.save_persisted_llm_settings")
    def test_clear_settings(self, mock_save):
        """DELETE /llm/settings clears settings and returns 204."""
        response = client.delete("/llm/settings")
        assert response.status_code == 204
        mock_save.assert_called_once_with({})


# ── POST /llm/generate ──


class TestGenerate:
    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_adapter_routing(self, mock_load, mock_get_adapter):
        """POST /llm/generate routes to correct adapter with valid settings."""
        encrypted = encrypt_value("sk-ant-test", "test-master-secret")
        mock_load.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "apiKey": encrypted,
        }
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = GenerateResponse(
            text="Hello from Claude",
            provider="anthropic",
            model="claude-sonnet-5",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/llm/generate",
            json={"prompt": "Say hello", "provider": "anthropic", "model": "claude-sonnet-5"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Hello from Claude"
        assert body["provider"] == "anthropic"
        assert body["model"] == "claude-sonnet-5"
        assert body["usage"]["prompt_tokens"] == 10

    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings", return_value={})
    def test_fallback_resolution(self, mock_load, mock_get_adapter):
        """POST /llm/generate with empty settings resolves to Ollama."""
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = GenerateResponse(
            text="Hello from Ollama",
            provider="ollama",
            model="",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/llm/generate", json={"prompt": "hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "ollama"

    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_no_key_fallback(self, mock_load, mock_get_adapter):
        """POST /llm/generate with settings missing apiKey falls back to Ollama."""
        mock_load.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
        }
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = GenerateResponse(
            text="Hello from Ollama",
            provider="ollama",
            model="",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/llm/generate", json={"prompt": "hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "ollama"

    @patch("app.map_provider_error")
    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_error_mapping(self, mock_load, mock_get_adapter, mock_map_error):
        """Provider auth error returns 502 with structured {error, hint, code}."""
        encrypted = encrypt_value("sk-ant-test", "test-master-secret")
        mock_load.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "apiKey": encrypted,
        }
        mock_adapter = MagicMock()
        mock_request = MagicMock()
        mock_response = MagicMock(status_code=401)
        mock_adapter.generate.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=mock_request, response=mock_response,
        )
        mock_get_adapter.return_value = mock_adapter
        mock_map_error.return_value = (
            "Provider authentication failed. Check your API key.",
            "Check your API key in LLM Settings.",
            "PROVIDER_AUTH_FAILED",
        )

        response = client.post(
            "/llm/generate",
            json={"prompt": "hello", "provider": "anthropic", "model": "claude-sonnet-5"},
        )
        assert response.status_code == 502
        detail = response.json().get("detail", response.json())
        assert "error" in detail
        assert "hint" in detail
        assert "code" in detail
        assert detail["code"] == "PROVIDER_AUTH_FAILED"
        # No raw key or URL in error
        assert "sk-ant-test" not in json.dumps(detail)
        assert "api.anthropic.com" not in json.dumps(detail)

    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_generate_with_system_prompt(self, mock_load, mock_get_adapter):
        """System prompt is passed through to the adapter."""
        encrypted = encrypt_value("sk-test", "test-master-secret")
        mock_load.return_value = {
            "provider": "openai",
            "model": "gpt-4o",
            "apiKey": encrypted,
        }
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = GenerateResponse(
            text="Response with system",
            provider="openai",
            model="gpt-4o",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/llm/generate",
            json={
                "prompt": "hello",
                "system": "You are a test assistant",
                "provider": "openai",
                "model": "gpt-4o",
            },
        )
        assert response.status_code == 200
        # Verify the adapter was called with system prompt
        call_kwargs = mock_adapter.generate.call_args
        assert call_kwargs is not None
        called_req = call_kwargs[0][0]
        assert called_req.system == "You are a test assistant"
        assert called_req.prompt == "hello"


# ── POST /llm/settings/test ──


class TestConnection:
    @patch("app.list_models_for_provider", return_value=["model1", "model2"])
    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_connection_success(self, mock_load, mock_get_adapter, mock_models):
        """POST /llm/settings/test with valid config returns success with latency."""
        encrypted = encrypt_value("sk-test", "test-master-secret")
        mock_load.return_value = {
            "provider": "openai",
            "model": "gpt-4o",
            "apiKey": encrypted,
        }
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/llm/settings/test")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["latencyMs"] is not None
        assert body["latencyMs"] >= 0
        assert body["models"] == ["model1", "model2"]

    @patch("app.load_persisted_llm_settings", return_value={})
    def test_connection_no_key(self, mock_load):
        """POST /llm/settings/test with no key returns actionable error."""
        response = client.post("/llm/settings/test")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["error"] is not None
        assert "No API key configured" in body["error"]

    @patch("app.get_adapter")
    @patch("app.load_persisted_llm_settings")
    def test_connection_provider_error(self, mock_load, mock_get_adapter):
        """POST /llm/settings/test with bad key returns error (not crash)."""
        encrypted = encrypt_value("sk-bad", "test-master-secret")
        mock_load.return_value = {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "apiKey": encrypted,
        }
        mock_adapter = MagicMock()
        mock_request = MagicMock()
        mock_response = MagicMock(status_code=401)
        mock_adapter.generate.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=mock_request, response=mock_response,
        )
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/llm/settings/test")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["error"] is not None


# ── GET /llm/models ──


class TestModels:
    @patch("app.list_models_for_provider", return_value=["model1", "model2"])
    def test_models_endpoint(self, mock_list):
        """GET /llm/models returns provider's model list."""
        response = client.get("/llm/models?provider=anthropic")
        assert response.status_code == 200
        body = response.json()
        assert body == ["model1", "model2"]

    @patch("app.list_models_for_provider", return_value=[])
    def test_models_empty_for_unknown(self, mock_list):
        """GET /llm/models for provider with no models returns empty list."""
        response = client.get("/llm/models?provider=ollama")
        assert response.status_code == 200
        assert response.json() == []


# ── Error response shape ──


def test_error_response_shape():
    """Verify _structured_error_response produces exactly 3 keys: error, hint, code."""
    from app import _structured_error_response

    exc = _structured_error_response("Something broke", "Try this fix", "ERR_CODE", 422)
    assert exc.status_code == 422
    detail = exc.detail
    assert set(detail.keys()) == {"error", "hint", "code"}
    assert detail["error"] == "Something broke"
    assert detail["hint"] == "Try this fix"
    assert detail["code"] == "ERR_CODE"


# ── Import all symbols ──


def test_module_imports():
    """All public symbols import without errors."""
    from llm_gateway import (
        AnthropicAdapter,
        GenerateRequest,
        GenerateResponse,
        LLMSettingsPayload,
        LLMSettingsResponse,
        LLMAdapter,
        OpenAIAdapter,
        OllamaAdapter,
        SEED_MODELS,
        TestResult,
        get_adapter,
        get_llm_settings_response,
        init_ollama_models,
        list_models_for_provider,
        load_persisted_llm_settings,
        map_provider_error,
        save_persisted_llm_settings,
        should_refresh_on_test,
    )  # noqa: F401
    assert get_adapter is not None
