---
name: phase-39-designstate-auto-validation
description: Auto-validation is triggered by a data-service in-process watcher over captured ValidationRun rows, verdicted by SHACL because no server-side SWRL evaluator exists, and fenced by three per-project guardrails
metadata:
  type: decision
  phase: 39
  decision_date: 2026-07-27
  requirements: [DSAV-01, DSAV-02, DSAV-03]
  status: accepted
  milestone: v9.0
---

# Phase 39: DesignState Auto-Validation — data-service watcher, SHACL verdict, guardrails

Investigation phase. The prototype exists to make this record true; production hardening is explicitly out of scope (`REQUIREMENTS.md`: *"Investigation + prototype + ADR only"*). Measured evidence lives in `.planning/phases/39-designstate-auto-validation-investigation/39-INVESTIGATION-NOTE.md` and its raw artifact `39-EVIDENCE.json`; this ADR points at them rather than restating their tables.

## Context

The question Phase 39 was asked: **can validation run automatically when a DesignState is captured?** The roadmap named three candidate trigger architectures — (a) a capture-time hook in the GH DESIGN STATE / VALIDATOR components, (b) a data-service watcher on DesignState writes, (c) an event-driven trigger on Neo4j ValidGraph writes.

Two blocking findings reframed the question before any comparison between those three mattered. **Both were discovered during this investigation, not assumed going in.**

1. **There is no `:DesignState` write to observe.** First-class `:DesignState` nodes do not exist in the live graph — Phase 29 recorded materializing them as FLAGGED BACKLOG needing explicit human sign-off and its own phase. A DesignState reaches Neo4j only as `statePayloadJson` on a `:ValidationRun`, written by `store_validation_run()` and only via `/validation/publish`, which is *already a completed validation run*. A watcher on "DesignState writes" as the roadmap literally worded it has nothing to watch. The capture event had to be invented.
2. **data-service cannot evaluate SWRL rules at all.** Rule evaluation is C# (`RuleEvaluator` in DG.Core, driven by the VALIDATOR component); `/validation/publish` only *receives* already-computed `failedRuleIds`. The only server-side judge that exists is SHACL, via the dg-reasoner sidecar. The verdict source was therefore not a choice either.

Everything below follows from those two facts.

## Decision

**Auto-validation is triggered by a data-service in-process watcher** — path (b), locked pre-discussion as D-A — **prototyped at spike depth with its guardrails demonstrated rather than described** (D-B), and **simulated at the client boundary rather than wired into Grasshopper** (D-02).

Concretely:

- **A capture is a `:ValidationRun` row with `status:'captured'`**, carrying `statePayloadJson`, written by an authenticated `POST /designstate/capture` (D-01). No new label, no schema-propagation sweep.
- **A daemon poll thread**, started through the FastAPI application lifespan and factored so its body is a pure function drivable by tests without a thread (D-03), polls for captured rows at a 2.0 s interval.
- **The watcher is gated by a per-project `IntegrationConfig` row with `provider:'AutoValidation'`** (D-13). An absent row means disabled — the correct default. `_auto_configure_integration`'s implicit-create precedent is deliberately *not* extended to this provider.
- **Captures are coalesced trailing-edge, newest wins** (D-14). Superseded rows are marked, not deleted.
- **The verdict comes from the existing SHACL / dg-reasoner path** (D-05), because no server-side SWRL evaluator exists. `dg-reasoner/valid_graph_export.py` already builds its ABox directly from `run.statePayloadJson`, so a captured row is SHACL-validatable with zero new export work.
- **The row is completed in place** (D-10) — a `SET` of verdict fields on the row the capture already `MERGE`d. `store_validation_run()` stays byte-for-byte untouched, pinned by a source-hash regression test. Zero regression surface on the shipped manual publish path.
- **A completed auto-run is stamped `trigger:'auto'` and `verdictSource:'shacl'`** (D-07), so a well-formedness verdict can never be silently misread downstream as a SWRL rule verdict.
- **Auto-runs are persist-only** unless a *separate* per-project publish flag is enabled (D-09). This makes the no-flood guarantee structural rather than a tuning exercise, and removes the Speckle-config hard dependency entirely.

The loop was measured closing hands-off on live Docker, with all three DSAV-03 guardrails demonstrated and one real Speckle version minted under the opt-in publish flag. See the investigation note for every figure.

## Rejected options, each with its empirical blocker

Not trade-off prose — each rejection rests on something found in this repository or this environment.

**Path (a) — GH capture-time hook in DESIGN STATE / VALIDATOR.**
The DESIGN STATE component **has no network client today**; only VALIDATOR carries `ValidationPublishClient`. Verifying the loop would require **live Rhino**, reproducing the deferred-in-Rhino-UAT pattern this project has already hit in Phase 33 plan 04, Phase 34-02/03 and Phase 824. A GH-side hook would additionally have to implement its own debounce client-side, since the collapse the watcher gets from one server-side newest-wins query becomes per-client state no server can arbitrate. Path (a) has the best latency floor of the three and is named below as follow-up scope — it is deferred, not dismissed.

**Path (c) — Neo4j write-event trigger.**
`neo4j:5.26` is **Community** edition, and Neo4j CDC is not a Community feature. **APOC is allowlisted but never installed** — `docker-compose.yml` sets the unrestricted/allowlist procedures to `n10s.*,apoc.*`, but the Dockerfile fetches only the neosemantics jar, so `apoc.trigger` would require both a Dockerfile change and an `apoc.conf` change. And the reliable APOC-trigger pattern for external side effects is **trigger → outbox node → external worker → HTTP**, which **structurally collapses into path (b)** with an extra hop and an extra failure mode. Empirically verifying this blocker by actually installing APOC was considered and declined as a detour outside the chosen path.

**Driving Grasshopper back through the Phase 33 canvas bridge to obtain a SWRL verdict.**
`CanvasCommandDispatcher` is **read-only by design** — its handler dictionary means write commands require a deliberate code change. It also needs live Rhino, which inverts the dependency so that "auto" only works while a canvas happens to be open.

**Porting a minimal SWRL evaluator to Python.**
Creates a second evaluator that can silently disagree with the C# one — the exact divergence hazard Phase 35-12 solved by single-sourcing.

**Adding a Rule-derived design-compliance shape to `ontology/dg-shapes.ttl`.**
Governed by `spec/RULE-PARTITION-POLICY.md`, which is normative on which validation system owns which rule category, and consistent with Phase 823's D-823-04 ("data-integrity shapes only, no business rules"). Re-deciding the partition line inside an investigation phase is out of bounds.

**Adding auto-validation fields to the existing `provider:'Speckle'` config row.**
Would weld auto-validation config to Speckle config, contradicting the persist-only default that makes auto-validation work on projects with no Speckle wiring at all.

**Making `publish_result` optional in `store_validation_run`.**
Edits shipped v2.0-era load-bearing code and makes every Speckle field conditionally null for readers that assume otherwise. A parallel `store_auto_validation_run` was likewise rejected — a duplicated `MERGE` that can drift.

## Headline finding: the SHACL/SWRL coverage gap

**A SHACL-verdicted auto-run answers "is this captured state well-formed?" — not "does this design comply?"**

The shapes in `ontology/dg-shapes.ttl` target state well-formedness (`DsKindLabelShape`, `PropStateCompletenessShape`, `ObjStateObjectRefShape`, `RunStatusShape`). None expresses a design-compliance constraint like "maximum building height is 75 metres". **The prototype proves the mechanism; it does not close the compliance loop.** This is **follow-up milestone item number one**.

**And the verdict is currently not even discriminating.** Finding F-39-01, measured and recorded in the evidence artifact: `poll_once` calls the SHACL sidecar and **only then** writes `ValidStatus`. At validation time the run node therefore has no `ValidStatus`, which trips the shapes graph's own `RunStatusShape_valid`. That finding's `focusLabel` is the `runId`, which matches no objState, so the conservative unmapped fallback flips **every** ObjState entry to `false`. Measured: `conforms: false`, one violation, `ValidStatus: [false, false]` for a two-objState envelope — reproduced identically in the separate Speckle publish leg hours later.

**Auto-runs therefore report a uniformly all-false `ValidStatus` regardless of the design's actual conformance.** The verdict is structurally sound — it never claims a passing state it cannot attribute — but it is **not yet discriminating**. This ADR must not be read as saying auto-validation currently produces meaningful pass/fail verdicts. It does not yet.

**This is an open, unresolved design question, and Phase 39 deliberately did not fix it.** The two candidate fixes — reorder the ValidGraph export so `ValidStatus` is written before validation, or scope the shapes graph so an auto-run's own Run shape is excluded from its own validation — each have consequences an investigation phase did not have the budget to explore. Whichever is chosen belongs with follow-up item 1, and needs its own decision record.

## Guardrails as built

All three DSAV-03 guardrails were demonstrated in the prototype, not merely described. Numbers are in the investigation note.

1. **Debounce window — trailing-edge coalesce, newest wins.** Within the window only the newest captured row per project is validated. **Superseded rows are marked `status:'superseded'`, not deleted**, so the skipped-work trail stays auditable and the collapse ratio is directly measurable. This matches what an architect actually wants: validate where I ended up, not every slider twitch.
2. **Per-project rate limit.** A sliding 60 s window per project, held in the watcher process. Measured throughput matched the configured cap exactly. Captures arriving while the limiter is saturated are skipped *before* coalesce, so their rows remain `captured` rather than being superseded or dropped — throughput is capped without data loss (finding F-39-02: **the rate limiter, not the debounce window, is what caps sustained throughput**).
3. **Per-project opt-in flag.** An `IntegrationConfig` row with `provider:'AutoValidation'`; **an absent row means disabled**, and a project with no such row is invisible to the watcher — the enabled-projects query filters at the Cypher level, so an unconfigured project is never even enumerated.

A fourth, not among DSAV-03's three: the **bounded attempt counter** from the departure below, which keeps a failing sidecar from producing an infinite retry loop.

## Identity-model decision: `add-alongside`

The primary noun is `:ValidationRun` — unchanged as a label, but its semantics widen in three directions at once. `status` becomes a state machine (`captured` → `completed` | `superseded` | `failed`) in which a row can exist having never run; `trigger` gains `'auto'` where manual was previously the only case; `verdictSource` gains `'shacl'` alongside the SWRL verdict every existing reader implicitly assumes.

**Decision: `add-alongside`.** Reuse the existing `:ValidationRun` label, the key `{graph, project, runId}`, and the existing property vocabulary. Add `trigger`, `verdictSource`, `capturedAt`, `completedAt`, `attempts` and `lastError` as **additive** properties. Do **not** promote a new `:DesignStateCapture` or `:CaptureEvent` noun.

**Rationale:** row reuse was chosen precisely to avoid the roughly ten-file schema-propagation sweep `CLAUDE.md` § Schema Change Propagation mandates. An investigation phase must not spend its budget on a schema migration it may end up recommending against.

**Accepted debt — three specific costs:**

1. A row with `status:'captured'` is a **"run that has not run"** — semantically muddy, conceded by the decision that created it.
2. **`list_validation_runs` has no status filter** and orders by `createdAt` descending. Verified during planning. So `captured`, `superseded` and `failed` rows all surface in `GET /validation/runs/{project}`, the VALIDATION GRAPH component and the ui-v2 Model screen — with null Speckle identifiers and, pre-verdict, null `ValidStatus`. This is **broader** than "auto-runs stay visible": non-completed rows are visible too. Mitigated only by stamping `createdAt` at capture time so ordering stays sane, plus a tolerance invariant test.
3. A `verdictSource:'shacl'` verdict answers a different question than a SWRL verdict, and **readers cannot tell the difference without inspecting the property** — which none of them currently does.

**What would force a later promote to a first-class noun.** Any one of: (a) a second non-SWRL verdict source arrives, making `verdictSource` a genuine dimension rather than a flag; (b) a reader needs to page or filter runs and the `captured`/`superseded` rows become a correctness problem rather than noise; (c) the Phase-29-flagged first-class `:DesignState` node lands, at which point the capture event has a natural home and no longer needs to squat on `:ValidationRun`.

## Departure from precedent: the SHACL sidecar error policy

**This decision deliberately departs from the Phase 823 degrade-never-raise policy** recorded in [[Phase 823 SHACL validation layer design decisions]] as **D-823-02** ("Non-fatal SHACL sidecar proxy в publish path": `_call_shacl_validate` is wrapped so that HTTP 504 / timeout / unavailable never drops the publish response, and SHACL findings are supplementary information rather than a blocking step).

The watcher calls that **exact same helper function, unchanged** — same `httpx.Timeout` shape, same three-state status dict. **But the caller-side policy is opposite.** Where the manual publish path treats a SHACL timeout or outage as non-fatal and completes the run anyway, an auto-run:

- stays `status:'captured'`,
- is retried on subsequent poll ticks with a **bounded attempt counter**,
- and only then flips to `status:'failed'` with a reason in `lastError`, leaving `completedAt` and `verdictSource` null.

**Justification:** an auto-run that silently completes with no verdict is a strictly worse failure mode than a manual one, because **nobody clicked anything to watch it**. A human who presses publish and sees a run appear without SHACL findings can interpret that; a run that materialises unattended and claims completion without a verdict is indistinguishable from a working system.

Phase 823's **D-823-07** timeout-budget lesson is inherited unchanged and matters more here, not less: the data-service HTTP read timeout must exceed the dg-reasoner internal timeout with margin, or slow-but-successful validations produce false timeouts. On the manual path a false timeout costs a missing findings panel; on the auto path it burns an attempt from a bounded counter and can drive a healthy run to `failed`.

The two records should be read together.

## Consequences and accepted limitations

1. **Run-list pollution including non-completed rows.** `captured`, `superseded` and `failed` auto-rows are returned to every existing reader alongside completed ones, with null Speckle identifiers. Measured live: a single project returned HTTP 200 with five runs spanning all four statuses, every one carrying a `runId`.
2. **A `shacl` verdict is indistinguishable from a SWRL verdict** to any reader that does not inspect `verdictSource` — which, today, is all of them. Combined with F-39-01, an unmodified UI would present an all-false well-formedness verdict as though it were a design-compliance result.
3. **The in-memory guardrail window resets on a data-service restart.** Debounce timer state and the per-project rate-limit window live in the watcher process's memory, keyed by project. **A restart briefly reopens the rate-limit floodgate.** This is an explicit accepted limitation, recorded here rather than solved speculatively: writing guardrail counters back to the very database the watcher polls would amplify writes, and there is no multi-instance case yet to justify shared state.
4. **No retention cap on auto-runs.** An enabled project accumulates rows indefinitely, including the `captured` rows a saturated rate limiter leaves behind.
5. **The single-worker assumption is load-bearing.** data-service runs one uvicorn worker with no `--workers` flag, so exactly one watcher daemon thread polls. A transitional claim state on the row is unnecessary today and would become **necessary** under a multi-worker or multi-instance deployment.
6. **No configuration route or panel.** Enabling auto-validation for a project means calling the watcher's config upsert out of band. Deliberate — the capture endpoint is the phase's only new public surface — but it makes the feature operator-only today.
7. **One piece of the phase's own evidence is no longer queryable.** The single publish-enabled run's Neo4j row was destroyed by a later routine test-suite run and was deliberately **not** recreated (re-running would mint a second Speckle version and break the one-publish rule). The Speckle-side proof is durable, independent and human-confirmed. Recorded in full in the evidence artifact's `row_lifecycle` block and in the investigation note.

## Follow-up milestone scope

Ordered. Item 1 is the headline finding.

1. **Close the SWRL coverage gap** — a bridge write-command path or a headless evaluator so auto-validation reaches design-compliance rules rather than state well-formedness only. Includes resolving F-39-01 (export ordering vs. shapes-graph scoping) so auto-run verdicts become discriminating.
2. **GH-side capture wiring** — a network client on DESIGN STATE, or a capture toggle on VALIDATOR, so a real canvas capture fires the loop without a simulated client.
3. **Guardrail durability across restarts** — persist the debounce and rate-limit windows so a restart cannot reopen the floodgate.
4. **A transitional claim state and a shared-state design** — required *before* any multi-worker or multi-instance deployment, not after.
5. **UI treatment of auto-runs** — filtering or badging `trigger:'auto'` in ui-v2 and the VALIDATION GRAPH component. The UI gate returned no frontend work for Phase 39, so none was done.
6. **A retention cap on auto-runs per project** — a fourth guardrail beyond DSAV-03's three. Pruning is a destructive write and needs its own decision.
7. **A configuration route or panel for the `provider:'AutoValidation'` row**, deliberately omitted here to keep the capture endpoint as the only new public surface.
8. **Extract a shared connector-token FastAPI dependency** once a third call site appears. Two inline call sites do not yet justify the abstraction.
9. **First-class `:DesignState` nodes in ValidGraph** — still the Phase-29-flagged backlog item, requiring explicit human sign-off and its own phase. Phase 39 routed around it rather than resolving it.

## Security posture

`POST /designstate/capture` is **an authenticated write amplifier**: one request enqueues a validation run and, with the publish flag on, a Speckle version. It was the highest-severity item in the phase's threat model and the auth mechanism was deliberately left to planning rather than locked in discussion. As built it is protected by:

- **The Phase 825 project-scoped connector token**, resolved inline at the route via the connectors module's authenticate path (not the heartbeat path, which would misrepresent capture traffic as connector liveness). Unknown, malformed, non-Bearer and revoked tokens all return 401 and reach the writer zero times.
- **Strict project binding** — the credential's bound project must equal the body's project exactly; a mismatch returns a **generic 403 that leaks neither project name**, so the endpoint cannot be used to enumerate projects.
- **A payload size cap** on `statePayloadJson` (UTF-8 bytes), returning 413.
- **A persist-only default**, which keeps Speckle out of the blast radius entirely unless a project explicitly opts in to publishing.

**Known residual:** the rate limiter is **in-memory and therefore restart-resettable** (consequence 3 above, follow-up item 3). A restart is a brief rate-limit bypass. This is recorded as accepted rather than mitigated, so a follow-up milestone inherits an honest starting point instead of rediscovering it.

No new external packages were installed anywhere in the phase.

## References

- `.planning/phases/39-designstate-auto-validation-investigation/39-INVESTIGATION-NOTE.md` — **the DSAV-01 investigation note.** The three-architecture comparison, every measured figure, the analytic estimates with their provenance markers, and the F-39-01 / F-39-02 findings in full. This ADR deliberately does not duplicate its tables.
- `.planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json` — the raw machine-written measurement artifact both documents cite as fact.
- `spec/RULE-PARTITION-POLICY.md` — normative on SWRL vs SHACL vs Cypher rule ownership; the reason the coverage gap is a partition question rather than a missing shape.
- `spec/DATABASE.md` — ValidGraph schema; `statePayloadJson` / `rulesJson` / `shaclReportJson` as schema-propagation surfaces.
- [[Phase 823 SHACL validation layer design decisions]] — D-823-02 (the degrade-never-raise policy this decision departs from), D-823-04 (data-integrity shapes only), D-823-07 (the timeout-budget lesson inherited unchanged).
- [[DesignState persists to ValidGraph not Metagraph]] — why validation-run data lives in ValidGraph.
- [[Run ValidStatus is a per-object boolean array]] — the contract the derived auto-run `ValidStatus` must satisfy.
- [[Phase 824 CONNECTOR credential integration decisions]] — the project-scoped connector token the capture endpoint authenticates against.
