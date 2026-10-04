---
tags: [decision, DeGram, v13.0, phase-1301, security, revit]
date: 2026-10-04
status: discussion captured; implementation and acceptance OPEN
---

# DeGram Phase 1301: client isolation, user-scoped auth relay and Revit MCP fork

Source of truth: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` (D-01..D-19). This note summarizes; it does not replace the context and closes no DGCL requirement.

## Decisions

- **Runtime isolation:** new `degram` variant in `apps/degram/apps/desktop/product-identity.cjs` (own appId/userData/lock); fixed DeGram home, inherited `HERMES_HOME` ignored, fail-closed on overlap with the user's Hermes profile; updater fully disabled; delivered as an unsigned NSIS installer based on upstream `bundled` (ships Python).
- **Login and web:** DG's own login page top-level in an isolated Electron partition (httpOnly cookie, security headers untouched, no iframe); embedded WebContentsView in the same partition with full V2 + Model Viewer, navigation allowlisted to the DG origin.
- **Agent identity:** short-lived delegated user-scoped token tied to the session and project, memory-only in the agent, dies with logout/revoke. User principal, not a connector token. New routes go into `spec/SECURITY-BOUNDARY.md`.
- **Revocation:** server check per request + `/auth/me` heartbeat + focus check; on 401/403 wipe agent context, token and web views.
- **Revit:** fork `Demolinator/revit-mcp-server` (MIT) to `Erarchitech/revit-mcp-server`, pinned submodule using the `apps/degram` pattern. Read-only via allowlist at **both** layers (pyRevit routes in `startup.py` and MCP tools): `execute_revit_code`, save and all writes are not registered. DeGram spawns it as MCP over stdio (no HTTP port). pyRevit installed as a pinned clean-install step.
- **Documents and snapshot:** explicit picker pinned to process/document identity, no silent switch; snapshot = selection + parameters (GH via existing DG serializer). No server-side per-PC CAD routing in 1301.
- **LLM:** new user-scoped OpenAI-compatible streaming chat/tools relay on DG backend as Hermes' only provider; key stays server-side; server policy, provenance, no fallback. Context card by the composer (whole-definition confirm), end-to-end cancel with partial answer marked, chat history scoped to user + company + project.

## Why

- `backend-env.ts` inherits `HERMES_HOME`, so without a fixed home DeGram could write into the user's live Hermes profile.
- pyRevit Routes on `:48884` are reachable by any local process; filtering only at the MCP layer would leave arbitrary code execution open, contradicting the 1300 exclusion of LLM-driven arbitrary CAD code.
- Keeping the system key and data-export policy on the server is the only way to satisfy 1300 D-05/D-06/D-09 (system-managed hidden model, policy-checked transfer).

## Left to planning

Minimal Hermes built-in tool allowlist (no shell/arbitrary code over DG data; owner approves), increment order (isolation tested before any Desktop launch), GH adapter shape, token TTL/heartbeat/timeouts. Execution needs separate authorization for fork/push/submodule, Desktop build/launch, pyRevit install and live calls.

## Related

- [[knowledge/decisions/DeGram Phase 1300 decisions require V8 and server-owned graphs]]
- [[sessions/2026-10-04 Phase 1301 context gathered]]
- [[degram/index]]
