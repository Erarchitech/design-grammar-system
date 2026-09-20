---
phase: 35-llm-recognition-canvas-preview
plan: 14
subsystem: recognition-eval
tags: [eval-harness, corpus, canvas-annotation, urbanblock, tier0-evidence, grasshopper]

requires:
  - phase: 35-llm-recognition-canvas-preview
    plan: 11
    provides: recognition_eval.corpus loader/validator (load, assert_provenance, assert_context_unchanged, check_freeze_commit) and the frame_ablated reference-file shape this plan mirrors
provides:
  - "Corpus B (urbanblock_slice): the SC1 EVIDENCE corpus -- a differently-authored canvas (UrbanBlock_V7), tagged through the production DG ENTITY TAG / DG OBJECT MARKER instrument, frozen with tier0Evidence:true"
  - "A live-canvas confirmation that Tier-0 rule R4 (bare-pass-through-Param detection) is unreachable on real Grasshopper data, traced to a naming-convention mismatch between the C# extractor and the rule's own only test"
affects: [35-15]

tech-stack:
  added: []
  patterns:
    - "Nested-Pattern block derivation subtracts the child's memberIds from the host's raw tagged memberIds so no id appears in two reference blocks; the parent/child relationship is carried structurally via hostBlockId, not via member overlap"
    - "A tagged pull's raw Pattern/Parameter/Interface memberIds can include a nested child Pattern's own Grasshopper Group instanceId as a phantom member (not a component, absent from nodes[]) -- the reference derivation must filter memberIds against context.nodes[] before emitting a block, not trust the raw tagged group verbatim"

key-files:
  created:
    - data-service/fixtures/recognition_eval/urbanblock_slice.context.json
    - data-service/fixtures/recognition_eval/urbanblock_slice.expected.json
  modified: []

key-decisions:
  - "Scope came out to 4 procedures (PLOT LAYOUT, BUILDING FOOTPRINT, BUILDING MASS EXTRUDING, OPENSPACE), not the plan's stated 2-3. Node count inside procedures (73) sits within the plan's 60-80 target and block count (32) clears the >=20 floor, so the scope intent -- eval unit matching the production per-procedure unit -- is satisfied; recorded as an accepted deviation rather than reworked."
  - "Reference block ids (b01..b32) are ordered by procedureIndex ascending, then by kind alphabetically (ConstantParam < EmergentParam < Interface < Pattern < VariableParam), then by entity name (case-sensitive ASCII). This is an original deterministic ordering rule for this corpus, not a byte-for-byte replica of frame_ablated's internal C#-emitter order (which is itself an artifact of that emitter's iteration order, not a documented contract)."
  - "For the one nested Pattern pair (13_Pat_2 Extruder / 13_Pat_3 HeightAssign, hostPatternId cg:1:pat:13_2), the host block's memberIds is the tagged group's raw memberIds MINUS the 3 ids that belong to the nested child -- otherwise those 3 ids would appear in both blocks, violating the plan's no-collision requirement. The nesting relationship is carried entirely by hostBlockId (b26 -> b25); block-level memberIds sets are disjoint."
  - "One further filter was required beyond the nesting subtraction: Extruder's raw tagged memberIds also contained id 7282017a-fb58-48c4-b664-2c12ff4df3a9, which is NOT a component in the pull's nodes[] array in either the tagged or ablated pull, has no wires, and is absent from the C# extractor's own node list entirely. It is HeightAssign's own Grasshopper Group instanceId, captured as a phantom 'member' of its enclosing group by whatever routine walked the group's Objects collection -- a leftover of the parser walking nested GH Group containment, not a bug specific to this reference. It was excluded from Extruder's block memberIds because the hard constraint requires every memberIds entry to resolve in context.nodes[]; a hand-editing shortcut was avoided by re-deriving the exclusion mechanically (set-difference against nodes[]) rather than deleting the id by inspection alone."
  - "frozenAtCommit follows Corpus A's established precedent (35-11): pinned to `git rev-parse HEAD` captured BEFORE the freeze commit (parent HEAD), not the freeze commit's own hash (which cannot be known at authoring time -- the commit's tree includes this very field). The freeze commit's actual sha (22cecc6176d0e0bfb7a9da5d5c9c525ad4f0878a) is recorded here in the summary per the plan's own guidance, resolvable at scoring time via `git log -1 --format=%H -- urbanblock_slice.expected.json`."

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "Corpus B (urbanblock_slice) exists: 32 reference blocks (>= 20 minimum) across 4 procedures, 8 abstainExpected entries (>= 2 minimum), tier0Evidence:true, mechanically derived from a live tagged /computgraph/context/pull of UrbanBlock_V7 -- a canvas authored by the architect for design reasons, independently of the Tier-0 rule authorship"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "corpus.load('urbanblock_slice') + assert_context_unchanged -- 32 blocks, 8 abstain, tier0Evidence=True, 0 memberId collisions, 0 memberIds missing from nodes[], docker compose exec data-service pytest tests/test_recognition_scoring.py -q (48 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Freeze commit (22cecc6) contains only the two urbanblock_slice.* fixture files -- no change to prompts/recognition_system.md, fixtures/frame_recognition_fewshot.json or cg_topology.py in the same commit"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "git show --name-only HEAD (2 files only) + corpus.check_freeze_commit(staged) -> [] (empty violation list)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tier-0 rule R4 (bare pass-through Param -> not-Interface) is confirmed unreachable on live Grasshopper canvas data -- a code defect traced to a naming mismatch between the C# extractor's Name field and R4's startswith('Param') test, not fixed in this plan per the freeze protocol"
    requirement: RCGN-01
    verification: []
    human_judgment: true
    rationale: "This is a finding to be acted on by a future follow-up plan (explicitly out of scope here per the freeze protocol's prohibition on touching cg_topology.py in the reference commit); a human must decide when/how R4 gets fixed, this plan only documents and evidences the defect."

duration: ~35min
completed: 2026-07-26
status: complete
---

# Phase 35-14: UrbanBlock Slice (Corpus B) Summary

**Corpus B (`urbanblock_slice`) frozen: a live, differently-authored 4-procedure UrbanBlock_V7 canvas slice (102 nodes/105 wires) tagged through the production DG ENTITY TAG/OBJECT MARKER instrument, yielding 32 reference blocks and 8 abstain candidates with `tier0Evidence: true` -- the first canvas that can carry an SC1 generalization claim.**

## Performance

- **Duration:** ~35 min (Tasks 2-3; Task 1 was performed live by the architect prior to this session)
- **Tasks:** 2 of 2 (Task 1 pre-completed)
- **Files created:** 2

## Accomplishments

- **Corpus B exists and is frozen.** `urbanblock_slice.context.json` (the ablated input, committed byte-verbatim from the architect's live pull, sha256 `9ac7ad8a...` matching `contextSha256`) and `urbanblock_slice.expected.json` (32 reference blocks + 8 `abstainExpected` entries, `tier0Evidence: true`, `ipClass: "own"`) are committed together in `22cecc6`, a commit that touches nothing outside `fixtures/recognition_eval/`.
- **The reference was mechanically derived, never hand-authored.** Every block's `kind`/`procedureIndex`/`name`/`memberIds`/`hostBlockId`/`publishable` was read directly off the architect's tagged pull (never the ablated one), with two derivation rules applied mechanically rather than by judgment: (1) a nested Pattern's host block excludes the child's memberIds so no id appears in two blocks; (2) any tagged memberId absent from the pull's own `nodes[]` array is dropped, because it denotes a nested Group's own instanceId leaking into its parent's raw member list, not a real component.
- **Corpus.py validates clean.** `corpus.load('urbanblock_slice')` + `assert_context_unchanged` pass; 32/32 blocks resolve entirely inside `nodes[]`; 0 memberId collisions across blocks; 0 overlap between `abstainExpected` ids and block ids; exactly 1 non-null `hostBlockId` (the `HeightAssign` -> `Extruder` nesting). `check_freeze_commit` returns an empty violation list for the staged file set. `tests/test_recognition_scoring.py` -- 48/48 pass (no regression).
- **FM-2 is confirmed uncovered, and the cause is a real code defect, not a corpus gap.** Tier-0 rule R4 in `cg_topology.py` (~line 383-393) only fires for components whose `name` starts with `"Param"`, but `CanvasAnnotationParser`/`ComputgraphContextSerializer`'s `Name` field is the Grasshopper DISPLAY name (`Geometry`, `Integer`, `Curve`, ...) -- never `Param...`. A scan of all 102 canvas nodes in this pull found zero components matching. R4's only test (`test_r4_pass_bare_param_relay_decides_intf`) feeds a synthetic `name="Param"` node that no real GH component produces, so the test cannot detect the defect. The architect deliberately added two genuine bare pass-through relays (`Geometry`/`Geo` and `Integer`/`Int`, both in_degree=1/out_degree=1, untagged, outside all `_Proc` groups) to the canvas specifically to probe this; they are present in the committed corpus as the standing evidence. Per the freeze protocol, R4 is **not** fixed in this plan -- `cg_topology.py` is untouched by the freeze commit, as verified above.
- **Composition coverage is otherwise strong.** FM-3 (8 fully isolated abstain candidates: Number Slider, 3x Panel, 3x CONNECTOR, CLASSIFICATOR -- all in=0/out=0). FM-4 (multi-member Patterns: OpenSpaceDomainOfRegions=9, Extruder=7 raw/4 direct, RegionConfig=6; one genuine nested pair HeightAssign inside Extruder). FM-5 (37 short/terse nicknames, 24 unique, e.g. `Srf`, `Lng`, `Cull`, `Item`, `Crv`, `Dom`, `A×B`). FM-6/E8 (`13_Const_VectorZ` wraps a `Unit Z` component the parser cannot type -- `publishable: false`, the deliberate E8 positive case). E3 (5 of 6 interfaces carry genuine inter-procedure traffic: `BaseRegion`->12, `AllRegions`->17, `DomainCuttedRegions`->13+17, `Indexes`->17, `SurroundingTest`->13+17; only `PlotTotalArea` is internal-only). FM-1 (spatially interleaved grouping) was satisfied per Task 1's live annotation session, per the architect's own record.

## Task Commits

1. **Task 1: Annotate the UrbanBlock slice in Grasshopper and pull the tagged context** -- performed live by the architect prior to this session; both pulls (tagged reference source and ablated corpus input) were captured and handed off, no commit in this repo (the tagged pull is a working artifact, not a committed fixture -- only the derived ablated context and reference are committed).
2. **Tasks 2+3: Ablated context + derived, validated, frozen reference** -- `22cecc6` (feat) -- `urbanblock_slice.context.json` committed verbatim from the ablated pull; `urbanblock_slice.expected.json` derived from the tagged pull, validated against `corpus.py`, and frozen in the same commit (both files are the plan's single stated deliverable pair; Tasks 2 and 3 were executed together as one atomic freeze commit per the plan's own freeze-protocol requirement that the two corpus files land in one commit touching nothing else).

**Plan metadata:** (this summary + STATE/ROADMAP update, committed separately per the standard docs commit)

## Files Created/Modified

- `data-service/fixtures/recognition_eval/urbanblock_slice.context.json` -- ablated `cgContextJson` input (102 nodes, 105 wires, 4 `_Proc` groups with empty patterns/parameters/interfaces, 32 untagged groups covering 68 demoted members, 37 raw untagged node ids, zero parser warnings)
- `data-service/fixtures/recognition_eval/urbanblock_slice.expected.json` -- 32 reference blocks (10 in PLOT LAYOUT, 12 in BUILDING FOOTPRINT, 7 in BUILDING MASS EXTRUDING, 3 in OPENSPACE), 8 `abstainExpected` entries, `tier0Evidence: true`, `ipClass: "own"`, `frozenAtCommit` pinned to parent HEAD `c15c32861c4c567a5ddbf17b771def1d8045b064`

## Decisions Made

See `key-decisions` in frontmatter for the full rationale on: the 4-procedure scope, the deterministic block-ordering rule, the nested-Pattern memberIds subtraction, the phantom-Group-instanceId filter, and the `frozenAtCommit` pinning convention (matches Corpus A's established precedent from 35-11).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Nested Pattern's raw tagged memberIds contained a phantom Grasshopper Group instanceId absent from `nodes[]`**
- **Found during:** Task 3 (deriving the `Extruder` block), during the mandatory pre-commit check that every `memberIds` entry resolves in `context.nodes[]`
- **Issue:** The tagged pull's `13_Pat_2 Extruder` group's raw `memberIds` included `7282017a-fb58-48c4-b664-2c12ff4df3a9`, an id present in neither the tagged nor ablated pull's `nodes[]` array and with zero wires anywhere in either file. It is the nested `HeightAssign` child group's own Grasshopper Group instanceId, picked up as a "member" of its enclosing group -- a container-walking artifact of however the tagged pull enumerated group Objects, not a real component.
- **Fix:** Excluded the id from `Extruder`'s block `memberIds` (alongside the 3 ids already subtracted for the `HeightAssign` nesting relationship). Verified mechanically: every one of the 64 memberIds across all 32 blocks now resolves inside the committed context's `nodes[]` (script-checked, zero misses).
- **Files modified:** `data-service/fixtures/recognition_eval/urbanblock_slice.expected.json`
- **Commit:** `22cecc6`

**2. [Accepted deviation] 4 procedures instead of the plan's stated 2-3**
- **Found during:** Reviewing Task 1's handoff (performed by the architect before this session)
- **Issue:** The plan's `plan_decisions` scope target was "2-3 procedures, ~60-80 nodes, >= 20 blocks." The architect's live annotation covered 4 procedures.
- **Assessment, not a fix:** Node count inside procedures (73) is within the 60-80 target band and block count (32) clears the >= 20 floor comfortably. The scope's underlying intent -- an eval unit matching the recommended per-procedure production scoping unit -- is satisfied; splitting hairs over "2-3" vs "4" would not change the corpus's evidentiary value. Recorded as an accepted deviation, not reworked.
- **Files affected:** both corpus files (scope is baked into the annotated region, not separable after the fact)

Or otherwise: no other deviations -- Tasks 2 and 3 executed per the plan's stated derivation rules, with the two mechanical fixes above.

---

**Total deviations:** 1 auto-fixed (Rule 1, data-integrity), 1 accepted (scope)
**Impact on plan:** The phantom-id fix was necessary for the hard "every memberIds resolves in nodes[]" constraint; the scope deviation does not compromise the corpus's evidentiary value against the plan's own stated composition target.

## Known Stubs

None. Both corpus files are complete, real artifacts derived from live Grasshopper pulls -- no placeholder blocks, no fabricated coverage. Where a composition requirement genuinely could not be checked in this session (FM-1's spatial-interleaving verdict specifically, since Task 1's live annotation happened outside this session), it is recorded as inherited from Task 1's own record rather than re-asserted here.

## Threat Flags

None. `urbanblock_slice.context.json`/`.expected.json` are read-only test fixtures under `data-service/fixtures/recognition_eval/`, consumed only by the test-only `data-service/tests/recognition_eval/corpus.py` (confirmed unreachable from production `data-service/*.py`, per 35-11's same check). No new network endpoints, auth paths, or schema changes.

## Issues Encountered

- **FM-2 (bare pass-through Param must NOT classify as Interface) is uncovered** -- not a limitation of this corpus but a defect in Tier-0 rule R4, documented in detail under Accomplishments above. This is a finding for a future follow-up plan, not something fixable within this plan's freeze-protocol boundary (`cg_topology.py` may not change in the reference commit).

## User Setup Required

None.

## Next Phase Readiness

- 35-15 can score any recognition arm against `urbanblock_slice` immediately via `corpus.load('urbanblock_slice')` -- the same loader/validator path already proven against Corpus A in 35-11.
- 35-15 should report FM-2/R4 as an explicit coverage gap in its SC1 write-up, with a pointer to this summary's finding, rather than silently omitting it.
- A follow-up plan (out of scope here) should fix Tier-0 rule R4's naming check (likely matching against known GH parameter display names like `Geometry`/`Integer`/`Number`/`Curve`/`Text`/`Boolean` rather than a `startswith("Param")` string match) and add a test using a real display name, not the synthetic `name="Param"` fixture.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*

## Self-Check: PASSED

All 2 created fixture files found on disk; SUMMARY.md found on disk; freeze commit `22cecc6` found in git log.
