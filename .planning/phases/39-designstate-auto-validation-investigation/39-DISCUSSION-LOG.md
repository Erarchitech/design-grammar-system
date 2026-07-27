# Phase 39: DesignState Auto-Validation Investigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 39-designstate-auto-validation-investigation
**Areas discussed:** Trigger source, Validation engine, Speckle coupling, Guardrail state

**Pre-loaded (not discussed):** D-A (path (b) data-service watcher) and D-B (spike depth, ADR-scoped) from `39-PRE-DECISIONS.md`.

**Research run during discussion:** one Perplexity search (orchestrator-run, sequential) on Neo4j 5 Community CDC availability and APOC trigger requirements — used to ground path (c) in the DSAV-01 comparison.

---

## Area selection

All four presented gray areas were selected for discussion.

| Option | Description | Selected |
|--------|-------------|----------|
| Trigger source — what the watcher watches | No `:DesignState` node exists to observe | ✓ |
| What 'runs validation' server-side | data-service has no SWRL evaluator | ✓ |
| Speckle coupling of auto-runs | publish-before-persist, Speckle config required | ✓ |
| Where guardrail state lives | opt-in flag, debounce, rate-limit config home | ✓ |

---

## Trigger source

### Q1 — What should the capture event be?

| Option | Description | Selected |
|--------|-------------|----------|
| ValidationRun with `status:'captured'` | Reuses existing row shape; no new label, no schema-propagation sweep; `status` becomes a state machine | ✓ |
| First-class `:DesignState` node in ValidGraph | Matches CLAUDE.md's schema tables, but Phase 29 flagged it as backlog needing human sign-off + its own phase | |
| Poll the canvas via the Phase 33 bridge | Zero schema change, but requires live Rhino — contradicts D-A's rationale | |

**User's choice:** ValidationRun with `status:'captured'`
**Notes:** Accepted cost is semantic muddiness — a "run" that hasn't run. Flagged for the ADR.

### Q2 — Who writes the captured row in the prototype?

| Option | Description | Selected |
|--------|-------------|----------|
| Simulated capture client only | `POST /designstate/capture` + curl/pytest driver; zero Rhino; GH wiring named as ADR follow-up | ✓ |
| Wire the GH component too | Highest fidelity, but reintroduces the deferred-in-Rhino-UAT pattern from Phase 33/34/824 and adds C# work | |
| Endpoint only, no client | Smallest surface, but no end-to-end demo — weakens DSAV-02 | |

**User's choice:** Simulated capture client only
**Notes:** Preserves D-A's rationale intact. GH-side path deferred explicitly, not silently.

### Q3 — How does the watcher observe?

| Option | Description | Selected |
|--------|-------------|----------|
| In-process background poll thread | Daemon thread + cursor; matches sync-`def` style; poll body a pure function for tests | ✓ |
| n8n scheduled workflow | Reuses orchestration, visible in UI — but drift-prone surface and Phase 30 hasn't settled n8n's future | |
| Explicit tick endpoint, no daemon | Maximally deterministic, but SC1 requires hands-off | |

**User's choice:** In-process background poll thread

### Q4 — How rigorous should the three-path comparison be?

| Option | Description | Selected |
|--------|-------------|----------|
| Measured for (b), analytic for (a)/(c) | Real latency / collapse ratio / runs-per-minute for the built path; reasoned estimates + recorded blockers for the others | ✓ |
| Analytic for all three | Cheaper, but SC2 requires the guardrails be validated, not described | |
| Measured for (b), verify (c)'s blocker empirically | Install APOC + `apoc.trigger` to test the verdict; strongest evidence, but a detour off the chosen path | |

**User's choice:** Measured for (b), analytic for (a)/(c)
**Notes:** Path (c) was shown to be largely foreclosed before the question was asked — `neo4j:5.26` is Community (CDC not a Community feature) and APOC is allowlisted but never installed. Perplexity research confirmed the reliable APOC pattern (trigger → outbox → worker → HTTP) collapses into path (b) anyway.

---

## Validation engine

### Q1 — What actually validates the captured state?

| Option | Description | Selected |
|--------|-------------|----------|
| SHACL / dg-reasoner server-side | Existing path, already reads `statePayloadJson`, no Rhino, no new evaluator; covers only the SHACL partition | ✓ |
| Drive Grasshopper via the canvas bridge | Covers full SWRL rule set, but bridge is read-only by design, needs live Rhino, inverts the dependency | |
| Port a minimal SWRL evaluator to Python | Headless SWRL coverage, but creates a second evaluator that can silently disagree with the C# one | |

**User's choice:** SHACL / dg-reasoner server-side
**Notes:** Scouting confirmed `dg-reasoner/valid_graph_export.py:43` builds its ABox directly from `run.statePayloadJson` — a captured row is SHACL-validatable with zero new export work.

### Q2 — How to handle the well-formedness vs. design-compliance gap?

| Option | Description | Selected |
|--------|-------------|----------|
| Accept it, name it as the headline finding | Prototype proves the mechanism; ADR states the partition limit; SWRL gap becomes follow-up item #1 | ✓ |
| Add a design-compliance shape | Stronger claim, but `RULE-PARTITION-POLICY.md` governs it and shape changes trigger the schema sweep | |
| SHACL + reasoner consistency | Broader automated verdict, but still not design compliance, at double the moving parts | |

**User's choice:** Accept it, name it as the headline finding

### Q3 — How does a completed auto-run record its verdict?

| Option | Description | Selected |
|--------|-------------|----------|
| Derive `ValidStatus` from SHACL + stamp provenance | Existing readers keep working; `trigger:'auto'` + `verdictSource:'shacl'` prevent misreading | ✓ |
| Leave `ValidStatus` null, `shaclReportJson` is the verdict | Maximally honest, but readers render an empty run and `RunStatusShape_valid` may flag it | |
| Separate `autoValidStatus` property | Cleanest separation, but a schema addition requiring the propagation sweep | |

**User's choice:** Derive `ValidStatus` from SHACL + stamp provenance

### Q4 — What if the SHACL sidecar is down or times out?

| Option | Description | Selected |
|--------|-------------|----------|
| Leave the row `captured`, retry with backoff | Bounded retries then `status:'failed'` with reason; needs an attempt counter | ✓ |
| Complete the run with an 'unavailable' verdict | Mirrors the Phase 823 degrade-never-raise precedent, but an auto-run completing silently with no verdict is a worse failure mode | |
| You decide | Let the planner follow existing retry patterns | |

**User's choice:** Leave the row `captured`, retry with backoff
**Notes:** Deliberate departure from the Phase 823 Plan 03 precedent — must be justified in the plan, not applied silently.

---

## Speckle coupling

### Q1 — What should an auto-run do about Speckle?

| Option | Description | Selected |
|--------|-------------|----------|
| Persist-only by default, publish opt-in | Makes SC2's no-flood guarantee structural; removes the Speckle-config hard dependency | ✓ |
| Publish every auto-run, rely on debounce | Zero new code path, but puts the whole success criterion on a tuning parameter | |
| Publish only when the verdict changes | Elegant Speckle history, but adds verdict-diffing and a published-verdict cursor to a spike | |

**User's choice:** Persist-only by default, publish opt-in

### Q2 — How is the persist-without-publish write built?

| Option | Description | Selected |
|--------|-------------|----------|
| Complete the existing captured row in place | Just a `SET`; `store_validation_run` stays untouched; zero regression surface on the shipped publish flow | ✓ |
| Make `publish_result` optional in `store_validation_run` | Single source of truth, but edits the shipped path and makes Speckle fields conditionally null | |
| Separate `store_auto_validation_run` | No risk to the existing path, but a duplicated MERGE that can drift | |

**User's choice:** Complete the existing captured row in place
**Notes:** The row already exists from the capture — no new persist function is needed at all.

### Q3 — Does the prototype exercise the publish leg?

| Option | Description | Selected |
|--------|-------------|----------|
| Demo it once with the publish flag on | Gives SC1 its literal "and (if enabled) publishes" evidence plus one real Speckle-noise data point | ✓ |
| Persist-only, publish leg ADR-scoped | Smallest surface, but SC1's second clause goes unverified | |
| Demo it, plus a deliberate flood test | Strongest SC2 evidence, but costs a deliberately noisy Speckle project and cleanup | |

**User's choice:** Demo it once with the publish flag on

### Q4 — Anything about auto-runs appearing in the run list?

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing — provenance stamps are enough | `trigger:'auto'` makes them filterable; off-by-default means nobody sees them unintentionally | ✓ |
| Exclude auto-runs from the default run list | Clean history by construction, but changes a shipped read endpoint for a prototype nobody has enabled | |
| Cap retained auto-runs per project | Useful given burst testing, but a fourth guardrail and a destructive write | |

**User's choice:** Nothing — provenance stamps are enough
**Notes:** Run-list pollution recorded in the ADR as a known consequence.

---

## Guardrail state

### Q1 — Where does the per-project opt-in flag live?

| Option | Description | Selected |
|--------|-------------|----------|
| `IntegrationConfig` with `provider:'AutoValidation'` | Reuses the existing `{graph, provider, project}` key; zero change to the Speckle row; absent = disabled | ✓ |
| New fields on the existing Speckle row | Fewer nodes, but welds auto-validation to Speckle config, contradicting the persist-only decision | |
| data-service settings file | Follows the llm/reasoner precedent, but those are global and DSAV-03 requires per-project | |

**User's choice:** `IntegrationConfig` with `provider:'AutoValidation'`

### Q2 — What does the debounce do to captures inside the window?

| Option | Description | Selected |
|--------|-------------|----------|
| Trailing-edge coalesce — newest wins | Superseded rows marked, not deleted; measurable collapse ratio (N in → 1 out) | ✓ |
| Leading-edge — first wins, rest dropped | Lowest latency, but the verdict describes a state already moved past | |
| Delay-and-run-all | Nothing dropped, but converts a burst into a backlog instead of suppressing it | |

**User's choice:** Trailing-edge coalesce — newest wins

### Q3 — Where do the runtime counters live?

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory in the watcher process | No write amplification against the polled database; single-instance data-service | ✓ |
| Persisted on the AutoValidation config node | Survives restart, but adds a Neo4j write per capture on the suppression path | |
| You decide | Let the planner choose for testability | |

**User's choice:** In-memory in the watcher process
**Notes:** Restart resets the window — to be recorded as an explicit ADR line.

### Q4 — Where do the investigation note and ADR live?

| Option | Description | Selected |
|--------|-------------|----------|
| Note in `.planning`, ADR in `DG_OBSIDIAN` | Matches the CLAUDE.md session protocol and the roadmap deliverable; cross-linked | ✓ |
| Both in `DG_OBSIDIAN` | Discoverable from the vault index, but measurements sit outside the GSD read path | |
| Both in `.planning`, vault note at phase close | Fewest context switches, but Phase 40 expects the decision already filed in the vault | |

**User's choice:** Note in `.planning`, ADR in `DG_OBSIDIAN`

---

## Wrap-up

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Write CONTEXT.md; carry capture-endpoint auth into planning as a threat-model item | ✓ |
| Discuss capture endpoint auth first | Lock the auth mechanism now rather than leaving it to the planner | |
| Explore more gray areas | Fixture relationship to Corpus A, meaning of off-by-default for CI | |

**User's choice:** I'm ready for context
**Notes:** Capture-endpoint authentication is deliberately left to planning, flagged in CONTEXT.md as the highest-severity threat-model item (ASVS L1, block on `high`).

## Claude's Discretion

None — every question was answered with an explicit choice. The one open item (capture-endpoint auth) was deliberately routed to the planner's `<threat_model>` block rather than left to Claude's discretion here.

## Deferred Ideas

- GH-side capture wiring (DESIGN STATE network client / VALIDATOR CAPTURE toggle) — ADR follow-up scope
- Closing the SWRL coverage gap — ADR follow-up item #1
- First-class `:DesignState` nodes — still the Phase-29-flagged, sign-off-gated backlog item
- Design-compliance SHACL shapes — blocked on `spec/RULE-PARTITION-POLICY.md`
- UI filtering/badging of `trigger:'auto'` runs — follow-up milestone; UI gate returned `frontend: false`
- Guardrail durability across restarts — explicit ADR line, not prototype work
- Retention cap on auto-runs — fourth guardrail beyond DSAV-03's three; destructive write
- Empirically verifying path (c)'s APOC blocker — declined as a detour off the chosen path
