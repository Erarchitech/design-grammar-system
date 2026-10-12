# Phase 1308: DG Web UI - Pattern Map

**Mapped:** 2026-10-12
**Files analyzed:** 36 (new or modified)
**Analogs found:** 33 / 36 (3 have no codebase analog)

Line numbers are from files as read on 2026-10-12. `data-service/app.py` is large and shifts often, so re-grep before citing a line in a plan.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `data-service/connector_session.py` (new) | service/store | CRUD + token auth | `data-service/delegation.py` | exact |
| `data-service/auth_routes.py` (add `POST/DELETE /auth/connector-session`) | route | request-response | same file, `exchange_degram_session` + `revoke_delegated_token` | exact |
| `data-service/auth.py` (`resolve_connector_principal`, `Principal.connector_id`) | middleware | request-response | same file, `authenticate_delegated_token` use at ~L1107 | exact |
| `data-service/connector_access.py` (`is_exempt`) | service | CRUD | same file L237, L277 (the four `"editor"` checks) | exact |
| `data-service/connectors.py` (status from sessions, retire credential create) | service | CRUD | `degram_pairing.pairing_retired()` precedent for 410 | role-match |
| `data-service/app.py`: `PUT /projects/{project}/members/{username}` | route | CRUD | `remove_project_member` L4959, invite branch L5008-5022 | exact |
| `data-service/app.py`: `GET /projects/{project}/summary` | route | request-response (Cypher read) | `GET /rules/{project}` (`RULES_LIST_QUERY`) | role-match |
| `data-service/app.py`: 410 on `POST /connectors/{id}/credentials`, heartbeat and capture on new resolver | route | request-response | `PAIRING_RETIRED` | role-match |
| `data-service/route_policy.py` (new rows) | config | n/a | same file L123-138, L176-203 | exact |
| `data-service/tests/auth_fixtures.py::connector_token_for` | test util | n/a | itself (L79-83) | exact |
| `data-service/tests/test_connector_session.py` (new) | test | CRUD | `tests/test_delegated_token.py`, `tests/test_degram_grants.py::_exchange` | role-match |
| `data-service/tests/test_member_roles.py` (new) | test | CRUD | `tests/test_project_routes.py` (`_headers`) | role-match |
| `data-service/tests/test_project_summary.py` (new) | test | request-response | `tests/test_graph_routes.py` | role-match |
| `data-service/tests/test_route_inventory.py`, `test_security_boundary_spec.py` (edit) | test | n/a | themselves | exact |
| `data-service/<one-off ops script>` (new, retire `dgc_` and remove UAT user) | utility | batch | `data-service/rotate_llm_master_secret.py` | exact |
| `spec/SECURITY-BOUNDARY.md` fenced blocks, `spec/API.md`, `GRASSHOPPER.md`, `DEPLOYMENT.md` | config/docs | n/a | existing fenced blocks | exact |
| `ui-v2/src/i18n/{index.js,ru.js,LanguageProvider.jsx,LanguageBadge.jsx}` (new) | provider/utility | transform | `ui-v2/src/lib/hostMode.js` (`hostLang`), `lib/auth.js` (`KEPT_KEYS`) | partial |
| `ui-v2/tests/i18n.test.mjs` (new) | test | transform | `ui-v2/tests/host-degram.test.mjs` | role-match |
| `ui-v2/src/lib/{projectSettingsApi,memberApi,summaryApi}.js` (new) | service | request-response | `ui-v2/src/lib/connectorsApi.js` | exact |
| `ui-v2/src/lib/runGroups.js` (new, extracted) | utility | transform | `ui-v2/src/screens/ModelScreen.jsx:449-459` | exact (extract) |
| `ui-v2/tests/{member-roles-api,project-settings-api,landing-summary}.test.mjs` (new) | test | request-response | `ui-v2/tests/connector-access-api.test.mjs` | exact |
| `ui-v2/src/lib/auth.js` (`KEPT_KEYS`) | utility | n/a | itself L29 | exact |
| `ui-v2/src/lib/hostMode.js` + `host-degram.test.mjs` | utility/test | n/a | itself L35-36, test L53-54 | exact |
| `ui-v2/src/lib/connectorsApi.js` (drop `createCredential`/`revokeCredential`) | service | request-response | itself L19-40 | exact |
| `ui-v2/src/landing/LandingLayer.jsx` (+ `landing.css`) summaries + badge slot | component | request-response | itself L317-340 | exact |
| `ui-v2/src/screens/ProjectsScreen.jsx` (role Select, Project settings panel) | component | CRUD | itself L228-262 | exact |
| `ui-v2/src/screens/ConnectorsScreen.jsx`, `HostedConnectorsTable.jsx` | component | CRUD | themselves | exact |
| `DG/src/DG.Core/Data/ConnectorSessionClient.cs` + `IConnectorSessionClient.cs` (new) | service | request-response | `ConnectorHeartbeatClient.cs` | exact |
| `DG/tests/DG.Tests/ConnectorSessionClientTests.cs` (new) | test | request-response | `ConnectorHeartbeatClientTests.cs` | exact |
| `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` | component | request-response | itself L36-70 | exact |
| `DG/src/DG.Core/Data/DataServiceRequestAuth.cs`, `Validator/ComputgraphPublish` components | utility/component | request-response | themselves | exact |
| `apps/degram/apps/desktop/{src/degram/sidebar-nav.ts, electron/degram/dg-view.ts, ipc.ts, src/degram/i18n.ts, sidebar.test.tsx}` (component repo) | component/config | event-driven | themselves | exact |
| `docs/RELEASE-NOTES-*.md` entry | docs | n/a | existing release notes | exact |

## Pattern Assignments

### `data-service/connector_session.py` (service/store, token auth)

**Analog:** `data-service/delegation.py` (324 lines). Copy the module shape; change the record fields, TTL, prefix and re-checks.

**Header constants** (L49-81): hash-only store via `auth._load/_save`, file next to the memberships file.
```python
import hashlib
import secrets
import auth
import company

TOKENS_FILE_NAME = "auth-delegated-tokens.json"      # -> "auth-connector-sessions.json"
DELEGATED_TOKEN_PREFIX = "dgd_"                       # -> "dgk_"
DELEGATED_TOKEN_TTL_SECONDS = 900                     # -> env DG_CONNECTOR_SESSION_TTL_SECONDS, default 28800
_RETENTION_SECONDS = 3600
_KEY = "tokens"

def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / TOKENS_FILE_NAME

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

**Issue** (L142-187): token = prefix + `secrets.token_urlsafe(32)`, store only the hash, prune expired rows past retention, all under `auth._STORE_LOCK`, return `(raw_token, public_record)` with hash stripped.
```python
token = DELEGATED_TOKEN_PREFIX + secrets.token_urlsafe(32)
record = {"token_hash": _hash(token), "username": normalized, "project": project,
          "company": company.company_for_project(project),
          "issued_at": current, "expires_at": current + TTL, "revoked": False}
with auth._STORE_LOCK:
    rows = auth._load(_file(), _KEY)
    kept = [r for r in rows if int(r.get("expires_at", 0)) + _RETENTION_SECONDS > current]
    kept.append(record)
    auth._save(_file(), _KEY, kept)
```
Add `connector_id`, `last_seen` to the record.

**Authenticate** (L199-254): hash the Bearer, find row, raise named error for unknown/revoked/expired, then live re-check inside the lock. For `dgk_` replace the session-parent check with `connector_access.is_authorized(...)` (owner/admin exempt, otherwise active per-connector row) and use `auth.effective_role`, not the stored-membership-only check that delegation uses (delegation deliberately gives no admin elevation; the connector session does, per D-04). Keep the company check and `_mark_revoked` pattern (L193-196, L242-244). Return `auth.Principal(kind="connector", username=..., bound_project=..., credential_id=digest[:16], connector_id=...)`.

**Revoke helpers** (L260-323): copy `_revoke_where` plus `revoke_for_user`, `revoke_for_user_project`, `revoke_for_project`, `revoke_token`; add `revoke_for_connector_grant(username, project, connector_id)`.

**Errors** (L86-128): named `auth.auth_error(error, hint, code, status)` factories; write `CONNECTOR_AUTH_FAILED`, `CONNECTOR_SESSION_EXPIRED`, `CONNECTOR_SESSION_ENDED`.

**Status derivation for `connectors.py`:** `active` = at least one live row; `stale` = rows existed, none live; `never_connected` = none (D-32). Keep the rows readable past expiry (retention window) so `stale` can be computed.

---

### `data-service/auth_routes.py` - `POST/DELETE /auth/connector-session` (route, request-response)

**Analog:** same file, `exchange_degram_session` L322-352, `_delegated_answer` L308-319, `revoke_delegated_token` L364-369.

**Mint** (L322-352): handler reads `request.state.principal` (cookie user, CSRF already enforced by `require_principal`), checks membership, checks the grant, issues, answers with `Cache-Control: no-store`.
```python
@router.post("/auth/degram/session-exchange", status_code=201)
def exchange_degram_session(payload: DelegatedTokenRequest, request: Request, response: Response):
    principal = request.state.principal
    project = payload.project
    username = principal.username or ""
    if not username or not principal.session_hash or auth.get_role(username, project) is None:
        raise auth.auth_error("Not authorized for the requested project.",
            "Request project access from a project owner.", "PROJECT_FORBIDDEN", 403)
    grant = degram_grants.active_grant(username, project)
    if grant is None:
        raise degram_grants.grant_required()
    token, record = delegation.issue_delegated_token(session_hash=..., grant_id=grant["grant_id"],
                                                     username=username, project=project)
    degram_grants.record_use(grant["grant_id"])
    return {**_delegated_answer(response, token, record), "username": record["username"]}
```
Differences for connector-session: use `auth.effective_role(principal, project)` (admin counts as owner; the DeGram path uses stored role only), call `connector_access.check_connector(connector_id)` first (404 `CONNECTOR_NOT_FOUND`), then `connector_access.is_authorized(...)` else `connector_access.access_required()` (403 `CONNECTOR_ACCESS_REQUIRED`). Add the Neo4j bundle only when `auth.deployment_profile() != "multi-user"`. Request model mirrors `DelegatedTokenRequest` (`auth_routes.py:110`) plus `connector_id`.

**Answer shape** (L308-319): `{token, project, company, expiresAt (strftime %Y-%m-%dT%H:%M:%SZ), expiresInSeconds}`; add `connectorId`, `username`, optional `neo4j`.

**Self-revoke** (L364-369): parse `Authorization: Bearer`, call `revoke_token`, return `None` with `status_code=204`.

**Cascades**: next to every existing `delegation.revoke_*` call add the connector-session twin:
- password change, `auth_routes.py:416`: `delegation.revoke_for_user(user["username"])`
- `remove_project_member`, `app.py:4979-4981`: `degram_grants.revoke_for_user_project`, `connector_access.revoke_for_user_project`, `delegation.revoke_for_user_project`
- `set_project_company` (grep `delegation.revoke_for_project`)
- grant revoke in `connector_access` and the new role-change route (when demoted below exempt and no grant exists the live re-check already denies, no explicit revoke is required).

---

### `data-service/auth.py` - connector resolver (middleware, request-response)

**Analog:** `resolve_connector_principal` L451-467 plus the call site L1107-1114.
```python
def resolve_connector_principal(token: str) -> Principal | None:
    if not token or not token.startswith(connectors.TOKEN_PREFIX):
        return None
    record = connectors.authenticate_token(token)
    if record is None:
        return None
    bound_project = record.get("project") or "default-project"
    return Principal(kind="connector", bound_project=bound_project, credential_id=record.get("credential_id"))
```
Rewrite to call `connector_session.authenticate(token)` (prefix `dgk_`, `dgc_` no longer matches). Note: delegation raises named errors from `authenticate_*`; the existing resolver returns `None` and the caller at L1109 raises `CONNECTOR_AUTH_FAILED`. Pick one convention: either keep `None` for unknown tokens or let the session module raise named errors as `authenticate_delegated_token` does. Update the L1109-1114 hint text, which currently tells the caller to create a credential. `Principal` (dataclass in `auth.py`) gains `connector_id: str | None = None`.

---

### `data-service/connector_access.py` - exemption (service, CRUD)

**Analog:** the four editor checks. Seen at L237 (`access_state`) and L277 (`create_request`); the other two are in `app.py` (`request_connector_access` handler and the credentials handler; grep `role_satisfies(.*"editor")`).
```python
if auth.role_satisfies(role, "editor"):
    return STATE_AVAILABLE
...
if auth.role_satisfies(auth.get_role(normalized, project), "editor") or can_create(normalized, project, connector_id):
    raise access_exists()
```
Replace each with one helper:
```python
def is_exempt(role: str | None) -> bool:
    return auth.role_satisfies(role, "owner")
```
Also add `is_authorized(username, project, connector_id, role)` = `is_exempt(role) or can_create(...)` (reuse the existing active-grant lookup, `can_create` is the grant predicate used at L277). Existing tests `test_connector_access.py` and `test_cross_project_matrix.py` assert the old editor behavior and must be rewritten.

---

### `data-service/app.py` - `PUT /projects/{project}/members/{username}` (route, CRUD)

**Analog:** `remove_project_member` (`app.py:4959-4982`) for lock + 404 + `LAST_OWNER`; invite branch (`app.py:5008-5022`) for the demotion guard to extract into a shared helper.
```python
with auth._STORE_LOCK:
    role = auth.get_role(username, project)
    if role is None:
        raise _structured_error_response("That user is not a member of this project.",
            "List the project members and try again.", "MEMBER_NOT_FOUND", 404)
    if role == "owner" and auth.count_owners(project) <= 1:
        raise _structured_error_response("A project must keep at least one owner.",
            "Promote another member to owner before removing this one.", "LAST_OWNER", 409)
```
Role validation: `payload.role not in auth.ROLES` -> 422 `ROLE_INVALID` (same check opens `create_project_invite`, `app.py:4991`). Request model: copy `InviteRequest` (`app.py:4635`) shape, only `role`. Policy row: `_p(_MEM, source="path", role="owner")`, same as the `DELETE` row at `route_policy.py:138`. `auth.set_membership(username, project, role)` as at L5019.

---

### `data-service/app.py` - `GET /projects/{project}/summary` (route, request-response)

**Analog:** `GET /rules/{project}` (`route_policy.py:147`, handler uses `RULES_LIST_QUERY`). Copy its Cypher-session helper and project-path validation (`_check_project_name`). Cypher is in RESEARCH "Landing summary query" (filter `n.project = $project`). Policy row: `_p(_MEM, source="path", role="viewer")`. Grants count comes from `connector_access` active rows plus `degram_grants` active rows for the project; counts only.

---

### `data-service/route_policy.py` (config)

**Analog:** same file. Row grammar `("METHOD", "/path"): _p(principals..., source=..., role=...)` (`_p` at L88-95). Rows to add or change:
```python
("POST",   "/auth/connector-session"):                       _p(_MEM, source="body", role="viewer"),   # mirror L131
("DELETE", "/auth/connector-session"):                       _p(_CON),                                 # mirror DELETE /auth/delegated-token L124 (_DEL)
("PUT",    "/projects/{project}/members/{username}"):        _p(_MEM, source="path", role="owner"),    # mirror L138
("GET",    "/projects/{project}/summary"):                   _p(_MEM, source="path", role="viewer"),
("POST",   "/connectors/heartbeat"):                         _p(_CON),                                 # was _p(_SELF) at L203
```
Update the L186-190 comment block (D-46 text) for D-49. The `POST /connectors/{connector_id}/credentials` row (L194) stays registered but its handler answers 410.

---

### `data-service/tests/test_route_inventory.py` / `test_security_boundary_spec.py` (test)

**Analog:** themselves. Edits required in the same commit as the routes:
- `test_security_boundary_spec.py:46-51`: remove the heartbeat entry from `PUBLIC_CREDENTIALS`
```python
PUBLIC_CREDENTIALS = {
    ("POST", "/auth/accept-invite"): "invite-code",
    ("POST", "/connectors/heartbeat"): "connector-token",   # remove
}
HEARTBEAT = ("POST", "/connectors/heartbeat")                # remove or repurpose
```
- `test_route_inventory.py:207` `test_policy_table_size` hardcodes a row count; bump it by the number of rows added (4 added plus nothing removed).
- Spec blocks (`<!-- security-boundary:public-routes:start -->` etc.; names in `BLOCKS` L38) in `spec/SECURITY-BOUNDARY.md` get the same row changes. Run both tests after every route change.

---

### `data-service/tests/auth_fixtures.py::connector_token_for` (test util, single seam)

**Analog:** itself L79-83.
```python
def connector_token_for(project: str) -> str:
    _record, token = connectors.create_credential("grasshopper", project=project)
    return token
```
Re-implement over `connector_session.issue(username=..., project=..., connector_id="grasshopper")`. It needs a username: either add a parameter with a default test user (created with `make_user`, owner membership on `project` via `make_user(..., memberships={project: "owner"})` L33-55) or create a throwaway owner inside. Keep the signature backwards compatible, because roughly a dozen test files call it. Returns the raw `dgk_` token.

---

### `data-service/<ops script>` (utility, batch)

**Analog:** `data-service/rotate_llm_master_secret.py`. Copy:
- module docstring with invocation (`docker exec` with `MSYS_NO_PATHCONV=1` per project memory), status words and exit codes table (L1-60)
- `STATUS_*` constants, a `run(..., dry_run: bool = False) -> str` function that writes only on the non-dry-run path, and `build_arg_parser()` with `--dry-run` (L56, L104-121)
- Difference: default must be dry-run; add `--apply`. Wrap read-modify-write in `with auth._STORE_LOCK:` and use `auth._load/_save` (rotate script has no lock and warns about races; this one must hold it). Print counts only. Steps: back up `data-service/data/*.json` (owner checkpoint), mark `connector-credentials.json` records `revoked` with `retired: "D-49"`, remove user `uat-pw-bd30ce@dg.local`, its memberships, sessions, grants, requests, pairing row.

---

### `ui-v2/src/lib/{projectSettingsApi,memberApi,summaryApi}.js` (service, request-response)

**Analog:** `ui-v2/src/lib/connectorsApi.js`.
```js
import { apiFetch, dataServiceBase } from "./apiClient.js";

function projectGrantsUrl(project) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}/degram-grants`;
}
export function issueGrant(project, { username, label, purpose }) {
  return apiFetch(projectGrantsUrl(project), { method: "POST", body: { username, label, purpose } });
}
export async function revokeCredential(connectorId, credentialId) {
  await apiFetch(`${dataServiceBase()}/connectors/${encodeURIComponent(connectorId)}/credentials/${encodeURIComponent(credentialId)}`, { method: "DELETE" });
}
```
Rules to copy: every call goes through `apiFetch` (cookie and CSRF), path segments through `encodeURIComponent`, body is a plain object (not pre-stringified), 204 answers via `await apiFetch(...)` without a return. Use `PUT` with `{ method: "PUT", body: { role } }` for `memberApi.changeMemberRole(project, username, role)`; for `projectSettingsApi.setDegramPolicy` send only the changed flag.

### `ui-v2/tests/{member-roles-api,project-settings-api,landing-summary}.test.mjs` (test)

**Analog:** `ui-v2/tests/connector-access-api.test.mjs` L1-50. Copy the harness verbatim: save and restore `fetch`/`window` descriptors, `globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} }`, a recording `fetch`, then a table-driven loop asserting url, method, `credentials === 'include'`, and `headers[CSRF_HEADER] === '1'` for non-GET. Use `project = 'A/B ?#'` to prove encoding.

---

### `ui-v2/src/i18n/*` (provider/utility, transform)

**Analog (partial; no i18n exists):** `ui-v2/src/lib/hostMode.js` for host language, `ui-v2/src/lib/auth.js:28-43` for storage keys.
```js
export function hostLang() {
  return DEGRAM_HOST && new URLSearchParams(globalThis.location?.search || "").get("lang") === "ru" ? "ru" : "en";
}
```
```js
const TENANT_KEY_PREFIX = "dgv2_";
const KEPT_KEYS = new Set(["dgv2_theme"]);            // add "dgv2_lang"; also export KEPT_KEYS so i18n.test.mjs can assert it (currently module-private)
```
`resolveLang` order (D-07): host `?lang=` (badge hidden) then `localStorage.dgv2_lang` in {en, ru} then `en`. Core `translate`/`plural` code is in RESEARCH Pattern 3 (uses `Object.hasOwn`, `Intl.PluralRules`); copy it. Always wrap `localStorage` access in try/catch as `clearTenantBrowserData` does.

### `ui-v2/tests/i18n.test.mjs`

**Analog:** `ui-v2/tests/host-degram.test.mjs` (pure-Node `node:test`, imports `src/lib` ESM directly). Because `hostMode.js` reads `globalThis.location` at import time, the host-language cases need the same import-with-stub technique that file uses (see its top of file). `ui-v2/package.json` has no `test` script yet; add `"test": "node --test tests/*.test.mjs"`.

---

### `ui-v2/src/lib/runGroups.js` (utility, transform)

**Analog:** `ui-v2/src/screens/ModelScreen.jsx:449-459` (extract verbatim, make pure):
```js
const buckets = new Map();
for (const r of runs) {
  const key = r.state?.stateId || NO_STATE;
  if (!buckets.has(key)) buckets.set(key, { key, state: r.state, runs: [] });
  buckets.get(key).runs.push(r);
}
const arr = [...buckets.values()];
arr.sort((a, b) => (a.key === NO_STATE) - (b.key === NO_STATE) || a.key.localeCompare(b.key));
return arr;
```
Export `groupRunsByState(runs)` and `NO_STATE` (find its definition in `ModelScreen.jsx`); `ModelScreen` keeps `React.useMemo(() => groupRunsByState(runs), [runs])`.

---

### `ui-v2/src/lib/hostMode.js` + `host-degram.test.mjs` (WEBUI-06 framework half)

**Analog:** itself. `HOST_REGIONS` already contains `projects` (L5), only the `#degram-go` regex rejects it:
```js
if (/^#degram-go=(landing|graph|model|connectors)$/.test(hash)) return { go: hash.slice(11) };   // L36 -> add |projects
```
Test, `host-degram.test.mjs:53-54`: the positive list needs `"projects"`, and the negative list currently contains `"#degram-go=projects"` and must lose it (otherwise the test fails after the change).
```js
for (const go of ["landing", "graph", "model", "connectors"]) assert.deepEqual(hosted.parseHostSignal(`#degram-go=${go}`), { go });
for (const hash of [..., "#degram-go=projects", ...]) {
```

---

### `ui-v2/src/landing/LandingLayer.jsx` + `landing.css` (component)

**Analog:** itself L317-340. Each label is a `div.dgl-region-label` with a ref and text child; the engine only transforms the box.
```jsx
<div ref={labelGraphRef} className="dgl-region-label" onClick={() => fly("graph")}>
  Graph Viewer
</div>
...
<div ref={labelAiEngineRef} className="dgl-region-label" onClick={() => fly("aiengine")}>
  AI Engine
</div>
```
Add a second line inside, e.g. `<div className="dgl-region-summary">{...}</div>`, styled in `landing.css` next to `.dgl-region-label` (L125-142: `text-transform: uppercase`, `white-space: nowrap`, `font-size: clamp(...)`; the summary line should set `text-transform: none` and a smaller, secondary color). Rename "AI Engine" to `t("LLM model")`. Note that Connectors, AI Engine, Reasoner and API Docs render only when `!degramHost` (L326-339), so the summary loader must skip those fetches in host mode. Badge goes top-right on this layer only.

### `ui-v2/src/screens/ProjectsScreen.jsx` (component, CRUD)

**Analog:** itself. Members panel L228-262: replace the static `Badge` (L235) with `Select`.
```jsx
<span style={{ flex: 1 }}>{m.username}</span>
<Badge variant={m.role === "owner" ? "signal" : "soft"}>{m.role}</Badge>
<Button variant="secondary" size="sm" onClick={() => removeMember(m.username)}>Remove</Button>
```
Existing `Select` usage (L262): `<Select options={ROLE_OPTIONS} value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} style={{ width: 130 }} />`. Request call pattern (L142): `await apiFetch(projectUrl(project, \`/members/${encodeURIComponent(username)}\`), { method: "DELETE" })`. Race guard: the `panelScope.current` comparison at L93 (`if (scope === panelScope.current) ...`), which is in the uncommitted working tree (D-49 hygiene: owner settles before editing). Admin gate: `user?.isAdmin` (L40 pattern `canAdminister`). Panel chrome: `<Panel title=... style={{ userSelect: "text" }}>`.

---

### `DG/src/DG.Core/Data/ConnectorSessionClient.cs` (service, request-response)

**Analog:** `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs`. Copy:
```csharp
public sealed class ConnectorHeartbeatClient : IConnectorHeartbeatClient
{
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(6);
    private readonly HttpClient _httpClient;
    public ConnectorHeartbeatClient(HttpMessageHandler? handler = null)
    { _httpClient = handler is null ? new HttpClient() : new HttpClient(handler); }
    ...
    using var response = await _httpClient.SendAsync(request, cancellationToken)
        .WaitAsync(RequestTimeout, cancellationToken).ConfigureAwait(false);
    if (response.StatusCode == HttpStatusCode.OK) { var body = await response.Content.ReadAsStringAsync(cancellationToken)... TryReadPayload(body) }
```
Key points: handler injection for tests, `NormalizeUrl`, secrets only flow into headers/body and never into fields, exceptions or the result record. Differences: `HttpClientHandler { CookieContainer = ... }` when `handler is null` (two-step login then connector-session then best-effort logout), send header `X-DG-CSRF: 1`, and refuse remote non-loopback `http://` before any request (new rule, no analog). Result record modeled on `HeartbeatResult`/`HeartbeatOutcome` in `DG.Core/Models/`.

### `DG/tests/DG.Tests/ConnectorSessionClientTests.cs`

**Analog:** `ConnectorHeartbeatClientTests.cs` L1-60. Copy the private nested `StubHttpMessageHandler` (responder func or exception, `CallCount`, `LastRequest`) and `Json(HttpStatusCode, string)` helper; one `[Fact]` per outcome with `Assert.Equal(1, handler.CallCount)` style. For a multi-request sign-in the stub needs to record all requests (a list instead of `LastRequest`) and be able to set a `Set-Cookie` header on the login response.

### `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`

**Analog:** itself L36-70. Fresh GUID with ADR comment (L36-40), `NonPersistentStringParam` input (L50-57), optional flag (L61), `Connect` boolean (L59). Add `Username`, `Password` (both `NonPersistentStringParam`, optional) and `Project`; output `Session`. Whole file is under `#if GRASSHOPPER_SDK`. `ConnectorComponentPortContractTests.cs` exists and must be updated to the new port list. `ValidatorComponent` and `ComputgraphPublishComponent` keep GUIDs and port order; only the `Token` input description and prefix check change.

---

### Fork sidebar (component repo, event-driven)

**Analog:** itself. Committing repository: **component** (`apps/degram`). Name every path as `apps/degram/apps/desktop/...`.

`src/degram/sidebar-nav.ts`:
```ts
export const DEGRAM_NAV_IDS = ['new-session', 'dg-graph', 'dg-model', 'dg-connectors', 'models', 'dg-menu'] as const   // L33: insert 'dg-projects' after 'models'
const REGION_BY_ID: Readonly<Record<string, DgRegion>> = { 'dg-graph': 'graph', 'dg-model': 'model', 'dg-connectors': 'connectors', 'dg-menu': 'landing' }   // add 'dg-projects': 'projects'
{ id: 'models', label: nav.models, icon: icon('layers'), route: DEGRAM_MODELS_PATH },   // add after: { id: 'dg-projects', label: nav.projects, icon: icon('folder'), route: DG_PAGE_PATH }
```
`electron/degram/dg-view.ts`: L26 `export type DgRegion = 'landing' | 'graph' | 'model' | 'connectors'`, L30 `DG_REGIONS`, L33 `HOST_GO_FRAGMENT = /^#degram-go=(landing|graph|model|connectors)$/`; add `projects` to all three; L384 uses `HOST_GO_FRAGMENT` in the navigation allowlist, so nothing else changes there. `ipc.ts` `asRegion` (name from research, not re-read here) must accept it. `src/degram/i18n.ts`: `nav: { models: string ... }` type at L43, EN `models: 'Models'` L177, RU `models: 'Модели'` L338; add `projects: 'Projects'` / `'Проекты'` in all three places. `sidebar.test.tsx:214` asserts the `models` row navigation; extend with row order and label tests. Run: `npx vitest run --project ui src/degram/sidebar.test.tsx` (baseline 14 pass). The file-header comment of `sidebar-nav.ts` says "exactly six" rows; update to seven.

---

## Shared Patterns

### Structured auth errors
**Source:** `data-service/delegation.py:86-128` (`auth.auth_error(error, hint, code, status)`) and `app.py` `_structured_error_response(error, hint, code, status)`.
**Apply to:** `connector_session.py`, `auth_routes.py` new handlers (use `auth.auth_error`), `app.py` new handlers (use `_structured_error_response`). Every answer carries `{error, hint, code}`; the UI maps `code` to RU via `describeError`.

### Store lock and atomic JSON store
**Source:** `delegation.py:177-183`, `auth._STORE_LOCK`, `auth._load/_save`.
**Apply to:** `connector_session.py`, role-change route, the ops script.
```python
with auth._STORE_LOCK:
    rows = auth._load(_file(), _KEY)
    ...
    auth._save(_file(), _KEY, kept)
```

### Cache-Control: no-store on credential answers
**Source:** `auth_routes.py:310` (`response.headers["Cache-Control"] = "no-store"`).
**Apply to:** `POST /auth/connector-session`.

### Revocation wiring
**Source:** `app.py:4979-4981`, `auth_routes.py:416`.
**Apply to:** every place that revokes `delegation` tokens (member removal, password change, company reassignment, user deletion): add the connector-session revoke beside it.

### Route classification gate
**Source:** `route_policy.py` rows plus `test_route_inventory.py` (every route has `require_principal`, registered routes equal policy keys both ways) and `test_security_boundary_spec.py` fenced blocks.
**Apply to:** every new or changed route; spec update and route in the same commit.

### Cookie plus CSRF client transport
**Source:** `ui-v2/src/lib/apiClient.js` `apiFetch`; asserted in `connector-access-api.test.mjs`.
**Apply to:** all new `ui-v2/src/lib/*Api.js`.

### Language persistence key
**Source:** `ui-v2/src/lib/auth.js:28-43`. `dgv2_lang` added to `KEPT_KEYS`.

### Working tree hygiene
`ProjectsScreen.jsx`, `lib/auth.js`, untracked `ui-v2/tests/*` and data-service WIP are uncommitted (D-49). Stage by explicit path; never `git add -A` after `dotnet build` (tracked `bin/obj`).

## No Analog Found

| File / piece | Role | Data Flow | Reason |
|---|---|---|---|
| `ui-v2/src/i18n/*` provider and `t()` | provider | transform | No i18n layer exists. Use RESEARCH Pattern 3 and `hostLang()`/`KEPT_KEYS` for the edges only |
| Add-in CookieContainer sign-in and loopback-only http refusal | service | request-response | `ConnectorHeartbeatClient` is a single Bearer POST, no cookie flow; use RESEARCH "Add-in two-step sign-in" |
| `data-service/tests/test_connector_session.py` cascade matrix | test | CRUD | Closest are `test_delegated_token.py` and `test_degram_grants.py`, but no existing test covers the exempt-versus-grant matrix; derive from `test_connector_access.py` after rewrite |

## Metadata

**Analog search scope:** `data-service/*.py`, `data-service/tests/`, `ui-v2/src/{lib,screens,landing}`, `ui-v2/tests/`, `DG/src/DG.Core/Data`, `DG/src/DG.Grasshopper/Components`, `DG/tests/DG.Tests`, `apps/degram/apps/desktop/{src/degram,electron/degram}` (named files only).
**Files read in full or by targeted range:** about 20. `delegation.py`, `auth_fixtures.py` read in full; others by grep-located ranges.
**Not verified:** `ipc.ts` `asRegion` line numbers, `ConnectorsScreen.jsx` and `HostedConnectorsTable.jsx` contents, `NO_STATE` definition, `Principal` dataclass fields, `test_policy_table_size` constant. Planner or executor should read them when the task is scheduled.
**Pattern extraction date:** 2026-10-12
