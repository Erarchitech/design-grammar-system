---
tags: [decision, gsd, workflow, git, worktrees]
date: 2026-06-23
---

# Decision: Disable GSD Worktree-Isolated Execution

## Decision

`.planning/config.json` now has `workflow.use_worktrees: false`. GSD's `/gsd-execute-phase` runs sequentially on the main working tree instead of forking parallel git worktrees per plan.

## Rationale

This project also has `commit_docs: false` (planning docs — PLAN/CONTEXT/PATTERNS/RESEARCH — are deliberately left uncommitted; the user controls commit timing). But `git worktree add` forks from the last *commit*, not the working tree, so a freshly-written, uncommitted PLAN.md is invisible inside a forked worktree. Both Wave 1 executors for v3.0 Phase 7 (07-01, 07-02) hit this independently and correctly halted with a blocker report rather than attempting to self-recover across the worktree boundary (per GSD's worktree isolation contract — a sub-agent must not commit in the main repo or copy files across worktree boundaries on the orchestrator's behalf).

Two fixes were possible: (a) commit planning docs before each execute-phase dispatch, or (b) disable worktree isolation entirely. The user chose (b) to keep `commit_docs: false` fully honored.

## What This Means Concretely

- Execution loses wave-level parallelism — plans within a wave that could have run concurrently in isolated worktrees now run one at a time on the main tree.
- This is the right tradeoff only as long as `commit_docs: false` holds. If a future session wants parallel worktree execution back, planning docs need to be committed before each `execute-phase` dispatch — re-evaluate both settings together, or the same deadlock recurs.

## Surfaced During

`/gsd-autonomous` v3.0 Phase 7 execution, 2026-06-23. See [[sessions/2026-06-23 v3.0 Phase 7 Schema Foundation execution|session note]].
