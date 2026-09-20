---
phase: 40
created: 2026-09-19
status: recorded
---

# v9.0 Deferred Requirements

v9.0 closes with Phases 30 and 31 unbuilt. Their requirements are deferred rather than descoped or blocked: the requirements remain recorded and unchecked, with ownership transferred to v10.0. `REQUIREMENTS.md` carries the machine-readable list; this file preserves the reasoning for the milestone archive.

## Phase 30 — Orchestration Evaluation (n8n vs OpenClaw)

Nothing was built for Phase 30: no `30-*` directory exists under `.planning/milestones/v9.0-phases/`. The four deferred requirements are:

- **ORCH-01:** A documented evaluation matrix compares n8n and OpenClaw on webhook parity, function-node equivalents, LLM provider support, self-host Docker footprint, state/retry handling, maintenance burden, and migration cost.
- **ORCH-02:** A working spike ports the graph-query workflow to OpenClaw against the live stack behind the existing Nginx proxy contract.
- **ORCH-03:** An ADR records the go/no-go decision with explicit criteria; a no-go leaves n8n untouched and closes the question for this milestone.
- **ORCH-04:** On a go decision, the migration plan moves one workflow at a time with n8n running in parallel as fallback until end-to-end parity is verified — no big-bang cut-over.

The evaluation was never run. n8n works today, while OpenClaw needs a decision-gate spike before any migration commitment. Writing the ADR now would be the wrong substitute: ORCH-03 is a go/no-go gate intended to rest on the evaluation matrix (ORCH-01) and the working spike (ORCH-02). Deciding it inside a documentation phase without either would decide Phase 30's entire deliverable without evidence. The owning milestone is **v10.0**.

The reader should consult [REASONER-VALUE-AND-AUTOREPAIR.md](../../research/REASONER-VALUE-AND-AUTOREPAIR.md), dated 2026-07-13, and the existing Key Decision in `REQUIREMENTS.md`: “OpenClaw evaluated behind a decision gate, not adopted upfront.” The companion vault deferral note is planned at `DG_OBSIDIAN/knowledge/decisions/Phase 30 orchestration evaluation deferred — n8n retained, OpenClaw question unresolved.md`.

## Phase 31 — Rules Ingestion and Editing Workflow Upgrade

Phase 31 is dependency-blocked, not merely unstarted. Its five deferred requirements are:

- **RING-01:** The upgraded ingest workflow (gateway + context layer + validation retry) achieves a pass-rate on the reference rule set ≥ the measured Ollama baseline.
- **RING-02:** Editing a rule shows an atom-level old→new diff preview before commit; confirming applies with old-atom MATCH-DELETE cleanup intact; cancelling leaves the graph unchanged.
- **RING-03:** Ambiguous rules (missing limit, unknown concept, ambiguous unit) trigger a clarification question to the user instead of a guessed graph.
- **RING-04:** Failed Cypher validation auto-retries with validator feedback up to a bounded attempt count, then surfaces an actionable error — never executes invalid Cypher.
- **RING-05:** The full ingest/edit flow still works on the local Ollama fallback path (regression-verified).

The ROADMAP dependency shape is `28 → 29 → 31`, with Phase 31 also gated by Phase 30's ADR. Phase 31 therefore cannot start before the deferred orchestration decision. Its owning milestone is **v10.0**.

## Also carried out of v9.0

- **D1 — per-entity vs all-or-nothing publish rejection:** the runbook decision remains open; fuller record is in `.planning/milestones/v9.0-phases/40-e2e-validation-and-docs/40-CONTEXT.md` and the v10.0 backlog.
- **D2 — partial-reselection re-tag duplicate:** the policy question remains open; concrete code pointer is `EntityTagComponent.cs:246-263`; fuller record is in the Phase 40 context and v10.0 backlog.
- **D3 — `PreviewRegistry` undo-awareness:** the design question remains open and needs a custom `IGH_UndoAction`; fuller record is in the Phase 40 context and v10.0 backlog.
- **F-39-01 — auto-validation verdicts are a constant:** follow-up milestone item #1 owns the unresolved auto-validation verdict issue; see the Phase 39 investigation/ADR records.
- **Tier-0 rule coverage:** `cg_topology.classify()` abstains on every scoped candidate; this needs its own follow-up item, not a Phase 40 fix.
- **Unapproved migration:** `migrations/2026-07-07_validationgraph_to_validgraph.cypher` remains the oldest standing item and is explicitly outside v9.0 scope; approval record belongs with the migration backlog.

D1, D2, and D3 are recorded as open questions, not proposed resolutions. Phase 40 does not restate or solve them.
