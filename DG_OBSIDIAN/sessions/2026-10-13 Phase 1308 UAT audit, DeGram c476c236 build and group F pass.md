---
tags: [session, degram, phase-1308, uat]
date: 2026-10-13
---
# Phase 1308 UAT audit, DeGram c476c236 build and group F pass

## Outcome

- **UAT audit.** `/gsd-audit-uat` found no UAT/VERIFICATION files anywhere; for 1308 the open items were plans 18–20 and the human backstops of plans 11, 14, 15, 17, 21, 22. A step-by-step test plan (groups 0, A–F) was written. Stale items found: plan 18 was already done (fork = gitlink = `c476c236`, `workspace.py verify` exit 0, gitlink bumped inside `adc602b`); plan 19's bundle marker «Грамматика.» no longer exists after the SVOD rebrand; plan 20's RU visual pass predates the browser dropdown amendment (D-07/D-08/D-53).
- **Plan 18 recorded** after the fact: `1308-18-SUMMARY.md`; the 1308-17 waiver is closed.
- **Plan 19 corrected:** the stale-image check now looks for «Свод правил проекта».
- **DeGram build for UAT.** Owner-authorized `win-unpacked` from `c476c236` via the clean clone `D:\dgb\src` and `D:\dgb\run-build.sh` (21:23–21:35Z, exit 0); stamp `dirty: false`; `app.asar` SHA-256 `ea34886f…9d62`. The builder still names it 0.1.11, so the earlier 0.1.11 artifacts were renamed `*-0.1.11-7edf519c` first. Record: `1301-BUILD.md` "1308 UAT build".
- **Group F passed** (owner): language list, live switch, no in-DeGram dropdown, sidebar «Проекты», hosted Connectors, in-app RU review (replaces the D-54 automated gate). Recorded in `1308-UAT.md`.

## Not done

- **Phase 1308 is not closed.** Plans 1308-19 (rebuild from `git archive HEAD`, D-32 closure) and 1308-20 (backup, dry run, apply token retirement and UAT account cleanup) have not run: no `1308-ROLLOUT.md`, `data-service` still on the untagged image `f98c3b8e3709`. The owner asked to close the phase; closure waits for these two plans and their "rebuild ok" / "apply ok".
- The in-session dry run of `d49_store_cleanup.py` (read-only without `--apply`) was refused by the auto-mode classifier; it was not retried.
- Groups C–E have no recorded results: the owner's «Все группы до F подтверждаю» came before the tests and was taken as plan approval.
- ROADMAP/STATE checkboxes for 15, 17, 18, 22 were not touched (those files hold other sessions' staged edits).

## Resume

1. `/gsd-execute-phase 1308` for plan 19: dry run → show Build plan → "rebuild ok" → build, probes, in-container suite.
2. Plan 20: backup → dry run → "apply ok" → apply with data-service stopped → verify; owner actions D-48 (grant `asiyagerey94` on `degram-uat-c`, plugin rebuild).
3. Groups C–E against the rebuilt stack; then `/gsd-verify-work 1308` and phase verification.
