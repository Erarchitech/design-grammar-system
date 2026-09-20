# Phase 39: DesignState Auto-Validation Investigation - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 8 (6 code, 2 writing deliverables)
**Analogs found:** 6 / 6 code files (all role-match or exact); writing deliverables have 3 competing style analogs each, surfaced for planner choice

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/dsav_watcher.py` (NEW) | service (poll daemon) | event-driven / batch | `data-service/dg_context.py` (`fetch_existing_design_states`, injectable-session shape) | role-match (no direct daemon-thread analog exists in-repo; `dg-reasoner/reasoning.py`'s `multiprocessing.Process` backgrounding is the nearest concurrency precedent but wrong primitive) |
| `data-service/app.py` — `POST /designstate/capture` route (NEW) | route/controller | request-response (write) | `data-service/app.py` `connector_heartbeat` (`POST /connectors/heartbeat`, inline Bearer auth) | role-match |
| `data-service/app.py` — `lifespan` startup wiring (NEW) | config/bootstrap | event-driven (process lifecycle) | none in-repo (zero `on_event`/`lifespan`/`threading` in `app.py` today) — nearest neighbours are `read_single`/`write_query` (`app.py:302-316`) for the per-call session discipline the thread must follow | no analog — greenfield, say so plainly |
| `data-service/app.py` — captured `ValidationRun` row completion (MODIFIED in place, `SET`) | model/write-path | CRUD (update) | `data-service/app.py` `_persist_shacl_report` (`app.py:1796-1814`) for the `SET`-in-place shape; `store_validation_run` (`app.py:455-513`) as **read-only reference for row shape — do not edit** (D-10) | exact (persist shape) / do-not-edit reference |
| `data-service/app.py` — `IntegrationConfig {provider:'AutoValidation'}` (NEW row, existing label) | config/model | CRUD | `data-service/app.py` `upsert_integration_config` / `get_integration_config` (`app.py:415-452`) | exact |
| `data-service/app.py` — SHACL call for auto-run verdict | service (proxy call) | request-response (external HTTP) | `data-service/app.py` `_call_shacl_validate` (`app.py:1749-1793`) | exact call shape / **different error policy** (see below) |
| `data-service/tests/test_dsav_watcher.py` (NEW) | test | unit | `data-service/tests/test_dg_context.py` `FixtureSession` + `TestContextAssemble` (lines 104-119, 122+) | exact |
| `data-service/tests/test_designstate_capture.py` (NEW) | test | request-response | `data-service/tests/test_connectors.py` (`TestClient` construction, lines 20-29) | role-match |
| DSAV-01 investigation note (NEW, phase dir) | doc | — | none code-shaped; no existing DSAV-01-style note in repo | no analog — new artifact type |
| DSAV-03 ADR (NEW, `DG_OBSIDIAN/knowledge/decisions/`) | doc | — | 3 coexisting ADR styles (see below) | style choice needed, not analog gap |

## Pattern Assignments

### `data-service/dsav_watcher.py` (service, event-driven/batch — the pure `poll_once()` requirement, D-03)

**Analog:** `data-service/dg_context.py` `fetch_existing_design_states()` (lines 420-439) + `data-service/tests/test_dg_context.py` `FixtureSession` (lines 104-119)

**Injectable-session core pattern** (`data-service/dg_context.py:420-439`):
```python
def fetch_existing_design_states(project: str, session: Any = None) -> list[dict[str, Any]]:
    """... `session` is duck-typed identically to `fetch_existing_entities()` --
    pass a FixtureSession in unit tests, omit in production for a lazily-opened
    live session."""
    if session is not None:
        result = session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
        rows = [dict(record) for record in result]
    else:
        with _get_driver().session() as live_session:
            result = live_session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
            rows = [dict(record) for record in result]
    return [ ... ]
```
`poll_once(session=None)` must follow this exact `if session is not None: ... else: with _get_driver().session() as live_session: ...` branch shape — not `app.py`'s `read_single`/`write_query` (always open their own session, non-injectable, cannot be unit-tested without live Neo4j).

**Test-double pattern** (`data-service/tests/test_dg_context.py:104-119`):
```python
class FixtureSession:
    """Duck-types `neo4j.Session.run(query, **params)` with zero live Neo4j.
    ... returns a fixed list of existing-entity rows regardless of the query
    text, just records the last `project` kwarg it was called with so tests
    can assert the bound-parameter contract."""
    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows if rows is not None else []
        self.last_project: str | None = None

    def run(self, query: str, **params):
        self.last_project = params.get("project")
        return list(self._rows)
```
`data-service/tests/test_dsav_watcher.py` should define an equivalent (or import/extend this exact class) to drive `poll_once()` with zero thread and zero `time.sleep`, per D-03.

**Concurrency primitive note:** `dg-reasoner/reasoning.py` backgrounds `sync_reasoner()` via `multiprocessing.Process` for hard-timeout isolation — confirms the project's comfort with stdlib-only concurrency over a job-runner dependency, but is the wrong primitive (process, not thread) for this daemon. Use `threading.Thread(daemon=True)` + `threading.Event` per RESEARCH.md Pattern 3, not this analog directly.

**Per-poll-tick session discipline** (`data-service/app.py:302-316`, `read_single`/`read_many`/`write_query`):
```python
def read_single(query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with driver.session() as session:
        record = session.run(query, parameters or {}).single()
    return None if record is None else record.data()
```
Every `poll_once()` call must open (and close) its own `driver.session()` exactly like this — never a session held across poll iterations or shared across threads (Neo4j thread-safety contract; see RESEARCH.md Anti-Patterns).

---

### `data-service/app.py` — `POST /designstate/capture` (route/controller, request-response write)

**Analog:** `data-service/app.py` `connector_heartbeat` (`app.py:1150-1178`)

**Inline Bearer-token auth pattern to copy verbatim in shape** (`app.py:1155-1164`):
```python
@app.post("/connectors/heartbeat")
def connector_heartbeat(request: Request):
    """Token-authenticated heartbeat. Updates the connector's last_connection
    and returns its derived status. 401 on unknown/revoked token (CONNB-03).
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[len("Bearer "):].strip() if auth_header.startswith("Bearer ") else ""
    record = connectors.record_heartbeat(token) if token.startswith(connectors.TOKEN_PREFIX) else None
    if record is None:
        raise _structured_error_response(
            "Invalid or revoked connector token.",
            "Create a new credential via POST /connectors/{connector_id}/credentials.",
            "CONNECTOR_AUTH_FAILED",
            401,
        )
    return HeartbeatResponse(...)
```
This is the **only existing caller** of the connector-token pattern in the entire codebase — no `Depends()`-wrapped FastAPI dependency exists anywhere. The planner must decide (per RESEARCH.md Pattern 4 / Open Question 2) whether to extract a shared `require_connector_token()` dependency or duplicate this 3-line inline block for the capture route. **Use `authenticate_token()`, not `record_heartbeat()`** — the latter stamps `last_connection`, which would misrepresent capture traffic as connector liveness (a category error the analog itself warns against).

**Auth primitive** (`data-service/connectors.py:212-223`):
```python
def authenticate_token(token: str) -> dict[str, Any] | None:
    """Match a plaintext token against non-revoked credentials by hash.
    Returns the credential record or None if unknown/revoked."""
    if not token:
        return None
    digest = hash_token(token)
    for record in load_credentials():
        if record.get("token_hash") == digest and not record.get("revoked"):
            return record
    return None
```
The returned `record["project"]` (defaulting to `"default-project"`, per `create_credential` at `connectors.py:181`) is what the capture route must compare against the request's own `project` field to satisfy the mandatory `<threat_model>` cross-project-scoping check.

**Request payload shape to echo (subset)** — `data-service/app.py:215-227` `ValidationPublishRequest`:
```python
class ValidationPublishRequest(BaseModel):
    project: str
    statePayloadJson: str | None = None
    validStatus: list[bool] | None = None
    rules: list[ValidationPublishRulePayload] = Field(default_factory=list)
    ruleResults: list[ValidationPublishRuleResultPayload] = Field(default_factory=list)
    entities: list[ValidationPublishEntityPayload] = Field(default_factory=list)
```
The new `DesignStateCaptureRequest` model should follow this Pydantic-BaseModel convention with `project: str` + `statePayloadJson: str | None = None` at minimum; `validStatus` is meaningless pre-verdict so is likely omitted from the capture payload.

---

### `data-service/app.py` — app-startup `lifespan` wiring (config/bootstrap, NO ANALOG)

**No existing analog.** Confirmed by grep: zero occurrences of `on_event`, `lifespan`, or `threading` anywhere in `app.py` today — this phase is greenfield for startup hooks. Do not invent a false analog.

**Nearest neighbours** (per-call session discipline the daemon thread must mirror) — `data-service/app.py:302-316`:
```python
def write_query(query: str, parameters: dict[str, Any] | None = None) -> None:
    with driver.session() as session:
        session.run(query, parameters or {}).consume()
```
The module-level `driver` object (`app.py:93`, created eagerly at import) is safe to share across threads; each thread/poll-tick must open its own session — this is the one concrete carry-over from existing code, everything else about `lifespan` itself must be built from the FastAPI official-docs idiom cited in RESEARCH.md Pattern 3 (`fastapi.tiangolo.com/advanced/events/`), not copied from this repo.

---

### `data-service/app.py` — captured `ValidationRun` row completion (model/write-path, CRUD update)

**Analog (template to copy):** `_persist_shacl_report()` (`app.py:1796-1814` region, `SET`-in-place after `_call_shacl_validate`):
```python
def _persist_shacl_report(project: str, run_id: str, report_json: str) -> None:
    """Persist a SHACL status dict as `shaclReportJson` on the ValidationRun node.
    Additive, second write after `store_validation_run` -- ordering of the ..."""
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET run.shaclReportJson = $shaclReportJson
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id, "shaclReportJson": report_json},
    )
```
This is the exact `MERGE {key}` + `SET {mutable fields}`, all-bound-parameters shape D-01/D-07/D-08/D-13 all reuse. RESEARCH.md's proposed `COMPLETE_QUERY`/`FAIL_QUERY` (below) follow this template — they are `[ASSUMED — proposed]`, not existing code, and must be verified against live Neo4j.

**DO-NOT-EDIT reference (read-only, row-shape source of truth, D-10):** `store_validation_run()` (`app.py:455-513`):
```python
def store_validation_run(
    project: str, run_id: str, config: SpeckleProjectConfigPayload,
    publish_result: dict[str, str], rules_summary: list[dict[str, Any]],
    entities: list[dict[str, Any]], state_payload_json: str | None = None,
    valid_status_param: list[bool] | None = None,
) -> None:
    ...
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET
            run.speckleProjectId = $speckleProjectId,
            ...
            run.status = 'completed',
            run.ValidStatus = $validStatus,
            run.SendStatus = true,
            run.createdAt = $createdAt
        """,
        { ... },
    )
```
**Must stay byte-for-byte untouched per D-10.** Zero regression surface on the shipped manual-publish path. Show this to the planner purely as the row-property vocabulary (`status`, `ValidStatus`, `SendStatus`, `statePayloadJson`, `createdAt`) the new capture/complete Cypher must stay consistent with — not as code to modify.

**Synthesized proposals (RESEARCH.md §Code Examples, `[ASSUMED]` — not existing code, needs live-Neo4j verification):**
```python
CAPTURE_QUERY = """
MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET run.statePayloadJson = $statePayloadJson, run.status = 'captured',
    run.capturedAt = $capturedAt, run.attempts = 0
"""

COALESCE_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, status:'captured'})
WITH run ORDER BY run.capturedAt DESC
WITH collect(run) AS runs
UNWIND runs[1..] AS stale
SET stale.status = 'superseded'
RETURN runs[0].runId AS keptRunId
"""

COMPLETE_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET run.status = 'completed', run.trigger = 'auto', run.verdictSource = 'shacl',
    run.shaclReportJson = $shaclReportJson, run.ValidStatus = $validStatus,
    run.completedAt = $completedAt
"""

FAIL_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET run.attempts = run.attempts + 1,
    run.status = CASE WHEN run.attempts + 1 >= $maxAttempts THEN 'failed' ELSE 'captured' END,
    run.lastError = $reason
"""
```

---

### `data-service/app.py` — `IntegrationConfig {provider:'AutoValidation'}` config row (D-13)

**Analog (exact key/merge shape to reuse unchanged):** `upsert_integration_config()` / `get_integration_config()` (`app.py:415-452`):
```python
def get_integration_config(project: str) -> SpeckleProjectConfigPayload | None:
    row = read_single(
        """
        MATCH (cfg:IntegrationConfig {graph:$graph, provider:'Speckle', project:$project})
        RETURN cfg.speckleProjectId AS speckleProjectId, ...
        """,
        {"graph": VALIDATION_GRAPH, "project": project},
    )
    return None if row is None else normalize_speckle_project_config_payload(SpeckleProjectConfigPayload(**row))

def upsert_integration_config(project: str, payload: SpeckleProjectConfigPayload) -> SpeckleProjectConfigPayload:
    payload = normalize_speckle_project_config_payload(payload)
    write_query(
        """
        MERGE (cfg:IntegrationConfig {graph:$graph, provider:'Speckle', project:$project})
        SET
            cfg.speckleProjectId = $speckleProjectId,
            ...
            cfg.updatedAt = $updatedAt
        """,
        { ... "updatedAt": datetime.now(timezone.utc).isoformat() },
    )
    return get_integration_config(project) or payload
```
Second provider row (`provider:'AutoValidation'`) reuses the exact `{graph, provider, project}` MERGE key — only the `provider` literal and the `SET` field list differ (e.g. `enabled`, `publishEnabled`, `debounceWindowSeconds`, `rateLimitPerMinute`). **Absent row = disabled** — do not extend `_auto_configure_integration`'s implicit-env-var-create precedent (`app.py:1730-1746`) to this new provider (D-13 explicitly rejects that).

---

### `data-service/app.py` — SHACL verdict call for auto-runs (D-05, error-policy departure per D-08)

**Analog (same call, DIFFERENT error policy):** `_call_shacl_validate()` (`app.py:1749-1793`):
```python
def _call_shacl_validate(project: str, run_id: str) -> dict[str, Any]:
    """... this proxy is catch-all non-fatal and NEVER raises -- a SHACL
    failure (unreachable/timeout/error) must never endanger the Speckle
    publish hot path. Returns a status dict:
      - {"status": "ok", **body} on success
      - {"status": "timeout"} on httpx timeout / sidecar {"error":"timeout"} / HTTP 504
      - {"status": "unavailable"} on connect error or any other exception
    """
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/shacl/validate",
            json={"project": project, "run_id": run_id},
            timeout=httpx.Timeout(connect=2.0, read=DG_SHACL_HTTP_TIMEOUT_SECONDS, write=2.0, pool=2.0),
        )
    except httpx.TimeoutException:
        return {"status": "timeout"}
    except Exception:
        return {"status": "unavailable"}
    ...
    return {"status": "ok", **body}
```
The watcher calls this **exact function, unchanged** — same `httpx.Timeout` shape, same three-state status dict. **But D-08 deliberately departs from its degrade-never-raise philosophy at the call site**: where the manual-publish caller treats `"timeout"`/`"unavailable"` as non-fatal and completes the run anyway (Phase 823 Plan 03 precedent), the watcher must instead: leave `status:'captured'` (retry via `FAIL_QUERY`'s attempt-counter path) rather than silently completing with no verdict. Flag this explicitly in the plan as "same helper function, opposite caller-side error handling" — do not let the analog's own docstring philosophy leak into the new caller's behavior.

---

### `data-service/tests/test_dsav_watcher.py` (test, unit)

**Analog:** `data-service/tests/test_dg_context.py` `FixtureSession` + `TestContextAssemble` (lines 104-119, 122-128 shown above). Reuse `FixtureSession` verbatim or subclass it; assert on `last_project` the same way existing tests do for the bound-parameter contract (`T-29-03a` precedent).

### `data-service/tests/test_designstate_capture.py` (test, request-response)

**Analog:** `data-service/tests/test_connectors.py:20-29`:
```python
from fastapi.testclient import TestClient
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
```
Use this exact `TestClient` construction convention for the 401/200 auth-path tests. **Caution (RESEARCH.md Pitfall 3):** once `lifespan` is added to `app.py`, verify this bare-instantiation pattern (used by every existing test file, not `with TestClient(app) as client:`) does not unexpectedly trigger a live background thread — prefer calling `dsav_watcher.start_watcher()`/`stop_watcher()` directly in the watcher's own tests rather than depending on `TestClient`'s lifespan-triggering behavior.

---

## Shared Patterns

### Parameterized MERGE/SET, never string-interpolated
**Source:** `_persist_shacl_report()` (`app.py:1796-1814`), `store_validation_run()` (`app.py:455-513`, read-only), `upsert_integration_config()` (`app.py:430-452`)
**Apply to:** All new Cypher this phase writes (capture, coalesce, complete, fail, config upsert) — every value passed as a bound parameter, no f-string/`.format()` Cypher construction anywhere.

### Injectable-session testability
**Source:** `data-service/dg_context.py:420-439` + `data-service/tests/test_dg_context.py:104-119`
**Apply to:** `dsav_watcher.poll_once(session=None)` — the load-bearing pattern for D-03's "pure function, testable without a thread" requirement.

### Inline Bearer-token auth (no shared dependency exists yet)
**Source:** `data-service/app.py:1155-1157` (`connector_heartbeat`)
**Apply to:** `POST /designstate/capture` — either duplicate the 3-line inline block (matches existing minimal-abstraction style) or extract a `require_connector_token()` `Depends()` wrapper (cleaner, but a new abstraction with only 2 call sites). Planner's call per RESEARCH.md Open Question 2 — both are internally consistent with the codebase.

### Per-call Neo4j session discipline (never span sessions across threads or iterations)
**Source:** `data-service/app.py:302-316` (`read_single`/`read_many`/`write_query`)
**Apply to:** `dsav_watcher.py`'s poll loop — every `poll_once()` tick opens and closes its own `driver.session()`.

### Degrade-never-raise around the SHACL sidecar — DEPARTED FROM, not applied
**Source:** `_call_shacl_validate()` (`app.py:1749-1793`), Phase 823 Plan 03 precedent
**Apply to:** The watcher reuses the *function* unchanged but must NOT reuse the manual-publish caller's *policy* of completing the run regardless of SHACL status. D-08 requires the departure be justified in the plan, not applied silently — call this out as its own plan section.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `data-service/app.py` — FastAPI `lifespan` startup hook | config/bootstrap | event-driven | Zero `on_event`/`lifespan`/`threading` usage anywhere in `app.py` today (confirmed by grep this session) — this phase is the first to add any startup hook. Use the FastAPI official-docs idiom from RESEARCH.md Pattern 3, not an in-repo analog. |
| DSAV-01 investigation note | doc | — | No existing "trigger architecture comparison + measured evidence" note format in `.planning/milestones/v9.0-phases/`; write it as a plain evidence table + narrative, no template to match. |
| DSAV-03 ADR | doc | — | Not "no analog" but "three competing analogs" — see below; the planner must pick one explicitly. |

### DSAV-03 ADR — three coexisting front-matter/section styles (planner must choose)

**Style A — YAML front-matter, `tags`/`date`/`status`** (`DG_OBSIDIAN/knowledge/decisions/Phase 823 SHACL validation layer design decisions.md`):
```yaml
---
tags: [decision, shacl, phase-823, v8.2]
date: 2026-07-12
status: resolved
---

# Phase 823: SHACL Validation Layer — Design Decisions

## D-823-01: Canonical envelope контракт

**Решение:** ...
```
Numbered decision-ID headers (`D-823-01`), bilingual prose (RU/EN mixed), no `name`/`description`/`metadata` block.

**Style B — minimal YAML, `tags`/`date` only, no `status`** (`DG_OBSIDIAN/knowledge/decisions/DesignState persists to ValidGraph not Metagraph.md`):
```yaml
---
tags: [decision, ontology, v7.0, schema]
date: 2026-07-03
---

# DesignState persists to ValidGraph, not Metagraph

## Decision

A `DesignState` node's Neo4j `graph` tag moves from **`Metagraph`** ... to **`ValidGraph`** in v7.0.
- Written **only by VALIDATOR on publish** ...
```
Single-topic title (not phase-numbered), `## Decision` / bullet-list body, no per-item decision IDs.

**Style C — structured `name`/`description`/`metadata` front-matter** (`DG_OBSIDIAN/knowledge/decisions/Phase 37 structure validation — rule-mapping file-first, severity taxonomy, ephemeral results.md`):
```yaml
---
name: phase-37-open-planning-resolutions
description: Three CONTEXT.md "Open for Planning" items resolved during Phase 37 planning
metadata:
  type: decision
  phase: 37
  context_items: 3
  decision_date: 2026-07-27
---

# Phase 37: Open-for-Planning Items — Design Decisions

During /gsd-plan-phase 37, three deliberate "Open for planning" items in 37-CONTEXT.md were resolved by the planner. Recorded here as binding design decisions.

## Decision 1: Rule-Mapping File Location and Shape
```
Machine-readable `metadata` block (`type`/`phase`/`decision_date`), numbered `## Decision N:` sections, explicit provenance sentence tying it back to the planning session.

**Recommendation for the planner:** DSAV-03 most resembles Style B (single cohesive decision, not a per-item resolutions log) but should adopt Style C's `metadata` block (`phase: 39`, `decision_date`) for machine-readability given `DG_OBSIDIAN/00-home/index.md`'s § Decisions links every phase decision file — pick one explicitly in the plan rather than defaulting silently.

## Metadata

**Analog search scope:** `data-service/app.py`, `data-service/connectors.py`, `data-service/dg_context.py`, `data-service/tests/`, `dg-reasoner/reasoning.py`, `dg-reasoner/valid_graph_export.py`, `DG_OBSIDIAN/knowledge/decisions/`
**Files scanned:** 6 code files (targeted line-range reads), 3 ADR files (front-matter comparison), graphify graph query for orientation
**Pattern extraction date:** 2026-07-27
