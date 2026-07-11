"""Tests for reasoner settings backend (Phase 814: REAS-01..03).

Follows the existing test pattern from test_connectors.py: FastAPI TestClient
with raise_server_exceptions=False. Persistence is redirected to a per-test
tmp_path by patching reasoner.REASONER_SETTINGS_FILE.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import reasoner  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

EXPECTED_IDS = ["hermit", "pellet"]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect reasoner settings persistence to a per-test temp file."""
    monkeypatch.setattr(reasoner, "REASONER_SETTINGS_FILE", tmp_path / "reasoner-settings.json")


# ── Registry Shape ──


class TestRegistry:
    def test_registry_ids_and_count(self):
        """Registry serves the two reasoners: HermiT, Pellet."""
        ids = [r["id"] for r in reasoner.REASONER_REGISTRY]
        assert ids == EXPECTED_IDS

    def test_registry_each_has_required_fields(self):
        """Every reasoner has id, name, description, status."""
        for r in reasoner.REASONER_REGISTRY:
            assert "id" in r
            assert "name" in r
            assert "description" in r
            assert r.get("status") == "placeholder"

    def test_get_reasoner_settings_endpoint_shape(self):
        """GET /reasoner/settings returns registry + selected (null initially)."""
        response = client.get("/reasoner/settings")
        assert response.status_code == 200
        body = response.json()
        assert [r["id"] for r in body["reasoners"]] == EXPECTED_IDS
        assert body["selected"] is None


# ── Select / Persist Round-Trip (REAS-01, REAS-02) ──


class TestSelectReasoner:
    def test_select_hermit_persists_and_returns(self):
        """PUT /reasoner/settings with hermit persists and is reflected in GET."""
        response = client.put("/reasoner/settings", json={"reasoner": "hermit"})
        assert response.status_code == 200
        body = response.json()
        assert body["selected"] == "hermit"
        assert [r["id"] for r in body["reasoners"]] == EXPECTED_IDS

        # Re-read
        reread = client.get("/reasoner/settings").json()
        assert reread["selected"] == "hermit"

    def test_select_pellet_persists_and_overwrites(self):
        """Selecting Pellet overwrites a previous selection."""
        client.put("/reasoner/settings", json={"reasoner": "hermit"})
        response = client.put("/reasoner/settings", json={"reasoner": "pellet"})
        assert response.status_code == 200
        assert response.json()["selected"] == "pellet"

        reread = client.get("/reasoner/settings").json()
        assert reread["selected"] == "pellet"

    def test_selection_survives_reload(self):
        """Persisted selection shows as active on remount/revisit."""
        client.put("/reasoner/settings", json={"reasoner": "hermit"})

        # Simulate restart by creating fresh client
        fresh = TestClient(app, raise_server_exceptions=False)
        body = fresh.get("/reasoner/settings").json()
        assert body["selected"] == "hermit"


# ── Unknown Reasoner Rejection (REAS-03) ──


class TestUnknownReasoner:
    def test_unknown_id_returns_422(self):
        """Unknown reasoner id yields 422 structured error."""
        response = client.put("/reasoner/settings", json={"reasoner": "fact++"})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "REASONER_NOT_FOUND"

    def test_selection_not_persisted_on_failure(self):
        """Failed selection does not overwrite previous selection."""
        client.put("/reasoner/settings", json={"reasoner": "pellet"})
        client.put("/reasoner/settings", json={"reasoner": "nope"})
        body = client.get("/reasoner/settings").json()
        assert body["selected"] == "pellet"
