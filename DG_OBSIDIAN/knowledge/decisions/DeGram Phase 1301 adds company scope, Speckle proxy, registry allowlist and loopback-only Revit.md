---
tags: [decision, DeGram, v13.0, phase-1301, security, revit, speckle]
date: 2026-10-04
status: planned; implementation and acceptance OPEN
---

# DeGram Phase 1301: company scope, Speckle proxy, registry tool allowlist, loopback-only Revit

Source of truth: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` D-20..D-23 (owner answers during plan-phase research, 2026-10-04). These decisions extend [[knowledge/decisions/DeGram Phase 1301 client isolation, auth relay and Revit MCP fork|D-01..D-19]].

## Decisions

- **D-20 Company scope:** an admin-set project→company map in the data-service auth store. It is returned in `/projects` and `/auth/me`, and checked by the delegated token and the LLM relay. Company vocabulary governance stays in 1302. Planned in 1301-05.
- **D-21 Speckle proxy:** Model Viewer loads geometry through a project-authorised DG proxy limited to the bound `speckleProjectId`. The Speckle read token never leaves the server, and `/validation/view` stops returning it. Planned in 1301-09.
- **D-22 Tool allowlist:** the degram variant registers only clarify, todo, the `degram` toolset and 8 revit-mcp read tools. Everything else is filtered at the registry: terminal, code, file, web, browser, memory, skills, delegation, cron, desktop_ui terminal. MCP sampling is off. Auxiliary LLM calls are pinned to the relay or disabled. Planned in 1301-10/11.
- **D-23 Loopback-only Revit:** the fork's `startup.py` registers only read routes, and only when the pyRevit routes host is loopback. The MCP server probes `:48884` on non-loopback addresses and reports `ROUTES_NOT_LOOPBACK`/`SETUP_INCOMPLETE` without reading. Planned in 1301-07.

## Why

- DG auth had no company concept, but DGCL-02/05 require company/project scope to be visible and checked.
- Today the browser holds one Speckle token for every model, which DGCL-03 forbids. The embedded full V2 would inherit that exposure.
- Hermes registers every built-in tool at import. A config-only filter hides schemas but leaves the handlers and RPCs live.
- pyRevit Routes defaults to binding all interfaces without authentication, and upstream ships `execute_revit_code`.

## Consequences

- New route-policy rows and principal `delegated` go into `spec/SECURITY-BOUNDARY.md`, plus a REPRODUCIBILITY call-site row. Operational outcome codes live in `spec/degram/OPERATIONAL-OUTCOMES.md`, disjoint from evaluator statuses.
- The upstream merge surface grows: registry, gateway, auxiliary and MCP-transport hooks. They are kept as one-line calls into a `degram_variant` package.
