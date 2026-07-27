"""DesignState Auto-Validation watcher (Phase 39: DSAV-02).

Standalone, importable, unit-testable state machine: capture -> debounce ->
coalesce -> validate (SHACL) -> complete/fail, plus in-memory guardrails
(debounce window read off the row, rate limiting, bounded retry).

Mirrors `dg_context.py`'s module shape (own lazy `_get_driver()`, own
`VALIDATION_GRAPH` constant -- duplicated, not imported, to avoid a circular
import: `app.py` imports this module, this module never imports `app.py`).

D-03: the poll body (`poll_once`) is a pure function. It takes an injected
`session`, an injected `now` clock, and injected `shacl_fn`/`publish_fn`
callables, so the entire state machine is testable on the host tier with
zero live Neo4j, zero thread, and zero `time.sleep`. `start_watcher()` /
`stop_watcher()` wrap `poll_once()` in a `threading.Thread(daemon=True)` +
`threading.Event` loop -- the thread is never started at import time (an
always-on background thread inside every unrelated `from app import app`
test module would be a real bug, not a convenience).

D-15: the in-memory guardrail state (per-project completion timestamps used
for rate limiting) lives in this module's process memory only. A data-service
restart resets this window -- an accepted limitation for this investigation
spike, recorded as an explicit follow-up line in the DSAV-03 ADR rather than
solved here.

D-08: this module's fail path deliberately departs from the Phase 823
`_call_shacl_validate` degrade-never-raise precedent. The manual-publish
caller (`publish_validation` in `app.py`) treats a SHACL timeout/unavailable
status as non-fatal and completes the run anyway. This watcher does not: an
auto-run that silently completes with no verdict is a worse failure mode
than a manual one, because nobody clicked anything to watch it. A captured
row that cannot get a verdict stays `status:'captured'` (retried next tick)
until `maxAttempts` is reached, then flips to `status:'failed'`.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from neo4j import GraphDatabase

_logger = logging.getLogger(__name__)

# ── Module constants ────────────────────────────────────────────────────────

AUTO_VALIDATION_PROVIDER = "AutoValidation"
VALIDATION_GRAPH = "ValidGraph"

DEFAULT_DEBOUNCE_WINDOW_SECONDS = 5.0
DEFAULT_RATE_LIMIT_PER_MINUTE = 6
DEFAULT_MAX_ATTEMPTS = 3

POLL_INTERVAL_SECONDS = float(os.getenv("DSAV_POLL_INTERVAL_SECONDS", "2.0"))
RATE_LIMIT_WINDOW_SECONDS = 60.0

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


# ── Lazy driver (never constructed at import time) ──────────────────────────

_driver: Any = None


def _get_driver() -> Any:
    """Lazily open this module's own Neo4j driver.

    Kept separate from `app.py`'s module-level `driver` (and from
    `dg_context.py`'s own copy of the identical idiom) to avoid a circular
    import -- functionally equivalent, same env vars, same lazy-connect
    behavior. Never called at import time, so `import dsav_watcher` succeeds
    on a host with no Neo4j reachable.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


# ── Session helpers (injectable-session idiom, dg_context.py precedent) ─────


def _run_read(session: Any, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Run a query that returns rows (plain reads and write-then-RETURN
    queries alike). `if session is not None: ... else: with _get_driver()...`
    -- the exact branch shape `dg_context.fetch_existing_design_states` uses,
    so a `FixtureSession` in tests and a lazily-opened live session in
    production are interchangeable at every call site."""
    if session is not None:
        result = session.run(query, **params)
        return [dict(record) for record in result]
    with _get_driver().session() as live_session:
        result = live_session.run(query, **params)
        return [dict(record) for record in result]


def _run_write(session: Any, query: str, params: dict[str, Any]) -> None:
    """Run a write-only query with no RETURN clause. Mirrors `write_query`'s
    per-call session discipline (`app.py:317-319`) -- every call opens and
    closes its own session; nothing is ever held across poll ticks or
    threads (Neo4j session thread-safety contract)."""
    if session is not None:
        session.run(query, **params)
        return
    with _get_driver().session() as live_session:
        live_session.run(query, **params).consume()


# ── Cypher constants (all parameterized, no interpolation) ──────────────────

ENABLED_PROJECTS_QUERY = """
MATCH (cfg:IntegrationConfig {graph:$graph, provider:'AutoValidation'})
WHERE cfg.enabled = true
RETURN cfg.project AS project
"""

CONFIG_READ_QUERY = """
MATCH (cfg:IntegrationConfig {graph:$graph, provider:'AutoValidation', project:$project})
RETURN
    cfg.enabled AS enabled,
    cfg.publishEnabled AS publishEnabled,
    cfg.debounceWindowSeconds AS debounceWindowSeconds,
    cfg.rateLimitPerMinute AS rateLimitPerMinute,
    cfg.maxAttempts AS maxAttempts
"""

CONFIG_UPSERT_QUERY = """
MERGE (cfg:IntegrationConfig {graph:$graph, provider:'AutoValidation', project:$project})
SET
    cfg.enabled = $enabled,
    cfg.publishEnabled = $publishEnabled,
    cfg.debounceWindowSeconds = $debounceWindowSeconds,
    cfg.rateLimitPerMinute = $rateLimitPerMinute,
    cfg.maxAttempts = $maxAttempts,
    cfg.updatedAt = $updatedAt
"""

CAPTURE_QUERY = """
MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET
    run.statePayloadJson = $statePayloadJson,
    run.status = 'captured',
    run.trigger = 'auto',
    run.capturedAt = $capturedAt,
    run.createdAt = $capturedAt,
    run.SendStatus = false,
    run.attempts = 0
"""

NEWEST_CAPTURED_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, status:'captured'})
WITH run ORDER BY run.capturedAt DESC
WITH collect(run) AS runs
RETURN
    CASE WHEN size(runs) > 0 THEN runs[0].runId ELSE null END AS runId,
    CASE WHEN size(runs) > 0 THEN runs[0].capturedAt ELSE null END AS capturedAt,
    CASE WHEN size(runs) > 0 THEN coalesce(runs[0].attempts, 0) ELSE null END AS attempts,
    size(runs) AS capturedCount
"""

# P-09 correction: FOREACH over the stale tail, not UNWIND -- UNWIND over an
# empty list (exactly one captured row) yields zero rows and the whole query
# returns nothing, losing keptRunId. FOREACH over an empty tail is a no-op
# and the RETURN row is always produced. Scoped strictly to status:'captured'
# (39-RESEARCH.md Pitfall 5) so a row a prior tick already completed can
# never be superseded. Additionally returns the kept row's statePayloadJson
# -- needed by derive_valid_status() and not persisted anywhere else once
# coalesce has run; this is an additive column beyond the plan's minimum
# spec, not a substitute for it.
COALESCE_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, status:'captured'})
WITH run ORDER BY run.capturedAt DESC
WITH collect(run) AS runs
WITH runs[0] AS kept, runs[1..] AS stale
FOREACH (s IN stale | SET s.status = 'superseded')
RETURN kept.runId AS keptRunId, kept.statePayloadJson AS statePayloadJson, size(stale) AS supersededCount
"""

COMPLETE_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET
    run.status = 'completed',
    run.trigger = 'auto',
    run.verdictSource = 'shacl',
    run.shaclReportJson = $shaclReportJson,
    run.ValidStatus = $validStatus,
    run.completedAt = $completedAt
"""

# P-09 correction: bind the incremented attempt count in a WITH before the
# SET -- reading run.attempts twice inside one SET (once to increment, once
# inside the CASE) is order-dependent.
FAIL_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
WITH run, coalesce(run.attempts, 0) + 1 AS nextAttempts
SET
    run.attempts = nextAttempts,
    run.status = CASE WHEN nextAttempts >= $maxAttempts THEN 'failed' ELSE 'captured' END,
    run.lastError = $reason,
    run.trigger = 'auto'
RETURN nextAttempts AS attempts, run.status AS status
"""


# ── Config value object ──────────────────────────────────────────────────────


@dataclass
class AutoValidationConfig:
    enabled: bool = False
    publish_enabled: bool = False
    debounce_window_seconds: float = DEFAULT_DEBOUNCE_WINDOW_SECONDS
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE
    max_attempts: int = DEFAULT_MAX_ATTEMPTS

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AutoValidationConfig":
        """Coerce a partially-populated (or entirely null-valued) config row
        into a usable config, falling back to the module defaults field by
        field -- never raises on a partial row."""
        row = row or {}
        enabled = row.get("enabled")
        publish_enabled = row.get("publishEnabled")
        debounce = row.get("debounceWindowSeconds")
        rate_limit = row.get("rateLimitPerMinute")
        max_attempts = row.get("maxAttempts")
        return cls(
            enabled=bool(enabled) if enabled is not None else False,
            publish_enabled=bool(publish_enabled) if publish_enabled is not None else False,
            debounce_window_seconds=(
                float(debounce) if debounce is not None else DEFAULT_DEBOUNCE_WINDOW_SECONDS
            ),
            rate_limit_per_minute=(
                int(rate_limit) if rate_limit is not None else DEFAULT_RATE_LIMIT_PER_MINUTE
            ),
            max_attempts=int(max_attempts) if max_attempts is not None else DEFAULT_MAX_ATTEMPTS,
        )


# ── Public config/capture API ────────────────────────────────────────────────


def get_auto_validation_config(project: str, session: Any = None) -> AutoValidationConfig | None:
    """`None` when no `IntegrationConfig{provider:'AutoValidation'}` row
    exists for this project -- absent row means disabled (D-13); this
    function never implicitly creates one."""
    rows = _run_read(session, CONFIG_READ_QUERY, {"graph": VALIDATION_GRAPH, "project": project})
    if not rows:
        return None
    return AutoValidationConfig.from_row(rows[0])


def upsert_auto_validation_config(
    project: str, config: AutoValidationConfig, session: Any = None
) -> None:
    _run_write(
        session,
        CONFIG_UPSERT_QUERY,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "enabled": config.enabled,
            "publishEnabled": config.publish_enabled,
            "debounceWindowSeconds": config.debounce_window_seconds,
            "rateLimitPerMinute": config.rate_limit_per_minute,
            "maxAttempts": config.max_attempts,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    )


def list_enabled_projects(session: Any = None) -> list[str]:
    rows = _run_read(session, ENABLED_PROJECTS_QUERY, {"graph": VALIDATION_GRAPH})
    return [row["project"] for row in rows if row.get("project")]


def capture_state(
    project: str,
    run_id: str,
    state_payload_json: str,
    captured_at: str,
    session: Any = None,
) -> None:
    """The single writer of CAPTURE_QUERY -- Plan 02's `POST
    /designstate/capture` route calls this rather than embedding Cypher in
    `app.py`."""
    _run_write(
        session,
        CAPTURE_QUERY,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            "statePayloadJson": state_payload_json,
            "capturedAt": captured_at,
        },
    )


# ── Pure verdict derivation (P-02) ────────────────────────────────────────────


def derive_valid_status(
    state_payload_json: str | None, shacl_body: dict[str, Any] | None
) -> tuple[list[bool], int]:
    """Derive a `ValidStatus` Boolean list (index-matched to the envelope's
    `objStates`) from a `_call_shacl_validate` success body, per P-02.

    `dg-reasoner`'s SHACL envelope is sanitized -- no raw focus-node IRI ever
    appears in a finding (`reasoning._enrich_shacl_result`). The only
    available join key is `focusLabel`, matched against
    `label or objectRef or stateId` per objState -- the exact key
    `valid_graph_export._state_label()` stamps for `objStates` on the export
    side.

    - `conforms` truthy -> all-true, length == len(objStates).
    - `conforms` falsy -> start all-true; each `severity == "violation"`
      finding whose `focusLabel` hits the index map flips that entry false;
      a violation that hits nothing increments the returned `unmapped` count.
    - `unmapped > 0` -> every entry is set false (an unattributable
      violation must never be reported as a passing state -- the
      conservative reading of D-07's "where resolvable").
    - Empty or unparseable `state_payload_json`, or an envelope with no
      `objStates`, returns `([], 0)`. Never raises.
    """
    if not state_payload_json:
        return [], 0
    try:
        envelope = json.loads(state_payload_json)
    except Exception:
        return [], 0
    if not isinstance(envelope, dict):
        return [], 0

    obj_states = envelope.get("objStates")
    if not isinstance(obj_states, list) or not obj_states:
        return [], 0

    index_by_key: dict[str, int] = {}
    for i, state in enumerate(obj_states):
        if not isinstance(state, dict):
            continue
        key = state.get("label") or state.get("objectRef") or state.get("stateId")
        if key:
            index_by_key[str(key)] = i

    valid_status = [True] * len(obj_states)

    shacl_body = shacl_body or {}
    if shacl_body.get("conforms"):
        return valid_status, 0

    unmapped = 0
    results = shacl_body.get("results")
    if not isinstance(results, list):
        results = []

    for finding in results:
        if not isinstance(finding, dict):
            continue
        if finding.get("severity") != "violation":
            continue
        focus_label = finding.get("focusLabel")
        idx = index_by_key.get(str(focus_label)) if focus_label else None
        if idx is not None:
            valid_status[idx] = False
        else:
            unmapped += 1

    if unmapped > 0:
        valid_status = [False] * len(obj_states)

    return valid_status, unmapped


# ── In-memory guardrail state (D-15) ─────────────────────────────────────────
#
# Per-project completion timestamps, keyed by project, pruned to the
# trailing RATE_LIMIT_WINDOW_SECONDS on each read. Nothing is written to
# Neo4j for guardrail bookkeeping -- no write amplification against the
# database being polled. A data-service process restart resets this window;
# accepted for this spike, recorded as an explicit ADR follow-up line (D-15).

_completion_timestamps: dict[str, list[float]] = {}


def reset_guardrail_state() -> None:
    """Clear the in-memory guardrail window so tests start clean."""
    _completion_timestamps.clear()


def _prune_window(project: str, now: float) -> list[float]:
    window = _completion_timestamps.get(project, [])
    pruned = [t for t in window if now - t < RATE_LIMIT_WINDOW_SECONDS]
    _completion_timestamps[project] = pruned
    return pruned


def _record_completion(project: str, now: float) -> None:
    window = _completion_timestamps.setdefault(project, [])
    window.append(now)


def _is_rate_limited(project: str, now: float, rate_limit_per_minute: int) -> bool:
    return len(_prune_window(project, now)) >= rate_limit_per_minute


def _parse_captured_at(value: Any) -> float:
    """Parse an ISO-8601 `capturedAt` string into epoch seconds, tolerating a
    trailing `Z` and treating a naive timestamp as UTC. Never raises --
    returns 0.0 (maximally "old") on anything unparseable."""
    if not value or not isinstance(value, str):
        return 0.0
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


# ── The pure poll body (D-03) ────────────────────────────────────────────────


def poll_once(
    session: Any = None,
    now: float | None = None,
    shacl_fn: Any = None,
    publish_fn: Any = None,
) -> dict[str, Any]:
    """One full tick of the watcher: for every project with an enabled
    `AutoValidation` config, debounce -> coalesce -> SHACL verdict ->
    complete/fail -> optional publish. Fully driven through the injected
    `session` and `now` clock; `shacl_fn(project, run_id) -> dict | None` and
    `publish_fn(project, run_id)` are injected so this function never opens
    an HTTP connection itself and is entirely host-testable.

    Returns a summary dict: `projects_seen`, `runs_completed`,
    `runs_failed`, `superseded`, `unmapped_violations`, `publish_attempted`,
    `publish_errors`, and `skipped` (project -> reason, one of
    `debounce_wait` / `rate_limited` / `no_captured_rows`).
    """
    if now is None:
        now = time.time()

    summary: dict[str, Any] = {
        "projects_seen": 0,
        "runs_completed": 0,
        "runs_failed": 0,
        "superseded": 0,
        "unmapped_violations": 0,
        "publish_attempted": 0,
        "publish_errors": 0,
        "skipped": {},
    }

    projects = list_enabled_projects(session=session)
    summary["projects_seen"] = len(projects)

    for project in projects:
        config = get_auto_validation_config(project, session=session)
        if config is None or not config.enabled:
            # Defensive only -- ENABLED_PROJECTS_QUERY already filters on
            # enabled=true, so this branch should be unreachable against a
            # real Neo4j instance; kept for a synthetic/racy test double.
            summary["skipped"][project] = "no_captured_rows"
            continue

        newest_rows = _run_read(
            session, NEWEST_CAPTURED_QUERY, {"graph": VALIDATION_GRAPH, "project": project}
        )
        newest = newest_rows[0] if newest_rows else {}
        newest_run_id = newest.get("runId")
        if not newest_run_id:
            summary["skipped"][project] = "no_captured_rows"
            continue

        captured_epoch = _parse_captured_at(newest.get("capturedAt"))
        age = now - captured_epoch
        if age < config.debounce_window_seconds:
            summary["skipped"][project] = "debounce_wait"
            continue

        if _is_rate_limited(project, now, config.rate_limit_per_minute):
            summary["skipped"][project] = "rate_limited"
            continue

        coalesce_rows = _run_read(
            session, COALESCE_QUERY, {"graph": VALIDATION_GRAPH, "project": project}
        )
        coalesced = coalesce_rows[0] if coalesce_rows else {}
        kept_run_id = coalesced.get("keptRunId")
        if not kept_run_id:
            summary["skipped"][project] = "no_captured_rows"
            continue

        summary["superseded"] += int(coalesced.get("supersededCount") or 0)
        state_payload_json = coalesced.get("statePayloadJson")

        shacl_body: dict[str, Any] | None = None
        if callable(shacl_fn):
            try:
                shacl_body = shacl_fn(project, kept_run_id)
            except Exception as exc:  # shacl_fn itself must never crash the tick
                shacl_body = {"status": "unavailable", "reason": str(exc)}

        status = shacl_body.get("status") if isinstance(shacl_body, dict) else None

        if status == "ok":
            valid_status, unmapped = derive_valid_status(state_payload_json, shacl_body)
            summary["unmapped_violations"] += unmapped
            completed_at = datetime.now(timezone.utc).isoformat()
            _run_write(
                session,
                COMPLETE_QUERY,
                {
                    "graph": VALIDATION_GRAPH,
                    "project": project,
                    "runId": kept_run_id,
                    "shaclReportJson": json.dumps(shacl_body),
                    "validStatus": valid_status,
                    "completedAt": completed_at,
                },
            )
            summary["runs_completed"] += 1
            _record_completion(project, now)

            if config.publish_enabled and callable(publish_fn):
                summary["publish_attempted"] += 1
                try:
                    publish_fn(project, kept_run_id)
                except Exception:
                    # A publish failure never reverts or fails the
                    # already-persisted verdict (behavior contract).
                    summary["publish_errors"] += 1
        else:
            # D-08 departure: unlike the manual-publish caller, a
            # timeout/unavailable/missing verdict never silently completes
            # the run. It stays 'captured' (retried next tick) until
            # maxAttempts is reached, then flips to 'failed'.
            reason = status or "no_response"
            fail_rows = _run_read(
                session,
                FAIL_QUERY,
                {
                    "graph": VALIDATION_GRAPH,
                    "project": project,
                    "runId": kept_run_id,
                    "maxAttempts": config.max_attempts,
                    "reason": reason,
                },
            )
            if fail_rows and fail_rows[0].get("status") == "failed":
                summary["runs_failed"] += 1

    return summary


# ── Thread lifecycle ─────────────────────────────────────────────────────────
#
# Never started at import time (39-RESEARCH.md Anti-Patterns): every
# existing test file does `from app import app`, and a module-import-time
# thread would spin a live Neo4j poller inside unrelated test runs.

_stop_event = threading.Event()
_watcher_thread: threading.Thread | None = None
_watcher_lock = threading.Lock()


def _poll_loop(shacl_fn: Any, publish_fn: Any) -> None:
    while not _stop_event.is_set():
        try:
            poll_once(shacl_fn=shacl_fn, publish_fn=publish_fn)
        except Exception:
            # One bad tick must never kill the daemon.
            _logger.exception("dsav_watcher: poll_once tick raised; continuing")
        _stop_event.wait(POLL_INTERVAL_SECONDS)


def start_watcher(shacl_fn: Any = None, publish_fn: Any = None) -> None:
    """Idempotent -- a second call while the thread is already alive is a
    no-op. `daemon=True` is a container-kill safety net; the `Event` plus
    `join(timeout)` in `stop_watcher()` is what makes the thread
    deterministically stoppable."""
    global _watcher_thread
    with _watcher_lock:
        if _watcher_thread is not None and _watcher_thread.is_alive():
            return
        _stop_event.clear()
        _watcher_thread = threading.Thread(
            target=_poll_loop, args=(shacl_fn, publish_fn), daemon=True
        )
        _watcher_thread.start()


def stop_watcher(timeout: float = 5.0) -> None:
    global _watcher_thread
    _stop_event.set()
    with _watcher_lock:
        thread, _watcher_thread = _watcher_thread, None
    if thread is not None:
        thread.join(timeout=timeout)
