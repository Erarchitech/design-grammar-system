---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 45
subsystem: degram-target-renderer
status: complete
completed: 2026-10-26
requires: [1301-44]
provides:
  - additive target-selector UI contract and main-authoritative selected/effective disclosure
  - generation-bound renderer state, documents, history replies, mapping and preview publication
  - main-issued operation leases covering consent, armed Send, streaming and settled Stop
  - real-store A-to-B-to-A regression tests and composed main producer stamp coverage
affects: [1301-46, 1301-47]
requirements-completed: []
key-files:
  created:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DGMODE-UI-SPEC.md
    - apps/degram/apps/desktop/src/degram/dg-target-selector.tsx
    - apps/degram/apps/desktop/src/degram/dg-target-selector.test.tsx
    - apps/degram/apps/desktop/src/degram/environment-scope.test.tsx
---

# Phase 1301 Plan 45: Target visibility and renderer isolation

**All three implementation tasks are complete at the bounded offline level. The renderer mirrors main-owned target descriptors, fences transient state by environment/generation, and holds target-bound operation leases through the user request lifecycle. This is not product, visual or live acceptance.**

## Scope and execution

- Invocation: `/gsd-execute-phase 1301 --wave 4 --no-transition`.
- Computed DAG wave 4 selects incomplete plan 45; plans 11/12 already had summaries. Plan 45's historical declared wave is 32. Dependency 44 has a completed offline summary.
- Current checkout only; no workers, worktrees, commits, pushes, package installation, Desktop build/launch, installed Hermes-profile access, live DG/CAD/server actions or paid inference.
- Framework gitlink and component HEAD remain `b619e02e3725869b1ab5125951d3311e3656dc9a`. Existing plan-42–44 component edits and unrelated framework changes were preserved. Source remains uncommitted; no commit-log completion claim is made because this plan explicitly prohibits automatic commits.
- The primary STATE position/counters remain Phase 1303. DGMODE-01/02/03, DGCL, HOST-05 and Phase 1301 acceptance remain open. No phase transition, requirement completion or phase-level verification.

## Task results

| Task | Repository | Result |
| --- | --- | --- |
| 1. Bounded UI amendment | Framework | Created `1301-DGMODE-UI-SPEC.md`; historic ring/sidebar/mapping/permission decisions remain unchanged. Defined authority, normal-flow header, selected/effective/error states, keyboard focus, localization and native-bounds acceptance boundary. |
| 2. Selector and disclosure | Component | Existing Select/Button primitives render configured Developer/Demo modes and separate selected/effective origins, before sign-in and in the working shell. Main IPC receives only configured mode and expected environmentId/generation. Busy refusal, override lock, invalid/mismatched descriptors, failure and explicit retry have bounded states. Stock variant renders no selector. |
| 3. Store/dispatch fences | Component | Main state/events carry runtime stamps through actual composition. Initial reads, events and async replies cannot publish across A→B→A. Consent/armed Send/streaming use main leases; abandoned arming expires. Stop retains its source lease until both context cancellation and session interrupt settle. |

## Isolation contract and cache inventory

- **Main producer:** the environment coordinator passes its immutable generation through both main-wiring layers into `createDegramRuntime`; `getState`, state publications and runtime events include environmentId/generation. An actual composed-runtime A→B→A test protects the forwarding seam, not just a direct-runtime fixture.
- **Initial state and events:** stamped runtime state arriving before its environment publication is buffered. Lower-generation, wrong-environment and late initial responses are ignored. Explicit refresh also checks source stamp/revision. Readiness requires selected/effective mode, origin, environmentId and partition agreement.
- **Transient identity:** environmentId/generation + authenticated user/company/project + scope epoch. Equal numeric epoch/profile/document/session IDs are not sufficient to reuse active caches.
- **Routes/chat:** switch invalidates route tickets and wipes active session lists/open-session state before new target paint. Superseded route completion cannot pin/open a fresh chat. Existing main backend admission and the renderer route-mismatch guard remain authoritative dispatch defenses; inactive backend/profile data is not deleted.
- **Durable history:** the sidebar scope tag includes environmentId/user/company/project, deliberately not transient generation. Returning to A can recover A's namespace only after main's authentication/membership-ready state; no history is copied to B or automatically uploaded.
- **Documents:** switching clears active lists/pins; generation/scope-bound list/pin completions cannot restore departed state. An obsolete pin's cleanup does not start a new-target refresh.
- **Preview:** main lease precedes preview dispatch; completion checks source scope and preview ID before bridge/document side effects. Stop or switch invalidates the preview.
- **Consent and Send:** main lease precedes consent or arming. Environment reset resolves outstanding consent false; late confirmation cannot send. Arming is source-key/text bound and expires after 30 seconds. Late Send response/error cannot modify a new environment's lifecycle. No automatic retry/resend to another target.
- **Streaming/Stop:** source-keyed event subscription; completion/failure releases the streaming lease. Stop paints immediately but awaits both cancellation and the existing stock interrupt path before releasing its captured source lease. It cannot release a newer operation's lease.
- **Mapping/native gateway:** captured transport and environment stamp plus a main dispatch lease; stale replies reject without retry. Mapping hook also fences read/adopt/follow by scope/document/local generation and hides prior state synchronously. Algorithms/native write permissions are unchanged.
- **Native surfaces:** gate and DG/sign-in hosts hide target-bound native content while environment readiness fails. Header is outside the measured native host; `use-dg-bounds` remains the actual rectangle authority. Offline checks do not prove physical/native placement.

## Files by repository

### Framework

- Created `1301-DGMODE-UI-SPEC.md` before component implementation and this summary.
- Updated only the bounded-client paragraph in `.planning/STATE.md` and plan-45 row in `.planning/ROADMAP.md` for bookkeeping. No primary Phase 1303 position/counter changes.
- Local AST refresh updates generated `graphify-out` and ignored `.degram/index` outputs; these are not product source or a public-fork deliverable.

### Component (`apps/degram`, no commit)

Created:
- `apps/desktop/src/degram/dg-target-selector.tsx`
- `apps/desktop/src/degram/dg-target-selector.test.tsx`
- `apps/desktop/src/degram/environment-scope.test.tsx`

Renderer modules amended:
- `src/degram/use-degram-state.ts`, `scope-route.ts`, `scope-route.test.ts`, `documents-store.ts`, `session-list.ts`
- `src/degram/request-lifecycle.ts`, `composer-seam.ts`, `host-actions.ts`, `use-degram-gateway.ts`, `use-mapping-session.ts`
- `src/degram/degram-gate.tsx`, `dg-page.tsx`, `sign-in-state.tsx`, `i18n.ts`, `test-harness.tsx`, `chat.test.tsx`
- `src/app/contrib/controller.tsx`, `src/app/session/hooks/use-prompt-actions/index.ts`

Producer seams amended on top of pre-existing plan-44 work:
- `electron/degram/ipc.ts`, `ipc.test.ts`, `main-wiring.ts`, `main-wiring.test.ts`, `scope.ts`

These paths are under `apps/desktop/` in the component. Whole-file diffs in shared main seams also contain pre-existing plan-42–44 changes; this summary does not claim those changes as plan-45 work. Framework notes/vault material were not copied into the public fork.

## Verification

| Check | Result |
| --- | --- |
| `python tools/degram/workspace.py verify` | Passed; context installed, HEAD=gitlink, `productAccepted: false`. |
| `python -m unittest discover -s tools/degram/tests -v` | 27/27 passed. Existing relay-fixture unclosed-socket ResourceWarnings; negative missing-upstream test prints its expected remote error. |
| Selector + real-store environment-scope + scope-route tests | 43/43 passed (9 selector, 11 environment-scope, 23 route). Covers keyboard/busy/focus handoff, equal-ID A→B→A races, late initial/history/documents/preview/mapping, consent, armed expiry and settled Stop. |
| Final focused renderer after formatting (selector + environment-scope + route + chat) | 143/143 passed, four files. |
| Main composition + IPC focused tests | 64/64 passed, including actual producer stamps after generation forwarding fix. |
| Full `npm --prefix apps/degram/apps/desktop run test:ui -- src/degram` | **347 passed / 1 failed (348 total)**. Only failure: `ru-catalog-completeness.test.ts > DeGram RU catalog (D-54) > explicitly translates settings without EN fallback`; `settings.plugins.installModal.repoPlaceholder` is the same `https://github.com/owner/repo` URL in EN/RU. Same named failure is recorded in plan-44 summary. Not fixed or hidden here. |
| Full `npm --prefix apps/degram/apps/desktop run test:desktop:platforms -- electron/degram` | 304/304 passed, 16 files. |
| `npm --prefix apps/degram/apps/desktop run typecheck` | Passed (renderer, Electron, E2E and builder config no-emit checks). |
| Focused ESLint on isolation/selector modules | No errors; final padding warning in composer seam corrected with existing lint tool. No blanket lint-clean claim for inherited/unrelated files. |
| `git diff --check` (component) | Passed; Git reports existing CRLF→LF normalization warnings, not whitespace errors. |

## Deviations and fixes found during execution

1. Working header belongs immediately before `LayoutTreeRoot` in the actual controller flex layout, not in sibling `DegramShellHost`; the supplement was corrected to reflect source. Selector stays above measured native content without a z-index workaround.
2. Required adjacent production seams beyond the plan's listed files: main runtime producer stamps, controller header placement, sign-in/DG readiness and stock composer Stop settlement. These are necessary for the planned behavior, not unrelated refactors.
3. A missing generation-forwarding layer in main composition was found by tracing production, fixed, and protected by composed-runtime tests. A direct IPC fixture alone would not catch it.
4. Gate and working header are separate surfaces. Explicit switch focus is handed to the active mode control across their handoff; a jsdom test exercises replacement, while actual native/visual focus remains plan 47.
5. Legacy isolated-runtime tests retain their no-environment compatibility path. The production coordinator stamps all runtime states, so those states buffer until authoritative environment publication rather than opening the working UI on missing coordinator data. Invalid environment objects fail closed; they do not take the legacy path.
6. An initial `index_code.py --help` invocation actually refreshed indexes because the script has no argument parser. It completed offline with `paidInference: false`; no installs were performed. The final source refresh also completed (exit 0, `paidInference: false`); SQL extraction remains incomplete without optional `tree_sitter_sql`.

## Acceptance boundary / continuation

- Plan 46 (computed wave 5) retains composed cross-environment offline acceptance, including broader route/backend/cache integration and error paths. No independent acceptance is inferred from this implementation's tests.
- Plan 47 (computed wave 6) retains explicit publication/build/install permissions and localhost/Contabo UAT, native rectangle/focus, narrow-window visual and TLS/login/grant behavior. No jsdom/live equivalence claim.
- Existing RU catalog regression remains open. No phase verification/transition because plans 16, 46 and 47 remain incomplete after this bounded wave.
- Next bounded command: `/gsd-execute-phase 1301 --wave 5 --no-transition`.

## Self-Check: PASSED (bounded offline implementation)

Required artifacts exist and actual focused/full check results are recorded above. The full renderer suite is not green because of the named pre-existing RU failure. No requirement/product acceptance or commit is claimed.
