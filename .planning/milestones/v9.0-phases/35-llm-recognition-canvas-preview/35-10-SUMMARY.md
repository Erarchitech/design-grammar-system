---
phase: 35-llm-recognition-canvas-preview
plan: 10
subsystem: api
tags: [recognition, topology, rule-classifier, parity, data-service]

requires:
  - phase: 35-llm-recognition-canvas-preview
    provides: enriched Frame fixture with real degree-bearing wiring (35-05); cg_schemas.StructureProposal output contract (35-06)
provides:
  - data-service/cg_topology.py -- Tier 0 of the two-tier hybrid recognizer: scope_untagged(), extract_features(), widget_kind(), classify(), merge(), output_token_budget()
  - Closes UAT F2 at its source -- scope_untagged() never falls back to all untagged nodes when a tagged procedure resolves to zero members
  - C#-parity-pinned widget_kind() mirroring CanvasAnnotationParser.ClassifyNodeKind exactly, with abstention where Python/C# would disagree
affects: [35-12, 35-13, 35-14]

tech-stack:
  added: []
  patterns:
    - "Deterministic-first recognition: a rule-based Tier 0 removes topologically-certain candidates before the LLM ever sees them, at zero token cost"
    - "Abstention is a first-class outcome, not an error path -- confidence 1.0 decisions are unchallengeable, so uncertainty routes to residual instead of being guessed"

key-files:
  created:
    - data-service/cg_topology.py
    - data-service/tests/test_cg_topology.py

key-decisions:
  - "R2/R3 defer to residual when group_member_count > 1 (node shares an untagged group with >= 1 other node) -- that is Pattern evidence, not a Constant/Emergent signal, per the plan's Pattern-evidence deferral"
  - "Const (R2) is not restricted to widgets -- widget_kind in {Panel, None} both qualify, since Frame's real constants include non-widget components like Construct Point and Unit Y"
  - "Procedure attribution abstains (does not guess procedureIndex) whenever adjacent_tagged_procedures has zero or more than one entry -- a wrong procedureIndex persists into Neo4j, so ambiguity always routes to residual even when the topological kind is certain"
  - "merge() sorts Tier-0 rows deterministically by (procedureIndex, kind, memberIds[0]) rather than trusting caller-supplied order, so G13's array-position-is-identity contract holds regardless of how classify() iterated its input dict"
  - "merge() never dedups/drops a Tier-1 proposal that overlaps a Tier-0 decision -- it survives into the merged object so validate_proposed_structure's duplicate_member check catches it downstream"
  - "widget_kind() for a bare 'Number Slider'-named node with no slider domain data returns None, not Number and not Slider -- strict C# parity means the exact-match trap protects against a false Number, and there is no name-based Slider detection in C# at all"

patterns-established:
  - "cgContextJson v1 fixtures for Python tests are reshaped from the DG.Tests RawCanvas-shaped fixture (frame-cg-context.json) rather than duplicating a second hand-authored corpus -- same nodes/wires/procedure membership, different envelope shape"

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "scope_untagged() resolves per-procedure scope via one-hop wire adjacency and never silently widens to all untagged nodes when a tagged procedure has zero members (closes UAT F2 at its source)"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py::TestScope -- 5 tests including test_empty_procedure_never_widens_scope"
        status: pass
    human_judgment: false
  - id: D2
    description: "output_token_budget(residual) = clamp(512, 256 + 120*n, 8192), sized to the residual after Tier 0 rather than a hardcoded constant"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py::TestOutputTokenBudget -- 3 tests"
        status: pass
    human_judgment: false
  - id: D3
    description: "widget_kind() mirrors C# CanvasAnnotationParser.ClassifyNodeKind exactly (substring/case-insensitive Value List/Panel/Toggle, exact-match Number/Integer/Text/String, geometry param set, else None), including the Number Slider exact-match trap"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py::TestWidgetKindParity -- 13 parametrized parity cases"
        status: pass
    human_judgment: false
  - id: D4
    description: "extract_features() derives in_degree/out_degree/widget_kind/group_id/group_member_count/adjacent_tagged_procedures from cgContextJson v1 alone, verified against the enriched Frame fixture's real wiring"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py::TestExtractFeatures -- 8 tests"
        status: pass
    human_judgment: false
  - id: D5
    description: "classify() applies R1-R6 in order, first match wins; R1-R4 decide with confidence 1.0 and a mechanical (non-grammar) rationale, R5/R6 abstain into residual, group-membership and procedure-attribution deferrals both route to residual rather than guess"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py -- TestClassifyR1Var..TestClassifyR6Everything, TestClassifyProcedureAttribution, TestClassifyShapeAndRationale (18 tests, PASS+ABSTAIN per rule plus deferral/shape/rationale coverage)"
        status: pass
    human_judgment: false
  - id: D6
    description: "merge() composes Tier-0 decided rows and Tier-1 proposals order-stably (G13): deterministic Tier-0 sort key regardless of caller order, Tier-1 rows unmodified in model-returned order, overlapping proposals survive for the duplicate_member validator to catch"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_topology.py::TestMerge -- 5 tests including duplicate_member cross-check against cg_recognition.validate_proposed_structure"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-07-26
status: complete
---

# Phase 35-10: Tier-0 Topology Recognizer Summary

**`cg_topology.py` -- a deterministic, no-LLM rule classifier (R1-R6) that resolves per-procedure scope, derives topology features from `cgContextJson v1` alone, decides the topologically-certain nodes with confidence 1.0, and abstains honestly on everything else.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-07-26T11:39:08Z (approx, per STATE.md session continuity)
- **Completed:** 2026-07-26T12:13:53Z
- **Tasks:** 4 of 4
- **Files created:** 2

## Accomplishments

- **Closed UAT F2 at its source.** `scope_untagged()` returns `empty_procedure=True` and an empty node list when a tagged `procedure_index` resolves to zero members -- it never falls back to all untagged nodes, the exact silent-widening bug that turned a 14-node call into a 214-node call and then into the F1 truncation.
- **C#-parity-pinned `widget_kind()`.** Mirrors `CanvasAnnotationParser.ClassifyNodeKind` exactly: slider-domain presence first, then substring/case-insensitive matches for Value List/Panel/Toggle, then EXACT (case-insensitive) matches for Number/Integer/Text/String, then the geometry param name set, else `None`. A 13-case parametrized parity table pins this, including the `"Number Slider"` exact-match trap (with a slider domain it's `Slider`; without one it's `None`, never `Number`).
- **Honest R1-R6 rule table.** R1-R4 decide with `confidence == 1.0` and a mechanical rationale citing only degree/widget evidence (never the naming grammar); R5 (fully isolated) and R6 (everything else, including all Procedure/Pattern grouping) abstain by falling through every rule -- no explicit R5/R6 branch is needed. R2/R3 additionally defer to `residual` when a node shares an untagged group with >= 1 other node (Pattern evidence), and every decided row abstains rather than guesses when `adjacent_tagged_procedures` is ambiguous.
- **Order-stable `merge()` (G13).** Tier-0 rows sort deterministically by `(procedureIndex, kind, memberIds[0])` -- independent of caller-supplied order -- and precede Tier-1 proposals, which pass through unmodified. A Tier-1 proposal overlapping a Tier-0 decision survives into the merged object rather than being silently dropped, verified end-to-end against `cg_recognition.validate_proposed_structure`'s `duplicate_member` check.
- **Zero network surface.** `grep -rn "httpx\|requests\|adapter\|generate(" data-service/cg_topology.py` returns no match.

## Task Commits

Each task was committed atomically:

1. **Task 1: scope_untagged() + output_token_budget()** - `9906e0a` (feat)
2. **Task 2: extract_features() + widget_kind() C# parity** - `53c1fa7` (feat)
3. **Task 3: classify() -- R1-R6 rule table with honest abstention** - `29b2c4b` (feat)
4. **Task 4: merge() -- order-stable Tier-0 + Tier-1 composition** - `7d50a43` (feat)

## Files Created/Modified

- `data-service/cg_topology.py` -- Tier 0: `Scope`, `NodeFeatures`, `Tier0Result` dataclasses; `scope_untagged`, `extract_features`, `widget_kind`, `classify`, `merge`, `output_token_budget` functions
- `data-service/tests/test_cg_topology.py` -- 53 tests: scope (5), token budget (3), widget parity (13 parametrized), extract_features (8), classify R1-R6 + procedure attribution + shape/rationale (18), merge (5, cross-checked against `cg_recognition.validate_proposed_structure`)

## Decisions Made

- R2/R3's Pattern-evidence deferral (`group_member_count > 1`) is checked as an `and` clause on the same `elif` branch as the rule's topological condition, so a node whose degree profile matches R2/R3 but is grouped falls through to `residual` in one step rather than being caught by a separate later check.
- `_decide_row()` centralizes the procedure-attribution abstention (`len(adjacent_tagged_procedures) != 1` -> `None`) so every rule (R1-R4) gets the same guard for free, and the `suggestedName` convention (`{procedureIndex}_{kind}_{nickname}`) is built in exactly one place.
- The Frame-derived cgContextJson v1 test fixture (`_frame_cg_context()`) is a reshaping of `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` (same 34 nodes, 33 wires, and real procedure membership from 35-05) rather than a second hand-authored corpus -- keeps the Python-side degree assertions grounded in the same frozen reference the C# side grades against, without touching the frozen fixture file itself.
- Test commits were split per-task by writing the module and test file incrementally (Task 1's scope/budget code first, then appending each subsequent task's functions and tests) rather than committing the whole file at once, satisfying the atomic-per-task commit requirement while keeping every intermediate commit's test suite green in isolation.

## Deviations from Plan

None -- plan executed as written. One clarification worth recording: the plan's acceptance criterion for the widget-parity trap reads `widget_kind({"name": "Number Slider"})` returns `Slider`, `NOT Number`. Taken completely literally (no `slider` key in the dict), strict C# parity requires this to return `None` (there is no name-based Slider detection in `ClassifyNodeKind` at all -- only `node.Slider is not null`), not `Slider`. The parity table covers both readings: a `Number Slider`-named node *with* a slider domain present returns `Slider` (satisfying the literal assertion), and the same name *without* a slider domain returns `None`, not `Number` (satisfying the "NOT Number" guard, which is the exact-match trap the criterion is actually protecting against). Both cases are asserted; nothing was left ambiguous.

## Issues Encountered

- My own first draft of `extract_features()`'s docstring literally spelled `nestedGroupIds` while explaining that the field is deliberately not read, which tripped the plan's own `grep -c nestedGroupIds data-service/cg_topology.py` acceptance check (count must be 0, including comments). Reworded the docstring to describe the concept without the literal token; re-verified `grep -c` returns 0.
- The running `data-service` container has no bind mount for source code (`docker-compose.yml` only mounts `./data-service/data` and a read-only repo copy) -- new files aren't visible via `docker compose exec` until an image rebuild. Used `docker cp` to stage `cg_topology.py`/`tests/test_cg_topology.py` into the running container for each verification pass instead of rebuilding the image mid-session, to avoid restarting the container shared with the concurrent Phase 36 session. The committed host files are authoritative; the container will pick them up on its next legitimate rebuild.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- 35-12 can wire `recognize_structure()`'s two-tier entry point directly against this module: `scope_untagged` -> `extract_features` -> `classify` -> (LLM over `tier0.residual`) -> `merge`, exactly as the AI-SPEC's Entry Point Pattern shows.
- 35-13/35-14 have a rule-classifier ready for dimension E0 scoring (T0-precision >= 0.98, T0-contamination = 0); per the plan's own caveat, Corpus A (the Frame fixture) is stamped `tier0Evidence:false` so Corpus B is the admissible E0 evidence source.
- `data-service/cg_topology.py` makes zero Neo4j/network calls and imports only stdlib -- no new runtime dependency introduced.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*

## Self-Check: PASSED

- FOUND: data-service/cg_topology.py
- FOUND: data-service/tests/test_cg_topology.py
- FOUND: .planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-10-SUMMARY.md
- FOUND commits: 9906e0a, 53c1fa7, 29b2c4b, 7d50a43, c5b3752
