---
tags: [session]
date: 2026-07-05
---

# Phase 18 planning — 5 plans, 2 waves with Path A ClassIri

**Goal:** Planned Phase 18 (Rules and Validator Rework) — RULE DECONSTRUCT partition, CLASSIFICATOR purge, VALIDATOR rework with DesignStateBindingService, Model Viewer v2 read-side adaptation.

**Outcome:** 5 plans across 2 waves, all 6 requirements covered, verification passed after 1 revision.

## Plans Created

### Wave 1 (parallel)

| Plan | Requirement | Deliverable |
|------|-------------|-------------|
| 18-01 | GHVL-04 | DesignStateBindingService + ObjState.ClassIri extension (Path A) + error templates + tests |
| 18-02 | GHVL-01 | RULE DECONSTRUCT — Objects/DataProperties outputs, VariableTypeInferrer partition |
| 18-03 | GHVL-02 | CLASSIFICATOR full purge — component, namespace, model, icon, tests |
| 18-04 | GHVL-06 | Model Viewer read-side — `_project_state_summary` v2 envelope detection + Python tests |

### Wave 2 (depends 18-01)

| Plan | Requirement | Deliverable |
|------|-------------|-------------|
| 18-05 | GHVL-03, GHVL-05 | VALIDATOR new contract (Rule+DesignState+SendValid), publish path v2 extension |

## Key Decisions

### Path A: ObjState.ClassIri for D-05 Class IRI matching

Checker found that the initial planner silently worked around D-05 (Class IRI matching) because ObjState from Phase 16 lacks a `ClassIri` field. The planner bound ALL ObjStates unconditionally, which broke D-02 exclusion semantics (non-applicable ObjStates contributed to overall pass/fail).

**Resolution (user chose Path A):** Add `ClassIri` (string?, default null for backward compat) to ObjState model. Update OBJECT STATE component with "Class" input port for Class IRI passthrough from METAGRAPH Objects output. Then implement D-05 matching properly: DesignStateBindingService matches rule variable's REFERS_TO Class IRI against ObjState.ClassIri; only matching ObjStates produce bindings. D-02 exclusion works on top of this: non-matching ObjStates get `false` in ValidStatus but are excluded from the overall pass AND.

### Other resolved findings
- Verify commands fixed from `Select-String` pipeline to `$LASTEXITCODE` pattern (PowerShell exit-code propagation)
- RESEARCH.md open questions marked RESOLVED
- VALIDATION.md created from RESEARCH.md Validation Architecture section

## Files Changed

- `.planning/ROADMAP.md` — annotated with wave dependencies + cross-cutting constraints
- `.planning/phases/18-rules-and-validator-rework/18-01-PLAN.md` — revised with ObjState.ClassIri + D-05 matching + verify commands
- `.planning/phases/18-rules-and-validator-rework/18-02-PLAN.md` — verify commands fixed
- `.planning/phases/18-rules-and-validator-rework/18-05-PLAN.md` — fixed D-02 exclusion semantics + verify commands
- `.planning/phases/18-rules-and-validator-rework/18-RESEARCH.md` — open questions marked RESOLVED
- `.planning/phases/18-rules-and-validator-rework/18-VALIDATION.md` — new, created per Nyquist

## Verification Results

- **Coverage:** 6/6 requirements (GHVL-01..06), 9/9 decisions (D-01..D-09), 15/15 total items
- **Decision coverage gate:** PASSED
- **Post-planning gap analysis:** PASSED
- **Plan checker:** VERIFICATION PASSED after revision (2 blockers fixed, 2 warnings fixed)

## Next Steps

- `/gsd-execute-phase 18` — run all 5 plans

## References
- [[sessions/2026-07-04 Phase 18 discuss - Rules and Validator Rework|Phase 18 discuss]]
- [[sessions/2026-07-04 Phase 18 planning — research|Phase 18 research]]
- [[sessions/2026-07-04 Phase 18 UI design contract|Phase 18 UI contract]]
- [[decisions/Phase 18 Rules and Validator Rework decisions|Phase 18 decisions]]
