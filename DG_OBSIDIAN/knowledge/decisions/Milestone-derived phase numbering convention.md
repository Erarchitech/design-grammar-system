---
tags: [decisions, phase-numbering, milestone]
date: 2026-07-11
---

# Milestone-derived phase numbering convention (vX.Y → X·100+Y·10)

**Decision:** GSD roadmap phases are numbered per-milestone as `<major><minor>0`-based blocks — milestone vX.Y gets phases X·100+Y·10 through X·100+Y·10+9 (v8.1 → phases 810–819). Hard cap of 10 phases per milestone.

**Rationale:** Earlier milestones used continuous global numbering (v7.0 → 13–20, v8.0 → 21–27, v9.0 → 28–40, v10.0 → 41–49). This collides when a milestone is inserted between existing ones (v8.1 between v8.0 and v9.0). The derived convention gives each milestone a private block, preventing overlap.

**Formula:** `phaseNumber = major * 100 + minor * 10 + localIndex` where `localIndex` ∈ [0, 9].

**Scope:** Applied to v8.1 (810–819). Pre-existing v9.0 (28–40) and v10.0 (41–49) keep their legacy numbers until re-planned. Future milestones (v8.2, v9.2, etc.) should adopt this convention.

**Date:** 2026-07-11 — established with milestone v8.1 Platform Setup Regions.
