# Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-12
**Phase:** 822-OWL 2 DL Reasoning Integration + Reasoner Screen Wiring
**Areas discussed:** Result presentation, Run trigger & card state, In-progress & unknown UX, Result freshness / re-run

---

## Result presentation — layout

| Option | Description | Selected |
|--------|-------------|----------|
| Inline result panel | A result card appears below the HermiT card after a run; same page, no navigation. | |
| Expand within HermiT card | The HermiT card expands to show the result inline where the "Integration pending" text was — keeps result bound to the engine. | ✓ |
| Modal / drawer | Result opens in an overlay; good for lots of detail but heavier, loses run context. | |

**User's choice:** Expand within HermiT card
**Notes:** Result stays visually bound to the engine that produced it.

## Result presentation — unsatisfiable detail

| Option | Description | Selected |
|--------|-------------|----------|
| Count + labeled list | "N unsatisfiable classes" + list by human-readable `Class.label` (IRI-name fallback); no raw IRIs. | ✓ |
| Count only | Just "N unsatisfiable classes" — exactly criterion 2, nothing more. | |
| Count + raw IRI list | Count + full IRIs — precise but exposes raw semantic-web vocabulary. | |

**User's choice:** Count + labeled list
**Notes:** Requires IRI→label resolution; flagged as a research/planning item (sidecar-enrich vs proxy-resolve vs UI-resolve). Keeps the Phase 823 "no raw RDF vocabulary to architects" principle.

---

## Run trigger & card state

| Option | Description | Selected |
|--------|-------------|----------|
| Per-card Run on HermiT only | HermiT gets Run + drops "Integration pending" badge (goes live); Pellet stays placeholder, no run; run always uses HermiT. | ✓ |
| Global Run, uses selected engine | One screen-level Run using whichever reasoner is selected; must handle Pellet-not-integrated gracefully. | |
| Per-card Run on both | Both cards get Run; Pellet's returns "not yet integrated". Symmetric but ships a button that only errors. | |

**User's choice:** Per-card Run on HermiT only
**Notes:** Matches REAS-06 (HermiT default engine) and criterion 1. Run forces `engine: "hermit"` against the active project.

---

## In-progress & unknown UX — during-run treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Spinner + elapsed timer, no cancel | Spinner + live elapsed-seconds; button disabled; no client cancel. | |
| Spinner + elapsed + Cancel | Same, plus a Cancel button that aborts the fetch client-side (AbortController). | ✓ |
| Plain spinner | Just a spinner, no elapsed timer. | |

**User's choice:** Spinner + elapsed + Cancel
**Notes:** Client abort may not stop the server run; acceptable.

## In-progress & unknown UX — verdict states

| Option | Description | Selected |
|--------|-------------|----------|
| 4 states: Consistent / Inconsistent / Unknown / Cancelled | Distinct treatments; user-cancel kept separate from server timeout. | ✓ |
| 3 states, cancel folds into Unknown | Consistent / Inconsistent / Unknown; client cancel shows as Unknown. | |
| 3 states, cancel just clears | Cancelling returns to idle with no result shown. | |

**User's choice:** 4 states: Consistent / Inconsistent / Unknown / Cancelled
**Notes:** Unknown = neutral/amber "timed out — inconclusive" (criterion 3, distinct from fail). Cancelled = quiet gray. Transport/hard errors (decided separately) surface as a distinct error line, not folded into Unknown.

---

## Result freshness / re-run

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp + persist for session, no staleness guess | "Last checked" timestamp; result persists in-memory across revisits; no change-detection. | ✓ |
| Timestamp + clear on revisit | Timestamp, but result clears on leaving/returning to the screen. | |
| Timestamp + active staleness banner | Timestamp + detect ontology-export change (hash/axiom-count) and warn "may be stale". | |

**User's choice:** Timestamp + persist for session, no staleness guess
**Notes:** Each run is a fresh POST → sidecar re-reads live Neo4j, satisfying criterion 4 by construction. Active change-detection deferred (821 contract provides no change signal).

---

## Claude's Discretion

- Verdict/label/error copy and the "schema consistency" framing text.
- Spinner + elapsed-counter styling and the color mapping across the four states (existing tokens).
- Elapsed-timer tick interval and relative-time formatting.
- **IRI→label resolution location** (sidecar-enrich / proxy-resolve / UI-resolve) — flagged for the researcher; option (a) may warrant coordinating into the 821 response shape before it locks.
- Reachability path settled without discussion: reuse the `/reasoner/consistency` data-service proxy; no new nginx/vite route.

## Deferred Ideas

- Pellet integration (stays placeholder).
- Active staleness detection / "ontology changed" banner.
- Durable run history across sessions.
- Async submit/poll job pattern for long reasoning runs.
- Justifications / why-a-class-is-unsatisfiable explanations.
