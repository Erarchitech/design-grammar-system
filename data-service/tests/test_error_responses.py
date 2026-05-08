"""Tests for structured error responses from validation endpoints (Phase 06 Plan 02, INTG-03)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app, _structured_error_response

client = TestClient(app, raise_server_exceptions=False)


def _assert_structured_body(body: dict) -> None:
    """Assert the response body has exactly the 3 structured error keys."""
    assert "error" in body, f"Missing 'error' key in {body}"
    assert "hint" in body, f"Missing 'hint' key in {body}"
    assert "code" in body, f"Missing 'code' key in {body}"
    assert isinstance(body["error"], str)
    assert isinstance(body["hint"], str)
    assert isinstance(body["code"], str)


@patch("app.get_integration_config", return_value=None)
def test_publish_validation_missing_config(mock_cfg):
    """POST /validation/publish with a non-existent project returns structured 404."""
    response = client.post("/validation/publish", json={
        "project": "nonexistent-project-xyz",
        "rules": [],
        "entities": [],
    })
    assert response.status_code == 404
    body = response.json()
    detail = body.get("detail", body)
    _assert_structured_body(detail)
    assert detail["code"] == "SPECKLE_CONFIG_MISSING"


@patch("app.get_validation_run", return_value=None)
def test_delete_run_not_found(mock_run):
    """DELETE /validation/run/{project}/{run_id} with fake IDs returns structured 404."""
    response = client.delete("/validation/run/fake-project/fake-run-id")
    assert response.status_code == 404
    body = response.json()
    detail = body.get("detail", body)
    _assert_structured_body(detail)
    assert detail["code"] == "RUN_NOT_FOUND"


def test_error_response_shape():
    """_structured_error_response produces exactly 3 keys: error, hint, code."""
    exc = _structured_error_response("Something broke", "Try this fix", "ERR_CODE", 422)
    assert exc.status_code == 422
    detail = exc.detail
    assert set(detail.keys()) == {"error", "hint", "code"}
    assert detail["error"] == "Something broke"
    assert detail["hint"] == "Try this fix"
    assert detail["code"] == "ERR_CODE"
