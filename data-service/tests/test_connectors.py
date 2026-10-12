"""Tests for connector credential backend (Phase 812: CONNB-01..04).

Follows the existing test pattern from test_llm_gateway.py: FastAPI TestClient
with raise_server_exceptions=False. Persistence is redirected to a per-test
tmp_path by patching connectors.CREDENTIALS_FILE.

Note: the registry contains 14 connectors — the enumerated contract in
REQUIREMENTS CONN-01 / PLAN 812-01 lists 14 slugs; the "13" count in prose
is a typo (see 812-01-SUMMARY.md deviations).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import auth_fixtures  # noqa: E402
import connector_session  # noqa: E402
import connectors  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

EXPECTED_IDS = [
    "grasshopper",
    "dynamo",
    "revit",
    "blender",
    "tekla",
    "archicad",
    "civil3d",
    "infraworks",
    "navisworks",
    "solibri",
    "bimcollab",
    "bimtrack",
    "lumion",
    "twinmotion",
]

EXPECTED_CATEGORIES = [
    "VPL Platforms",
    "BIM Authoring",
    "BIM Coordination",
    "BCF Trackers",
    "Visualization",
]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect credential persistence to a per-test temp file."""
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")


def _read_store() -> list[dict]:
    return json.loads(connectors.CREDENTIALS_FILE.read_text(encoding="utf-8"))["credentials"]


def _mint(connector_id: str, project: str | None = "P1", label: str | None = None):
    """Seed a cleanup-only legacy credential; no route mints one anymore."""
    record = auth_fixtures.seed_legacy_credential(project or "default-project", connector_id)
    if label:
        rows = connectors.load_credentials()
        rows[-1]["label"] = label
        connectors.save_credentials(rows)
        record = rows[-1]
    return record


def _session(connector_id: str = "grasshopper", project: str = "P1", now: int | None = None) -> str:
    """A real ``dgk_`` connector sign-in session (D-26): what the heartbeat
    authenticates with since 1308-13. The shared test admin is exempt from the
    per-connector grant."""
    if now is None:
        return auth_fixtures.connector_token_for(project, connector_id=connector_id)
    auth_fixtures.connector_token_for(project, connector_id=connector_id)  # ensure the admin exists
    token, _record = connector_session.issue(
        username=auth_fixtures.TEST_ADMIN_USERNAME,
        project=project,
        connector_id=connector_id,
        now=now,
    )
    return token


def _stored_session_row(token: str) -> dict:
    digest = connector_session._hash(token)
    rows = auth._load(connector_session._file(), "sessions")
    return next(r for r in rows if r["token_hash"] == digest)


# ── Registry Shape ──


class TestRegistry:
    def test_registry_slugs_and_count(self):
        """Registry serves the enumerated connector slugs (14, per fixed contract)."""
        assert [c["id"] for c in connectors.CONNECTOR_REGISTRY] == EXPECTED_IDS

    def test_registry_five_categories(self):
        """Registry spans exactly the 5 contract categories."""
        assert connectors.CONNECTOR_CATEGORIES == EXPECTED_CATEGORIES
        assert {c["category"] for c in connectors.CONNECTOR_REGISTRY} == set(EXPECTED_CATEGORIES)

    def test_get_connectors_endpoint_shape(self):
        """GET /connectors reports sign-in sessions, not stored credentials."""
        response = client.get("/connectors")
        assert response.status_code == 200
        body = response.json()
        # Phase 1301-30 (D-39): the DeGram grants card follows the registry in
        # its own "Agents" category; it is not a registry connector.
        assert body["categories"] == [*EXPECTED_CATEGORIES, "Agents"]
        assert [c["id"] for c in body["connectors"]] == [*EXPECTED_IDS, "degram"]
        for connector in body["connectors"]:
            assert connector["status"] == "never_connected"
            assert connector["last_connection"] is None
            if connector["id"] != "degram":
                assert connector["active_sessions"] == 0
                assert "credentials" not in connector
            assert "name" in connector and "category" in connector


# ── Credential Creation (CONNB-02) ──


class TestCreateCredential:
    """Phase 1308 (D-31): connector-token creation is retired. Every signed-in
    caller gets 410 CONNECTOR_TOKENS_RETIRED for a registry connector and the
    store is never written; an unknown connector id and `degram` stay 404."""

    @pytest.mark.parametrize("connector_id", EXPECTED_IDS)
    def test_create_is_retired_for_every_registry_connector(self, connector_id):
        response = client.post(
            f"/connectors/{connector_id}/credentials",
            json={"label": "Office seat", "project": "P1"},
        )
        assert response.status_code == 410
        detail = response.json()["detail"]
        assert detail["code"] == "CONNECTOR_TOKENS_RETIRED"
        assert "/auth/connector-session" in detail["hint"]
        assert "token" not in response.json()
        assert not connectors.CREDENTIALS_FILE.exists()

    def test_create_without_body_is_also_410(self):
        """The policy row is `session`: no project source, no PROJECT_REQUIRED."""
        response = client.post("/connectors/grasshopper/credentials")
        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "CONNECTOR_TOKENS_RETIRED"

    def test_create_unknown_connector_404(self):
        """Unknown connector id → 404 structured error."""
        response = client.post("/connectors/sketchup/credentials", json={"project": "P1"})
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CONNECTOR_NOT_FOUND"

    def test_degram_is_not_a_connector_id(self):
        response = client.post("/connectors/degram/credentials", json={"project": "P1"})
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CONNECTOR_NOT_FOUND"

    def test_tokens_retired_factory_shape(self):
        error = connectors.tokens_retired()
        assert error.status_code == 410
        assert error.detail["code"] == "CONNECTOR_TOKENS_RETIRED"
        assert error.detail["error"] == "Connector tokens are retired."
        assert connectors.tokens_retired(status_code=401).status_code == 401

    def test_legacy_credential_not_exposed_by_listing(self):
        """A cleanup-only credential must not influence or appear in the registry."""
        record = _mint("dynamo")
        body = client.get("/connectors").json()
        dump = json.dumps(body)
        assert record["token_hash"] not in dump
        assert record["credential_id"] not in dump
        dynamo = next(c for c in body["connectors"] if c["id"] == "dynamo")
        assert dynamo["status"] == "never_connected"
        assert dynamo["active_sessions"] == 0
        assert "credentials" not in dynamo


# ── Heartbeat (CONNB-03, D-26/D-34) ──
#
# The heartbeat is a normal connector row now: the caller is a `dgk_` sign-in
# session, never an anonymous token check. No cookie is attached, so the
# principal is exactly what the Bearer says.


@pytest.mark.dg_principal("none")
class TestHeartbeat:
    def test_valid_session_activates_and_stamps_last_seen(self):
        issued_at = int(datetime.now(timezone.utc).timestamp()) - 3600
        token = _session("blender", now=issued_at)
        assert _stored_session_row(token)["last_seen"] == issued_at

        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["connector_id"] == "blender"
        assert body["project"] == "P1"
        assert body["status"] == "active"
        assert _stored_session_row(token)["last_seen"] > issued_at

    def test_unknown_session_401(self):
        response = client.post(
            "/connectors/heartbeat",
            headers={"Authorization": "Bearer dgk_not-a-real-session"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"

    def test_legacy_stored_token_401(self):
        """D-26: a valid, non-revoked legacy `dgc_` credential no longer
        authenticates the heartbeat, and the refusal stamps nothing."""
        _mint("tekla")
        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": "Bearer dgc_retired"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"
        assert _read_store()[0]["last_connection"] is None

    def test_missing_or_malformed_authorization_401(self):
        assert client.post("/connectors/heartbeat").status_code == 401
        assert (
            client.post(
                "/connectors/heartbeat", headers={"Authorization": "Basic dgk_whatever"}
            ).status_code
            == 401
        )

    def test_revoked_session_401(self):
        token = _session("tekla")
        assert (
            client.delete(
                "/auth/connector-session", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 204
        )
        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "CONNECTOR_SESSION_ENDED"

    def test_a_user_session_cookie_is_not_a_connector(self):
        """The row lists the connector principal only: a signed-in user cookie
        is refused, not treated as a heartbeat."""
        cookie = auth_fixtures.admin_session_token()
        as_user = TestClient(app, raise_server_exceptions=False)
        as_user.cookies.set(auth.SESSION_COOKIE_NAME, cookie)
        response = as_user.post("/connectors/heartbeat", headers={auth.CSRF_HEADER: "1"})
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "PRINCIPAL_NOT_PERMITTED"


# ── Phase 825 (CONNG-03): project-scoped session + connection bundle ──


@pytest.mark.dg_principal("none")
class TestHeartbeatBundle:
    def test_session_project_is_echoed_by_heartbeat(self):
        token = _session("grasshopper", "urban-tower")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["project"] == "urban-tower"

    def test_heartbeat_returns_host_facing_neo4j_bundle(self):
        token = _session("grasshopper")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        bundle = body["neo4j"]
        # Host-facing URI so an off-Docker connector can reach Neo4j, never the
        # Docker-internal bolt://neo4j:7687 (Phase 825 ADR-825-2).
        assert bundle["uri"] == "bolt://localhost:7687"
        assert bundle["uri"] != "bolt://neo4j:7687"
        assert bundle["user"] == "neo4j"
        assert bundle["password"]
        assert bundle["database"] == "neo4j"

    def test_neo4j_public_uri_env_overrides_bundle_uri(self, monkeypatch):
        import app as app_module

        monkeypatch.setattr(app_module, "NEO4J_PUBLIC_URI", "bolt://10.0.0.5:7687")
        token = _session("grasshopper")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["neo4j"]["uri"] == "bolt://10.0.0.5:7687"


# ── Status Derivation (CONNB-04) ──


class TestStatusDerivation:
    def test_never_connected(self):
        assert connectors.derive_status(None) == "never_connected"
        assert connectors.derive_status("") == "never_connected"

    def test_active_within_seven_days(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        recent = (now - timedelta(days=6, hours=23)).isoformat()
        assert connectors.derive_status(recent, now=now) == "active"

    def test_stale_older_than_seven_days(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        old = (now - timedelta(days=8)).isoformat()
        assert connectors.derive_status(old, now=now) == "stale"

    def test_ended_session_surfaces_as_stale_in_endpoint(self):
        token = _session("lumion")
        assert connector_session.revoke_token(token)
        overview = client.get("/connectors").json()["connectors"]
        lumion = next(c for c in overview if c["id"] == "lumion")
        assert lumion["status"] == "stale"
        assert lumion["active_sessions"] == 0
        assert lumion["last_connection"] is not None


# ── Revoke Lifecycle (CONNB-01) ──


class TestRevokeLifecycle:
    def test_revoke_marks_cleanup_credential_without_activating_listing(self):
        record = _mint("navisworks", "P1", "Site laptop")
        response = client.delete(
            f"/connectors/navisworks/credentials/{record['credential_id']}"
        )
        assert response.status_code == 204
        assert _read_store()[0]["revoked"] is True

        overview = client.get("/connectors").json()["connectors"]
        navisworks = next(c for c in overview if c["id"] == "navisworks")
        assert navisworks["status"] == "never_connected"
        assert "credentials" not in navisworks

    def test_revoke_unknown_credential_404(self):
        response = client.delete("/connectors/navisworks/credentials/nope")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CREDENTIAL_NOT_FOUND"

    def test_revoke_unknown_connector_404(self):
        """Phase 1205: the credential resolver runs before the handler, so an
        unknown connector id is indistinguishable from an unknown credential
        (no-leak 404)."""
        response = client.delete("/connectors/sketchup/credentials/whatever")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CREDENTIAL_NOT_FOUND"

    def test_revoke_preserves_cleanup_row_but_not_overview_history(self):
        record = _mint("solibri")
        stored = _read_store()
        stored[0]["last_connection"] = datetime.now(timezone.utc).isoformat()
        connectors.save_credentials(stored)
        client.delete(f"/connectors/solibri/credentials/{record['credential_id']}")

        assert _read_store()[0]["last_connection"] == stored[0]["last_connection"]
        overview = client.get("/connectors").json()["connectors"]
        solibri = next(c for c in overview if c["id"] == "solibri")
        assert solibri["last_connection"] is None
        assert solibri["status"] == "never_connected"


# ── Phase 1205 plan 10: tenant-filtered overview (T-1205-10-06) ──


class TestOverviewProjectFilter:
    def _seed(self):
        token_p1 = _session("blender", "P1")
        token_p2 = _session("blender", "P2")
        _session("solibri", "P2")
        _mint("revit", "default-project")  # Legacy rows are cleanup-only.
        return token_p1, token_p2

    def test_projects_none_returns_every_live_session(self):
        self._seed()
        blender = next(c for c in connectors.get_connector_overview() if c["id"] == "blender")
        assert blender["status"] == "active"
        assert blender["active_sessions"] == 2
        assert blender["last_connection"] is not None

    def test_other_projects_are_dropped_before_status_is_derived(self):
        _token_p1, token_p2 = self._seed()
        assert connector_session.revoke_token(token_p2)
        overview = connectors.get_connector_overview(projects={"P1"})
        blender = next(c for c in overview if c["id"] == "blender")
        assert blender["active_sessions"] == 1
        assert blender["status"] == "active"
        solibri = next(c for c in overview if c["id"] == "solibri")
        assert solibri["status"] == "never_connected"
        assert solibri["last_connection"] is None
        assert "credentials" not in blender

    def test_empty_set_lists_no_sessions(self):
        self._seed()
        overview = connectors.get_connector_overview(projects=set())
        assert all(c["active_sessions"] == 0 and c["last_connection"] is None for c in overview)

    def test_legacy_record_does_not_count_as_session(self):
        self._seed()
        overview = connectors.get_connector_overview(projects={"default-project"})
        revit = next(c for c in overview if c["id"] == "revit")
        assert revit["status"] == "never_connected"
        assert "credentials" not in revit

    def test_route_filters_by_membership_and_admin_sees_all(self):
        self._seed()
        member = auth_fixtures.make_user("p1member@dg.local", memberships={"P1": "viewer"})
        cookie = auth_fixtures.session_cookie_for(member["username"])
        as_member = TestClient(app, raise_server_exceptions=False)
        as_member.cookies.set("dg_session", cookie)
        listed = as_member.get("/connectors").json()["connectors"]
        blender = next(c for c in listed if c["id"] == "blender")
        assert blender["status"] == "active"
        assert blender["active_sessions"] == 1
        solibri = next(c for c in listed if c["id"] == "solibri")
        assert solibri["status"] == "never_connected"

        as_admin = TestClient(app, raise_server_exceptions=False)
        as_admin.cookies.set("dg_session", auth_fixtures.admin_session_token())
        all_listed = as_admin.get("/connectors").json()["connectors"]
        assert next(c for c in all_listed if c["id"] == "blender")["active_sessions"] == 2

    def test_ended_session_becomes_stale_without_exposing_other_projects(self):
        _token_p1, token_p2 = self._seed()
        assert connector_session.revoke_token(token_p2)
        p2 = next(c for c in connectors.get_connector_overview(projects={"P2"}) if c["id"] == "blender")
        assert p2["status"] == "stale"
        assert p2["active_sessions"] == 0
        assert p2["last_connection"] is not None
        p1 = next(c for c in connectors.get_connector_overview(projects={"P1"}) if c["id"] == "blender")
        assert p1["status"] == "active"


# ── Per-connector access (Phase 1301-40, D-46) ──


class TestConnectorAccessField:
    def test_project_query_adds_access_to_registry_connectors_only(self):
        """An admin (owner everywhere) reads every registry connector as
        available; the DeGram card has no access field."""
        body = client.get("/connectors", params={"project": "P1"}).json()
        by_id = {c["id"]: c for c in body["connectors"]}
        assert all(by_id[i]["access"] == "available" for i in EXPECTED_IDS)
        assert "access" not in by_id["degram"]

    def test_no_project_query_leaves_the_payload_unchanged(self):
        body = client.get("/connectors").json()
        assert all("access" not in c for c in body["connectors"])
