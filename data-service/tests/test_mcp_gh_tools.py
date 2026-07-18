"""Tests for the 4 gh_* MCP tools on POST /mcp (Phase 33 Plan 03: BRDG-03).

Extends the existing `/mcp` JSON-RPC "neo4j-mcp" server verbatim (no new
abstraction); tests mirror test_reasoner.py's TestClient + monkeypatch style.
"""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

EXPECTED_GH_TOOL_NAMES = {
    "gh_get_context",
    "gh_get_selection",
    "gh_preview_structure",
    "gh_clear_preview",
}


class TestToolsList:
    def test_tools_list_includes_gh_tools_alongside_existing_neo4j_tools(self):
        response = client.post("/mcp", json={"method": "tools/list"})
        assert response.status_code == 200
        names = {t["name"] for t in response.json()["result"]["tools"]}

        assert EXPECTED_GH_TOOL_NAMES.issubset(names)
        assert {"neo4j_schema", "neo4j_query"}.issubset(names)
        # Exactly the 4 new tools in addition to the 2 pre-existing ones.
        assert names == EXPECTED_GH_TOOL_NAMES | {"neo4j_schema", "neo4j_query"}


class TestToolsCallGhGetContext:
    def test_tools_call_gh_get_context_dispatches_through_gh_bridge(self, monkeypatch):
        canned_context = {"documentId": "d", "procedures": [], "project": "p1"}

        def fake_get_canvas_context(project: str):
            assert project == "p1"
            return canned_context

        monkeypatch.setattr(app_module.gh_bridge, "get_canvas_context", fake_get_canvas_context)

        response = client.post(
            "/mcp",
            json={
                "method": "tools/call",
                "id": 1,
                "params": {"name": "gh_get_context", "arguments": {"project": "p1"}},
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["result"]["data"] == canned_context


class TestToolsCallGhGetSelection:
    def test_tools_call_gh_get_selection_dispatches_through_gh_bridge(self, monkeypatch):
        canned_selection = {"selection": ["guid-1", "guid-2"]}

        monkeypatch.setattr(
            app_module.gh_bridge, "get_selection", lambda: canned_selection
        )

        response = client.post(
            "/mcp",
            json={"method": "tools/call", "id": 2, "params": {"name": "gh_get_selection", "arguments": {}}},
        )

        assert response.status_code == 200
        assert response.json()["result"]["data"] == canned_selection


class TestToolsCallGhPreviewStructure:
    def test_tools_call_gh_preview_structure_returns_stub_unsupported(self, monkeypatch):
        stub_result = {"supported": False}

        captured_args = {}

        def fake_preview_structure(structure: dict):
            captured_args["structure"] = structure
            return stub_result

        monkeypatch.setattr(app_module.gh_bridge, "preview_structure", fake_preview_structure)

        response = client.post(
            "/mcp",
            json={
                "method": "tools/call",
                "id": 3,
                "params": {"name": "gh_preview_structure", "arguments": {"nodes": []}},
            },
        )

        assert response.status_code == 200
        assert response.json()["result"]["data"]["supported"] is False
        assert captured_args["structure"] == {"nodes": []}


class TestToolsCallGhClearPreview:
    def test_tools_call_gh_clear_preview_returns_stub_unsupported(self, monkeypatch):
        stub_result = {"supported": False}
        monkeypatch.setattr(app_module.gh_bridge, "clear_preview", lambda: stub_result)

        response = client.post(
            "/mcp",
            json={"method": "tools/call", "id": 4, "params": {"name": "gh_clear_preview", "arguments": {}}},
        )

        assert response.status_code == 200
        assert response.json()["result"]["data"]["supported"] is False


class TestToolsCallErrorPropagation:
    def test_gh_bridge_error_propagates_as_httpexception_not_jsonrpc_error(self, monkeypatch):
        """Errors from gh_bridge propagate as HTTPException/_structured_error_response
        (do NOT get wrapped in a JSON-RPC error object) — matches the neo4j_query
        precedent (33-RESEARCH.md Anti-Patterns)."""
        from fastapi import HTTPException

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

        response = client.post(
            "/mcp",
            json={
                "method": "tools/call",
                "id": 5,
                "params": {"name": "gh_get_context", "arguments": {"project": "p1"}},
            },
        )

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "GH_BRIDGE_UNREACHABLE"
