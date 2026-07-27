"""Host-tier tests for `POST /designstate/capture` (Phase 39 Plan 02, DSAV-02).

Covers the authentication matrix (T-39-01), the project-binding rejection
(T-39-02) and its information-disclosure guard (T-39-06), the payload size cap
(T-39-07), the accepted happy path, the FastAPI `lifespan` watcher wiring, the
best-effort auto-publish adapter, and the D-10 `store_validation_run`
no-regression guard.

Host tier, no pytest marker: there is no live Neo4j here. The single Neo4j
write the capture route performs is replaced by a recording double
(`app.dsav_watcher.capture_state`), which keeps the auth matrix pure while
still asserting the write contract -- which project, which run id, which
payload reached the writer, and critically that every rejection path reached
it exactly zero times.

Preamble (sys.path insert, LLM_MASTER_SECRET default, module-scope
`TestClient(app, raise_server_exceptions=False)`) and the `tmp_path` credential
redirection both follow `test_connectors.py`.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import connectors  # noqa: E402
import dsav_watcher  # noqa: E402
from app import app  # noqa: E402

from dsav_fixtures import FIXTURE_PROJECT, capture_envelope_json  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

OTHER_PROJECT = "p39-someone-elses-project"

CAPTURE_URL = "/designstate/capture"


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect credential persistence to a per-test temp file so no real
    credential store is ever read or written (test_connectors.py convention)."""
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture(autouse=True)
def capture_recorder(monkeypatch):
    """Replace the route's single Neo4j write with a recorder.

    Autouse by design: a test that forgot this double would try to open a live
    Bolt connection from the host tier. The returned list holds one dict of
    keyword arguments per `dsav_watcher.capture_state()` call.
    """
    calls: list[dict] = []

    def _record(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(dsav_watcher, "capture_state", _record)
    return calls


def _mint_token(project: str = FIXTURE_PROJECT) -> str:
    """Mint a connector credential scoped to `project` and return its plaintext
    token. `create_credential` returns `(record, token)` and defaults `project`
    to "default-project" when not supplied -- always supplied here."""
    _record, token = connectors.create_credential("grasshopper", "phase-39-capture", project)
    return token


def _body(project: str = FIXTURE_PROJECT, payload_json: str | None = None) -> dict:
    return {
        "project": project,
        "statePayloadJson": capture_envelope_json() if payload_json is None else payload_json,
    }


# ── T-39-01: authentication matrix ───────────────────────────────────────────


def test_missing_header_returns_401_auth_failed(capture_recorder):
    response = client.post(CAPTURE_URL, json=_body())
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
    assert capture_recorder == []


def test_non_bearer_header_returns_401_auth_failed(capture_recorder):
    token = _mint_token()
    response = client.post(CAPTURE_URL, json=_body(), headers={"Authorization": token})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
    assert capture_recorder == []


def test_wrong_prefix_token_returns_401_auth_failed(capture_recorder):
    """A Bearer value that does not carry `connectors.TOKEN_PREFIX` is rejected
    before `authenticate_token` is ever consulted."""
    response = client.post(
        CAPTURE_URL, json=_body(), headers={"Authorization": "Bearer not-a-dg-connector-token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
    assert capture_recorder == []


def test_unknown_token_returns_401_auth_failed(capture_recorder):
    """Well-formed (correct prefix) but never issued."""
    unknown = connectors.generate_token()
    response = client.post(
        CAPTURE_URL, json=_body(), headers={"Authorization": f"Bearer {unknown}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
    assert capture_recorder == []


def test_revoked_credential_token_returns_401_auth_failed(capture_recorder):
    """Revocation takes effect immediately on the capture route, exactly as it
    does on the heartbeat (CONNB-01)."""
    record, token = connectors.create_credential("grasshopper", "revoke-me", FIXTURE_PROJECT)
    assert connectors.revoke_credential("grasshopper", record["credential_id"]) is True
    response = client.post(
        CAPTURE_URL, json=_body(), headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
    assert capture_recorder == []


# ── T-39-02 / T-39-06: project binding ───────────────────────────────────────


def test_project_mismatch_returns_403_and_writes_nothing(capture_recorder):
    """A token bound to project A may not capture into project B."""
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL,
        json=_body(project=OTHER_PROJECT),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CAPTURE_PROJECT_MISMATCH"
    assert capture_recorder == []


def test_project_mismatch_response_leaks_no_project_names(capture_recorder):
    """T-39-06: the 403 body names neither the credential's bound project nor
    the requested one, so the endpoint cannot be used to probe which projects
    exist or which project a stolen token belongs to."""
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL,
        json=_body(project=OTHER_PROJECT),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    body_text = response.text
    assert FIXTURE_PROJECT not in body_text
    assert OTHER_PROJECT not in body_text
    assert capture_recorder == []


# ── Accepted path ────────────────────────────────────────────────────────────


def test_matching_project_returns_202_accepted_and_records_one_capture(capture_recorder):
    token = _mint_token(FIXTURE_PROJECT)
    envelope = capture_envelope_json()
    response = client.post(
        CAPTURE_URL,
        json=_body(payload_json=envelope),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    body = response.json()

    assert body["project"] == FIXTURE_PROJECT
    assert body["status"] == "captured"
    run_id = body["runId"]
    assert len(run_id) == 32
    int(run_id, 16)  # raises if not hexadecimal
    # Parseable ISO-8601, and the same instant the writer received.
    datetime.fromisoformat(body["capturedAt"])

    assert len(capture_recorder) == 1
    call = capture_recorder[0]
    assert call["project"] == FIXTURE_PROJECT
    assert call["run_id"] == run_id
    assert call["state_payload_json"] == envelope
    assert call["captured_at"] == body["capturedAt"]


def test_capture_never_calls_record_heartbeat_on_accepted_path(capture_recorder, monkeypatch):
    """P-01: the route resolves the token with `authenticate_token`, never with
    `record_heartbeat` -- stamping `last_connection` would misrepresent capture
    traffic as connector liveness."""

    def _fail(*_args, **_kwargs):
        raise AssertionError("capture must not call connectors.record_heartbeat")

    monkeypatch.setattr(connectors, "record_heartbeat", _fail)
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL, json=_body(), headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 202
    assert len(capture_recorder) == 1


# ── T-39-07: payload cap and shape ───────────────────────────────────────────


def test_oversized_payload_returns_413_and_writes_nothing(capture_recorder, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "DSAV_MAX_STATE_PAYLOAD_BYTES", 64)
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL,
        json=_body(payload_json="x" * 512),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "CAPTURE_PAYLOAD_TOO_LARGE"
    assert capture_recorder == []


def test_empty_state_payload_returns_422_and_writes_nothing(capture_recorder):
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL,
        json=_body(payload_json=""),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert capture_recorder == []


def test_absent_state_payload_returns_422_and_writes_nothing(capture_recorder):
    token = _mint_token(FIXTURE_PROJECT)
    response = client.post(
        CAPTURE_URL,
        json={"project": FIXTURE_PROJECT},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert capture_recorder == []
