# Phase 39 — DesignState Auto-Validation: Trigger-Architecture Investigation Note

**Requirement:** DSAV-01
**Written:** 2026-07-27
**Evidence artifact:** [`39-EVIDENCE.json`](39-EVIDENCE.json) — `measured_at` **2026-07-27T19:48:07.152293+00:00** (Speckle leg merged in at `measurements.speckle_publish.measured_at` **2026-07-27T20:04:58.896285+00:00**)
**Companion ADR:** `DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md`

---

## The question, and the answer

**Question (ROADMAP Phase 39):** can validation run automatically when a DesignState is captured, and if so, which of three trigger architectures should carry it — (a) a capture-time hook in the GH DESIGN STATE / VALIDATOR components, (b) a data-service watcher on DesignState writes, or (c) an event-driven trigger on Neo4j ValidGraph writes?

**Answer:** **path (b), a data-service in-process watcher.** It closed the loop hands-off on live Docker in a measured **2.679 s**, collapsed **8** rapid captures into **1** run, and held throughput at exactly its configured limit under a sustained burst. Paths (a) and (c) are not merely less attractive — each is foreclosed by a *specific, recorded* blocker in this repository's current environment, not by a trade-off judgement.

**But the choice was not really between the three architectures.** Two blocking findings, both discovered *during* this investigation rather than assumed going in, determined the shape of the prototype before any architecture comparison mattered:

1. **There is no `:DesignState` write to observe.** The roadmap deliverable says "a data-service watcher **on DesignState writes**". No such write exists. First-class `:DesignState` nodes do not exist in the live graph — Phase 29 recorded materializing them as FLAGGED BACKLOG needing explicit human sign-off and its own phase. A DesignState reaches Neo4j only as `statePayloadJson` on a `:ValidationRun`, written by `store_validation_run()` and only via `/validation/publish` — which is *already a completed validation run*. A watcher on "DesignState writes" as literally worded has nothing to watch. The capture event had to be invented (D-01: a `:ValidationRun` row with `status:'captured'`).
2. **data-service cannot evaluate SWRL rules at all.** Rule evaluation is C# (`RuleEvaluator` in DG.Core, driven by the VALIDATOR component); `/validation/publish` only *receives* already-computed `failedRuleIds`. The only server-side judge that exists is SHACL, via the dg-reasoner sidecar. So the auto-run's verdict source was not a choice either (D-05).

Everything below follows from those two facts. The second one is also the phase's **headline finding** — see [Coverage gap](#headline-finding-the-shaclswrl-coverage-gap).

---

## What was measured, and against what

| Property | Value (from `39-EVIDENCE.json`) |
|---|---|
| Fixture project | **`p39-autoval`** — a synthetic phase-reserved project string, isolated from `p37-structure`, `p1` and `default-project` |
| Neo4j | **Neo4j Kernel 5.26.28 (community)** |
| data-service workers | **1** uvicorn worker → exactly one watcher daemon thread; the rate-limit window is that one process's memory (D-15) |
| Poll interval | **2.0 s** |
| Rate-limit window | **60.0 s** |
| Max attempts | **3** |
| Target | `http://localhost:8000` |
| Source modules | `data-service/tests/test_dsav_live_loop.py` (six scenarios), `data-service/tests/test_dsav_publish_leg.py` (the single publish leg) |

Debounce window and rate limit were varied per scenario and are quoted with each figure below; they are not one global setting.

---

## Comparison of the three trigger architectures

Path (b) is **measured** — every cell is a figure read off `39-EVIDENCE.json`. Paths (a) and (c) are **analytic** per D-04, and every analytic cell ends with a bracketed provenance marker naming either the measured path-(b) figure it is derived from or the specific empirical blocker it rests on. A cell with no marker would be a defect.

| | **(a) GH capture-time hook** *(analytic)* | **(b) data-service watcher** *(measured)* | **(c) Neo4j write-event trigger** *(analytic)* |
|---|---|---|---|
| **Latency** (capture → completed run) | Sub-second floor: no poll interval and no debounce wait, so the floor is the SHACL round-trip plus the completion write alone. Upper-bounded at **0.679 s** by artifact arithmetic. `[anchor: measured SC1 2.679 s − the 2.0 s debounce window = 0.679 s, which must contain both the ≤2.0 s poll phase offset and the SHACL round-trip]` | **2.679 s**, read off the row: `capturedAt` 19:44:51.686809Z → `completedAt` 19:44:54.365992Z, with debounce **2.0 s** and poll interval **2.0 s**. The artifact's own interpretation: latency is bounded below by the debounce window plus a capture-to-next-tick phase offset of up to one poll interval, plus the dg-reasoner round-trip. **Latency is dominated by the debounce window by design, not by processing cost.** | Path (b)'s latency plus one outbox round-trip: the trigger writes an outbox node, an external worker reads it, then calls back over HTTP. **≥ 2.679 s + one Neo4j write + one poll-or-read hop.** `[anchor: measured SC1 2.679 s; blocker: the reliable APOC-trigger pattern for external side effects is trigger → outbox node → external worker → HTTP (Perplexity research, 39-CONTEXT.md § Environment constraints), which structurally collapses into path (b) with an extra hop]` |
| **Publish-flood behaviour** | Would need a **client-side** debounce implemented per GH client. The trailing-edge collapse path (b) gets for free from a single newest-wins query becomes per-client state that no server can arbitrate. `[anchor: measured collapse 8 captures → 1 run, 7 superseded, achieved by one server-side newest-wins query over rows for one project]` | **Measured 8:1 collapse** — **8** captures inside the window (burst span **0.124 s**) produced **1** non-superseded run and **7** rows marked `status:'superseded'`, still queryable. Under sustained load the **rate limiter**, not the debounce window, is what caps throughput (F-39-02): **20** captures over a 60.0 s window produced exactly **3** completed runs against a configured limit of **3**. | Same collapse *is* achievable, but only by putting the debounce in the external worker — i.e. by rebuilding path (b) behind the trigger. The trigger itself fires per write and cannot coalesce. `[anchor: measured 8:1 collapse is a property of the watcher's newest-wins query, not of the write event; blocker: outbox pattern means the worker is path (b)]` |
| **Speckle noise** | Identical to (b) once the flag is on — the publish leg is server-side either way — but a GH-side trigger has *no* server-side rate limiter in front of it unless one is added, so the measured 1-version-per-surviving-capture rate would apply to a larger surviving population. `[anchor: measured 1 Speckle version per capture that survives debounce and the rate limiter; anchor: measured 3 runs/min cap is enforced in the watcher process, which path (a) bypasses]` | **Measured, not estimated.** With `publishEnabled` on for the single deliberate run (D-11), **1 capture → 1 Speckle version**: version **`2ab708e884`** in Speckle project `44088eefc6`, model `a6d1e0c5da`. Persist-only by default, so **0** versions unless a project explicitly opts in (D-09). **The version's emptiness is the finding** — see below. | Same as (b) once the worker publishes; the trigger adds no Speckle behaviour of its own. `[anchor: measured 1 Speckle version per surviving capture on path (b); blocker: the worker in the outbox pattern is path (b)]` |
| **Dependency footprint** | A network client on the DESIGN STATE component (none exists today — only VALIDATOR carries `ValidationPublishClient`), plus live Rhino at runtime. `[blocker: DESIGN STATE has no network client; 39-CONTEXT.md D-02]` | **Zero new packages phase-wide.** One new module (`data-service/dsav_watcher.py`), one new route, one `threading.Thread` daemon on the existing FastAPI process. No queue, no n8n workflow, no new container. | An APOC install (Dockerfile change: the image currently fetches only the neosemantics jar) plus `apoc.trigger.enabled` in `apoc.conf`, plus an external worker process. `[blocker: APOC is allowlisted in docker-compose.yml (n10s.*,apoc.*) but never installed; blocker: neo4j:5.26 Community has no CDC]` |
| **Testability without Rhino** | **No.** Verifying the loop requires a live Rhino session — the deferred-in-Rhino-UAT pattern this project has already hit in Phase 33 plan 04, Phase 34-02/03 and Phase 824. `[blocker: recorded in-Rhino UAT deferral pattern, 39-CONTEXT.md D-02 / D-A rationale]` | **Yes, and it was.** Six live-Docker scenarios plus the publish leg ran entirely inside the compose network with a simulated client at the trust boundary (D-02). No Rhino was involved at any point; `manual_trigger_used` is recorded as `false`. | Partially — the trigger fires headlessly, but proving it requires installing APOC first, which the phase declined as a detour outside the chosen path. `[blocker: APOC absent; recorded as a declined detour in 39-CONTEXT.md § Deferred]` |
| **Verdict** | **Rejected for now, named as follow-up scope.** The right long-term shape (lowest latency, closest to the user's actual act), but not verifiable in this phase and blocked on a component that cannot make network calls. `[blocker: no network client on DESIGN STATE; blocker: live Rhino required]` | **Chosen.** Measured, hands-off, Rhino-free, zero new dependencies, guardrails demonstrated rather than described. | **Rejected — structurally, not by preference.** Its only viable form is path (b) plus an outbox hop and an extra failure mode. `[blocker: Community edition → no CDC; blocker: APOC allowlisted but not installed; blocker: outbox pattern collapses into path (b)]` |

**The four empirical blockers, named plainly:** `neo4j:5.26` **Community** edition (Neo4j CDC is not a Community feature); **APOC allowlisted but never installed** (`docker-compose.yml` sets the unrestricted/allowlist procedures to `n10s.*,apoc.*`, but the Dockerfile fetches only the neosemantics jar); the **canvas bridge is read-only by design** (`CanvasCommandDispatcher`'s handler dictionary means write commands require a deliberate code change, and driving GH from the server would invert the dependency so that "auto" only works while a canvas is open); and **there is no server-side SWRL evaluator** (rule evaluation is C# in `RuleEvaluator`; data-service only receives already-computed `failedRuleIds`).

---

## Path (b), measured in full

Every figure in this section is transcribed from `39-EVIDENCE.json`.

### Latency (SC1)

| Signal | Value |
|---|---|
| `latency_seconds` | **2.679** |
| `latency_source` | `row.completedAt - row.capturedAt` (P-13 — read off the node, never an in-process stopwatch) |
| `capturedAt` → `completedAt` | 2026-07-27T19:44:51.686809Z → 2026-07-27T19:44:54.365992Z |
| `run_id` | `10a2045c603a4d238aaaec0b47f805b6` |
| Debounce window | **2.0 s** |
| Poll interval | **2.0 s** |
| Rate limit | **30**/min |
| `publish_enabled` | `false` |
| `trigger` / `verdict_source` | `auto` / `shacl` |
| `manual_trigger_used` | **`false`** — SC1's literal claim |

The **2.0 s debounce window is 75 % of the 2.679 s total**. Subtracting it leaves **0.679 s** to contain both the capture-to-next-tick phase offset (anywhere from 0 to one full 2.0 s poll interval) and the dg-reasoner SHACL round-trip plus the completion write. Latency here is a *policy* number, not a *cost* number: it is dominated by how long the system deliberately waits to see whether more captures are coming.

> **Provenance caveat.** `39-03-SUMMARY.md` decomposes this latency as "2.0 s debounce + up to one 2.0 s poll interval + a ~1.5 s dg-reasoner SHACL round-trip", and reports a three-run spread of 3.427 s / 2.801 s / 2.679 s. Neither the ~1.5 s round-trip nor the other two run times appears in `39-EVIDENCE.json`, and the ~1.5 s figure cannot be reconciled with the recorded 2.679 s total (2.0 + 1.5 already exceeds it). This note therefore uses only the artifact's arithmetic. The summary's spread is reported here as context, explicitly marked as *summary-sourced, not artifact-sourced*.

### Publish-flood: the collapse ratio (SC2)

| Signal | Value |
|---|---|
| `captures_in` → `runs_out` | **8 → 1** (`collapse_ratio` `"8:1"`) |
| `superseded` | **7** |
| `superseded_rows_still_queryable` | **`true`** — marked, not deleted (D-14) |
| `burst_span_seconds` | **0.124** |
| `kept_run_id` | `aa7d3dadd5664424be45e78a6558f9aa` |
| `status_counts` | `superseded: 7`, `completed: 1` |
| Debounce / rate limit | **5.0 s** / **3**/min |
| Rate-window drain before the scenario | 59.718 s |

Eight captures inside 0.124 s produced exactly one validated run. The seven skipped captures left an auditable trail rather than vanishing — the whole point of trailing-edge *coalesce* over *drop*.

### Publish-flood: sustained throughput (SC2, and finding F-39-02)

| Signal | Value |
|---|---|
| `measured_runs_per_minute` | **3** |
| `configured_rate_limit_per_minute` | **3** |
| `window_seconds` | **60.0** (19:47:00.893984Z → 19:48:00.893984Z) |
| `captures_issued` | **20** over **5** cycles |
| `capture_schedule` | 4 captures at 1.0 s intervals, then 8.0 s idle, repeated for 60.0 s |
| `status_counts` | `completed: 3`, `superseded: 9`, `captured: 8` |
| `counting_rule` | rows with `status='completed'` and `trigger='auto'` whose row `completedAt` falls in `[window_start, window_end)` |

**Finding F-39-02: the rate limiter, not the debounce window, is what caps sustained throughput.** The limiter binds exactly — 3 measured against 3 configured. Captures arriving while the limiter is saturated are skipped *before* coalesce, so their rows stay `captured` rather than being superseded or dropped: **8** rows were still `captured` at window close. Throughput is capped without data loss, but a saturated project accumulates `captured` rows that existing readers already see.

### The D-08 attempt ladder

Observed with an injected `unavailable` SHACL sidecar, `max_attempts` **3**, the live daemon parked on a 3600 s debounce so it could not race the ladder:

| Tick | `attempts` | `status` | `lastError` | Runs failed this tick |
|---|---|---|---|---|
| 1 | 1 | `captured` | `unavailable` | 0 |
| 2 | 2 | `captured` | `unavailable` | 0 |
| 3 | 3 | **`failed`** | `unavailable` | 1 |

Terminal state `failed`, `completed_at` **`null`**, `verdict_source` **`null`**. An auto-run whose verdict could not be obtained never claims to have one.

### Speckle noise — measured, once, deliberately

| Signal | Value |
|---|---|
| `status` | **`published`** — not blocked, not estimated |
| `versions_minted` / `captures_issued` | **1 / 1** → `speckle_versions_per_capture` **1.0** |
| Version | **`2ab708e884`** in Speckle project `44088eefc6`, model `a6d1e0c5da` (base model `4c546c0771`, base version `9ff670f197`) |
| Run | `0afe92c2e2324a85a988d42c4ffedc95`, `trigger: auto`, `verdictSource: shacl`, `send_status: true` |
| `capturedAt` → `completedAt` | 20:04:53.204018Z → 20:04:57.502692Z (**4.299 s**, derived from the two recorded timestamps) |
| `valid_status` / `obj_state_count` | `[false, false]` / **2** |
| `validation_entity_count` | **0** |
| `verdict_state_before_publish` | `status: completed`, `sendStatus: false`, `validationVersionId: null` — the P-07 inverted ordering, **observed** |

**The emptiness is the Speckle-noise characteristic.** A captured DesignState envelope carries no per-entity geometry and no `failedRuleIds`, so the published version is a *state-level marker* rather than a coloured overlay — the artifact records `validation_entity_count: 0`. With the flag on, the observed auto-run Speckle-noise rate is **one near-empty commit appended to the project's `dg-validation` model per capture that survives debounce and the rate limiter**. Multiply that by the measured guardrail behaviour and the shape is clear: 8 captures in a 0.124 s burst would append 1 version, not 8; 20 captures in a minute would append 3, not 20.

The Speckle configuration used was **discovered from the dev stack** (from DG project `nonexistent-project-xyz`, an unfortunately-named leftover) and re-pointed at `p39-autoval`, which is a synthetic phase-reserved string with no Speckle project of its own. Recorded in the artifact as `speckle_config_source`.

> ### Caveat a reader must not miss: the published Neo4j row no longer exists
>
> `measurements.speckle_publish.row_lifecycle` records that `run_row_present_at_measurement` is `true` but `run_row_present_now` is **`false`**. The row was destroyed by `data-service/tests/test_dsav_live_loop.py::live_session`, whose `_scrub` deletes every `:ValidationRun` and `:IntegrationConfig` scoped to `p39-autoval` at both setup and teardown. That module was `integration`-marked but not yet `live`-marked, so a bare in-container `pytest tests/ -q` collected it — and that bare run was executed roughly four minutes after the publish leg, as an acceptance check, destroying the published run row as a side effect.
>
> Immediately after the leg: `send_status_true_rows: 1`. Now: `send_status_true_rows: 0`, `validation_run_rows_for_project: 0`.
>
> **The row was deliberately not recreated and the leg was deliberately not re-run.** D-11 permits exactly one publish-enabled run in the phase, and re-running would mint a second Speckle version. The deletion is *reported rather than repaired*.
>
> **The Speckle-side proof is durable and independent**, which is why this is an annoyance and not lost evidence: version `2ab708e884` carries the message `DG validation run 0afe92c2e2324a85a988d42c4ffedc95` and `created_at` 2026-07-27T20:04:58.470Z — **0.97 s after** the row's `completedAt` of 20:04:57.503Z — and a human operator opened the viewer and confirmed it. The `live` marker has since been added to the offending module so a routine suite run can no longer scrub phase evidence.

### Cypher shapes discharged

All **8** watcher Cypher constants (`CAPTURE_QUERY`, `COALESCE_QUERY`, `COMPLETE_QUERY`, `CONFIG_READ_QUERY`, `CONFIG_UPSERT_QUERY`, `ENABLED_PROJECTS_QUERY`, `FAIL_QUERY`, `NEWEST_CAPTURED_QUERY`) executed against live **Neo4j Kernel 5.26.28 (community)** without a Cypher error and produced the expected row shapes — discharging 39-RESEARCH.md assumption A2. The load-bearing case, `COALESCE_QUERY` returning its `keptRunId` when exactly one captured row exists, returned `supersededCount: 0` with `statePayloadJson_returned: true`.

---

## Headline finding: the SHACL/SWRL coverage gap

**A SHACL-verdicted auto-run answers "is this captured state well-formed?" — not "does this design comply?"**

The shapes in `ontology/dg-shapes.ttl` target *state well-formedness*: `DsKindLabelShape`, `PropStateCompletenessShape`, `ObjStateObjectRefShape`, `RunStatusShape`. None of them expresses a design-compliance constraint such as "maximum building height is 75 metres". That is not an oversight — it is the recorded Phase 823 decision D-823-04 ("data-integrity shapes only, no business rules"), and `spec/RULE-PARTITION-POLICY.md` is normative on which validation system owns which rule category. Re-deciding the SWRL/SHACL partition line inside an investigation phase was deliberately out of bounds.

**So the prototype proves the mechanism end to end. It does not close the compliance loop.** Capture → debounce → coalesce → verdict → persist → (optionally) publish all work, measurably. What arrives at the end is a well-formedness verdict wearing a validation run's clothes.

### And the verdict is currently not even discriminating — finding F-39-01

This is the single most important thing in this note, and it is an **open, unresolved design question**. Phase 39 measured it; Phase 39 deliberately did not fix it.

`poll_once` calls the SHACL sidecar and **only then** writes `ValidStatus` via `COMPLETE_QUERY`. At validation time the run node therefore has *no* `ValidStatus` — which trips the shapes graph's own Run shape. Measured:

| Signal | Value |
|---|---|
| `shacl_conforms` | **`false`** |
| `shacl_shape_ids` | **`["RunStatusShape_valid"]`** |
| `shacl_counts` | violation **1**, warning 0, info 0 |
| `valid_status` | **`[false, false]`** for an `obj_state_count` of **2** |

That finding's `focusLabel` is the **`runId`**, which matches no objState, so P-02's conservative unmapped fallback flips **every** ObjState entry to `false`.

**Consequence: auto-runs report a uniformly all-false `ValidStatus` regardless of the design's actual conformance.** The verdict is *structurally sound* — it never claims a passing state it cannot attribute — but it is **not yet discriminating**. The same `[false, false]` appears in the Speckle publish leg's run, four hours' worth of scenarios apart, on a different run id.

**Do not read the phase's success criteria as saying auto-validation currently produces meaningful pass/fail verdicts. It does not yet.** The mechanism is proven; the judgement it delivers is, at present, a constant.

Whether to fix this by ordering the ValidGraph export (write `ValidStatus` before validating) or by scoping the shapes graph (exclude the Run shape from an auto-run's own validation) is an open design question the DSAV-03 ADR presents rather than resolves. Both options have consequences the investigation did not have the budget to explore.

---

## Guardrails as built and measured

DSAV-03 names three guardrails. All three were **demonstrated in the prototype rather than described** (D-B), and each has a measured number behind it.

| Guardrail | Design | Measured behaviour |
|---|---|---|
| **Debounce window** — trailing-edge coalesce, newest wins (D-14) | Within the window, only the newest `captured` row per project is validated; the rest are marked `status:'superseded'`, **not deleted**, so the skipped-work trail stays auditable | **8 captures in → 1 run out, 7 superseded**, burst span 0.124 s, debounce 5.0 s. `superseded_rows_still_queryable: true` |
| **Per-project rate limit** (D-15) | An in-memory 60.0 s sliding window per project in the watcher process | **3 runs/min measured against 3 configured**, from 20 captures across 5 cycles. Captures arriving while saturated are skipped *before* coalesce and stay `captured` — throughput capped without data loss (F-39-02) |
| **Per-project opt-in flag** (D-13) | An `IntegrationConfig` row with `provider:'AutoValidation'`; **absent row = disabled**, which is the default. No implicit-create | A project with no `provider:'AutoValidation'` row is **invisible to the watcher** — `ENABLED_PROJECTS_QUERY` filters `enabled = true` at the Cypher level, so an unconfigured project is never even enumerated. At phase teardown, `auto_validation_config_rows_remaining: 0` |

A fourth guardrail — the D-08 bounded attempt counter — was also built and measured (the ladder above). It is not one of DSAV-03's three, but it is what keeps a failing sidecar from producing an infinite retry loop.

---

## Consequences if this ships as-is

These are not risks to be mitigated later; they are properties of the design as measured, and a reader of the run list will meet them immediately.

1. **Run-list pollution is broader than auto-runs alone.** `list_validation_runs` has **no status filter** and orders by `createdAt` — verified during planning. So `captured`, `superseded` and `failed` rows all surface in `GET /validation/runs/{project}`, and therefore in the VALIDATION GRAPH component and the ui-v2 Model screen. Measured: `GET /validation/runs/p39-autoval` returned **HTTP 200** with **5** runs — 2 `superseded`, 1 `completed`, 1 `captured`, 1 `failed` — every one carrying a `runId`, and every non-completed row carrying **null** Speckle identifiers. D-12 accepted visibility for *completed* auto-runs; this is wider than that.
2. **A `shacl` verdict is indistinguishable from a SWRL verdict without inspecting the property.** `verdictSource:'shacl'` is stamped on every auto-run precisely so the difference is *recoverable* — but no existing reader inspects it. Combined with F-39-01, an unmodified UI would display an all-false well-formedness verdict as though it were a design-compliance result.
3. **The in-memory guardrail window resets on a data-service restart.** The debounce timer state and the per-project rate-limit window live in the watcher process's memory (D-15), keyed by project. A restart briefly reopens the rate-limit floodgate. This was an explicit, recorded acceptance rather than an oversight — there is no multi-worker case yet to justify shared state (`data_service_workers: 1`), and writing guardrail counters back to the very database the watcher polls would amplify writes.
4. **The single-worker assumption is load-bearing.** One uvicorn worker, no `--workers` flag, therefore exactly one watcher daemon thread. A transitional claim state on the row is unnecessary today and would become necessary under a multi-worker or multi-instance deployment.
5. **There is no retention cap on auto-runs.** A project with auto-validation enabled accumulates rows indefinitely — including the `captured` rows that a saturated rate limiter leaves behind (8 of them in the measured burst alone). Pruning is a destructive write and needs its own decision.
6. **There is no configuration route.** Enabling auto-validation for a project means calling `dsav_watcher.upsert_auto_validation_config()` out of band. That was deliberate — the capture endpoint is the phase's only new public surface — but it means the feature is currently operator-only.

---

## Provenance

Every numeral in this note was transcribed from `39-EVIDENCE.json` at write time. None was retyped from memory, from a terminal scrollback, or from a prior summary — the two places where a summary figure is quoted for context (the ~1.5 s SHACL round-trip and the three-run latency spread) are explicitly marked as summary-sourced and *not* used in any comparison cell. Two figures are stated as derived arithmetic over artifact values and are labelled as such: the 0.679 s residual (2.679 − 2.0) and the 4.299 s publish-leg capture-to-complete interval (two recorded timestamps).

The artifact's `missing_measurements` list is **empty** — every scenario the plan specified was measured. Where the phase declined to measure something (empirically verifying path (c)'s blocker by installing APOC), that is recorded as a declined detour in `39-CONTEXT.md § Deferred`, not disguised as an estimate.

**Artifact `measured_at`: 2026-07-27T19:48:07.152293+00:00** (Speckle leg: 2026-07-27T20:04:58.896285+00:00).

### A note on requirement traceability

`REQUIREMENTS.md` carries the three DSAV requirements as individual checkboxes but records their traceability as a **single phase-level range row** — `DSAV-01 … DSAV-03 | Phase 39 | Pending`. The `requirements mark-complete` tooling cannot split a range row per-ID, so marking DSAV-02 complete after Wave 3 was a **no-op against the traceability table** even though the checkbox flipped. The same applies to DSAV-01 and DSAV-03 here: their checkboxes are authoritative, the range row is not, and the range row only becomes accurate once all three are done. Recorded so a later reader does not mistake a stale `Pending` in that table for unfinished work.

---

## See also

- **`39-EVIDENCE.json`** — the raw machine-written artifact this note transcribes. Source of truth for every figure above.
- **`DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md`** — the DSAV-03 ADR: the decision, the empirically-blocked rejections, the identity-model debt, the precedent departure, and the ordered follow-up milestone scope.
- `spec/RULE-PARTITION-POLICY.md` — normative on SWRL vs SHACL rule ownership; the reason the coverage gap is a partition question and not a missing shape.
- `39-CONTEXT.md` — the sixteen locked decisions (D-01 … D-16) plus D-A and D-B.
- `39-01-SUMMARY.md`, `39-02-SUMMARY.md`, `39-03-SUMMARY.md`, `39-04-SUMMARY.md` — what was actually built and measured, wave by wave.

---
*Phase: 39-designstate-auto-validation-investigation · Requirement: DSAV-01 · Written 2026-07-27*
