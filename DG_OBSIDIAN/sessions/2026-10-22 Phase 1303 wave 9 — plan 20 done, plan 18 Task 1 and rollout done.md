---
tags: [session, phase-1303, gsd, d-54, d-57, d-60, d-61, dgopn-05, dgopn-06]
date: 2026-10-22
---

# Session: 2026-10-22 (evening) — Phase 1303 wave 9: plan 20 done, plan 18 Task 1 and rollout done

Worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp`. Model: claude-sonnet-5-5. Run through `/gsd-execute-phase 1303 --wave 9 Task 1`, then «continue plan 20, then plan 18's rollout». `workflow.use_worktrees=false`: each plan ran as a sequential `gsd-executor` on the main tree. Nothing pushed.

## What was done

- **Wave guard overridden on purpose.** Plans 06, 07 (wave 3) and 14 (wave 8) are still incomplete, which normally stops `--wave 9`. STATE.md records them as held (06 live demo open, 07 cut, 14 blocked on the owner's Revit) and names «20 then 18» as next, so the explicit `--wave 9` request was followed.
- **"Task 1" read as Task 1 only** for both wave-9 plans, first run: no SUMMARY, no STATE/ROADMAP change.
- **1303-20 complete** (3/3). Task 1: tests on top of WIP `24be756` (`913b5b0`; RED shown against the pre-WIP `dg_knowledge.py`, 3 new tests fail). Task 2: Russian shape keywords and ObjectProperty `domain` in existing entities (`7b19c5f` RED, `689ab0d` GREEN). Task 3: schema propagation (`bbaf667`). SUMMARY/STATE/ROADMAP `03178ad`. `ontology/dg-shapes.ttl` unchanged. DGOPN-06 stays open until plans 21–23.
- **1303-18 Task 1** (`ab41fcf` RED, `e38b2b3` GREEN): calculator review card, 5 API helpers, i18n in the Mapping panel. ui-v2 363/363, build ok. D-60: retired calculators never show Reject, «Подтвердить снова» only when `canRetire`.
- **1303-18 Task 2 (rollout, owner asked for it)**: `2a61d07` built `--no-cache` from `git archive` into `D:\dgb\mapping-release-2a61d07`; only `data-service` and `design-grammars` recreated (`dg-mapping-data-service:2a61d07`, `dg-mapping-ui:2a61d07`). Rollback tags `pre-1303-16` cut from what was actually running (`093ea13` data-service, `b7bcbf0` UI, not the `4cd7298` the plan named); rollback file `compose.mapping-rollback.yml` in the release folder. Probes: anonymous candidates/confirm 401, served code equals archive, 4 policy rows, UI bundle has «Review generated calculators», store probe 10/10 and 0 nodes left. Evidence `test/str-openings-01/evidence/promotion-rollout.json`, commit `0a03ad5`. Test guide «Шаг 8» and UAT test 13 added.
- **Nginx boundary tests fixed** (`2a61d07`): `/data-service/scripts/` (plan 15, 240 s read timeout, same upstream, no Authorization header) added to the allow-list in `test_static_proxy_boundary.py`. Closes the deferred item from 1303-16 and the open «decision needed» from the previous session.

## Decisions made

- Wave guard may be overridden when STATE.md records the lower-wave plans as deliberately held and the user names the wave explicitly.
- The scripts nginx location is intended, so the test allow-list was widened rather than the location removed.

## Issues encountered / open

- **Plan 18 Task 3 blocked:** `str-openings-01` has no company (companies: `v12-hexagonal-facade-01` UAT-A, `degram-uat-b` UAT-B). An admin must put `str-openings-01` and the second test project in the same company before steps 4/5 of the owner's script.
- **Deviation in 1303-20:** «не ближе» alone did not match the plan's own slab rule «не может быть ближе»; added «не может/должен/должна/должно быть ближе» (min_limit) and the «… быть дальше» mirror (max_limit). Still six shapes.
- **1303-18 i18n:** `en` map in `screens.js` may hold only plural tables and `error.*` texts, so only RU entries were added there; existing key `Reason: «Обоснование»` kept instead of the plan's «Причина» (owner may change).
- Unverified: whether the real LLM adds participants only when the rule names them; needs the live pass in 1303-23, and plans 19 and 20 must ship together.
- Baselines unchanged: 4 `test_dg_context` endpoint tests, `neo4j:7687` DNS errors, one `tools/de01` golden-fixture runner test.
- Open: plan 18 SUMMARY (after Task 3), plans 21–23, 06, 07, 14.

## Next

`/gsd-execute-phase 1303 --wave 10` (plans 21 and 22), after plan 20's live participant pass is understood to wait for 1303-23.
