---
name: Phase-35-Corpus-A-frozen-as-is-binaries-not-committed
tags: [phase-35, decision, corpus-a, frame-recovery, git-hygiene]
date: 2026-07-26
links: [sessions/2026-07-26 Phase 35 Wave 3 execution — two-tier orchestrator, Corpus B frozen, R4 defect found]
---

# Phase 35: Corpus A Frozen As-Is; Frame/Truss Binaries Not Committed

## Context

35-UAT.md asserted "there is no Frame `.gh` file on disk (whole-profile scan negative)." The architect located two candidate source files outside the scanned tree:

- `docs/Bridge_Truss_V4_OntologyMapping.gh` (126 KB)
- `docs/Truss_Joint_V4_RH7.3dm` (20.4 MB)

Both untracked, neither previously covered by `.gitignore`.

**Identity is plausible but not mechanically confirmed.** For: Corpus A's two procedures are named `2D Truss Configuration` / `2D Footer Configuration`, and the live few-shot fixture cites `Truss`/`Footer`/`DivideLine`. Against: `frame-cg-context.json` records `definition.fileName = "frame.gh"`, a different name — but that field carries little weight, since the fixture's whole `definition` block is synthetic (canonical Swagger placeholder `documentId`, a round-midnight `capturedAt`), i.e. hand-authored rather than captured. Confirming identity needs a live pull off the recovered file plus a node-GUID diff against the fixture — not done this session.

## Decision

**1. Corpus A is not re-grounded.** Plan 35-05 hand-repaired `frame-cg-context.json` (it arrived with 34 nodes and exactly 1 wire, both `_Proc` groups member-less). A live pull off the recovered file would replace that reconstruction with a real capture — but Corpus A is frozen (`contextSha256`, `frozenAtCommit`) and 35-11 is closed. The architect explicitly declined re-grounding; any future re-grounding is a new plan, not an edit to 35-11's output.

**2. Neither binary is committed.** `.gitignore` gained `*.gh` / `*.3dm`. Verified first that zero files matching either extension were tracked anywhere in the repo, so the rule shadows nothing existing. The `.3dm` alone is 20 MB — a committed binary of that size can only be removed from history by rewriting it, which is a much higher-cost mistake to walk back than leaving two files untracked on disk. Provenance (paths, sizes, the plausible-identity reasoning above) lives in `35-UAT.md`'s "Frame source recovered" section instead of in git objects.

## Consequences

- UAT test 1 (cold whole-canvas recognition on Frame) remains blocked on frontier-LLM access, but is no longer blocked on "no source file exists" — it's now merely unrun.
- If someone later wants Corpus A re-grounded on a live pull, or wants UAT test 1 run against the real Frame canvas, the files are on disk at the paths above (not in git) — check they still exist before assuming so.
- `*.gh`/`*.3dm` are now blanket-ignored project-wide. If a future phase needs to commit a Grasshopper source file on purpose, this rule will silently swallow `git add` unless overridden with `git add -f`.

## Related

- [[sessions/2026-07-26 Phase 35 Wave 3 execution — two-tier orchestrator, Corpus B frozen, R4 defect found|Session: Wave 3 execution]]
- [[debugging/Phase 35 R4 interface rule unreachable on live Grasshopper data|Debugging: R4 defect found during the same session]]
