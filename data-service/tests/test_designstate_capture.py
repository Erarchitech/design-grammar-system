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
import time
from datetime import datetime
from types import SimpleNamespace

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


# ── Watcher lifecycle: the FastAPI lifespan ──────────────────────────────────


def test_lifespan_import_does_not_start_watcher_thread():
    """39-RESEARCH.md Pitfall 3. Roughly thirty existing test modules do
    `from app import app` at import time; if importing app started the watcher,
    every one of them would spin a live Neo4j poller as a side effect. The
    thread must only exist inside an entered lifespan."""
    assert dsav_watcher._watcher_thread is None or not dsav_watcher._watcher_thread.is_alive()


def test_lifespan_starts_and_stops_watcher_thread_injecting_both_callables(monkeypatch):
    """Entering the lifespan starts exactly one thread and hands `poll_once`
    the real `_call_shacl_validate` and `_auto_publish_run`; exiting signals the
    stop event and joins."""
    import app as app_module

    monkeypatch.setattr(app_module, "ensure_spec_indexes", lambda: None)

    seen: list[tuple] = []

    def _poll_once(shacl_fn=None, publish_fn=None, **_kwargs):
        seen.append((shacl_fn, publish_fn))
        return {}

    monkeypatch.setattr(dsav_watcher, "poll_once", _poll_once)
    monkeypatch.setattr(dsav_watcher, "POLL_INTERVAL_SECONDS", 0.01)

    assert dsav_watcher._watcher_thread is None or not dsav_watcher._watcher_thread.is_alive()

    with TestClient(app):
        thread = dsav_watcher._watcher_thread
        assert thread is not None and thread.is_alive()
        deadline = time.time() + 3.0
        while not seen and time.time() < deadline:
            time.sleep(0.01)

    assert dsav_watcher._watcher_thread is None
    assert not thread.is_alive(), "stop_watcher must join the thread on shutdown"
    assert seen, "the watcher thread never reached poll_once"
    assert seen[0][0] is app_module._call_shacl_validate
    assert seen[0][1] is app_module._auto_publish_run


def test_lifespan_still_runs_ensure_spec_indexes(monkeypatch):
    """Regression guard for the on_event/lifespan interaction.

    Starlette runs the `on_startup` handlers registered by `@app.on_event`
    ONLY through its default lifespan; passing an explicit `lifespan=` to the
    FastAPI constructor replaces that default outright and the handlers are
    then silently never invoked. `ensure_spec_indexes` (SpecGraph fulltext
    index + hub nodes + `init_ollama_models`) predates Phase 39, so the
    lifespan must call it explicitly or Phase 39 would have quietly disabled a
    shipped startup hook.
    """
    import app as app_module

    fired: list[bool] = []
    monkeypatch.setattr(app_module, "ensure_spec_indexes", lambda: fired.append(True))
    monkeypatch.setattr(dsav_watcher, "start_watcher", lambda **_kwargs: None)
    monkeypatch.setattr(dsav_watcher, "stop_watcher", lambda **_kwargs: None)

    with TestClient(app):
        pass

    assert fired == [True]


def test_lifespan_survives_watcher_start_failure(monkeypatch):
    """T-39-08: a watcher that fails to start must never stop the service from
    serving requests."""
    import app as app_module

    monkeypatch.setattr(app_module, "ensure_spec_indexes", lambda: None)

    def _boom(**_kwargs):
        raise RuntimeError("watcher refused to start")

    monkeypatch.setattr(dsav_watcher, "start_watcher", _boom)
    monkeypatch.setattr(dsav_watcher, "stop_watcher", lambda **_kwargs: None)

    with TestClient(app) as live_client:
        response = live_client.get("/connectors")
        assert response.status_code == 200


# ── P-07: the best-effort auto-publish adapter ───────────────────────────────


def _speckle_config():
    from app import SpeckleProjectConfigPayload

    return SpeckleProjectConfigPayload(
        speckleProjectId="spkproj",
        baseModelId="basemodel",
        baseModelName=None,
        validationModelId="validmodel",
    )


def _publish_result() -> dict:
    return {
        "baseVersionId": "base-version-1",
        "validationModelId": "validmodel",
        "validationVersionId": "validation-version-1",
        "modelViewerUrl": "http://speckle/viewer",
        "baseResourceUrl": "http://speckle/base",
        "validationResourceUrl": "http://speckle/validation",
    }


@pytest.fixture
def no_store_validation_run(monkeypatch):
    """P-07/D-10: the adapter must never route through the manual-publish
    persistence helper."""

    def _fail(*_args, **_kwargs):
        raise AssertionError("_auto_publish_run must never call store_validation_run")

    import app as app_module

    monkeypatch.setattr(app_module, "store_validation_run", _fail)


def test_auto_publish_run_skips_when_speckle_config_missing(monkeypatch, no_store_validation_run):
    """D-13: an auto-run must never implicitly provision Speckle configuration,
    so the implicit-create helper the manual route falls through to is not
    reached."""
    import app as app_module

    monkeypatch.setattr(app_module, "get_integration_config", lambda _project: None)

    def _fail_autoconf(_project):
        raise AssertionError("_auto_publish_run must not reach _auto_configure_integration")

    def _fail_upsert(*_args, **_kwargs):
        raise AssertionError("_auto_publish_run must not create an IntegrationConfig row")

    monkeypatch.setattr(app_module, "_auto_configure_integration", _fail_autoconf)
    monkeypatch.setattr(app_module, "upsert_integration_config", _fail_upsert)

    result = app_module._auto_publish_run(FIXTURE_PROJECT, "run-cfg-missing")

    assert result["status"] == "skipped"
    assert result["reason"] == "speckle_config_missing"


def test_auto_publish_run_skips_when_speckle_token_missing(monkeypatch, no_store_validation_run):
    import app as app_module

    monkeypatch.setattr(app_module, "get_integration_config", lambda _project: _speckle_config())
    monkeypatch.setattr(
        app_module,
        "get_speckle_settings",
        lambda: SimpleNamespace(write_token="", internal_url="http://speckle"),
    )

    def _fail_build(*_args, **_kwargs):
        raise AssertionError("must not build a Speckle client without a write token")

    monkeypatch.setattr(app_module, "build_client", _fail_build)

    result = app_module._auto_publish_run(FIXTURE_PROJECT, "run-token-missing")

    assert result["status"] == "skipped"
    assert result["reason"] == "speckle_token_missing"


def test_auto_publish_run_publishes_and_sets_speckle_fields_in_place(
    monkeypatch, no_store_validation_run
):
    """On success the adapter SETs the same field names store_validation_run
    writes, in place on the already-completed run, so list_validation_runs and
    build_view_payload read an auto-published run identically to a manual one."""
    import app as app_module

    writes: list[tuple] = []
    published: list[dict] = []

    monkeypatch.setattr(app_module, "get_integration_config", lambda _project: _speckle_config())
    monkeypatch.setattr(
        app_module,
        "get_speckle_settings",
        lambda: SimpleNamespace(write_token="tok", internal_url="http://speckle"),
    )
    monkeypatch.setattr(app_module, "build_client", lambda _url, _token: "CLIENT")
    monkeypatch.setattr(
        app_module, "get_or_create_validation_model_id", lambda _c, _p, _v: "validmodel"
    )
    monkeypatch.setattr(
        app_module, "get_latest_model_version_id", lambda _c, _p, _b: "base-version-1"
    )

    def _publish(_settings, **kwargs):
        published.append(kwargs)
        return _publish_result()

    monkeypatch.setattr(app_module, "publish_validation_version", _publish)
    monkeypatch.setattr(app_module, "upsert_integration_config", lambda _p, payload: payload)
    monkeypatch.setattr(app_module, "write_query", lambda q, params=None: writes.append((q, params)))

    result = app_module._auto_publish_run(FIXTURE_PROJECT, "run-ok")

    assert result["status"] == "published"

    # A captured DesignState envelope carries no per-entity geometry and no
    # failedRuleIds, so the published version is a state-level marker. This is
    # the D-11 Speckle-noise data point being measured, not a missing feature.
    assert published[0]["rules"] == []
    assert published[0]["entities"] == []
    assert published[0]["run_id"] == "run-ok"

    assert len(writes) == 1
    query, params = writes[0]
    assert "AUTO" in query or "MERGE" in query
    assert params["runId"] == "run-ok"
    assert params["project"] == FIXTURE_PROJECT
    assert params["speckleProjectId"] == "spkproj"
    assert params["baseVersionId"] == "base-version-1"
    assert params["validationVersionId"] == "validation-version-1"
    assert params["modelViewerUrl"] == "http://speckle/viewer"
    assert "run.SendStatus = true" in query


def test_auto_publish_run_returns_error_result_and_never_raises(
    monkeypatch, no_store_validation_run
):
    """P-07: the verdict is already persisted; a publish failure must not cost
    the run, and must never propagate into the watcher tick."""
    import app as app_module

    monkeypatch.setattr(app_module, "get_integration_config", lambda _project: _speckle_config())
    monkeypatch.setattr(
        app_module,
        "get_speckle_settings",
        lambda: SimpleNamespace(write_token="tok", internal_url="http://speckle"),
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("speckle unreachable")

    monkeypatch.setattr(app_module, "build_client", _boom)

    result = app_module._auto_publish_run(FIXTURE_PROJECT, "run-error")

    assert result["status"] == "error"
    assert result["reason"] == "RuntimeError"


def test_auto_publish_run_is_callable_with_the_watcher_publish_fn_contract():
    """dsav_watcher.poll_once invokes `publish_fn(project, kept_run_id)` with
    exactly two positional arguments. Any additional adapter parameter must
    therefore carry a default, or every auto-publish would fail with a
    TypeError swallowed as a generic publish_error."""
    import inspect

    import app as app_module

    signature = inspect.signature(app_module._auto_publish_run)
    signature.bind(FIXTURE_PROJECT, "run-1")  # raises TypeError if incompatible


# ── D-10: the manual publish path stays byte-for-byte untouched ──────────────

STORE_VALIDATION_RUN_SHA256 = "db6615b823d3247c313b3f5f4cc1bfb7302f33012f79cf92323e9147d11c2b01"


def test_store_validation_run_source_hash_is_pinned():
    """D-10 requires the shipped manual-publish persistence path to stay
    byte-for-byte untouched by Phase 39, enforced here by a pinned source hash
    rather than by inspection.

    The hash was pinned during Phase 39 planning on 2026-07-27 over
    `inspect.getsource(app.store_validation_run)` (4036 characters).

    A failure here means one of exactly two things:
      1. An accidental edit -- revert it; the auto-validation path must SET the
         Speckle fields in place via AUTO_COMPLETE_PUBLISH_QUERY instead of
         routing through this function.
      2. A deliberate, approved change -- re-pin the hash in the very same
         commit as the change, so the review gate D-10 wants is exercised
         consciously rather than bypassed.
    """
    import hashlib
    import inspect

    import app as app_module

    source = inspect.getsource(app_module.store_validation_run)
    digest = hashlib.sha256(source.encode()).hexdigest()

    assert digest == STORE_VALIDATION_RUN_SHA256, (
        "store_validation_run changed (D-10). Revert the edit, or re-pin this "
        f"hash deliberately in the same commit. Actual: {digest}"
    )
