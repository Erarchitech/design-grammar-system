"""Tests for validation runs state projection (Phase 05 Plan 01, MVGP-02)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import _project_state_summary


def test_state_projection_valid_full_payload():
    payload = (
        '{"stateId":"S-001",'
        '"capturedAtUtc":"2026-05-01T10:00:00.0000000Z",'
        '"parameters":['
        '{"parameterId":"p1","displayName":"Height","type":"number","value":75.0},'
        '{"parameterId":"p2","displayName":"Floors","type":"integer","value":12}'
        ']}'
    )
    result = _project_state_summary(payload)
    assert result == {
        "stateId": "S-001",
        "capturedAtUtc": "2026-05-01T10:00:00.0000000Z",
        "parameterCount": 2,
    }


def test_state_projection_none_returns_none():
    assert _project_state_summary(None) is None


def test_state_projection_empty_string_returns_none():
    assert _project_state_summary("") is None


def test_state_projection_malformed_json_returns_none():
    assert _project_state_summary("not-valid-json") is None


def test_state_projection_non_object_json_returns_none():
    # JSON valid but not an object — should not crash, must return None
    assert _project_state_summary("[1, 2, 3]") is None
    assert _project_state_summary('"just-a-string"') is None
    assert _project_state_summary("42") is None


def test_state_projection_missing_stateid_uses_empty_string():
    payload = '{"capturedAtUtc":"2026-05-01T10:00:00Z","parameters":[]}'
    result = _project_state_summary(payload)
    assert result is not None
    assert result["stateId"] == ""
    assert result["capturedAtUtc"] == "2026-05-01T10:00:00Z"
    assert result["parameterCount"] == 0


def test_state_projection_missing_parameters_yields_zero_count():
    payload = '{"stateId":"S-002","capturedAtUtc":"2026-05-01T10:00:00Z"}'
    result = _project_state_summary(payload)
    assert result == {
        "stateId": "S-002",
        "capturedAtUtc": "2026-05-01T10:00:00Z",
        "parameterCount": 0,
    }


def test_state_projection_parameters_not_a_list_yields_zero_count():
    payload = '{"stateId":"S-003","capturedAtUtc":"2026-05-01T10:00:00Z","parameters":"oops"}'
    result = _project_state_summary(payload)
    assert result == {
        "stateId": "S-003",
        "capturedAtUtc": "2026-05-01T10:00:00Z",
        "parameterCount": 0,
    }


def test_state_projection_does_not_raise_on_garbage_input():
    # Defensive: any string survives without exception.
    for garbage in ["{", "}", "{not:json}", "\x00\x01", "[" * 1000]:
        try:
            _project_state_summary(garbage)
        except Exception as e:
            pytest.fail(f"_project_state_summary raised on input {garbage!r}: {e}")
