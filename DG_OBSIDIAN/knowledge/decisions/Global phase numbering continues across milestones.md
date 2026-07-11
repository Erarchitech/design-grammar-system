---
tags: [decision, planning, gsd]
date: 2026-07-11
---

# Decision: Global phase numbering continues across milestones

## Decision

Phase numbers in `.planning/` are **global and continuous**, not reset per milestone. v7.0 was Phases 13-20, v8.0 is Phases 21-27, v9.0 is Phases 28-40, v10.0 is Phases 41-49. When a new milestone is created (`/gsd-new-milestone`), its phases must start at `(highest existing phase number) + 1`, never at 1.

## Rationale

Per-milestone-local numbering (each milestone starting its phase count at 1) caused ambiguity — "Phase 5" could mean five different things depending on which milestone's ROADMAP you were reading, and archived milestones' phase directories collided in naming pattern even though they never collided in practice (they live in separate `milestones/vX.Y-phases/` dirs). Global numbering makes phase references unambiguous in conversation, in commit messages, and across cross-milestone dependency notes (e.g. v10.0 phases referencing specific v9.0 phases by number).

## How to apply

- Before creating a new milestone's ROADMAP/REQUIREMENTS, check the highest phase number used by any shipped, paused, or planned milestone (search across `ROADMAP.md` + `milestones/*-ROADMAP.md`).
- **v4.0 BOT Ontology Bridge is still on the old milestone-local convention** ("Phases 1-4") — it predates this convention being made explicit and was out of scope for the 2026-07-08/2026-07-11 renumbering work. It will need renumbering (likely starting at 50) whenever it's activated. See [[sessions/2026-07-11 v9.0-v10.0 global phase renumbering|session note]].
- When renumbering an existing milestone's phases (as done for v9.0/v10.0), rename phase directories with `git mv` to preserve history, then sed-sweep all cross-references (ROADMAP, REQUIREMENTS traceability tables, CONTEXT/RESEARCH internal links, MILESTONES.md, main ROADMAP.md, STATE.md, PROJECT.md) — verify with a final grep for stale numbers before committing.
