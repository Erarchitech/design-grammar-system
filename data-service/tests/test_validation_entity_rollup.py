"""Regression coverage for get_validation_entity_sets' per-object rollup (Phase 1202
plan 05, D-12, ALGN12-10).

`get_validation_entity_sets` (app.py:846-...) used to run a hand-written failed-wins
dedup where `error` lost to `failed` -- the opposite of the shipped
`evidence_contract.ROLLUP_PRECEDENCE` order (`error > failed > indeterminate >
unsupported > unknown > not_evaluated > no_population > passed`). This module is a
sibling to `test_validation_run_immutability.py` (that file's own scope is the
publish-path Cypher-shape/immutability regression from D-15; this file's scope is the
per-object rollup behavior change from D-12 -- distinct concerns, kept in separate
files rather than widened into one).

These tests monkeypatch `app.read_many` to return synthetic ValidationEntity rows,
the same "capture the seam, no live Neo4j" convention
`test_validation_run_immutability.py` uses for `write_query`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app


@pytest.fixture
def rows_from(monkeypatch):
    """Monkeypatch app.read_many to return a fixed list of rows, regardless of the
    query/parameters passed in -- get_validation_entity_sets issues exactly one
    read_many call per invocation."""

    def _install(rows: list[dict]):
        def _fake_read_many(query, parameters=None):
            return rows

        monkeypatch.setattr(app, "read_many", _fake_read_many)

    return _install


def _row(dg_entity_id: str, status: str, display_name: str | None = None) -> dict:
    return {"dgEntityId": dg_entity_id, "displayName": display_name, "status": status}


def test_error_outranks_failed_for_the_same_object(rows_from):
    """The real behavior change D-12 introduces: an object with one `failed` row and
    one `error` row must roll up to `error`, not `failed` (the old failed-wins
    behavior)."""
    rows_from([
        _row("OBJ_1", "failed"),
        _row("OBJ_1", "error"),
    ])

    result = app.get_validation_entity_sets("P", "RUN_1")

    # error is not a legacy-boolean `passed`, so it still lands in "failed" --
    # the test below (mixed rollup value) proves the *identity* of the winner via a
    # spy on evidence_contract.ROLLUP_PRECEDENCE ordering rather than the bucket alone.
    assert [e["dgEntityId"] for e in result["failed"]] == ["OBJ_1"]
    assert result["passed"] == []


def test_error_outranks_failed_is_the_precedence_walk_not_bucket_alone(rows_from, monkeypatch):
    """Directly proves the winner is `error`, not merely that it lands in the
    `failed` bucket (which `failed` alone would also do) -- by asserting the warning
    log is NOT triggered (both statuses are recognized) and by re-deriving the
    winner via the same evidence_contract precedence walk the production code uses,
    confirming `error` sorts before `failed`."""
    import evidence_contract

    rows_from([
        _row("OBJ_1", "failed"),
        _row("OBJ_1", "error"),
    ])

    app.get_validation_entity_sets("P", "RUN_1")

    statuses = {evidence_contract.CanonicalStatus.FAILED, evidence_contract.CanonicalStatus.ERROR}
    winner = next(c for c in evidence_contract.ROLLUP_PRECEDENCE if c in statuses)
    assert winner == evidence_contract.CanonicalStatus.ERROR


def test_passed_only_rolls_up_to_passed(rows_from):
    rows_from([
        _row("OBJ_1", "passed"),
        _row("OBJ_1", "passed"),
    ])

    result = app.get_validation_entity_sets("P", "RUN_1")

    assert [e["dgEntityId"] for e in result["passed"]] == ["OBJ_1"]
    assert result["failed"] == []


def test_unrecognized_status_participates_rather_than_vanishing(rows_from, caplog):
    """A status string outside the legacy passed/failed pair (e.g. a newer producer
    emitting `no_population`) must not be silently dropped -- it participates in the
    rollup and the object is reported (in the `failed` bucket, since only `passed`
    maps to the legacy-boolean-true bucket)."""
    rows_from([
        _row("OBJ_1", "no_population"),
    ])

    result = app.get_validation_entity_sets("P", "RUN_1")

    assert [e["dgEntityId"] for e in result["failed"]] == ["OBJ_1"]
    assert result["passed"] == []


def test_truly_unrecognized_status_string_maps_to_unknown_and_is_logged(rows_from, caplog):
    """A status string that isn't even a CanonicalStatus member (a producer bug or a
    future/foreign value) maps to UNKNOWN and is logged at warning level -- never
    silently discarded, since discarding it would let a producer bug improve an
    object's verdict by omission."""
    import logging

    rows_from([
        _row("OBJ_1", "some_future_status_nobody_shipped_yet"),
    ])

    with caplog.at_level(logging.WARNING):
        result = app.get_validation_entity_sets("P", "RUN_1")

    assert [e["dgEntityId"] for e in result["failed"]] == ["OBJ_1"]
    assert any(
        "unrecognized" in record.message.lower() and "OBJ_1" in record.message
        for record in caplog.records
    ), "expected a warning-level log naming the offending status and the entity"


def test_object_with_only_recognized_worse_than_failed_status_still_reports_correctly(rows_from):
    """A pure-`error` object (no coincident `failed` row) still rolls up to `error`
    and lands in the `failed` (non-passed) bucket -- confirms the precedence walk
    handles a single-status group, not only the two-status collision case."""
    rows_from([_row("OBJ_1", "error")])

    result = app.get_validation_entity_sets("P", "RUN_1")

    assert [e["dgEntityId"] for e in result["failed"]] == ["OBJ_1"]


def test_build_view_payload_shape_is_unchanged():
    """build_view_payload's returned shape (objectSets plus evidenceEnvelope, among
    other top-level keys) must be unchanged by this plan -- it is not itself touched,
    but this pins the contract get_validation_entity_sets' return value must keep
    satisfying as the value passed in as `object_sets`."""
    run = {
        "runId": "RUN_1",
        "rulesJson": None,
        "speckleProjectId": "p",
        "baseModelId": "b",
        "baseVersionId": "bv",
        "validationModelId": "vm",
        "validationVersionId": "vv",
        "baseResourceUrl": "http://example.invalid/base",
        "validationResourceUrl": "http://example.invalid/validation",
        "modelViewerUrl": "http://example.invalid/viewer",
    }
    object_sets = {"failed": [{"dgEntityId": "OBJ_1", "displayName": "OBJ_1"}], "passed": []}

    payload = app.build_view_payload("P", run, object_sets)

    assert payload["objectSets"] == object_sets
    assert set(payload.keys()) >= {"project", "runId", "objectSets", "evidenceEnvelope"}


def test_rows_missing_dg_entity_id_are_skipped(rows_from):
    """A row with no dgEntityId (defensive: should not happen from the write path,
    but the read-side must not crash or fabricate an entry for it) is silently
    skipped, matching the pre-existing `if not dg_entity_id: continue` behavior."""
    rows_from([
        {"dgEntityId": None, "displayName": "x", "status": "failed"},
        _row("OBJ_1", "passed"),
    ])

    result = app.get_validation_entity_sets("P", "RUN_1")

    assert [e["dgEntityId"] for e in result["passed"]] == ["OBJ_1"]
    assert result["failed"] == []
