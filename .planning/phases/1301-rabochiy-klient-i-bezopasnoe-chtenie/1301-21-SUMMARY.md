---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 21
subsystem: desktop-client
tags: [degram, pinned-documents, two-pins, context-payload, revit, grasshopper, scope-strip, context-card, python, electron-renderer]

requires:
  - phase: 1301-19
    provides: per-bridge preview deadlines (20 s) and the outcome copy this plan reuses for exclusion rows
  - phase: 1301-18
    provides: route guard in sendBlockedReason and composerGate (kept first)
  - phase: 1301-11
    provides: ContextComposer, DocumentsService, degram.documents.* RPCs
provides:
  - "DocumentsService keeps one pin per bridge (_pins keyed by app): pin replaces only its bridge, unpin(app), unpin_all(), pinned -> {app: doc}, read_snapshots(scope, project, cancel, deadline_s per app) reading each pinned bridge concurrently (D-29)"
  - "Preview/payload with one snapshot section per readable pinned document ('snapshots'), summary {project, documents[{app,name,path,objects,parameters,truncated,emptySelection}], rules, fragments, bytes, excluded[{app,name,code,reason,message,bridgeState}]}; limits per document, 256 KiB on the whole body, truncation entries carry the app"
  - "RPC degram.documents.unpin {app | null} (contract, lockdown allowlist, regenerated apps/shared gateway contract + OpenRPC)"
  - "Agent tool degram_document_snapshot returns both pinned selections (snapshots[], excluded[]); descriptions name the pinned Revit model and/or Grasshopper definition"
  - "Renderer: DocumentsStore.pinned / mismatch / pinError per bridge; per-bridge unpin in the picker; strip 'Documents: n' + per-bridge pinned name and accent dot; Context card with one line per document, project line, 'not included' warn rows; per-bridge send gating; composer-focus re-read"
affects: [1301-16, 1301-23, DGCL-04, DGCL-07]

tech-stack:
  added: []
  patterns:
    - "One pin per bridge: every store/service operation names its bridge and touches only that bridge's entry"
    - "A bridge outcome is an exclusion row of the preview, not a failure of the preview: the other bridge and the project data still go out"
    - "Effective scope of a payload (none / selection / whole-definition) is computed from what was actually read"

key-files:
  created: []
  modified:
    - apps/degram/degram_variant/documents.py
    - apps/degram/degram_variant/context_composer.py
    - apps/degram/degram_variant/lockdown.py
    - apps/degram/tui_gateway/methods_degram.py
    - apps/degram/tui_gateway/contracts/degram.py
    - apps/degram/tools/degram_tools.py
    - apps/degram/apps/shared/src/gateway-contract.generated.ts
    - apps/degram/apps/shared/src/gateway-contract.openrpc.json
    - apps/degram/tests/degram/test_context_composer.py
    - apps/degram/tests/degram/test_revit_bridge.py
    - apps/degram/tests/degram/test_gh_bridge.py
    - apps/degram/tests/degram/test_cad_cancel.py
    - apps/degram/apps/desktop/src/degram/use-degram-gateway.ts
    - apps/degram/apps/desktop/src/degram/documents-store.ts
    - apps/degram/apps/desktop/src/degram/document-picker.tsx
    - apps/degram/apps/desktop/src/degram/scope-strip.tsx
    - apps/degram/apps/desktop/src/degram/connected-scope-strip.tsx
    - apps/degram/apps/desktop/src/degram/context-card.tsx
    - apps/degram/apps/desktop/src/degram/request-lifecycle.ts
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/degram/chat.test.tsx
    - apps/degram/apps/desktop/src/components/assistant-ui/thread/assistant-message.tsx
    - apps/degram/apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/status.ts

key-decisions:
  - "A bridge failure at preview time (IDENTITY_MISMATCH, DOCUMENT_NOT_OPEN, BUSY, BRIDGE_OFF, setup states incl. ROUTES_NOT_LOOPBACK) is returned as summary.excluded with the preview still status ok; CANCELLED still ends the whole preview. A preview-level error (credentials, whole-definition without a GH pin, DG errors) keeps the old 'read failed' path"
  - "sendBlockedReason returns 'mismatch' only when every pinned document is flagged identity-mismatch; BUSY / not-loopback on the only pinned bridge does not block (project data still goes out, the card says the document is not included). This follows the plan literally"
  - "The payload's effective scope is derived from what was read: none when every pinned document was excluded, selection when Revit was read but the GH definition was excluded, whole-definition only while the GH definition was read whole; requestedScope keeps what the user asked for"
  - "Bridges are read concurrently (one thread each, own deadline) so two slow bridges cost one deadline, keeping the 20 + 5 + 15 s = 40 s worst case under the 45 s preview RPC timeout"
  - "Whole-definition scope: Revit contributes its selection while the GH definition is read whole; the card control is shown only with a GH pin and the preview request falls back to the selection when the GH pin is gone"

patterns-established:
  - "Payload body is {project, scope, documents[], excluded[], rules, fragments, snapshots[], truncation[], missing[]}; header line 'documents: name [app]; ...'"
  - "Preview exclusions feed the documents store (noteBridgeOutcome per excluded app, noteDocumentsRead clears a stale mismatch of a document that was read)"

requirements-completed: []

coverage:
  - id: D1
    description: "A Revit model and a Grasshopper definition are pinned at the same time; pinning on one bridge never unpins the other; each picker group has its own Unpin; a project switch clears both pins"
    requirement: "DGCL-04"
    verification:
      - kind: unit
        ref: "tests/degram test_revit_bridge.py TestTwoPins (coexist, unpin one/all, scope reset), test_context_composer.py TestRpc unpin x3; chat.test.tsx picker (one pin per bridge, rollback of one bridge, unpin() both), card (project switch clears both pins)"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 4.7-4.13 on 0.1.6 with both pins (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D2
    description: "The Context card shows one line per pinned document and one project line, and the payload carries one snapshot section per readable pinned document exactly as previewed (preview == sent bytes); limits apply per document, 256 KiB to the whole body, truncation disclosed per document"
    requirement: "DGCL-07"
    verification:
      - kind: unit
        ref: "TestTwoPins (one preview two sections, summary == sections, prepare_send embeds the preview payload, per-document limits and disclosure, 256 KiB cap over both), TestSend; chat.test.tsx 'one line per pinned document and one project line', badges name the document"
        status: pass
      - kind: manual_procedural
        ref: "live payload expansion, >200 truncation and whole-definition confirm on 0.1.6 (plan 16 Task 3; blocked before by G-7)"
        status: unverified
    human_judgment: false
  - id: D3
    description: "Identity mismatch, a closed document, BUSY or ROUTES_NOT_LOOPBACK on one bridge excludes only that bridge's document ('not included' warn row), Send stays enabled for the rest, and nothing is ever re-pinned or switched; Send is blocked only when every pinned document is gone"
    requirement: "DGCL-04"
    verification:
      - kind: unit
        ref: "TestTwoPins (GH mismatch, not-loopback, busy concurrent read, never unpinned); chat.test.tsx (excluded row + Badge warn, BUSY/not-loopback rows, Send blocked only when all mismatched, unpinning lifts it, strip keeps the other bridge's dot)"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 4.13 and 4.16 on 0.1.6"
        status: unverified
    human_judgment: false
  - id: D4
    description: "Whole-definition scope stays available only for the pinned Grasshopper definition; with both pins only the GH definition expands whole, Revit keeps its selection; consent dialog counts the GH document"
    requirement: "DGCL-07"
    verification:
      - kind: unit
        ref: "TestTwoPins whole-definition x3; chat.test.tsx control only with a GH pin, dialog counts 5 objects / 9 parameters from the GH document, fallback to the selection without a GH pin"
        status: pass
    human_judgment: false
  - id: D5
    description: "The Context card also re-reads when the composer gains focus (UAT 4.8), not on focus moving inside the composer, not while a read or turn is running, not with no pin"
    requirement: "DGCL-07"
    verification:
      - kind: unit
        ref: "chat.test.tsx 'the card re-reads when the composer gains focus' x2"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 4.8 (changed Revit selection) on 0.1.6"
        status: unverified
    human_judgment: false

duration: ~3h
completed: 2026-10-09
status: complete
---

# Phase 1301 Plan 21: One pinned document per bridge Summary

**The agent now holds one pinned document per bridge and reads both in one request (Revit selection plus Grasshopper selection or whole definition), a problem on one bridge leaves only that document out of the request with a warn row while the other document and the project data still send, and the card re-reads when the composer gains focus.**

## Accomplishments

- **Python pins (Task 1).** `DocumentsService._pins` is keyed by bridge; `pin` replaces only its bridge, `unpin(app)` and `unpin_all()` bump the generation, `list` marks each bridge's pinned row and returns `pinned: {app: doc}` (`{}` when none), `read_snapshots` reads every pinned bridge with its own deadline, in parallel when there are two, returning a snapshot or the bridge's `BridgeError` per app. Whole-definition scope is passed to the Grasshopper source only; Revit always reads its selection.
- **Payload.** `ContextComposer._compose` builds one section per readable document with the limits applied per document, binary-searches one common per-document cap so the whole body fits 256 KiB, and lists unread documents under `excluded` (also inside the payload body so the model is told). Truncation entries carry `app`. `agent_snapshot` returns both selections plus `excluded` and raises the first outcome only when no document could be read. `prepare_send` is unchanged: stale on any pin change (generation), consent for whole-definition.
- **RPC.** `degram.documents.unpin {app | null}` (contract, lockdown allowlist, regenerated TypeScript contract and OpenRPC); the legacy `pin {app: null}` unpins all and returns `{}`.
- **Renderer (Task 2).** `DocumentsStore.pinned`, `mismatch` and `pinError` are per bridge; `pinRow` replaces and rolls back only its bridge; `unpin(app?)`. The picker has a per-bridge Unpin in each group heading. The strip document segment reads «Выбрать документ» / «Документы: n» and each bridge segment carries its pinned name and accent dot (neutral «другой файл» when mismatched). The card shows `project · rules · fragments · size`, one `document · objects · parameters` line per pinned document, `«{document}: не включён — {reason}»` warn rows, per-document truncation badges, and the whole-definition control only with a GH pin. `refreshPreview` reads whenever a pin exists unless every pinned document is already known gone; exclusions and read documents feed the store so a stale mismatch clears. Composer focus (`focusin` arriving from outside `[data-slot="composer-root"]`) re-reads under the same guards as window focus.

## Task Commits

All three tasks end in one component commit, as the plan prescribes (tasks 1 and 2 say "do not commit yet", task 3 commits):

1. Tasks 1-3, component repo `apps/degram`, branch `degram/phase-1301`, local, not pushed, gitlink not bumped (plan 23): `02993674` feat(1301-21): one pinned document per bridge (D-29, G-13)

## Verification

- `apps/degram/.venv/Scripts/python.exe -m pytest tests/degram tests/tui_gateway/contracts -q`: 404 passed (381 in tests/degram before the plan; 400 now, 19 new, 15 of them in TestTwoPins; plus the 4 gateway-contract tests).
- `npm run typecheck` (renderer, electron, e2e, builder config): pass.
- `npx vitest run --project ui src/degram`: 9 files, 211 tests pass (chat.test.tsx: 100 tests, rewritten for two pins with 15 new cases).
- `npx vitest run --project electron electron/degram`: 12 files, 218 tests pass.
- `npx vitest run --project ui` (whole project): 10766 passed, 3 failed: `src/store/voice-prefs.test.ts` x2 ("expected 'false' to be null") and `src/plugins/hermes-bots/cron-detail.test.tsx` x1 ("Overdue since" label), the same three plans 18 and 20 reported. They fail when run alone; neither file imports anything this plan changed (`@/hermes`, `@/lib/voice-stop-word`, `./i18n-test-helper`). They were not run against a clean checkout, so "pre-existing" is shown by the import graph only, not verified.
- eslint on `src/degram` and the two touched stock files: 0 errors (padding warnings fixed with `--fix`). prettier clean on `context-card.tsx` and `scope-strip.tsx` (clean at base); `request-lifecycle.ts` and `chat.test.tsx` were already prettier-dirty at the base commit and were not reformatted wholesale.
- `python tools/degram/workspace.py verify`: only the tolerated "Submodule gitlink does not match the selected component HEAD".
- Not run: live recheck of UAT 4.7-4.13, 4.16 and the DGCL-07 payload steps on 0.1.6 (plan 16 Task 3), any Desktop launch (not authorized). Unverified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stock files outside `files_modified` read the single pinned document**
- **Found during:** Task 2
- **Issue:** `components/assistant-ui/thread/assistant-message.tsx` and `app/session/hooks/use-message-stream/gateway-event/status.ts` used `documents.pinned?.name` for the failure headline, which no longer type-checks.
- **Fix:** both use the new `pinnedName(store, app?)` helper (that bridge's pinned document, else the first pinned one).
- **Files modified:** the two files above
- **Commit:** `02993674`

**2. [Rule 3 - Blocking] Generated gateway contract and lockdown allowlist**
- **Found during:** Task 1
- **Issue:** a new RPC needs `apps/shared/src/gateway-contract.generated.ts`, `gateway-contract.openrpc.json` (generated by `scripts/gen_gateway_contracts.py`, diffed by CI) and an entry in `degram_variant/lockdown.py`'s method allowlist, none listed in `files_modified`.
- **Fix:** regenerated with the script; `degram.documents.unpin` added to the allowlist (inline, not in the threaded long-RPC set: it is instant).
- **Commit:** `02993674`

**3. [Rule 1 - Test fidelity] The scripted gateway named every pinned document 'tower.gh'**
- **Found during:** Task 2
- **Issue:** the chat.test fake pinned Revit rows under the GH name; with two pins that hides name mix-ups. The "named failures" cases that pin Revit therefore now expect `Tower.rvt`.
- **Fix:** the fake backend keeps one pin per bridge with the right names, `unpin`, and per-app exclusions.

### Design adjustments within the plan

- `pinned` in list/unpin answers is `{}` (not `null`) when nothing is pinned; `summary.document/objects/parameters/emptySelection` moved into `summary.documents[]`; the payload body key `snapshot` became `snapshots[]` and `document` became `documents[]`/`excluded[]`; the header line reads `documents: ...`. The payload shape is internal to the agent turn (the relay sees only the headers); the spec contracts under `spec/` do not describe this body, none was edited.
- The plan names the i18n key `degram.strip.documentsCount`; it is `strip.documentsCount` on `DegramCopy` (and `context.excluded`), as the existing copy tree has no `degram.` prefix inside the object.
- Beyond `files_modified`: the picker, the strip and `use-degram-gateway.ts` parsing were rewritten as listed; `test_cad_cancel.py`, `lockdown.py`, `apps/shared/...` were touched as above.
- Tests were adapted and added after the implementation in one pass (the Python suite went red on 29 existing assertions first, then green); no separate RED commit exists. Tasks 1-3 share one commit.
- Preview-level bridge errors (a fake or an older agent returning `status: error` with a bridge code) still show the old inline read-error with Retry; the real agent no longer produces them for bridge outcomes.
- Send is **not** blocked when the only pinned document is excluded for BUSY or ROUTES_NOT_LOOPBACK (the plan's "otherwise null"): the card shows the warn row and the request goes out with project data only. If the owner wants the old "block when nothing can be read" for those codes, it is a one-line change in `sendBlockedReason`.

## Deferred Issues

- One extra preview read happens when a preview discovers a mismatch (the store flag change re-triggers the card effect; the second read confirms the same answer). Harmless; could be deduplicated.
- `degram_list_documents` / `degram_bridge_status` agent tools describe pins per bridge, but the `spec/degram` and DB/contract documents were not reviewed for the old single-pin wording (grep found no `documents.pin` references in `spec/degram`).
- The three whole-project ui test failures above.

## Known Stubs

None.

## Threat Flags

None. T-1301-21-01 (the payload is built from the same preview the card renders; PREVIEW_STALE on any pin change, tested for either bridge), T-1301-21-02 (per-bridge identity re-check, mismatch excludes and never re-pins, tested) and T-1301-21-03 (each bridge has its own deadline and the two reads run concurrently, tested with one hung adapter) are implemented. `degram.documents.unpin` is a new RPC on the existing authenticated loopback channel, listed in the lockdown allowlist, with no argument besides the bridge name.

## Self-Check: PASSED

Commit `02993674` found in `apps/degram` (branch `degram/phase-1301`); no tracked file in `apps/degram` is modified after the commit; `documents.py` (`_pins`, `unpin_all`), `methods_degram.py` (`degram.documents.unpin`), `documents-store.ts` (`Partial<Record<BridgeApp`...), `i18n.ts` ("Документы: ", "не включён") present.
