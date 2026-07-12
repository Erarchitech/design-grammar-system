"""Tests for the non-fatal SHACL sidecar proxy + persistence/view wiring
(Phase 823 Plan 03, SHCL-01/SHCL-02).

Follows the existing httpx-monkeypatch pattern from test_reasoner.py
(TestClient + monkeypatched httpx) and the @patch-decorator pattern from
test_error_responses.py for full publish_validation flow tests.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
from app import (  # noqa: E402
    app,
    _call_shacl_validate,
    _persist_shacl_report,
    SpeckleConnectionSettings,
    SpeckleProjectConfigPayload,
)

client = TestClient(app, raise_server_exceptions=False)


class _FakeSidecarResponse:
    """Minimal stand-in for httpx.Response — only .status_code/.json()/.text used."""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


# ── _call_shacl_validate: never raises, maps outcomes to status dicts ──


class TestCallShaclValidate:
    def test_success_maps_to_status_ok_with_passthrough(self, monkeypatch):
        """A successful sidecar response wraps the canonical envelope under status:ok."""
        sidecar_body = {
            "conforms": False,
            "results": [
                {
                    "severity": "violation",
                    "what": "Rule missing SWRL",
                    "where": "R_URB_HEIGHT_MAX_75_V",
                    "howToFix": "Add a SWRL body atom",
                    "focusLabel": "R_URB_HEIGHT_MAX_75_V",
                    "shapeId": "RuleStructuralShape",
                }
            ],
            "counts": {"violation": 1, "warning": 0, "info": 0},
        }

        def fake_post(url, json=None, timeout=None):
            return _FakeSidecarResponse(200, sidecar_body)

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")

        assert result["status"] == "ok"
        assert result["conforms"] is False
        assert result["results"] == sidecar_body["results"]
        assert result["counts"] == sidecar_body["counts"]

    def test_connect_error_returns_unavailable(self, monkeypatch):
        def fake_post(url, json=None, timeout=None):
            raise httpx.ConnectError("simulated connect failure")

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")
        assert result == {"status": "unavailable"}

    def test_timeout_exception_returns_timeout(self, monkeypatch):
        def fake_post(url, json=None, timeout=None):
            raise httpx.TimeoutException("simulated transport timeout")

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")
        assert result == {"status": "timeout"}

    def test_generic_exception_returns_unavailable(self, monkeypatch):
        def fake_post(url, json=None, timeout=None):
            raise RuntimeError("something unforeseen")

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")
        assert result == {"status": "unavailable"}

    def test_http_504_body_returns_timeout(self, monkeypatch):
        """A transport-level HTTP 504 from the sidecar maps to status:timeout."""

        def fake_post(url, json=None, timeout=None):
            return _FakeSidecarResponse(504, {"detail": "gateway timeout"})

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")
        assert result == {"status": "timeout"}

    def test_sidecar_body_error_timeout_returns_timeout(self, monkeypatch):
        """A 200-status sidecar body with error=='timeout' (semantic timeout) also maps to timeout."""

        def fake_post(url, json=None, timeout=None):
            return _FakeSidecarResponse(200, {"error": "timeout", "conforms": None})

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        result = _call_shacl_validate("proj-a", "run-1")
        assert result == {"status": "timeout"}

    def test_run_id_and_project_forwarded_in_request_body(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return _FakeSidecarResponse(200, {"conforms": True, "results": [], "counts": {}})

        monkeypatch.setattr(app_module.httpx, "post", fake_post)

        _call_shacl_validate("proj-a", "run-xyz")

        assert captured["json"] == {"project": "proj-a", "run_id": "run-xyz"}
        assert captured["url"].endswith("/shacl/validate")


# ── _persist_shacl_report: parameterized write, never string-interpolated ──


class TestPersistShaclReport:
    def test_persist_uses_parameterized_query(self, monkeypatch):
        captured = {}

        def fake_write_query(query, parameters=None):
            captured["query"] = query
            captured["parameters"] = parameters

        monkeypatch.setattr(app_module, "write_query", fake_write_query)

        _persist_shacl_report("proj-a", "run-1", json.dumps({"status": "ok"}))

        assert "$shaclReportJson" in captured["query"]
        assert "$project" in captured["query"]
        assert "$runId" in captured["query"]
        assert "proj-a" not in captured["query"]  # never string-interpolated
        assert "run-1" not in captured["query"]
        assert captured["parameters"] == {
            "graph": app_module.VALIDATION_GRAPH,
            "project": "proj-a",
            "runId": "run-1",
            "shaclReportJson": json.dumps({"status": "ok"}),
        }


# ── publish_validation: SHACL runs non-fatally after store, never breaks 200 ──


class TestPublishValidationShaclWiring:
    def _patch_publish_happy_path(self, stack):
        """Patch the Speckle/Neo4j collaborators publish_validation calls before
        reaching the SHACL wiring, so only the SHACL proxy behavior is under test."""
        config = SpeckleProjectConfigPayload(speckleProjectId="sp-1", baseModelId="bm-1")
        settings = SpeckleConnectionSettings(
            base_url="http://speckle.local",
            internal_url="http://speckle.local",
            write_token="tok",
            read_token="tok",
            dg_base_url="http://dg.local",
        )
        publish_result = {
            "validationModelId": "vm-1",
            "validationVersionId": "vv-1",
            "baseVersionId": "bv-1",
            "modelViewerUrl": "http://dg.local/model-viewer/?project=x&runId=y",
            "validationResourceUrl": "http://speckle.local/projects/sp-1/models/vm-1@vv-1",
            "baseResourceUrl": "http://speckle.local/projects/sp-1/models/bm-1@bv-1",
        }
        stack.enter_context(patch("app.get_integration_config", return_value=config))
        stack.enter_context(patch("app.get_speckle_settings", return_value=settings))
        stack.enter_context(patch("app.build_client", return_value=object()))
        stack.enter_context(patch("app.get_or_create_validation_model_id", return_value="vm-1"))
        stack.enter_context(patch("app.get_latest_model_version_id", return_value="bv-1"))
        stack.enter_context(patch("app.publish_validation_version", return_value=publish_result))
        stack.enter_context(patch("app.upsert_integration_config", return_value=config))
        stack.enter_context(patch("app.store_validation_run", return_value=None))
        stack.enter_context(patch("app._persist_shacl_report", return_value=None))

    def test_publish_returns_200_with_shacl_ok_block(self):
        from contextlib import ExitStack

        with ExitStack() as stack:
            self._patch_publish_happy_path(stack)
            stack.enter_context(
                patch(
                    "app._call_shacl_validate",
                    return_value={"status": "ok", "conforms": True, "results": [], "counts": {}},
                )
            )
            response = client.post(
                "/validation/publish",
                json={"project": "proj-a", "rules": [], "entities": []},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "published"
        assert body["shacl"] == {"status": "ok", "conforms": True, "results": [], "counts": {}}

    def test_publish_still_returns_200_when_shacl_sidecar_raises(self):
        """If _call_shacl_validate somehow raises (defense in depth), publish_validation's
        outer try/except degrades to an unavailable status block rather than a 500."""
        from contextlib import ExitStack

        with ExitStack() as stack:
            self._patch_publish_happy_path(stack)
            stack.enter_context(
                patch("app._call_shacl_validate", side_effect=RuntimeError("sidecar exploded"))
            )
            response = client.post(
                "/validation/publish",
                json={"project": "proj-a", "rules": [], "entities": []},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "published"
        assert body["shacl"] == {"status": "unavailable"}

    def test_publish_still_returns_200_when_persist_raises(self):
        """A persistence-layer failure (e.g. Neo4j write error) also must not break publish."""
        from contextlib import ExitStack

        with ExitStack() as stack:
            self._patch_publish_happy_path(stack)
            stack.enter_context(
                patch(
                    "app._call_shacl_validate",
                    return_value={"status": "ok", "conforms": True, "results": [], "counts": {}},
                )
            )
            stack.enter_context(
                patch("app._persist_shacl_report", side_effect=RuntimeError("neo4j write failed"))
            )
            response = client.post(
                "/validation/publish",
                json={"project": "proj-a", "rules": [], "entities": []},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "published"
        assert body["shacl"] == {"status": "unavailable"}
