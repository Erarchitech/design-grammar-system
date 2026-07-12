"""Tests for reasoner settings backend (Phase 814: REAS-01..03).

Follows the existing test pattern from test_connectors.py: FastAPI TestClient
with raise_server_exceptions=False. Persistence is redirected to a per-test
tmp_path by patching reasoner.REASONER_SETTINGS_FILE.
"""

from __future__ import annotations

import json
import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
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
        """Every reasoner has id, name, description, and a valid status."""
        for r in reasoner.REASONER_REGISTRY:
            assert "id" in r
            assert "name" in r
            assert "description" in r
            assert r.get("status") in {"placeholder", "integrated"}

    def test_hermit_status_is_integrated(self):
        """HermiT is the one live/integrated engine (D-04); Pellet stays placeholder."""
        by_id = {r["id"]: r for r in reasoner.REASONER_REGISTRY}
        assert by_id["hermit"]["status"] == "integrated"
        assert by_id["pellet"]["status"] == "placeholder"

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


# ── Consistency Proxy Timeout Reconciliation & Error Shapes (Phase 822 Plan 02, REAS-06 criterion 3) ──


class _FakeSidecarResponse:
    """Minimal stand-in for httpx.Response — only .status_code/.json()/.text used by the proxy."""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


class TestReasonerConsistencyProxy:
    def test_reasoner_consistency_proxy_read_timeout_tracks_sidecar(self, monkeypatch):
        """The proxy's read timeout must exceed the sidecar's own hard timeout ceiling
        (DG_REASONER_TIMEOUT_SECONDS, default 90s) with margin, while connect stays a
        fast-fail 2.0s (RESEARCH Pitfall 2)."""
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["timeout"] = timeout
            return _FakeSidecarResponse(
                200,
                {
                    "consistent": True,
                    "unsatisfiable_classes": [],
                    "axiom_counts": {},
                    "duration_ms": 1,
                    "stripped_builtin_rules": 0,
                },
            )

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        response = client.post("/reasoner/consistency", json={"project": "x", "engine": "hermit"})

        assert response.status_code == 200
        captured_timeout = captured["timeout"]
        assert captured_timeout.read >= float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90"))
        assert captured_timeout.connect == 2.0

    def test_reasoner_consistency_timeout_returns_504_structured(self, monkeypatch):
        """A data-service transport timeout is a hard error (D-09): 504 with a structured
        detail.code == REASONER_TIMEOUT body, and NO top-level `consistent` key -- shape-distinct
        from a genuine sidecar semantic timeout (D-08)."""

        def fake_post(url, json=None, timeout=None):
            raise httpx.TimeoutException("simulated transport timeout")

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        response = client.post("/reasoner/consistency", json={"project": "x", "engine": "hermit"})

        assert response.status_code == 504
        body = response.json()
        assert body["detail"]["code"] == "REASONER_TIMEOUT"
        assert body["detail"]["error"]
        assert "consistent" not in body

    def test_reasoner_consistency_connect_error_returns_502(self, monkeypatch):
        """An unreachable sidecar is a hard error (D-09): 502 with detail.code == REASONER_UNAVAILABLE."""

        def fake_post(url, json=None, timeout=None):
            raise httpx.ConnectError("simulated connect failure")

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        response = client.post("/reasoner/consistency", json={"project": "x", "engine": "hermit"})

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "REASONER_UNAVAILABLE"

    def test_reasoner_consistency_passes_through_sidecar_timeout_body(self, monkeypatch):
        """A genuine sidecar semantic timeout (D-08) is passed through verbatim -- status 504,
        body still carries `consistent: null` + `error: "timeout"`, and has NO `detail` wrapper,
        proving it is shape-distinct from the proxy's own transport-error body (D-09)."""
        sidecar_timeout_body = {
            "consistent": None,
            "error": "timeout",
            "duration_ms": 90000,
            "stripped_builtin_rules": 3,
            "timeout_seconds": 90,
        }

        def fake_post(url, json=None, timeout=None):
            return _FakeSidecarResponse(504, sidecar_timeout_body)

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        response = client.post("/reasoner/consistency", json={"project": "x", "engine": "hermit"})

        assert response.status_code == 504
        body = response.json()
        assert body["consistent"] is None
        assert body["error"] == "timeout"
        assert "detail" not in body
