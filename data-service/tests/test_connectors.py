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
        assert body["categories"] == EXPECTED_CATEGORIES
        assert [c["id"] for c in body["connectors"]] == EXPECTED_IDS
        for connector in body["connectors"]:
            assert connector["status"] == "never_connected"
            assert connector["last_connection"] is None
            assert connector["credentials"] == []
            assert "name" in connector and "category" in connector


# ── Credential Creation (CONNB-02) ──


class TestCreateCredential:
    def test_create_returns_token_once_and_persists_only_hash(self):
        """POST returns dgc_ token; store holds only the SHA-256 hash."""
        response = client.post("/connectors/revit/credentials", json={"label": "Office seat"})
        assert response.status_code == 201
        body = response.json()
        token = body["token"]
        assert token.startswith("dgc_")
        assert len(token) > 20

        stored = _read_store()
        assert len(stored) == 1
        record = stored[0]
        assert record["credential_id"] == body["credential_id"]
        assert record["connector_id"] == "revit"
        assert record["label"] == "Office seat"
        assert record["token_hash"] == connectors.hash_token(token)
        assert token not in json.dumps(stored)
        assert record["revoked"] is False
        assert record["last_connection"] is None

    def test_create_without_body(self):
        """Label is optional — POST with no body works."""
        response = client.post("/connectors/grasshopper/credentials")
        assert response.status_code == 201
        assert response.json()["token"].startswith("dgc_")

    def test_create_unknown_connector_404(self):
        """Unknown connector id → 404 structured error."""
        response = client.post("/connectors/sketchup/credentials", json={})
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CONNECTOR_NOT_FOUND"

    def test_token_never_exposed_by_listing(self):
        """GET /connectors credential summaries omit token and token_hash."""
        token = client.post("/connectors/dynamo/credentials", json={}).json()["token"]
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
        token = client.post("/connectors/blender/credentials", json={}).json()["token"]
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
        created = client.post("/connectors/tekla/credentials", json={}).json()
        token = created["token"]
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
        token = client.post(
            "/connectors/grasshopper/credentials", json={"project": "urban-tower"}
        ).json()["token"]
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["project"] == "urban-tower"

    def test_missing_project_defaults_to_default_project(self):
        token = client.post("/connectors/grasshopper/credentials", json={}).json()["token"]
        body = client.post(
            "/connectors/heartbeat", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert body["project"] == "default-project"

    def test_heartbeat_returns_host_facing_neo4j_bundle(self):
        token = client.post("/connectors/grasshopper/credentials", json={}).json()["token"]
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
        token = client.post("/connectors/grasshopper/credentials", json={}).json()["token"]
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
        client.post("/connectors/lumion/credentials", json={})
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
        created = client.post(
            "/connectors/navisworks/credentials", json={"label": "Site laptop"}
        ).json()
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
        response = client.delete("/connectors/sketchup/credentials/whatever")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CONNECTOR_NOT_FOUND"

    def test_revoke_preserves_last_connection_history(self):
        """Revoking a credential keeps the connector's past connection date."""
        created = client.post("/connectors/solibri/credentials", json={}).json()
        client.post(
            "/connectors/heartbeat",
            headers={"Authorization": f"Bearer {created['token']}"},
        )
        client.delete(f"/connectors/solibri/credentials/{created['credential_id']}")

        overview = client.get("/connectors").json()["connectors"]
        solibri = next(c for c in overview if c["id"] == "solibri")
        assert solibri["last_connection"] is not None
        assert solibri["status"] == "active"
