# Phase 1301: Рабочий клиент и безопасное чтение — Research

**Researched:** 2026-10-04
**Domain:** Electron/Hermes Desktop fork isolation, delegated user auth, streaming LLM relay, local CAD read adapters (pyRevit Routes MCP, GH loopback bridge), Speckle access scoping
**Confidence:** HIGH for in-repo seams (read at file:line), MEDIUM for upstream revit-mcp/pyRevit (read at upstream commit), LOW for `genpro` router behaviour (never probed)

Mode: fully inline orchestration (owner choice 2026-10-04). Fan-out reading was done by four read-only Explore agents; every claim below marked **V** was read in code/docs at the cited location, **I** is inferred, **[ASSUMED]** needs confirmation.

## Summary

Phase 1301 spans four code bases: the DeGram fork (`apps/degram` — Electron shell `apps/desktop` + Python agent), the DG framework (`data-service`, `ui-v2`, `DG/` C# plugin, specs), and a new Revit adapter fork (`Erarchitech/revit-mcp-server`, planned submodule `apps/revit-mcp`). None of the locked decisions is blocked by a missing capability, but almost every seam needs **code** changes, not configuration: Hermes resolves `HERMES_HOME` from the Windows registry and can attach to an already-running host backend; every built-in tool registers at import; auxiliary LLM calls have a provider discovery chain; DG auth sends every Bearer to the connector path and enforces CSRF on every user principal; the LLM gateway has no streaming, no tools and silently falls back to Ollama; nginx cannot stream; pyRevit Routes binds all interfaces by default with no auth; Model Viewer receives a server-wide Speckle read token.

Four owner decisions were taken during research (recorded as D-20..D-23 in CONTEXT.md): minimal project→company attribute; server-side Speckle proxy; minimal read tool allowlist enforced at the registry; Revit bridge fail-closed unless pyRevit Routes is loopback-only. One locked decision needs an implementation note: D-04 asks for NSIS, while the upstream Windows pipeline is MSIX-only (`electron-builder.config.cjs:236`, `BUILDING.md:17`); NSIS is a first-class electron-builder target, so the `degram` variant adds its own `nsis` target and skips MSIX manifest generation — D-04 stands.

**Primary recommendation:** Build runtime isolation (D-01..D-03) and the DG backend contracts (company, delegated token, relay, Speckle proxy) first, each under its own offline test suite; then the agent lockdown and CAD read adapters; then the Electron main/renderer surfaces; packaging, installs, fork publication and every live call stay behind explicit owner-authorization checkpoints.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| App identity, home, userData, updater (D-01..D-03) | Electron main (`apps/degram/apps/desktop/electron`) | build scripts (`scripts/*.mjs`, `scripts/bundles/*.py`) | Identity is baked at build time (`product-identity.cjs`, `__HERMES_PRODUCT_IDENTITY__` define) and resolved at boot (`data-paths.mjs`) |
| DG sign-in, cookie, embedded DG web (D-05, D-07) | Electron main (partition `persist:degram-dg`, `WebContentsView`) | ui-v2 login page (unchanged) | Security headers forbid iframes; top-level navigation in an isolated partition keeps `SameSite=Strict` working |
| Delegated token mint/verify/revoke (D-06, D-08) | data-service auth (`auth.py`, `auth_routes.py`, `route_policy.py`) | Electron main (mints from partition cookie, hands to agent) | Server membership is the only authority; token is never persisted client-side |
| Company scope (D-20) | data-service auth store | `/auth/me`, delegated token, relay | No company concept exists today (auth.py has only project membership) |
| LLM relay (D-16) | data-service new async streaming route | nginx streaming location | System key stays server-side; provenance + policy checks are server duties |
| Tool surface lockdown (D-22) | Hermes agent registry/toolsets/gateway | Desktop renderer (hide entries) | Config alone only hides schemas; handlers stay registered |
| Context composition/disclosure (D-17) | Agent (`degram` toolset + composer RPC) | Renderer (Context card) | The agent owns sessions/tools; renderer presents the exact payload it gets back |
| Revit read (D-09..D-13, D-23) | Revit fork: pyRevit routes (IronPython, in Revit) + FastMCP stdio server | Agent MCP client | Both layers must be allowlisted because Routes is directly reachable over HTTP |
| GH read (D-14) | C# `CanvasListenerComponent` loopback TCP | Agent `degram` toolset client | Existing serializer `get_canvas_context`; Desktop-side client mirrors `gh_bridge.py` with `127.0.0.1` |
| Model Viewer geometry (D-21) | data-service Speckle proxy | ui-v2 `SpeckleViewport` | Token must not leave the server |
| Local history scope (D-19) | Agent profiles (one HERMES_HOME profile per user+company+project) | Electron main (profile selection, deletion on revoke) | `state.db` has no project column; profiles are already isolated dirs |

## Standard Stack

### Core (all already present upstream or in DG — no new libraries)
| Component | Version (observed) | Purpose | Source |
|---|---|---|---|
| Electron + electron-builder | builder `27.0.0-alpha.6` | Desktop shell, NSIS target | `apps/degram/apps/desktop/package.json` (V) |
| Vitest | 4.1.10 (projects `ui` jsdom, `electron` node) | Desktop unit tests | `vitest.config.ts` (V) |
| Playwright | 1.62.1 | Desktop e2e (not used for live runs here) | (V) |
| Hermes Python agent + pytest | repo `pyproject.toml:848-862`, runner `scripts/run_tests.sh` | Agent lockdown tests | (V) |
| FastAPI + `fastapi.testclient` + httpx | data-service requirements | Relay, token, proxy; `httpx.AsyncClient` streaming | (V) |
| `mcp` (FastMCP) | 1.9.0 (revit-mcp `uv.lock`) | Revit adapter stdio transport | upstream (V) |
| pyRevit | 6.5.3 installed on this PC; Routes enabled, `host = "127.0.0.1"`, port 48884 in `%APPDATA%\pyRevit\pyRevit_config.ini` | Revit HTTP routes | local (V) |
| @speckle/viewer | ^2.31.14 | Model Viewer | `ui-v2/package.json:12` (V) |
| .NET SDK | 10.0.301 (DG.Grasshopper targets net7.0-windows, tests net9.0) | GH listener changes | local (V) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Demolinator revit-mcp fork (owner-locked D-09) | pyRevit "Agent runtime" (named pipe, `readonly` policy, `get_context` with `open_documents`) | Experimental branch `feature/agent-runtime`, MCP server unfinished — not viable now; note for later |
| `key_cmd` token source in Hermes | Callable `api_key` passed to `AIAgent` | `key_cmd` spawns a subprocess per mint; callable keeps the token in process memory (D-06) |
| MSIX (upstream) | NSIS (D-04) | Unsigned MSIX cannot be installed on a clean PC without developer mode/cert trust; NSIS installs unsigned with SmartScreen prompt |

**Installation (each step needs owner authorization at execution — package installs are not authorized by default):**
- `npm ci` in `apps/degram` (workspace root lockfile `apps/degram/package-lock.json`; `apps/desktop` has no own lockfile) — required for any Desktop vitest run.
- `python -m pm.build_env --source . --out .venv --group dev --group test` in `apps/degram` — required for agent pytest.
- `uv sync` in the revit-mcp checkout — required for its offline tests.
- Fonts (UI-SPEC): copy `@fontsource/{geist-sans,geist-mono,oswald}` files from `ui-v2/node_modules` (already installed) — no new package.

## Package Legitimacy Audit

No new package is introduced. All installs restore existing lockfiles of upstream projects.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---|---|---|---|---|---|---|
| Hermes Desktop/agent lockfile deps (`apps/degram/package-lock.json`, `uv.lock`) | npm / PyPI | upstream-pinned | n/a | github.com/NousResearch/hermes-agent | OK (lockfile restore) | Approved, install behind owner authorization |
| revit-mcp lockfile deps (`mcp 1.9.0`, `httpx 0.28.1`, `pydantic 2.11.4`, `starlette 0.46.2`, `uvicorn 0.34.2`) | PyPI | established | high | github.com/Demolinator/revit-mcp-server `uv.lock` | OK | Approved, install behind owner authorization |
| @fontsource geist-sans / geist-mono / oswald | npm | established | high | github.com/fontsource/font-files | OK (already in ui-v2/node_modules) | File copy only |

**Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                 ┌──────────── participant PC ─────────────────────────────────────────┐
 user ──▶ DeGram Electron main ──(partition persist:degram-dg, top-level)──▶ DG login page
          │  reads httpOnly dg_session from partition cookie jar
          │  POST /auth/delegated-token (cookie + X-DG-CSRF) ─────────────────────────┐
          │◀── dgd_… token (TTL, bound session_hash+project+company) ───────────────┤
          │  RPC degram.credentials.set (memory only) ──▶ Hermes agent (serve, 127.0.0.1:ephemeral)
          │  WebContentsView (same partition, DG-origin allowlist) ──▶ ui-v2 #degram / full V2
          │  heartbeat GET /auth/me + focus check ── 401/403 ⇒ clear token, scope, views, profile history
          ▼
 renderer: scope strip · project/document pickers · Context card · chat (session.interrupt)
          │ RPC degram.context.preview / prompt
          ▼
 Hermes agent (variant degram, registry allowlist D-22, profile per user+company+project)
   ├─ degram toolset ─ dg_project_graph_read ──(Bearer dgd_)──▶ data-service
   │                 ─ gh_snapshot/gh_selection ──TCP 127.0.0.1:8720──▶ GH CANVAS LISTENER (UI-thread marshalled)
   ├─ MCP stdio child: revit-mcp fork (read tools only) ──HTTP 127.0.0.1:48884──▶ pyRevit Routes (read routes only, ExternalEvent)
   └─ provider "custom" (api_mode chat_completions, callable api_key=dgd_) ──SSE──▶ nginx ──▶ data-service relay
                 └───────────────────────────────────────────────────────────────────────┘
 DG backend: relay checks principal=delegated, company+project, provider-export policy, whole-definition consent
             ──httpx.AsyncClient stream──▶ genpro router (model mimo-v2.5-pro), provenance requested/served, cancel on disconnect
             Speckle proxy: project-authorised, bound speckleProjectId only, server-held read token
```

### Recommended Structure (new files only)
```
apps/degram/apps/desktop/electron/degram/      # isolation, DG session, DG view, heartbeat, token handoff (small modules, DI, testable)
apps/degram/apps/desktop/src/degram/           # scope strip, pickers, context card, hidden-surface gate, i18n keys
apps/degram/degram_variant/ (or agent/degram/) # tool allowlist filter, provider pin, network kill switches, gateway RPCs
apps/degram/tools/degram_*.py                  # degram toolset: DG graph read, GH bridge client, context composer
apps/revit-mcp/                                # submodule: read-only routes/tools, document enumeration
data-service/delegation.py, company.py, degram_relay.py, speckle_proxy.py
```

### Pattern 1: Variant gating through the existing identity seam
**What:** Add `degram` to `product-identity.cjs` variants and to every variant list (`electron-builder.config.cjs:132`, `scripts/write-build-stamp.mjs:187,248-255`, `scripts/before-build.mjs:88`, `scripts/bundles/desktop.py:150`, `desktop_prepare.py:125`); pin `cliName`, `channel: null` (`:57`, `:71`), protocol `degram` (builder `:78-83`), AppUserModelId, window title. Expose a `degram` feature flag via the existing `feature-flags.ts` → IPC `hermes:feature-flags` → preload `sendSync` → nanostore pattern (`main.ts:18296-18304`, `preload.ts:18-38`, `src/store/local-models-flag.ts`).
**When to use:** every DeGram-specific behaviour switch in shell or renderer.

### Pattern 2: Home resolution that ignores every inherited source
`resolveDesktopHermesHome` (`data-paths.mjs:41-66`) consults `env.HERMES_HOME`, `HERMES_DESKTOP_USER_DATA_DIR`, the **Windows registry user env** `HERMES_HOME` (`:50-55`), the platform default and a legacy `~\.hermes` migration (`:59-64`). For `degram`, resolve a fixed `%LOCALAPPDATA%\DeGram\home` (and userData `%LOCALAPPDATA%\DeGram\userData`), ignore all of the above, and fail closed when the resolved path equals/contains/is contained by any Hermes candidate path (D-02). Also set `HERMES_DESKTOP_ISOLATED_BACKEND=1` so `attachToRunningHostBackend` (`main.ts:12719,12773-12794`) never dials a host Hermes backend; `applyDesktopIdentity` (`product-identity.ts:30-48`) must pin userData for `degram` (its condition at `:38` skips stable variants).

### Pattern 3: Delegated principal as a distinct policy token
New prefix `dgd_`, new principal kind/policy token `delegated` (route_policy `PRINCIPAL_*` at `:27-33`, kind check `auth.py:1069-1080`), credential branch before the connector Bearer branch (`auth.py:1041-1050` currently sends every Bearer to connectors). The token record stores `token_hash`, `session_hash` (parent), `username`, `project`, `company`, `expires_at`, `revoked`; every use re-validates the parent session (revoked/expired/idle) and current membership. CSRF: a Bearer credential is not ambient, so the delegated kind is exempt from `_require_csrf` (`auth.py:900-909, 1083-1084`) — documented in SECURITY-BOUNDARY §3. Mirrors connector storage (`connectors.py:57,182-189,218-227,255-271`) with expiry added.

### Pattern 4: Streaming relay with disconnect-driven cancel
`httpx.AsyncClient.stream("POST", f"{base}/chat/completions", json={...,"stream":True,"tools":...})` inside a FastAPI `StreamingResponse` generator that checks `await request.is_disconnected()` and `aclose()`s upstream on disconnect. nginx location for the relay needs `proxy_http_version 1.1; proxy_buffering off; proxy_read_timeout` above the relay timeout; current nginx has none of these (`ui-v2/nginx.conf`, V). Do not route through the existing `/llm/` location (it already exposes `/llm/*` at a second public path).

### Pattern 5: Registry-level tool allowlist
Every `tools/*.py` with top-level `registry.register()` is imported and registered (`tools/AGENTS.md:9-18`). Filter in `discover_builtin_tools`/`tools/registry.py` when the degram variant is active, then additionally pin `platform_toolsets.cli`, disable the coding posture (`agent.coding_context`, `agent/coding_context.py:144,394`), remove the always-added `desktop_ui` (`tui_gateway/server.py:1979-1997` keeps it unconditionally), set `sampling.enabled: false` for the Revit MCP server (`tools/mcp_tool_server_run.py:268-270`) and `tools.include` to the read list (`tools/mcp_tool_registration.py:212-226`).

### Anti-Patterns to Avoid
- **Config-only lockdown:** hides schemas but keeps handlers registered and RPCs (`model.options`, `model.save_key`, `config.set`, `/model`, `/fallback`, REST `/api/providers/*`) callable.
- **MCP-only Revit filtering:** pyRevit Routes stays callable by any local process (`execute_code` route); routes must not be registered at all (D-10).
- **Reusing `/llm/generate` or `resolve_active_provider`:** service-only and falls back to Ollama (`llm_gateway.py:784-808`).
- **Reusing the `kind=="user"` principal for the agent:** `is_admin` makes the user owner of every project (`auth.py:597-599`) and CSRF would reject the agent.
- **Reading the active document:** upstream revit-mcp handlers resolve `ActiveUIDocument.Document`; DeGram must address the pinned identity and refuse on mismatch (D-13).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Per-scope chat history | Project column/filter over one `state.db` | One Hermes profile (HERMES_HOME subdir) per user+company+project | Profiles already isolate state.db, memory, logs; titles are globally UNIQUE per db |
| Turn cancellation | Custom abort plumbing | `session.interrupt` RPC → `InterruptControlMixin.interrupt` (`agent/interrupt_control.py:115-212`), partial kept with `display_metadata.interrupted` (`agent/turn_api_call.py:172-212`) | Already closes sockets, interrupts tool threads and MCP calls |
| MCP child lifecycle | Own process supervisor | Hermes stdio transport (`tools/mcp_tool_transport.py:354-399`, job object KILL_ON_JOB_CLOSE, `mcp_tool_lifecycle.py:155,267-360`) | Handles tree kill and orphan reaping on Windows |
| GH serialization | New serializer | `get_canvas_context` / `get_selection` (`CanvasBridgeCommands.cs`, `CanvasContextExtractor.cs`) | DGCL-07 requires the existing DG serializer |
| Provenance fields | New schema | `GenerateResponse` fields `model/served_model/response_id/system_fingerprint/usage` (`llm_gateway.py:47-86`) | Matches REPRODUCIBILITY provenance contract |
| Theme | New design system | `DesktopTheme` preset seam + existing primitives (UI-SPEC) | DESIGN.md binding |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Hermes `state.db`, memory, logs live under HERMES_HOME (V); DG auth JSON stores under `DG_DATA_DIR` (`auth-users/sessions/memberships/invites.json`, V) | New `degram` home; new JSON stores for delegated tokens and project→company map (atomic write pattern of auth.py) |
| Live service config | `llm-settings.json` (single provider slot, Fernet key) holds the genpro base URL today (I — not read, encrypted) | Relay needs its own operator config slot (provider pair, policy); never reuse the user-editable slot silently |
| OS-registered state | Windows registry user env `HERMES_HOME` may exist (read by `data-paths.mjs:50-55`); `hermes://` protocol registered by an installed Hermes | degram ignores the registry value; registers `degram://` only |
| Secrets/env vars | `LLM_MASTER_SECRET`, `SPECKLE_READ_TOKEN`, `DG_SERVICE_TOKEN` (names only) | Relay and Speckle proxy read them server-side; nothing reaches the PC |
| Build artifacts | `apps/degram` has no `node_modules`/`.venv` (V, 2026-10-04) | Authorized install before any Desktop/agent test |

## Common Pitfalls

### Pitfall 1: Registry HERMES_HOME leak
**What goes wrong:** degram boots against the user's installed Hermes profile. **Why:** `data-paths.mjs:50-55` reads the registry user env. **Avoid:** degram resolver ignores every inherited source; unit test with env + registry stub + legacy dir present. **Warning sign:** `config.yaml` read from `%LOCALAPPDATA%\hermes`.

### Pitfall 2: Host backend attach
**What goes wrong:** degram reuses a running Hermes backend (different toolsets/provider). **Why:** spawn ledger attach (`main.ts:12773-12794`). **Avoid:** isolated home + `HERMES_DESKTOP_ISOLATED_BACKEND=1`; test that attach is never attempted for the variant.

### Pitfall 3: Silent provider egress
**What goes wrong:** compression/title/vision/curator/background_review/session_search/MCP sampling call OpenRouter or Nous. **Why:** auxiliary `provider: "auto"` with discovery chain (`agent/auxiliary_client.py:4693-4720`, `config_defaults.py:26`); `background_review.enabled: true` (`:814`). **Avoid:** pin all `auxiliary.*` to the relay or disable them; close `_discovery_chain_allowed`; test that only the relay base URL is ever constructed.

### Pitfall 4: Background network calls
Model catalog fetch every 20 min (`config_defaults.py:2044-2053`), models.dev (`agent/models_dev.py:27`), OSV preflight before each MCP spawn (`tools/mcp_tool.py:34-51`; `HERMES_SAFE_MODE` is not usable — it disables MCP too), git/plugin update checks, free-tier guest mint (`hermes_cli/anon_auth.py`), skills hub/plugin catalog. **Avoid:** variant kill switches + a test that stubs sockets/httpx and asserts no non-allowlisted host is contacted (Nous feed included, D-03).

### Pitfall 5: CSRF and Bearer routing in DG auth
Any non-`dgc_` Bearer → 401 `CONNECTOR_AUTH_FAILED`; any user principal on unsafe method needs `X-DG-CSRF: 1`. **Avoid:** delegated branch + exemption, spec §3 precedence text and error-code rows updated.

### Pitfall 6: Route inventory gates
`test_route_inventory.py:208` asserts `len(ROUTE_POLICIES) == 84`; `test_policy_rows_are_well_formed` whitelists exactly seven principal tokens (`:229-244`); spec block `route-policy` must equal ROUTE_POLICIES field by field (`test_security_boundary_spec.py:322,336`). Every new route/token updates all of them; plans touching routes must be serialized (same files).

### Pitfall 7: REPRODUCIBILITY drift scan loophole
The scan only catches `<adapter-ish>.generate(` calls (`spec/REPRODUCIBILITY.md:187-191`). A relay calling a streaming method escapes it; add the call-site row deliberately and update the "exactly seven lines" prose.

### Pitfall 8: UI-thread hangs in CAD bridges
GH `InvokeOnCanvas` (`CanvasListenerComponent.cs:196-213`) blocks without timeout and the listener serves one client serially (`:649`); pyRevit sync path busy-spins without timeout (`server.py:157-159`, `handler.py:152-158`) and shares one global ExternalEvent handler across threads. **Avoid:** client deadlines, serialized calls, a bounded wait + `BUSY` code in the GH listener, no automatic retry (1300 D-10).

### Pitfall 9: pyRevit API calls off the API context
Upstream `/status/` and `/model_info/` handlers take no `doc`/`uidoc` argument, so pyRevit runs them on the HTTP worker thread (`server.py:193-207`). Fork adds `doc`/`uiapp` to every read handler signature.

### Pitfall 10: Weak document identity
GH: only `DocumentID` + `DisplayName`, and the listener serves the document that hosts it (`CanvasContextExtractor.cs:49-53`). Revit upstream: only active `Title`. **Avoid:** GH listener read command returning `DocumentID`, `FilePath`, `DisplayName`, `IsModified`; Revit route enumerating `uiapp.Application.Documents` (excluding linked/family docs) with `Title`, `PathName`, `CreationGUID` (Revit 2024+) — identity = CreationGUID + PathName; unsaved docs have empty PathName (UI-SPEC «Не сохранён»).

### Pitfall 11: MiMo tool-history 400
GitHub issue XiaomiMiMo/MiMo#44 (open, unofficial): a follow-up request containing assistant `tool_calls` + `role:"tool"` returns `400 Param Incorrect`. Thinking mode forces temperature 1.0 / top_p 0.95 and expects `reasoning_content` preserved. Whether `genpro` passes `stream`, `tools`, `reasoning_content` through is UNKNOWN (1300 D-09). **Avoid:** relay reports the provider error verbatim as an operational outcome (no fallback); a live probe is an owner-authorized checkpoint.

## Code Examples
No new library APIs are introduced; executors follow the cited in-repo patterns (`connectors.py` token lifecycle, `auth_tracer` tests, `product-identity.test.ts` env + `vi.resetModules()` pattern, `test_gh_bridge.py` socket fakes, upstream `tests/test_offline.py` tool-contract snapshot).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Revit `Document` identity by title | `Document.CreationGUID` | Revit 2024 API | Available on the pinned Revit 2024 target |
| `/llm/generate` sync single-shot | Streaming chat/tools relay (new) | this phase | REPRODUCIBILITY call-site list grows by one |
| Browser-held Speckle read token | Server-side proxy (D-21) | this phase | `build_view_payload` stops returning `readToken` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `genpro` is an OpenAI-compatible router reachable with the existing encrypted base URL (inferred from `fixtures/llm_repeatability/MANIFEST.md:63`) | Relay | Relay config shape changes; caught by the authorized live probe |
| A2 | `genpro` passes `stream:true` and `tools` through | Relay | DGCL-06/07 chat works only without tools; reported as operational outcome, owner decides |
| A3 | `CreationGUID` + `PathName` uniquely identify an open Revit document on one PC | Revit identity | Save-As copies share CreationGUID; PathName disambiguates; unsaved twins disabled in picker |
| A4 | electron-builder 27 alpha NSIS target works with the bundled payload hooks (`after-pack.mjs` batch signing is a no-op without Azure env) | Packaging | Build step fails; fixed in the authorized packaging plan |
| A5 | Speckle object loading for a bound project can be satisfied by proxying `/objects/{projectId}/{objectId}` and `/api/getobjects/{projectId}` after server-side resource-URL resolution | Speckle proxy | Executor confirms exact requests in `ui-v2/node_modules/@speckle/objectloader` before coding |

## Open Questions
1. **Delegated token TTL/heartbeat values** — recommendation (Claude's discretion): token TTL 15 min, renewed by Electron main every 10 min while the parent session is valid; heartbeat `/auth/me` every 60 s plus on window focus; relay timeouts connect 10 s / first byte 60 s / total 300 s; snapshot limits 200 objects, 50 parameters per object, 256 KiB payload. All values are named constants with tests.
2. **Provider-export policy model** — no policy exists in code (V). Recommendation: operator-set per-project policy record `{providerExportAllowed: bool, wholeDefinitionAllowed: bool}` in the same store as the company map; deny by default; `whole-definition` additionally needs a per-request consent flag. Policy deny is terminal (1300 D-06).
3. **pyRevit loopback verification method** — recommendation: the fork's MCP server checks the OS listener table for `:48884` (psutil `net_connections`, bundled in Hermes? else `netstat -ano` parse) and refuses reads unless every listener is `127.0.0.1`/`::1`; status `setup-incomplete` with the D-23 copy.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Node.js | Desktop/ui-v2 tests | ✓ | 20.20.0 | — |
| Python | data-service tests, agent | ✓ | 3.14.2 (host) | agent venv via `pm.build_env` |
| .NET SDK | GH listener build/tests | ✓ | 10.0.301 | — |
| uv | revit-mcp env | ✓ | `~/.local/bin/uv` | — |
| pyRevit CLI | protocol, Routes config | ✓ | 6.5.3; Routes enabled, host 127.0.0.1 | — |
| Revit 2024 / Rhino 8 | live acceptance | ✓ (also Revit 2025/2027 installed) | — | — |
| Desktop node_modules | Desktop vitest | ✗ | — | Authorized `npm ci` |
| Agent .venv | agent pytest | ✗ | — | Authorized `pm.build_env` |
| ui-v2 esbuild/Chrome | ui-v2 browser tests | ✓ | esbuild in node_modules | — |

**Missing dependencies with no fallback:** none. **Missing with fallback:** Desktop/agent test environments — require an owner-authorized install before execution.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | Vitest 4.1.10 (Desktop), pytest (agent, data-service, revit-mcp), node:test + headless Chrome (ui-v2), xUnit (DG) |
| Config file | `apps/degram/apps/desktop/vitest.config.ts`; `apps/degram/pyproject.toml`; `data-service/tests/conftest.py`; revit-mcp `pyproject.toml` |
| Quick run command | per area: `npx vitest run --project electron <file>` (cwd `apps/degram/apps/desktop`); `bash scripts/run_tests.sh <path>` (cwd `apps/degram`); `python -m pytest data-service/tests/<file> -q`; `node --test ui-v2/tests/<file>`; `dotnet test .\DG\tests\DG.Tests\ --filter <name>` |
| Full suite command | `python -m pytest data-service/tests -q` + `node --test ui-v2/tests/*.test.mjs` + `npm --prefix ui-v2 run build` + `npx vitest run` (desktop) + `bash scripts/run_tests.sh` (agent) + `dotnet test .\DG\tests\DG.Tests\` + `python -m unittest discover -s tools/degram/tests -v` + `python tools/degram/workspace.py verify` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| DGCL-01 | degram identity/home/userData/lock isolated; updater never contacts a feed; NSIS target | unit (vitest) | `npx vitest run --project electron electron/degram/isolation.test.ts scripts/degram-build.test.mjs` | ❌ Wave 0 |
| DGCL-01 | clean-PC install + sign-in + explicit project | manual UAT (protocol) | `docs` protocol checklist | ❌ |
| DGCL-02 | `/auth/me` carries company; scope change reflected in next request payload; provider/model surfaces absent | pytest + vitest(ui) | `python -m pytest data-service/tests/test_company_scope.py -q`; `npx vitest run --project ui src/degram` | ❌ Wave 0 |
| DGCL-03 | DG view navigation allowlist; Speckle proxy serves only bound project; no readToken in payload | vitest + pytest + node | `npx vitest run --project electron electron/degram/dg-view.test.ts`; `python -m pytest data-service/tests/test_speckle_proxy.py -q`; `node --test ui-v2/tests/speckle-proxy.test.mjs` | ❌ |
| DGCL-04 | Revit read-only registry exact set; document enumeration + pinned identity mismatch outcome; GH identity + busy | pytest (fork) + xUnit + agent pytest | `uv run pytest tests/test_degram_readonly.py`; `dotnet test --filter CanvasBridge`; `bash scripts/run_tests.sh tests/degram/test_cad_bridges.py` | ❌ |
| DGCL-05 | delegated token dies on logout/revoke/expiry; cross-project/company deny on relay, graph read, Speckle proxy | pytest | `python -m pytest data-service/tests/test_delegated_token.py data-service/tests/test_degram_relay.py -q` | ❌ |
| DGCL-06 | cancel propagates client→relay→provider; timeouts/unavailable map to named outcomes; listener released | pytest + agent pytest + vitest | `python -m pytest data-service/tests/test_degram_relay.py -k cancel -q`; `bash scripts/run_tests.sh tests/degram/test_interrupt.py` | ❌ |
| DGCL-07 | context preview equals sent payload; truncation/missing disclosed; whole-definition requires consent; deny not overridable | agent pytest + pytest | `bash scripts/run_tests.sh tests/degram/test_context_composer.py`; relay policy tests | ❌ |

### Sampling Rate
- **Per task commit:** the task's quick command.
- **Per wave merge:** full suite of every touched area + `workspace.py verify`.
- **Phase gate:** full suite green + authorized live UAT before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] Owner-authorized installs: `npm ci` (apps/degram), `pm.build_env` (apps/degram), `uv sync` (revit-mcp).
- [ ] Owner-authorized fork creation `Erarchitech/revit-mcp-server`, submodule registration `apps/revit-mcp`.
- [ ] New test files listed in the map above.

## Security Domain

### Applicable ASVS Categories (L1, block on high)
| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | yes | Existing DG session login (D-05); delegated token derived from it, never a second login |
| V3 Session Management | yes | Short TTL token bound to parent session_hash; revoke on logout/password change/membership removal; heartbeat + focus check |
| V4 Access Control | yes | route_policy rows + project/company check in `require_principal`; delegated principal cannot hit session/admin routes |
| V5 Input Validation | yes | pydantic models on relay/token/proxy; MCP tool args typed; bridge line limits (5 MiB in, 10 MiB out) |
| V6 Cryptography | yes | `secrets.token_urlsafe` + SHA-256 hash storage (connector pattern); Fernet for provider key (existing) |
| V9 Communications | partial | Loopback-only local channels (8720, 48884, agent ws); TLS for remote DG is a G-06 deployment concern |
| V12 Files/Resources | yes | No file tools in agent (D-22); Revit export routes not registered |
| V14 Configuration | yes | Updater off, telemetry/catalog/hubs off, no fallback provider |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| LAN access to pyRevit Routes (0.0.0.0 default, no auth) | Elevation | Read routes only + loopback bind verified, fail closed (D-23) |
| Local process drives GH listener mutations (`preview_structure`) | Tampering | DeGram client sends read commands only; listener stays loopback; accepted residual risk documented |
| Token theft from agent logs/LLM payload | Info disclosure | Callable api_key never logged; redaction test over log handlers and payload preview |
| Cross-project data via chat/tools | Info disclosure | Server-side project+company checks on every delegated call; per-scope profile |
| Prompt-injected tool use to run code | Elevation | No code/shell/file tools registered (registry filter) |
| Silent document substitution | Tampering | Identity-pinned reads, mismatch outcome (D-13) |
| Provider fallback leaking data to another vendor | Info disclosure | Single provider, no fallback, discovery chain closed |
| Browser-held global Speckle token | Info disclosure | Server proxy (D-21) |
| Update feed supply chain | Tampering | Updater disabled (D-03) |

## Sources

### Primary (HIGH)
- In-repo files cited above (data-service auth/route_policy/connectors/llm_gateway/app.py, ui-v2 nginx/auth/modelApi/SpeckleViewport, DG CanvasListener/Bridge, specs SECURITY-BOUNDARY/REPRODUCIBILITY/EVIDENCE-CONTRACT).
- `apps/degram` at gitlink `8b66a510`: `product-identity.cjs`, `electron-builder.config.cjs`, `electron/data-paths.mjs`, `electron/main.ts`, `electron/backend-env.ts`, `update-feed.cjs`, `toolsets.py`, `tools/registry.py`, `tools/mcp_tool_*.py`, `tui_gateway/server.py`, `agent/auxiliary_client.py`, `hermes_cli/config_defaults.py`.
- https://github.com/Demolinator/revit-mcp-server @ `74a8ddca` (main.py, startup.py, tools/__init__.py, SECURITY.md, uv.lock).
- https://github.com/pyrevitlabs/pyRevit `develop` (routes server.py, handler.py, PyRevitConsts.cs, docs/config-api.md, docs/agent-runtime.md).
- https://www.revitapidocs.com/2024/4d2418fc-e00a-f5b8-609e-8f027eeed992.htm (CreationGUID), Application.Documents.
- https://mimo.mi.com/docs/en-US/api/chat/openai-api (stream, tools, thinking parameters).

### Secondary (MEDIUM)
- https://github.com/XiaomiMiMo/MiMo/issues/44 (tool-history 400, unofficial).

### Tertiary (LOW)
- Third-party gateway listings of mimo-v2.5-pro tool support (Vercel, Novita).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components present and versioned locally/upstream.
- Architecture: HIGH for seams, MEDIUM for Speckle proxy request shape (A5) and NSIS on the alpha builder (A4).
- Pitfalls: HIGH — each cited at file:line.
- LLM endpoint: LOW — `genpro` never probed; live probe requires owner authorization.

**Research date:** 2026-10-04
**Valid until:** 2026-10-18 (fast-moving upstream fork; re-check gitlink before execution)
