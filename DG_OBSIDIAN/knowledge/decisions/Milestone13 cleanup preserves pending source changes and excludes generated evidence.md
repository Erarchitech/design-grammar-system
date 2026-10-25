---
tags: [decision, git, phase-1309, pending-review]
date: 2026-10-25
status: owner-directed
---

# Milestone13 cleanup preserves pending source changes and excludes generated evidence

## Decision

Owner instruction on 2026-10-25:
- Back up the main working tree before reorganizing it.
- Continue framework development in the main folder on `gsd/milestone13`.
- Track only current graphify outputs (`graph.json`, `GRAPH_REPORT.md`, `manifest.json`), not caches/snapshots; do not track `evidence/public-*`.
- Commit Phase 1309 as-is, continue its completion on this branch; a WIP commit is not phase/recovery acceptance.
- Commit CLAUDE.md and AGENTS.md.
- Review old code/tests/spec provenance; decide admission later, not through blanket staging.

Applied: `5ba01a1`, `f17445e`, `4584e88`, `86b2502`, all pushed to `gsd/milestone13`. Only 458 verified unchanged archive pairs were admitted; 24 pairs with audit edits and their supporting unreviewed evidence remain pending. Do not silently commit env fixtures, PhD/manuscript/PDF downloads, generated bin/obj or unrelated editor/scratch files under the phrase “others per recommendation”.

## Rationale and boundaries

The tree contains work from multiple sessions and runtime evidence of differing provenance. A backup or historical test report does not constitute publication approval or fresh verification. Owner acceptance of the old product/spec/test set remains deferred after independent review found concrete issues.

Revit MCP commit/push was requested but inspection found identical HEAD/index/worktree content; no empty or fabricated child commit was made. Existing child revision is already on the fork.

Related: [[DeGram is developed in the submodule on degram-milestone13 and the build clone only pulls]], [[knowledge/debugging/Pending source review found stale v12 paths and duplicate MERGE rejection]], [[sessions/2026-10-25 Stand update and milestone13 consolidation]].
