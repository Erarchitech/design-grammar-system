---
tags: [decision, DeGram, v13.0, phase-1301, D-29]
date: 2026-10-09
status: accepted (owner), implementation pending in 0.1.6
---

# DeGram pins one document per bridge

## Context

D-13 as built kept a single pinned document for the whole scope. In the live UAT (1301-UAT G-13) pinning the Grasshopper definition silently unpinned the Revit model, so its selection stopped reaching the Context card. The owner works with a Revit model and its GH definition side by side.

## Decision

**D-29 (owner, 2026-10-09):** one pinned document per bridge — one Revit model and one Grasshopper definition at the same time. Amends D-13.

- The Context card and the payload carry both snapshots, each with its own identity and counts.
- Losing identity on one bridge (closed, another file active) blocks reads of that bridge only.
- A project switch clears both pins.

## Consequences

- Document store, picker and composer change from one `pinned` to a per-bridge map; DGCL-04/07 are rechecked on 0.1.6.
- Prepares the Phase 1303 rule ↔ GH ↔ object trace, which needs both sides in context.

## Related

- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` (D-29)
- [[sessions/2026-10-09 Phase 1301 live UAT on PC1 and the 0.1.6 gap list]]
