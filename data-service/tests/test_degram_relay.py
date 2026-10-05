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
                 first_delay=0.0, chunk_delay=0.0, hang=False):
        self.chunks = list(DEFAULT_CHUNKS if chunks is None else chunks)
        self.status = status
        self.headers = dict(headers or {})
        self.body = body
        self.raises = raises
        self.first_delay = first_delay
        self.chunk_delay = chunk_delay
        self.hang = hang
        self.requests: list[httpx.Request] = []
        self.sent_chunks = 0
        self.closed = 0

    def transport(self):
        return httpx.MockTransport(self._handle)

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
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
        for chunk in self.up.chunks:
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


@pytest.fixture
def world(client, upstream):
    company.set_project_company("P1", "Acme")
    _configure(client)
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
