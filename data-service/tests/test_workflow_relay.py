"""Workflow relay routes (Phase 1205 plan 14, ALGN12-17/ALGN12-18; D-04, D-08).

Covers ``fire_n8n_webhook`` (service-token header, fail-closed on an unset
token, ack parsing), ``call_n8n_sync`` (still returns the completed payload and
now sends the header), the two relay routes (project authorisation, body built
only from the validated request, 202 ack) and owner-bound result polling --
including the two-users-at-once concurrency edge.

``urllib.request.urlopen`` is monkeypatched to a fake that records the Request;
no test contacts n8n. Every credential is a real session minted through the
1205-08 fixtures (D-20); nothing patches ``require_principal``.
"""

from __future__ import annotations

import json
import os
import sys
import threading

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
FAKE_SERVICE_TOKEN = "dg-test-relay-token-not-a-secret-0123456789"


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    app_module.EXECUTION_OWNERS.clear()
    app_module.EXECUTION_RESULTS.clear()
    yield
    app_module.EXECUTION_OWNERS.clear()
    app_module.EXECUTION_RESULTS.clear()


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeN8n:
    """Records each urlopen Request; answers with a programmable ack."""

    def __init__(self):
        self.requests: list = []
        self.timeouts: list = []
        self.ack = lambda body: {"executionId": f"exec-{len(self.requests)}"}
        self.raw = None
        self.raises: Exception | None = None
        self._lock = threading.Lock()

    def __call__(self, req, timeout=None):
        with self._lock:
            self.requests.append(req)
            self.timeouts.append(timeout)
        if self.raises is not None:
            raise self.raises
        if self.raw is not None:
            return _FakeResponse(self.raw)
        return _FakeResponse(json.dumps(self.ack(json.loads(req.data))).encode())

    @staticmethod
    def header(req, name):
        for key, value in req.header_items():
            if key.lower() == name.lower():
                return value
        return None


@pytest.fixture
def n8n(monkeypatch):
    fake = FakeN8n()
    monkeypatch.setattr(app_module.urllib.request, "urlopen", fake)
    monkeypatch.setenv("DG_SERVICE_TOKEN", FAKE_SERVICE_TOKEN)
    return fake


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username, memberships):
    auth_fixtures.make_user(username, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _service_headers():
    return {auth.SERVICE_TOKEN_HEADER: FAKE_SERVICE_TOKEN}


class TestFireN8nWebhook:
    def test_sends_json_post_with_service_token_and_returns_execution_id(self, n8n):
        n8n.ack = lambda body: {"executionId": "abc-123"}

        result = app_module.fire_n8n_webhook("dg/rules-ingest", {"k": "v"})

        assert result == "abc-123"
        (req,) = n8n.requests
        assert req.full_url == f"{app_module.N8N_INTERNAL_URL}/webhook/dg/rules-ingest"
        assert req.get_method() == "POST"
        assert FakeN8n.header(req, "Content-Type") == "application/json"
        assert FakeN8n.header(req, auth.SERVICE_TOKEN_HEADER) == FAKE_SERVICE_TOKEN
        assert json.loads(req.data) == {"k": "v"}
        assert n8n.timeouts == [15]

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_unset_token_fails_closed_without_a_network_call(self, n8n, monkeypatch, value):
        if value is None:
            monkeypatch.delenv("DG_SERVICE_TOKEN", raising=False)
        else:
            monkeypatch.setenv("DG_SERVICE_TOKEN", value)

        with pytest.raises(app_module.HTTPException) as info:
            app_module.fire_n8n_webhook("dg/rules-ingest", {})

        assert info.value.status_code == 503
        assert info.value.detail["code"] == "RELAY_UNAVAILABLE"
        assert n8n.requests == []

    @pytest.mark.parametrize("raw", [b"{}", b'{"executionId": ""}', b"not json", b"[]"])
    def test_ack_without_execution_id_is_a_502(self, n8n, raw):
        n8n.raw = raw

        with pytest.raises(app_module.HTTPException) as info:
            app_module.fire_n8n_webhook("dg/rules-ingest", {})

        assert info.value.status_code == 502
        assert info.value.detail["code"] == "RELAY_NO_EXECUTION_ID"

    def test_unreachable_n8n_is_relay_unavailable(self, n8n):
        n8n.raises = app_module.urllib.error.URLError("refused")

        with pytest.raises(app_module.HTTPException) as info:
            app_module.fire_n8n_webhook("dg/rules-ingest", {})

        assert info.value.status_code == 503
        assert info.value.detail["code"] == "RELAY_UNAVAILABLE"


class TestCallN8nSync:
    def test_returns_completed_payload_and_sends_the_service_token(self, n8n, monkeypatch):
        n8n.ack = lambda body: {"executionId": "sync-1"}
        app_module.EXECUTION_RESULTS["sync-1"] = {"status": "completed", "payload": {"ok": 1}}

        payload = app_module.call_n8n_sync("dg/graph-query", {"prompt": "x"}, timeout=5)

        assert payload == {"ok": 1}
        (req,) = n8n.requests
        assert FakeN8n.header(req, auth.SERVICE_TOKEN_HEADER) == FAKE_SERVICE_TOKEN

    def test_failed_workflow_is_a_502(self, n8n):
        n8n.ack = lambda body: {"executionId": "sync-2"}
        app_module.EXECUTION_RESULTS["sync-2"] = {"status": "failed"}

        with pytest.raises(app_module.HTTPException) as info:
            app_module.call_n8n_sync("dg/graph-query", {}, timeout=5)

        assert info.value.status_code == 502


class TestRelayRoutes:
    def test_editor_relays_rules_ingest_with_the_authorised_project(self, client, n8n):
        headers = _headers("ed@dg.local", {"P1": "editor"})

        response = client.post(
            "/workflows/rules-ingest",
            json={"project": "P1", "rulesText": "Max height is 75 m."},
            headers=headers,
        )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["executionId"] == "exec-1"
        (req,) = n8n.requests
        assert req.full_url.endswith("/webhook/dg/rules-ingest")
        assert json.loads(req.data) == {
            "rules_text": "Max height is 75 m.",
            "project": "P1",
            "project_name": "P1",
            "cypher_prompt": False,
        }
        assert FakeN8n.header(req, auth.SERVICE_TOKEN_HEADER) == FAKE_SERVICE_TOKEN
        assert app_module.EXECUTION_OWNERS["exec-1"]["username"] == "ed@dg.local"
        assert app_module.EXECUTION_OWNERS["exec-1"]["project"] == "P1"

    def test_viewer_cannot_relay_rules_ingest(self, client, n8n):
        headers = _headers("vw@dg.local", {"P1": "viewer"})

        response = client.post(
            "/workflows/rules-ingest",
            json={"project": "P1", "rulesText": "x"},
            headers=headers,
        )

        assert response.status_code == 403
        assert n8n.requests == []

    def test_foreign_project_is_forbidden(self, client, n8n):
        headers = _headers("ed@dg.local", {"P1": "editor"})

        response = client.post(
            "/workflows/rules-ingest",
            json={"project": "P2", "rulesText": "x"},
            headers=headers,
        )

        assert response.status_code == 403
        assert n8n.requests == []

    def test_viewer_relays_graph_query(self, client, n8n):
        headers = _headers("vw@dg.local", {"P1": "viewer"})

        response = client.post(
            "/workflows/graph-query",
            json={"project": "P1", "prompt": "list rules"},
            headers=headers,
        )

        assert response.status_code == 202
        (req,) = n8n.requests
        assert req.full_url.endswith("/webhook/dg/graph-query")
        assert json.loads(req.data) == {
            "prompt": "list rules",
            "project": "P1",
            "project_name": "P1",
            "cypher_prompt": False,
        }

    def test_extra_body_fields_never_reach_n8n(self, client, n8n):
        headers = _headers("vw@dg.local", {"P1": "viewer"})

        client.post(
            "/workflows/graph-query",
            json={"project": "P1", "prompt": "q", "project_name": "P2", "cypher_prompt": True},
            headers=headers,
        )

        (req,) = n8n.requests
        sent = json.loads(req.data)
        assert sent["project_name"] == "P1"
        assert sent["cypher_prompt"] is False

    def test_service_principal_cannot_use_the_relay(self, client, n8n):
        response = client.post(
            "/workflows/graph-query",
            json={"project": "P1", "prompt": "q"},
            headers=_service_headers(),
        )

        assert response.status_code == 403
        assert n8n.requests == []

    def test_request_size_limits_are_enforced(self, client, n8n):
        headers = _headers("ed@dg.local", {"P1": "editor"})

        too_long = client.post(
            "/workflows/rules-ingest",
            json={"project": "P1", "rulesText": "x" * 20001},
            headers=headers,
        )
        empty = client.post(
            "/workflows/graph-query",
            json={"project": "P1", "prompt": ""},
            headers=headers,
        )

        assert too_long.status_code == 422
        assert empty.status_code == 422
        assert n8n.requests == []

    def test_unset_token_answers_503_and_never_calls_n8n(self, client, n8n, monkeypatch):
        headers = _headers("ed@dg.local", {"P1": "editor"})
        monkeypatch.delenv("DG_SERVICE_TOKEN", raising=False)

        response = client.post(
            "/workflows/rules-ingest",
            json={"project": "P1", "rulesText": "x"},
            headers=headers,
        )

        # Without DG_SERVICE_TOKEN no principal can authenticate as the service,
        # but a signed-in user still reaches the route -- and it fails closed.
        assert response.status_code == 503
        assert _code(response) == "RELAY_UNAVAILABLE"
        assert n8n.requests == []
        assert app_module.EXECUTION_OWNERS == {}

    def test_ack_without_execution_id_answers_502_and_records_no_owner(self, client, n8n):
        headers = _headers("ed@dg.local", {"P1": "editor"})
        n8n.raw = b"{}"

        response = client.post(
            "/workflows/rules-ingest",
            json={"project": "P1", "rulesText": "x"},
            headers=headers,
        )

        assert response.status_code == 502
        assert _code(response) == "RELAY_NO_EXECUTION_ID"
        assert app_module.EXECUTION_OWNERS == {}


class TestOwnerBoundPolling:
    def test_only_the_initiator_reads_the_result(self, client, n8n):
        a = _headers("a@dg.local", {"P1": "editor"})
        b = _headers("b@dg.local", {"P1": "editor"})
        n8n.ack = lambda body: {"executionId": "run-A"}
        client.post(
            "/workflows/graph-query", json={"project": "P1", "prompt": "q"}, headers=a
        )

        running = client.get("/execution-result/run-A", headers=a)
        assert running.status_code == 200
        assert running.json() == {"status": "running"}

        stored = client.post(
            "/execution-result",
            json={"executionId": "run-A", "status": "completed", "payload": {"answer": 42}},
            headers=_service_headers(),
        )
        assert stored.status_code == 200

        done = client.get("/execution-result/run-A", headers=a)
        assert done.status_code == 200
        assert done.json() == {"status": "completed", "payload": {"answer": 42}}

        other = client.get("/execution-result/run-A", headers=b)
        assert other.status_code == 404
        assert _code(other) == "EXECUTION_NOT_FOUND"
        assert "answer" not in other.text

    def test_unknown_execution_id_is_indistinguishable_from_someone_elses(self, client, n8n):
        a = _headers("a@dg.local", {"P1": "editor"})

        response = client.get("/execution-result/never-issued", headers=a)

        assert response.status_code == 404
        assert _code(response) == "EXECUTION_NOT_FOUND"


class TestConcurrentRelays:
    @pytest.mark.parametrize("post_order", [("exec-P1", "exec-P2"), ("exec-P2", "exec-P1")])
    def test_two_users_each_read_only_their_own_result(self, n8n, post_order):
        a = _headers("a@dg.local", {"P1": "editor"})
        b = _headers("b@dg.local", {"P2": "editor"})
        barrier = threading.Barrier(2, timeout=10)

        def ack(body):
            # Both relays are inside the n8n call at once before either acks.
            barrier.wait()
            return {"executionId": f"exec-{body['project']}"}

        n8n.ack = ack
        results: dict[str, object] = {}

        def relay(name, headers, project):
            local = TestClient(app, raise_server_exceptions=False)
            results[name] = local.post(
                "/workflows/graph-query",
                json={"project": project, "prompt": f"q-{project}"},
                headers=headers,
            )

        threads = [
            threading.Thread(target=relay, args=("a", a, "P1")),
            threading.Thread(target=relay, args=("b", b, "P2")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        assert results["a"].status_code == 202
        assert results["b"].status_code == 202
        assert results["a"].json()["executionId"] == "exec-P1"
        assert results["b"].json()["executionId"] == "exec-P2"

        client = TestClient(app, raise_server_exceptions=False)
        for execution_id in post_order:
            stored = client.post(
                "/execution-result",
                json={
                    "executionId": execution_id,
                    "status": "completed",
                    "payload": {"owner": execution_id},
                },
                headers=_service_headers(),
            )
            assert stored.status_code == 200

        own_a = client.get("/execution-result/exec-P1", headers=a)
        own_b = client.get("/execution-result/exec-P2", headers=b)
        assert own_a.json()["payload"] == {"owner": "exec-P1"}
        assert own_b.json()["payload"] == {"owner": "exec-P2"}
        assert client.get("/execution-result/exec-P2", headers=a).status_code == 404
        assert client.get("/execution-result/exec-P1", headers=b).status_code == 404
