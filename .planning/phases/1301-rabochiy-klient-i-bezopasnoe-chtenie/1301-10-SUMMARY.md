---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 10
subsystem: degram-agent-lockdown
tags: [degram, hermes, variant-degram, lockdown, in-memory-credential, relay-provider, tool-allowlist, rpc-deny-by-default, socket-guard, profiles, tdd, fail-closed]
requires: ["1301-04", "1301-08"]
provides:
  - "degram_variant package in the component (apps/degram): HERMES_DEGRAM=1 switch, in-memory DegramCredentials (callable api_key, redacted repr, no pickle), pinned relay provider, lockdown, rest_lock, profiles, config_template.yaml"
  - "Gateway RPCs degram.credentials.set / clear / status (camelCase contract: token, expiresAt, relayBaseUrl, user, company, project) with generated TS + OpenRPC; the token is never returned, logged or persisted"
  - "Pinned runtime: provider custom, base_url <relayBaseUrl>/degram/v1, api_mode chat_completions, model alias degram-system, api_key = callable, no fallback chain, no credential pool"
  - "Named errors CREDENTIALS_MISSING / CREDENTIALS_EXPIRED / CREDENTIALS_INVALID (terminal in the retry classifier) and DEGRAM_LOCKED (RPC code 4403, REST 403)"
  - "Registry-level tool allowlist (clarify, todo_list, 4 reserved degram_* names, 8 mcp_revit_* reads); deny-by-default RPC allowlist; dashboard reduced to /api/ws, /api/health, /api/status; config lock; auxiliary pinning; egress kill switches"
  - "Per-scope profiles: scope-<sha256[:16]> under <home>/profiles, config regenerated per ensure, purge, CLI python -m degram_variant.profiles"
affects: [1301-11, 1301-12, 1301-13, 1301-14, 1301-15]
tech-stack:
  added: []
  patterns:
    - "One-line hooks into degram_variant.lockdown (no-op unless HERMES_DEGRAM=1) so upstream merges stay small"
    - "Chokepoint hooks: ToolRegistry.register, rpc_dispatch._handle_admitted_request, config._merge_managed_overlay, model_metadata_http.stream, auxiliary resolve_provider_client, mcp _filter_suspicious_mcp_servers, web_server route prune"
    - "Closed in code, observed from a clean interpreter: registry / REST / config / socket-guard tests run in subprocesses with a fresh HERMES_HOME"
key-files:
  created:
    - apps/degram/degram_variant/__init__.py
    - apps/degram/degram_variant/credentials.py
    - apps/degram/degram_variant/provider.py
    - apps/degram/degram_variant/lockdown.py
    - apps/degram/degram_variant/rest_lock.py
    - apps/degram/degram_variant/profiles.py
    - apps/degram/degram_variant/config_template.yaml
    - apps/degram/tui_gateway/methods_degram.py
    - apps/degram/tui_gateway/contracts/degram.py
    - apps/degram/tests/degram/__init__.py
    - apps/degram/tests/degram/test_credentials_provider.py
    - apps/degram/tests/degram/test_lockdown.py
    - apps/degram/tests/degram/test_profiles.py
  modified:
    - apps/degram/pyproject.toml
    - apps/degram/apps/shared/src/gateway-contract.generated.ts
    - apps/degram/apps/shared/src/gateway-contract.openrpc.json
    - apps/degram/tui_gateway/contracts/__init__.py
    - apps/degram/tui_gateway/server.py
    - apps/degram/tui_gateway/agent_callbacks.py
    - apps/degram/tui_gateway/rpc_dispatch.py
    - apps/degram/tools/registry.py
    - apps/degram/tools/mcp_tool.py
    - apps/degram/tools/mcp_tool_config.py
    - apps/degram/agent/auxiliary_client.py
    - apps/degram/agent/error_classifier.py
    - apps/degram/agent/model_metadata.py
    - apps/degram/agent/model_metadata_http.py
    - apps/degram/agent/models_dev.py
    - apps/degram/hermes_cli/config.py
    - apps/degram/hermes_cli/model_switch_providers.py
    - apps/degram/hermes_cli/web_server.py
key-decisions:
  - "The RPC lock is an allowlist, not a denylist: every method not named in ALLOWED_RPC_METHODS answers DEGRAM_LOCKED before any handler or lookup, so a method a future upstream release adds is closed by default. A test enumerates server._methods and requires each name to be allowed or raise"
  - "Task-level seams over per-handler edits: one guard in rpc_dispatch, one gate in ToolRegistry.register (plus discover_builtin_tools not importing stock tool modules), one lock_config in config._merge_managed_overlay (wins over config.yaml and the managed scope), one egress refusal in model_metadata_http.stream"
  - "Compression is the only auxiliary that runs, on the pinned relay route; every other auxiliary task, vision, the fallback chains and the discovery chain are closed in code; an explicit auxiliary endpoint is honoured only when it equals the pinned relay URL"
  - "relayBaseUrl is the origin plus path prefix WITHOUT /degram/v1 (for the DG stack: <origin>/data-service); http is accepted only for loopback hosts, credentials/query/fragment refused"
  - "The registered name of the todo tool is todo_list (toolset todo); the allowlist uses the registered name. Tool Search is switched off by the config lock so the two allowlisted built-ins stay directly visible"
  - "A named credential failure is a terminal classifier verdict (auth_permanent, not retryable, no rotate/fallback): a cleared credential fails the turn in 0.15 s with the CREDENTIALS_* code instead of three backoff retries"
  - "Profile purge refuses any path whose resolved parent is not <home>/profiles, including symlinks and Windows junctions"
metrics:
  duration: ~1h (wall clock; test suites dominate)
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-02, DGCL-05, DGCL-06]  # agent side of the single-provider lockdown, credential handoff and scope isolation; Desktop wiring (12/13), the degram toolset (11) and the live run (15) are later plans
status: complete
---

# Phase 1301 Plan 10: Variant degram agent lockdown Summary

The Hermes agent in variant degram now talks to exactly one model route (the DG relay) with a delegated token that lives only in process memory, registers only the allowlisted tools in the registry itself, refuses every provider/model/toolset/MCP RPC, REST route and slash command that could re-open a surface, makes no background network call, and keeps one isolated profile per user, company and project that can be purged on revoke. All of it is proven offline by 212 new tests, including a socket guard that sees only loopback during dashboard startup, gateway boot work and a real streamed turn.

## Authorization and boundaries

Per the orchestrator brief: local commits on component branch `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch/build/dev server/packaging, no Docker, no write to `%LOCALAPPDATA%\hermes` or the installed Hermes profile, no package install (only the existing `apps/degram/.venv`), no real provider/paid call (the relay is a local fake SSE server), `.secrets` not read, `apps/degram` gitlink NOT bumped (plan 15), `apps/degram` and `apps/revit-mcp` not staged in the framework. `python tools/degram/workspace.py verify` reports "Submodule gitlink does not match the selected component HEAD", the expected state until plan 15; it was not worked around.

## Commits (component repo `apps/degram`, branch `degram/phase-1301`, committing repository: component)

| Task | Commit | Message |
|---|---|---|
| 1 | `d2d819e0` | feat(1301-10): in-memory delegated credential and pinned relay provider for variant degram |
| 2 | `b1e09d52` | feat(1301-10): close tools, RPCs, REST, auxiliaries and network egress in variant degram |
| 3 | `c27f31cd` | feat(1301-10): per-scope Hermes profiles with locked config and purge |

`git -C apps/degram status --short` is empty after the three commits; no deletions in any of them. The framework commit for this SUMMARY/STATE/ROADMAP is a separate `docs(1301-10)` commit in the framework repo.

## What was built

**Task 1 (tracer): credential + pinned provider + one streamed turn.**
- `credentials.py`: thread-safe store; `set` validates (token, user, project required; `expiresAt` ISO-8601 or epoch; `relayBaseUrl` http(s), http only for loopback, no credentials/query/fragment); `api_key_provider()` returns the current token or raises `DegramCredentialsError` (CREDENTIALS_MISSING after `clear`/before `set`, CREDENTIALS_EXPIRED at `now >= expiresAt`, inclusive like the server's token store); `repr/str` redacted, pickling and copying refused.
- `provider.py`: `pinned_runtime()` = provider `custom`, `base_url = <relay>/degram/v1`, `api_mode chat_completions`, `api_key = credentials.api_key_provider` (callable: the OpenAI SDK reads the current token before every request, so renewal and clear apply to the next call), `credential_pool None`, `DEGRAM_MODEL_ALIAS = "degram-system"`; raises CREDENTIALS_MISSING when no scope credential exists, so an agent is never built without a relay.
- RPCs `degram.credentials.set/clear/status` (`methods_degram.py` + `contracts/degram.py`; regenerated `apps/shared` TS and OpenRPC; `NOT_DEGRAM` outside the variant, `CREDENTIALS_INVALID` on bad input, never the token in any response).
- Hooks: `_resolve_agent_model_runtime` returns the pinned model/runtime whatever the session, override or config asks; `_load_fallback_model` returns `[]`; `get_model_context_length` returns a fixed 128 000 (config `model.context_length` still wins); `model_metadata_http.stream` refuses every metadata probe; `detect_local_server_type` returns None; the retry classifier treats `DegramCredentialsError` as terminal.
- A real turn against the fake relay sends exactly one request shape: `POST /data-service/degram/v1/chat/completions`, `Authorization: Bearer <token>`, `model degram-system`, `stream true`.

**Task 2: closed surfaces.** See `degram_variant/lockdown.py`.
- *Tools (D-22):* `ALLOWED_TOOL_NAMES` = `clarify`, `todo_list`, `degram_project_graph`, `degram_document_snapshot`, `degram_list_documents`, `degram_bridge_status` (reserved for plan 11) and the eight `mcp_revit_*` reads. `ToolRegistry.register` refuses any other name; `discover_builtin_tools` does not even import stock tool modules (only `tools.clarify_tool`, `tools.todo_tool`, `tools.degram*`). The fixed toolset selection `[clarify, todo, degram, mcp-revit]` ignores surface fold-in (`desktop_ui`, `project`), the coding posture and `HERMES_TUI_TOOLSETS`; `_make_agent` sets `skip_context_files` and `skip_memory` in the variant.
- *RPC/REST (DGCL-02):* `assert_rpc_allowed` runs in `_handle_admitted_request` before the handler or method lookup; `config.set` additionally refuses model/provider/providers/fallback*/toolsets/platform_toolsets/mcp*/auxiliary*/cwd/prompt/personality/yolo/approval keys; `slash.exec`/`command.dispatch`/`command.resolve` accept only `/help /clear /new /reset /title /undo /retry /usage /compress /history /stop /status /copy /quit /exit` (so `/model`, `/fallback`, `/provider`, `/tools`, `/skills`, `/cron`, `/plugins`, `/yolo`, `/terminal`, `/reload-mcp` are locked). The dashboard keeps only `/api/ws`, `/api/health`, `/api/status`; the rest of `/api/*` (and docs/openapi/dashboard-plugins routes) is removed, with a catch-all answering 403 `DEGRAM_LOCKED` (so `/api/providers/*` is closed).
- *Auxiliaries (D-16):* `resolve_provider_client` returns `(None, None)` for every task except `compression` and forces `auto`+main route unless the explicit endpoint equals the pinned relay URL; `resolve_vision_provider_client` is disabled; fallback and discovery chains return nothing.
- *Config lock:* `lock_config` (in `_merge_managed_overlay`) forces provider custom/alias, `fallback_providers []`, `providers {}`, the fixed toolsets, MCP servers reduced to the allowlisted stdio `revit` entry with sampling/elicitation off and no url/headers/auth, `model_catalog`, telemetry, updates, free tier (`nous.guest`), curator, plugin update checks, memory off, Tool Search off, every auxiliary block pinned to `auto` with no base_url/api_key/key_env and non-compression tasks disabled.
- *Egress:* models.dev never contacted (`allow_network=False`), `/model` picker prefetch not started, OSV preflight skipped (T-1301-10-06 accepted), MCP sampling off.

**Task 3: profiles (D-19).** `profile_name_for_scope(user, company, project)` = `scope-` + first 16 hex of sha256 of the three fields joined by U+001F (company None encodes as empty, empty user/project and the separator inside a field are refused). `ensure_scope_profile(home, scope, revit_command=None, revit_args=None)` creates `<home>/profiles/<name>`, rewrites `config.yaml` from `config_template.yaml` on every call (user edits discarded, existing `state.db`/memory/logs untouched, `mcp_servers.revit` a disabled stdio placeholder until a command is passed), `purge_scope_profile` removes the whole profile (idempotent, read-only files handled, retries on Windows handle locks, refuses anything not directly under `<home>/profiles`). CLI `python -m degram_variant.profiles ensure|purge --home H --user U [--company C] --project P` prints one JSON object; bad input exits 1, bad usage exits 2. The template contains no URL, no secret.

## TDD

- **Task 1:** honest caveat: the credentials/provider scaffolding was written before the test file. The first run of `test_credentials_provider.py` against that scaffolding was a real RED: 2 tests failed (the agent contacted the relay host with `GET /api/show`, `/api/tags`, `/v1/props`, `/props`, `/version`, `/v1/models`, `/models`, the last one carrying the delegated token, from local-server detection and cost estimation). Those probes led to the `model_metadata_http.stream` choke point; a `clear` made the agent walk three backoff retries (9 s) before the terminal classifier verdict existed. GREEN: 44 tests.
- **Task 2:** RED = collection `ImportError: cannot import name 'ALLOWED_RPC_METHODS'` (nothing existed), then 8 failing tests on the first GREEN pass (tool_search bridge hiding `todo_list`, compression route resolving to None because `_try_main_provider_route` re-enters `resolve_provider_client` without a task, REST catch-all 422 because FastAPI cannot resolve annotations under `from __future__ import annotations`, and the socket guard catching `api.anthropic.com`, `api.github.com`, `api.githubcopilot.com`, `models.dev` from the picker prefetch). All fixed: 134 tests.
- **Task 3:** RED = collection `ImportError: cannot import name 'profiles'`; GREEN 34 tests (the symlink-escape test uses a Windows directory junction when symlinks need privilege, and refuses the escape).

## Verification

All Python through `HERMES_PYTHON=<apps/degram/.venv python>` and `scripts/run_tests.sh` (no uv download), nothing launched.

| Check | Result |
|---|---|
| `tests/degram` (3 files) on the committed state | **212 passed, 0 failed** (credentials 44, lockdown 134, profiles 34) in 45 s |
| Targeted baseline of touched modules on the UNTOUCHED code, before any edit (9 files: `tests/tools/test_registry.py`, `test_osv_check.py`, `test_mcp_transport_group_reconnect.py`, `test_mcp_dynamic_discovery.py`, `test_mcp_capability_gating.py`, `test_mcp_lazy_start.py`, `tests/tui_gateway/test_gui_surface_toolsets.py`, `tests/agent/test_auxiliary_client.py`, `tests/hermes_cli/test_web_server.py`) | **544 passed, 0 failed, 5 skipped** (the six `tests/tools` files: 108 passed) |
| Broad targeted run after Task 2 (238 files: all `test_auxiliary*`, `test_models_dev*`, `test_model_metadata*`, `test_tool_search*` in agent; `test_config*`, `test_mcp*`, `test_model_switch*`, `test_web_server*` in hermes_cli; `test_mcp*`, `test_tool_search*`, `test_registry`, `test_osv_check` in tools; `test_model_tools_async_bridge`, `test_packaging_py_modules`) | 2720 passed, 50 failed, 63 skipped |
| Same 12 failing files re-run on a pristine `git worktree` of the fork at `8b66a510` (removed afterwards) | 353 passed, **the same 50 failed** (identical test names) |
| `tests/tui_gateway` full after Task 1 | 2393 passed, 18 failed, all 18 in the 1301-ENV.md list of 23 |
| `tests/tui_gateway` full after Task 2 | 2394 passed, 17 failed: 16 in the ENV list plus `test_foreground_notification_snapshot.py::test_tui_real_turn_snapshot_next_turn_and_child_threads[False-True]` (a `prompt-turn-snapshot` thread still alive under load; 10/10 passed in three solo runs) |
| `tests/tui_gateway/contracts` (generated TS/OpenRPC fresh), `tests/test_packaging_py_modules.py`, `tests/pm/test_workspace_build_inputs.py`, `test_error_classifier*`, `test_model_metadata*`, `test_usage_pricing` | all pass |

**The tests/tools baseline 1301-ENV.md left open.** The 50 failures present on the untouched fork are Windows/environment issues, none in a touched code path: `OAuthNonInteractiveError` in 40 tests (`test_mcp_cimd` 9, `test_mcp_oauth_manager` 22, `test_mcp_oauth_user_agent` 5, `test_mcp_oauth` 4), `os.killpg` absent on Windows in 4 (`test_mcp_stability` 3, `test_mcp_windows_orphan_fix` 1), and 6 environment/locale/fixture assertions (`test_mcp_shared_connection_resolved_identity` 1, `test_mcp_startup_summary_names_failures` 1 with a localized WinError text, and the ENV-listed `test_config` 2, `test_mcp_config` 1, `test_config_cache_signature` 1). A single extra failure appeared only under load (`test_auxiliary_explicit_cancellation.py::test_cancelled_codex_orphan_timeout_preserves_cached_shared_client`); it passes on the runner's retry and in three solo runs.

The full `tests/hermes_cli` and `tests/tools` directories were NOT run whole (the 1301-ENV.md record shows `tests/hermes_cli` exceeds the 15-minute hard limit on Windows); the targeted sets above cover every touched module and the modules that read the touched seams. No new failure was found.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Seams differ from the plan's file list.** The plan names `methods_complete.py`, `methods_config_set.py`, `tools/mcp_tool_transport.py`. The strongest single seams are elsewhere: the RPC guard is one call in `tui_gateway/rpc_dispatch.py` (it also covers `model.options`, `model.save_key` and every other method with no per-handler edit); the MCP allowlist is in `tools/mcp_tool_config.py::_filter_suspicious_mcp_servers` (the one function every native, portable and explicit registration passes through) and the OSV preflight lives in `tools/mcp_tool.py::_preflight_stdio_command`. Not edited: `methods_complete.py`, `methods_config_set.py`, `mcp_tool_transport.py`.

**2. [Rule 2 - Missing critical] Extra hooks the closed surface needed**, found by the failing tests and the socket guard: `tui_gateway/agent_callbacks.py` (the fallback loader lives there, not in `server.py`), `agent/error_classifier.py` (terminal CREDENTIALS_* verdict), `agent/model_metadata.py` and `agent/model_metadata_http.py` (fixed context length, probe refusal; without them the agent sent `GET /models` with the delegated token to the relay host), `agent/models_dev.py` and `hermes_cli/model_switch_providers.py` (models.dev and picker prefetch), `hermes_cli/config.py` (`lock_config`), `tui_gateway/contracts/degram.py` + `contracts/__init__.py` + regenerated `apps/shared` TS/OpenRPC (every RPC must have a contract), `degram_variant/rest_lock.py`.

**3. [Rule 1 - Bug in the plan text] The todo tool's registered name is `todo_list`**, not `todo` (the `todo` toolset holds `todo_list`). The allowlist uses `todo_list`.

**4. [Rule 2 - Missing critical] RPC lock is deny-by-default.** The plan lists specific RPCs; a denylist would leave `shell.exec`, `cli.exec`, `process.*`, `mcp.servers.add`, `file.attach`, `complete.path`, `image.*`, `llm.oneshot`, `plugins.manage`, `skills.manage`, `cron.manage`, `connectors.*`, `groups.*`, `billing.*` and 200 others reachable. The allowlist names 55 methods; everything else answers DEGRAM_LOCKED.

**5. [Rule 2 - Missing critical] Tool Search switched off by the config lock.** With it on, `todo_list` was hidden behind `tool_search`/`tool_describe`/`tool_call` bridge tools that are not in the allowlist.

**6. [Plan interpretation] Added `degram.credentials.status`** (presence, scope, expiry, never the token): the plan says "get never returns the token over RPC"; a status call makes that testable and gives plan 12 a verification handle.

**7. [Plan interpretation] Provenance headers not sent.** The relay's `X-DeGram-Context-Scope` defaults to `selection` and the whole-definition consent header is not sent: the OpenAI SDK default headers are fixed at client construction, and a per-request header mechanism belongs to the plan that owns the consent UI (11/14).

**8. [Rule 3 - Blocking] A pristine `git worktree` was created** under a short temp path to establish the tests/tools baseline the 1301-ENV.md left open (not `stash`/`reset`/`clean`); it was removed, including its metadata under the framework `.git/modules/degram/worktrees`.

## Findings for later plans

- **Plan 12 (Electron main):** set `HERMES_DEGRAM=1` in the env of every backend it spawns; call `degram.credentials.set` before `session.create` (an agent cannot be built without the credential); `relayBaseUrl` is the origin plus `/data-service` (no `/degram/v1`); `expiresAt` accepts the ISO string the delegated-token mint returns; renewal is another `set` (the next request uses it); sign-out/revoke is `clear` plus `python -m degram_variant.profiles purge`. A `set` while a turn runs is safe (the provider is read per request).
- **Plan 11:** register the `degram_*` tools with toolset `degram` and the revit tools through MCP server `revit`; the four `degram_*` names and the eight `mcp_revit_*` names are the whole allowlist, any other name is silently not registered (log at debug). A tool module may live at `tools/degram*.py`; any other new module name must be added to `ALLOWED_TOOL_MODULES`. `ensure_scope_profile(..., revit_command=, revit_args=)` fills the revit entry.
- **Plans 11-14:** any additional RPC the Desktop needs (for example `shared_metrics.*`, `usage.bars`, `session.cwd.set`, `profiles.*`) must be added to `ALLOWED_RPC_METHODS` deliberately; it answers `DEGRAM_LOCKED` (code 4403, `error.data.code`) until then. Same for dashboard REST paths (`ALLOWED_REST_PATHS`) and slash commands (`ALLOWED_SLASH_COMMANDS`).
- **Plan 13/14 (copy):** a `CREDENTIALS_*` failure surfaces as the turn's `error` string starting with the code, but the stock agent text around it still says "custom rejected your API key ... Update it in Settings → Providers, or run `hermes setup`". Map the code to DeGram copy in the UI instead of showing that sentence.
- **Plan 15 audit:** plugin discovery still imports bundled plugins in the variant (their tools cannot register, but plugin hooks may run); consider closing it. The picker/`/model` catalogs, update checks, telemetry and free tier are off by config lock and by code.

## Known Stubs

None that block the plan's goal. By design: `config_template.yaml` ships `mcp_servers.revit` disabled with an empty command until plan 11/12 pass the bundled revit-mcp command, and variant degram drops that entry at load; the four `degram_*` tool names are reserved here and registered by plan 11.

## Unverified

- No live relay, no real genpro endpoint, no real token (all forbidden here); the wire was exercised against a local fake OpenAI-compatible SSE server. Whether the production relay accepts `reasoning_effort`, `stream_options` and the tool schema the agent forwards is unverified (plan 08 recorded the same).
- Desktop was not launched; the REST/RPC lock is proven on the Python server (`starlette TestClient`, `handle_request`). That the Desktop renderer boots when every RPC outside the allowlist errors is plan 13's to confirm.
- The socket-guard subprocess test covers dashboard lifespan, MCP discovery with an uninstalled revit command and picker prefetch; a real stdio revit-mcp server under the guard is plan 11/15.

## Threat Flags

None beyond the plan's register. T-1301-10-01 (forbidden tools absent from the registry: subprocess registry test and the assembled-agent test), -02 (token memory-only: log, file-tree, env and RPC-echo scans, including the provider-error dump path), -03 (auxiliary/fallback egress: hostile-config route test, closed chains, socket guard), -04 (provider/model/config RPCs, slash and REST locks, config regenerated and locked in code), -05 (profile per scope, separate `state.db`, purge, path safety) are covered by tests; -06 accepted as planned.

## Self-Check: PASSED

- FOUND (component, `apps/degram`): `degram_variant/{__init__,credentials,provider,lockdown,rest_lock,profiles}.py`, `degram_variant/config_template.yaml`, `tui_gateway/methods_degram.py`, `tui_gateway/contracts/degram.py`, `tests/degram/{__init__,test_credentials_provider,test_lockdown,test_profiles}.py`
- FOUND commits in the component repo: `d2d819e0`, `b1e09d52`, `c27f31cd` (`git -C apps/degram log`); `git -C apps/degram status --short` empty; no deletions in any commit
- Gitlink not bumped; `apps/degram` and `apps/revit-mcp` not staged in the framework
