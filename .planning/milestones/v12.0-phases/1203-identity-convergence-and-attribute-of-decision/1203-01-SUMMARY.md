---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 01
subsystem: testing
tags: [pytest, xunit, neo4j, shacl, identity, dgid, preflight]

requires: []
provides:
  - "Verified observed test-suite baselines (Python 819/4/25, C# 552/4) superseding the stale 1202-era '823 passed / 1 pre-existing-failed' figure"
  - "Full repo-wide identity-literal blast-radius inventory (90 hits) for D-08/D-09, classified by role"
  - "Answer to RESEARCH.md Open Question 1: canonical-vectors.json carries dg: literals (frozen Object dgIds), no OS_/DS_/PS_ literal"
  - "WR-02 relocated to spec/DATABASE.md:518 with two concrete verb mismatches identified against app.py"
  - "True SHACL shape count (17), correcting both CONTEXT.md (20) and RESEARCH.md (18)"
  - "Observed Atom_Id-suffix-to-type convention from cypher_template.txt backing D-04"
affects: ["1203-02", "1203-03", "1203-04", "1203-05", "1203-06"]

tech-stack:
  added: []
  patterns: ["read-and-record preflight gate before an irreversible re-derivation phase"]

key-files:
  created:
    - .planning/phases/1203-identity-convergence-and-attribute-of-decision/1203-PREFLIGHT.md
  modified: []

key-decisions:
  - "Recorded true baseline (819 passed/4 failed/25 errors Python; 552 passed/4 failed C#) as a correction to VALIDATION.md's cited prior figure, rather than silently reconciling to it"
  - "Recorded true SHACL shape count as 17, correcting both prior claims (CONTEXT.md 20, RESEARCH.md 18) instead of picking one"
  - "Relocated WR-02 to spec/DATABASE.md:518 (PATCH vs POST /identity/bind, and POST vs GET /identity/{dgId}/representations) rather than accepting the stale :336 citation"
  - "Surfaced (not resolved) a blocking question for plan 02/03: whether D-09's length-prefix fix touches the frozen fixture dgIds in fixtures/golden/, which would conflict with the MANIFEST.md freeze policy"

patterns-established:
  - "Preflight plans must classify every failure/error explicitly as documented-environment-dependent or unexplained before an irreversible change proceeds"

requirements-completed: [ALGN12-12, ALGN12-13, ALGN12-14]

coverage:
  - id: D1
    description: "Observed baseline counts for both test suites captured before any source edit"
    requirement: "ALGN12-12"
    verification:
      - kind: other
        ref: "python -m pytest data-service/tests -q (819 passed/4 failed/1 skipped/8 deselected/25 errors)"
        status: pass
      - kind: other
        ref: "dotnet test DG/tests/DG.Tests/ -v minimal (552 passed/4 failed/556 total)"
        status: pass
    human_judgment: false
  - id: D2
    description: "canonical-vectors.json identity-literal presence answered with grep evidence"
    requirement: "ALGN12-13"
    verification:
      - kind: other
        ref: "grep -nE identity-literal-regex fixtures/golden/canonical-vectors.json (2 matches, both frozen Object dgIds)"
        status: pass
    human_judgment: false
  - id: D3
    description: "WR-02 defect relocated to spec/DATABASE.md:518 with evidenced verb mismatches"
    requirement: "ALGN12-14"
    verification:
      - kind: other
        ref: "grep -n /identity/ spec/DATABASE.md + grep -n @app.*/identity data-service/app.py (line-by-line comparison table)"
        status: pass
    human_judgment: false
  - id: D4
    description: "True sh:NodeShape count recorded in ontology/dg-shapes.ttl"
    requirement: "ALGN12-14"
    verification:
      - kind: other
        ref: "grep -c 'a sh:NodeShape' ontology/dg-shapes.ttl (17)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Repo-wide identity-literal blast-radius inventory enumerated and classified"
    requirement: "ALGN12-12"
    verification:
      - kind: other
        ref: "grep -rn identity-literal-regex . (90 hits, classified into 5 categories in 1203-PREFLIGHT.md § 2)"
        status: pass
    human_judgment: false

duration: 35 min
completed: 2026-09-22
status: complete
---

# Phase 1203 Plan 01: Preflight Baseline Summary

**Established the verified pre-change baseline for phase 1203's irreversible identity re-derivation: observed suite counts (819/4/25 Python, 552/4 C#), a 90-hit identity-literal blast-radius inventory, WR-02 relocated to `spec/DATABASE.md:518`, and the true SHACL shape count of 17 — correcting three stale figures cited in prior planning artifacts.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-22T00:00:00Z (approx, session start)
- **Completed:** 2026-09-22
- **Tasks:** 2
- **Files modified:** 1 created (`1203-PREFLIGHT.md`)

## Accomplishments

- Ran both full test suites live and recorded verbatim summary lines, classifying every failure/error as documented environment-dependent (Neo4j unreachable from host) — zero unexplained failures found in either suite
- Discovered and recorded that the previously-cited 1202-era baseline ("823 passed / 1 pre-existing-failed") no longer matches reality; the true count is 819 passed / 4 failed / 25 errors (Python)
- Inventoried all 90 repo-wide identity-literal hits (`dg:`, `OS_`, `DS_`, `PS_` 16-hex forms), classifying them into known test pins, frozen-fixture literals, illustrative doc examples, and deliberately-fake sentinels
- Answered RESEARCH.md Open Question 1: `fixtures/golden/canonical-vectors.json` DOES carry `dg:` literals (the two frozen Object dgIds it describes), closing an open verification item with a correction rather than an assumption
- Surfaced a previously undetected blocking question for plans 02/03: whether D-09's length-prefix fix touches the same hash-input encoding used for the frozen `fixtures/golden/` fixture dgIds, which would conflict with the fixture freeze policy in `fixtures/golden/MANIFEST.md`
- Relocated WR-02 from the stale `spec/DATABASE.md:336` citation to its real location at line 518, identifying two co-located verb mismatches (`PATCH` vs. actual `POST /identity/bind`; `POST` vs. actual `GET /identity/{dg_id}/representations`)
- Recorded the true SHACL shape count (17), contradicting both CONTEXT.md's claim of 20 and RESEARCH.md's claim of 18
- Recorded the observed `Atom_Id` suffix→`type` convention from `cypher_template.txt` (`_A2` and `_H1` both map to `DataPropertyAtom`), the factual basis plan 04 needs for the D-04 attachment rule

## Task Commits

1. **Task 1: Capture both suite baselines and the identity-literal blast radius** - `0b612bf` (docs)
2. **Task 2: Relocate the WR-02 defect and record the D-04 attachment decision inputs** - `0b612bf` (docs, same commit — both tasks landed in a single atomic commit to the one output file)

**Plan metadata:** (this SUMMARY commit, following)

## Files Created/Modified

- `.planning/phases/1203-identity-convergence-and-attribute-of-decision/1203-PREFLIGHT.md` - Observed baseline record: suite counts, identity-literal inventory, WR-02 location, SHACL shape count, D-04 atom-type convention

## Decisions Made

- Recorded three explicit corrections rather than reconciling silently: (1) the true test-suite baseline diverges materially from the cited 1202 figure, (2) the true SHACL shape count (17) matches neither CONTEXT.md nor RESEARCH.md, (3) canonical-vectors.json is not literal-free as RESEARCH.md's open question implied it might be.
- Chose to surface (not resolve) whether D-09 conflicts with the `fixtures/golden/` freeze policy — this preflight plan is read-and-record only per its own prohibitions, so the actual resolution is deferred to whichever later plan implements D-09.

## Deviations from Plan

None - plan executed exactly as written. Both tasks landed in the read-and-record scope with no source, spec, ontology, or fixture file touched.

## Issues Encountered

None. All classification and evidence-gathering completed without ambiguity requiring escalation. The single noteworthy finding (potential D-09/fixture-freeze conflict) was explicitly a "surface for downstream plans" item per the task 2 action text ("recording it here means the rule rests on an observed convention"), not an issue blocking this plan's own completion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plans 02-06 now have a verified, observed baseline to work from instead of re-deriving or trusting stale figures:
- Plan 02 (identity re-derivation) has the full blast-radius inventory and the fixture-freeze conflict question to resolve
- Plan 03 (test suite updates) has the true pre-change baseline to diff against
- Plan 04 (D-04 attachment) has the observed atom-type convention
- Plan 05 (WR-02 / API docs fix) has the exact line number and both mismatches, plus the `spec/API.md` first-write status

No blockers identified. The one open question this plan surfaces (D-09 vs. fixture freeze) is explicitly not blocking for this plan — it is a decision input for whichever later plan implements D-09.

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Completed: 2026-09-22*

## Self-Check: PASSED

- `1203-PREFLIGHT.md` exists on disk: confirmed
- `1203-01-SUMMARY.md` exists on disk: confirmed
- Commit `0b612bf` found in `git log --oneline --all`: confirmed
- All task acceptance criteria re-verified via grep (see PREFLIGHT.md § verification commands): all pass
- `git status --porcelain` scoped outside the phase directory shows only pre-existing changes (`.planning/STATE.md`, DG.Core/DG.Grasshopper build artifacts, graphify-out cache, DG_OBSIDIAN notes) that predate this plan's execution — confirmed no source/spec/ontology/fixture file was modified by this plan
