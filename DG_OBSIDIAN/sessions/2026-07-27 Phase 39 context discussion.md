---
tags: [session, phase-39, dsav]
date: 2026-07-27
phase: 39
title: Phase 39 context discussion — trigger paths, validation engines, Speckle coupling, guardrails
status: completed
---

# Session: 2026-07-27 Phase 39 Context Discussion

## What happened

Ran `/gsd-discuss-phase 39` to lock implementation decisions before planning. All four gray areas discussed and decided.

## Key findings that reshape the roadmap

1. **No DesignState write to observe.** `:DesignState` nodes don't exist in the live graph — Phase 29 flagged them as sign-off-gated backlog. A DesignState only reaches Neo4j as `statePayloadJson` on a `:ValidationRun` via `/validation/publish`. So the capture event cannot be "a watcher on DesignState writes" as the roadmap literally reads — it must be "a capture row that exists before validation."

2. **No server-side SWRL evaluator.** SWRL rule evaluation is C# (VALIDATOR component). `/validation/publish` only *receives* already-computed `failedRuleIds`. The server-side verdict engines that exist are SHACL (→ dg-reasoner) and the OWL reasoner.

3. **Every auto-run would mint a Speckle version by default.** `/validation/publish` publishes to Speckle *before* persisting. Routing auto-runs through it makes publish-flood the default behavior, not a risk to mitigate.

## Decisions locked

### Trigger source
- **D-01:** Capture event = `ValidationRun {status:'captured'}` row, not a `:DesignState` node. No new label, no schema sweep.
- **D-02:** Capture written by simulated client (`POST /designstate/capture` + curl/pytest), not GH wiring. No live Rhino needed; GH path deferred to follow-up.
- **D-03:** Watcher = in-process daemon poll thread, poll body factored as pure function.
- **D-04:** DSAV-01 comparison measured for path (b), analytic + blockers for (a)/(c). Perplexity research confirmed path (c) collapses to (b) anyway (Neo4j 5 Community, APOC absent, reliable pattern is trigger→outbox→worker).

### Validation engine
- **D-05:** Verdict from existing SHACL/dg-reasoner path (already reads `run.statePayloadJson`).
- **D-06:** SHACL covers state well-formedness, not design compliance — accepted as headline ADR finding. SWRL gap = follow-up item #1.
- **D-07:** `ValidStatus` derived from SHACL, stamped `trigger:'auto'` + `verdictSource:'shacl'`.
- **D-08:** Sidecar failure retries rather than silently completing — deliberate departure from Phase 823 precedent (auto-runs need supervision).

### Speckle coupling
- **D-09:** Persist-only by default, publish opt-in. Removes Speckle-config hard dependency.
- **D-10:** Completion is a `SET` on the existing captured row. `store_validation_run` untouched.
- **D-11:** Publish leg demoed once with the flag on (SC1 evidence + real Speckle-noise data point).
- **D-12:** Auto-runs stay in the normal run list, distinguished only by provenance.

### Guardrail state
- **D-13:** Config on `IntegrationConfig {provider:'AutoValidation'}`, reusing existing key shape.
- **D-14:** Trailing-edge coalesce debounce; superseded rows marked, not deleted.
- **D-15:** Counters in-memory in the watcher. Restart resets the window — explicit ADR line.
- **D-16:** DSAV-01 note in `.planning`, DSAV-03 ADR in `DG_OBSIDIAN/knowledge/decisions/`.

## Artifacts produced

- `.planning/phases/39-designstate-auto-validation-investigation/39-CONTEXT.md` — 16 decision categories + canonical refs + code context + deferred ideas
- `.planning/phases/39-designstate-auto-validation-investigation/39-DISCUSSION-LOG.md` — audit trail of areas discussed, options presented, choices made
- Commits: `c67ade1` (context + log), `d208984` (state update)

## Open for the planner

**Capture-endpoint authentication** is the highest-severity threat-model item (ASVS L1, block-on-`high`). `POST /designstate/capture` is a new unauthenticated write amplifier. Candidate: reuse Phase 825 project-scoped connector token. Left open deliberately so plans carry a `<threat_model>` block.

## Next steps

1. `/gsd-plan-phase 39` to create the implementation plan
2. During planning, resolve capture-endpoint auth (and record threat model)
3. During execution, build the watcher daemon, capture endpoint, guardrails, prototype the publish leg once

## Reference

- Full decisions: `.planning/phases/39-designstate-auto-validation-investigation/39-CONTEXT.md` (16 D-NN entries)
- Discussion log: `.planning/phases/39-designstate-auto-validation-investigation/39-DISCUSSION-LOG.md` (areas, options, choices, notes)
- Pre-locked decisions: `.planning/phases/39-designstate-auto-validation-investigation/39-PRE-DECISIONS.md` (D-A, D-B)
