"""Tests for the startup-time deployment-profile consumers (Phase 1205
"Security and Tenancy Release Gate" plan 07, D-05/D-07/D-11/D-19).

Covers: the heartbeat's Neo4j bundle omission in `multi-user` (D-07), the
lifespan's profile validation + known-default secret refusal (D-11) +
bootstrap-admin creation (D-05), and the import-time docs/redoc/openapi
gating (D-07/D-19).

Follows test_designstate_capture.py's lifespan-test pattern: `ensure_spec_indexes`
and the watcher start/stop are monkeypatched to no-ops so entering
`with TestClient(app):` never touches a live Neo4j or starts a real
background thread; auth store persistence is redirected to a per-test
tmp_path (test_auth_store.py convention).
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret-for-deployment-profile")

import auth  # noqa: E402
import connectors  # noqa: E402
import dsav_watcher  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402

DATA_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..")

# A secret value that passes secrets_policy.classify_secret cleanly: long
# enough for every MIN_LENGTHS entry and not a known-default literal/prefix/digest.
_STRONG_SECRET = "s" * 40
_STRONG_ADMIN_PASSWORD = "strong-admin-password-1"


@pytest.fixture(autouse=True)
def _redirect_connector_store(tmp_path, monkeypatch):
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def _redirect_auth_store(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")


@pytest.fixture
def _noop_startup(monkeypatch):
    """Neutralize the pre-existing SpecGraph bootstrap + watcher thread so the
    lifespan tests below exercise only the new Phase 1205 startup hooks."""
    monkeypatch.setattr(app_module, "ensure_spec_indexes", lambda: None)
    monkeypatch.setattr(dsav_watcher, "start_watcher", lambda **_kwargs: None)
    monkeypatch.setattr(dsav_watcher, "stop_watcher", lambda **_kwargs: None)


def _set_passing_secrets(monkeypatch, *, except_neo4j_password=False):
    monkeypatch.setenv("LLM_MASTER_SECRET", _STRONG_SECRET)
    monkeypatch.setenv("DG_SERVICE_TOKEN", _STRONG_SECRET)
    monkeypatch.setenv("DG_BOOTSTRAP_ADMIN_PASSWORD", _STRONG_ADMIN_PASSWORD)
    if not except_neo4j_password:
        monkeypatch.setenv("NEO4J_PASSWORD", _STRONG_SECRET)


# ── Heartbeat Neo4j bundle omission (D-07) ──────────────────────────────────


def test_heartbeat_local_profile_includes_neo4j_bundle(monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "local")
    _record, token = connectors.create_credential("grasshopper", project="P1")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["project"] == "P1"
    assert body["neo4j"] is not None
    assert body["neo4j"]["uri"]


def test_heartbeat_multi_user_profile_omits_neo4j_bundle(monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "multi-user")
    _record, token = connectors.create_credential("grasshopper", project="P1")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["project"] == "P1"
    assert body["neo4j"] is None


# ── Lifespan: profile validation, secrets refusal, bootstrap admin (D-05/D-11/D-19) ──


def test_lifespan_multi_user_raises_on_default_neo4j_password(
    monkeypatch, _redirect_auth_store, _noop_startup
):
    monkeypatch.setenv("DG_DEPLOYMENT", "multi-user")
    _set_passing_secrets(monkeypatch, except_neo4j_password=True)
    monkeypatch.setenv("NEO4J_PASSWORD", "12345678")  # known default

    with pytest.raises(RuntimeError, match="NEO4J_PASSWORD"):
        with TestClient(app):
            pass


def test_lifespan_local_warns_once_naming_the_key_and_starts(
    monkeypatch, _redirect_auth_store, _noop_startup, caplog
):
    monkeypatch.setenv("DG_DEPLOYMENT", "local")
    _set_passing_secrets(monkeypatch, except_neo4j_password=True)
    monkeypatch.setenv("NEO4J_PASSWORD", "12345678")  # known default

    with caplog.at_level("WARNING"):
        with TestClient(app) as client:
            resp = client.get("/")  # public health route; /connectors now needs a login (1205-10)
            assert resp.status_code == 200

    secrets_warnings = [
        r for r in caplog.records
        if r.levelname == "WARNING" and "NEO4J_PASSWORD" in r.getMessage()
    ]
    assert len(secrets_warnings) == 1


def test_lifespan_unknown_profile_raises(monkeypatch, _redirect_auth_store, _noop_startup):
    monkeypatch.setenv("DG_DEPLOYMENT", "prod")

    with pytest.raises(ValueError):
        with TestClient(app):
            pass


def test_lifespan_creates_bootstrap_admin_when_none_exists(
    monkeypatch, _redirect_auth_store, _noop_startup
):
    monkeypatch.setenv("DG_DEPLOYMENT", "local")
    _set_passing_secrets(monkeypatch)
    monkeypatch.setenv("DG_BOOTSTRAP_ADMIN_USER", "bootstrap-admin")
    monkeypatch.setenv("DG_BOOTSTRAP_ADMIN_PASSWORD", _STRONG_ADMIN_PASSWORD)

    assert auth.get_user("bootstrap-admin") is None

    with TestClient(app):
        pass

    created = auth.get_user("bootstrap-admin")
    assert created is not None
    assert created["is_admin"] is True


# ── Docs/redoc/openapi gated by the import-time profile (D-07/D-19) ────────


def test_docs_exposed_in_local_absent_in_multi_user():
    script = (
        "import os\n"
        "os.environ.setdefault('LLM_MASTER_SECRET', 'test-subprocess-master-secret')\n"
        "from app import app\n"
        "print(app.docs_url, '|', app.redoc_url, '|', app.openapi_url)\n"
    )

    local_env = dict(os.environ, DG_DEPLOYMENT="local")
    multi_env = dict(os.environ, DG_DEPLOYMENT="multi-user")

    local_result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=DATA_SERVICE_DIR,
        env=local_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    multi_result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=DATA_SERVICE_DIR,
        env=multi_env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert local_result.returncode == 0, local_result.stderr
    assert multi_result.returncode == 0, multi_result.stderr
    assert local_result.stdout.strip() == "/docs | /redoc | /openapi.json"
    assert multi_result.stdout.strip() == "None | None | None"
