---
phase: 1308-dg-web-ui
plan: "18"
subsystem: degram-workspace
tags: [submodule, gitlink, fork, workspace-verify]
requirements-completed: []
key-files:
  modified:
    - apps/degram
completed: 2026-10-13
status: complete-recorded-after-the-fact
---

# Plan 1308-18: Fork push and gitlink bump — recorded after the fact

**The component branch `degram/phase-1308` is on the public fork and the framework gitlink pins its head `c476c236ad04be8aa28f42410ed20f2e1372858e`; `workspace.py verify` exits 0, which closes the 1308-17 single-check waiver.**

## What happened

The plan's steps were carried out in the session of 2026-10-13 ("Browser language dropdown and DeGram host locale recheck"), not as a separate plan run:

- **Push (owner, Task 1 answer 1):** the owner pushed `degram/phase-1308` to `origin` (`https://github.com/Erarchitech/degram`) themselves; no agent push. Recorded in `DG_OBSIDIAN/sessions/2026-10-13 Browser language dropdown and DeGram host locale recheck.md`.
- **Gitlink (Task 1 answer 2, Task 2):** the gitlink moved `7edf519c` → `c476c236` inside the session commit `adc602b`, not in a dedicated commit `chore(1308-18): …` with only `apps/degram` staged as the plan specified. The deviation is cosmetic: the gitlink change in `adc602b` is exactly that one line, and the pinned object was on the fork before the commit.

The branch holds exactly the two authorized component commits on top of `7edf519c`: `5f1d3aa8` (1308-17, Projects sidebar row) and `c476c236` (1308-21, single language setting).

## Verification (2026-10-13, re-run when this record was written)

| Check | Result |
|---|---|
| `git -C apps/degram ls-remote origin degram/phase-1308` | `c476c236ad04be8aa28f42410ed20f2e1372858e` |
| `git -C apps/degram rev-parse HEAD` | `c476c236ad04be8aa28f42410ed20f2e1372858e` |
| `git ls-tree HEAD apps/degram` | `160000 commit c476c236…` |
| `python tools/degram/workspace.py verify` | exit 0, every check green |

The transitional waiver recorded in 1308-17 (`gitlinkCommit ≠ componentHead` only) is **closed**.

## Limits

- D-44 holds for this plan: no installer build, Desktop launch, `hermes update` or installed-profile write was part of it. The later local build of `c476c236` for the owner's DeGram UAT is a separate, separately authorized step (recorded in `1301-BUILD.md`).
- WEBUI-06 and WEBUI-01 stay open until the live DeGram check (sidebar «Projects» row, language switch) passes.
