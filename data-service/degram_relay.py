"""DeGram LLM relay (Phase 1301 plan 08, D-16, DGCL-02, DGCL-05, DGCL-06, DGCL-07).

``POST /degram/v1/chat/completions`` is the ONLY model path of the local DeGram
agent. It is user-scoped (a delegated ``dgd_`` principal only), streaming and
OpenAI-compatible:

* The upstream is the ONE endpoint of the DG Web UI LLM settings
  (``llm-settings.json``, owner decision 2026-10-06 amending D-16): provider
  type ``openai`` (OpenAI or an OpenAI-compatible base URL), its model and its
  system key, Fernet-encrypted at rest with the LLM gateway's master secret.
  The relay has no config file of its own and does not use
  ``llm_gateway.resolve_active_provider``: a non-OpenAI provider leaves it
  unconfigured, and there is NO fallback to another provider, to Ollama or to a
  different model.
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

import asyncio
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

import anyio
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

import degram_policy
from llm_gateway import LLM_SETTINGS_FILE, decrypt_value, load_persisted_llm_settings, mask_key

_LOGGER = logging.getLogger(__name__)

RELAY_ROUTE = "/degram/v1/chat/completions"
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

# Request fields forwarded to the upstream besides messages/tools/tool_choice.
# ``model``, ``provider`` and ``stream`` are never forwarded from the client.
_PASSTHROUGH_FIELDS = ("temperature", "top_p", "max_tokens", "max_completion_tokens", "stop")

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Timeouts (D-18, T-1301-08-04). Read at call time so tests can shorten them.
DEGRAM_RELAY_CONNECT_TIMEOUT_S = 10
DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S = 60
DEGRAM_RELAY_TOTAL_TIMEOUT_S = 300
EXCERPT_LIMIT = 2048  # bytes of an upstream error body echoed to the client
EXCERPT_READ_TIMEOUT_S = 5

# Operational outcomes (NOT evaluator verdicts; spec/degram/OPERATIONAL-OUTCOMES.md).
OUTCOME_COMPLETED = "COMPLETED"
OUTCOME_CANCELLED = "CANCELLED"
OUTCOME_PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
OUTCOME_PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
OUTCOME_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
OUTCOME_PROVIDER_ERROR = "PROVIDER_ERROR"
OUTCOME_RELAY_NOT_CONFIGURED = "RELAY_NOT_CONFIGURED"
OUTCOME_POLICY_DENY = "POLICY_DENY"
OUTCOME_CONSENT_REQUIRED = "CONSENT_REQUIRED"

RELAY_OUTCOMES = frozenset(
    {
        OUTCOME_COMPLETED,
        OUTCOME_CANCELLED,
        OUTCOME_PROVIDER_TIMEOUT,
        OUTCOME_PROVIDER_RATE_LIMITED,
        OUTCOME_PROVIDER_UNAVAILABLE,
        OUTCOME_PROVIDER_ERROR,
        OUTCOME_RELAY_NOT_CONFIGURED,
        OUTCOME_POLICY_DENY,
        OUTCOME_CONSENT_REQUIRED,
    }
)
# Reported by the DG Canvas / Revit bridges (plans 1301-06, 1301-07, 1301-11).
BRIDGE_OUTCOMES = frozenset(
    {
        "BUSY",
        "BRIDGE_OFF",
        "EXTENSION_NOT_LOADED",
        "ROUTES_DISABLED",
        "ROUTES_NOT_LOOPBACK",
        "SETUP_INCOMPLETE",
        "IDENTITY_MISMATCH",
        "DOCUMENT_NOT_OPEN",
    }
)
# Reported by the local agent (plans 1301-10, 1301-11).
AGENT_OUTCOMES = frozenset(
    {
        "CREDENTIALS_MISSING",
        "CREDENTIALS_EXPIRED",
        "DEGRAM_LOCKED",
        "SCOPE_NOT_SUPPORTED",
        "DG_UNAVAILABLE",
        "ACCESS_DENIED",
    }
)
# The closed operational vocabulary. It is disjoint from the eight canonical
# evaluator statuses (spec/evidence-contract.schema.json CanonicalStatus), which
# stay untouched: an operational outcome is never a verdict.
OPERATIONAL_OUTCOMES = frozenset(RELAY_OUTCOMES | BRIDGE_OUTCOMES | AGENT_OUTCOMES)

_PROVENANCE_LOCK = threading.Lock()


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


# -- operator config: the Web UI LLM settings (llm-settings.json) ----------------
#
# Owner decision 2026-10-06 (amends 1301 D-16): the relay has no config of its
# own. Its endpoint, model and system key are the ones the operator entered in
# the DG Web UI LLM settings (PUT /llm/settings). The relay speaks OpenAI chat
# completions with streaming and tools, so only the `openai` provider type
# (OpenAI or any OpenAI-compatible base URL) is runnable; anything else leaves
# the relay unconfigured. Nothing falls back.

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
CONFIG_SOURCE = "llm-settings"


def _data_dir() -> Path:
    return Path(os.getenv("DG_DATA_DIR", "/app/data"))


def gateway_settings_path() -> Path:
    """The Web UI LLM settings file, resolved per call (llm_gateway resolves its
    own copy once at import)."""
    return _data_dir() / LLM_SETTINGS_FILE.name


def provenance_path() -> Path:
    return _data_dir() / PROVENANCE_FILE_NAME


def _master_secret() -> str:
    return os.getenv("LLM_MASTER_SECRET", "")


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


@dataclass(frozen=True)
class RelayConfig:
    base_url: str
    model: str
    provider_label: str
    api_key: str = ""

    def __repr__(self) -> str:  # never print the key
        return f"RelayConfig(base_url={self.base_url!r}, model={self.model!r}, provider_label={self.provider_label!r})"


def _resolve() -> tuple[RelayConfig | None, str, dict[str, str]]:
    """(runnable config or None, reason, settings). Reasons: ``ok``,
    ``incomplete``, ``provider-not-openai-compatible``, ``base-url-invalid``,
    ``key-unreadable``."""
    settings = load_persisted_llm_settings(gateway_settings_path())
    secret = _master_secret()
    if not settings.get("model") or not settings.get("apiKey") or not secret:
        return None, "incomplete", settings
    if settings.get("provider") != "openai":
        return None, "provider-not-openai-compatible", settings
    try:
        base_url = validate_base_url(settings.get("baseUrl") or OPENAI_DEFAULT_BASE_URL)
    except ValueError:
        return None, "base-url-invalid", settings
    try:
        key = decrypt_value(settings["apiKey"], secret)
    except Exception:  # noqa: BLE001 - wrong secret / corrupt token == not configured
        return None, "key-unreadable", settings
    label = urlparse(base_url).hostname or "openai"
    return RelayConfig(base_url=base_url, model=settings["model"], provider_label=label, api_key=key), "ok", settings


def resolve_runtime_config() -> RelayConfig | None:
    """The runnable config with the key decrypted, or None when the Web UI LLM
    settings do not describe a runnable OpenAI-compatible endpoint."""
    return _resolve()[0]


def masked_config() -> dict[str, Any]:
    """Operator-facing view of the effective relay config: never the key."""
    config, reason, settings = _resolve()
    view: dict[str, Any] = {
        "configured": config is not None,
        "source": CONFIG_SOURCE,
        "baseUrl": config.base_url if config else settings.get("baseUrl"),
        "model": settings.get("model"),
        "providerLabel": config.provider_label if config else None,
        "apiKeyPreview": mask_key(config.api_key) if config else "",
    }
    if config is None:
        view["reason"] = reason
    return view


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


@dataclass(frozen=True)
class RelayTimeouts:
    connect: float
    first_byte: float
    total: float

    @classmethod
    def current(cls) -> "RelayTimeouts":
        return cls(
            DEGRAM_RELAY_CONNECT_TIMEOUT_S,
            DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S,
            DEGRAM_RELAY_TOTAL_TIMEOUT_S,
        )


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
        timeouts: RelayTimeouts | None = None,
    ) -> AsyncIterator[str]:
        """Yield the upstream SSE lines (without the trailing newline, blank
        separators included) while recording model/id/usage. Raises
        :class:`RelayError` with a named outcome. Exactly one upstream call, no
        retry. Closing the generator closes the upstream response."""
        limits = timeouts or RelayTimeouts.current()
        payload = self.build_payload(messages, tools, tool_choice, extra)
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "text/event-stream",
        }
        started = time.monotonic()
        total_deadline = started + limits.total
        first_deadline = started + min(limits.first_byte, limits.total)

        def remaining(deadline: float) -> float:
            return max(0.0, deadline - time.monotonic())

        client = httpx.AsyncClient(
            transport=_transport_factory(),
            follow_redirects=False,  # a redirect would carry the key elsewhere
            timeout=httpx.Timeout(limits.total, connect=limits.connect),
        )
        response: httpx.Response | None = None
        try:
            try:
                request = client.build_request("POST", url, json=payload, headers=headers)
                response = await asyncio.wait_for(
                    client.send(request, stream=True), timeout=remaining(first_deadline)
                )
            except (TimeoutError, httpx.TimeoutException) as exc:
                raise _timeout_error("first-byte") from exc
            except httpx.HTTPError as exc:
                raise _unavailable_error() from exc

            if not 200 <= response.status_code < 300:
                raise await self._status_error(response)

            lines = response.aiter_lines().__aiter__()
            seen_first = False
            while True:
                deadline = total_deadline if seen_first else min(first_deadline, total_deadline)
                try:
                    line = await asyncio.wait_for(lines.__anext__(), timeout=remaining(deadline))
                except StopAsyncIteration:
                    return
                except (TimeoutError, httpx.TimeoutException) as exc:
                    raise _timeout_error("total" if seen_first else "first-byte") from exc
                except httpx.HTTPError as exc:
                    raise _unavailable_error() from exc
                seen_first = True
                self.capture.feed(line)
                yield line
        finally:
            with anyio.CancelScope(shield=True):
                if response is not None:
                    await response.aclose()
                await client.aclose()

    async def _status_error(self, response: httpx.Response) -> RelayError:
        status = response.status_code
        if status == 429:
            retry_after = _parse_retry_after(response.headers.get("retry-after"))
            return RelayError(
                OUTCOME_PROVIDER_RATE_LIMITED,
                status=429,
                error="The model provider is rate limiting requests.",
                hint="Wait and try again.",
                extra={"retryAfter": retry_after},
                headers={"Retry-After": str(retry_after)} if retry_after is not None else None,
            )
        if status >= 500:
            return _unavailable_error()
        excerpt = await _read_excerpt(response, self.config.api_key)
        return RelayError(
            OUTCOME_PROVIDER_ERROR,
            status=502,
            error="The model provider refused the request.",
            hint="Ask an administrator to check the relay configuration.",
            extra={"upstreamStatus": status, "upstreamExcerpt": excerpt},
        )


def _parse_retry_after(value: str | None) -> int | None:
    """Seconds from a numeric ``Retry-After``; None for absent or an HTTP-date."""
    if value is None:
        return None
    cleaned = value.strip()
    return int(cleaned) if cleaned.isdigit() and len(cleaned) <= 9 else None


async def _read_excerpt(response: httpx.Response, api_key: str) -> str:
    """At most ``EXCERPT_LIMIT`` bytes of the upstream error body, decoded
    leniently, with the key scrubbed. Reading is itself time-boxed."""
    buffer = bytearray()

    async def collect() -> None:
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            if len(buffer) >= EXCERPT_LIMIT:
                return

    try:
        await asyncio.wait_for(collect(), timeout=EXCERPT_READ_TIMEOUT_S)
    except (TimeoutError, httpx.HTTPError):
        pass
    text = bytes(buffer[:EXCERPT_LIMIT]).decode("utf-8", errors="ignore")
    if api_key:
        text = text.replace(api_key, "***")
    return text.encode("utf-8")[:EXCERPT_LIMIT].decode("utf-8", errors="ignore")


def _timeout_error(kind: str) -> RelayError:
    return RelayError(
        OUTCOME_PROVIDER_TIMEOUT,
        status=504,
        error="The model provider did not answer in time.",
        hint="Try again, or narrow the context.",
        extra={"timeout": kind},
    )


def _unavailable_error() -> RelayError:
    return RelayError(
        OUTCOME_PROVIDER_UNAVAILABLE,
        status=503,
        error="The model provider is unavailable.",
        hint="Try again later.",
    )


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
    except asyncio.CancelledError:
        finish(OUTCOME_CANCELLED)
        raise
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
                # D-18: between chunks, a vanished client ends the upstream call.
                if await request.is_disconnected():
                    outcome = OUTCOME_CANCELLED
                    break
                yield pending + "\n"
                try:
                    pending = await stream.__anext__()
                except StopAsyncIteration:
                    pending = None
        except RelayError as exc:
            outcome = exc.code
            yield _error_event(exc)
        except (asyncio.CancelledError, GeneratorExit):
            outcome = OUTCOME_CANCELLED
            raise
        finally:
            with anyio.CancelScope(shield=True):
                await stream.aclose()  # closes the upstream response
            finish(outcome)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
