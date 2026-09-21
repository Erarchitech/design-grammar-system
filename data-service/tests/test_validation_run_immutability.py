"""RED regression proving the ValidationRun publish path must not overwrite
immutable snapshot fields on re-publish (Phase 1202 plan 01 Task 2, D-15).

`store_validation_run` (app.py:549-607) today issues a single MERGE followed
by one unconditional `SET` clause that writes both the immutable snapshot
(`rulesJson`, `statePayloadJson`, `createdAt`) and the mutable run status
(`status`, `ValidStatus`, `SendStatus`) onto the same `:ValidationRun` node.
Because the MERGE key is `(graph, project, runId)`, re-publishing the same
`runId` today silently clobbers the original snapshot -- there is no
`ON CREATE SET` split.

These tests do not require a live Neo4j: `write_query` is monkeypatched at
module level (the same seam `app.py` calls through for every write), and the
emitted Cypher text + parameter dict are captured for inspection. This is
the "capture the emitted Cypher string" convention this plan's PLAN.md
specifies for this exact case, since `test_validation_runs_state.py` (the
closest existing analog) tests pure projection functions that never reach
`write_query` at all and has no stubbing convention of its own to copy.

The IMMUTABLE_PROPERTIES / MUTABLE_PROPERTIES constants below are the same
contract plan 05 (D-15) codifies in `spec/DATABASE.md` -- this test file and
that spec update describe one contract, not two.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re

import pytest

import app


# Declaring authority: spec/DATABASE.md (Phase 1202 plan 05, D-15) documents
# this exact split between immutable snapshot identity and mutable
# operational/run status on the shared `:ValidationRun` node.
IMMUTABLE_PROPERTIES = {"rulesJson", "statePayloadJson", "createdAt"}
MUTABLE_PROPERTIES = {"status", "ValidStatus", "SendStatus"}


def _split_set_clauses(cypher: str) -> tuple[str, str]:
    """Split a MERGE...SET Cypher string into its `ON CREATE SET` clause body
    and its plain (unconditional) `SET` clause body.

    Splits on the `ON CREATE SET` and trailing `SET` *keywords* -- not on a
    naive substring scan -- so a property name appearing anywhere else in the
    query text (e.g. inside a comment or another clause) cannot masquerade as
    membership in either clause. Returns ("", <whole-query-set-body>) when no
    `ON CREATE SET` clause is present at all, which is today's (pre-D-15)
    shape and is exactly what these tests must detect as the RED state.
    """
    on_create_match = re.search(
        r"ON CREATE SET\s+(.*?)(?=\bSET\b|\Z)", cypher, re.DOTALL | re.IGNORECASE
    )
    # The plain SET clause is whatever SET keyword is NOT part of
    # "ON CREATE SET" / "ON MATCH SET". Find every top-level SET occurrence
    # and take the one that is not immediately preceded by "ON CREATE " or
    # "ON MATCH ".
    plain_set_match = re.search(
        r"(?<!CREATE )(?<!MATCH )\bSET\s+(.*)\Z", cypher, re.DOTALL | re.IGNORECASE
    )

    on_create_body = on_create_match.group(1) if on_create_match else ""
    plain_body = plain_set_match.group(1) if plain_set_match else ""
    return on_create_body, plain_body


def _properties_assigned_in(clause_body: str) -> set[str]:
    """Extract the set of `run.<property> = ...` property names assigned in a
    SET clause body, by parsing `run.<name>` tokens rather than substring
    matching -- so a property name that merely appears as part of a longer
    identifier or a parameter name is never falsely counted as assigned."""
    return set(re.findall(r"run\.([A-Za-z_][A-Za-z0-9_]*)\s*=", clause_body))


@pytest.fixture
def captured_queries(monkeypatch):
    """Monkeypatch app.write_query to capture every (cypher, parameters) pair
    the publish path emits, without touching a real Neo4j driver/session."""
    calls: list[tuple[str, dict]] = []

    def _fake_write_query(query, parameters=None):
        calls.append((query, parameters or {}))

    monkeypatch.setattr(app, "write_query", _fake_write_query)
    return calls


def _publish(run_id: str, created_at_hint: str | None = None):
    """Drive app.store_validation_run with a minimal, valid payload. The
    function itself computes `createdAt` internally (datetime.now), so
    `created_at_hint` is accepted only for documentation/readability at call
    sites -- it is not threaded into the call, matching store_validation_run's
    actual signature (app.py:549-558)."""
    config = app.SpeckleProjectConfigPayload()
    publish_result = {
        "baseVersionId": "v1",
        "validationModelId": "model-1",
        "validationVersionId": "vv1",
        "modelViewerUrl": "http://example.invalid/viewer",
        "baseResourceUrl": "http://example.invalid/base",
        "validationResourceUrl": "http://example.invalid/validation",
    }
    rules_summary = [{"ruleId": "R_GOLD_HEIGHT_MAX_75_V", "passed": True}]
    entities: list[dict] = []
    app.store_validation_run(
        project="DG-1202-REPLAY",
        run_id=run_id,
        config=config,
        publish_result=publish_result,
        rules_summary=rules_summary,
        entities=entities,
        state_payload_json='{"version":"2","stateId":"DS_1"}',
        valid_status_param=[True],
    )


def test_publish_cypher_writes_immutable_snapshot_fields_on_create_only(captured_queries):
    _publish("R_TEST_IMMUTABILITY_01")

    # The first write_query call is store_validation_run's own MERGE+SET
    # (app.py:571-589); entity_rows is empty here so no second call is made.
    cypher, _params = captured_queries[0]
    on_create_body, plain_body = _split_set_clauses(cypher)

    on_create_props = _properties_assigned_in(on_create_body)
    plain_props = _properties_assigned_in(plain_body)

    # RED today: rulesJson/statePayloadJson/createdAt are written by the one
    # unconditional SET clause, and no ON CREATE SET clause exists at all.
    for prop in IMMUTABLE_PROPERTIES:
        assert prop in on_create_props, (
            f"Expected '{prop}' to appear in an ON CREATE SET clause (write-once "
            f"snapshot identity, D-15), but it was not found there. "
            f"on_create_props={on_create_props!r} plain_props={plain_props!r} "
            f"cypher={cypher!r}"
        )
        assert prop not in plain_props, (
            f"'{prop}' must never appear in the unconditional SET clause -- it "
            f"is immutable snapshot content per D-15, not mutable status."
        )


def test_publish_cypher_writes_mutable_status_fields_on_every_write(captured_queries):
    _publish("R_TEST_IMMUTABILITY_02")

    cypher, _params = captured_queries[0]
    on_create_body, plain_body = _split_set_clauses(cypher)

    on_create_props = _properties_assigned_in(on_create_body)
    plain_props = _properties_assigned_in(plain_body)

    for prop in MUTABLE_PROPERTIES:
        assert prop in plain_props, (
            f"Expected '{prop}' to appear in the unconditional SET clause (it "
            f"must keep updating on every re-publish, D-15), but it was not "
            f"found there. on_create_props={on_create_props!r} "
            f"plain_props={plain_props!r} cypher={cypher!r}"
        )
        assert prop not in on_create_props, (
            f"'{prop}' must never be write-once via ON CREATE SET -- it is "
            f"mutable operational/run status per D-15, not immutable snapshot "
            f"content."
        )


def test_republish_same_run_id_preserves_original_created_at(captured_queries):
    """Publish the same runId twice. At the Cypher-shape level (this stub
    cannot simulate Neo4j's own MERGE/ON CREATE semantics -- there is no
    graph here, only captured query text) this asserts that `createdAt` is
    bound on both calls but is only ever placed in an `ON CREATE SET` clause,
    which MERGE's own semantics guarantee fires exactly once per node --
    the second call's `createdAt` value is bound as a parameter but the
    clause it lives in does not execute against an already-existing node.
    """
    _publish("R_TEST_IMMUTABILITY_03")
    _publish("R_TEST_IMMUTABILITY_03")

    assert len(captured_queries) >= 2

    for cypher, params in captured_queries[:2]:
        on_create_body, _plain_body = _split_set_clauses(cypher)
        on_create_props = _properties_assigned_in(on_create_body)
        assert "createdAt" in on_create_props, (
            "createdAt must be placed in an ON CREATE SET clause so MERGE's "
            "own semantics (fires only when the node is first created) "
            "preserve the original value across a re-publish with the same "
            "runId -- this stub verifies clause placement only; the graph "
            "itself is what makes the value actually stick."
        )
        assert "createdAt" in params, "createdAt must still be a bound parameter."


def test_immutable_and_mutable_property_sets_are_disjoint(captured_queries):
    """Regression guard: catches a future edit that silently moves a property
    across the immutable/mutable line without updating both sets here."""
    assert IMMUTABLE_PROPERTIES.isdisjoint(MUTABLE_PROPERTIES), (
        f"IMMUTABLE_PROPERTIES and MUTABLE_PROPERTIES must never share a "
        f"member: {IMMUTABLE_PROPERTIES & MUTABLE_PROPERTIES!r}"
    )

    _publish("R_TEST_IMMUTABILITY_04")
    cypher, _params = captured_queries[0]
    on_create_body, plain_body = _split_set_clauses(cypher)
    on_create_props = _properties_assigned_in(on_create_body)
    plain_props = _properties_assigned_in(plain_body)

    assert on_create_props.isdisjoint(plain_props), (
        f"A property must not be assigned in both the ON CREATE SET clause "
        f"and the unconditional SET clause of the same query: "
        f"{on_create_props & plain_props!r}"
    )
