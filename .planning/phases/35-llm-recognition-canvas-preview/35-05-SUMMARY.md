---
phase: 35-llm-recognition-canvas-preview
plan: 05
subsystem: testing
tags: [fixtures, grasshopper, computgraph, topology, recognition-corpus]

requires:
  - phase: 32-computgraph-serialization-core
    provides: frame-cg-context.json RawCanvas fixture + SC1-SC4 serialization assertions
provides:
  - Frame fixture with both _Proc groups owning their members (20 + 11) and naming direct child groups only
  - 33 wires of real component-semantics wiring (was exactly 1 wire)
  - Three invariant guard tests pinning what 35-10 and 35-11 depend on
affects: [35-10, 35-11, 35-13, 35-14, recognition-eval]

tech-stack:
  added: []
  patterns:
    - "Fixture freeze protocol: reference and graded artifacts land in separate commits, reference before consumer"
    - "Wiring authored from each node's real Grasshopper component type, not from what would make a rule fire"

key-files:
  created: []
  modified:
    - DG/tests/DG.Tests/Fixtures/frame-cg-context.json
    - DG/tests/DG.Tests/FrameFixtureTests.cs

key-decisions:
  - "nestedGroupIds lists DIRECT children only — 11_Pat_TopChord is nested inside 11_Pat_DivideLine, not directly under the procedure. Consistent with ComputeHostPatternIds' 'immediate host id' contract (CanvasAnnotationParser.cs:414)"
  - "The three abstain nodes (n-untagged-01, n-scratch-01, n-scratch-02) are deliberately in neither procedure — they are the corpus's abstainExpected set and must stay ungroundable"
  - "Wiring authored from each node's real component type rather than to make rules fire; the degree properties Tier 0 keys on are emergent and verified, not engineered"
  - "Landed as two separate commits, and before data-service/cg_topology.py exists (asserted at commit time) — AI-SPEC §5 freeze protocol: a reference changing together with the artifacts it grades makes a run void, not merely suspect"

patterns-established:
  - "Invariant guard tests: a fixture edit that would delete a load-bearing property fails a named test instead of silently reading as an improvement"

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "Both _Proc groups own their members (20 and 11) and name their direct child groups — closes the live UAT F2 trigger where empty membership made _filtered_untagged_node_ids fall back to ALL untagged nodes"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/FrameFixtureTests.cs#Frame_Procedures_OwnTheirMembers"
        status: pass
    human_judgment: false
  - id: D2
    description: "33 wires of component-semantics wiring so Tier-0 degree rules are testable instead of collapsing to R5-abstain"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/FrameFixtureTests.cs#Frame_Fixture_CarriesRealWiring"
        status: pass
    human_judgment: false
  - id: D3
    description: "The three abstain nodes stay fully isolated — the corpus's only positive case for abstention recall"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/FrameFixtureTests.cs#Frame_AbstainNodes_StayIsolated"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 32 SC1-SC4 serialization assertions still pass unchanged against the enriched fixture, including the nesting proof (divideLine.Id == topChord.HostPatternId)"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ — 380 pass (was 377)"
        status: pass
    human_judgment: false

duration: unrecorded
completed: 2026-07-26
status: complete
---

# Phase 35-05: Frame Fixture Enrichment Summary

**The Frame fixture went from 34 nodes / 1 wire to a real topology corpus — both `_Proc` groups own their members, 33 wires carry component semantics, and three guard tests pin what Wave 2 grades against.**

## Performance

- **Tasks:** 3 of 3
- **Files modified:** 2
- **Commits:** 3 (one per task)

## Accomplishments

- **Closed the live UAT F2 trigger.** Both `_Proc` groups carried empty `memberIds`/`nestedGroupIds`. That is what makes `_filtered_untagged_node_ids` fall back to ALL untagged nodes when the requested `procedure_index` resolves to a member-less procedure — a caller who believed they scoped to 14 nodes silently sent 214 and then hit the F1 truncation. `11_Proc` now owns its 20 component members and names its 19 direct child groups; `12_Proc` owns 11 members and 11 child groups.
- **Made Tier 0 testable at all.** The fixture had exactly one wire, so every Tier-0 degree rule collapsed to R5-abstain and an eval built on it would have measured the LLM alone. 33 wires now model Construct Point + Unit Y + a length slider driving a Line SDL; that line feeding Divide Curve with an integer count slider; Divide Curve fanning out to a Panel and two bare Params; Evaluate Curve terminating the parameter branch; the footer procedure running Panels → Line → Param → terminal Lines.
- **Verified rather than engineered degree properties.** Because the wiring was authored from each node's real component type, the properties Tier 0 keys on came out emergent: Var-grouped nodes are never a `toNode`, Const-grouped nodes have in-degree 0, Emg/Emr-grouped nodes have out-degree 0, and all four bare-Param Interfaces are exactly 1-in/1-out.
- **Pinned the invariants.** Three guard tests stop a later fixture edit from silently removing what 35-10 and 35-11 depend on — and, critically, from having that deletion read as an improvement (more nodes classifiable).

## Task Commits

1. **Fill `_Proc` group members** — `2ce1de3` (fix)
2. **Add component-semantics wiring** — `1492514` (fix)
3. **Pin the load-bearing invariants** — `932e304` (test)

## Files Created/Modified

- `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` — `_Proc` membership filled; 33 wires added
- `DG/tests/DG.Tests/FrameFixtureTests.cs` — `Frame_AbstainNodes_StayIsolated`, `Frame_Procedures_OwnTheirMembers`, `Frame_Fixture_CarriesRealWiring`

## Decisions Made

- `nestedGroupIds` lists **direct children only**. `11_Pat_TopChord` is nested inside `11_Pat_DivideLine`, not directly under the procedure. This matches `ComputeHostPatternIds`' own contract ("each pattern group's IMMEDIATE host id", `CanvasAnnotationParser.cs:414`) and it is load-bearing: host resolution at `:429` is `FirstOrDefault` over document order, so listing a nested pattern as a direct child of an earlier group would hand it a non-pattern host, fail the `idByGroup` lookup, fall through to the strict-superset fallback, find nothing (TopChord's members are not a subset of DivideLine's), and silently lose the nesting.
- The three abstain nodes stay in neither procedure — they are the corpus's `abstainExpected` set and the sole positive case for abstention recall.
- Two separate commits, reference before consumer, asserted at commit time that `data-service/cg_topology.py` did not yet exist (AI-SPEC §5 freeze protocol).

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

**Latent order-dependence found in the parser, flagged not fixed.** Host resolution at `CanvasAnnotationParser.cs:429` is `FirstOrDefault` over document order, so a nested pattern listed as a direct child of an earlier group silently loses its nesting through the strict-superset fallback. Out of scope for a fixture change; this is the defect plan **35-16** was added to close.

## User Setup Required

None.

## Next Phase Readiness

- 35-10 can now derive in/out degree from real wiring; 35-11 can ablate this fixture into Corpus A.
- Fixture is frozen for grading purposes — any later edit must re-run the freeze protocol.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*
*Summary reconstructed from commits 2ce1de3, 1492514, 932e304 during Wave 1 close-out (2026-07-26).*
