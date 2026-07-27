"""Host-tier unit suite for `dsav_watcher.py` (Phase 39 Wave 0: DSAV-02).

Drives `poll_once()` and `derive_valid_status()` directly with an injected
`DsavFixtureSession` and an injected `now` clock -- zero live Neo4j, zero
thread, zero `time.sleep`, per D-03's explicit pure-function requirement.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import dsav_watcher  # noqa: E402
import dsav_fixtures  # noqa: E402
from dsav_fixtures import DsavFixtureSession, FIXTURE_PROJECT  # noqa: E402


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _config_row(**overrides) -> dict:
    row = {
        "enabled": True,
        "publishEnabled": False,
        "debounceWindowSeconds": 5.0,
        "rateLimitPerMinute": 6,
        "maxAttempts": 3,
    }
    row.update(overrides)
    return row


@pytest.fixture(autouse=True)
def _reset_guardrail_state():
    dsav_watcher.reset_guardrail_state()
    yield
    dsav_watcher.reset_guardrail_state()


# ── No enabled projects ──────────────────────────────────────────────────────


def test_no_enabled_projects_returns_noop_summary_and_issues_no_writes():
    session = DsavFixtureSession(routes={"enabled_projects": []})
    summary = dsav_watcher.poll_once(session=session, now=1000.0)

    assert summary["projects_seen"] == 0
    assert summary["skipped"] == {}
    assert summary["runs_completed"] == 0
    assert summary["runs_failed"] == 0
    # Only the enabled-projects read ran -- no coalesce/complete/fail write.
    assert len(session.calls) == 1


# ── Debounce ──────────────────────────────────────────────────────────────────


def test_debounce_hold_skips_with_reason_and_shacl_never_called():
    now = 1000.0
    captured_at = _iso(now - 2.0)  # 2s old, inside the 5s debounce window
    shacl_calls: list[tuple[str, str]] = []

    def shacl_fn(project, run_id):
        shacl_calls.append((project, run_id))
        return dsav_fixtures.shacl_ok()

    routes = {
        "enabled_projects": [{"project": FIXTURE_PROJECT}],
        "config_read": [_config_row()],
        "newest_captured": [
            {"runId": "run-1", "capturedAt": captured_at, "attempts": 0, "capturedCount": 1}
        ],
    }
    session = DsavFixtureSession(routes=routes)
    summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=shacl_fn)

    assert summary["skipped"] == {FIXTURE_PROJECT: "debounce_wait"}
    assert shacl_calls == []
    assert session.call_count("coalesce") == 0


def test_debounce_release_coalesces_five_captured_rows_marks_four_superseded():
    now = 1000.0
    captured_at = _iso(now - 10.0)  # older than the 5s debounce window
    envelope_json = dsav_fixtures.capture_envelope_json(obj_labels=["FrameColumn", "FrameBeam"])
    shacl_calls: list[tuple[str, str]] = []

    def shacl_fn(project, run_id):
        shacl_calls.append((project, run_id))
        return dsav_fixtures.shacl_ok(conforms=True)

    routes = {
        "enabled_projects": [{"project": FIXTURE_PROJECT}],
        "config_read": [_config_row()],
        "newest_captured": [
            {"runId": "run-kept", "capturedAt": captured_at, "attempts": 0, "capturedCount": 5}
        ],
        "coalesce": [
            {"keptRunId": "run-kept", "statePayloadJson": envelope_json, "supersededCount": 4}
        ],
    }
    session = DsavFixtureSession(routes=routes)
    summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=shacl_fn)

    assert summary["superseded"] == 4
    assert summary["runs_completed"] == 1
    assert shacl_calls == [(FIXTURE_PROJECT, "run-kept")]
    assert session.call_count("coalesce") == 1

    complete_calls = session.calls_for("complete")
    assert len(complete_calls) == 1
    complete_query, complete_params = complete_calls[0]
    assert "trigger" in complete_query and "verdictSource" in complete_query
    assert complete_params["validStatus"] == [True, True]
    assert complete_params["completedAt"]

    # The completion timestamp is appended to the project's rate-limit window.
    assert now in dsav_watcher._completion_timestamps.get(FIXTURE_PROJECT, [])


# ── Rate limiting ─────────────────────────────────────────────────────────────


def test_rate_limit_skips_when_window_is_full_and_shacl_never_called():
    now = 1000.0
    captured_at = _iso(now - 10.0)
    shacl_calls: list[tuple[str, str]] = []

    def shacl_fn(project, run_id):
        shacl_calls.append((project, run_id))
        return dsav_fixtures.shacl_ok()

    routes = {
        "enabled_projects": [{"project": FIXTURE_PROJECT}],
        "config_read": [_config_row(rateLimitPerMinute=2)],
        "newest_captured": [
            {"runId": "run-1", "capturedAt": captured_at, "attempts": 0, "capturedCount": 1}
        ],
    }
    session = DsavFixtureSession(routes=routes)

    # Pre-seed the guardrail window with rateLimitPerMinute (2) recent completions.
    dsav_watcher._record_completion(FIXTURE_PROJECT, now - 10.0)
    dsav_watcher._record_completion(FIXTURE_PROJECT, now - 5.0)

    summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=shacl_fn)

    assert summary["skipped"] == {FIXTURE_PROJECT: "rate_limited"}
    assert shacl_calls == []
    assert session.call_count("coalesce") == 0


# ── Complete path ─────────────────────────────────────────────────────────────


def test_complete_path_with_unmapped_violation_flips_every_objstate_and_counts_it():
    now = 1000.0
    captured_at = _iso(now - 10.0)
    envelope_json = dsav_fixtures.capture_envelope_json(obj_labels=["A", "B"])
    shacl_body = dsav_fixtures.shacl_ok(conforms=False, violations=[dsav_fixtures.unmapped_violation()])

    routes = {
        "enabled_projects": [{"project": FIXTURE_PROJECT}],
        "config_read": [_config_row()],
        "newest_captured": [
            {"runId": "run-x", "capturedAt": captured_at, "attempts": 0, "capturedCount": 1}
        ],
        "coalesce": [
            {"keptRunId": "run-x", "statePayloadJson": envelope_json, "supersededCount": 0}
        ],
    }
    session = DsavFixtureSession(routes=routes)
    summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=lambda p, r: shacl_body)

    assert summary["unmapped_violations"] == 1
    complete_calls = session.calls_for("complete")
    assert len(complete_calls) == 1
    _, complete_params = complete_calls[0]
    assert complete_params["validStatus"] == [False, False]


# ── Fail path (D-08 departure) ────────────────────────────────────────────────


class _FailCounter:
    """Stateful `FAIL_QUERY` handler simulating Neo4j's server-side
    `coalesce(run.attempts, 0) + 1` increment across sequential
    `poll_once()` calls -- a real Neo4j instance would persist this on the
    row; the fixture double tracks it in-process instead."""

    def __init__(self, max_attempts: int):
        self.attempts = 0
        self.max_attempts = max_attempts

    def __call__(self, params: dict) -> list[dict]:
        self.attempts += 1
        status = "failed" if self.attempts >= self.max_attempts else "captured"
        return [{"attempts": self.attempts, "status": status}]


def test_fail_path_shacl_timeout_flips_to_failed_on_third_attempt():
    """D-08 departure: the manual publish path (`publish_validation` ->
    `_call_shacl_validate`) treats a SHACL timeout/unavailable status as
    non-fatal and completes the run anyway (Phase 823 degrade-never-raise).
    The watcher deliberately does NOT inherit that policy here -- an
    auto-run that silently completes with no verdict is worse than a
    manual one, because nobody clicked anything to watch it. The row stays
    `status:'captured'` (retried) until `maxAttempts`, then flips to
    `status:'failed'`.
    """
    now = 1000.0
    captured_at = _iso(now - 10.0)
    envelope_json = dsav_fixtures.capture_envelope_json()
    fail_counter = _FailCounter(max_attempts=3)

    def make_session() -> DsavFixtureSession:
        return DsavFixtureSession(
            routes={
                "enabled_projects": [{"project": FIXTURE_PROJECT}],
                "config_read": [_config_row()],
                "newest_captured": [
                    {
                        "runId": "run-timeout",
                        "capturedAt": captured_at,
                        "attempts": fail_counter.attempts,
                        "capturedCount": 1,
                    }
                ],
                "coalesce": [
                    {
                        "keptRunId": "run-timeout",
                        "statePayloadJson": envelope_json,
                        "supersededCount": 0,
                    }
                ],
                "fail": fail_counter,
            }
        )

    def shacl_fn(project, run_id):
        return {"status": "timeout"}

    summary = None
    for _ in range(3):
        session = make_session()
        summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=shacl_fn)
        fail_calls = session.calls_for("fail")
        assert len(fail_calls) == 1
        _, fail_params = fail_calls[0]
        assert fail_params["reason"] == "timeout"
        assert session.calls_for("complete") == []  # COMPLETE_QUERY never ran

    assert fail_counter.attempts == 3
    assert summary["runs_failed"] == 1  # only the 3rd tick crosses maxAttempts


def test_fail_path_shacl_fn_none_never_completes_and_reason_is_no_response():
    now = 1000.0
    captured_at = _iso(now - 10.0)
    envelope_json = dsav_fixtures.capture_envelope_json()

    routes = {
        "enabled_projects": [{"project": FIXTURE_PROJECT}],
        "config_read": [_config_row()],
        "newest_captured": [
            {"runId": "run-none", "capturedAt": captured_at, "attempts": 0, "capturedCount": 1}
        ],
        "coalesce": [
            {"keptRunId": "run-none", "statePayloadJson": envelope_json, "supersededCount": 0}
        ],
        "fail": [{"attempts": 1, "status": "captured"}],
    }
    session = DsavFixtureSession(routes=routes)
    summary = dsav_watcher.poll_once(session=session, now=now, shacl_fn=None)

    fail_calls = session.calls_for("fail")
    assert len(fail_calls) == 1
    _, fail_params = fail_calls[0]
    assert fail_params["reason"] == "no_response"
    assert session.calls_for("complete") == []
    assert summary["runs_completed"] == 0


# ── derive_valid_status unit cases (P-02) ─────────────────────────────────────


def test_derive_valid_status_conforms_true_is_all_true():
    envelope_json = dsav_fixtures.capture_envelope_json(obj_labels=["A", "B", "C"])
    shacl_body = dsav_fixtures.shacl_ok(conforms=True)

    valid_status, unmapped = dsav_watcher.derive_valid_status(envelope_json, shacl_body)

    assert valid_status == [True, True, True]
    assert unmapped == 0


def test_derive_valid_status_mapped_violation_flips_exactly_one_index():
    envelope_json = dsav_fixtures.capture_envelope_json(obj_labels=["A", "B"])
    shacl_body = dsav_fixtures.shacl_ok(conforms=False, violations=[dsav_fixtures.mapped_violation("B")])

    valid_status, unmapped = dsav_watcher.derive_valid_status(envelope_json, shacl_body)

    assert valid_status == [True, False]
    assert unmapped == 0


def test_derive_valid_status_unmapped_violation_flips_every_index_and_reports_it():
    envelope_json = dsav_fixtures.capture_envelope_json(obj_labels=["A", "B"])
    shacl_body = dsav_fixtures.shacl_ok(conforms=False, violations=[dsav_fixtures.unmapped_violation()])

    valid_status, unmapped = dsav_watcher.derive_valid_status(envelope_json, shacl_body)

    assert valid_status == [False, False]
    assert unmapped == 1


def test_derive_valid_status_empty_envelope_returns_empty_list():
    envelope_json = json.dumps({"version": "2", "stateId": "DS_EMPTY", "objStates": []})

    valid_status, unmapped = dsav_watcher.derive_valid_status(envelope_json, dsav_fixtures.shacl_ok())

    assert valid_status == []
    assert unmapped == 0


def test_derive_valid_status_unparseable_json_returns_empty_list_without_raising():
    valid_status, unmapped = dsav_watcher.derive_valid_status("{not valid json", dsav_fixtures.shacl_ok())

    assert valid_status == []
    assert unmapped == 0


# ── Publish gating ────────────────────────────────────────────────────────────


def _complete_path_session(envelope_json: str, publish_enabled: bool) -> DsavFixtureSession:
    now = 1000.0
    captured_at = _iso(now - 10.0)
    return DsavFixtureSession(
        routes={
            "enabled_projects": [{"project": FIXTURE_PROJECT}],
            "config_read": [_config_row(publishEnabled=publish_enabled)],
            "newest_captured": [
                {"runId": "run-pub", "capturedAt": captured_at, "attempts": 0, "capturedCount": 1}
            ],
            "coalesce": [
                {"keptRunId": "run-pub", "statePayloadJson": envelope_json, "supersededCount": 0}
            ],
        }
    )


def test_publish_gating_disabled_never_calls_publish_fn():
    envelope_json = dsav_fixtures.capture_envelope_json()
    publish_calls: list[tuple[str, str]] = []

    def publish_fn(project, run_id):
        publish_calls.append((project, run_id))

    session = _complete_path_session(envelope_json, publish_enabled=False)
    summary = dsav_watcher.poll_once(
        session=session,
        now=1000.0,
        shacl_fn=lambda p, r: dsav_fixtures.shacl_ok(),
        publish_fn=publish_fn,
    )

    assert publish_calls == []
    assert summary["publish_attempted"] == 0


def test_publish_gating_enabled_calls_publish_fn_once_after_completion():
    envelope_json = dsav_fixtures.capture_envelope_json()
    publish_calls: list[tuple[str, str]] = []

    def publish_fn(project, run_id):
        publish_calls.append((project, run_id))

    session = _complete_path_session(envelope_json, publish_enabled=True)
    summary = dsav_watcher.poll_once(
        session=session,
        now=1000.0,
        shacl_fn=lambda p, r: dsav_fixtures.shacl_ok(),
        publish_fn=publish_fn,
    )

    assert publish_calls == [(FIXTURE_PROJECT, "run-pub")]
    assert summary["publish_attempted"] == 1
    assert summary["publish_errors"] == 0
    assert summary["runs_completed"] == 1


def test_publish_gating_publish_fn_raising_is_reported_but_run_still_completes():
    envelope_json = dsav_fixtures.capture_envelope_json()

    def publish_fn(project, run_id):
        raise RuntimeError("speckle unreachable")

    session = _complete_path_session(envelope_json, publish_enabled=True)
    summary = dsav_watcher.poll_once(
        session=session,
        now=1000.0,
        shacl_fn=lambda p, r: dsav_fixtures.shacl_ok(),
        publish_fn=publish_fn,
    )

    assert summary["publish_errors"] == 1
    assert summary["publish_attempted"] == 1
    assert summary["runs_completed"] == 1  # publish failure never reverts the verdict


# ── Config helpers ─────────────────────────────────────────────────────────────


def test_get_auto_validation_config_absent_row_returns_none():
    session = DsavFixtureSession(routes={"config_read": []})

    config = dsav_watcher.get_auto_validation_config(FIXTURE_PROJECT, session=session)

    assert config is None


def test_get_auto_validation_config_partial_row_coerces_to_module_defaults():
    session = DsavFixtureSession(
        routes={
            "config_read": [
                {
                    "enabled": True,
                    "publishEnabled": None,
                    "debounceWindowSeconds": None,
                    "rateLimitPerMinute": None,
                    "maxAttempts": None,
                }
            ]
        }
    )

    config = dsav_watcher.get_auto_validation_config(FIXTURE_PROJECT, session=session)

    assert config.enabled is True
    assert config.publish_enabled is False
    assert config.debounce_window_seconds == dsav_watcher.DEFAULT_DEBOUNCE_WINDOW_SECONDS
    assert config.rate_limit_per_minute == dsav_watcher.DEFAULT_RATE_LIMIT_PER_MINUTE
    assert config.max_attempts == dsav_watcher.DEFAULT_MAX_ATTEMPTS


def test_upsert_auto_validation_config_writes_config_upsert_query():
    session = DsavFixtureSession(routes={"config_upsert": []})
    config = dsav_watcher.AutoValidationConfig(enabled=True, publish_enabled=True)

    dsav_watcher.upsert_auto_validation_config(FIXTURE_PROJECT, config, session=session)

    upsert_calls = session.calls_for("config_upsert")
    assert len(upsert_calls) == 1
    _, params = upsert_calls[0]
    assert params["enabled"] is True
    assert params["publishEnabled"] is True
    assert params["project"] == FIXTURE_PROJECT
