---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 11
subsystem: degram-agent-read-capabilities
tags: [degram, hermes, variant-degram, grasshopper-bridge, revit-mcp-stdio, document-pinning, context-preview, whole-definition-consent, cancellation, operational-outcomes, tdd]
requires: ["1301-06", "1301-07", "1301-08", "1301-10"]
provides:
  - "degram_variant read capabilities: gh_bridge.py (GhBridgeClient, GH_READ_COMMANDS, GhDocumentSource), revit_bridge.py (RevitBridgeClient, RevitDocumentSource), dg_client.py, documents.py (DocumentsService), context_composer.py (ContextComposer, SNAPSHOT_LIMITS), relay_headers.py, cancel.py, outcomes.py, snapshot.py, runtime.py"
  - "Gateway RPCs degram.documents.list / degram.documents.pin (app null unpins) / degram.context.preview / degram.context.send / degram.context.cancel, with contracts, regenerated TS + OpenRPC, ALLOWED_RPC_METHODS entries"
  - "Toolset degram (tools/degram_tools.py, toolsets.py): degram_project_graph, degram_list_documents, degram_document_snapshot, degram_bridge_status; available only in variant degram"
  - "config_template.yaml mcp_servers.revit: ${DEGRAM_PYTHON} ${DEGRAM_REVIT_MCP_DIR}/main.py, DEGRAM_MODE=1, the eight reads, resources/prompts/sampling/elicitation off, connect 20 s / call 40 s"
  - "Per-request relay provenance headers X-DeGram-Context-Scope and X-DeGram-Whole-Definition-Consent (value true), armed only by degram.context.send"
  - "Relay error bodies (POLICY_DENY, CONSENT_REQUIRED, PROVIDER_*, RELAY_NOT_CONFIGURED, ...) are terminal named outcomes: one request, no unmask probe, the code leads result.error and final_response"
  - "Framework: DG_UNAVAILABLE and ACCESS_DENIED added to spec/degram/OPERATIONAL-OUTCOMES.md and degram_relay.AGENT_OUTCOMES (drift test green)"
affects: [1301-12, 1301-13, 1301-14, 1301-15]
tech-stack:
  added: []
  patterns:
    - "Blocking-socket client with 50 ms poll of a CancelToken and the per-thread interrupt: one code path serves RPC pool threads and agent tool threads"
    - "Revit reads call the registered mcp__revit__* handlers on a bounded worker thread (deadline to BUSY, cancel through the thread interrupt bit under a lock), instead of re-implementing the MCP client"
    - "Preview registry keyed by previewId bound to (user, company, project) and the pin generation; prepare_send embeds the stored payload text unchanged"
    - "One-line variant hooks: effective_request_overrides (headers), prompt.submit (context reset), _summarize_api_error / nonretryable_copy (named outcome text), _unmask_server_error_with_nonstreaming (no second call)"
key-files:
  created:
    - apps/degram/degram_variant/gh_bridge.py
    - apps/degram/degram_variant/revit_bridge.py
    - apps/degram/degram_variant/dg_client.py
    - apps/degram/degram_variant/documents.py
    - apps/degram/degram_variant/context_composer.py
    - apps/degram/degram_variant/relay_headers.py
    - apps/degram/degram_variant/cancel.py
    - apps/degram/degram_variant/outcomes.py
    - apps/degram/degram_variant/snapshot.py
    - apps/degram/degram_variant/runtime.py
    - apps/degram/tools/degram_tools.py
    - apps/degram/tests/degram/test_gh_bridge.py
    - apps/degram/tests/degram/test_revit_bridge.py
    - apps/degram/tests/degram/test_context_composer.py
    - apps/degram/tests/degram/test_cad_cancel.py
    - apps/degram/tests/degram/conftest.py
    - apps/degram/tests/degram/fakes.py
    - apps/degram/tests/degram/fixtures/fake_revit_mcp.py
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-11-SUMMARY.md
  modified:
    - apps/degram/degram_variant/config_template.yaml
    - apps/degram/degram_variant/lockdown.py
    - apps/degram/degram_variant/provider.py
    - apps/degram/tui_gateway/methods_degram.py
    - apps/degram/tui_gateway/contracts/degram.py
    - apps/degram/tui_gateway/methods_prompt.py
    - apps/degram/tui_gateway/server.py
    - apps/degram/apps/shared/src/gateway-contract.generated.ts
    - apps/degram/apps/shared/src/gateway-contract.openrpc.json
    - apps/degram/toolsets.py
    - apps/degram/agent/fast_mode.py
    - apps/degram/agent/api_error_summary.py
    - apps/degram/agent/turn_failure_copy.py
    - apps/degram/agent/chat_completion_helpers.py
    - apps/degram/tests/degram/test_lockdown.py
    - apps/degram/tests/degram/test_profiles.py
    - data-service/degram_relay.py
    - spec/degram/OPERATIONAL-OUTCOMES.md
key-decisions:
  - "Outcomes are an ok RPC result with status error and a code from the closed set; only requests refused for what they are (unknown or stale preview, bad scope, busy session) are JSON-RPC errors with data.code"
  - "The whole-definition consent header is sent as true, not as the previewId: the relay (plan 08) accepts only true or 1; the previewId binding of the consent is local (a preview is bound to scope, pin generation and the credential scope)"
  - "previewId may be chosen by the client so degram.context.cancel can name a read before preview returns; without an id cancel signals every in-flight read"
  - "Pinning needs the document in the bridge's fresh list; identity is re-checked before every read (GH: get_document_identity then definition.documentId of the context; Revit: get_selection_snapshot identity pair), a mismatch returns IDENTITY_MISMATCH and nothing is read"
  - "No document pinned: scope selection degrades to none (project data only, disclosed in requestedScope vs scope); whole-definition without a pin or for Revit is SCOPE_NOT_SUPPORTED"
  - "Relay provenance context is process-wide and reset by any prompt.submit that does not carry the in-process SEND_TICKET, so a later plain message never inherits a whole-definition consent; without a context the scope header is none, never an implicit selection"
  - "Limits (200 objects, 50 parameters per object, 256 KiB) are applied client-side by dropping objects from the tail by binary search; rules are capped at 200 entries of 2000 characters; every cut is disclosed in truncation and inside the payload"
  - "degram_document_snapshot and degram_project_graph take no arguments that could widen the read (no scope, no project); whole-definition scope exists only through the context card and its consent"
  - "Two operational codes added to the framework vocabulary: DG_UNAVAILABLE and ACCESS_DENIED, because D-18 asks for a named cause when the DG server cannot be read and 401/403 on a delegated read must not read as a bridge or provider fault"
metrics:
  duration: ~3 h (wall clock; the full tests/tui_gateway and tests/tools runs dominate)
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-02, DGCL-04, DGCL-06, DGCL-07]  # agent side: document pinning, typed bounded snapshot, preview == sent payload, whole-definition consent, cancel, named outcomes. The Desktop picker/card UI (13/14), Electron env wiring (12) and live GH/Revit runs (15) are later plans
status: complete
---

# Phase 1301 Plan 11: CAD read capabilities and the context disclosure contract Summary

The locked-down DeGram agent can now list and pin one open Grasshopper or Revit document, read its selection through the existing serializers (GH) or the identity-pinned Revit snapshot tool, show exactly what it will send in a preview whose payload text is the very text embedded in the model request, and abandon any bridge read within a second. Everything is proven offline against fake bridges, a fake DG backend and a fake relay, with a real agent turn for the wire checks.

## Authorization and boundaries

Per the orchestrator brief: local commits on component branch `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch/build/dev server/packaging, no Docker, no write to `%LOCALAPPDATA%\hermes` or the installed Hermes profile, no package install, no real provider call, no live Grasshopper/Rhino/Revit/pyRevit connection (loopback fake listeners and a fake stdio MCP server only), `.secrets` not read. The `apps/degram` and `apps/revit-mcp` gitlinks were NOT bumped and not staged in the framework; `python tools/degram/workspace.py verify` keeps reporting gitlink != child HEAD, the expected state until plan 15, and was not worked around.

## Commits

Component repo `apps/degram`, branch `degram/phase-1301` (committing repository: component):

| Task | Commit | Message |
|---|---|---|
| 1 | `95d301a4` | feat(1301-11): GH document pinning, bounded context preview that equals the sent payload |
| 2 | `7ae4fb6a` | feat(1301-11): Revit MCP stdio wiring, document merge, bridge states and the degram toolset |
| 3 | `50cc2246` | feat(1301-11): cancellable CAD reads, whole-definition consent and named relay outcomes |

Framework repo (master): `ca735d9` feat(1301-11): DG_UNAVAILABLE and ACCESS_DENIED operational outcomes for DG backend reads (`data-service/degram_relay.py`, `spec/degram/OPERATIONAL-OUTCOMES.md`), plus the `docs(1301-11)` commit for this SUMMARY, STATE.md and ROADMAP.md. No deletions in any commit.

## What was built

**Task 1 (tracer): GH pin, snapshot, preview equals sent payload.**
- `gh_bridge.py`: `GhBridgeClient` sends only `GH_READ_COMMANDS` (get_canvas_context, get_selection, get_preview_status, get_document_identity) and raises `DEGRAM_LOCKED` before any connection for anything else; the host is the module constant `127.0.0.1` (no parameter, no environment variable); connect 2 s, read 30 s, 10 MiB cap counted in bytes; every wait polls the cancel token. Envelope errors map to BUSY, EXTENSION_NOT_LOADED (UNKNOWN_COMMAND), DOCUMENT_NOT_OPEN (no active document), SETUP_INCOMPLETE (not the DG bridge, malformed, oversized); a refused connection is BRIDGE_OFF. `GhDocumentSource.read_snapshot` checks `get_document_identity` first, then reads `get_selection` and `get_canvas_context` (the existing DG serializer, D-14/D-15) and also requires `definition.documentId` to equal the pinned id.
- `documents.py`: `DocumentsService.list/status/pin/unpin/read_snapshot`; one state per bridge (ready, pinned, busy, off, setup-incomplete, identity-mismatch); nothing pinned until `pin`, even with a single document; pin must find the document in the bridge's fresh list.
- `dg_client.py`: `GET {relayBaseUrl}/graph/{project}` and `/rules/{project}` for the bound project only, delegated Bearer read from the in-memory credential, no redirects, 8 MiB cap, named `DG_UNAVAILABLE` / `ACCESS_DENIED`.
- `context_composer.py`: `preview` returns previewId, summary (project, document, objects, parameters, rules, fragments, bytes, emptySelection), truncation (`{what, kept, total}`), missing (`{what, reason}`) and the exact payload text (short text header with project, document and scope, then compact JSON). `prepare_send` embeds the stored payload unchanged: `payload + "\n\nRequest:\n" + text`; unknown, stale (re-pin, other credential scope) and scope-mismatched previews are refused.
- RPCs, contracts (regenerated `apps/shared` TS and OpenRPC), allowlist entries, `_LONG_HANDLERS` for the three reads (cancel stays inline), and `relay_headers.py` with the per-request headers through `effective_request_overrides`.

**Task 2: Revit stdio wiring, merge, toolset.**
- `config_template.yaml` carries the pinned Revit server block; `profiles.ensure_scope_profile(revit_command=, revit_args=)` still overrides command and args.
- `revit_bridge.py`: `RevitBridgeClient` calls the registered `mcp__revit__*` handlers (only the eight allowlisted names) on a bounded worker thread: BUSY after 40 s, CANCELLED as soon as the token or the turn interrupt fires, never a retry. `RevitDocumentSource` maps `list_open_documents` rows (title, pathName, creationGuid, isActive, isModified) and reads through `get_selection_snapshot` with identity `{creationGuid, pathName}` and 200/50 limits. Adapter outcomes keep their reason (SETUP_INCOMPLETE/ROUTES_NOT_LOOPBACK, NO_DOCUMENT_OPEN, ...); an unconnected adapter is SETUP_INCOMPLETE/REVIT_ADAPTER_NOT_CONNECTED.
- `tools/degram_tools.py` + `toolsets.py`: the four tools of toolset `degram` (variant-only `check_fn`). `degram_document_snapshot` reads the pinned selection (no scope argument), `degram_project_graph` reads graph and rules of the bound project (no project argument; at most 200 nodes, 400 relationships and 256 KiB with the cut disclosed), `degram_list_documents` and `degram_bridge_status` report the picker data.

**Task 3: cancel, deadlines, consent, relay outcomes.**
- `degram.context.cancel(previewId)` closes the GH socket / abandons the MCP call and the preview resolves with `CANCELLED` well under a second (measured under 1 s in tests); a tool-driven read is cancelled by the turn interrupt (`agent.interrupt`, what `session.interrupt` calls) with the partial assistant text kept and no follow-up model call.
- GH read with no answer for 30 s (clock patched) is BUSY, connect refused is BRIDGE_OFF, the fake listener sees exactly one connection (no retry); the Revit deadline is the module constant 40 s.
- Whole-definition: without `consent: true` the composer refuses locally with `CONSENT_REQUIRED`, nothing is armed or submitted; with consent the relay request carries `X-DeGram-Context-Scope: whole-definition` and `X-DeGram-Whole-Definition-Consent: true`; a later plain prompt.submit resets the context to scope `none` (a forged `_degram_send` value does not keep it).
- Relay error bodies are terminal and named: `provider.relay_outcome` finds the code in `detail`/`error`, `terminal_verdict` makes the turn stop (not retryable, no fallback), `_summarize_api_error` and `nonretryable_copy` lead with `CODE: message (reason: ...)`, and the non-streaming "unmask probe" that re-issued a failed 5xx is switched off in variant degram. A policy deny with consent given is denied again on every attempt, one request each.

## TDD

- **Task 1:** RED = collection `ImportError: cannot import name 'gh_bridge' from 'degram_variant'` for both test files (nothing existed); GREEN after the modules and RPCs: 25 + 33 tests, then the FakeGh `Raw` reply and two test-parameter fixes (one test sent an invalid RPC param under `extra="forbid"`).
- **Task 2:** RED = the Revit adapter fixture could not register its tools: `registration of tool 'get_revit_status' as 'mcp__revit__get_revit_status' was rejected by the registry`, which exposed the allowlist naming bug (Deviation 1); then 35 tests green (config template, merge, state mapping, BUSY, snapshot, identity outcomes, child lifecycle, toolset).
- **Task 3:** RED observed on the relay outcomes: two POSTs for every 5xx (the unmask probe) and the stock "rejected this request as malformed" copy for a policy deny, plus a connection-count assertion that forgot the pin read. GREEN: 25 tests.

## Verification

All Python through `HERMES_PYTHON=<apps/degram/.venv python>` and `scripts/run_tests.sh` (no uv download); nothing launched.

| Check | Result |
|---|---|
| `tests/degram` (7 files) | **331 passed, 0 failed**: test_gh_bridge 26, test_context_composer 33, test_revit_bridge 35, test_cad_cancel 25 (new, 119) + credentials 44, lockdown 134, profiles 34 |
| Targeted neighbours of touched modules in the same run (`test_packaging_py_modules`, `test_cli_init`, `test_tools_config`, `test_mcp_tool`, `test_mcp_dynamic_discovery`, `test_mcp_lazy_start`, `test_mcp_capability_gating`, `tools/test_toolsets`, `tools/test_registry`) | all pass |
| 19 agent / acp files that read the touched failure-copy, summary, fast-mode and stream seams | 364 passed; 3 failing tests (2 collection errors `No module named 'acp'`, 1 `~/.hermes` path copy assertion) fail identically on a pristine worktree of the fork at `8b66a510` |
| `tests/tui_gateway` full (1301-ENV.md baseline: 23 known failures) | 2394 passed, 17 failed; all 17 are in the 1301-ENV.md list, none new; `tests/tui_gateway/contracts/test_generated.py` passes (TS/OpenRPC fresh) |
| `tests/tools` full (849 s, inside the 15 min limit; no ENV baseline existed) | 8975 passed, 248 failed in 71 files (Windows/env: file tools, browser, bot_desktop, mcp oauth, tirith, ...). The same 71 files on the pristine worktree: 1669 passed, **248 failed**, the same count. The two sets differ by 8 vs 3 file-tool tests that flip between runs (re-run solo: 12 file-tool failures, in untouched modules) |
| `data-service/tests/test_degram_relay.py` + `test_degram_policy.py` after the vocabulary extension | 74 passed (spec block and `OPERATIONAL_OUTCOMES` equal in both directions) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan 10] The Revit tool allowlist used names MCP never registers.**
- **Found during:** Task 2 (fake adapter fixture: "registration ... was rejected by the registry").
- **Issue:** `REVIT_TOOL_NAMES` held `mcp_revit_<tool>`; the Hermes MCP client registers `mcp__<server>__<tool>`, so the registry gate would have refused every Revit tool in a real session.
- **Fix:** names changed to `mcp__revit__*` in `lockdown.py`, plan 10's `test_lockdown.py`, and the new tests; the subprocess registry test now also requires the degram toolset.
- **Files:** `degram_variant/lockdown.py`, `tests/degram/test_lockdown.py`. **Commit:** `7ae4fb6a`.

**2. [Rule 1 - Bug in plan text] The consent header value.** The plan says `X-DeGram-Whole-Definition-Consent: previewId`; the relay accepts only `true` or `1` (`_CONSENT_VALUES`, plan 08) and would answer 428. The header is sent as `true`; the previewId binding is local. **Commit:** `95d301a4`.

**3. [Rule 2 - Missing critical] Two operational codes were needed.** `DG_UNAVAILABLE` and `ACCESS_DENIED` for DG graph/rules reads (D-18 names "DG server unavailable"; 401/403 must not read as a bridge fault). Added to the machine-checked block and `degram_relay.AGENT_OUTCOMES`; a component test checks that every code the component emits is in the spec block. **Framework commit:** `ca735d9`.

**4. [Rule 3 - Blocking] Hooks outside the plan's file list.** `agent/fast_mode.py` (the one per-request seam for headers), `tui_gateway/methods_prompt.py` (context reset), `tui_gateway/server.py` (`_LONG_HANDLERS`), `agent/api_error_summary.py` and `agent/turn_failure_copy.py` (named outcome text), `agent/chat_completion_helpers.py` (unmask probe off), `tui_gateway/contracts/degram.py` and the regenerated `apps/shared` files (every RPC needs a contract), `degram_variant/provider.py` (outcome mapping lives next to the credential verdict).

**5. [Plan interpretation] Blocking sockets, not an asyncio stream client.** The bridge client polls a cancel token every 50 ms from the RPC pool thread or the agent's tool thread; no event loop is involved, which keeps cancel and the patched-clock deadline test simple.

**6. [Plan interpretation] Contract shape.** `previewId` is an optional client-chosen param of `degram.context.preview` (so cancel can name a read in flight); `degram.documents.pin` with `app: null` unpins (no sixth RPC); `degram.documents.list` and `status` carry the same `status: ok` field as every other result.

**7. [Plan interpretation] Template enabled.** The template's Revit block is now `enabled: true` with placeholders (plan 10 shipped it disabled and empty); plan 10's profile test was updated. An unset `DEGRAM_PYTHON` keeps the literal placeholder, the spawn fails and the Revit group reports setup-incomplete.

**8. New files not in `files_modified`:** `outcomes.py`, `cancel.py`, `snapshot.py`, `runtime.py`, `relay_headers.py`, and the test support `conftest.py`, `fakes.py`, `fixtures/fake_revit_mcp.py`. The cancel/deadline mechanics were implemented with Tasks 1 and 2; Task 3's commit holds their end-to-end tests plus the relay-outcome work.

## Findings for later plans

- **Plan 12 (Electron main):** set `DEGRAM_PYTHON` and `DEGRAM_REVIT_MCP_DIR` for the backend (or pass `revit_command` / `revit_args` to `ensure_scope_profile`), plus `HERMES_DEGRAM=1`. **Risk:** `apps/revit-mcp/main.py` imports `mcp.server.fastmcp.FastMCP`; the gateway venv has `mcp` 2.0.0, which has no `mcp.server.fastmcp` (verified by import). If the adapter runs on that interpreter it will not start. The bundled Python for the adapter must carry an `mcp` 1.x, or the adapter must be ported to the 2.x `MCPServer` API; the fake adapter in the tests uses the 2.x API.
- **Plans 13/14 (UI):** bridge states arrive as `group.state` (ready, pinned, busy, off, setup-incomplete) and `bridgeState` on outcomes (identity-mismatch added); `reason` carries ROUTES_NOT_LOOPBACK, NO_DOCUMENT_OPEN, REVIT_ADAPTER_NOT_CONNECTED, ... for the matching copy. A turn failure's `error` and `final_response` start with the outcome code (`POLICY_DENY: ... (reason: ...)`), so the UI can map the code to DeGram copy and must never offer consent for POLICY_DENY. Send flow: preview (optionally with a client previewId, cancel by that id) then `degram.context.send {session_id, previewId, text, consent}`; `whole-definition` needs `consent: true`; `unpin` is `degram.documents.pin {app: null}`. A running session answers `SESSION_BUSY`.
- **Plan 15 (audit/live):** (a) the stock transport retry ladder is untouched: a refused or reset connection to the relay (no named relay body) still goes through `agent.api_max_retries` (default 3) and `HERMES_STREAM_RETRIES` (default 2); closing it fully means a `lock_config` value and an env default, a deliberate follow-up. (b) Tool results (`degram_document_snapshot`, `degram_project_graph`) reach the model without the pre-send card; they are bounded exactly like a preview and appear in the transcript as tool calls. (c) The compression auxiliary request carries no scope header (relay default `selection`, no consent). (d) Revit residual from plan 07: only `get_selection_snapshot` is identity-pinned; the other allowlisted reads (`get_element_properties`, `list_levels`, `get_current_view_info`, `list_category_parameters`, `get_revit_model_info`) read Revit's active document and remain callable by the model. (e) The relay provenance context is process-wide (one scope per gateway process, D-19).

## Not verified (honest limits)

- No live Grasshopper, Rhino, Revit or pyRevit session, no real relay, no real token, no real provider (all forbidden). The wire shapes come from the C# sources and plan 06/07 documents, exercised against fakes: the `CanvasContextExtractor` output is a hand-built `cg-context-1` fixture, and the Revit snapshot is a fake stdio server speaking the DEGRAM.md result shape.
- The real `apps/revit-mcp` server was not started (see the mcp 2.x risk above).
- `degram.context.cancel` and the thread interrupt were exercised on Windows only; the abandon-within-1 s measurement is under test load, not under a busy Revit.
- Desktop was not launched: the five new RPCs are proven through `handle_request` (contract validation on), not through the renderer.

## Known Stubs

None. The `fragments` count in the preview summary is always 0 by design (no fragment source exists in 1301).

## Threat Flags

None beyond the plan's register. T-1301-11-01 (mutating GH commands): allowlist test, nothing reaches the listener. -02 (document substitution): identity first and the context's documentId, tested for both bridges. -03 (hidden or oversized context): preview == request body byte for byte through a real agent turn, limits and disclosure, consent. -04 (cross-project reads): the DG client has no project parameter and the paths are asserted. -05 (hung bridge): deadlines, cancel, BUSY, no retry. -06 (GH host redirect): constant host, no knob (test asserts the signature and the environment variable are inert).

## Self-Check: PASSED (one cleanup item open, see the last section)

- FOUND (component, `apps/degram`): `degram_variant/{gh_bridge,revit_bridge,dg_client,documents,context_composer,relay_headers,cancel,outcomes,snapshot,runtime}.py`, `tools/degram_tools.py`, `tests/degram/{test_gh_bridge,test_revit_bridge,test_context_composer,test_cad_cancel,conftest,fakes}.py`, `tests/degram/fixtures/fake_revit_mcp.py`
- FOUND commits in the component repo: `95d301a4`, `7ae4fb6a`, `50cc2246`; framework commit `ca735d9`
- Gitlink not bumped; `apps/degram` and `apps/revit-mcp` not staged in the framework; no deletions in any commit
- Open item for the caller: see "Cleanup left for the owner" below

## Cleanup left for the owner

Two leftovers could not be removed because the delete commands were denied by the permission classifier, and they were not worked around:
1. Eight untracked junk files in the `apps/degram` working-tree root created by the full `tests/tools` run (names start with the literal path `C:\Users\Admin\AppData\Local\Temp\hermes-pytest\...`: `snapshot.sh.tmp.*` and `out.bin`); `git -C apps/degram status --short` lists only these eight entries, all untracked, no tracked change.
2. The empty metadata directory `.git/modules/degram/worktrees/dgp-t` of the removed pristine comparison worktree (`git worktree list` no longer shows it; the directory itself would not delete: Permission denied).
