---
tags: [debugging, git, worktree, gsd, windows]
date: 2026-05-10
---

# Worktree Branch Commits with Spurious Deletions

## Problem

During Phase 05 execution, the GSD `gsd-executor` subagent for Plan 05-02 ran inside a git worktree (`isolation: "worktree"`). It returned with 4 atomic task commits (`e8cc560`, `5464f4c`, `9794a40`, `53897de`) on its branch `worktree-agent-ac3274cb17d07fe47`, plus a SUMMARY commit (`26eb5f1`).

Inspecting the commits revealed that EACH commit's diff contained:

- **Real intended changes** to `graph-viewer/model-viewer/*` files (correct).
- **Spurious deletions** of unrelated Phase 1-4 source files: `DG/src/DG.Core/Models/DesignStateParameter.cs`, `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs`, all of `DG/tests/DG.Tests/`, `data-service/tests/test_validation_runs_state.py`, etc. Total: 4,695 lines deleted across the 4 commits.

The branch's parent commit (`29e3146`) was correct — it included Phase 1-4 work. So the deletions were introduced by the agent's commits themselves, not by an old base.

A naive `git merge --ff-only worktree-agent-ac3274cb17d07fe47` succeeded as fast-forward and would have **destroyed all Phase 1-4 source code** had we not noticed and reset.

## Symptom Pattern

After spawning a worktree-isolated executor agent on Windows:

- `git log <worktree-branch>` shows expected commit messages.
- `git show --stat <commit>` reveals 100+ unrelated files marked as deletions per commit.
- `git diff <parent>..<commit>` shows the working tree of the worktree was NOT identical to its declared parent at commit time — it had been reset to an older state.

## Likely Root Cause

The GSD `execute-phase.md` workflow includes a `<worktree_branch_check>` block that runs FIRST in the spawned agent:

```bash
ACTUAL_BASE=$(git merge-base HEAD <EXPECTED_BASE>)
if [ "$ACTUAL_BASE" != "<EXPECTED_BASE>" ]; then
  git reset --soft <EXPECTED_BASE>  # rewrites branch pointer, keeps working tree
fi
```

This is supposed to fix a known Windows issue where `EnterWorktree` creates branches from `main` instead of the feature-branch HEAD. But `git reset --soft` only moves the branch pointer; it does NOT touch the working tree. If the worktree's checkout was already on a stale commit, the working tree still contains stale files — and when the agent runs `git add -A; git commit`, it captures the stale state as DELETIONS relative to the (now-corrected) parent.

In effect: the soft-reset patched the parentage but left a working tree that was missing Phase 1-4 files, so every commit "removed" those files.

## Recovery

1. **Don't merge the corrupt branch.** Reset master to before any orphan SUMMARY commit:
   ```bash
   git reset --hard <pre-summary-commit>
   ```
2. **Clear lingering merge state** if a previous merge attempt left it behind:
   ```bash
   rm .git/MERGE_HEAD .git/MERGE_MSG
   git reset HEAD
   git restore -- <corrupted-files>
   ```
3. **Cherry-pick by file, not by commit.** Use `git checkout <worktree-tip> -- <only-the-files-the-agent-was-supposed-to-touch>` to pull just the intended work onto master.
4. **Recommit as one consolidated commit** on master, with a clear message explaining the recovery path.
5. **Leave the worktree branch alive** until the agent process (locked by pid) exits, then `git branch -D worktree-agent-...`.

## Prevention

- After spawning a worktree executor, **inspect the first commit's `git show --stat`** before merging. If the file count or line count is suspiciously high relative to the plan's `files_modified`, treat the branch as suspect.
- Consider switching `git reset --soft` to `git reset --hard <EXPECTED_BASE>` in the worktree-base check (downside: loses any in-progress edits the agent had staged before the check ran, but that's safer than corrupting commits).
- For high-touch phases, prefer `workflow.use_worktrees: false` so executors run sequentially on the main working tree — no worktree branching means no chance of this divergence.

## Related

- [[Docker layer caching can serve stale index.html]]
- [[Browser cache prevents seeing UI updates after rebuild]]
