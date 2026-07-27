"""Phase 39 Wave 0 fixtures for the DesignState Auto-Validation watcher
(`dsav_watcher.py`). Pure data + a duck-typed session double -- no pytest
import, no Neo4j, no `app` import.

`FIXTURE_PROJECT` (P-03) pins this phase's isolation string per the Phase
37-01 convention documented in `data-service/tests/README.md` ("any test
that publishes into a live Neo4j must scope itself to a project string no
other suite uses"): distinct from `p37-structure` (`cg_fixtures.py`), `p1`
(`test_computgraph_publish.py`'s `GOLDEN_PROJECT`), and `default-project`.
"""

from __future__ import annotations

import json
from typing import Any, Callable

FIXTURE_PROJECT = "p39-autoval"


# ── DesignState v2 envelope builders ─────────────────────────────────────────


def capture_envelope(state_id: str = "DS_P39_1", obj_labels: list[str] | None = None) -> dict:
    """Build a schema-v2 DesignState envelope (`version`, `stateId`,
    `capturedAtUtc`, `objStates`/`paramStates`/`propStates`), matching the
    real envelope shape `data-service/tests/test_validation_runs_state.py`
    exercises. Each label in `obj_labels` becomes one objState carrying a
    `stateId` of the form `OS_<n>` and a `label` -- the exact join key
    `label or objectRef or stateId` P-02's `derive_valid_status()` depends
    on. Defaults to two objStates."""
    labels = obj_labels if obj_labels is not None else ["FrameColumn", "FrameBeam"]
    return {
        "version": "2",
        "stateId": state_id,
        "capturedAtUtc": "2026-07-27T10:00:00.0000000Z",
        "objStates": [
            {"stateId": f"OS_{i + 1}", "label": label} for i, label in enumerate(labels)
        ],
        "paramStates": [],
        "propStates": [],
    }


def capture_envelope_json(state_id: str = "DS_P39_1", obj_labels: list[str] | None = None) -> str:
    return json.dumps(capture_envelope(state_id=state_id, obj_labels=obj_labels))


# ── SHACL verdict builders (dg-reasoner `_call_shacl_validate` success body) ─


def _violation(
    focus_label: str = "", what: str = "Violation", shape_id: str = "SomeShape"
) -> dict:
    """One sanitized finding, matching `reasoning._enrich_shacl_result`'s
    `{severity, what, where, howToFix, focusLabel, shapeId}` shape -- no raw
    focus-node IRI, no `sh:*` term, ever."""
    return {
        "severity": "violation",
        "what": what,
        "where": focus_label or "(unresolved)",
        "howToFix": "Fix the reported condition.",
        "focusLabel": focus_label,
        "shapeId": shape_id,
    }


def shacl_ok(conforms: bool = True, violations: list[dict] | None = None) -> dict:
    """Build the `{"status":"ok","conforms":...,"results":[...],"counts":{...}}`
    envelope `_call_shacl_validate` returns on success."""
    results = list(violations) if violations else []
    counts = {"violation": 0, "warning": 0, "info": 0}
    for finding in results:
        severity = finding.get("severity", "violation")
        counts[severity] = counts.get(severity, 0) + 1
    return {
        "status": "ok",
        "conforms": conforms,
        "results": results,
        "counts": counts,
    }


def mapped_violation(label: str, what: str = "Violation") -> dict:
    """A violation whose `focusLabel` matches an objState's `label` exactly."""
    return _violation(focus_label=label, what=what)


def unmapped_violation(what: str = "Unresolvable violation") -> dict:
    """A violation whose `focusLabel` matches no objState -- exercises P-02's
    conservative "every index false" fallback."""
    return _violation(focus_label="NoSuchObject", what=what)


# ── Duck-typed Neo4j session double, dispatching by query identity ──────────

# Each of dsav_watcher.py's eight Cypher constants contains one of these
# markers exactly once and no other constant contains it -- confirmed by
# direct read of dsav_watcher.py at fixture-authoring time. Used to route a
# `.run(query, **params)` call to the right canned-rows handler without
# comparing the full query text.
QUERY_MARKERS: dict[str, str] = {
    "enabled_projects": "cfg.project AS project",
    "config_read": "AS debounceWindowSeconds",
    "config_upsert": "cfg.updatedAt = $updatedAt",
    "capture": "run.attempts = 0",
    "newest_captured": "capturedCount",
    "coalesce": "supersededCount",
    "complete": "verdictSource = 'shacl'",
    "fail": "lastError",
}

RouteHandler = Callable[[dict[str, Any]], list[dict[str, Any]]]


class DsavFixtureSession:
    """Duck-types `neo4j.Session.run(query, **params)` with zero live Neo4j.

    Unlike `test_dg_context.py`'s single-fixed-list `FixtureSession`,
    `poll_once()` issues several distinct queries per tick, so this variant
    dispatches by query identity: constructed with a mapping from a query
    marker name (see `QUERY_MARKERS`) to either a fixed list of row dicts or
    a callable `(params) -> list[dict]` for stateful/dynamic scenarios (e.g.
    an attempt counter that increments across ticks). Every `(query, params)`
    pair is recorded on `self.calls` so tests can assert the bound-parameter
    contract without live Neo4j.
    """

    def __init__(self, routes: dict[str, list[dict] | RouteHandler] | None = None):
        self.routes: dict[str, list[dict] | RouteHandler] = dict(routes or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, query: str, **params: Any) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        for name, marker in QUERY_MARKERS.items():
            if marker in query:
                handler = self.routes.get(name)
                if handler is None:
                    return []
                if callable(handler):
                    return list(handler(params))
                return list(handler)
        raise AssertionError(
            f"DsavFixtureSession: query matched no known marker:\n{query}"
        )

    def calls_for(self, marker_name: str) -> list[tuple[str, dict[str, Any]]]:
        """Every recorded `(query, params)` call whose query matched the
        named marker -- the assertion helper for the bound-parameter
        contract."""
        marker = QUERY_MARKERS[marker_name]
        return [(q, p) for (q, p) in self.calls if marker in q]

    def call_count(self, marker_name: str) -> int:
        return len(self.calls_for(marker_name))
