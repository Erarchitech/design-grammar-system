---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 01
status: bounded-increment-implemented-offline-verified
requirements-completed: []
requirements-partial: [DGCL-01, DGCL-02, DGCL-03, DGCL-05]
---

# 1301-01 — first functioning reused-web client increment

## Delivered

Open the existing DG web origin at **`/#degram`** after serving the normal rebuilt ui-v2 output. No new server or install command is required by this surface; none was launched here. `ui-v2/src/main.jsx` chooses the isolated root before dynamically importing normal App; crossing the hash boundary reloads the entry instead of preserving hidden normal layers. Normal DG remains available outside this route.

- `ui-v2/src/degram/DeGramWorkspace.jsx`: current cookie session → existing authorized `fetchProjects` → explicit project selection → existing `fetchGraph`. No remembered-project restore. Compact sign-in uses existing `auth.login` and shared Input/Button primitives, not a second auth implementation. Logout clears graph/inspector/projects and tenant browser data immediately; server failure is disclosed and retry offered without automatic session re-entry.
- `ui-v2/src/degram/ReadOnlyGraph.jsx`: existing `buildRings` + `GraphEngine`, real canvas and accessible node list, shared `PropertiesTable editable={false}`. Untagged nodes remain inspectable without inventing graph layers. No duplicate engine or authoritative graph store.
- `ui-v2/src/degram/inspection.js`: immutable surface projection excluding provider/model/credential metadata, recursively including JSON-encoded properties, before ring mapping and inspection. This is UI display filtering, not backend redaction or an arbitrary-prose classifier.
- Monotonic request generations discard late session/project/graph results after switch, refresh, logout or expiry; new selection immediately unmounts previous graph. Current-scope 403 removes all read context; shared 401 expiry also clears identity. Explicit loading, empty, denied and unavailable outcomes. Refresh/focus rechecks access and requires selection again.
- No mutation/ingestion/NL-query/history-writing UI or requests, LLM settings/provider/model/key controls, connectors, CAD/files or Model Viewer token requests. The normal GraphScreen/AiEngineScreen and other App layers are not mounted on this root. Owner/admin receive the same restricted controls; their backend powers are not changed.
- `ui-v2/src/graph/graphEngine.js`: backward-compatible `start({thinkingAssets=true}={})`; only this read surface opts out of unused thinking-GIF requests. No layout algorithm fork.
- `ui-v2/src/degram/degram.css` reuses DG tokens, typography and orbital identity, with responsive panels and visible keyboard focus; reduced-motion preference disables idle drift. `README.md` records launch, verification and boundaries.

## Actual verification

| Command | Executed result | Evidence |
|---|---|---|
| `node ui-v2/tests/run-degram.mjs verified` | **22/22 browser cases PASS**, 0 unmatched requests, 0 browser/runtime/CSP errors | `ui-v2/tests/evidence/degram-verified.json` (source hashes, dependency versions, actual request transcript) |
| `node --test ui-v2/tests/degram-boundary.test.mjs` | **2/2 PASS** | `ui-v2/tests/evidence/degram-boundary.log` |
| `node --test ui-v2/tests/api-security.test.mjs ui-v2/tests/auth-security.test.mjs` | **164/164 PASS**, 0 failures/skips | `ui-v2/tests/evidence/degram-existing-security.log` |
| `npm --prefix ui-v2 run build` | **exit 0**, Vite 5.4.21, 956 modules; separate DeGram entry chunk | `ui-v2/tests/evidence/degram-build.log` |
| `git diff --check -- ui-v2` | no whitespace errors; Git CRLF conversion notices | terminal execution |

Browser proof uses installed Chrome, actual React/ReactDOM 18.3.1 and esbuild 0.21.5, file URLs and a disposable isolated profile. Only finite exact synthetic API replies are allowed; CSP rejects connections and unexpected resources. The actual application entry is exercised; existing Vite documentation-glob macro is expanded by the test builder, not replaced with mocked components. The real graph engine draws a frame and canvas pixels are checked. No live server/API/DB/LLM/CAD proof is claimed.

Boundary tests verify the restricted root's dependency closure excludes normal screens, landing, model/LLM/connector clients; the tree-shaken bundle excludes mutation/workflow/history endpoint strings. They also check immutable nested metadata filtering. Browser cases cover happy-path inspection, remembered-selection rejection, stale switch, logout and retry, sign-in and duplicate-submit prevention, late login/project/session/graph responses, 401/403, revocation via refresh/focus, empty/unavailable, untagged nodes, provider metadata, owner/admin controls, real canvas drawing and forbidden networking.

## TDD execution record

Each new behavior slice was tested before production implementation, observed RED, then GREEN. Retained JSON pairs under `ui-v2/tests/evidence/degram-{red,green}-*.json` cover entry, switch, logout, login, revoke, denied, empty, metadata/thinking-asset, errors, login-race, logout-retry, focus, untagged and pending-login. Initial entry RED specifically showed normal App background requests to remembered graph/history and no DeGram root. Later supplemental tests verify already-implemented invariants; they are regression checks, not claimed additional RED cycles.

One harness-only failure occurred when waiting on RAF under Chrome virtual time: no final result DOM was emitted. Replaced that wait with an explicit call to the unchanged real engine draw method, then verified nonempty canvas pixels. No fabricated output or skipped browser gate. Production build still warns that the normal App chunk exceeds 500 kB; this is not the small DeGram entry and no warning was suppressed.

## Requirement disposition and limitations

**No DGCL ID is completed, no whole-phase/milestone completion claimed.** DGCL-01 has only existing web login/project-selection evidence (no Desktop installation). DGCL-02 has explicit project scope and hidden system metadata but no company/native-document/bridge integration. DGCL-03 has only this isolated graph-reading web slice, not all web screens or Model Viewer. DGCL-05 has offline client-side expiry/revocation/scope evidence, not live multi-user/backend/model enforcement acceptance. DGCL-04/06/07 remain outside this increment.

Remote revocation is discovered on next protected response, explicit refresh or window focus, not pushed into a continuously focused cached view. No timeout/cancel/desktop reconnect contract is claimed. Server membership enforcement remains authoritative; no roles/policy/endpoints were changed and UI hiding does not globally restrict owner/admin backend capabilities. Existing auth/session semantics remain unchanged.

Pre-existing dirty `ui-v2/src/lib/auth.js`, `ui-v2/src/screens/ProjectsScreen.jsx` and existing untracked tests were read but preserved. Only new DeGram/test files, `main.jsx`, the tiny graph-engine startup option, and these two owned 1301 plan/summary files were authored; build regenerated ignored `ui-v2/dist`. No installs, commits/staging/push/branch/stash, secrets/.env, server/deploy, live DB/CAD/LLM calls, installed Hermes/profile changes, or other planning writes. Workflow lessons are recorded here and in the repo README rather than an installed skill, respecting the explicit no-profile-change boundary.
