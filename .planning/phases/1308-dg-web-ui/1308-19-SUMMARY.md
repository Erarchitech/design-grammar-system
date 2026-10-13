---
phase: 1308-dg-web-ui
plan: "19"
subsystem: rollout
tags: [docker, rebuild, git-archive, d-32, probes]
requirements-completed: []
key-files:
  created:
    - .planning/phases/1308-dg-web-ui/1308-ROLLOUT.md
completed: 2026-10-13
status: complete
---

# Plan 1308-19: D-32 closure and rebuild from a clean export of HEAD

**D-32 is closed on evidence, and `data-service` and `design-grammars` now run images built with `--no-cache` from a `git archive HEAD` export; probes and the in-container suite show no regression.**

## What was done

- **D-32 (D-45, D-05):** `degram_policy.py` in the running image hash-equals HEAD (`db776292…`, CR removed); `policy_for_project('zz-1308-probe')` → `providerExportAllowed: True`, `wholeDefinitionAllowed: False`.
- **Dry run (Task 1, commit `26fa79f`):** HEAD `42a9ead`, trees `HEAD:data-service` = `b787ca84…`, `HEAD:ui-v2` = `9b2c05e4…`; export `C:/dgsrc1308`; 8 modified + 4 untracked working-tree files from other sessions listed as excluded; no container restarted.
- **Approval (Task 2):** owner "rebuild ok".
- **Build (Task 3):** tree gate passed at the start (trees equal the Build plan; HEAD had moved to `26fa79f` only). New images `data-service` `sha256:c1e018ee…`, `design-grammars` `sha256:3b790ebb…`; both containers recreated with `compose up -d --no-build --no-deps` and run exactly these ids; neo4j untouched.

## Verification

| Check | Result |
|---|---|
| `grep -c auth/connector-session /app/app.py` | 5 |
| Served bundle contains «Свод правил проекта» | yes (`PropertiesTable-DmQGXmWU.js`), no «Грамматика.» |
| 3 unauthenticated probes × 2 bases | 401 `AUTH_REQUIRED` (6/6) |
| UI `:8080/` | 200 |
| In-container suite | 5249 passed, 13 failed, 296 errors — all environmental (repo-root `/fixtures`, `/spec`, `/tools` not in the image; `dotnet` absent from the image) |
| 1308 test files (28) | 3234 passed, 2 failed (environmental, `test_degram_relay.py` spec file) |

## Deviations

- The plain `pytest tests -q` stops at collection on `test_freeze_rule_ingest_prompts.py` (unmounted fixture); the suite was run with `--continue-on-collection-errors`.
- The recorded baseline (1130 pass + 13 env failures) is stale: the suite has grown to 5249 passing, and 295 setup errors come from C#-factory tests (added 2026-09-30) that need `dotnet`, which the data-service image has never had. Both are environmental; the baseline memory should be updated.
- The UI string check found «Свод правил проекта» in a lazily loaded chunk, not the entry bundle.

## Limits

No other service, volume or store was touched. The cleanup script `d49_store_cleanup.py` now ships in the running image for plan 1308-20.
