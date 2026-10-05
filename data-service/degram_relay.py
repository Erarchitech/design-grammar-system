"""DeGram LLM relay (Phase 1301 plan 08, D-16, DGCL-02, DGCL-05, DGCL-06, DGCL-07).

``POST /degram/v1/chat/completions`` is the ONLY model path of the local DeGram
agent. It is user-scoped (a delegated ``dgd_`` principal only), streaming and
OpenAI-compatible:

* The upstream is ONE operator-configured endpoint (``degram-llm.json``): base
  URL, model (default ``mimo-v2.5-pro``), provider label (default ``genpro``)
  and the system API key, Fernet-encrypted at rest with the same master secret
  and helpers as the LLM gateway. It does not read ``llm-settings.json`` and does
  not use ``llm_gateway.resolve_active_provider``: there is NO fallback to
  another provider, to Ollama, or to a different model.
* The user never selects the model or the provider (DGCL-02): any ``model`` /
  ``provider`` in the request is discarded and the configured model is sent.
* Every relayed request appends one provenance record (JSONL, append-only) with
  the requested and the served model, response id, fingerprint, usage, outcome,
  user, company, project and payload size. It never contains prompt text, tool
  arguments or the key.

The relay is deliberately NOT the ``/llm/generate`` gateway (synchronous, no
streaming or tools, service-token only) and ``/llm/*`` does not route here.

Operational outcomes (``OPERATIONAL_OUTCOMES``) are NOT evaluator statuses; see
``spec/degram/OPERATIONAL-OUTCOMES.md``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import degram_policy
from llm_gateway import decrypt_value, encrypt_value, mask_key

_LOGGER = logging.getLogger(__name__)

RELAY_ROUTE = "/degram/v1/chat/completions"
CONFIG_FILE_NAME = "degram-llm.json"
PROVENANCE_FILE_NAME = "degram-llm-provenance.jsonl"

# Request body ceiling (T-1301-08-04); enforced before any provider contact.
DEGRAM_RELAY_MAX_BODY_BYTES = 1048576

HEADER_CONTEXT_SCOPE = "X-DeGram-Context-Scope"
HEADER_WHOLE_DEFINITION_CONSENT = "X-DeGram-Whole-Definition-Consent"
SCOPE_NONE = "none"
SCOPE_SELECTION = "selection"
SCOPE_WHOLE_DEFINITION = "whole-definition"
CONTEXT_SCOPES = (SCOPE_NONE, SCOPE_SELECTION, SCOPE_WHOLE_DEFINITION)
_CONSENT_VALUES = frozenset({"true", "1"})

DEFAULT_PROVIDER_LABEL = "genpro"
DEFAULT_MODEL = "mimo-v2.5-pro"

# Request fields forwarded to the upstream besides messages/tools/tool_choice.
# ``model``, ``provider`` and ``stream`` are never forwarded from the client.
_PASSTHROUGH_FIELDS = ("temperature", "top_p", "max_tokens", "max_completion_tokens", "stop")

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Outcomes written to provenance.
OUTCOME_COMPLETED = "COMPLETED"
OUTCOME_RELAY_NOT_CONFIGURED = "RELAY_NOT_CONFIGURED"
OUTCOME_PROVIDER_ERROR = "PROVIDER_ERROR"

_PROVENANCE_LOCK = threading.Lock()
_CONFIG_LOCK = threading.Lock()


def _transport_factory() -> httpx.AsyncBaseTransport | None:
    """Transport used for the upstream call. ``None`` means the real network;
    tests replace this module attribute with an ``httpx.MockTransport`` factory
    so no test ever reaches a provider."""
    return None


# -- errors -------------------------------------------------------------------


def relay_error(
    status_code: int, code: str, error: str, hint: str, **extra: Any
) -> HTTPException:
    """``{error, hint, code}`` detail (the data-service shape) plus optional
    extra fields (``reason``, ``retryAfter``, ...)."""
    detail: dict[str, Any] = {"error": error, "hint": hint, "code": code}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


class RelayError(Exception):
    """An upstream or relay failure with a named operational outcome."""

    def __init__(
        self,
        code: str,
        *,
        status: int,
        error: str,
        hint: str,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(f"{code}: {error}")
        self.code = code
        self.status = status
        self.error = error
        self.hint = hint
        self.extra = dict(extra or {})
        self.headers = dict(headers or {})

    def to_http(self) -> HTTPException:
        detail: dict[str, Any] = {"error": self.error, "hint": self.hint, "code": self.code}
        detail.update(self.extra)
        return HTTPException(status_code=self.status, detail=detail, headers=self.headers or None)


# -- operator config store (degram-llm.json) ------------------------------------


def _data_dir() -> Path:
    return Path(os.getenv("DG_DATA_DIR", "/app/data"))


def config_path() -> Path:
    return _data_dir() / CONFIG_FILE_NAME


def provenance_path() -> Path:
    return _data_dir() / PROVENANCE_FILE_NAME


def _master_secret() -> str:
    return os.getenv("LLM_MASTER_SECRET", "")


def _atomic_write(path: Path, text: str) -> None:
    """Write `text` to `path` through a temp file and ``os.replace``; the
    result is owner-only where the platform supports it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass
    last: OSError | None = None
    for attempt in range(5):  # a Windows scanner can briefly hold the target
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:  # pragma: no cover - Windows only
            last = exc
            time.sleep(0.05 * (attempt + 1))
    if last is not None:  # pragma: no cover
        raise last


def load_stored_config() -> dict[str, str]:
    """The stored config dict, or ``{}`` when absent or unreadable."""
    path = config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if isinstance(v, str) and v.strip()}


def validate_base_url(value: str) -> str:
    """Normalise and validate the upstream base URL. https only, except plain
    http to localhost; no credentials, query or fragment. Raises ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("baseUrl must not be empty")
    candidate = value.strip()
    try:
        parsed = urlparse(candidate)
        host = parsed.hostname
    except ValueError as exc:
        raise ValueError("baseUrl is not a valid URL") from exc
    if parsed.scheme not in ("https", "http") or not host:
        raise ValueError("baseUrl must be an https URL")
    if parsed.scheme == "http" and host not in _LOCAL_HOSTS:
        raise ValueError("plain http is allowed only for localhost")
    if parsed.username or parsed.password:
        raise ValueError("baseUrl must not carry credentials")
    if parsed.query or parsed.fragment or parsed.params:
        raise ValueError("baseUrl must not carry a query or fragment")
    return candidate.rstrip("/")


class RelayConfigPayload(BaseModel):
    baseUrl: str | None = None
    model: str | None = None
    providerLabel: str | None = None
    apiKey: str | None = None


def _clean_label(value: str, name: str, limit: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > limit or any(ord(c) < 32 or ord(c) == 127 for c in cleaned):
        raise ValueError(f"{name} must be 1-{limit} printable characters")
    return cleaned


def store_config(payload: RelayConfigPayload) -> dict[str, Any]:
    """Merge `payload` into the stored config (an omitted or empty field keeps
    the stored value) and persist it with the key encrypted. Raises
    HTTPException 422 ``RELAY_CONFIG_INVALID`` / 500 for a missing secret."""
    master_secret = _master_secret()
    if not master_secret:
        raise relay_error(
            500,
            "LLM_MASTER_SECRET_NOT_CONFIGURED",
            "The server has no master secret to encrypt the relay key with.",
            "Set LLM_MASTER_SECRET for the data-service container.",
        )
    with _CONFIG_LOCK:
        stored = load_stored_config()
        merged = dict(stored)
        try:
            if payload.baseUrl:
                merged["baseUrl"] = validate_base_url(payload.baseUrl)
            if payload.model:
                merged["model"] = _clean_label(payload.model, "model", 200)
            if payload.providerLabel:
                merged["providerLabel"] = _clean_label(payload.providerLabel, "providerLabel", 60)
        except ValueError as exc:
            raise relay_error(
                422,
                "RELAY_CONFIG_INVALID",
                f"The relay configuration is not valid: {exc}.",
                "Use an https base URL (http only for localhost), a model name and a provider label.",
            ) from exc
        if payload.apiKey:
            merged["apiKey"] = encrypt_value(payload.apiKey.strip(), master_secret)
        if not merged.get("baseUrl") or not merged.get("apiKey"):
            raise relay_error(
                422,
                "RELAY_CONFIG_INVALID",
                "The relay configuration needs a base URL and an API key.",
                "Send baseUrl and apiKey on the first configuration.",
            )
        merged.setdefault("model", DEFAULT_MODEL)
        merged.setdefault("providerLabel", DEFAULT_PROVIDER_LABEL)
        _atomic_write(config_path(), json.dumps(merged, indent=2))
    return masked_config()


@dataclass(frozen=True)
class RelayConfig:
    base_url: str
    model: str
    provider_label: str
    api_key: str = ""

    def __repr__(self) -> str:  # never print the key
        return f"RelayConfig(base_url={self.base_url!r}, model={self.model!r}, provider_label={self.provider_label!r})"


def resolve_runtime_config() -> RelayConfig | None:
    """The runnable config with the key decrypted, or None when the relay is
    not configured (missing file/fields/secret, or an unreadable key)."""
    stored = load_stored_config()
    secret = _master_secret()
    if not stored.get("baseUrl") or not stored.get("apiKey") or not secret:
        return None
    try:
        key = decrypt_value(stored["apiKey"], secret)
    except Exception:  # noqa: BLE001 - wrong secret / corrupt token == not configured
        return None
    return RelayConfig(
        base_url=stored["baseUrl"],
        model=stored.get("model") or DEFAULT_MODEL,
        provider_label=stored.get("providerLabel") or DEFAULT_PROVIDER_LABEL,
        api_key=key,
    )


def masked_config() -> dict[str, Any]:
    """Operator-facing view of the config: never the key."""
    stored = load_stored_config()
    config = resolve_runtime_config()
    return {
        "configured": config is not None,
        "baseUrl": stored.get("baseUrl"),
        "model": stored.get("model") or DEFAULT_MODEL,
        "providerLabel": stored.get("providerLabel") or DEFAULT_PROVIDER_LABEL,
        "apiKeyPreview": mask_key(config.api_key) if config else "",
    }


# -- provenance -----------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def append_provenance(record: dict[str, Any]) -> None:
    """Append one JSON line to the provenance log. A write failure is logged
    and never turns a relayed request into an error."""
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    try:
        path = provenance_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _PROVENANCE_LOCK, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        _LOGGER.warning("degram relay: could not append the provenance record")


class StreamCapture:
    """Reads the model, id, fingerprint and usage out of the SSE ``data:``
    lines as they pass. It keeps no message content."""

    def __init__(self) -> None:
        self.served_model: str | None = None
        self.response_id: str | None = None
        self.fingerprint: str | None = None
        self.usage: dict[str, Any] | None = None

    def feed(self, line: str) -> None:
        if not line.startswith("data:"):
            return
        data = line[5:].strip()
        if not data or data == "[DONE]":
            return
        try:
            chunk = json.loads(data)
        except ValueError:
            return
        if not isinstance(chunk, dict):
            return
        if isinstance(chunk.get("model"), str) and chunk["model"]:
            self.served_model = chunk["model"]
        if isinstance(chunk.get("id"), str) and chunk["id"]:
            self.response_id = chunk["id"]
        if isinstance(chunk.get("system_fingerprint"), str) and chunk["system_fingerprint"]:
            self.fingerprint = chunk["system_fingerprint"]
        if isinstance(chunk.get("usage"), dict):
            self.usage = chunk["usage"]


# -- upstream adapter -----------------------------------------------------------


class DegramRelayAdapter:
    """Streaming OpenAI-compatible chat adapter for the ONE configured
    endpoint. One call per request, no retry, no fallback."""

    def __init__(self, config: RelayConfig, *, capture: StreamCapture | None = None) -> None:
        self.config = config
        self.capture = capture or StreamCapture()

    def build_payload(
        self,
        messages: list[Any],
        tools: Any = None,
        tool_choice: Any = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in (extra or {}).items():
            if key in _PASSTHROUGH_FIELDS:
                payload[key] = value
        payload["messages"] = messages
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        payload["model"] = self.config.model  # the server picks the model, always
        payload["stream"] = True
        return payload

    async def stream_chat(
        self,
        messages: list[Any],
        tools: Any = None,
        tool_choice: Any = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Yield the upstream SSE lines (without the trailing newline, blank
        separators included) while recording model/id/usage. Raises
        :class:`RelayError`."""
        payload = self.build_payload(messages, tools, tool_choice, extra)
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "text/event-stream",
        }
        client = httpx.AsyncClient(transport=_transport_factory(), follow_redirects=False)
        response: httpx.Response | None = None
        try:
            try:
                request = client.build_request("POST", url, json=payload, headers=headers)
                response = await client.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise RelayError(
                    OUTCOME_PROVIDER_ERROR,
                    status=502,
                    error="The model provider could not be reached.",
                    hint="Try again later or ask an administrator to check the relay.",
                ) from exc
            if response.status_code < 200 or response.status_code >= 300:
                raise RelayError(
                    OUTCOME_PROVIDER_ERROR,
                    status=502,
                    error="The model provider refused the request.",
                    hint="Ask an administrator to check the relay configuration.",
                    extra={"upstreamStatus": response.status_code},
                )
            async for line in response.aiter_lines():
                self.capture.feed(line)
                yield line
        finally:
            if response is not None:
                await response.aclose()
            await client.aclose()


# -- route handler --------------------------------------------------------------


def _error_event(error: RelayError) -> str:
    body = {"code": error.code, "error": error.error, "hint": error.hint, **error.extra}
    return f"event: degram-error\ndata: {json.dumps(body)}\n\n"


def _too_large() -> HTTPException:
    return relay_error(
        413,
        "RELAY_BODY_TOO_LARGE",
        f"The request body exceeds {DEGRAM_RELAY_MAX_BODY_BYTES} bytes.",
        "Send less context: narrow the selection or drop history.",
    )


async def _read_capped_body(request: Request) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > DEGRAM_RELAY_MAX_BODY_BYTES:
        raise _too_large()
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > DEGRAM_RELAY_MAX_BODY_BYTES:
            raise _too_large()
        chunks.append(chunk)
    return b"".join(chunks)


def _policy_deny(reason: str) -> HTTPException:
    return relay_error(
        403,
        "POLICY_DENY",
        "DG policy does not allow sending this data to the model.",
        "Narrow the context or ask the project owner. Confirming does not override a policy.",
        reason=reason,
    )


def _check_export_policy(request: Request, project: str) -> str:
    """Provider-export policy, context scope and whole-definition consent, in
    that order, all before any upstream contact. Returns the context scope.
    A policy deny is terminal: consent is only consulted once the policy
    already allows the scope."""
    policy = degram_policy.policy_for_project(project)
    if not policy["providerExportAllowed"]:
        raise _policy_deny("provider-export-not-allowed")
    scope = (request.headers.get(HEADER_CONTEXT_SCOPE) or SCOPE_SELECTION).strip().lower()
    if scope not in CONTEXT_SCOPES:
        raise relay_error(
            422,
            "CONTEXT_SCOPE_INVALID",
            "The context scope is not recognised.",
            f"Use one of: {', '.join(CONTEXT_SCOPES)}.",
        )
    if scope == SCOPE_WHOLE_DEFINITION:
        if not policy["wholeDefinitionAllowed"]:
            raise _policy_deny("whole-definition-not-allowed")
        consent = (request.headers.get(HEADER_WHOLE_DEFINITION_CONSENT) or "").strip().lower()
        if consent not in _CONSENT_VALUES:
            raise relay_error(
                428,
                "CONSENT_REQUIRED",
                "Sending the whole definition needs the user's confirmation.",
                f"Confirm in the client and resend with {HEADER_WHOLE_DEFINITION_CONSENT}: true.",
            )
    return scope


async def _read_json_body(request: Request) -> tuple[dict[str, Any], int]:
    raw = await _read_capped_body(request)
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or not isinstance(messages, list)
        or not messages
        or not all(isinstance(m, dict) for m in messages)
    ):
        raise relay_error(
            422,
            "RELAY_REQUEST_INVALID",
            "The request body is not a valid chat completion request.",
            "Send a JSON object with a non-empty messages list of objects.",
        )
    return payload, len(raw)


async def relay_chat_completions(request: Request) -> StreamingResponse:
    """``POST /degram/v1/chat/completions`` (route policy: delegated only)."""
    principal = getattr(request.state, "principal", None)
    if getattr(principal, "kind", None) != "delegated":
        raise relay_error(
            403,
            "PRINCIPAL_NOT_PERMITTED",
            "Not authorized for this operation.",
            "Use a delegated token minted for the project.",
        )
    project = principal.bound_project
    scope = _check_export_policy(request, project)
    payload, payload_bytes = await _read_json_body(request)

    config = resolve_runtime_config()
    if config is None:
        raise relay_error(
            503,
            OUTCOME_RELAY_NOT_CONFIGURED,
            "The DeGram model relay is not configured.",
            "Ask an administrator to set the relay endpoint and key.",
        )

    capture = StreamCapture()
    adapter = DegramRelayAdapter(config, capture=capture)
    provenance: dict[str, Any] = {
        "timestamp": _now_iso(),
        "requestedProvider": config.provider_label,
        "requestedModel": config.model,
        "username": principal.username,
        "project": project,
        "company": principal.company,
        "payloadBytes": payload_bytes,
        "contextScope": scope,
        "toolCount": len(payload["tools"]) if isinstance(payload.get("tools"), list) else 0,
    }

    def finish(outcome: str) -> None:
        provenance.update(
            outcome=outcome,
            servedModel=capture.served_model,
            responseId=capture.response_id,
            systemFingerprint=capture.fingerprint,
            usage=capture.usage,
        )
        append_provenance(provenance)

    stream = adapter.stream_chat(
        payload["messages"], payload.get("tools"), payload.get("tool_choice"), extra=payload
    )
    try:
        first = await stream.__anext__()
    except RelayError as exc:
        finish(exc.code)
        raise exc.to_http() from exc
    except StopAsyncIteration:
        finish(OUTCOME_PROVIDER_ERROR)
        raise relay_error(
            502,
            OUTCOME_PROVIDER_ERROR,
            "The model provider returned an empty stream.",
            "Try again later.",
        ) from None

    async def body() -> AsyncIterator[str]:
        outcome = OUTCOME_COMPLETED
        try:
            pending: str | None = first
            while pending is not None:
                yield pending + "\n"
                try:
                    pending = await stream.__anext__()
                except StopAsyncIteration:
                    pending = None
        except RelayError as exc:
            outcome = exc.code
            yield _error_event(exc)
        finally:
            await stream.aclose()
            finish(outcome)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
