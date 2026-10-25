# DeGram Developer Mode / Demo Mode — priority planning brief

**Captured:** 2026-10-25
**Status:** scoped executable plans 1301-42..47 prepared; structural self-check only, no independent checker; implementation and acceptance pending
**Delivery owner:** Phase 1301; hosted integration counterpart: Phase 1309 / HOST-05
**Requirements:** DGMODE-01..04 (additive, outside the original 51 MVP IDs)
**Todo:** `.planning/todos/pending/2026-10-25-add-degram-developer-mode-and-demo-mode.md`

## Owner intent

DeGram must support two explicit operating modes in the near term:

| Mode | DG target | Purpose |
|---|---|---|
| Developer Mode | Local DG on localhost | Continue development and internal testing independently of the hosted stand |
| Demo Mode | DG stand on Contabo | Test the real hosted DG version from the Windows DeGram client |

This is not a request to replace localhost with Contabo, create another product/fork, or activate v14. Demo Mode uses the real stand, not fabricated results or a mock evaluator. Developer Mode grants no extra permissions and does not disable security checks.

## Scheduling and dependencies

- Next bounded **DeGram client** follow-up in Phase 1301; prior deferral of remaining 1301 work does not defer this newly requested slice.
- Coordinate the hosted-client leg with 1309 / HOST-05. Do not wait for the entire 1302–1307 chain or full six-store HOST-04 recovery work to implement and offline-test mode selection.
- Existing independent semantic, security, runtime-isolation and release gates remain applicable to the capability actually exercised. Mode support alone closes neither HOST-05 nor DGCL-01..07.
- Framework branch: `gsd/milestone13`; component work base: `apps/degram` on `degram/milestone13`. `D:\dgb\src` pulls only for builds; do not develop there.

## Required behavior and guardrails

1. Persist an explicit mode and associated DG target using the existing supported settings path. Show both the mode and effective target before sign-in and while working; do not require editing source or rebuilding to change modes.
2. Preserve the current localhost installation through an explicit, tested migration/default. Exact storage format, selector location and profile naming are implementation decisions to settle before executable plans, not invented owner decisions.
3. Namespace authentication/cookies, project/company selection, agent sessions/history/context, caches and retained document bindings by environment identity and origin, not just project ID. Identical project/user IDs on localhost and Contabo must not collide. Preserve the inactive environment's state without copying credentials/data into the active one.
4. Switching must safely stop or refuse while an operation is in flight, then release the old scope/backend/listeners and authenticate against the new target. Ignore late old-target responses. Do not reroute an already confirmed operation to another environment or silently fall back to localhost when Contabo is unavailable.
5. Apply the selected target consistently to embedded DG navigation, login/session exchange, relay/tools and model/graph APIs. Remote targets require the supported HTTPS trust boundary; never disable certificate checks or send old-origin credentials to a new origin.
6. CAD bridges remain local to the workstation and subject to existing permissions. Selecting Contabo must not publish a local bridge listener, expose Bolt, imply native write permission, or silently keep an old server-side project binding.
7. Target failure, missing login/grant and cancelled/failed switching must be explicit and recoverable. Mode selection does not grant demo users admin access or relax project/connector grants.
8. No automatic sync/migration of local project data, secrets, chat history or model contents to the stand. Credentials stay out of code, bundles, logs and planning artifacts.

## Scoped executable plans (prepared)

Additive slice only; existing plans 01–41 are not replanned. See `1301-DGMODE-RESEARCH.md`, `1301-DGMODE-VALIDATION.md` and `1301-DGMODE-PLAN-CHECK.md` for rationale, test strategy and actual planning-check status.

| Plan | Wave | Scope |
|---|---|---|
| 1301-42 | 29 | Target config, explicit override policy, compatible settings/partition ownership |
| 1301-43 | 30 | Environment profiles, migration and origin-scoped purge/cleanup |
| 1301-44 | 31 | Main/backend switch barrier, target-bound runtime and typed IPC |
| 1301-45 | 32 | UI amendment, selector and fenced renderer consumers |
| 1301-46 | 33 | Same-home real-path A→B→A, collision/race/negative tests and offline evidence |
| 1301-47 | 34 | Framework guide/integration and separately authorized publication/live acceptance |

Dependencies are 42 → 43 → 44 → 45 → 46 → 47. Plan 42 has no old-release dependency; wave numbering continues the existing phase without requiring old plan 41. Execute only this explicit plan set, not a blanket phase rerun. Implementation decisions are identified as such in supplemental research, not represented as new owner decisions. All requirement and independent phase/hosted gates remain pending.

## Original proposed work packages

These are planning work packages, **not executable PLAN files**. Run scoped planning before execution; inspect the named component areas through the local index and read the Desktop AGENTS/DESIGN rules first. Allocate the next available plan numbers (currently after 1301-41) only after checking existing plans.

| Package | Committing repository | Scope | Dependencies |
|---|---|---|---|
| A — mode configuration and isolation | component | Config/model, mode identity, compatible migration, environment-scoped persistence and focused tests | Workspace verify, current settings/session lifecycle reconnaissance |
| B — selector and safe target switch | component | Visible selector/indicator, Electron/renderer/agent propagation, in-flight safety, stale-response fencing, A→B→A tests | A; settle UI amendment before UI implementation |
| C — integration and owner acceptance | framework | Published component gitlink, framework compatibility/security docs if affected, reproducible guide, evidence matrix | A/B tested; child commit/push and build/install require their own authorization |

Cross-repository order: child changes + tests → explicitly authorized child commit → explicitly authorized fork push → framework gitlink/docs → `python tools/degram/workspace.py verify` on the exact pair. Never commit a gitlink whose object is not published. Framework GSD artifacts own acceptance; no second `.planning` in the child.

If target selection changes a route, principal, port or secret boundary, consult/update `spec/SECURITY-BOUNDARY.md` and its machine-checked inventories. Prefer existing settings/adapter seams; do not create a second auth or evaluator implementation. Do not alter unrelated GH mapping, hosted recovery modules or upstream stock-variant behavior.

## Acceptance matrix

| Check | Expected | Evidence |
|---|---|---|
| Existing install → Developer Mode | Local DG remains reachable; no profile loss or Hermes profile change | Migration test with temporary runtime homes; owner local check |
| Developer → Demo | Mode/target visible; Contabo login and grants apply; no localhost credential forwarding | Offline real-path integration + separately authorized live check |
| Demo → Developer | Original local state recovered without server context/data leakage | Real-path A→B→A test with distinct temporary homes/origins |
| Same company/project/user IDs in both targets | Independent credentials, histories, caches and bindings | Deliberate identity-collision negative fixture |
| Switch during an operation + delayed old response | Operation stopped/refused safely; no cross-target retry or stale UI update | Cancellation/lifecycle race tests |
| Contabo down, TLS failure, expired/revoked grant | Explicit failure; no fallback or permission bypass | Negative offline fixtures + authorized live revocation test |
| Restart in either mode | Selected mode/target restored with correct environment state | Persistence/restart integration tests |
| Native bridge in Demo Mode | Listener remains loopback-only; any mapping/check uses the selected authorized DG scope | Boundary test; owner-authorized CAD act if included |
| Unmodified stock Hermes variant | Existing identity/settings/profile behavior unchanged | Focused variant regressions |

Focused commands must be pinned to the actual suites found during planning, not guessed. Baseline integration commands: `python tools/degram/workspace.py verify` and `python -m unittest discover -s tools/degram/tests -v`; component planning must add actual Electron/UI/agent test and typecheck commands. Use temporary homes; never exercise the installed Hermes profile or the known user-PATH-writing test. Record failures/skips honestly. Unit mocks alone cannot prove target propagation or isolation.

## Authorization and non-goals

This capture changes framework planning only. It does not authorize deployment/server changes, Desktop launch/build/install, package installation, paid inference, data/CAD mutations, publishing internal planning to the public component fork, or component commits/pushes. Apply existing owner authorizations only to their exact scope and obtain fresh approval for separately gated runtime/publication steps. Do not mark requirements or phases complete before the required evidence exists.
