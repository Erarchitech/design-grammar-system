---
tags: [decision, phase-822, reasoner-screen, ui, ux]
date: 2026-07-12
relates: [[../../sessions/2026-07-12 Phase 822 context — OWL 2 DL Reasoning Integration and Reasoner Screen Wiring]]
---

# Reasoner Screen: Four-State Result Display, Per-Card Run on HermiT

**Decision date:** 2026-07-12
**Phase:** 822 (OWL 2 DL Reasoning Integration + Reasoner Screen Wiring)
**Scope:** How the Reasoner screen turns from a placeholder selector into a real consistency-check flow

## The Decision

### Result presentation
- Verdict expands **inside the HermiT card** (not modal, not separate panel) — keeps result bound to the engine that produced it.
- On inconsistent verdict: show **count + unsatisfiable classes by human-readable label** (OntoGraph `Class.label` property, IRI-name fallback). Never raw IRIs.
- Label the result **"schema consistency"** to prevent confusion with design-compliance results.

### Run trigger & reasoner card state
- **HermiT card gets a per-card Run button** and drops its "Integration pending" badge — becomes the only live engine in v8.2.
- **Pellet stays a placeholder** — no run button, no interaction.
- Run always uses `engine: "hermit"` against the active project.

### Four verdict states
1. **Consistent** — positive/ok visual treatment
2. **Inconsistent** — signal/red + unsat-class count & labeled list
3. **Unknown** — neutral/amber "timed out — inconclusive"; distinct from a real fail
4. **Cancelled** — quiet gray "you stopped this run — no result"

Plus a separate **transport error line** (sidecar down / 5xx / malformed) so semantic verdicts are never confused with hard failures.

### In-progress UX
- Spinner + live elapsed-seconds counter
- Disabled Run button
- Cancel button (AbortController) — aborting client-side doesn't necessarily stop the server run; acceptable

### Result freshness
- Show "Last checked: <relative time>" timestamp
- Result persists in-memory across screen revisits within the session
- Each run is a fresh POST; sidecar re-reads live Neo4j → satisfies freshness by construction
- No active staleness detection (e.g., axiom-count hash comparison) — deferred

## Why This Design

**Result visibility within the card:** Expanding the verdict inside the HermiT card keeps selection and result context together. Modal/drawer would be heavier and lose the engine context.

**Labeled unsat list, not raw IRIs:** Architects don't need (and shouldn't see) full RDF IRIs. Readable labels + count satisfy REAS-06 criterion 2 ("pass/fail summary with unsatisfiable-class count") without exposing semantic-web vocabulary. Phase 823 (SHACL) explicitly wants to keep raw vocabulary away from users.

**Per-card Run on HermiT only:** Symmetric UI (Run on both) would ship a Pellet button that only ever errors. Global Run (whichever is selected) requires graceful degradation of a dead path. Per-card is clearest.

**Four distinct states:** Unknown (timeout) must be visually distinct from Inconsistent (real failure) per REAS-06 criterion 3. Cancelled gets its own treatment because a user-initiated stop is not a reasoning outcome.

**In-progress feedback:** 60–120s server timeout is long; elapsed counter signals progress. Cancel (AbortController) gives the user control; server may finish anyway, but the UI stops waiting.

**Fresh by construction:** Every POST is fresh. No cache-busting or change-detection needed. Timestamp lets architects judge freshness and re-run at will.

## Integration Point (Flagged)

**IRI→label resolution:** The sidecar returns `unsatisfiable_classes[]` (shape TBD in Phase 821). Turning IRIs into readable labels can happen at:
- (a) **Sidecar level** — enrich each class with its OntoGraph `Class.label` at export time (best; keeps the UI simple)
- (b) **Data-service proxy level** — Neo4j lookup to resolve IRI→label (good; but moves state boundary)
- (c) **UI level** — resolve against already-loaded OntoGraph data in React (least ideal; requires that data to be current)

Since Phase 821 is not yet executed, worth coordinating (a) into the `/reason/consistency` response shape before it locks.

## Related Decisions

- Phase 821 D-10: `/reason/consistency` response shape (unsatisfiable_classes needs to carry labels or IRIs; label enrichment location TBD)
- Phase 821 D-09: Synchronous + hard server-side timeout (determines Unknown state trigger)
- REAS-06: HermiT default engine; pass/fail summary + unsat count; replaces v8.1 placeholder

## Deferred

Pellet integration, active staleness detection, durable run history, async job pattern, justifications for why a class is unsatisfiable.
