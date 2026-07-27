"""Phase 39 Wave 3 live-Docker evidence driver for the DesignState
Auto-Validation loop (DSAV-01 / DSAV-02).

This module is the *only* place in Phase 39 where the loop runs for real:
against the live uvicorn process whose FastAPI `lifespan` owns the watcher
daemon (P-12), against live Neo4j 5.26, and against the live `dg-reasoner`
SHACL sidecar. Everything Waves 1 and 2 asserted with a fixture session or a
`TestClient` is re-asserted here through HTTP + bolt.

Run it inside the compose network -- the `neo4j` and `dg-reasoner` hostnames
resolve nowhere else -- and select it explicitly, because it is `live`-marked
and therefore deselected by a bare `pytest` run:

    docker compose exec -T data-service python -m pytest \
        tests/test_dsav_live_loop.py -q -m "integration and live"

The `live` marker was added after Phase 39 Wave 4 (operator-authorized at the
39-04 checkpoint). This module's `live_session` fixture DELETES every
`:ValidationRun` and `:IntegrationConfig` scoped to `p39-autoval` at both
setup and teardown. While the module was `integration`-only, a routine
`pytest tests/ -q` collected it and silently destroyed the phase's published
run row -- the very evidence Wave 4 had just measured. The marker makes
running this module a deliberate act, matching `test_dsav_publish_leg.py`.

**The image must be rebuilt first.** `data-service/tests/` has no live bind
mount, so this file (and `dsav_watcher.py`, `dsav_fixtures.py`) is invisible
inside a stale container. See `data-service/tests/README.md` -> "Known gotcha
-- image staleness".

Evidence (P-11): the repository is mounted read-only at `/mnt/repo`, so this
module cannot write into `.planning/`. It writes to `DSAV_EVIDENCE_PATH`
(default `/app/data/dsav-evidence.json`) on the writable `./data-service/data`
bind mount; the executor copies that file to the phase directory. No token or
credential ever reaches the artifact.

Timings (P-13) are read back off the row's own `capturedAt`/`completedAt`
properties, never off an in-process stopwatch: the row is the auditable
record, and a wall-clock timer would additionally fold in the poll interval's
phase offset in a way nobody can reproduce.

Guardrail note (D-15): the watcher's rate-limit window lives in the
data-service process's memory. Re-running this module within 60 seconds of a
previous run can therefore start with a partly-full window. Restart
`data-service` (or wait a minute) between consecutive measured runs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dsav_watcher  # noqa: E402
from dsav_fixtures import FIXTURE_PROJECT, capture_envelope, capture_envelope_json  # noqa: E402

# `integration` = needs the compose network. `live` = it mutates shared live
# state (it scrubs every p39-autoval row) and so must never be collected by a
# bare `pytest` run. Same convention as `test_dsav_publish_leg.py`, so both
# modules behave identically under `-m "integration and live"`.
pytestmark = [pytest.mark.integration, pytest.mark.live]

# ── T-39-10 isolation guard ─────────────────────────────────────────────────
# Every write this module performs is scoped to this one project string, and
# it must not collide with any other suite sharing the Neo4j instance.
assert FIXTURE_PROJECT == "p39-autoval", (
    "Phase 39 reserves exactly one live-Neo4j project string; the fixture "
    "module changed it out from under this driver."
)
assert FIXTURE_PROJECT not in {"p37-structure", "p1", "default-project"}

# ── Environment-selected targets ─────────────────────────────────────────────

# P-12: drive HTTP against the running service, not the app object. Inside the
# container this is the local uvicorn process; from the host it is the
# published port; on the compose network it is http://data-service:8000.
BASE_URL = os.getenv("DSAV_TARGET_BASE_URL", "http://localhost:8000").rstrip("/")

# P-11: the writable bind mount, not the read-only /mnt/repo.
EVIDENCE_PATH = os.getenv("DSAV_EVIDENCE_PATH", "/app/data/dsav-evidence.json")

CONNECTOR_ID = "grasshopper"
HTTP_TIMEOUT_SECONDS = 20.0

# ── P-14 pinned guardrail parameters ─────────────────────────────────────────
# Pinned so the numbers are reproducible. Every measurement records the
# parameters that produced it -- a measurement without its configuration is
# not evidence.

SC1_DEBOUNCE_SECONDS = 2.0
SC1_RATE_LIMIT_PER_MINUTE = 30

SC2_DEBOUNCE_SECONDS = 5.0
SC2_RATE_LIMIT_PER_MINUTE = 3

MAX_ATTEMPTS = 3
PUBLISH_ENABLED = False  # T-39-04: persist-only throughout; Speckle is untouched.

BURST_CAPTURES = 8
RPM_WINDOW_SECONDS = 60.0
RPM_CYCLE_CAPTURES = 4
RPM_CYCLE_CAPTURE_INTERVAL_SECONDS = 1.0
RPM_CYCLE_IDLE_SECONDS = 8.0
RPM_SETTLE_SECONDS = 6.0

# A debounce window nothing will ever outlive: parks the live daemon on
# `debounce_wait` so tests 4-6 can drive the state machine themselves without
# racing it, while keeping the config `enabled` (which `poll_once` requires).
PARKED_DEBOUNCE_SECONDS = 3600.0

SC1_DEADLINE_SECONDS = 30.0  # debounce + 4 poll intervals + the 15s SHACL timeout
SC2_DEADLINE_SECONDS = 45.0

# ── Measurement accumulator ─────────────────────────────────────────────────

MEASUREMENTS: dict[str, Any] = {}
EXPECTED_MEASUREMENTS = (
    "sc1_loop_closure",
    "sc2_collapse",
    "sc2_runs_per_minute",
    "d08_failure_ladder",
    "list_runs_tolerance",
    "cypher_shapes",
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    """Parse an ISO-8601 row timestamp, tolerating a trailing `Z` and
    treating a naive timestamp as UTC. Returns None on anything unparseable
    -- a measurement is never invented from a bad string."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _enable_auto_validation(
    session: Any,
    debounce_window_seconds: float,
    rate_limit_per_minute: int,
    max_attempts: int = MAX_ATTEMPTS,
    enabled: bool = True,
) -> None:
    """P-06: there is deliberately no configuration route, so the driver
    enables auto-validation out of band through the watcher module itself."""
    dsav_watcher.upsert_auto_validation_config(
        FIXTURE_PROJECT,
        dsav_watcher.AutoValidationConfig(
            enabled=enabled,
            publish_enabled=PUBLISH_ENABLED,
            debounce_window_seconds=debounce_window_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
            max_attempts=max_attempts,
        ),
        session=session,
    )


def _post_capture(token: str, payload_json: str | None = None) -> dict[str, Any]:
    """One authenticated capture across the same trust boundary a real
    connector crosses (T-39-01). Raises on any non-2xx so a broken capture
    can never be silently measured as a slow one."""
    response = httpx.post(
        f"{BASE_URL}/designstate/capture",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "project": FIXTURE_PROJECT,
            "statePayloadJson": payload_json if payload_json is not None else capture_envelope_json(),
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    assert response.status_code == 202, (response.status_code, response.text)
    return response.json()


def _scrub(session: Any) -> None:
    session.run(
        "MATCH (n:ValidationRun {project:$project}) DETACH DELETE n",
        project=FIXTURE_PROJECT,
    )
    session.run(
        "MATCH (n:IntegrationConfig {project:$project}) DETACH DELETE n",
        project=FIXTURE_PROJECT,
    )


def _all_rows(session: Any) -> list[dict[str, Any]]:
    result = session.run(
        """
        MATCH (run:ValidationRun {graph:$graph, project:$project})
        OPTIONAL MATCH (run)-[:HAS_ENTITY]->(ve:ValidationEntity)
        RETURN
            run.runId AS runId,
            run.status AS status,
            run.trigger AS trigger,
            run.verdictSource AS verdictSource,
            run.capturedAt AS capturedAt,
            run.completedAt AS completedAt,
            run.attempts AS attempts,
            run.lastError AS lastError,
            run.ValidStatus AS validStatus,
            run.SendStatus AS sendStatus,
            run.shaclReportJson AS shaclReportJson,
            run.validationVersionId AS validationVersionId,
            count(DISTINCT ve) AS entityCount
        """,
        graph=dsav_watcher.VALIDATION_GRAPH,
        project=FIXTURE_PROJECT,
    )
    return [dict(record) for record in result]


def _row(session: Any, run_id: str) -> dict[str, Any] | None:
    for row in _all_rows(session):
        if row.get("runId") == run_id:
            return row
    return None


def _status_counts(session: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in _all_rows(session):
        status = row.get("status") or "(null)"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _completions_since(session: Any, cutoff: datetime) -> list[dict[str, Any]]:
    out = []
    for row in _all_rows(session):
        if row.get("status") != "completed":
            continue
        completed_at = _parse_iso(row.get("completedAt"))
        if completed_at is not None and completed_at >= cutoff:
            out.append(row)
    return out


def _wait_for_empty_rate_window(session: Any, timeout: float = 80.0) -> float:
    """Block until no completion for this project falls inside the trailing
    `RATE_LIMIT_WINDOW_SECONDS`, so the next measured scenario starts against
    an empty limiter rather than one already primed by the previous test.
    Returns the number of seconds actually waited."""
    started = time.time()
    deadline = started + timeout
    while time.time() < deadline:
        cutoff = _now_utc() - timedelta(seconds=dsav_watcher.RATE_LIMIT_WINDOW_SECONDS)
        if not _completions_since(session, cutoff):
            break
        time.sleep(2.0)
    return round(time.time() - started, 3)


def _wait_for_status(
    session: Any,
    run_id: str,
    wanted: set[str],
    deadline_seconds: float,
) -> dict[str, Any]:
    """Poll Neo4j until `run_id` reaches one of `wanted`, bounded by an
    overall wall-clock deadline so a hung sidecar fails this test in bounded
    time instead of hanging the whole suite."""
    deadline = time.time() + deadline_seconds
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        last = _row(session, run_id)
        if last is not None and last.get("status") in wanted:
            return last
        time.sleep(0.5)
    raise AssertionError(
        f"run {run_id} did not reach {sorted(wanted)} within {deadline_seconds}s; "
        f"last row = {last}"
    )


def _wait_for_any_completed(session: Any, deadline_seconds: float) -> dict[str, Any]:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        for row in _all_rows(session):
            if row.get("status") == "completed":
                return row
        time.sleep(0.5)
    raise AssertionError(
        f"no run for {FIXTURE_PROJECT} completed within {deadline_seconds}s; "
        f"status counts = {_status_counts(session)}"
    )


def _neo4j_version(session: Any) -> str:
    try:
        rows = [
            dict(record)
            for record in session.run(
                "CALL dbms.components() YIELD name, versions, edition "
                "RETURN name AS name, versions[0] AS version, edition AS edition"
            )
        ]
    except Exception:
        return "unknown"
    if not rows:
        return "unknown"
    row = rows[0]
    return f"{row.get('name')} {row.get('version')} ({row.get('edition')})"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def live_session():
    """One real Neo4j session for the whole module, with the
    `test_cg_structure_checks.py` scrub discipline: everything scoped to
    FIXTURE_PROJECT is deleted before the module runs and again afterwards,
    so a re-run never measures rows left over from the previous one.

    The rate-window drain happens *before* the scrub -- the surviving rows are
    the only observable proxy for the daemon's in-memory limiter state."""
    driver = dsav_watcher._get_driver()
    with driver.session() as session:
        _wait_for_empty_rate_window(session, timeout=80.0)
        _scrub(session)
        dsav_watcher.reset_guardrail_state()
        MEASUREMENTS["software_context"] = {
            "fixture_project": FIXTURE_PROJECT,
            "target_base_url": BASE_URL,
            "neo4j": _neo4j_version(session),
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
            "rate_limit_window_seconds": dsav_watcher.RATE_LIMIT_WINDOW_SECONDS,
            "data_service_workers": 1,
            "note": (
                "data-service runs a single uvicorn worker, so exactly one "
                "watcher daemon thread polls; the rate-limit window is that "
                "one process's memory (D-15)."
            ),
        }
        yield session
        _scrub(session)


@pytest.fixture(scope="module")
def capture_token():
    """Mint a real project-scoped connector credential (T-39-01: the measured
    path is the authenticated path) and revoke it at teardown. The plaintext
    token lives in this process only -- never in the evidence artifact, never
    in a committed file."""
    created = httpx.post(
        f"{BASE_URL}/connectors/{CONNECTOR_ID}/credentials",
        json={"label": "phase-39 live loop driver", "project": FIXTURE_PROJECT},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    assert created.status_code == 201, (created.status_code, created.text)
    body = created.json()
    yield body["token"]
    httpx.delete(
        f"{BASE_URL}/connectors/{CONNECTOR_ID}/credentials/{body['credential_id']}",
        timeout=HTTP_TIMEOUT_SECONDS,
    )


def _derive_findings() -> list[dict[str, Any]]:
    """Promote the qualitative findings that fall out of the measured numbers
    into named entries, so Plan 05's note and the DSAV-03 ADR cannot miss
    them. Every field here is copied from an observed measurement -- nothing
    is asserted that was not measured, and a scenario that did not run
    contributes no finding."""
    findings: list[dict[str, Any]] = []

    sc1 = MEASUREMENTS.get("sc1_loop_closure")
    if sc1 is not None and sc1.get("shacl_conforms") is False:
        findings.append(
            {
                "id": "F-39-01",
                "title": (
                    "An auto-run is SHACL-validated before its own ValidStatus "
                    "exists, so every auto-run currently self-violates"
                ),
                "observed": {
                    "shacl_conforms": sc1.get("shacl_conforms"),
                    "shacl_shape_ids": sc1.get("shacl_shape_ids"),
                    "shacl_counts": sc1.get("shacl_counts"),
                    "valid_status": sc1.get("valid_status"),
                    "obj_state_count": sc1.get("obj_state_count"),
                },
                "explanation": (
                    "poll_once calls the sidecar and only then writes "
                    "ValidStatus via COMPLETE_QUERY. At validation time the "
                    "run node therefore has no ValidStatus, which trips the "
                    "shapes graph's own Run shape. That finding's focusLabel "
                    "is the runId, which matches no objState, so P-02's "
                    "conservative unmapped fallback flips every ObjState "
                    "entry to false."
                ),
                "consequence": (
                    "Auto-runs report a uniformly all-false ValidStatus "
                    "regardless of the design's actual conformance. The "
                    "verdict is structurally sound (it never claims a passing "
                    "state it cannot attribute) but it is not yet "
                    "discriminating. Ordering the ValidGraph export or "
                    "scoping the shapes graph is an open design question for "
                    "the DSAV-03 ADR, not something this investigation "
                    "resolves."
                ),
            }
        )

    rpm = MEASUREMENTS.get("sc2_runs_per_minute")
    if rpm is not None:
        findings.append(
            {
                "id": "F-39-02",
                "title": "The rate limiter, not the debounce window, is what caps throughput under a sustained burst",
                "observed": {
                    "captures_issued": rpm.get("captures_issued"),
                    "measured_runs_per_minute": rpm.get("measured_runs_per_minute"),
                    "configured_rate_limit_per_minute": rpm.get(
                        "configured_rate_limit_per_minute"
                    ),
                    "superseded_total": rpm.get("superseded_total"),
                    "status_counts": rpm.get("status_counts"),
                },
                "explanation": (
                    "Captures that arrive while the limiter is saturated are "
                    "skipped before coalesce, so their rows stay 'captured' "
                    "rather than being superseded or dropped. They are "
                    "picked up once the window drains."
                ),
                "consequence": (
                    "Throughput is capped without data loss, but a saturated "
                    "project accumulates captured rows that existing readers "
                    "already see (see list_runs_tolerance). The window is "
                    "in-process and resets on restart (D-15)."
                ),
            }
        )

    return findings


@pytest.fixture(scope="module", autouse=True)
def evidence_writer():
    """Serialize the accumulator once, at module teardown. A scenario that
    never ran is listed under `missing_measurements` rather than being filled
    in with a plausible number -- a hole is recoverable, a fabricated
    datapoint silently corrupts the ADR that cites this file."""
    yield
    measurements = {k: v for k, v in MEASUREMENTS.items() if k != "software_context"}
    if not measurements:
        # Nothing was observed (e.g. this module was collected on the host
        # tier, where `neo4j` does not resolve). Writing an artifact of pure
        # nulls would be worse than writing none: Plan 05 cites this file as
        # measured fact.
        return
    payload = {
        "phase": 39,
        "measured_at": _now_utc().isoformat(),
        "source": "data-service/tests/test_dsav_live_loop.py",
        "configuration": {
            "fixture_project": FIXTURE_PROJECT,
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
            "debounce_window_seconds": {
                "sc1_loop_closure": SC1_DEBOUNCE_SECONDS,
                "sc2_burst": SC2_DEBOUNCE_SECONDS,
                "parked_for_state_machine_tests": PARKED_DEBOUNCE_SECONDS,
            },
            "rate_limit_per_minute": {
                "sc1_loop_closure": SC1_RATE_LIMIT_PER_MINUTE,
                "sc2_burst": SC2_RATE_LIMIT_PER_MINUTE,
            },
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "rate_limit_window_seconds": dsav_watcher.RATE_LIMIT_WINDOW_SECONDS,
        },
        "software_context": MEASUREMENTS.get("software_context"),
        "measurements": measurements,
        "findings": _derive_findings(),
        "missing_measurements": [
            name for name in EXPECTED_MEASUREMENTS if name not in measurements
        ],
    }
    os.makedirs(os.path.dirname(EVIDENCE_PATH) or ".", exist_ok=True)
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


# ── 1. SC1: the loop closes hands-off ────────────────────────────────────────


def test_sc1_loop_closes_hands_off(live_session, capture_token):
    """One authenticated capture, then nothing. No manual VALIDATOR trigger,
    no `/validation/publish`, no second HTTP call -- the lifespan-owned daemon
    must carry the row to `completed` on its own (SC1)."""
    _scrub(live_session)
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=SC1_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC1_RATE_LIMIT_PER_MINUTE,
    )

    envelope = capture_envelope()
    obj_state_count = len(envelope["objStates"])
    accepted = _post_capture(capture_token, json.dumps(envelope))
    run_id = accepted["runId"]
    assert accepted["status"] == "captured"

    # --- no further action of any kind from here on ---
    row = _wait_for_status(
        live_session, run_id, {"completed", "failed"}, SC1_DEADLINE_SECONDS
    )

    assert row["status"] == "completed", row
    assert row["trigger"] == "auto", row
    assert row["verdictSource"] == "shacl", row

    shacl_report = json.loads(row["shaclReportJson"])
    assert shacl_report.get("status") == "ok", shacl_report
    assert "conforms" in shacl_report, shacl_report

    assert isinstance(row["validStatus"], list)
    assert len(row["validStatus"]) == obj_state_count, row["validStatus"]

    # D-09: persist-only. T-39-04: Speckle is never touched by this plan.
    assert row["sendStatus"] is False, row
    assert row["validationVersionId"] is None, row
    assert row["entityCount"] == 0, row

    captured_at = _parse_iso(row["capturedAt"])
    completed_at = _parse_iso(row["completedAt"])
    assert captured_at is not None and completed_at is not None, row
    latency_seconds = (completed_at - captured_at).total_seconds()
    assert latency_seconds > 0, latency_seconds

    MEASUREMENTS["sc1_loop_closure"] = {
        "run_id": run_id,
        "captured_at": row["capturedAt"],
        "completed_at": row["completedAt"],
        "latency_seconds": round(latency_seconds, 3),
        "latency_source": "row.completedAt - row.capturedAt (P-13)",
        "trigger": row["trigger"],
        "verdict_source": row["verdictSource"],
        "valid_status": list(row["validStatus"]),
        "obj_state_count": obj_state_count,
        "send_status": row["sendStatus"],
        "validation_version_id": row["validationVersionId"],
        "validation_entity_count": row["entityCount"],
        "shacl_conforms": shacl_report.get("conforms"),
        "shacl_counts": shacl_report.get("counts"),
        "shacl_shape_ids": [
            finding.get("shapeId") for finding in (shacl_report.get("results") or [])
        ],
        "manual_trigger_used": False,
        "configuration": {
            "debounce_window_seconds": SC1_DEBOUNCE_SECONDS,
            "rate_limit_per_minute": SC1_RATE_LIMIT_PER_MINUTE,
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
            "deadline_seconds": SC1_DEADLINE_SECONDS,
        },
        "interpretation": (
            "Latency is bounded below by the debounce window plus the "
            "capture-to-next-tick phase offset (up to one poll interval), "
            "plus the dg-reasoner SHACL round-trip."
        ),
    }


# ── 2. SC2: the debounce collapse ratio ──────────────────────────────────────


def test_sc2_debounce_collapse_ratio(live_session, capture_token):
    """N captures back to back inside one debounce window must yield exactly
    one non-superseded run; the other N-1 rows are marked, not deleted
    (D-14), and stay queryable (SC2)."""
    rate_window_wait = _wait_for_empty_rate_window(live_session)
    _scrub(live_session)
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=SC2_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC2_RATE_LIMIT_PER_MINUTE,
    )

    burst_started = time.time()
    run_ids = [_post_capture(capture_token)["runId"] for _ in range(BURST_CAPTURES)]
    burst_span_seconds = time.time() - burst_started
    assert len(set(run_ids)) == BURST_CAPTURES
    assert burst_span_seconds < SC2_DEBOUNCE_SECONDS, (
        "the burst must fit inside one debounce window for the collapse to "
        f"mean anything; took {burst_span_seconds}s"
    )

    _wait_for_any_completed(live_session, SC2_DEADLINE_SECONDS)
    # Let any straggler tick land before counting.
    time.sleep(dsav_watcher.POLL_INTERVAL_SECONDS * 2)

    rows = _all_rows(live_session)
    counts = _status_counts(live_session)
    completed = [r for r in rows if r["status"] == "completed"]
    superseded = [r for r in rows if r["status"] == "superseded"]

    assert len(rows) == BURST_CAPTURES, counts
    assert len(completed) == 1, counts
    assert len(superseded) == BURST_CAPTURES - 1, counts
    # Marked, not deleted: every superseded row is still readable, still
    # carries its capture payload and its trigger.
    for row in superseded:
        assert row["runId"] in run_ids
        assert row["trigger"] == "auto"
    assert completed[0]["runId"] in run_ids
    assert completed[0]["verdictSource"] == "shacl"

    MEASUREMENTS["sc2_collapse"] = {
        "captures_in": BURST_CAPTURES,
        "runs_out": len(completed),
        "superseded": len(superseded),
        "collapse_ratio": f"{BURST_CAPTURES}:{len(completed)}",
        "burst_span_seconds": round(burst_span_seconds, 3),
        "kept_run_id": completed[0]["runId"],
        "status_counts": counts,
        "superseded_rows_still_queryable": True,
        "rate_window_drain_wait_seconds": rate_window_wait,
        "configuration": {
            "debounce_window_seconds": SC2_DEBOUNCE_SECONDS,
            "rate_limit_per_minute": SC2_RATE_LIMIT_PER_MINUTE,
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
        },
    }


# ── 3. SC2: runs per minute under a sustained burst ──────────────────────────


def test_sc2_runs_per_minute_under_burst(live_session, capture_token):
    """Sustain captures across one wall-clock minute in cycles that re-arm the
    debounce window and then let it lapse, so completions are actually
    attempted and the rate limiter is the thing capping throughput -- not a
    permanently-re-armed debounce that would trivially report zero."""
    rate_window_wait = _wait_for_empty_rate_window(live_session)
    _scrub(live_session)
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=SC2_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC2_RATE_LIMIT_PER_MINUTE,
    )

    window_start_dt = _now_utc()
    window_start = time.time()
    window_end = window_start + RPM_WINDOW_SECONDS
    captures_issued = 0
    cycles = 0

    while time.time() < window_end:
        cycles += 1
        for _ in range(RPM_CYCLE_CAPTURES):
            if time.time() >= window_end:
                break
            _post_capture(capture_token)
            captures_issued += 1
            time.sleep(RPM_CYCLE_CAPTURE_INTERVAL_SECONDS)
        idle_until = min(time.time() + RPM_CYCLE_IDLE_SECONDS, window_end)
        while time.time() < idle_until:
            time.sleep(0.5)

    window_end_dt = window_start_dt + timedelta(seconds=RPM_WINDOW_SECONDS)
    # Let in-flight completions land before counting; rows completing after
    # window_end_dt are excluded by timestamp, not by luck.
    time.sleep(RPM_SETTLE_SECONDS)

    rows = _all_rows(live_session)
    in_window = []
    for row in rows:
        if row["status"] != "completed" or row["trigger"] != "auto":
            continue
        completed_at = _parse_iso(row["completedAt"])
        if completed_at is not None and window_start_dt <= completed_at < window_end_dt:
            in_window.append(row)

    measured_runs_per_minute = len(in_window)
    superseded = [r for r in rows if r["status"] == "superseded"]

    # The guardrail is what caps throughput, and it must actually bind.
    assert measured_runs_per_minute <= SC2_RATE_LIMIT_PER_MINUTE, (
        measured_runs_per_minute,
        _status_counts(live_session),
    )
    assert captures_issued > SC2_RATE_LIMIT_PER_MINUTE, captures_issued

    MEASUREMENTS["sc2_runs_per_minute"] = {
        "measured_runs_per_minute": measured_runs_per_minute,
        "configured_rate_limit_per_minute": SC2_RATE_LIMIT_PER_MINUTE,
        "window_seconds": RPM_WINDOW_SECONDS,
        "window_start": window_start_dt.isoformat(),
        "window_end": window_end_dt.isoformat(),
        "captures_issued": captures_issued,
        "cycles": cycles,
        "superseded_total": len(superseded),
        "status_counts": _status_counts(live_session),
        "completed_at_in_window": [r["completedAt"] for r in in_window],
        "rate_window_drain_wait_seconds": rate_window_wait,
        "capture_schedule": (
            f"{RPM_CYCLE_CAPTURES} captures at "
            f"{RPM_CYCLE_CAPTURE_INTERVAL_SECONDS}s intervals, then "
            f"{RPM_CYCLE_IDLE_SECONDS}s idle, repeated for "
            f"{RPM_WINDOW_SECONDS}s"
        ),
        "counting_rule": (
            "rows with status='completed' and trigger='auto' whose row "
            "completedAt falls in [window_start, window_end) -- read off the "
            "row, not off a stopwatch (P-13)"
        ),
        "configuration": {
            "debounce_window_seconds": SC2_DEBOUNCE_SECONDS,
            "rate_limit_per_minute": SC2_RATE_LIMIT_PER_MINUTE,
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "poll_interval_seconds": dsav_watcher.POLL_INTERVAL_SECONDS,
            "settle_seconds": RPM_SETTLE_SECONDS,
        },
    }


# ── 4. D-08: the failure ladder, live ────────────────────────────────────────


def test_shacl_unavailable_leaves_row_captured_then_failed(live_session):
    """D-08's departure from the Phase 823 degrade-never-raise precedent,
    proven against live Neo4j: an unavailable sidecar never silently
    completes an auto-run. The row stays `captured` with `attempts`
    incrementing, and only the `maxAttempts`-th failure flips it to `failed`.

    The live daemon is parked on a 3600s debounce for the duration, and this
    test drives `poll_once` itself with a `now` past that window -- so the
    ladder is stepped deterministically instead of racing the real one."""
    _scrub(live_session)
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=PARKED_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC1_RATE_LIMIT_PER_MINUTE,
    )
    dsav_watcher.reset_guardrail_state()

    run_id = "p39-ladder-run"
    dsav_watcher.capture_state(
        FIXTURE_PROJECT,
        run_id,
        capture_envelope_json(),
        _now_utc().isoformat(),
        session=live_session,
    )

    def unavailable_shacl(_project: str, _run_id: str) -> dict[str, Any]:
        return {"status": "unavailable"}

    future = time.time() + PARKED_DEBOUNCE_SECONDS * 2
    observed: list[dict[str, Any]] = []
    for tick in range(1, MAX_ATTEMPTS + 1):
        summary = dsav_watcher.poll_once(
            session=live_session, now=future, shacl_fn=unavailable_shacl
        )
        row = _row(live_session, run_id)
        assert row is not None
        observed.append(
            {
                "tick": tick,
                "attempts": row["attempts"],
                "status": row["status"],
                "lastError": row["lastError"],
                "runs_failed_this_tick": summary["runs_failed"],
            }
        )

    assert [o["attempts"] for o in observed] == [1, 2, 3], observed
    assert [o["status"] for o in observed] == ["captured", "captured", "failed"], observed
    assert observed[-1]["lastError"] == "unavailable", observed
    final = _row(live_session, run_id)
    assert final["completedAt"] is None, final
    assert final["verdictSource"] is None, final

    MEASUREMENTS["d08_failure_ladder"] = {
        "max_attempts": MAX_ATTEMPTS,
        "observed_sequence": observed,
        "terminal_status": final["status"],
        "last_error": final["lastError"],
        "completed_at": final["completedAt"],
        "verdict_source": final["verdictSource"],
        "shacl_status_injected": "unavailable",
        "configuration": {
            "debounce_window_seconds": PARKED_DEBOUNCE_SECONDS,
            "rate_limit_per_minute": SC1_RATE_LIMIT_PER_MINUTE,
            "max_attempts": MAX_ATTEMPTS,
            "publish_enabled": PUBLISH_ENABLED,
            "driver": (
                "poll_once driven directly against the live session with an "
                "injected unavailable shacl_fn; the daemon is parked on a "
                "3600s debounce so it cannot race the ladder"
            ),
        },
    }


# ── 5. The assumption-delta invariant: list_validation_runs tolerates them ───


def test_list_runs_tolerates_auto_rows(live_session):
    """`list_validation_runs` has no status filter, so every auto row --
    captured, superseded, failed and shacl-verdicted completed alike -- is
    visible to existing readers. Assert the *shape*, not their absence: this
    is D-12's accepted run-list pollution, widened by Plan 01's no-status-
    filter finding, and the ADR records it as accepted debt rather than
    pretending the rows are hidden."""
    _scrub(live_session)
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=PARKED_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC1_RATE_LIMIT_PER_MINUTE,
    )

    base = _now_utc()
    # Three captures -> coalesce keeps the newest, supersedes two.
    for index in range(3):
        dsav_watcher.capture_state(
            FIXTURE_PROJECT,
            f"p39-list-{index}",
            capture_envelope_json(),
            (base + timedelta(seconds=index)).isoformat(),
            session=live_session,
        )
    coalesced = dsav_watcher._run_read(
        live_session,
        dsav_watcher.COALESCE_QUERY,
        {"graph": dsav_watcher.VALIDATION_GRAPH, "project": FIXTURE_PROJECT},
    )[0]
    kept_run_id = coalesced["keptRunId"]
    dsav_watcher._run_write(
        live_session,
        dsav_watcher.COMPLETE_QUERY,
        {
            "graph": dsav_watcher.VALIDATION_GRAPH,
            "project": FIXTURE_PROJECT,
            "runId": kept_run_id,
            "shaclReportJson": json.dumps({"status": "ok", "conforms": True, "results": []}),
            "validStatus": [True, True],
            "completedAt": _now_utc().isoformat(),
        },
    )
    # One left captured, one driven to failed.
    dsav_watcher.capture_state(
        FIXTURE_PROJECT,
        "p39-list-captured",
        capture_envelope_json(),
        _now_utc().isoformat(),
        session=live_session,
    )
    dsav_watcher.capture_state(
        FIXTURE_PROJECT,
        "p39-list-failed",
        capture_envelope_json(),
        _now_utc().isoformat(),
        session=live_session,
    )
    for _ in range(MAX_ATTEMPTS):
        dsav_watcher._run_read(
            live_session,
            dsav_watcher.FAIL_QUERY,
            {
                "graph": dsav_watcher.VALIDATION_GRAPH,
                "project": FIXTURE_PROJECT,
                "runId": "p39-list-failed",
                "maxAttempts": MAX_ATTEMPTS,
                "reason": "unavailable",
            },
        )

    counts = _status_counts(live_session)
    assert counts.get("captured") == 1, counts
    assert counts.get("superseded") == 2, counts
    assert counts.get("failed") == 1, counts
    assert counts.get("completed") == 1, counts

    response = httpx.get(
        f"{BASE_URL}/validation/runs/{FIXTURE_PROJECT}", timeout=HTTP_TIMEOUT_SECONDS
    )
    assert response.status_code == 200, response.text
    body = response.json()
    listed = body["runs"]
    assert body["project"] == FIXTURE_PROJECT
    assert len(listed) == 5, listed
    for run in listed:
        assert run["runId"], run

    by_id = {run["runId"]: run for run in listed}
    non_completed_ids = [
        "p39-list-captured",
        "p39-list-failed",
    ] + [f"p39-list-{i}" for i in range(3) if f"p39-list-{i}" != kept_run_id]
    for run_id in non_completed_ids:
        run = by_id[run_id]
        assert run["speckleProjectId"] is None, run
        assert run["validationVersionId"] is None, run
        assert run["modelViewerUrl"] is None, run

    MEASUREMENTS["list_runs_tolerance"] = {
        "endpoint": f"GET /validation/runs/{FIXTURE_PROJECT}",
        "http_status": response.status_code,
        "runs_returned": len(listed),
        "status_counts_present": counts,
        "every_run_has_run_id": True,
        "non_completed_speckle_identifiers": "null",
        "consequence": (
            "list_validation_runs has no status filter, so captured, "
            "superseded and failed auto rows are returned to every existing "
            "reader alongside completed ones (D-12 accepted debt)."
        ),
    }


# ── 6. The [ASSUMED] Cypher shapes, executed live ────────────────────────────


def test_cypher_shapes_execute_on_live_neo4j(live_session):
    """39-RESEARCH.md flagged all eight watcher Cypher constants as
    `[ASSUMED -- proposed, not existing code]`: synthesized in research and
    never executed against a real database. Execute each one here with
    representative bound parameters and assert its row shape.

    The load-bearing case is COALESCE_QUERY with exactly one captured row --
    the defect P-09 corrects in the researcher's `UNWIND`-based proposal,
    where an empty stale tail would yield zero rows and lose `keptRunId`
    entirely."""
    _scrub(live_session)
    graph = dsav_watcher.VALIDATION_GRAPH
    executed: dict[str, Any] = {}

    # CONFIG_UPSERT_QUERY + CONFIG_READ_QUERY
    _enable_auto_validation(
        live_session,
        debounce_window_seconds=PARKED_DEBOUNCE_SECONDS,
        rate_limit_per_minute=SC1_RATE_LIMIT_PER_MINUTE,
    )
    config = dsav_watcher.get_auto_validation_config(FIXTURE_PROJECT, session=live_session)
    assert config is not None
    assert config.enabled is True
    assert config.debounce_window_seconds == PARKED_DEBOUNCE_SECONDS
    assert config.max_attempts == MAX_ATTEMPTS
    executed["CONFIG_UPSERT_QUERY"] = "ok"
    executed["CONFIG_READ_QUERY"] = {
        "enabled": config.enabled,
        "debounceWindowSeconds": config.debounce_window_seconds,
        "rateLimitPerMinute": config.rate_limit_per_minute,
        "maxAttempts": config.max_attempts,
    }

    # ENABLED_PROJECTS_QUERY
    enabled_projects = dsav_watcher.list_enabled_projects(session=live_session)
    assert FIXTURE_PROJECT in enabled_projects, enabled_projects
    executed["ENABLED_PROJECTS_QUERY"] = {"contains_fixture_project": True}

    # CAPTURE_QUERY
    run_id = "p39-cypher-run"
    captured_at = _now_utc().isoformat()
    dsav_watcher.capture_state(
        FIXTURE_PROJECT, run_id, capture_envelope_json(), captured_at, session=live_session
    )
    row = _row(live_session, run_id)
    assert row["status"] == "captured"
    assert row["trigger"] == "auto"
    assert row["attempts"] == 0
    assert row["sendStatus"] is False
    executed["CAPTURE_QUERY"] = {
        "status": row["status"],
        "trigger": row["trigger"],
        "attempts": row["attempts"],
        "sendStatus": row["sendStatus"],
    }

    # NEWEST_CAPTURED_QUERY
    newest = dsav_watcher._run_read(
        live_session,
        dsav_watcher.NEWEST_CAPTURED_QUERY,
        {"graph": graph, "project": FIXTURE_PROJECT},
    )
    assert len(newest) == 1, newest
    assert newest[0]["runId"] == run_id
    assert newest[0]["capturedCount"] == 1
    assert newest[0]["attempts"] == 0
    assert newest[0]["capturedAt"] == captured_at
    executed["NEWEST_CAPTURED_QUERY"] = dict(newest[0])

    # COALESCE_QUERY with exactly one captured row -- the P-09 defect check.
    coalesced = dsav_watcher._run_read(
        live_session,
        dsav_watcher.COALESCE_QUERY,
        {"graph": graph, "project": FIXTURE_PROJECT},
    )
    assert len(coalesced) == 1, coalesced
    assert coalesced[0]["keptRunId"] == run_id, coalesced
    assert coalesced[0]["supersededCount"] == 0, coalesced
    assert json.loads(coalesced[0]["statePayloadJson"])["objStates"], coalesced
    executed["COALESCE_QUERY_single_captured_row"] = {
        "keptRunId": coalesced[0]["keptRunId"],
        "supersededCount": coalesced[0]["supersededCount"],
        "statePayloadJson_returned": True,
    }

    # COALESCE_QUERY with a stale tail.
    for index in range(2):
        dsav_watcher.capture_state(
            FIXTURE_PROJECT,
            f"p39-cypher-tail-{index}",
            capture_envelope_json(),
            (_now_utc() + timedelta(seconds=index + 1)).isoformat(),
            session=live_session,
        )
    coalesced_many = dsav_watcher._run_read(
        live_session,
        dsav_watcher.COALESCE_QUERY,
        {"graph": graph, "project": FIXTURE_PROJECT},
    )
    assert len(coalesced_many) == 1, coalesced_many
    assert coalesced_many[0]["supersededCount"] == 2, coalesced_many
    kept_run_id = coalesced_many[0]["keptRunId"]
    executed["COALESCE_QUERY_with_stale_tail"] = {
        "keptRunId": kept_run_id,
        "supersededCount": coalesced_many[0]["supersededCount"],
    }

    # COMPLETE_QUERY
    completed_at = _now_utc().isoformat()
    dsav_watcher._run_write(
        live_session,
        dsav_watcher.COMPLETE_QUERY,
        {
            "graph": graph,
            "project": FIXTURE_PROJECT,
            "runId": kept_run_id,
            "shaclReportJson": json.dumps({"status": "ok", "conforms": True, "results": []}),
            "validStatus": [True, False],
            "completedAt": completed_at,
        },
    )
    completed_row = _row(live_session, kept_run_id)
    assert completed_row["status"] == "completed"
    assert completed_row["verdictSource"] == "shacl"
    assert list(completed_row["validStatus"]) == [True, False]
    assert completed_row["completedAt"] == completed_at
    executed["COMPLETE_QUERY"] = {
        "status": completed_row["status"],
        "verdictSource": completed_row["verdictSource"],
        "validStatus": list(completed_row["validStatus"]),
    }

    # FAIL_QUERY
    fail_rows = dsav_watcher._run_read(
        live_session,
        dsav_watcher.FAIL_QUERY,
        {
            "graph": graph,
            "project": FIXTURE_PROJECT,
            "runId": run_id,
            "maxAttempts": MAX_ATTEMPTS,
            "reason": "timeout",
        },
    )
    assert len(fail_rows) == 1, fail_rows
    assert fail_rows[0]["attempts"] == 1
    assert fail_rows[0]["status"] == "captured"
    executed["FAIL_QUERY"] = dict(fail_rows[0])

    MEASUREMENTS["cypher_shapes"] = {
        "neo4j": MEASUREMENTS.get("software_context", {}).get("neo4j"),
        "constants_executed": sorted(
            [
                "ENABLED_PROJECTS_QUERY",
                "CONFIG_READ_QUERY",
                "CONFIG_UPSERT_QUERY",
                "CAPTURE_QUERY",
                "NEWEST_CAPTURED_QUERY",
                "COALESCE_QUERY",
                "COMPLETE_QUERY",
                "FAIL_QUERY",
            ]
        ),
        "results": executed,
        "assumed_flag": (
            "39-RESEARCH.md A2 discharged: all eight constants executed "
            "against live Neo4j without a Cypher error and produced the "
            "expected row shapes."
        ),
    }
