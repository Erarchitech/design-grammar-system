"""Phase 1301 plan 08 (DGCL-02, DGCL-05, DGCL-06, DGCL-07, D-16, D-17, D-18): the
user-scoped, streaming, OpenAI-compatible DeGram relay.

Every upstream is an ``httpx.MockTransport`` injected through the module-level
``degram_relay._transport_factory``: no test opens a network connection, calls a
model provider or reads a real key. Credentials come from the 1205-08 fixtures
(real sessions, a real ``dgd_`` delegated token); nothing is overridden.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import company  # noqa: E402
import connectors  # noqa: E402
import degram_policy  # noqa: E402
import degram_relay  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402
from llm_gateway import decrypt_value  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"
ADMIN = "root@dg.local"
SYSTEM_KEY = "sk-genpro-system-key-0123456789abcdef"
PROMPT_TEXT = "SECRET-PROMPT-TEXT the relay must never record"
BASE_URL = "https://genpro.example/v1"
RELAY_PATH = "/degram/v1/chat/completions"


# -- upstream double ----------------------------------------------------------


def sse(obj) -> bytes:
    payload = obj if isinstance(obj, str) else json.dumps(obj)
    return f"data: {payload}\n\n".encode()


DEFAULT_CHUNKS = [
    sse({"id": "chatcmpl-7", "model": "served-model-x", "system_fingerprint": "fp_abc",
         "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hel"}}]}),
    sse({"id": "chatcmpl-7", "model": "served-model-x",
         "choices": [{"index": 0, "delta": {"content": "lo"}}]}),
    sse({"id": "chatcmpl-7", "model": "served-model-x", "choices": [],
         "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}),
    sse("[DONE]"),
]


class FakeUpstream:
    """A network-free provider. Counts requests and stream closes."""

    def __init__(self, chunks=None, *, status=200, headers=None, body=b"", raises=None,
                 first_delay=0.0, chunk_delay=0.0, hang=False, handler_delay=0.0,
                 fail_after=None):
        self.chunks = list(DEFAULT_CHUNKS if chunks is None else chunks)
        self.status = status
        self.headers = dict(headers or {})
        self.body = body
        self.raises = raises
        self.first_delay = first_delay
        self.chunk_delay = chunk_delay
        self.hang = hang
        self.handler_delay = handler_delay
        self.fail_after = fail_after
        self.requests: list[httpx.Request] = []
        self.sent_chunks = 0
        self.closed = 0

    def transport(self):
        return httpx.MockTransport(self._handle)

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.handler_delay:
            await asyncio.sleep(self.handler_delay)
        if self.raises is not None:
            raise self.raises
        if self.status != 200:
            return httpx.Response(self.status, headers=self.headers, content=self.body)
        return httpx.Response(
            200, headers={"content-type": "text/event-stream", **self.headers}, stream=_Stream(self)
        )

    def upstream_json(self, index=0):
        return json.loads(self.requests[index].content)


class _Stream(httpx.AsyncByteStream):
    def __init__(self, upstream: FakeUpstream):
        self.up = upstream

    async def __aiter__(self):
        if self.up.hang:
            await asyncio.sleep(3600)
        if self.up.first_delay:
            await asyncio.sleep(self.up.first_delay)
        for index, chunk in enumerate(self.up.chunks):
            if self.up.fail_after is not None and index >= self.up.fail_after:
                raise httpx.ReadError("connection reset by the fake upstream")
            self.up.sent_chunks += 1
            yield chunk
            await asyncio.sleep(self.up.chunk_delay)

    async def aclose(self):
        self.up.closed += 1


# -- fixtures -------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(app_module, "read_many", lambda *a, **k: [])
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.setenv("DG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LLM_MASTER_SECRET", "test-master-secret")
    monkeypatch.setattr(degram_relay, "_transport_factory", lambda: None)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def upstream(monkeypatch):
    fake = FakeUpstream()
    monkeypatch.setattr(degram_relay, "_transport_factory", fake.transport)
    return fake


def _cookie(username=ALICE, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _detail(response):
    return response.json().get("detail")


def _configure(client, **overrides):
    payload = {"baseUrl": BASE_URL, "model": "mimo-v2.5-pro", "providerLabel": "genpro",
               "apiKey": SYSTEM_KEY, **overrides}
    response = client.put("/degram/admin/llm-config", json=payload, headers=_cookie(ADMIN, admin=True))
    assert response.status_code == 200, response.text
    return response


def _delegated(client, project="P1", username=ALICE):
    cookie = _cookie(username, memberships={project: "editor"})
    response = client.post("/auth/delegated-token", json={"project": project}, headers=cookie)
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _body(**extra):
    body = {"messages": [{"role": "user", "content": PROMPT_TEXT}]}
    body.update(extra)
    return body


def _provenance():
    path = degram_relay.provenance_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _data_lines(text):
    return [line for line in text.splitlines() if line.startswith("data:")]


def _allow(project="P1", *, whole=False):
    degram_policy.set_policy(
        project, provider_export_allowed=True, whole_definition_allowed=whole
    )


@pytest.fixture
def world(client, upstream):
    company.set_project_company("P1", "Acme")
    _configure(client)
    _allow("P1")
    return {"token": _delegated(client), "upstream": upstream}


# -- operator config -------------------------------------------------------------


def test_config_put_is_admin_only(client):
    member = _cookie(ALICE, memberships={"P1": "owner"})
    payload = {"baseUrl": BASE_URL, "apiKey": SYSTEM_KEY}
    denied = client.put("/degram/admin/llm-config", json=payload, headers=member)
    assert denied.status_code == 403 and _code(denied) == "ADMIN_REQUIRED"
    assert client.put("/degram/admin/llm-config", json=payload).status_code == 401
    denied_get = client.get("/degram/admin/llm-config", headers=member)
    assert denied_get.status_code == 403 and _code(denied_get) == "ADMIN_REQUIRED"


def test_config_put_get_masks_the_key_and_encrypts_it_at_rest(client):
    put = _configure(client)
    assert SYSTEM_KEY not in put.text
    got = client.get("/degram/admin/llm-config", headers=_cookie(ADMIN, admin=True))
    assert got.status_code == 200
    body = got.json()
    assert SYSTEM_KEY not in got.text
    assert body["configured"] is True
    assert body["baseUrl"] == BASE_URL
    assert body["model"] == "mimo-v2.5-pro"
    assert body["providerLabel"] == "genpro"
    assert body["apiKeyPreview"] and body["apiKeyPreview"] != SYSTEM_KEY
    stored = json.loads(degram_relay.config_path().read_text(encoding="utf-8"))
    assert stored["apiKey"] != SYSTEM_KEY and SYSTEM_KEY not in json.dumps(stored)
    assert decrypt_value(stored["apiKey"], "test-master-secret") == SYSTEM_KEY
    assert degram_relay.config_path().name == "degram-llm.json"
    assert not list(degram_relay.config_path().parent.glob("*.tmp"))


def test_config_defaults_model_and_keeps_key_when_omitted(client):
    _configure(client, model=None, providerLabel=None)
    admin = _cookie(ADMIN, admin=True)
    body = client.get("/degram/admin/llm-config", headers=admin).json()
    assert body["model"] == "mimo-v2.5-pro" and body["providerLabel"] == "genpro"
    again = client.put("/degram/admin/llm-config", json={"model": "other-model"}, headers=admin)
    assert again.status_code == 200 and again.json()["model"] == "other-model"
    stored = json.loads(degram_relay.config_path().read_text(encoding="utf-8"))
    assert decrypt_value(stored["apiKey"], "test-master-secret") == SYSTEM_KEY


@pytest.mark.parametrize(
    "base_url",
    ["http://genpro.example/v1", "ftp://x.example", "https://user:pw@genpro.example/v1",
     "https://genpro.example/v1?x=1", "not a url", "https://"],
)
def test_config_rejects_unsafe_base_urls(client, base_url):
    response = client.put(
        "/degram/admin/llm-config",
        json={"baseUrl": base_url, "apiKey": SYSTEM_KEY},
        headers=_cookie(ADMIN, admin=True),
    )
    assert response.status_code == 422, response.text
    assert _code(response) == "RELAY_CONFIG_INVALID"
    assert not degram_relay.config_path().exists()


def test_config_accepts_localhost_over_http(client):
    response = client.put(
        "/degram/admin/llm-config",
        json={"baseUrl": "http://localhost:8123/v1/", "apiKey": SYSTEM_KEY},
        headers=_cookie(ADMIN, admin=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["baseUrl"] == "http://localhost:8123/v1"


def test_first_config_needs_url_and_key(client):
    admin = _cookie(ADMIN, admin=True)
    for payload in ({"model": "m"}, {"baseUrl": BASE_URL}, {"apiKey": SYSTEM_KEY}):
        response = client.put("/degram/admin/llm-config", json=payload, headers=admin)
        assert response.status_code == 422 and _code(response) == "RELAY_CONFIG_INVALID"


def test_get_config_before_setup_reports_unconfigured(client):
    body = client.get("/degram/admin/llm-config", headers=_cookie(ADMIN, admin=True)).json()
    assert body["configured"] is False and body["apiKeyPreview"] == ""


# -- principal scope ---------------------------------------------------------------


def test_relay_without_config_is_503_before_streaming(client, upstream):
    _allow("P1")
    token = _delegated(client)
    response = client.post(RELAY_PATH, json=_body(), headers=_bearer(token))
    assert response.status_code == 503, response.text
    assert _code(response) == "RELAY_NOT_CONFIGURED"
    assert not response.headers["content-type"].startswith("text/event-stream")
    assert upstream.requests == []


def test_relay_refuses_every_non_delegated_principal(client, upstream):
    _configure(client)
    plain = _cookie(ALICE, memberships={"P1": "owner"})
    admin = _cookie(ADMIN, admin=True)
    connector = {"Authorization": f"Bearer {auth_fixtures.connector_token_for('P1')}"}
    for headers in (plain, admin, connector, auth_fixtures.service_headers()):
        response = client.post(RELAY_PATH, json=_body(), headers=headers)
        assert response.status_code == 403, (headers, response.text)
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"
    assert client.post(RELAY_PATH, json=_body()).status_code == 401
    assert upstream.requests == []


def test_relay_route_is_not_reachable_through_the_legacy_llm_prefix(client, world):
    for path in ("/llm/degram/v1/chat/completions", "/llm/v1/chat/completions"):
        response = client.post(path, json=_body(), headers=_bearer(world["token"]))
        assert response.status_code in (403, 404, 405)
    assert world["upstream"].requests == []


# -- happy path --------------------------------------------------------------------


def test_relay_streams_upstream_sse_verbatim_and_overrides_model(client, world):
    tools = [{"type": "function", "function": {"name": "dg_get_graph", "parameters": {"type": "object"}}}]
    response = client.post(
        RELAY_PATH,
        json=_body(model="gpt-4-client-pick", provider="openai", stream=False, tools=tools,
                   tool_choice="auto", temperature=0.2),
        headers=_bearer(world["token"]),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.text.encode() == b"".join(DEFAULT_CHUNKS)
    assert SYSTEM_KEY not in response.text

    upstream = world["upstream"]
    assert len(upstream.requests) == 1
    sent = upstream.requests[0]
    assert str(sent.url) == "https://genpro.example/v1/chat/completions"
    assert sent.headers["authorization"] == f"Bearer {SYSTEM_KEY}"
    payload = upstream.upstream_json()
    assert payload["model"] == "mimo-v2.5-pro"
    assert payload["stream"] is True
    assert payload["tools"] == tools and payload["tool_choice"] == "auto"
    assert payload["temperature"] == 0.2
    assert "provider" not in payload
    assert payload["messages"][0]["content"] == PROMPT_TEXT
    assert upstream.closed == 1


def test_relay_records_provenance_without_content_or_key(client, world):
    body = _body(model="client-pick")
    raw = json.dumps(body)
    response = client.post(RELAY_PATH, content=raw, headers={**_bearer(world["token"]),
                                                              "content-type": "application/json"})
    assert response.status_code == 200
    records = _provenance()
    assert len(records) == 1
    record = records[0]
    assert record["requestedProvider"] == "genpro"
    assert record["requestedModel"] == "mimo-v2.5-pro"
    assert record["servedModel"] == "served-model-x"
    assert record["responseId"] == "chatcmpl-7"
    assert record["systemFingerprint"] == "fp_abc"
    assert record["usage"] == {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
    assert record["outcome"] == "COMPLETED"
    assert record["username"] == ALICE
    assert record["project"] == "P1"
    assert record["company"] == "Acme"
    assert record["payloadBytes"] == len(raw.encode())
    assert record["timestamp"].endswith("Z")
    text = degram_relay.provenance_path().read_text(encoding="utf-8")
    assert PROMPT_TEXT not in text and SYSTEM_KEY not in text
    assert degram_relay.provenance_path().name == "degram-llm-provenance.jsonl"


def test_provenance_served_model_is_null_when_upstream_omits_it(client, world):
    world["upstream"].chunks = [sse({"choices": [{"delta": {"content": "x"}}]}), sse("[DONE]")]
    client.post(RELAY_PATH, json=_body(), headers=_bearer(world["token"]))
    record = _provenance()[0]
    assert record["servedModel"] is None
    assert record["responseId"] is None
    assert record["usage"] is None


def test_relay_rejects_a_malformed_body(client, world):
    headers = {**_bearer(world["token"]), "content-type": "application/json"}
    for raw in ("not json", "[]", json.dumps({"messages": []}), json.dumps({"messages": "x"}),
                json.dumps({"messages": [1]})):
        response = client.post(RELAY_PATH, content=raw, headers=headers)
        assert response.status_code == 422, (raw, response.text)
        assert _code(response) == "RELAY_REQUEST_INVALID"
    assert world["upstream"].requests == []


# -- provider-export policy, whole-definition consent, scope denies (task 2) ----------

SCOPE = "X-DeGram-Context-Scope"
CONSENT = "X-DeGram-Whole-Definition-Consent"


def _relay(client, token, *, headers=None, body=None):
    return client.post(RELAY_PATH, json=body or _body(), headers={**_bearer(token), **(headers or {})})


def test_export_policy_defaults_to_deny_and_nothing_reaches_the_provider(client, upstream):
    _configure(client)
    token = _delegated(client)  # no policy row for P1: deny by default
    response = _relay(client, token)
    assert response.status_code == 403, response.text
    assert _code(response) == "POLICY_DENY"
    assert _detail(response)["reason"] == "provider-export-not-allowed"
    assert upstream.requests == []
    assert _provenance() == []


def test_consent_header_never_overrides_a_policy_deny(client, upstream):
    _configure(client)
    token = _delegated(client)
    for headers in ({CONSENT: "true"}, {SCOPE: "whole-definition", CONSENT: "true"}):
        response = _relay(client, token, headers=headers)
        assert response.status_code == 403
        assert _code(response) == "POLICY_DENY"
        assert _detail(response)["reason"] == "provider-export-not-allowed"
    assert upstream.requests == []


def test_a_policy_change_takes_effect_on_the_next_request(client, world):
    assert _relay(client, world["token"]).status_code == 200
    degram_policy.set_policy("P1", provider_export_allowed=False)
    denied = _relay(client, world["token"])
    assert denied.status_code == 403 and _code(denied) == "POLICY_DENY"
    assert len(world["upstream"].requests) == 1


def test_policy_of_another_project_does_not_allow_this_one(client, upstream):
    _configure(client)
    _allow("P2")
    token = _delegated(client, project="P1")
    response = _relay(client, token)
    assert response.status_code == 403 and _code(response) == "POLICY_DENY"
    assert upstream.requests == []


def test_whole_definition_without_policy_is_a_deny_even_with_consent(client, world):
    for headers in ({SCOPE: "whole-definition"}, {SCOPE: "whole-definition", CONSENT: "true"}):
        response = _relay(client, world["token"], headers=headers)
        assert response.status_code == 403, response.text
        assert _code(response) == "POLICY_DENY"
        assert _detail(response)["reason"] == "whole-definition-not-allowed"
    assert world["upstream"].requests == []


def test_whole_definition_with_policy_needs_the_consent_header(client, world):
    _allow("P1", whole=True)
    for headers in ({SCOPE: "whole-definition"}, {SCOPE: "whole-definition", CONSENT: "false"},
                    {SCOPE: "whole-definition", CONSENT: ""}):
        response = _relay(client, world["token"], headers=headers)
        assert response.status_code == 428, (headers, response.text)
        assert _code(response) == "CONSENT_REQUIRED"
    assert world["upstream"].requests == []


def test_whole_definition_with_policy_and_consent_is_relayed_and_recorded(client, world):
    _allow("P1", whole=True)
    response = _relay(client, world["token"], headers={SCOPE: "Whole-Definition", CONSENT: "true"})
    assert response.status_code == 200, response.text
    assert len(world["upstream"].requests) == 1
    assert _provenance()[0]["contextScope"] == "whole-definition"


def test_default_and_selection_scope_need_no_consent(client, world):
    assert _relay(client, world["token"]).status_code == 200
    assert _relay(client, world["token"], headers={SCOPE: "selection"}).status_code == 200
    assert _relay(client, world["token"], headers={SCOPE: "none"}).status_code == 200
    scopes = [record["contextScope"] for record in _provenance()]
    assert scopes == ["selection", "selection", "none"]


def test_unknown_scope_value_is_refused_before_the_provider(client, world):
    response = _relay(client, world["token"], headers={SCOPE: "everything"})
    assert response.status_code == 422 and _code(response) == "CONTEXT_SCOPE_INVALID"
    assert world["upstream"].requests == []


def test_changed_company_is_refused_before_the_relay_runs(client, world):
    company.set_project_company("P1", "Other Co")
    response = _relay(client, world["token"])
    assert response.status_code == 403
    assert _code(response) == "DELEGATED_SCOPE_CHANGED"
    assert world["upstream"].requests == []
    assert _provenance() == []


def test_body_over_one_mebibyte_is_413_before_the_provider(client, world):
    assert degram_relay.DEGRAM_RELAY_MAX_BODY_BYTES == 1048576
    big = {"messages": [{"role": "user", "content": "x" * (1048576 + 10)}]}
    response = client.post(RELAY_PATH, json=big, headers=_bearer(world["token"]))
    assert response.status_code == 413, response.status_code
    assert _code(response) == "RELAY_BODY_TOO_LARGE"
    assert world["upstream"].requests == []


def test_body_at_the_limit_is_accepted(client, world):
    filler = "x" * 1000
    base = {"messages": [{"role": "user", "content": filler}]}
    overhead = len(json.dumps(base).encode()) - len(filler)
    raw = json.dumps({"messages": [{"role": "user", "content": "x" * (1048576 - overhead)}]})
    assert len(raw.encode()) == 1048576
    response = client.post(RELAY_PATH, content=raw,
                           headers={**_bearer(world["token"]), "content-type": "application/json"})
    assert response.status_code == 200, response.text


def test_content_length_over_the_limit_is_refused_without_reading_the_body(client, world):
    response = client.post(
        RELAY_PATH,
        content=b"{}",
        headers={**_bearer(world["token"]), "content-type": "application/json",
                 "content-length": str(1048576 + 1)},
    )
    assert response.status_code == 413
    assert world["upstream"].requests == []


# -- cancellation, timeouts, named failures, outcome vocabulary (task 3) ---------------

import re  # noqa: E402
from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTCOMES_SPEC = REPO_ROOT / "spec" / "degram" / "OPERATIONAL-OUTCOMES.md"
EVIDENCE_SCHEMA = REPO_ROOT / "spec" / "evidence-contract.schema.json"


def _last_event(text):
    """(event name or None, parsed data) of the final SSE event in `text`."""
    blocks = [b for b in text.split("\n\n") if b.strip()]
    block = blocks[-1]
    name = None
    data = None
    for line in block.splitlines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
    return name, (json.loads(data) if data and data != "[DONE]" else data)


def _many_chunks(n=60):
    head = [
        sse({"id": "chatcmpl-9", "model": "served-model-x", "choices": [{"delta": {"content": "a"}}]}),
        sse({"id": "chatcmpl-9", "model": "served-model-x", "choices": [],
             "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4}}),
    ]
    tail = [sse({"id": "chatcmpl-9", "model": "served-model-x",
                 "choices": [{"delta": {"content": "b"}}]}) for _ in range(n)]
    return head + tail + [sse("[DONE]")]


def _asgi_stream(token, body_obj, *, disconnect_after_body_messages):
    """Drive the real app with a raw ASGI call so the client can vanish
    mid-stream. Returns the list of messages the app sent."""
    raw = json.dumps(body_obj).encode()
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": RELAY_PATH, "raw_path": RELAY_PATH.encode(),
        "query_string": b"", "root_path": "",
        "headers": [
            (b"host", b"testserver"), (b"authorization", f"Bearer {token}".encode()),
            (b"content-type", b"application/json"), (b"content-length", str(len(raw)).encode()),
        ],
        "client": ("testclient", 50000), "server": ("testserver", 80),
    }
    sent: list[dict] = []
    state = {"body_delivered": False}

    def bodies():
        return sum(1 for m in sent if m["type"] == "http.response.body")

    async def receive():
        if not state["body_delivered"]:
            state["body_delivered"] = True
            return {"type": "http.request", "body": raw, "more_body": False}
        if bodies() >= disconnect_after_body_messages:
            return {"type": "http.disconnect"}
        await asyncio.sleep(3600)

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    return sent


def test_client_disconnect_closes_the_upstream_and_records_cancelled(client, world):
    up = world["upstream"]
    up.chunks = _many_chunks(60)
    up.chunk_delay = 0.005
    sent = _asgi_stream(world["token"], _body(), disconnect_after_body_messages=5)
    assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 200
    delivered = [m for m in sent if m["type"] == "http.response.body" and m.get("body")]
    assert 0 < len(delivered) < 30, len(delivered)
    assert up.closed == 1
    assert up.sent_chunks < len(up.chunks)
    assert len(up.requests) == 1
    record = _provenance()[0]
    assert record["outcome"] == "CANCELLED"
    assert record["usage"] == {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4}
    assert record["responseId"] == "chatcmpl-9"


def test_disconnect_stops_within_a_chunk_of_the_signal(client, world):
    up = world["upstream"]
    up.chunks = _many_chunks(200)
    up.chunk_delay = 0.002
    sent = _asgi_stream(world["token"], _body(), disconnect_after_body_messages=4)
    delivered = [m for m in sent if m["type"] == "http.response.body" and m.get("body")]
    # signal after 4 body messages; one more line may already be in flight
    assert len(delivered) <= 4 + 2


def test_connect_timeout_is_provider_timeout_and_not_retried(client, world):
    up = world["upstream"]
    up.raises = httpx.ConnectTimeout("connect timed out")
    response = _relay(client, world["token"])
    assert response.status_code == 504, response.text
    assert _code(response) == "PROVIDER_TIMEOUT"
    assert len(up.requests) == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_TIMEOUT"


def test_no_first_byte_in_time_is_provider_timeout(client, world, monkeypatch):
    monkeypatch.setattr(degram_relay, "DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S", 0.2)
    up = world["upstream"]
    up.hang = True
    response = _relay(client, world["token"])
    assert response.status_code == 504 and _code(response) == "PROVIDER_TIMEOUT"
    assert len(up.requests) == 1
    assert up.closed == 1


def test_slow_response_headers_count_against_the_first_byte_window(client, world, monkeypatch):
    monkeypatch.setattr(degram_relay, "DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S", 0.2)
    world["upstream"].handler_delay = 1.0
    response = _relay(client, world["token"])
    assert response.status_code == 504 and _code(response) == "PROVIDER_TIMEOUT"


def test_total_timeout_mid_stream_ends_with_a_degram_error_event(client, world, monkeypatch):
    monkeypatch.setattr(degram_relay, "DEGRAM_RELAY_FIRST_BYTE_TIMEOUT_S", 0.4)
    monkeypatch.setattr(degram_relay, "DEGRAM_RELAY_TOTAL_TIMEOUT_S", 0.5)
    up = world["upstream"]
    up.chunks = _many_chunks(100)
    up.chunk_delay = 0.1
    response = _relay(client, world["token"])
    assert response.status_code == 200  # streaming had already begun
    name, data = _last_event(response.text)
    assert name == "degram-error" and data["code"] == "PROVIDER_TIMEOUT"
    assert up.closed == 1 and len(up.requests) == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_TIMEOUT"


def test_upstream_429_is_rate_limited_with_retry_after(client, world):
    up = world["upstream"]
    up.status, up.headers = 429, {"Retry-After": "7"}
    response = _relay(client, world["token"])
    assert response.status_code == 429, response.text
    assert _code(response) == "PROVIDER_RATE_LIMITED"
    assert _detail(response)["retryAfter"] == 7
    assert response.headers["retry-after"] == "7"
    assert len(up.requests) == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_RATE_LIMITED"


@pytest.mark.parametrize("headers", [{}, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}])
def test_upstream_429_without_a_numeric_retry_after_has_null(client, world, headers):
    world["upstream"].status, world["upstream"].headers = 429, headers
    response = _relay(client, world["token"])
    assert response.status_code == 429
    assert _detail(response)["retryAfter"] is None


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_upstream_5xx_is_provider_unavailable(client, world, status):
    up = world["upstream"]
    up.status, up.body = status, b"boom"
    response = _relay(client, world["token"])
    assert response.status_code == 503, response.text
    assert _code(response) == "PROVIDER_UNAVAILABLE"
    assert len(up.requests) == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_UNAVAILABLE"


def test_unreachable_upstream_is_provider_unavailable(client, world):
    up = world["upstream"]
    up.raises = httpx.ConnectError("name resolution failed")
    response = _relay(client, world["token"])
    assert response.status_code == 503 and _code(response) == "PROVIDER_UNAVAILABLE"
    assert len(up.requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_other_4xx_is_provider_error_with_bounded_excerpt(client, world, status):
    up = world["upstream"]
    up.status = status
    up.body = ("bad request " + SYSTEM_KEY + " " + "z" * 10000).encode()
    response = _relay(client, world["token"])
    assert response.status_code == 502, response.text
    detail = _detail(response)
    assert detail["code"] == "PROVIDER_ERROR"
    assert detail["upstreamStatus"] == status
    assert 0 < len(detail["upstreamExcerpt"].encode()) <= 2048
    assert SYSTEM_KEY not in response.text
    assert len(up.requests) == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_ERROR"


def test_a_redirect_is_not_followed_and_is_provider_error(client, world):
    up = world["upstream"]
    up.status, up.headers = 302, {"Location": "https://elsewhere.example/steal"}
    response = _relay(client, world["token"])
    assert response.status_code == 502 and _code(response) == "PROVIDER_ERROR"
    assert len(up.requests) == 1


def test_error_after_streaming_began_is_a_final_degram_error_event(client, world):
    up = world["upstream"]
    up.fail_after = 1
    response = _relay(client, world["token"])
    assert response.status_code == 200
    name, data = _last_event(response.text)
    assert name == "degram-error"
    assert data["code"] == "PROVIDER_UNAVAILABLE"
    assert SYSTEM_KEY not in response.text
    assert len(up.requests) == 1 and up.closed == 1
    assert _provenance()[0]["outcome"] == "PROVIDER_UNAVAILABLE"


def test_exactly_one_upstream_call_per_request_across_failures(client, world):
    up = world["upstream"]
    up.status = 503
    for _ in range(3):
        _relay(client, world["token"])
    assert len(up.requests) == 3  # one per request, never a retry


def test_the_relay_never_falls_back_to_another_provider(client, world, monkeypatch):
    """A failing upstream must not trigger the LLM gateway, Ollama or any other
    network client: the only transport used is the relay's own factory."""
    import llm_gateway

    def explode(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("fallback path touched")

    monkeypatch.setattr(llm_gateway, "resolve_active_provider", explode)
    monkeypatch.setattr(llm_gateway, "get_adapter", explode)
    world["upstream"].status = 503
    response = _relay(client, world["token"])
    assert response.status_code == 503 and _code(response) == "PROVIDER_UNAVAILABLE"


def test_operational_outcomes_are_disjoint_from_the_canonical_statuses():
    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    canonical = {s.lower() for s in schema["$defs"]["CanonicalStatus"]["enum"]}
    assert len(canonical) == 8
    outcomes = {o.lower() for o in degram_relay.OPERATIONAL_OUTCOMES}
    assert outcomes and outcomes.isdisjoint(canonical)


def test_every_relay_outcome_the_code_emits_is_in_the_vocabulary():
    emitted = {
        degram_relay.OUTCOME_COMPLETED, degram_relay.OUTCOME_CANCELLED,
        degram_relay.OUTCOME_PROVIDER_TIMEOUT, degram_relay.OUTCOME_PROVIDER_RATE_LIMITED,
        degram_relay.OUTCOME_PROVIDER_UNAVAILABLE, degram_relay.OUTCOME_PROVIDER_ERROR,
        degram_relay.OUTCOME_RELAY_NOT_CONFIGURED, "POLICY_DENY", "CONSENT_REQUIRED",
    }
    assert emitted <= degram_relay.OPERATIONAL_OUTCOMES
    assert degram_relay.RELAY_OUTCOMES == emitted


def test_outcomes_spec_lists_exactly_the_vocabulary():
    text = OUTCOMES_SPEC.read_text(encoding="utf-8")
    assert "PROVIDER_TIMEOUT" in text and "IDENTITY_MISMATCH" in text
    start = "<!-- degram-outcomes:codes:start -->"
    end = "<!-- degram-outcomes:codes:end -->"
    assert text.count(start) == 1 and text.count(end) == 1
    block = text[text.index(start) + len(start): text.index(end)]
    codes = {line.strip() for line in block.splitlines() if line.strip() and not line.startswith("```")}
    assert codes == set(degram_relay.OPERATIONAL_OUTCOMES)
    # The spec states the vocabulary is not an evaluator verdict set.
    assert "never evaluator verdicts" in text.replace("\n", " ")
