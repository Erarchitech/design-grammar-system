---
tags: [session, phase-822, reasoning-engine, reasoner-screen]
date: 2026-07-12
phase: 822
title: Phase 822 context — OWL 2 DL Reasoning Integration and Reasoner Screen Wiring
---

# Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring

**Session:** 2026-07-12
**Duration:** 30 min discuss-phase
**Status:** Context gathered, ready for planning

## Summary

Wired the Reasoner screen from a placeholder into a real "run a consistency check and read the result" flow. Four gray areas discussed; 13 decisions (D-01…D-13) captured in `822-CONTEXT.md` + design decision note `reasoner-screen-phases-checks-results`.

## Key Decisions

**Result presentation** — Verdict expands inside the HermiT card; inconsistent state shows unsatisfiable-class count + list by `Class.label` (IRI-name fallback), framed as "schema consistency."

**Run trigger & cards** — Per-card Run button on HermiT only; HermiT drops "Integration pending" badge and goes live; Pellet stays placeholder. Run forces `engine: "hermit"` on the active project.

**In-progress & unknown UX** — Spinner + elapsed counter + Cancel (AbortController). Four distinct verdict states (Consistent / Inconsistent / Unknown-timeout / Cancelled) with separate visual treatments; transport errors are a distinct error line.

**Result freshness** — "Last checked" timestamp; result persists in-memory across revisits within the session. Each run is a fresh POST (satisfies REAS-06 criterion 4 by construction). No active staleness detection (deferred).

**Reachability** — Reach sidecar via existing `/reasoner/consistency` data-service proxy (no new nginx route needed).

## Flagged for Research

- **IRI→label resolution for unsatisfiable-class list** — needs a decision: enrich at the sidecar level (best), resolve in the data-service proxy (good), or resolve in the UI (least ideal). Phase 821 not yet executed, so worth coordinating into the `/reason/consistency` response shape before it locks.

## Deferred

Pellet integration, active staleness detection, durable run history, async job pattern, unsatisfiability justifications — all future.

## Upstream Dependencies

Phase 822 consumes the Phase 821 sidecar contract:
- `POST /reason/consistency {project, engine?}`
- Response: `{consistent, unsatisfiable_classes[], axiom_counts{}, duration_ms, stripped_builtin_rules}`
- Synchronous with hard server-side timeout (~60–120s, 504-style)

Cannot be verified end-to-end until 821 ships the sidecar + data-service proxy.

## Next Steps

- `/gsd-plan-phase 822`
- Consider `/gsd-ui-phase 822` for a design contract (four-state verdict rendering warrants design review)
- Coordinate IRI→label resolution into Phase 821 planning if still in flight

## Files Changed

- `.planning/phases/822-owl-2-dl-reasoning-integration-reasoner-screen-wiring/822-CONTEXT.md` (created, 175 lines)
- `.planning/phases/822-owl-2-dl-reasoning-integration-reasoner-screen-wiring/822-DISCUSSION-LOG.md` (created, 107 lines)
- `.planning/STATE.md` (updated)

**Commits:** `114e527` (phase 822 context) + `5510d78` (state session record)
