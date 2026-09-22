---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 09
subsystem: database
tags: [spec-documentation, json-serialization, neo4j, evidence-contract, gap-closure]

# Dependency graph
requires:
  - phase: 1202-03
    provides: "The two regression Facts (TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope / _DivergeOnSerializerOwnConciseParameterShape) proving the parameters[] dual-wire-shape divergence, and the halted Task 3 disposition table"
  - phase: 1202-05
    provides: "The declared-exclusion subsection pattern in spec/DATABASE.md (geometry D-06, legacy-run not_evaluated D-11) this plan's subsection matches in register and heading convention"
provides:
  - "spec/DATABASE.md exclusion-contract subsection naming both parameters[] wire shapes, both readers, which is authoritative for which producer, asymmetric failure modes, and the two pinning Facts"
  - "spec/EVIDENCE-CONTRACT.md short cross-reference (5.2) pointing at the full contract"
  - "Comment-only pointers at both reader sites (Neo4jValidGraphRepository.TryParseDesignState, DesignStatePayloadV2Serializer.ParamFromDto)"
affects: [1202-verification, future-parameters-array-convergence]

# Tech tracking
tech-stack:
  added: []
  patterns: ["declared-exclusion spec subsection (heading convention: #### <title> (Phase NN plan MM, D-XX, ALGN-NN))"]

key-files:
  created: []
  modified:
    - spec/DATABASE.md
    - spec/EVIDENCE-CONTRACT.md
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs

key-decisions:
  - "Chose documented-exclusion disposition (option 3 of 1202-03's three) over reader convergence or writer-shape change — zero risk to stored data, satisfies ROADMAP's own escape-hatch wording verbatim"
  - "add-alongside assumption-delta accepted: two readers remain split by design, promoted from undocumented accident to declared contract"

patterns-established:
  - "Declared-exclusion spec subsections cite pinning regression Facts by exact name as the machine-checked tripwire, so a future test rename/removal is caught by grep-based acceptance checks re-run against the spec"

requirements-completed: [ALGN12-09]

coverage:
  - id: D1
    description: "spec/DATABASE.md carries a written exclusion-contract entry documenting the parameters[] dual-wire-shape divergence, its scope, and which reader is authoritative for which producer"
    requirement: "ALGN12-09"
    verification:
      - kind: other
        ref: "grep -c 'Declared exclusion: `parameters\\[\\]` has two wire shapes and two readers' spec/DATABASE.md == 1; grep numberValue/TryParseDesignState/cg_paramstate_store/DesignStatePayloadV2Serializer all >=1 (all were 0 pre-plan)"
        status: pass
    human_judgment: false
  - id: D2
    description: "spec/EVIDENCE-CONTRACT.md cross-references the divergence as a declared non-alignment"
    requirement: "ALGN12-09"
    verification:
      - kind: other
        ref: "grep -c 'Declared non-alignment' spec/EVIDENCE-CONTRACT.md == 1; grep -c 'spec/DATABASE.md' >=1; frozen-vocabulary diff check == 0 deletions"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both reader sites carry comment-only pointers to the spec contract, with zero executable code change"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ --filter Neo4jValidGraphRepositoryTests (30/30 passing, including both Diverge* Facts)"
        status: pass
      - kind: other
        ref: "dotnet build DG/src/DG.Core/DG.Core.csproj -c Release (0 errors); git diff -U0 non-comment-addition grep == 0; git diff --numstat both files == 0 deletions"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 09: parameters[] Dual-Wire-Shape Exclusion Contract Summary

**Documented the `parameters[]` dual-wire-shape divergence (flat numberValue/integerValue/booleanValue vs condensed {type,value}) as an explicit exclusion contract in spec/DATABASE.md and spec/EVIDENCE-CONTRACT.md, plus comment-only pointers at both C# reader sites — closing VERIFICATION.md gap 2 without touching any reader behavior.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-22T11:55:00Z (approx, first Read call)
- **Completed:** 2026-09-22T12:19:51Z
- **Tasks:** 3/3 completed
- **Files modified:** 4

## Accomplishments

- Added `#### Declared exclusion: parameters[] has two wire shapes and two readers (Phase 1202 plan 09, D-09, ALGN12-09)` subsection to `spec/DATABASE.md`'s ValidGraph section, placed immediately after the existing "Declared exclusion: legacy runs report `not_evaluated`" subsection. Names both wire shapes (flat vs condensed), states which reader is authoritative for which producer, describes the asymmetric failure modes (loud `InvalidOperationException` vs silent null), states the accepted cost, cites both pinning regression Facts by name, and lists what would force convergence.
- Amended the `:Run` section's `statePayloadJson` bullet with a pointer sentence to the new subsection.
- Added a short sibling subsection `### 5.2 Declared non-alignment: parameters[] wire shapes (Phase 1202 plan 09, D-09, ALGN12-09)` to `spec/EVIDENCE-CONTRACT.md`, cross-referencing the full contract in `spec/DATABASE.md` by heading name.
- Added comment-only pointer blocks at both divergent reader sites — `Neo4jValidGraphRepository.TryParseDesignState`'s inline v2 branch and `DesignStatePayloadV2Serializer.ParamFromDto` — each naming the site's own authority, the asymmetric failure mode, and citing the spec subsection plus both regression Fact names.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the parameters[] dual-wire-shape exclusion contract into spec/DATABASE.md** - `380f04b` (docs)
2. **Task 2: Cross-reference the exclusion in spec/EVIDENCE-CONTRACT.md** - `f289507` (docs)
3. **Task 3: Point the two divergent readers at the spec contract** - `c821d80` (docs)

_Sequential-mode execution: this executor owns STATE.md/ROADMAP.md updates itself (no worktree isolation for this run), per the orchestrator's explicit instruction._

## Files Created/Modified

- `spec/DATABASE.md` - New declared-exclusion subsection (60 lines, 1 deletion for the amended bullet); no other content touched.
- `spec/EVIDENCE-CONTRACT.md` - New short cross-reference subsection 5.2 (10 lines, 0 deletions); Phase 1200's frozen status vocabulary, envelope field table, and canonicalization rules untouched.
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` - Comment block added immediately before the existing v2-branch comment, citing spec + both Fact names (14 lines added, 0 deleted, 0 executable lines changed).
- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` - Comment block added immediately before `ParamFromDto`, citing spec + both Fact names (9 lines added, 0 deleted, 0 executable lines changed).

## CLAUDE.md § Schema Change Propagation Walk

Per the plan's Task 1 instruction, walked every listed propagation surface and recorded the judgment (all expected non-touches confirmed correct on inspection — no edit needed to any of them):

| Surface | Touched? | Reason |
|---|---|---|
| `ontology/dg-shapes.ttl` | No | SHACL shapes constrain graph structure and data integrity; this divergence is a JSON-internal wire-shape variance inside an opaque `statePayloadJson` string property that no SHACL shape inspects. No structural or data-integrity constraint changed. |
| `cypher_template.txt`, `training/dataset_schema.json`, n8n workflow prompts, `config.template.js` | No | No node label, relationship, or LLM-visible schema member changed; the divergence is entirely inside an existing sidecar string property (`statePayloadJson`'s `parameters[]` member). |
| `spec/SWRL-SUBSET.md` | No | No parser, builtin, or atom-type change. |
| `spec/RULE-PARTITION-POLICY.md` | No | No shift in the SWRL-vs-SHACL ownership line. |
| `spec/API.md` | No | No response envelope changes. |
| `spec/DG-ID.md` | No | No `dgId` minting, format, or identity-authority change. This exclusion concerns only the `parameters[]` JSON member inside `statePayloadJson`; `dgId` remains the platform-neutral identity it already defines, and neither wire shape alters how a parameter is bound to one. (Confirmed explicitly because `1202-CONTEXT.md`'s `<canonical_refs>` names `spec/DG-ID.md:15`/`:24` as surfaces this phase must respect.) |
| `README.md`, `.github/copilot-instructions.md` | No | Not named in the plan's own propagation-surface list for this task; the change is internal spec/code documentation, not a user-facing API or setup change. |

## Grep Evidence: Before/After Term Counts

Every term below was confirmed at **zero hits** in `spec/DATABASE.md` before this plan (stated verbatim in the plan's `<objective>` and verified independently before editing):

| Term | File | Before | After |
|---|---|---|---|
| `numberValue` | spec/DATABASE.md | 0 | 1 |
| `TryParseDesignState` | spec/DATABASE.md | 0 | 5 |
| `cg_paramstate_store` | spec/DATABASE.md | 0 | 1 |
| `DesignStatePayloadV2Serializer` | spec/DATABASE.md | 0 | 4 |
| `authoritative` (case-insensitive) | spec/DATABASE.md | (not required at 0, but confirmed non-zero after) | 5 |
| `silent` (case-insensitive) | spec/DATABASE.md | (not required at 0, but confirmed non-zero after) | 7 |
| `DivergeOnAcceptCandidateWriterEnvelope` | spec/DATABASE.md | 0 | 1 |
| `DivergeOnSerializerOwnConciseParameterShape` | spec/DATABASE.md | 0 | 1 |
| `statePayloadJson` | spec/DATABASE.md | 11 | 13 |
| `wire shape` (case-insensitive) | spec/EVIDENCE-CONTRACT.md | 0 | 3 |
| `Declared non-alignment` | spec/EVIDENCE-CONTRACT.md | 0 | 1 |

`spec/DATABASE.md` diff: 60 insertions, 1 deletion (the amended `statePayloadJson` bullet — low single digits, far below the file's total line count, as required).
`spec/EVIDENCE-CONTRACT.md` diff: 10 insertions, 0 deletions (genuinely additive, under the 25-line budget).

## Section 11 "Consistency & Propagation" (spec/EVIDENCE-CONTRACT.md)

Inspected per Task 2's conditional instruction. Section 11 is prose describing this document's coupling to other spec files (`spec/DATABASE.md`, `spec/evidence-contract.schema.json`, `spec/DG-ID.md`, `spec/SWRL-SUBSET.md`) and a propagation-review trigger — it does **not** maintain an enumerated list of declared exclusions or propagated decisions to append to. Left unmodified, as instructed for this case.

## No Executable Code Changed

Confirmed by three independent checks:
- `git diff -U0 <both C# files> | grep '^+' | grep -v '^+++' | grep -vc '^\+\s*(//|///|\*|/\*)'` returns `0` — every added line in both files is a comment.
- `git diff --numstat <both C# files>` shows `0` deletions in both files.
- `grep -c 'JsonSerializer.Deserialize<DesignState>' Neo4jValidGraphRepository.cs` returns exactly `1` — the inline reader remains present and unconverged.

## Build and Test Evidence

- `dotnet build DG/src/DG.Core/DG.Core.csproj -c Release` — 0 warnings, 0 errors.
- `dotnet test DG/tests/DG.Tests/ -v minimal --filter "Neo4jValidGraphRepositoryTests"` — 30/30 passing, including both `TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope` and `TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape`.
- `git diff --numstat DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` — empty output, confirming the test file is byte-unmodified (the two pinning Facts were not touched, renamed, or weakened).

## Decisions Made

- **Disposition:** documented exclusion (1202-03's option 3), not reader convergence (option 1) or writer-shape change (option 2). Zero risk to already-stored production data; satisfies the ROADMAP's "or an explicit exclusion contract" wording verbatim; matches the in-repo pattern plan 05 established for every other declared exclusion (geometry D-06, legacy-run `not_evaluated` D-11, immutable/mutable D-15). Not a one-way door — no `checkpoint:decision` needed, since no reader authority changed, only recorded.
- **Assumption-delta:** `add-alongside` (accepted debt) — the two readers remain split, promoted from undocumented accident to declared contract. What would force a later `promote` (full convergence): a third producer of v2 `parameters[]`; a consumer needing both producers' rows through a single code path; or a v3 payload version.
- Placed the new `spec/DATABASE.md` subsection immediately after "Declared exclusion: legacy runs report `not_evaluated`" (D-11), keeping all three declared-exclusion subsections in the ValidGraph section adjacent, matching the plan's explicit sibling-placement instruction.
- Numbered the `spec/EVIDENCE-CONTRACT.md` cross-reference `### 5.2` — the file's existing `### 5.1 Canonical per-object verdict source` sits directly above section 6, so `5.2` is the correct next sub-number in the surrounding scheme.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed; all `read_first` guidance matched the actual current code and spec state on inspection (no line-number drift required a fallback to grep-based location).

## Issues Encountered

None.

## Next Phase Readiness

- VERIFICATION.md gap 2 is closed: a written exclusion-contract entry exists in both `spec/DATABASE.md` and `spec/EVIDENCE-CONTRACT.md`, naming both wire shapes, both readers, which reader is authoritative for which producer, and the two machine-checked pinning Facts.
- No reader changed, no stored payload's interpretation changed — the accept-candidate-writer flat-shape rows already in Neo4j remain correctly parsed by the inline reader exactly as before this plan.
- This plan's own text (spec + code comments) is the durable record of what would force a future `promote` to full reader convergence, should a third producer or a v3 payload version ever appear.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*
