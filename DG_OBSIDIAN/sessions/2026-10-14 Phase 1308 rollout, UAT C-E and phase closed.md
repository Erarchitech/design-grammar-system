---
tags: [session, degram, phase-1308, rollout, uat, verification, security]
date: 2026-10-14
---
# Phase 1308 rollout, UAT C–E and phase closed

## Outcome

- **Plan 1308-19 (rebuild, D-32, D-45/D-46).** D-32 closed against the running image: `degram_policy.py` hash equals HEAD (`db776292…`), the default policy for an unknown project is export allowed / whole-definition refused. Clean export `git archive HEAD data-service ui-v2` → `C:\dgsrc1308`; the 12 uncommitted working-tree files of other sessions were listed and kept out. After the owner's "rebuild ok": tree-hash gate passed, `docker build --no-cache` → data-service `c1e018ee…`, design-grammars `3b790ebb…`, recreated with `compose up -d --no-build --no-deps`; running ids equal the built ids. `app.py` has 5 × `auth/connector-session`; the served chunk carries «Свод правил проекта», no «Грамматика.». Six unauthenticated probes → 401 `AUTH_REQUIRED`, UI 200.
- **In-container suite.** 5249 passed, 13 failed, 296 errors — all environmental: unmounted repo-root `/fixtures`, `/spec`, `/tools`, and 295 C#-factory tests that need `dotnet`, which the data-service image never had. The old "1130 passed" baseline is obsolete. 1308 test files: 3234 passed, 2 env failures.
- **Plan 1308-20 (D-47/D-49 cleanup).** Verified backup of all 19 stores in `C:\dgbackup1308\20261013T223918Z\` (sha256 19/19, `SHA256SUMS.txt`). Neo4j has 0 nodes for `uat-pw-bd30ce`. The owner ran the dry run and the apply from PowerShell (the agent's `docker exec` was refused by the auto-mode classifier): 13 credentials retired (`retired: "D-49"`, 11 already revoked; two more than at plan time), 1 user, 1 membership, 1 pairing removed; `applied`, exit 0; post-apply dry run `nothing-to-do`. Neo4j, graphs, validation runs and non-auth stores untouched. Record: `1308-ROLLOUT.md`.
- **UAT** 11/11: groups A and B from the rollout evidence, C (browser RU/EN visual), D (roles and connector access with real accounts), E (Grasshopper CONNECTOR account sign-in) passed by the owner on the rebuilt stack.
- **Verification** (gsd-verifier): 191/191 plan truths, 11 owner overrides, 11/11 WEBUI. Owner decisions: WEBUI-01 reworded to the UAT amendment (DeGram setting; own RU/EN dropdown in a plain browser, choice saved, browser language as default); the 1308-18 gitlink bump inside the mixed commit `adc602b` accepted as an override.
- **Security** (gsd-security-auditor, ASVS L1, block on high): 92/92 threats closed, 3 accepted risks logged, `threats_open: 0` → `1308-SECURITY.md`.
- **Phase 1308 closed**: ROADMAP (phase and all 24 plans ticked), REQUIREMENTS (WEBUI-01..11), STATE (phase complete). CONTEXT D-03 and UI-SPEC copy rows now carry SVOD / «Свод правил проекта» and ALNST/Tektur instead of «Грамматика.» / «Граф правил проекта.»; PLAN/SUMMARY/RESEARCH keep the original strings as history.

## Decisions

- WEBUI-01 text follows the owner's UAT amendment (D-07/D-08/D-53) rather than the original "no switcher in the Web UI".
- The 1308-18 commit-shape deviation is accepted; history is not rewritten.
- Running the apply from PowerShell after reviewing the dry-run counts is the approval of record for plan 20.

## Not done

- GSD transition step "evolve PROJECT.md" skipped: PROJECT.md holds other sessions' unstaged edits. STATE keeps `current_phase: 1308` (complete) instead of switching to 1309, which runs in a separate session.
- `C:\dgsrc1308` (export) and `C:\dgbackup1308\…` (backup) are left in place.
- The DeGram RU completeness test (`ru-catalog-completeness.test.ts`, 1/66) is still red in the component; accepted via the in-app review.
- ALNST web-embedding licence still open before any public deployment.

## Commits

`26fa79f`, `d273e72` (plan 19), `3c4c631` (plan 20), `99c2801` (UAT), `05f8a89` (verification and phase close), `5376020` (security), plus the session commit. ROADMAP/REQUIREMENTS/STATE and vault home files were committed through a temporary index so the 1309 session's staged hunks stay staged.

## Related

- [[sessions/2026-10-13 Phase 1308 UAT audit, DeGram c476c236 build and group F pass]]
- [[knowledge/decisions/Service images are rebuilt from a clean git export of HEAD, not the dirty working tree]]
- [[knowledge/decisions/Connector access is a per-connector grant without tokens, owner and admin exempt (D-49)]]
- [[knowledge/decisions/SVOD name, ALNST and Tektur design system, drawn landing hero]]
