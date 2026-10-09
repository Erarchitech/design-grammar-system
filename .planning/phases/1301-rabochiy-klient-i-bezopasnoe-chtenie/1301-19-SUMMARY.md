---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 19
subsystem: desktop-client
tags: [degram, error-card, relay-errors, preview-deadlines, hidden-surfaces, react, python]

requires:
  - phase: 1301-18
    provides: request-lifecycle, outcome-copy (named codes), hidden-surfaces gate, scope route
provides:
  - "Failed-turn card and error toast in variant degram: the DeGram outcome sentence only (degramFailureHeadline), no provider/key/diagnostics text or raw Details (G-4)"
  - "Six hidden-surface ids for the stock card actions: stock-error-update-key, -switch-provider, -sign-in, -open-logs, -send-diagnostics, -copy-details (G-4, DGCL-02)"
  - "Relay 401/403 without a named code -> CREDENTIALS_INVALID / ACCESS_DENIED, terminal (auth_permanent), never the stock auth/api_key surface (G-4)"
  - "Preview deadlines below the preview RPC timeout: REVIT_PREVIEW_DEADLINE_S 20, GH_PREVIEW_READ_TIMEOUT_S 20 (shared by the three GH calls), PREVIEW_RULES_READ_TIMEOUT_S 15, PREVIEW_RPC_TIMEOUT_MS 45_000 (G-14)"
  - "classifyPreviewError + PREVIEW_TIMEOUT outcome: a preview RPC timeout reads as a timeout with its seconds; only gateway transport failures read as DG unreachable (G-14)"
affects: [1301-16, 1301-23, DGCL-02, DGCL-04, DGCL-06]

tech-stack:
  added: []
  patterns:
    - "Hidden-surface ids are per entry point (one id per stock card action), pinned by the SITES source-scan test"
    - "A shared read budget: the first bridge call gets the whole deadline, later ones what the earlier ones left"

key-files:
  created:
    - apps/degram/tests/degram/test_relay_error_mapping.py
  modified:
    - apps/degram/apps/desktop/src/degram/hidden-surfaces.ts
    - apps/degram/apps/desktop/src/degram/hidden-surfaces.test.tsx
    - apps/degram/apps/desktop/src/components/assistant-ui/thread/assistant-message.tsx
    - apps/degram/apps/desktop/src/components/assistant-ui/thread/assistant-message.test.tsx
    - apps/degram/apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/status.ts
    - apps/degram/apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/status.test.ts
    - apps/degram/apps/desktop/src/degram/outcome-copy.ts
    - apps/degram/apps/desktop/src/degram/request-lifecycle.ts
    - apps/degram/apps/desktop/src/degram/use-degram-gateway.ts
    - apps/degram/apps/desktop/src/degram/context-card.tsx
    - apps/degram/apps/desktop/src/degram/chat.test.tsx
    - apps/degram/degram_variant/provider.py
    - apps/degram/degram_variant/revit_bridge.py
    - apps/degram/degram_variant/gh_bridge.py
    - apps/degram/degram_variant/documents.py
    - apps/degram/degram_variant/context_composer.py
    - apps/degram/degram_variant/dg_client.py
    - apps/degram/tui_gateway/server.py
    - apps/degram/tests/degram/test_cad_cancel.py
    - apps/degram/tests/degram/test_revit_bridge.py
    - apps/degram/tests/degram/test_gh_bridge.py
    - apps/degram/tests/degram/test_context_composer.py

key-decisions:
  - "Under variant degram the card's raw 'Details' text is hidden too (id stock-error-copy-details): it carries the provider name and key hint that the headline replacement removes"
  - "The model picker and free-tier card actions reuse the existing ids model-picker-overlay and free-tier instead of new ids"
  - "A failure text with no outcome code reads as errors.modelUnavailable (plan), not errors.unknown: the raw text is never the headline"
  - "The Grasshopper preview deadline is one budget for its three sequential bridge calls; three 20 s reads would still outlive the 45 s RPC"
  - "The tool path (agent calls) keeps REVIT_DEADLINE_S 40 / READ_TIMEOUT_S 30; only the preview path is shortened"

patterns-established:
  - "Renderer-only outcome codes (ROUTE_MISMATCH, PREVIEW_TIMEOUT) live in EXTRA_CODES, outside the machine-checked spec vocabulary"

requirements-completed: []

coverage:
  - id: D1
    description: "A failed turn in variant degram shows the DeGram outcome sentence and none of Update API key, Switch provider, Sign in again, Open logs, Send diagnostics, Copy error details; the toast carries the same copy; no provider name"
    requirement: "DGCL-02"
    verification:
      - kind: unit
        ref: "assistant-message.test.tsx (degram card x3, upstream cases unchanged), hidden-surfaces.test.tsx (ids + source sites), status.test.ts (toast x2)"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 2.6 error path on 0.1.6 (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D2
    description: "A relay 401/403 without a named code reaches the renderer as CREDENTIALS_INVALID / ACCESS_DENIED, terminal, only in variant degram"
    requirement: "DGCL-02"
    verification:
      - kind: unit
        ref: "tests/degram/test_relay_error_mapping.py (13)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A preview whose bridge does not answer returns BUSY within 20 s, below the 45 s preview RPC timeout; tool calls keep 40 s"
    requirement: "DGCL-04, DGCL-06"
    verification:
      - kind: unit
        ref: "test_cad_cancel.py constants + worst-case arithmetic, test_revit_bridge.py TestRevitPreviewDeadline, test_gh_bridge.py TestPreviewBudget, test_context_composer.py TestPreviewBudget"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 4.14 (Revit modal dialog open) on 0.1.6 (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D3b
    description: "A preview RPC timeout reads as the timeout copy with its seconds; only a gateway transport failure reads as DG unreachable"
    requirement: "DGCL-04, DGCL-06"
    verification:
      - kind: unit
        ref: "src/degram/chat.test.tsx 'preview failures name their cause' (5 cases)"
        status: pass
    human_judgment: false

duration: ~1h 15m
completed: 2026-10-09
status: complete
---

# Phase 1301 Plan 19: Error-path cards and preview deadlines Summary

**A failed turn in DeGram now shows only DeGram's own outcome sentence (no provider, key or diagnostics surface), a relay 401/403 is a named DeGram code, and a blocked Revit or Grasshopper answers BUSY at 20 s, inside the 45 s preview RPC, with RPC timeouts named as timeouts.**

## Performance

- **Completed:** 2026-10-09
- **Tasks:** 3/3 (Tasks 1-3 are one component commit, as the plan prescribes)
- **Execution:** sequential executor, no checkpoints

## Accomplishments

- **G-4 card and toast.** `ErrorCardHeadline` renders `degramFailureHeadline(copy, errorText, ctx)` under `$degramEnabled` (one `data-testid="degram-error-headline"` line, no title, no raw Details); `ErrorRecoveryActions` gates every provider-flavoured action by its own hidden-surface id. The gateway `error` toast (`status.ts`) uses the same sentence, drops the raw detail, and collapses duplicates on the sentence.
- **G-4 relay codes.** `provider.relay_outcome` falls back, in variant degram only, to the status in the cause chain: 401 -> `CREDENTIALS_INVALID`, 403 -> `ACCESS_DENIED`. The summary leads with the code (`parseFailureText` finds it), `named_outcome_copy` returns it as the chat copy, and `terminal_verdict` marks it `auth_permanent`, not retryable, no rotate/fallback.
- **G-14 deadlines.** `REVIT_PREVIEW_DEADLINE_S = 20.0` (tool `REVIT_DEADLINE_S = 40.0` unchanged), `GH_PREVIEW_READ_TIMEOUT_S = 20.0` as a shared budget, `PREVIEW_RULES_READ_TIMEOUT_S = 15.0` through a per-call read timeout in `DgClient`; worst case 20 + 5 + 15 = 40 s < `PREVIEW_RPC_TIMEOUT_MS = 45_000`, which `previewContext` now passes. The stale "up to 30 s" comment in `tui_gateway/server.py` states the budget.
- **G-14 classification.** `classifyPreviewError`: `request timed out after Ns` -> `PREVIEW_TIMEOUT` (copy `errors.timeout` with N), gateway transport text -> `DG_UNAVAILABLE`, anything else -> `UNKNOWN`. The context card passes the seconds into the sentence.

## Task Commits

All in the component repo `apps/degram`, branch `degram/phase-1301`, local, not pushed, gitlink not bumped (plan 23):

1. Tasks 1-3: `199ef7cd` fix(1301-19): DeGram copy on failed turns; preview deadlines below the RPC timeout (G-4, G-14)

## Verification

- `python -m pytest tests/degram tests/tui_gateway/test_failed_turn_retention.py -q` (apps/degram `.venv`, the system Python lacks `ruamel`): 384 passed.
- `npm run typecheck` (renderer, electron, e2e, builder config): pass.
- `npx vitest run --project ui src/degram src/components/assistant-ui src/lib src/app/session`: 371 files, 3855 tests pass.
- eslint on all touched TS/TSX files: clean after `--fix` (import order in `chat.test.tsx`).
- Not run: live recheck of UAT 2.6 (error path) and 4.14 (Revit modal dialog) on 0.1.6 (plan 16 Task 3). Unverified.
- `workspace.py verify`: only the tolerated "Submodule gitlink does not match the selected component HEAD".
- The pre-existing failures noted by plan 18 (`store/voice-prefs.test.ts`, `plugins/hermes-bots/cron-detail.test.tsx`) are outside the paths run here and did not appear.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A per-read Grasshopper timeout would not have met the 45 s RPC budget**
- **Found during:** Task 2
- **Issue:** `GhDocumentSource.read_snapshot` makes three sequential bridge calls (identity, selection, canvas context). `GH_PREVIEW_READ_TIMEOUT_S = 20` applied per read allows 60 s, above `PREVIEW_RPC_TIMEOUT_MS`, so the 0.1.5 symptom would persist on a busy canvas.
- **Fix:** `read_snapshot(..., deadline_s)` shares one budget: the first call gets all of it, later calls what is left, `BUSY` once exhausted. `DocumentsService.read_snapshot` forwards `deadline_s` only when given, so the `DocumentSource` protocol stays compatible.
- **Files modified:** `degram_variant/gh_bridge.py`, `degram_variant/documents.py`
- **Commit:** `199ef7cd`

**2. [Rule 2 - Missing critical functionality] Raw error text and two more provider doors on the card**
- **Found during:** Task 1
- **Issue:** the collapsed "Details" disclosure carries the raw text (provider name, key hint), and `Choose a model`, `Sign in (free tier)`, `Open Hermes folder` are provider/log doors the six listed ids do not cover.
- **Fix:** Details hidden under `stock-error-copy-details`; Choose a model reuses `model-picker-overlay`, free-tier sign-in reuses `free-tier`, Open Hermes folder reuses `stock-error-open-logs`. `Start new session`, `Edit message`, `Compress` stay.
- **Files modified:** `assistant-message.tsx`
- **Commit:** `199ef7cd`

**3. [Rule 3 - Blocking] The unnamed-code seconds were dropped**
- **Found during:** Task 2 (vitest, "No answer within 0 s")
- **Issue:** `parseFailureText` returns early with no `seconds` when the text names no code, so the preview timeout lost its figure.
- **Fix:** `classifyPreviewError` writes the code into the message (`PREVIEW_TIMEOUT: request timed out after 45s`), and `context-card.tsx` passes the parsed seconds.
- **Files modified:** `request-lifecycle.ts`, `context-card.tsx`
- **Commit:** `199ef7cd`

### Design adjustments within the plan

- Files beyond `files_modified`: `degram_variant/documents.py`, `gateway-event/status.test.ts`, `src/degram/context-card.tsx`.
- 401/403 mapping is gated by `is_degram()`; stock variants keep their classifier untouched (tested).
- `tools` path of the GH bridge keeps `READ_TIMEOUT_S = 30`; the send-time re-read in `prepare_send` keeps tool deadlines (the plan names only the preview path).
- Tests were written with the implementation in one pass; no separate RED run was recorded.

## Deferred Issues

None from this plan. The send-time snapshot re-read (`context_composer.prepare_send`) still uses the 40 s / 30 s tool deadlines; it is a send, not a preview, and was not part of G-14.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-1301-19-01 (headline replaced, raw details and copy-details hidden), T-1301-19-02 (Send diagnostics hidden under degram), T-1301-19-03 (classified preview errors keep the cause) implemented.

## Self-Check: PASSED

Commit `199ef7cd` found in `apps/degram`; `test_relay_error_mapping.py` exists; no tracked file in `apps/degram` is modified after the commit.
