---
phase: 25-projects-and-scoping
plan: "25-01"
status: complete
completed: 2026-07-07
commits:
  - c21497d feat(25-01) Projects screen + scoping fix
duration: ~25min
---

# Summary 25-01: Projects and Scoping

## What shipped

PROJ-01: Projects tile grid from live Neo4j (`DISTINCT project` with node counts, active project marked). PROJ-02: opening a project scopes Graph and Model Viewer queries — verified live by switching projects and observing different data in both viewers. New Project inline flow (name → becomes the active scope; nodes appear on first ingest). Selected project persists across sessions (`dgv2_project`).

## Notes

- Project selection returns to the landing (mockup behaviour) where the member state annotation shows the active project in Signal Red.
- The post-ingest tagging claim (Phase 23 fix) is what actually binds new rules to the opened project — same mechanism as the legacy SPA.
