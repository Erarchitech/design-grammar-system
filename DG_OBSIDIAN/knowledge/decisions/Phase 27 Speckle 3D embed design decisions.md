---
tags: [decision]
date: 2026-07-08
---

# Phase 27 Speckle 3D Embed — 6 design decisions (D-01..D-06)

Decisions locked during Phase 27 planning for replacing synthetic SVG boxes with Speckle 3D viewer in V2 ModelScreen.

## D-01: Integration approach

**Decision:** Use `@speckle/viewer` npm package directly in the V2 React app, NOT iframe embedding of the legacy viewer.

**Why:** Native React integration enables event handling (entity click → instance mode), styling consistency with V2 design system, and avoids cross-origin iframe complexity.

## D-02: Viewer lifecycle

**Decision:** Viewer instance created on run select, destroyed on run change/unmount. Camera resets per run.

**Why:** Matches current SVG map behavior where viewBox resets per run. Clean memory management.

## D-03: Auth token flow

**Decision:** Speckle read token fetched from data-service view payload (already returns `readToken`). NOT stored in UI env vars.

**Why:** Data-service already manages Speckle tokens. No new endpoint needed — `build_view_payload` at `app.py:707-727` already includes the token.

## D-04: Geometry color mapping

**Decision:** No client-side recoloring. Server-side Speckle publish pipeline already applies pass/fail colors to geometry vertices.

**Why:** The publish pipeline in `speckle_validation.py` already colors entities (Signal Red for failing, ink/gray for passing). Client renders as-is.

## D-05: Entity selection → Instance mode

**Decision:** Clicking a Speckle object triggers the same `pick(dgEntityId)` flow used by the SVG map (ModelScreen.jsx:233).

**Why:** Reuses existing instance mode in Properties sidebar. Zero behavioral change for the user.

## D-06: Fallback toggle

**Decision:** "3D / Map" toggle in toolbar. Default: 3D when Speckle available, map as fallback on init failure. SVG map code preserved verbatim.

**Why:** Degraded environments (missing token, network error, pre-Speckle runs) must still work. Minimal risk — existing code untouched.

**How to apply:** These decisions are captured in `27-CONTEXT.md` and reflected in `27-01-PLAN.md` Task 1 and Task 2.

**See also:** [[sessions/2026-07-08 audit-fix and Phase 27 Speckle 3D embed plan|session]]
