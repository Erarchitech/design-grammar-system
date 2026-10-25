---
tags: [decision, degram, git, milestone13]
date: 2026-10-25
---
# DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls

## Owner decision (2026-10-25)
Development continues on new branches: framework `gsd/milestone13` (from `master`), component `degram/milestone13` on the fork `Erarchitech/degram`. Everything that was ready was merged into `master` first.

## Why
Three DeGram checkouts had drifted apart and it was unclear where DeGram was developed:
- `apps/degram` (submodule, `.git/modules/degram`): the pinned component, gitlink `c476c236` on `degram/phase-1308`.
- `D:\dgb\src`: build clone made on 2026-10-05 from the submodule (shallow, `origin` = the submodule path) to build installers from a commit, not from a working tree. From 2026-10-18 the Phase 1303 mapping work was committed **directly there** on `feature/mapping-mvp`: 4 commits (`93997683`, `1aa3b39c`, `38d3e7e7`, `b619e02e`) existed nowhere else, while the running mapping DeGram was built from them.
- `C:\Users\Admin\source\repos\degram`: separate clone of the fork from 2026-10-11, branch `main` (upstream mirror `8b66a51`), without any DeGram code. Not a working base; why it was made is not recorded.

## What was done (2026-10-25)
1. `feature/hosting-dg-pilot` merged into `master` (`6ca8c5c`; the mapping branch was already in `master`).
2. The 4 build-clone commits fetched into the submodule as `degram/milestone13` (fast-forward of `c476c236`, scanned for secrets and private paths: none) and pushed to the fork.
3. `master` gitlink `apps/degram` moved from `c476c236` to `b619e02e`.

## Rules from now on
- Component source changes are committed **only in the submodule** on `degram/milestone13` (or a branch made from it), pushed to the fork with explicit authorization, then the framework gitlink is bumped on `gsd/milestone13`.
- `D:\dgb\src` is **build-only**: `git -C D:/dgb/src pull origin degram/milestone13` before a build; never commit there. If it ever holds a commit again, fetch it into the submodule before anything else.
- `C:\Users\Admin\source\repos\degram` is not used for DeGram work; its removal is the owner's call.
- `degram/phase-1301` and `degram/phase-1308` stay on the fork as history; they are not moved.

See [[degram/index]], [[degram/Repository topology]], `spec/degram/WORKSPACE.md`.
