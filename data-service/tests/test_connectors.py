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


def _read_store() -> list[dict]:
    return json.loads(connectors.CREDENTIALS_FILE.read_text(encoding="utf-8"))["credentials"]


def _mint(connector_id: str, project: str | None = "P1", label: str | None = None):
    """Seed a legacy dgc_ credential directly in the store. Phase 1308 (D-31)
    retired ``POST /connectors/{id}/credentials``, so no route can mint one;
    ``connectors.create_credential`` stays only to seed legacy rows here until
    plan 1308-13 refuses them and 1308-24 deletes the function."""
    return connectors.create_credential(connector_id, label, project)


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
        """GET /connectors returns registry joined with status + credentials."""
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
            assert connector["credentials"] == []
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

    def test_token_never_exposed_by_listing(self):
        """GET /connectors credential summaries omit token and token_hash."""
        _record, token = _mint("dynamo")
        body = client.get("/connectors").json()
        dump = json.dumps(body)
        assert token not in dump
        assert "token_hash" not in dump
        dynamo = next(c for c in body["connectors"] if c["id"] == "dynamo")
        summary = dynamo["credentials"][0]
        assert set(summary) == {"credential_id", "label", "created_at", "revoked"}


# ── Heartbeat (CONNB-03) ──


class TestHeartbeat:
    def test_valid_token_activates_and_stamps_last_connection(self):
        _record, token = _mint("blender")
        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["connector_id"] == "blender"
        assert body["status"] == "active"

        overview = client.get("/connectors").json()["connectors"]
        blender = next(c for c in overview if c["id"] == "blender")
        assert blender["status"] == "active"
        assert blender["last_connection"] is not None
        # Stamped timestamp parses and is recent
        stamped = datetime.fromisoformat(blender["last_connection"])
        assert datetime.now(timezone.utc) - stamped < timedelta(minutes=1)

    def test_unknown_token_401(self):
        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": "Bearer dgc_not-a-real-token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"

    def test_missing_or_malformed_authorization_401(self):
        assert client.post("/connectors/heartbeat").status_code == 401
        assert (
            client.post(
                "/connectors/heartbeat", headers={"Authorization": "Basic dgc_whatever"}
            ).status_code
            == 401
        )

    def test_revoked_token_401(self):
        record, token = _mint("tekla")
        created = {"credential_id": record["credential_id"]}
        assert (
            client.delete(
                f"/connectors/tekla/credentials/{created['credential_id']}"
            ).status_code
            == 204
        )
        response = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


# ── Phase 825 (CONNG-03): project-scoped token + connection bundle ──


class TestHeartbeatBundle:
    def test_created_project_is_echoed_by_heartbeat(self):
        _record, token = _mint("grasshopper", "urban-tower")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["project"] == "urban-tower"

    def test_missing_project_defaults_to_default_project(self):
        # A legacy credential minted with no project (the route now requires
        # one, so it is created directly in the store).
        _record, token = connectors.create_credential("grasshopper")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["project"] == "default-project"

    def test_heartbeat_returns_host_facing_neo4j_bundle(self):
        _record, token = _mint("grasshopper")
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        bundle = body["neo4j"]
        # Host-facing URI so an off-Docker connector can reach Neo4j — never the
        # Docker-internal bolt://neo4j:7687 (Phase 825 ADR-825-2).
        assert bundle["uri"] == "bolt://localhost:7687"
        assert bundle["uri"] != "bolt://neo4j:7687"
        assert bundle["user"] == "neo4j"
        assert bundle["password"]
        assert bundle["database"] == "neo4j"

    def test_neo4j_public_uri_env_overrides_bundle_uri(self, monkeypatch):
        import app as app_module

        monkeypatch.setattr(app_module, "NEO4J_PUBLIC_URI", "bolt://10.0.0.5:7687")
        _record, token = _mint("grasshopper")
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

    def test_stale_surfaces_in_endpoint(self):
        """A connection older than 7 days shows as stale via GET /connectors."""
        _mint("lumion")
        stored = _read_store()
        stored[0]["last_connection"] = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).isoformat()
        connectors.save_credentials(stored)

        overview = client.get("/connectors").json()["connectors"]
        lumion = next(c for c in overview if c["id"] == "lumion")
        assert lumion["status"] == "stale"
        assert lumion["last_connection"] == stored[0]["last_connection"]


# ── Revoke Lifecycle (CONNB-01) ──


class TestRevokeLifecycle:
    def test_revoke_marks_credential_and_reflects_in_listing(self):
        record, _token = _mint("navisworks", "P1", "Site laptop")
        created = {"credential_id": record["credential_id"]}
        response = client.delete(
            f"/connectors/navisworks/credentials/{created['credential_id']}"
        )
        assert response.status_code == 204

        overview = client.get("/connectors").json()["connectors"]
        navisworks = next(c for c in overview if c["id"] == "navisworks")
        assert navisworks["credentials"][0]["revoked"] is True

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

    def test_revoke_preserves_last_connection_history(self):
        """Revoking a credential keeps the connector's past connection date."""
        record, token = _mint("solibri")
        created = {"credential_id": record["credential_id"]}
        client.post(
            "/connectors/heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.delete(f"/connectors/solibri/credentials/{created['credential_id']}")

        overview = client.get("/connectors").json()["connectors"]
        solibri = next(c for c in overview if c["id"] == "solibri")
        assert solibri["last_connection"] is not None
        assert solibri["status"] == "active"


# ── Phase 1205 plan 10: tenant-filtered overview (T-1205-10-06) ──


class TestOverviewProjectFilter:
    def _seed(self):
        _rec_a, token_a = connectors.create_credential("blender", "mine", "P1")
        _rec_b, token_b = connectors.create_credential("blender", "theirs", "P2")
        _rec_c, _tok_c = connectors.create_credential("solibri", "theirs-too", "P2")
        # Legacy record with no project reads as default-project.
        creds = connectors.load_credentials()
        creds.append(
            {
                "credential_id": "legacy1",
                "connector_id": "revit",
                "label": "legacy",
                "token_hash": "x",
                "created_at": "2026-01-01T00:00:00+00:00",
                "revoked": False,
                "last_connection": None,
            }
        )
        connectors.save_credentials(creds)
        connectors.record_heartbeat(token_b)  # P2 activity only
        return token_a, token_b

    def test_projects_none_returns_every_credential(self):
        self._seed()
        overview = connectors.get_connector_overview()
        blender = next(c for c in overview if c["id"] == "blender")
        assert len(blender["credentials"]) == 2

    def test_credentials_outside_the_set_are_dropped_before_status_is_derived(self):
        self._seed()
        overview = connectors.get_connector_overview(projects={"P1"})
        blender = next(c for c in overview if c["id"] == "blender")
        assert [c["label"] for c in blender["credentials"]] == ["mine"]
        # P2's heartbeat must not leak into P1's view of the connector.
        assert blender["last_connection"] is None
        assert blender["status"] == "never_connected"
        solibri = next(c for c in overview if c["id"] == "solibri")
        assert solibri["credentials"] == []

    def test_empty_set_lists_no_credentials(self):
        self._seed()
        overview = connectors.get_connector_overview(projects=set())
        assert all(c["credentials"] == [] for c in overview)

    def test_legacy_record_counts_as_default_project(self):
        self._seed()
        overview = connectors.get_connector_overview(projects={"default-project"})
        revit = next(c for c in overview if c["id"] == "revit")
        assert [c["credential_id"] for c in revit["credentials"]] == ["legacy1"]

    def test_route_filters_by_membership_and_admin_sees_all(self):
        import auth_fixtures

        self._seed()
        member = auth_fixtures.make_user("p1member@dg.local", memberships={"P1": "viewer"})
        cookie = auth_fixtures.session_cookie_for(member["username"])
        as_member = TestClient(app, raise_server_exceptions=False)
        as_member.cookies.set("dg_session", cookie)
        listed = as_member.get("/connectors").json()["connectors"]
        blender = next(c for c in listed if c["id"] == "blender")
        assert [c["label"] for c in blender["credentials"]] == ["mine"]
        assert blender["last_connection"] is None

        as_admin = TestClient(app, raise_server_exceptions=False)
        as_admin.cookies.set("dg_session", auth_fixtures.admin_session_token())
        all_listed = as_admin.get("/connectors").json()["connectors"]
        assert len(next(c for c in all_listed if c["id"] == "blender")["credentials"]) == 2


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
