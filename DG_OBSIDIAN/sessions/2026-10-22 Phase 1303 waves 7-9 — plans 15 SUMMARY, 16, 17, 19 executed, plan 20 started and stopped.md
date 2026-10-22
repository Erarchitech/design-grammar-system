---
tags: [session, phase-1303, gsd, d-54, d-61, dgopn-05, dgopn-06]
date: 2026-10-22
---

# Session: 2026-10-22 — Phase 1303 executed in waves: 1303-15 SUMMARY, 16, 17, 19 done; 1303-20 started and stopped

Worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp`. Model: claude-sonnet-5-5. Work was run through `/gsd-progress` and `/gsd-execute-phase 1303 --wave N`; `workflow.use_worktrees=false`, so every plan ran as a sequential `gsd-executor` on the main tree. Nothing pushed, nothing deployed, no Docker operation, no DG.gha install.

## What was done

- **Routing.** Progress report: STATE.md was stale (`current_plan: 14`, no 15–23). GSD wave numbers come from the dependency graph, not from the `wave:` frontmatter: index wave 7 = 13/16/19, 8 = 14/17, 9 = 18/20, 10 = 21/22, 11 = 23. `--wave 10` was refused (earlier waves incomplete).
- **1303-15 SUMMARY reconstructed** (`b550d71`), `status: partial`. Implemented and run live (313 boxes, 4 runs), but gold, inventory, run1, PROTOCOL «Акт 4», TEST-GUIDE step and UAT test 13 do not exist. DGOPN-01..04 are **not accepted**.
- **1303-16 done** (`0448848`, `1b8dba3`, `e60d5e7`, `35036b5`): store half of D-54 (integrity check of stored code, review-preserving save, blocked-hash read, company catalogue confirm/reject/retire with owner gate). 209 plan tests green.
- **1303-19 done** (`2ed3102`, `71ca2c8`, `8a51f14`, `0424611`): C# half of D-61. `RuleVariableRoles`, context-only participants are not bound, are answered as matched, and are disclosed in the Passed/Failed message. 21 new tests; SWRL-SUBSET updated.
- **1303-17 done** (`08bd4d7`, `7819c9a`, `c707b1f`, `9f6cdd7`): resolution order file → company → project-stored → LLM, company vocabulary merged into a deep copy, four routes (`candidates`, `confirm`, `reject`, `retire`) with route-policy rows (129 → 133 routes). 211 tests green on rerun.
- **STATE.md tracking** fixed by hand (`98a7f51`): 14 of 23 plus 15 partial.
- **1303-20 started, then stopped by request.** The executor had been running about 1 minute. It left one uncommitted edit to `data-service/dg_knowledge.py` (the `computable_form` convention now allows participant classes and adds a `participants_example`). Committed separately as a WIP, not as plan completion.

## Decisions made

- GSD wave order is by dependency; the plan 1303-14 checkpoint (owner installs pyRevit, opens the model copy, signs in) is not given to an executor.
- A rollout is never started from a wave command. 1303-18 Task 2 rebuilds and recreates `data-service` and `design-grammars` on the running stack, so it waits for an explicit owner «yes».

## Issues encountered / open

- **WIP in `dg_knowledge.py`.** `test_computable_form_convention_steers_rules_to_one_numeric_subject_property` fails on purpose-to-be: it still asserts the old one-class wording. Plan 20 has to update that test and finish the rest (`dg_context.py`, `cypher_template.txt`, `training/dataset_schema.json`, spec rows, `.github/copilot-instructions.md`, `README.md`, `test_cypher_allowlist.py`). Review the WIP before building on it.
- **Two nginx tests fail** (`test_static_proxy_boundary.py`: `unexpected-proxy-location:/data-service/scripts/`), caused by plan 15 commit `4b03c61`. Logged in `deferred-items.md`; the owner decides whether to allow the location in the test or remove it.
- `DG.Tests.FrameAblatedCorpusEmitterTests.EmitFrameAblatedCorpus_MatchesCommittedGoldenFiles` fails in this worktree because `FindRepoRoot` looks for a `.git` directory and a linked worktree has a `.git` file. Environmental, not caused by these plans. Not fixed.
- Known baselines unchanged: 4 `test_dg_context` endpoint tests, `neo4j:7687` DNS errors, 4 `DesignStateValidationFlowTests`.
- The roadmap tool overwrites the long 1303 «Plans» line and the 1303 table row each time; executors restored them. ROADMAP marks 1303-15 `[x]` although its SUMMARY is `partial`.
- Research assumptions A1 (objectRef → Revit box mapping) and A2 (a `send=true` run carries propStates) are tested on canned payloads only; confirm them in 1303-18.

## Next steps (in order)

1. Resume **1303-20**: `/gsd-execute-phase 1303 --wave 9`, but tell the executor about the WIP commit and let it finish and test it (or revert it if it disagrees). Do not hand it 1303-18.
2. **1303-21** and **1303-22** (wave 10, both need 17 and 20), then **1303-23** (owner acceptance on `str-openings-01`).
3. **1303-18**: Task 1 (Web UI panel) is local. Task 2 is the live rollout (git archive, `pre-1303-16` rollback tags, rebuild, recreate two services) and Task 3 is the owner's acceptance in the UI. Needs the owner present and an explicit «yes».
4. Close the tail of **1303-15**: rerun the check from DeGram, confirm boxes 4747124 and 4747406 in Revit, record gold, run1, PROTOCOL, guide step, UAT test 13.
5. **1303-14** stays blocked on the owner (pyRevit, Revit, sign-in).
6. Decide the nginx location test.

Not authorized: push, merge with 1309, Docker or deployment, DG.gha installation, paid LLM calls.

## Related notes

- [[sessions/2026-10-21 Multi-participant rules design, plans 1303-19 to 23 and Graph Viewer cap fix|design session for D-61…D-65]]
- [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR|plan 15 session]]
- [[knowledge/decisions/Multi-participant rules keep one subject and assert the other classes as context (Phase 1303, D-61 to D-65)|decision D-61…D-65]]
- `.planning/phases/1303-pravilo-gh-obekt/` (`1303-16-SUMMARY.md`, `1303-17-SUMMARY.md`, `1303-19-SUMMARY.md`, `deferred-items.md`)
