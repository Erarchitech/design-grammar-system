# DeGram read-only web increment

Open the existing DG web origin at **`/#degram`** after the normal ui-v2 build is served. No new server, port, desktop install or separate datastore is introduced. The current session is resolved via `/auth/me`; otherwise the compact form uses the existing `auth.login` cookie/CSRF flow. Only projects returned by `fetchProjects` are offered. Every initial load, sign-in and access refresh requires an explicit project selection.

`main.jsx` chooses this root before dynamically importing the normal App. Switching between this hash and normal DG reloads the entry, rather than keeping hidden App layers mounted. `ReadOnlyGraph` reuses `buildRings`, `GraphEngine` and `PropertiesTable` (`editable=false`). Nodes without a graph layer remain inspectable in the node list without inventing a sixth graph. `GraphEngine.start({thinkingAssets:false})` skips an unused animation asset; normal callers retain the previous default.

## Host mode (DeGram)

Opening the normal DG entry with `?host=degram` is a UI-only filter for the DeGram host. It keeps only **Graph Viewer**, **Model Viewer**, and **Projects** on the landing ring. The host may navigate to **Connectors**, which renders only the caller's project grants and access-request control; the ordinary connector registry is neither loaded nor shown there. DG API Docs, Reasoner, and AI Engine are refused. The flag grants no API, token, storage, or server capability; normal browser access without the flag is unchanged. `?lang=ru` selects Russian host-only labels; English is the default.

The fragment channel is fixed vocabulary and conveys navigation or display state only:

- Page → host: choosing a project announces `#degram-select=<url-encoded name>` (non-empty, at most 64 characters); the host validates it against memberships. Pressing the ready-state pill announces `#degram-new-session` to request an empty chat in the current scope. Neither message contains a token, nor grants access. The page clears the announcement with `history.replaceState` while preserving pathname and host query parameters.
- Host → page: `#degram-state=connecting|ready|idle` changes only the ring centre, and `#degram-go=landing|graph|model|connectors` navigates only to an allowed region. Exact matches only; other fragments are ignored. The page clears an accepted signal after applying it, preserving pathname and query. `main.jsx` reloads only for the separate `#degram` root slice, never for these signals.

From the Projects click until the host signals `ready`, the centre shows the theme-matched thinking sphere and a connecting label. `ready` restores the hero/project line and shows the new-session pill beneath Sign out. The host controls readiness after its own scope/grant check; the page does not infer authorization from a fragment. The Projects region continues to use only the existing `GET /projects` result.


- No graph mutations, natural-language query/ingestion, history writes, model viewer token requests, ordinary connector credentials, CAD/files, LLM settings, provider/model/key inputs or navigation to refused screens.
- Display projection strips provider/model/credential metadata recursively, including JSON-encoded properties, before rendering. This is **not server-side redaction** and not a promise about arbitrary prose containing a provider name.
- A monotonic request generation rejects stale session/project/graph results after context changes, expiry, logout or access refresh. Switching/refreshing clears the canvas and inspector immediately.
- 401 clears identity and all read context; a current-scope 403 clears projects/graph and shows denial. Shared transport conservatively treats any 401, including a stale request's response, as session expiry.
- Access is rechecked on explicit **Refresh access** and window focus; server enforcement still applies on every request. No push revocation subscription exists, so a continuously focused cached view does not discover a remote revocation until the next read/refresh/focus. This is not live revocation acceptance.
- Logout clears local data before awaiting the server. If sign-out fails, no automatic session re-entry occurs; an explicit retry is shown. No credentials, graph, or remembered project are persisted by this workspace.
- Owner/admin capabilities remain unchanged on the backend and in normal DG. This is a bounded UI surface, **not** a global capability restriction.

## Offline verification

From the repository root, using already installed dependencies/browser:

```text
node ui-v2/tests/run-degram.mjs verified
node --test ui-v2/tests/degram-boundary.test.mjs
node --test ui-v2/tests/api-security.test.mjs ui-v2/tests/auth-security.test.mjs
npm --prefix ui-v2 run build
```

The browser runner follows the existing `tests/run-panel.mjs` file-URL strategy. It bundles actual `main.jsx`/ReactDOM and real renderer, permits only finite explicit synthetic API responses, rejects unmatched requests and CSP resource violations, uses an isolated disposable browser profile, and launches no server. A real graph frame is drawn and pixels checked; virtual-time RAF scheduling is not used as a correctness oracle. Evidence under `tests/evidence/degram-*.json` includes observed RED/GREEN runs; `degram-verified.json` is the final complete run with source hashes. These are UI integration tests, not live API/DB/CAD proof.

This increment is a reusable web surface for a future minimal Hermes Desktop fork. Desktop packaging, model/native-document/bridge integration, cancellations/timeouts, live multi-user tenancy verification and full DGCL-01..07 acceptance remain outside this increment.
