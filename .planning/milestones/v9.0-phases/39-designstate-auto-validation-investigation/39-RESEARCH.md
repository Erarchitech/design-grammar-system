# Phase 39: DesignState Auto-Validation Investigation - Research

**Researched:** 2026-07-27
**Domain:** In-process background polling in a sync-def FastAPI service; Neo4j Cypher state-machine design; connector-token auth reuse; investigation/ADR artifact conventions
**Confidence:** MEDIUM-HIGH (all core code claims verified by direct file read at cited line numbers; the two Cypher-shape proposals in §Code Examples are synthesized, not lifted from existing code, and are flagged accordingly)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 .. D-16, D-A, D-B — see 39-CONTEXT.md for full rationale; not re-litigated here)

- D-A: prototype targets path (b), data-service watcher. Paths (a)/(c) compared on paper only.
- D-B: prototype is spike quality, ADR-scoped; guardrails demonstrated not merely described; off-by-default flag; hardening deferred by the ADR.
- D-01: capture event = `:ValidationRun` row with `status:'captured'`, reusing the existing row shape/key `{graph, project, runId}`. No new label, no schema-propagation sweep.
- D-02: capture row written by a simulated client — new `POST /designstate/capture` + curl/pytest driver posting a real `statePayloadJson` v2 envelope. No GH wiring, no live Rhino. GH-side capture is named in the ADR as follow-up milestone scope.
- D-03: watcher = in-process daemon poll thread started at app startup behind the off-by-default flag, polling `status='captured'` rows past a cursor. Poll body **must** be factored as a pure function testable without a thread or sleep.
- D-04: DSAV-01 comparison is measured for (b), analytic for (a)/(c), anchored to (b)'s real numbers plus recorded blockers.
- D-05: verdict comes from the existing SHACL/dg-reasoner path (`dg-reasoner/valid_graph_export.py:43` builds ABox directly from `run.statePayloadJson` — zero new export work). Rejected: canvas-bridge write path (read-only by design), Python SWRL port (second evaluator divergence hazard).
- D-06: SHACL/SWRL coverage gap is accepted and is the headline ADR finding — a SHACL-verdicted auto-run answers "is this state well-formed?", not "does this design comply?". Closing the gap is ADR follow-up item #1. Re-deciding the SWRL/SHACL partition line is out of bounds for this phase (`spec/RULE-PARTITION-POLICY.md` governs it).
- D-07: completed auto-run derives `ValidStatus` from the SHACL report; stamps `run.trigger='auto'` and `run.verdictSource='shacl'`.
- D-08: SHACL sidecar down/timeout → row stays `status:'captured'`, retried with bounded backoff, then `status:'failed'` with a reason. Deliberately departs from the Phase 823 degrade-never-raise precedent. Requires an attempt counter on the row.
- D-09: auto-runs persist-only by default; Speckle publish is opt-in behind a separate per-project flag. Makes SC2's no-flood guarantee structural.
- D-10: no new persist-without-publish function — completing a captured row is a `SET` in place. `store_validation_run()` stays byte-for-byte untouched.
- D-11: prototype demos the publish leg exactly once with auto-publish on; everything else persist-only.
- D-12: auto-runs stay visible in the normal run list; `run.trigger='auto'` is the only distinction; run-list pollution recorded as a known consequence in the ADR.
- D-13: config lives on an `IntegrationConfig {graph, provider:'AutoValidation', project}` row, reusing the exact key/merge pattern as the `provider:'Speckle'` row. Absent row = disabled.
- D-14: debounce = trailing-edge coalesce, newest wins; superseded rows marked `status:'superseded'`, not deleted.
- D-15: guardrail counters (debounce timer, rate-limit window) are in-memory in the watcher process, keyed by project. Restart resets the window — recorded as an explicit ADR line, not solved here.
- D-16: DSAV-01 note lives in `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/`; DSAV-03 ADR lives in `DG_OBSIDIAN/knowledge/decisions/`, cross-linked.

### Claude's Discretion

None — every question in the discussion was answered with an explicit choice (per 39-CONTEXT.md).

### Open for the Planner (NOT decided here — this research's primary contribution)

- **Capture-endpoint authentication** is unresolved and is the highest-severity threat-model item. Candidate: reuse the Phase 825 project-scoped connector token. Plans MUST carry a `<threat_model>` block covering authentication, per-project scoping, rate-limit bypass, and publish-flood. See §5 below for the concrete investigation of the candidate mechanism and its gaps — this research presents options with trade-offs, it does not pick one.

### Deferred Ideas (OUT OF SCOPE for this phase)

- GH-side capture wiring (network client on DESIGN STATE / CAPTURE toggle on VALIDATOR) — ADR follow-up, D-02.
- Closing the SWRL coverage gap — ADR follow-up item #1, D-06.
- First-class `:DesignState` nodes in ValidGraph — Phase-29-flagged backlog, D-01 routes around it.
- Design-compliance SHACL shapes — blocked on `spec/RULE-PARTITION-POLICY.md`.
- UI treatment of auto-runs (filtering/badging `trigger:'auto'`) — follow-up milestone, D-12.
- Guardrail durability across restarts — explicit ADR line, D-15.
- Retention cap on auto-runs — a fourth guardrail beyond DSAV-03's three named ones, declined.
- Empirically installing APOC to verify path (c)'s blocker — declined as a detour, D-04.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSAV-01 | Investigation note compares trigger architectures (GH hook, data-service watcher, Neo4j write event) with latency/publish-flood/Speckle-noise analysis | §4 (measurement methodology for the measured path (b) numbers); §3 (Cypher shapes that produce the debounce collapse ratio); path (a)/(c) analytic treatment is already in 39-CONTEXT.md D-04/§Environment constraints — cited, not re-derived |
| DSAV-02 | Working prototype: capturing a new DesignState produces a validation Run without a manual VALIDATOR trigger | §1 (poll-thread startup idiom), §2 (pure poll-function precedent), §3 (Cypher for capture/claim/complete), §5 (auth candidate) |
| DSAV-03 | ADR records chosen architecture + guardrails, scopes full implementation to a follow-up milestone | §7 (ADR structure/naming/front-matter conventions from existing vault files) |

</phase_requirements>

## Summary

This phase's mechanics live entirely inside `data-service/app.py` (2,900+ lines, sync-`def` FastAPI throughout — confirmed by grep: zero occurrences of `on_event`, `lifespan`, or `threading` anywhere in the file today) plus one or two new sibling modules following the existing `connectors.py` / `dg_context.py` / `cg_recognition.py` pattern of app.py importing a topic module and wiring thin route handlers to it. There is **no existing background-thread precedent in data-service** — this phase introduces the first one. The closest analog in the repo is `dg-reasoner/reasoning.py`, which backgrounds `sync_reasoner()` in a `multiprocessing.Process` (not a thread) for hard-timeout isolation — not directly reusable, but confirms the project's general comfort with a stdlib-only concurrency primitive over adding a job-runner dependency.

The single most load-bearing precedent for D-03's "pure poll function" requirement already exists in this exact codebase: `data-service/dg_context.py`'s `fetch_existing_entities(project, session=None)` / `fetch_existing_design_states(project, session=None)` / `fetch_computgraph_subgraph(project, definition_id, session=None)` all take an optional duck-typed `session` parameter, defaulting to a lazily-opened module-driver session in production and accepting an injected `FixtureSession` in tests (`data-service/tests/test_dg_context.py:104-119`). The watcher's poll body should follow this exact idiom, not `dg-reasoner`'s `session` parameter (same idea, different module) and not `app.py`'s own `read_single`/`write_query` helpers (which always open their own session, non-injectable). `_persist_shacl_report` (`app.py:1796-1814`) and `store_validation_run` (`app.py:455-513`) are the parameterized `MERGE`/`SET` templates to copy verbatim in shape.

Neo4j's Python driver documentation confirms the module-level `driver` object (`app.py:93`, created eagerly at import) is safe to share across threads; each thread must open its own `driver.session()` and never share or span a session across threads — which is exactly what `read_single`/`read_many`/`write_query` already do per-call (`app.py:302-316`), so the watcher thread can reuse the identical per-call session pattern with no new risk. FastAPI's `@app.on_event("startup")` is deprecated (since FastAPI 0.93+) in favor of the `lifespan` async context manager, which is also the cleaner fit for a start-before-yield / stop-and-join-after-yield background thread.

Testing follows the two-tier convention already documented in `data-service/tests/README.md`: a host-run unit tier (`python -m pytest data-service/tests/ -q`, no Neo4j) covers the pure poll function, debounce/coalesce logic, and Cypher-shape assertions; an in-container integration tier (`docker compose exec data-service python -m pytest tests/ -q`) is required for anything touching live Neo4j, the dg-reasoner SHACL sidecar, or the one D-11 Speckle-publish leg — and carries a documented image-staleness gotcha (new files invisible in the running container until rebuild) that will recur for this phase's new module(s).

The Phase 825 connector token (`connectors.authenticate_token`, `connectors.py:212-223`) is the strongest existing candidate for capture-endpoint auth: it is already project-scoped (`record["project"]`, defaulting to `"default-project"`), already hashes tokens (SHA-256, never stores plaintext), and is a plain function with no FastAPI dependency wrapper yet — every current caller (`connector_heartbeat`, `app.py:1150-1178`) inlines the same three-line Bearer-header-extraction pattern. Using `record_heartbeat()` for capture auth would be a category error (it stamps `last_connection`, polluting the connector's own liveness signal with capture traffic); `authenticate_token()` is the correct primitive to reuse or wrap in a new dependency.

**Primary recommendation:** implement the watcher as a new sibling module (e.g. `data-service/dsav_watcher.py`, mirroring `connectors.py`'s shape) exposing (a) a pure `poll_once(session=None) -> PollResult` function following `dg_context.py`'s injectable-session idiom, (b) a thin `start_watcher(app)` / `stop_watcher()` pair wired into a FastAPI `lifespan` context manager, and (c) the new `POST /designstate/capture` route reusing `connectors.authenticate_token()` for auth and the existing `ValidationRun` MERGE/SET conventions for the row. Test the pure function on the host tier with a `FixtureSession`; test the live daemon, SHACL round-trip, and the one publish leg in-container.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `POST /designstate/capture` endpoint | API/Backend | — | New FastAPI route in `data-service`; writes the `status:'captured'` row (D-01/D-02) |
| Poll/watcher daemon thread | API/Backend | — | In-process background thread inside `data-service`, no new service (D-03) |
| Capture-endpoint authentication | API/Backend | — | Reuses (or extends) the existing connector-token check already living in `data-service` (D-A "Open for planner") |
| Debounce / rate-limit guardrail state | API/Backend | — | In-memory in the watcher process per D-15 — explicitly NOT the Database tier (no write amplification against the DB being polled) |
| SHACL verdict computation | API/Backend (proxy) | External Service (dg-reasoner sidecar) | `_call_shacl_validate`/`_persist_shacl_report` already proxy to the `dg-reasoner` container; D-05 reuses this unchanged |
| `ValidationRun` capture/claim/complete rows | Database/Storage (Neo4j) | — | ValidGraph, existing label/key shape (D-01/D-10) |
| `IntegrationConfig {provider:'AutoValidation'}` | Database/Storage (Neo4j) | API/Backend (read/write helpers) | Config-as-data, mirrors the existing Speckle config row (D-13) |
| Speckle publish (opt-in, single demo run) | External Service | API/Backend (client) | Unchanged `publish_validation_version` / Speckle stack; only reached once per D-11 |
| DSAV-01 investigation note | Docs (phase dir) | — | Not a runtime tier — evidence artifact |
| DSAV-03 ADR | Docs (Obsidian vault) | — | Not a runtime tier — decision record |

## Standard Stack

### Core

No new external packages are required. This phase is implementable entirely with dependencies already pinned in `data-service/requirements.txt` (`cryptography`, `fastapi`, `httpx`, `pydantic>=2.7,<3`, `neo4j`, `pytest`, `specklepy==3.2.4`, `uvicorn` — read directly from the file) plus Python's own standard library (`threading`, `time`).

| Library | Version | Purpose | Why Standard (in this repo) |
|---------|---------|---------|------------------------------|
| `threading` (stdlib) | Python 3.11 (per `data-service/Dockerfile`'s `FROM python:3.11-slim`) | Background poll thread (D-03) | No async job runner exists anywhere in `data-service`; matches the sync-`def` convention CONTEXT.md and this research both confirm by direct grep |
| `neo4j` | already pinned, unversioned in requirements.txt | Poll queries, capture/claim/complete Cypher | Same driver object already used everywhere in `app.py`; thread-safety of the shared driver + per-thread sessions is documented Neo4j behavior (see Sources) |
| `httpx` | already pinned | SHACL sidecar proxy call, reused unchanged (`_call_shacl_validate`) | Existing pattern, D-05/D-08 build on it directly |
| `fastapi` | unpinned (no version floor in requirements.txt — **unverified installed version, flagged below**) | `lifespan` context manager for thread start/stop | Modern FastAPI replacement for the deprecated `@app.on_event` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` (existing, host + in-container tiers) | already pinned | Pure poll-function unit tests; live-Docker burst-measurement tests | Follow `data-service/tests/README.md`'s two-tier split exactly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `threading.Thread(daemon=True)` | APScheduler / Celery beat / a proper job runner | Rejected by D-03 itself — "no new dependency," matches the sync-`def` prevailing style; a job runner is disproportionate to a spike-quality investigation prototype |
| In-process poll loop | Neo4j write-event trigger (path c) | Already rejected on paper per D-04/39-CONTEXT.md — Community edition has no CDC, APOC not installed, and the reliable outbox pattern structurally collapses into path (b) anyway. **Not re-derived here per scope discipline.** |

**Installation:** none — no new packages to add to `requirements.txt`.

**Version verification:** `data-service/requirements.txt` pins `fastapi` with no version floor, so the actual installed version inside the built image is **not verified in this research session** — [ASSUMED] that it is recent enough to support `lifespan` (available since FastAPI 0.93, a multi-year-old release as of this writing, so this is a low-risk assumption, but the planner should confirm with `docker compose exec data-service pip show fastapi` before committing to the `lifespan` pattern over `on_event`).

## Package Legitimacy Audit

**Not applicable — this phase installs zero new external packages.** All implementation work reuses `threading` (stdlib) plus the already-pinned `neo4j`, `httpx`, `fastapi`, and `pydantic` dependencies in `data-service/requirements.txt`. No `npm view` / `pip index versions` / registry check was needed or performed.

## Architecture Patterns

### System Architecture Diagram

```
        [pytest / curl driver]                         [Grasshopper — OUT OF SCOPE, D-02]
                 |
                 v POST /designstate/capture
      +---------------------------+
      |  data-service (FastAPI)   |
      |  ------------------------ |
      |  1. authenticate_token()  |<---- connectors.py (Phase 825 project token,
      |     (or extended dep.)    |       candidate, D-A "open for planner")
      |  2. MERGE ValidationRun   |
      |     {status:'captured'}   |----> Neo4j (ValidGraph)
      +---------------------------+
                 |
                 |  (in-process, no HTTP hop)
                 v
      +---------------------------------------------+
      |  watcher daemon thread (D-03)                |
      |  started/stopped via FastAPI lifespan        |
      |  loop: poll_once(session=None)                |
      |    a. claim next captured row(s) past cursor  |
      |    b. debounce: trailing-edge coalesce        |
      |       (D-14) -> mark stale 'superseded'       |
      |    c. rate-limit guard (in-memory, D-15)      |
      |    d. call _call_shacl_validate() (existing)  |---> dg-reasoner sidecar
      |    e. SET run status='completed'|'failed',    |       (SHACL /shacl/validate,
      |       trigger='auto', verdictSource='shacl'   |        reads run.statePayloadJson
      |       (D-07)                                  |        directly, D-05)
      +---------------------------------------------+
                 |
                 |  IF provider:'AutoValidation' row has publish enabled (D-09, opt-in)
                 v
      publish_validation_version() (existing, unchanged) ---> Speckle
                 |
                 v
      run visible in GET /validation/runs/{project} (existing, unchanged, D-12)
```

### Recommended Project Structure

```
data-service/
├── app.py                    # thin route handlers only: POST /designstate/capture,
│                              #   lifespan wiring calling dsav_watcher.start()/stop()
├── dsav_watcher.py            # NEW — mirrors connectors.py's module shape:
│                              #   - poll_once(session=None) pure function (D-03)
│                              #   - claim/coalesce/complete Cypher constants
│                              #   - in-memory guardrail state (debounce timers,
│                              #     rate-limit window) keyed by project (D-15)
│                              #   - start_watcher()/stop_watcher() thread lifecycle
├── connectors.py              # UNCHANGED — authenticate_token() reused, not modified
└── tests/
    ├── test_dsav_watcher.py   # NEW — host tier: poll_once() with FixtureSession,
    │                          #   debounce/coalesce assertions, no thread, no sleep
    └── test_designstate_capture.py  # NEW — TestClient POST /designstate/capture,
                                #   auth 401/200 cases (host tier, mocked/no live Neo4j
                                #   needed for the auth-rejection paths)
```

This mirrors the existing `connectors.py` / `dg_context.py` / `cg_recognition.py` split: `app.py` stays a thin router, each topic gets its own importable, independently-testable module.

### Pattern 1: Injectable-session pure function (the D-03 precedent)

**What:** Business-logic functions accept an optional `session` parameter; production omits it (lazy module driver), tests inject a duck-typed fixture.
**When to use:** Any Cypher-touching logic that must be unit-testable without live Neo4j or a live thread — exactly D-03's requirement.
**Example (verified, existing code):**
```python
# Source: data-service/dg_context.py:420-438 (fetch_existing_design_states)
def fetch_existing_design_states(project: str, session: Any = None) -> list[dict[str, Any]]:
    if session is not None:
        result = session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
        return [dict(record) for record in result]
    with _get_driver().session() as live_session:
        result = live_session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
        return [dict(record) for record in result]

# Source: data-service/tests/test_dg_context.py:104-119
class FixtureSession:
    """Duck-types neo4j.Session.run(query, **params) with zero live Neo4j."""
    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows if rows is not None else []
        self.last_project: str | None = None

    def run(self, query: str, **params):
        self.last_project = params.get("project")
        return list(self._rows)
```
The watcher's `poll_once(session=None)` should follow this exact shape so `data-service/tests/test_dsav_watcher.py` can drive it directly with a `FixtureSession`, with zero thread and zero `time.sleep`, per D-03's explicit requirement.

### Pattern 2: Parameterized MERGE/SET, never string-interpolated (the D-01/D-07/D-10/D-13 template)

**What:** All ValidationRun and IntegrationConfig writes use `MERGE {key-properties}` then `SET` the mutable fields, with every value passed as a bound parameter.
**When to use:** Every new Cypher this phase writes (capture, claim, coalesce, complete, config).
**Example (verified, existing code):**
```python
# Source: data-service/app.py:1796-1814 (_persist_shacl_report)
def _persist_shacl_report(project: str, run_id: str, report_json: str) -> None:
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET run.shaclReportJson = $shaclReportJson
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            "shaclReportJson": report_json,
        },
    )
```

### Pattern 3: FastAPI `lifespan` for background thread start/stop

**What:** An async context manager passed to `FastAPI(lifespan=...)`; code before `yield` runs at startup, code after `yield` runs at graceful shutdown.
**When to use:** D-03's poll-thread start/stop. `@app.on_event("startup")`/`@app.on_event("shutdown")` are **deprecated** since FastAPI 0.93 — do not introduce a new deprecated pattern into a codebase that has neither today (verified: zero `on_event`/`lifespan` occurrences currently exist in `app.py`, so this phase is greenfield for startup hooks).
**Example (idiom, not copied from this repo — no lifespan precedent exists here yet):**
```python
# Source: FastAPI official docs, https://fastapi.tiangolo.com/advanced/events/ [CITED]
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI

_stop_event = threading.Event()
_watcher_thread: threading.Thread | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _watcher_thread
    if _auto_validation_enabled_anywhere():  # gate: off-by-default per project (D-B)
        _stop_event.clear()
        _watcher_thread = threading.Thread(target=_poll_loop, args=(_stop_event,), daemon=True)
        _watcher_thread.start()
    yield
    _stop_event.set()
    if _watcher_thread is not None:
        _watcher_thread.join(timeout=5)

app = FastAPI(lifespan=lifespan)
```
`daemon=True` is a safety net (container kill won't hang), but the explicit `stop_event` + `join()` is what makes the thread deterministically stoppable in tests and in a graceful `docker compose stop`.

### Pattern 4: Connector-token authentication (candidate for capture-endpoint auth)

**What:** `connectors.authenticate_token(token)` matches a bearer token's SHA-256 hash against non-revoked credential records and returns the record (including its bound `project`) or `None`.
**When to use:** As the leading candidate for `POST /designstate/capture` auth (D-A "open for planner"). **Not `record_heartbeat()`** — that also stamps `last_connection`, which would misrepresent capture traffic as connector liveness.
**Example (verified, existing code):**
```python
# Source: data-service/connectors.py:212-223 (authenticate_token)
def authenticate_token(token: str) -> dict[str, Any] | None:
    """Match a plaintext token against non-revoked credentials by hash."""
    if not token:
        return None
    digest = hash_token(token)
    for record in load_credentials():
        if record.get("token_hash") == digest and not record.get("revoked"):
            return record
    return None

# Source: data-service/app.py:1155-1157 (current inline caller — the pattern to
# either repeat or extract into a shared FastAPI dependency)
auth_header = request.headers.get("Authorization", "")
token = auth_header[len("Bearer "):].strip() if auth_header.startswith("Bearer ") else ""
```
Gap: no `Depends()`-wrapped FastAPI dependency exists today; every caller (there is exactly one — `connector_heartbeat`) inlines this three-line pattern. The planner should decide whether to extract a small `require_connector_token()` dependency (cleaner, reusable for future endpoints) or duplicate the inline pattern (matches existing style exactly, zero new abstraction risk for a spike). Either is consistent with the codebase; this research does not pick one (per the CONTEXT.md instruction that auth mechanics stay "open for the planner").

### Anti-Patterns to Avoid

- **Sharing a `neo4j.Session` across threads or reusing a session across poll iterations:** the driver is thread-safe to share, but sessions are explicitly documented as not safe for concurrent/cross-thread use and should be short-lived (`neo4j.com/docs/python-manual/current/transactions/` [CITED]). Every poll iteration must open (and close) its own `driver.session()`, exactly like `read_single`/`read_many`/`write_query` already do per-call (`app.py:302-316`).
- **Starting the watcher thread at module import time** instead of inside `lifespan`: this would make every `TestClient(app)` instantiation in unrelated test files silently spin up a live-Neo4j-polling thread, contaminating unrelated test runs. Gate thread start strictly behind (a) the `lifespan` startup hook and (b) the per-project `IntegrationConfig{provider:'AutoValidation'}` flag being enabled somewhere (or simply always start the thread but have `poll_once` immediately no-op if no project has the flag enabled — simpler, and avoids the thread-restart-on-config-change problem entirely).
- **Using `@app.on_event("startup")`:** deprecated since FastAPI 0.93+ [CITED: github.com/fastapi/fastapi discussion #12027, fastapi.tiangolo.com/advanced/events/]. Introducing a newly-deprecated pattern into a codebase that has zero existing startup hooks (verified by grep) is avoidable at zero cost — use `lifespan`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SWRL/design-compliance rule evaluation server-side | A Python SWRL evaluator | Existing SHACL/dg-reasoner path (D-05) | A second evaluator can silently disagree with the C# `RuleEvaluator` — the exact divergence hazard Phase 35-12 solved by single-sourcing `GRAMMAR_CITATION_PATTERNS` (cited in 39-CONTEXT.md D-05) |
| Background job scheduling | A cron-like scheduler, Celery, APScheduler | `threading.Thread(daemon=True)` + `Event`-based stop, started via `lifespan` | Matches the sync-`def` prevailing style; D-03 explicitly rejects new dependencies; a spike-quality prototype does not need job-runner infrastructure |
| Capture-endpoint authentication | A new auth scheme / API-key table | `connectors.authenticate_token()` (Phase 825) | Already project-scoped, already hashes tokens, already has a revoke path; building a parallel auth mechanism duplicates security-relevant code for no reason |
| Speckle-config lookup for auto-runs | A new config table/file | `IntegrationConfig {provider:'AutoValidation', project}` reusing `get_integration_config`/`upsert_integration_config`'s exact `{graph, provider, project}` key shape (`app.py:415-452`) | Zero schema change, zero propagation sweep (D-13) |

**Key insight:** every "don't hand-roll" item in this phase is a reuse-an-existing-pattern decision already locked in CONTEXT.md (D-05, D-13) or directly implied by D-03's "no new dependency" framing — this research's job was to confirm the reused code actually has the shape CONTEXT.md claims (it does, at the cited line numbers) and to name the *new* abstraction (`poll_once`, the watcher module) the phase must still build.

## Common Pitfalls

### Pitfall 1: Container image staleness hides new test/watcher files
**What goes wrong:** the running `data-service` container was built from an older snapshot; new files (`dsav_watcher.py`, new test files) exist on the host but are invisible inside the container until rebuilt, because `data-service/tests/` (and the service code itself) has no live bind-mount in `docker-compose.yml`.
**Why it happens:** documented, recurring gotcha — Phase 37 hit this exact issue (`data-service/tests/README.md` "Known gotcha — image staleness"; `37-01-SUMMARY.md`).
**How to avoid:** `docker compose build --no-cache data-service && docker compose up -d data-service` before any in-container verification step; state this explicitly as a plan task, not an assumed side effect.
**Warning signs:** in-container pytest collects fewer tests than the host tier for no code reason.

### Pitfall 2: Session shared across threads / poll iterations
**What goes wrong:** a long-lived `driver.session()` opened once at thread start and reused across every poll tick violates Neo4j's own thread-safety contract and can produce subtle transaction-state bugs.
**Why it happens:** tempting "optimization" to avoid session-open overhead.
**How to avoid:** open a fresh `driver.session()` inside each `poll_once()` call (or let the injectable-session pattern's `None` branch do it), exactly matching `read_single`/`write_query`'s existing per-call session lifecycle (`app.py:302-316`).
**Warning signs:** intermittent, hard-to-reproduce Cypher failures that don't reproduce when polling interval is slowed down.

### Pitfall 3: `TestClient(app)` lifecycle nuances with `lifespan`
**What goes wrong:** whether `TestClient(app)` actually triggers the `lifespan` context manager depends on how it is used (as a context manager `with TestClient(app) as client:` vs. bare instantiation) and on the installed Starlette/FastAPI version. If tests use the bare form, the watcher thread may never start during tests that expect it to (test flakiness), or — worse — every existing test file that does `from app import app; client = TestClient(app, raise_server_exceptions=False)` at module scope (confirmed convention: `data-service/tests/test_connectors.py:20-29`) could unexpectedly start a real background thread against live Neo4j the moment `app.py` is imported, if the gating logic is wrong.
**Why it happens:** FastAPI/Starlette's `TestClient` lifespan-triggering behavior is version-sensitive and easy to get wrong when adding the *first* lifespan hook to a codebase that never had one.
**How to avoid:** verify the installed `fastapi`/`starlette` version (flagged unverified above) and explicitly test that (a) unrelated existing test files that already do `from app import app` are unaffected, and (b) the watcher's own tests can deterministically control thread start/stop without depending on `TestClient`'s lifespan-triggering quirks — i.e., prefer calling `dsav_watcher.start_watcher()`/`stop_watcher()` directly in the watcher's own tests rather than relying on `TestClient` context-manager entry/exit.
**Warning signs:** existing, previously-passing test files start failing or hanging after this phase's changes land, with no code change to those files.

### Pitfall 4: Claim/complete race is only a non-issue because polling is single-threaded and single-instance
**What goes wrong:** a naive design might assume a separate "claimed"/"processing" transitional status is required to prevent two concurrent pollers from double-processing the same captured row.
**Why it happens:** it *would* matter under multi-worker uvicorn or a multi-instance deployment — but this phase's shipped configuration is `uvicorn app:app --host 0.0.0.0 --port 8000` (confirmed: `data-service/Dockerfile` CMD line, no `--workers` flag → single worker process) plus D-15's own "single-instance data-service means there is no multi-worker case to justify shared state yet."
**How to avoid:** a sequential `while not stop_event.is_set(): poll_once(); stop_event.wait(interval)` loop never has two concurrent claimers, so a transitional `status:'processing'` state is optional hardening (worth naming in the ADR as follow-up scope for a future multi-worker deployment) rather than a requirement for this spike. The attempt counter (D-08) is still required regardless — that's about retry bookkeeping, not concurrency.
**Warning signs:** planner over-engineers a distributed-locking mechanism for a guarantee the deployment topology doesn't need yet.

### Pitfall 5: Debounce coalesce query must not touch already-completed or already-superseded rows
**What goes wrong:** an unscoped "mark all but the newest per project as superseded" query could accidentally supersede a row that a concurrent (sequential-but-in-flight) poll cycle already flipped to `'completed'` or `'processing'`, corrupting run history.
**Why it happens:** easy to forget the `status:'captured'` filter when writing the `ORDER BY ... LIMIT`-style coalesce query.
**How to avoid:** scope the coalesce `MATCH` strictly to `status:'captured'` (see the proposed shape in §Code Examples below) so only rows that haven't started processing yet are eligible to be marked superseded.
**Warning signs:** a completed run's `ValidStatus`/`shaclReportJson` disappearing or a run silently vanishing from `/validation/runs/{project}`.

## Code Examples

### Capture/claim/complete Cypher shapes (§3 — SYNTHESIZED PROPOSALS, not existing code)

The four constants below are **researcher-proposed shapes for the planner to adopt or refine**, built strictly on the confirmed `MERGE`/`SET` parameterization conventions (`_persist_shacl_report`, `store_validation_run`) and the confirmed row-shape decisions (D-01, D-07, D-08, D-10, D-14). They are tagged `[ASSUMED]` as a design proposal, not `[VERIFIED]`, because no existing code in this repo implements a capture/claim/coalesce/complete state machine — this phase is the first to need one.

```python
# [ASSUMED — proposed, not existing code] Capture: POST /designstate/capture writes this.
# run_id minted the same way publish_validation already does (app.py:1850, uuid.uuid4().hex).
CAPTURE_QUERY = """
MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET
    run.statePayloadJson = $statePayloadJson,
    run.status = 'captured',
    run.capturedAt = $capturedAt,
    run.attempts = 0
"""

# [ASSUMED — proposed] Debounce coalesce (D-14): scoped strictly to status:'captured'
# so completed/processing/failed rows are never touched (Pitfall 5).
COALESCE_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, status:'captured'})
WITH run ORDER BY run.capturedAt DESC
WITH collect(run) AS runs
UNWIND runs[1..] AS stale
SET stale.status = 'superseded'
RETURN runs[0].runId AS keptRunId
"""

# [ASSUMED — proposed] Completion (D-07/D-10): SET-in-place, no new function needed
# alongside store_validation_run.
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

# [ASSUMED — proposed] Bounded backoff on SHACL sidecar failure (D-08): row stays
# 'captured' (re-picked next poll tick) until $maxAttempts is reached, then 'failed'.
FAIL_QUERY = """
MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET
    run.attempts = run.attempts + 1,
    run.status = CASE WHEN run.attempts + 1 >= $maxAttempts THEN 'failed' ELSE 'captured' END,
    run.lastError = $reason
"""
```

### Existing `ValidationPublishRequest` shape the capture payload should echo

```python
# Source: data-service/app.py:215-227 (ValidationPublishRequest) — the fields
# a POST /designstate/capture payload should mirror a subset of (statePayloadJson
# at minimum; validStatus is meaningless pre-verdict so the capture payload
# likely omits it).
class ValidationPublishRequest(BaseModel):
    project: str
    statePayloadJson: str | None = None
    validStatus: list[bool] | None = None
    rules: list[ValidationPublishRulePayload] = Field(default_factory=list)
    ruleResults: list[ValidationPublishRuleResultPayload] = Field(default_factory=list)
    entities: list[ValidationPublishEntityPayload] = Field(default_factory=list)
```

### TestClient pattern for the new capture endpoint's tests

```python
# Source: data-service/tests/test_connectors.py:20-29 (existing convention)
from fastapi.testclient import TestClient
from app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `@app.on_event("startup")`/`("shutdown")` | `lifespan` async context manager | FastAPI 0.93+ [CITED: fastapi.tiangolo.com/advanced/events/] | This phase is the first to add any startup hook to `data-service/app.py` — use the modern pattern, not the deprecated one |

**Deprecated/outdated:** none specific to this repo's existing code (no prior background-thread or startup-hook code exists to be "outdated" relative to).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | Installed `fastapi` version (unpinned in `requirements.txt`) supports the `lifespan` parameter | Standard Stack, Pattern 3 | Low — `lifespan` has existed since FastAPI 0.93 (mid-2023); planner should run `docker compose exec data-service pip show fastapi` once to confirm before committing the plan to it |
| A2 | The four Cypher query shapes in §Code Examples (`CAPTURE_QUERY`, `COALESCE_QUERY`, `COMPLETE_QUERY`, `FAIL_QUERY`) are syntactically and semantically correct against the live Neo4j 5.26 instance | Code Examples | Medium — these are researcher-synthesized proposals following the codebase's confirmed `MERGE`/`SET` conventions but were never executed against live Neo4j in this research session; the plan must include a task that runs them against live Docker and adjusts as needed |
| A3 | A sequential single-thread poll loop makes a transitional `status:'processing'` claim state unnecessary for this phase's single-instance deployment | Pitfall 4 | Low-Medium — correct under the confirmed single-worker `uvicorn` CMD and D-15's own single-instance reasoning, but if the planner instead chooses a thread-pool or multiple concurrent poll workers, this assumption breaks and a claim state becomes required |
| A4 | `authenticate_token()` (not `record_heartbeat()`) is the correct primitive for capture-endpoint auth | Pattern 4, §5 | Low — this is a design recommendation grounded in reading both functions' actual behavior (`connectors.py:212-241`), not an unverified guess; risk is limited to the planner independently re-deriving the same conclusion (no downside) or the planner choosing a different mechanism entirely (their prerogative — this stays "open for planner" per CONTEXT.md) |

## Open Questions

1. **Should the poll interval and `DG_SHACL_HTTP_TIMEOUT_SECONDS` (currently 15s default) be reconciled the way `DG_SHACL_HTTP_TIMEOUT_SECONDS` and `DG_REASONER_TIMEOUT_SECONDS` already had to be (Phase 823 D-823-07, timeout-budget mismatch bug)?**
   - What we know: `_call_shacl_validate` already has a documented timeout-budget precedent bug class (`DG_OBSIDIAN/knowledge/decisions/Phase 823 SHACL validation layer design decisions.md` D-823-07) where a too-short outer timeout produced false timeouts on slow-but-successful validations.
   - What's unclear: whether the watcher's poll interval needs to be longer than `DG_SHACL_HTTP_TIMEOUT_SECONDS` to avoid a slow SHACL call overlapping the next poll tick (relevant to Pitfall 4's single-threaded-loop reasoning — if the loop blocks on `_call_shacl_validate` during `poll_once`, this is naturally serialized, but the plan should say so explicitly).
   - Recommendation: plan should state the poll loop is fully synchronous/blocking per tick (no concurrent SHACL calls in flight), making this a non-issue by construction — confirm this explicitly in the plan rather than leaving it implicit.

2. **Where exactly should `require_connector_token()`-style auth logic live if extracted into a reusable dependency?**
   - What we know: only one existing caller (`connector_heartbeat`) inlines the Bearer-header pattern; no FastAPI `Depends()` wrapper exists anywhere in `data-service` today (confirmed by reading `app.py`'s connector-related routes in full).
   - What's unclear: whether extracting a dependency is worth the abstraction for a single additional call site (the new capture endpoint), or whether inlining matches the codebase's existing minimal-abstraction style better.
   - Recommendation: leave to the planner/threat-model discussion; either choice is internally consistent with the codebase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose stack (neo4j, data-service, dg-reasoner, speckle-*) | Live-Docker E2E for SC1/SC2, D-11's single publish leg | Not verified running in this research session — [ASSUMED] available per project convention (`docker compose up -d`) | — | None — SC1/SC2 explicitly require live Docker per the phase's own success criteria; no fallback is acceptable |
| `fastapi` (unpinned version) | `lifespan` context manager | Installed per `requirements.txt`, exact version unverified | unpinned | Confirm via `docker compose exec data-service pip show fastapi` (A1 in Assumptions Log) |
| `git` inside the `data-service` container | Not required by this phase (that's a Phase 35-13 recognition-eval dependency) | N/A | — | — |

**Missing dependencies with no fallback:** none identified beyond the standing requirement that live Docker must be up for SC1/SC2 evidence — this is a phase requirement, not a gap.

**Missing dependencies with fallback:** `fastapi` version — confirm before finalizing the `lifespan` vs. any alternative decision (low risk, see A1).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already the sole framework across `data-service/tests/`, 29 existing test files) |
| Config file | `data-service/tests/conftest.py` (registers `eval`/`live`/`integration` markers; `not live` is the default marker expression — no config file like `pytest.ini` exists, markers/options are registered programmatically) |
| Quick run command | `python -m pytest data-service/tests/ -q` (host tier — 492 passed / 4 pre-existing Neo4j-dependent failures measured 2026-07-27 per `data-service/tests/README.md`) |
| Full suite command | `docker compose exec data-service python -m pytest tests/ -q` (integration tier — requires rebuild if new files were added since the last image build, per the documented gotcha) |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DSAV-02 | `poll_once()` correctly claims/coalesces/completes a captured row given a `FixtureSession` | unit | `python -m pytest data-service/tests/test_dsav_watcher.py -q` | ❌ Wave 0 |
| DSAV-02 | `POST /designstate/capture` returns 401 for missing/invalid/revoked token, 200 for a valid project-scoped token | unit (TestClient, no live Neo4j needed for the 401 branch; 200 branch needs a live/fixture write) | `python -m pytest data-service/tests/test_designstate_capture.py -q` | ❌ Wave 0 |
| DSAV-02 (SC1) | Capture -> Run appears in ValidGraph -> optional Speckle publish, hands-off, on live Docker | integration/E2E | `docker compose exec data-service python -m pytest tests/test_dsav_watcher.py -k live_loop -q` (or a dedicated live-Docker script — plan decides exact shape) | ❌ Wave 0 |
| DSAV-01/DSAV-02 (SC2) | Rapid successive captures produce one run (debounce collapse ratio) and a bounded runs-per-minute figure under burst | integration/E2E, must emit a measured evidence artifact (see below) | same live-Docker driver as SC1, parameterized with a burst of N captures | ❌ Wave 0 |
| D-11 | The one publish-enabled demo run reaches Speckle | manual/live, requires a configured Speckle write token in the dev stack | one manual `docker compose exec` invocation or a dedicated marked test, run once | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest data-service/tests/ -q` (host tier — fast, no live dependencies for pure logic)
- **Per wave merge:** `docker compose exec data-service python -m pytest tests/ -q` (integration tier — after rebuilding the image if new test/watcher files were added, per the documented image-staleness gotcha)
- **Phase gate:** full suite green (both tiers) before `/gsd-verify-work 39`, plus the live-Docker SC1/SC2 evidence run (see below) — this is not optional for this phase since SC1 and SC2 explicitly require live-Docker demonstration, not description

### Wave 0 Gaps

- [ ] `data-service/tests/test_dsav_watcher.py` — covers the pure `poll_once()` function, debounce coalesce logic, and the four Cypher constants' parameter binding (string-shape assertions at minimum; live-Docker execution assertions separately marked)
- [ ] `data-service/tests/test_designstate_capture.py` — covers `POST /designstate/capture` auth paths and payload validation
- [ ] A live-Docker evidence-capture mechanism for SC1/SC2 — this is not a standard pytest fixture gap but a **methodology gap**: the plan needs an explicit task that (a) issues a burst of real `POST /designstate/capture` calls against the running container, (b) reads back `capturedAt`/`completedAt`/`status` timestamps from Neo4j after the fact, and (c) persists the resulting latency/collapse-ratio/runs-per-minute numbers into the DSAV-01 investigation note as measured evidence, not narrated prose (per the phase's explicit instruction that SC1/SC2 require evidence artifacts). No existing test in this repo does this pattern today — it is new methodology, not a reused convention.

### Measurement Methodology (DSAV-01 / SC2 specifics — research_focus item 4)

Three numbers are required as **evidence**, not assertions:

1. **Capture -> run latency:** `run.capturedAt` (set by the capture endpoint at write time, same `datetime.now(timezone.utc).isoformat()` convention already used at `app.py:465`) vs. `run.completedAt` (set by the `COMPLETE_QUERY` proposal above). Read both back from Neo4j after the fact — do not trust in-process wall-clock timers, since the authoritative numbers are the ones stored on the row itself (auditable, matches D-14's "auditable trail" framing for superseded rows).
2. **Debounce collapse ratio ("N captures in, 1 run out", D-14):** drive N rapid `POST /designstate/capture` calls for one project within the debounce window (a tight pytest loop with no sleep between calls), then, after waiting longer than the debounce window plus one poll interval, query Neo4j for `status IN ['completed','failed']` rows for that project created in the burst window — the ratio N:count-of-non-superseded-rows is the collapse ratio. Superseded rows remain queryable (D-14, marked not deleted) so the "skipped work" trail is itself part of the evidence.
3. **Runs-per-minute under a rapid-capture burst:** sustain a burst of captures across a fixed wall-clock window (e.g., 60s) and count `status:'completed', trigger:'auto'` rows created in that window — this demonstrates the rate-limit guardrail actually caps throughput rather than merely being configured to.

All three numbers should be captured into a small, reproducible artifact (a short table or a raw JSON/CSV dump referenced by the DSAV-01 note) generated by a pytest test or script run against live Docker — not typed by hand into the note after eyeballing logs.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | yes | Reuse (or extend) the Phase 825 project-scoped connector token (`connectors.authenticate_token`) for `POST /designstate/capture` — candidate, not locked (D-A "open for planner") |
| V3 Session Management | no | Stateless bearer-token check per request; no session/cookie state introduced |
| V4 Access Control | yes | Per-project scoping already built into the connector-token record (`record["project"]`); the capture endpoint must reject/route a request whose token project does not match the requested capture's project — this is a concrete plan requirement, not automatic |
| V5 Input Validation | yes | `statePayloadJson` is user-supplied at the capture endpoint; existing Pydantic models (`ValidationPublishRequest`) already validate the request envelope shape — the new capture payload model should follow the same pattern, and the JSON string itself is parsed defensively downstream (`dg-reasoner/valid_graph_export.py`'s `RUN_QUERY` already reads `statePayloadJson` leniently by design) |
| V6 Cryptography | yes (reused, not new) | Token hashing already uses SHA-256 (`connectors.hash_token`, `connectors.py:146-148`) — no new crypto to write for this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Unauthenticated write-amplifier: anonymous POST enqueues a validation run and (if publish enabled) a Speckle version | Denial of Service / Elevation of Privilege | Authenticate the capture endpoint (V2/V4 above) — this is the CONTEXT.md-flagged highest-severity item; the plan's `<threat_model>` block is mandatory |
| Rate-limit bypass via data-service restart resetting in-memory guardrail state (D-15) | Denial of Service | Documented, accepted limitation for this spike — recorded explicitly in the ADR as follow-up hardening (D-15), not silently left unaddressed |
| Cross-project capture (a token scoped to project A enqueues a capture for project B) | Elevation of Privilege / Tampering | The capture endpoint must validate the authenticated token's bound `project` against the request's `project` field and reject a mismatch — no existing code does this today because no prior endpoint accepted a caller-supplied `project` alongside a connector token in this way; this is new logic the plan must add, not a reuse |
| Publish-flood (every capture becomes a Speckle version) | Denial of Service (against the Speckle service) | Structurally prevented by D-09 (persist-only by default, publish opt-in per project) — not a runtime guard, an architectural default |

## Sources

### Primary (HIGH confidence — direct code read, this session)

- `data-service/app.py` (full read of imports, driver setup, `store_validation_run`, `publish_validation`, `_call_shacl_validate`, `_persist_shacl_report`, `get_integration_config`/`upsert_integration_config`, `create_connector_credential`/`connector_heartbeat`, `ValidationPublishRequest`) — lines cited throughout this document
- `data-service/connectors.py` (full read of token generation/hashing/authentication/heartbeat functions, lines 60-260)
- `data-service/dg_context.py` + `data-service/tests/test_dg_context.py` (injectable-session pattern and `FixtureSession` precedent)
- `dg-reasoner/reasoning.py` (lazy driver pattern, `_get_driver`) and `dg-reasoner/valid_graph_export.py` (confirms D-05's "zero new export work" claim by reading `RUN_QUERY`'s `statePayloadJson`-only dependency)
- `data-service/Dockerfile` and `docker-compose.yml` (confirms `uvicorn app:app --host 0.0.0.0 --port 8000`, no `--workers` flag — single-worker assumption)
- `data-service/requirements.txt` (confirms no new package is needed)
- `data-service/tests/README.md` (two-tier test convention, measured pass counts, image-staleness gotcha)
- `data-service/tests/conftest.py` (marker registration: `eval`, `live`, `integration`)
- `data-service/tests/test_connectors.py` (`TestClient` usage convention)
- `DG_OBSIDIAN/knowledge/decisions/Phase 823 SHACL validation layer design decisions.md`, `.../DesignState persists to ValidGraph not Metagraph.md`, `.../Phase 37 structure validation....md` (ADR structure/front-matter conventions — three coexisting formats observed)
- `DG_OBSIDIAN/00-home/index.md` (§ Decisions — confirms every phase decision file is linked from the index)

### Secondary (MEDIUM confidence — WebSearch, official docs)

- [Run your own transactions — Neo4j Python Driver Manual](https://neo4j.com/docs/python-manual/current/transactions/) [CITED] — driver is thread-shareable, sessions must not span threads
- [Lifespan Events — FastAPI](https://fastapi.tiangolo.com/advanced/events/) [CITED] — `lifespan` is the current recommended pattern
- [Events are deprecated, But docs encourage to write them — fastapi/fastapi Discussion #12027](https://github.com/fastapi/fastapi/discussions/12027) [CITED] — confirms `on_event` deprecation status since FastAPI 0.93+

### Tertiary (LOW confidence)

- None — every claim in this document is either grounded in a direct file read this session or an official-docs citation; the four Cypher shapes in §Code Examples are explicitly flagged `[ASSUMED — proposed]` rather than presented as verified fact.

## Metadata

**Confidence breakdown:**
- Existing-code claims (driver setup, function signatures, MERGE/SET templates, test conventions, connector-token auth): HIGH — every claim was verified by direct `Read`/`Grep` of the cited file and line range in this session.
- Proposed Cypher shapes (capture/claim/coalesce/complete/fail): MEDIUM — grounded in confirmed conventions but not executed against live Neo4j in this research session; flagged `[ASSUMED]` throughout.
- `fastapi` version / `lifespan` support: MEDIUM — reasoned from FastAPI's public deprecation timeline, not verified against the actual installed version in this container image.
- Measurement methodology: HIGH — directly derived from existing, measured test-tier conventions already documented in this repo (`data-service/tests/README.md`).
- ADR structure: HIGH — read three real examples from the target directory; multiple valid conventions coexist, presented as options rather than a single mandate.

**Research date:** 2026-07-27
**Valid until:** 30 days (stable domain — no fast-moving external dependency; the one time-sensitive fact, `fastapi`'s unpinned version, should be reverified if this research is reused after a `requirements.txt` change)
