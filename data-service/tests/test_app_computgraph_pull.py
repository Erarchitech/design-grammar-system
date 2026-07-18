"""Tests for POST /computgraph/context/pull (Phase 33 Plan 03: BRDG-02).

Follows the existing test pattern from test_reasoner.py: FastAPI TestClient
with raise_server_exceptions=False, monkeypatching module-level state — here
`gh_bridge.get_canvas_context` (imported into `app` at module scope).
"""

from __future__ import annotations

import os
import sys

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


class TestComputgraphContextPull:
    def test_pull_stamps_project_and_returns_document(self, monkeypatch):
        """A successful bridge round-trip returns 200 with project stamped onto
        the returned document, and the document's own fields intact."""

        def fake_get_canvas_context(project: str):
            return {"documentId": "d", "procedures": []}

        monkeypatch.setattr(app_module.gh_bridge, "get_canvas_context", fake_get_canvas_context)

        response = client.post("/computgraph/context/pull", json={"project": "p1"})

        assert response.status_code == 200
        body = response.json()
        assert body["project"] == "p1"
        assert body["documentId"] == "d"

    def test_pull_propagates_bridge_unreachable_as_503(self, monkeypatch):
        """When gh_bridge raises the structured 503, the endpoint returns 503
        with the structured detail intact — no hang, no generic 500."""

        def fake_get_canvas_context(project: str):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Grasshopper bridge unreachable at host.docker.internal:8720: refused",
                    "hint": "Start Rhino and enable DG CANVAS LISTENER (port 8720).",
                    "code": "GH_BRIDGE_UNREACHABLE",
                },
            )

        monkeypatch.setattr(app_module.gh_bridge, "get_canvas_context", fake_get_canvas_context)

        response = client.post("/computgraph/context/pull", json={"project": "p1"})

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "GH_BRIDGE_UNREACHABLE"
