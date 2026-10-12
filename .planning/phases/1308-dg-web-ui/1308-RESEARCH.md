# Phase 1308: DG Web UI — Research

**Researched:** 2026-10-12
**Domain:** FastAPI data-service auth/tenancy (roles, grants, connector sign-in), React 18 + Vite `ui-v2` (i18n, landing, Projects/Connectors screens), C# Grasshopper add-in sign-in, DeGram fork sidebar (component repo)
**Confidence:** HIGH for codebase facts (every route, store and test named below was read or run in this session); MEDIUM for UX/limit values marked `[ASSUMED]`

## User Constraints (from CONTEXT.md)

There is **no `1308-CONTEXT.md`**. The owner instruction for this run (2026-10-12) is "skip discussing, approve all recommendations": every item under `## Open Questions — Recommendations` below is a **locked decision** for planning, as are the owner decisions copied here from `1301-CONTEXT.md` and `1308-SEED.md`.

### Locked Decisions
- **D-36 [owner 2026-10-10]:** In DG Web UI the role of an existing project member can be changed (outside the DeGram client). Needs a data-service route (project owner; the last owner is never demoted) and a Web UI action.
- **D-37 [owner 2026-10-10]:** The project export policy (`providerExportAllowed`, `wholeDefinitionAllowed`) in DG Web UI is changed by a DG admin only; the control is visible to and changeable by a DG admin only. A project owner does not change it.
- **D-38 [owner 2026-10-10]:** A small EN / RU language badge in the corner of the start screen; with RU selected the whole DG Web UI is Russian. Owner-fixed translations: «Design Grammars.» → «Грамматика.»; «Encode your design intent.» → «Граф правил проекта.»; «System initiated» → «Система инициализирована». The rest follows `1301-D38-GLOSSARY.md`. Outside the DeGram client (`ui-v2`).
- **D-49 [owner 2026-10-12]:** Connector access (Grasshopper, Revit, …) is issued **only** as a grant per connector, separately for each; **connector tokens are not created**; the Grasshopper add-in signs in with the user's account like DeGram; **project owner and DG admin are exempt** from the grant; editor and viewer need a grant. Amends D-46.
- **D-32:** provider export allowed by default; `wholeDefinitionAllowed` false by default; malformed store fails closed (already implemented and committed, see Q7).
- **Seed items:** landing summaries (Graph Viewer: classes, properties, rules; Model Viewer: Design States, Validation runs; «LLM model» (renamed from AI Engine): Provider, Model; Connectors: Active, Keys issued; Reasoner: Active); sidebar «Projects» / «Проекты» under «Models» / «Модели» in DeGram; cleanup of UAT account `uat-pw-bd30ce@dg.local` and project `uat-pw-bd30ce`.
- **D-42 / D-45 / D-46 (context, amended by D-49):** DeGram sidebar set; connectors table with «Вкл/Выкл» (green/red inside DeGram, monochrome in Web UI); per-connector access requests.

### Claude's Discretion
All HOW choices not fixed above (i18n mechanism, route shapes, summary data sources, session TTLs, plan split). Resolved in `## Open Questions — Recommendations`.

### Deferred Ideas (OUT OF SCOPE)
- Changing DeGram Desktop build/launch, `hermes update`, Docker/service operations for DeGram, paid inference, package installs (CLAUDE.md boundaries) — not authorized by this phase.
- Translating the *body* of the developer API reference (`ui-v2/src/screens/apidocs/content/*.js`) — see Q4, kept English; only its chrome is translated.
- A masked password dialog (Eto) in Grasshopper — see Q3, deferred.
- Changing DeGram's own 7-day status semantics — see Q3.

## Project Constraints (from CLAUDE.md)

- Single Neo4j DB with `project` isolation; **no graph schema change in this phase** (auth data is JSON under `DG_DATA_DIR`), so the Schema Change Propagation list is *not* triggered. `[VERIFIED: spec/SECURITY-BOUNDARY.md "No graph schema change"]`
- `spec/SECURITY-BOUNDARY.md` governs routes, principals, secrets; **adding a route/principal means updating the machine-checked fenced blocks in the same commit** and running `test_route_inventory.py` + `test_security_boundary_spec.py`.
- DeGram: framework `.planning/` and `DG_OBSIDIAN/` are the only authorities; component (`apps/degram`) tasks name their committing repository; child commit + push to the fork **need explicit owner authorization**; framework gitlink bump only after the child commit is on the fork; `python tools/degram/workspace.py verify` before any task touching `apps/degram/**`, `integration/degram/**`, `spec/degram/**`, `tools/degram/**`, `ui-v2/src/degram/**`. Verified green this session. `[VERIFIED: ran workspace.py verify]`
- No Desktop launch/build against the installed Hermes profile; no `hermes update`; no package installs.
- UI rebuild: `docker compose build --no-cache design-grammars` (Docker layer cache serves stale `index.html`).
- `#if GRASSHOPPER_SDK` guards all GH-dependent C# code; testable logic goes in `DG.Core` (no GH deps).
- DSH workers: briefs need absolute paths; "do not commit"; do not touch `DG/src/*/bin/`, `obj/`, lockfiles, `graphify-out/`, `.planning/milestones/`, `DG_OBSIDIAN/archive/`. Note: `DG/src/*/bin|obj` are **tracked and currently dirty** — never `git add -A` after a `dotnet build`.
- Windows paths: use Write/Edit, not sed (memory: backslash corruption); docker exec paths need `MSYS_NO_PATHCONV=1`.
- Session end commits only the session's own files; commit trailer per attribution reminder.

<phase_requirements>
## Phase Requirements

No IDs are mapped in REQUIREMENTS.md/ROADMAP.md (`Requirements: TBD`). **Proposed IDs (WEBUI-xx), to be added to REQUIREMENTS.md by the planner:**

| ID | Description | Research Support |
|----|-------------|------------------|
| WEBUI-01 | EN/RU language badge on the start screen; choice persists per browser; DeGram host follows `?lang=` | Q4 (resolution order, `KEPT_KEYS`, `hostLang()`) |
| WEBUI-02 | Entire DG Web UI renders in Russian with RU selected (glossary + owner translations); server errors mapped by `code`; key-coverage test keeps EN/RU in sync | Q4, Pitfalls 1-4, Validation |
| WEBUI-03 | Project owner/admin changes an existing member's role (`PUT /projects/{project}/members/{username}`), last owner protected, UI action | Q6 |
| WEBUI-04 | Admin-only project settings control for `providerExportAllowed` / `wholeDefinitionAllowed` | Q5 |
| WEBUI-05 | Landing menu items show summaries under their captions; «AI Engine» renamed «LLM model» | Q1 |
| WEBUI-06 | «Projects» / «Проекты» row in the DeGram sidebar under «Models», opening the DG PROJECTS screen | Q2 |
| WEBUI-07 | Server: per-connector grant model (owner/admin exempt, editor/viewer need a grant), connector sign-in session replaces tokens, `POST /connectors/{id}/credentials` retired, new status meaning | Q3 |
| WEBUI-08 | Grasshopper add-in signs in with the user's account (CONNECTOR, VALIDATOR, COMPUTGRAPH PUBLISH), no token input | Q3 |
| WEBUI-09 | Web UI Connectors screen, DeGram-hosted connectors table and API docs content drop the token flow | Q3 |
| WEBUI-10 | `spec/SECURITY-BOUNDARY.md` (+ API.md, GRASSHOPPER.md, DEPLOYMENT.md, release notes) and route inventory reflect all route/principal changes | Q3, Security Domain |
| WEBUI-11 | Live rollout: image rebuild from committed code, token retirement, D-32 verification, UAT account/project cleanup — each behind a checkpoint | Q7, Q8, Runtime State Inventory |
</phase_requirements>

## Summary

Phase 1308 is five independent-ish workstreams on two repositories plus one component slice: (1) an in-house EN/RU i18n layer for `ui-v2` (~13.7k JS/JSX lines; no i18n lib today), (2) two small admin features on the Projects screen (member role change, admin-only export policy), (3) landing summaries, (4) the D-49 connector-access rework, which is the only structurally large and security-relevant item, and (5) a one-row DeGram sidebar addition that lives in the fork.

Four facts changed the picture versus the seed. **D-32 needs no rebuild**: the running `data-service` image (built 2026-10-12 06:31) holds files byte-identical (ignoring CRLF) to `HEAD` for `degram_policy.py`, `app.py`, `auth.py`, `route_policy.py`, `connectors.py`, `connector_access.py`; the unrelated uncommitted WIP (`cypher_allowlist.py`, `dg_context.py`) is **not** in the image. **D-37's server half already exists** (`GET|PUT /projects/{project}/degram-policy`, admin-only), so D-37 is a UI task. **D-36's role mutation already exists** inside `POST /auth/invites` for an existing account (with last-owner protection), but there is no dedicated route; add a proper `PUT`. **D-49 cannot be done by deleting tokens**: the Grasshopper add-in uses the `dgc_` token for four things (heartbeat + Neo4j bundle, `/computgraph/publish`, `/validation/publish`, `/validation/view`, `/designstate/capture`), so it needs a replacement credential with the same principal shape.

**Primary recommendation:** Build the D-49 replacement as a *connector sign-in session* (`dgk_` Bearer minted by `POST /auth/connector-session` from a short-lived login cookie, exactly parallel to `POST /auth/degram/session-exchange`) that resolves to the existing `connector` principal kind, so every `_CON` / `connector-self` route row keeps working unchanged, the grant is re-checked live on every request, and `dgc_` tokens and `POST /connectors/{id}/credentials` are retired. Do i18n with a ~100-line in-house `t()` (English text as key) plus a static key-coverage `node:test`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Language selection + dictionary | Browser / Client (`ui-v2`) | — | Pure presentation; persisted in `localStorage`; DeGram host passes `?lang=` |
| Server error → RU message | Browser / Client | API (stable `code`) | API keeps English `{error,hint,code}`; client maps `code` |
| Role change, last-owner guard | API / Backend (`auth`, `app.py`) | Browser (control) | Authorization and invariant must be server-side |
| Export-policy edit | API (existing admin route) | Browser (admin-only panel) | `ADMIN_REQUIRED` enforced by route policy; UI hides it for non-admins |
| Landing summary counts | API (new read route + existing reads) | Browser | Counting over Neo4j must be project-scoped server-side |
| Connector grant / exemption decision | API (`connector_access.py`) | — | Never decided by the client or the add-in |
| Connector sign-in session | API (new module + `auth_routes.py`) | Add-in (HTTP client) | Credential minting/revocation is server state |
| Add-in account sign-in | Add-in (`DG.Core` client + GH components) | API | `DG.Core` holds testable HTTP logic; GH layer only wires inputs |
| «Projects» sidebar row | DeGram Desktop (component repo `apps/desktop`) | `ui-v2` host-signal parser | Sidebar is DeGram's; `ui-v2` only accepts the `projects` region |
| Status «Вкл/Выкл» derivation | API (`connectors.py` / session store) | Browser (display) | Computed from live sessions server-side |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.x (`ui-v2/package.json`) | UI | Already the stack `[VERIFIED: ui-v2/package.json]` |
| In-house `ui-v2/src/i18n/` (new, ~100 lines) | — | `t()`, `plural()`, `LanguageProvider`, `useT()` | Two locales, no new dependency, offline-testable with `node:test`; `Intl.PluralRules('ru')` is built in `[VERIFIED: node -e Intl.PluralRules('ru') → 1:one 2:few 5:many 21:one]` |
| FastAPI + Pydantic (existing) | as installed in `data-service` | New routes, `StrictBool`, enums | Existing pattern |
| `node:test` + `esbuild` (installed) | Node 20.20 | UI unit + headless-browser harnesses | Existing `ui-v2/tests/*.test.mjs` (231 pass) `[VERIFIED: ran]` |
| `pytest` | 9.1.1 in container; runs locally | data-service tests | `1013 passed` on the four directly relevant files `[VERIFIED: ran]` |
| `vitest` 4.1.10 (fork) | in `apps/degram/apps/desktop` | Sidebar tests | `sidebar.test.tsx` 14 pass in 25 s `[VERIFIED: ran]` |
| xUnit (`DG.Tests`) | .NET 10 SDK present | `DG.Core` client tests | Existing `ConnectorHeartbeatClientTests` stub-handler pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `System.Net.Http` `CookieContainer` (BCL) | built in | Add-in two-step sign-in | Login cookie used for ~1 s then logged out |
| `Intl.PluralRules` / `Intl.DateTimeFormat` | built in | RU plurals, date formatting | Replace the three `toLocale*` call sites (`ConnectorsScreen.jsx:25`, `DegramGrantsPanel.jsx:19`, `GraphScreen.jsx:72`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-house i18n | `i18next` + `react-i18next` | Adds 2 packages (supply-chain gate, install not authorized for DeGram boundaries, generic for the repo); ICU/plurals are overkill for 2 locales. `[ASSUMED]` that it would work, not evaluated further. |
| English-text-as-key | Structured ids (`connectors.create`) | Ids are tidier but force ~500-800 key invents and a rename pass; text keys let the sweep be mechanical (`"Log in"` → `t("Log in")`). Context disambiguation via `tc(ctx, text)`. |
| `dgk_` connector session (recommended) | Reuse `dgd_` delegated token | `dgd_` is already accepted by read routes DeGram uses; adding write routes (`/computgraph/publish`, `/validation/publish`) to `_DEL` would let DeGram tokens write. A separate token class keeps the DeGram boundary intact. |

**Installation:** none. No new npm/pip/NuGet packages in any repository.

## Package Legitimacy Audit

No external packages are installed by this phase (i18n, session store, add-in client and tests all use the standard library or already-installed dependencies). `gsd-tools package-legitimacy check` not required.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | None installed |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Browser (ui-v2)                                    data-service (FastAPI)                         Stores (DG_DATA_DIR JSON) / Neo4j
-----------------------------------------------------------------------------------------------------------------------------
Landing ──GET /llm/settings────────────────────────▶ session  (provider, model)
        ──GET /reasoner/settings───────────────────▶ session  (selected)
        ──GET /validation/runs/{p}─────────────────▶ member viewer ──────────────────────────▶ Neo4j ValidationRun
        ──GET /projects/{p}/summary (NEW)──────────▶ member viewer ── counts ────────────────▶ Neo4j (Class/Prop/Rule) + connector-access.json + degram-grants.json
        ──GET /connectors?project=p────────────────▶ session ── status from live sessions ────▶ connector-sessions.json (NEW)
Projects screen
        ──PUT /projects/{p}/members/{u} (NEW)──────▶ member owner|admin ── last-owner guard ─▶ auth-memberships.json
        ──GET|PUT /projects/{p}/degram-policy──────▶ admin only (EXISTS) ────────────────────▶ degram-policy.json
Connectors screen (no tokens)
        ──POST /connector-access-requests──────────▶ member viewer   ┐
        ──GET|POST|DELETE /projects/{p}/connector-access ▶ owner|admin ┴─▶ connector-access.json   (owner/admin exempt; editor+viewer need a row)

Grasshopper add-in (DG.Core client)
   1 POST /auth/login ───────────────(cookie, CSRF hdr)──▶ public, throttled ──▶ auth-sessions.json
   2 POST /auth/connector-session {project, connector_id} ▶ member viewer ── grant/exempt check ──▶ connector-sessions.json (token hash, TTL 8 h, last_seen)
   3 POST /auth/logout  (drops the cookie session; connector session is independent)
   4 Bearer dgk_… ─▶ /connectors/heartbeat · /computgraph/publish · /validation/publish · /validation/view/* · /designstate/capture
          └─ every request: live re-check (user exists, project bound, owner|admin|active grant, company unchanged) ▶ else 401/403

DeGram Desktop (component repo)  sidebar row «Проекты» ─ degram.dgGo('projects') ─ #degram-go=projects ─▶ ui-v2 hostMode.parseHostSignal ─▶ ProjectsScreen
```

### Recommended Project Structure
```
data-service/
├── connector_session.py        # NEW: dgk_ store (hash only), issue/authenticate/revoke/derive_status; modelled on delegation.py
├── connector_access.py         # CHANGE: exemption = owner|admin only; add is_authorized(username, project, connector_id)
├── connectors.py               # CHANGE: registry + overview(status from sessions); create_credential retired
├── auth.py                     # CHANGE: resolve_connector_principal reads dgk_; Principal gains connector_id
├── auth_routes.py              # NEW routes: POST/DELETE /auth/connector-session
├── app.py                      # CHANGE: 410 on credentials POST, heartbeat/capture use new resolver, PUT members, GET summary
├── route_policy.py             # rows for every new/changed route
└── tests/auth_fixtures.py      # connector_token_for() re-implemented on connector_session (single seam for ~12 test files)
ui-v2/src/
├── i18n/                       # NEW: index.js (t, tc, plural, describeError), en.js (optional glossary), ru.js, LanguageProvider.jsx, LanguageBadge.jsx
├── lib/{projectSettingsApi,memberApi,summaryApi,runGroups}.js   # NEW thin API/pure helpers (runGroups shared with ModelScreen)
├── landing/LandingLayer.jsx    # summaries inside each .dgl-region-label; badge slot
├── screens/{ProjectsScreen,ConnectorsScreen,HostedConnectorsTable}.jsx   # role select, policy panel, no token UI
└── screens/apidocs/content/    # 02/03/04/05 updated for connector sign-in
DG/src/DG.Core/Data/            # NEW ConnectorSessionClient (+ interface), replaces ConnectorHeartbeatClient; DataServiceRequestAuth 'dgk_'
DG/src/DG.Grasshopper/Components/ConnectorComponent.cs  # inputs Username/Password/Project/Connect; output Session
apps/degram/apps/desktop/{electron/degram/dg-view.ts, ipc.ts, src/degram/{sidebar-nav.ts,i18n.ts,sidebar.test.tsx}}   # COMPONENT repo
```

### Pattern 1: Connector sign-in session (mirror of the DeGram session exchange)
**What:** `POST /auth/connector-session` (policy `_MEM`, source `body`, role `viewer`, cookie + CSRF) with `{project, connector_id}`. Handler: stored membership **or** admin; `connector_id` in `CONNECTOR_IDS` (404 `CONNECTOR_NOT_FOUND` for `degram`); allow if effective role is `owner` (stored owner or admin), else require an active `connector_access` row (403 `CONNECTOR_ACCESS_REQUIRED`). Mint `dgk_` + `secrets.token_urlsafe(32)`, store only SHA-256 hash with `{connector_id, username, project, company, issued_at, expires_at (8 h), last_seen, revoked}`. Response `{token, project, connectorId, username, expiresAt, expiresInSeconds, neo4j?}` with `Cache-Control: no-store`; `neo4j` bundle only when `auth.deployment_profile() != "multi-user"` (same D-07 rule as today's heartbeat). Authentication (`auth.resolve_connector_principal`) hashes the Bearer, rejects revoked/expired, re-checks live: user exists, `connector_access.is_authorized(...)`, project company unchanged; returns `Principal(kind="connector", username, bound_project, credential_id, connector_id)`.
**When to use:** all connector authentication after this phase; `dgc_` is no longer accepted anywhere.
**Example:**
```python
# Source: pattern copied from data-service/auth_routes.py exchange_degram_session() and delegation.py (read this session)
@router.post("/auth/connector-session", status_code=201)
def connector_session(payload: ConnectorSessionRequest, request: Request, response: Response):
    principal = request.state.principal            # cookie user, CSRF already enforced by require_principal
    role = auth.effective_role(principal, payload.project)   # admin -> "owner"
    if role is None:
        raise auth.auth_error("Not authorized for the requested project.", "Request project access from a project owner.", "PROJECT_FORBIDDEN", 403)
    connector_access.check_connector(payload.connector_id)
    if not connector_access.is_authorized(principal.username, payload.project, payload.connector_id, role=role):
        raise connector_access.access_required()
    token, record = connector_session.issue(username=principal.username, project=payload.project, connector_id=payload.connector_id)
    response.headers["Cache-Control"] = "no-store"
    return connector_session.public_answer(token, record, neo4j=_bundle_or_none())
```

### Pattern 2: Role change under the store lock
**What:** `PUT /projects/{project}/members/{username}` body `{role}`; policy `_p(_MEM, source="path", role="owner")` (owner or admin). Inside `auth._STORE_LOCK`: 404 `MEMBER_NOT_FOUND`, 422 `ROLE_INVALID`, 409 `LAST_OWNER` when demoting the only owner, then `auth.set_membership`. Same-role request is a 200 no-op. Reuse the guard already written in `create_project_invite` (`app.py` ~5008-5022) rather than re-deriving it; extract a helper used by both.
**Example:**
```python
# Source: app.py remove_project_member() / create_project_invite() (read this session)
@router.put("/projects/{project}/members/{username}")
def change_member_role(project: str, username: str, payload: MemberRoleRequest):
    _check_project_name(project)
    if payload.role not in auth.ROLES: raise _structured_error_response("That role is not valid.", "Use one of: viewer, editor, owner.", "ROLE_INVALID", 422)
    with auth._STORE_LOCK:
        current = auth.get_role(username, project)
        if current is None: raise _structured_error_response("That user is not a member of this project.", "List the project members and try again.", "MEMBER_NOT_FOUND", 404)
        if current == "owner" and payload.role != "owner" and auth.count_owners(project) <= 1:
            raise _structured_error_response("A project must keep at least one owner.", "Promote another member to owner before changing this role.", "LAST_OWNER", 409)
        auth.set_membership(username, project, payload.role)
    return {"project": project, "username": username.strip().lower(), "role": payload.role}
```

### Pattern 3: English-text-as-key i18n with a static coverage test
**What:** `t("Log in")`, `t("{n} node", {n})` with `plural("project", n)` using `Intl.PluralRules(lang)`. EN returns the key (after `{name}` interpolation); RU looks up `ru[key]`, falling back to the key (and `console.warn` in DEV only). `tc("verb", "Create")` for same-English/different-Russian cases. Only **string literals** are allowed as the first argument (a test fails on `t(` followed by a non-literal), so extraction is mechanical.
**Example:**
```js
// Source: design for this phase; Intl.PluralRules verified in Node 20
export function plural(lang, n, forms) {            // forms: {one, few, many, other}
  const cat = new Intl.PluralRules(lang === "ru" ? "ru" : "en").select(n);
  return forms[cat] ?? forms.other;
}
const dict = { ru: Object.freeze({ "Log in": "Войти" /* … */ }) };
export function translate(lang, key, params) {
  const raw = lang === "ru" && Object.hasOwn(dict.ru, key) ? dict.ru[key] : key;   // hasOwn: no prototype keys
  return params ? raw.replace(/\{(\w+)\}/g, (_, k) => (k in params ? String(params[k]) : `{${k}}`)) : raw;
}
```

### Anti-Patterns to Avoid
- **Reusing `dgd_` for the add-in** — widens the DeGram token's write scope (see Alternatives).
- **Changing every route row for D-49** — keep the `connector` principal kind and `_CON` rows; only the resolver changes.
- **Translating with `dangerouslySetInnerHTML`** — none exists in `ui-v2/src` (checked); keep it that way, interpolate as text only.
- **Persisting the language under a tenant key that sign-out wipes** — `clearTenantBrowserData()` deletes every `dgv2_*` key except `KEPT_KEYS`; add `dgv2_lang` there.
- **Building from the dirty working tree** for the live rebuild — use a clean export of committed code (Q7).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token store with live revocation | A new store format | Copy the shape of `delegation.py` (`auth._load/_save` under `auth._STORE_LOCK`, hash-only, retention window) | Atomic writes, Windows replace retries, named errors already solved |
| Password verification / throttling for the add-in | A second login path | Existing `POST /auth/login` (+ `auth.throttle_*`, scrypt slots) then the exchange | No new credential-checking surface |
| Last-owner invariant | Re-implementation | `auth.count_owners` under `_STORE_LOCK` (as `remove_project_member`) | Race-free, already tested |
| Russian plural forms | A hand-written `n % 10` switch | `Intl.PluralRules('ru')` | Correct for 11-14, 21, 22… |
| Date/time formatting | `toLocaleDateString("en-US")` | `Intl.DateTimeFormat(lang)` | Language follows the badge |
| Model Viewer "Design States" count | A second grouping | Extract the `groups` logic from `ModelScreen.jsx:449-459` into `lib/runGroups.js` and use it in both | Landing count equals the Model Viewer badge by construction |
| Route/spec drift | Manual doc edits | Update the fenced blocks and run `test_security_boundary_spec.py` | Test fails on any drift |

**Key insight:** every security-sensitive piece of D-49 has a working twin in the DeGram grant/delegation code; the safest implementation is a parallel module, not a new design.

## Runtime State Inventory

D-49 retires stored credentials and the cleanup item removes an account; both leave runtime state that a file edit will not fix.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data-service/data/connector-credentials.json`: 22 records, **11 not revoked** (grasshopper ×8, dynamo ×2, revit ×1 across `default-project`, `v8-ui-smoke`, `DG-1200-GOLDEN`, `v12-hexagonal-facade-01`, `degram-uat-c`). `connector-access.json` **does not exist** (no grant ever issued). `degram-pairings.json` holds retired pairings, one belongs to `uat-pw-bd30ce@dg.local`. `auth-users.json`: 3 users (`erarchitech@gmail.com` admin, `asiyagerey94@gmail.com`, `uat-pw-bd30ce@dg.local`). `auth-memberships.json`: `uat-pw-bd30ce@dg.local` owner of `uat-pw-bd30ce`; `asiyagerey94` is **editor** of `degram-uat-c`. | Data migration (one-off script, dry-run first): mark all credentials `revoked` with `retired: "D-49"`; remove the UAT user, its membership, its pairing row; no sessions/grants/invites/delegated-token rows reference it (verified 0 mentions). Neo4j: project `uat-pw-bd30ce` has **0 nodes** (read-only count), so nothing to delete in the graph. `asiyagerey94` (editor) will need per-connector grants after the rollout. |
| Live service config | n8n workflows do not call connector routes (they call `/llm/generate`, `/mcp`, `/execution-result` with the service token) `[VERIFIED: route_policy rows]`. | None. |
| OS-registered state | None — verified by scope: no scheduled task or service embeds connector token names. | None. |
| Secrets / env vars | New optional `DG_CONNECTOR_SESSION_TTL_SECONDS` (default 28800) needs documenting in `spec/DEPLOYMENT.md`; no key renamed. `SECURITY-BOUNDARY.md` §9 step 11 ("revoke every Grasshopper connector credential and reissue") becomes "connector sign-in sessions end on password change / restart of the store"; rewrite it. | Code edit + docs. |
| Build artifacts / installed packages | **Installed Grasshopper plugin** on the owner's PC still carries the old `ConnectorComponent` (`3F9B1C7E-…`) and token inputs; saved `.gh` canvases wired to it break. `DG/src/*/bin|obj` are tracked and dirty. Docker image `design-grammar-system-data-service` (06:31 today) and `design-grammars` image carry the old code until rebuilt. | Rebuild plugin (`dotnet build .\DG\DG.sln -c Release`) as an owner step; new CONNECTOR GUID per ADR-825-3 pattern + release-notes re-wire note; rebuild images with `--no-cache`. Never `git add` build output. |

## Common Pitfalls

### Pitfall 1: `dgv2_lang` wiped on sign-out
**What goes wrong:** language resets to EN every sign-out / account switch.
**Why:** `clearTenantBrowserData()` (`lib/auth.js:28-40`) removes every `dgv2_*` key not in `KEPT_KEYS = {"dgv2_theme"}`.
**How to avoid:** add `dgv2_lang` to `KEPT_KEYS`; unit-test it.
**Warning signs:** badge shows EN after logout in a manual run.

### Pitfall 2: Static scan misses dynamic strings
**What goes wrong:** `t(\`Hello ${name}\`)` or `t(msg)` compiles but has no dictionary entry.
**How to avoid:** coverage test rejects non-literal first arguments; placeholders use `{name}`; EN/RU placeholder sets must be equal.

### Pitfall 3: Mixed language in one view
**What goes wrong:** screens translated but `ApiError.message` (English from server) or canvas labels (`graphEngine.js`/`landingEngine.js` draw text from data, not UI strings) show English.
**How to avoid:** `describeError(err)` looks up `error.<code>` first; server `error` text is the fallback. Data values (rule text, class names, project names) stay as-is by design. Grep canvas engines for UI literals during the sweep.

### Pitfall 4: Same English word, different Russian
**What goes wrong:** «Create» (project) vs «Create» (grant) need different forms; «Active» (adjective list) vs «active» (project badge).
**How to avoid:** `tc(context, text)`; the dictionary key is `"context\u0004text"`.

### Pitfall 5: Editors silently lose connector access
**What goes wrong:** today `role_satisfies(role, "editor")` appears in four places (`connector_access.access_state`, `create_request`, the `request_connector_access` handler, the credentials handler); changing only the handler leaves the UI showing «Доступен» for editors.
**How to avoid:** change the exemption to `owner` in **all** of them via one helper `connector_access.is_exempt(role)`; update `GET /connectors?project=` `access`, `HostedConnectorsTable`, `ConnectorsScreen` and the 409 `ACCESS_EXISTS` path. Existing tests `test_connector_access.py`, `test_cross_project_matrix.py` assert the old behavior and must be rewritten, not patched.

### Pitfall 6: Heartbeat is a "public" row in a machine-checked block
**What goes wrong:** `test_security_boundary_spec.py:49-51` hardcodes `POST /connectors/heartbeat` as `connector-token` in `public-routes`; moving it to a normal `_CON` row breaks the test and the spec block.
**How to avoid:** change both in one commit: policy row `_p(_CON)` (no project source; bound project is the principal's), remove the heartbeat row from the public block, update the test constants and §5 "Connector-self routes" prose (only `POST /designstate/capture` stays `connector-self`, and keep its inline bound-project check).

### Pitfall 7: Remote `http://` now carries a password
**What goes wrong:** `DataServiceRequestAuth.IsInsecureRemoteTransport` only *warns* for a bearer token; a password over plain http to a remote host is worse.
**How to avoid:** the sign-in client **refuses** (Rejected with a named message) a remote non-loopback `http://` URL; keep the warning for the session token on publish.

### Pitfall 8: `Secure` cookie vs http loopback in the add-in
**What goes wrong:** with `DG_COOKIE_SECURE=true` the .NET `CookieContainer` will not send the `dg_session` cookie over `http://`.
**How to avoid:** documented behavior: multi-user deployments are https; local profile defaults to non-Secure. Test both in `DG.Tests` with the stub handler (cookie set → exchange sends it).

### Pitfall 9: Dirty working tree on files this phase edits
**What goes wrong:** uncommitted v12 offline-repair changes exist in `ui-v2/src/screens/ProjectsScreen.jsx` (panel-scope race fix, +21/-6), `ui-v2/src/lib/auth.js` (+4/-1), untracked `ui-v2/tests/{api-security,auth-security}.test.mjs`, `projects-panel.browser.jsx`, `run-panel.mjs`; and in `data-service/` the unrelated WIP listed in Q7. Plans that edit these files will mix histories.
**How to avoid:** Wave 0 task: owner decides to commit (or stash) the ui-v2 files first as their own commit; data-service WIP stays out of every 1308 commit (stage by explicit path).

### Pitfall 10: Task ordering on `ProjectsScreen.jsx`
**What goes wrong:** the translation sweep and the role/policy features both rewrite this file.
**How to avoid:** i18n infrastructure first; features (role select, policy panel, summaries, connectors UI) are written with `t()` from the start; the sweep then covers only untouched legacy screens (GraphScreen, ModelScreen, Reasoner, AiEngine, remaining landing/auth card, SessionHistory, CandidateTable, apidocs chrome).

### Pitfall 11: Host `#degram-go` signals
**What goes wrong:** `parseHostSignal` accepts only `landing|graph|model|connectors`, and the fork's `dg-view.ts` has the same closed vocabulary (`HOST_GO_FRAGMENT`, `DG_REGIONS`, `asRegion` in `ipc.ts`). Adding `projects` on one side only makes the row a silent no-op.
**How to avoid:** change both sides; the framework half is testable (`host-degram.test.mjs`), the fork half by vitest; keep the two vocabularies in one comment cross-reference.

## Code Examples

### Language resolution (host > storage > default)
```js
// Source: ui-v2/src/lib/hostMode.js hostLang() exists today (read this session)
export function resolveLang({ isHost, hostLang, stored }) {
  if (isHost) return hostLang === "ru" ? "ru" : "en";     // DeGram owns the language inside its window
  return stored === "ru" ? "ru" : "en";                    // allowlist, never trust arbitrary strings
}
```

### Add-in two-step sign-in (DG.Core, testable)
```csharp
// Source: pattern of ConnectorHeartbeatClient (read this session); new ConnectorSessionClient
// 1) POST {base}/auth/login          {username,password}  header X-DG-CSRF: 1   -> dg_session cookie (CookieContainer)
// 2) POST {base}/auth/connector-session {project, connector_id:"grasshopper"} + CSRF -> {token:"dgk_…", project, neo4j?}
// 3) POST {base}/auth/logout (best effort). The password is never stored, logged, or placed in the result record.
public sealed record ConnectorSessionResult(SessionOutcome Outcome, string? Project, ConnectionBundle? Bundle, string? Token);
```

### Landing summary query (validated read-only against the live graph: v12 project → classes 7, properties 16, rules 12)
```cypher
// Source: ran against live Neo4j via the data-service container; shape mirrors RULES_LIST_QUERY
MATCH (n) WHERE n.project = $project
RETURN sum(CASE WHEN n:Class THEN 1 ELSE 0 END) AS classes,
       sum(CASE WHEN n:DatatypeProperty OR n:ObjectProperty THEN 1 ELSE 0 END) AS properties,
       sum(CASE WHEN n:Rule AND n.graph = 'Metagraph' THEN 1 ELSE 0 END) AS rules
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Token per connector credential (`dgc_`) | Account sign-in + per-connector grant (`dgk_` session) | D-49, 2026-10-12 | `POST /connectors/{id}/credentials` → 410; UI token reveal removed |
| Editor creates connector tokens freely (D-46) | Only owner/admin exempt; editor needs a grant | D-49 | Editors need grants |
| DeGram pairing token (`dgp_`) | Grant + session exchange (`dgd_`) | D-39 | Precedent: create route answers 410 `PAIRING_RETIRED` |
| «AI Engine» menu name | «LLM model» | owner 2026-10-09 | Rename caption + screen title; region key `aiengine` unchanged |

**Deprecated/outdated:**
- Seed claim "`degram_policy.py` default is hot-patched into the container only": stale; the image holds `HEAD` (Q7).
- Seed claim "role is set only at invitation": partly stale; `POST /auth/invites` for an existing account already changes the role (guarded), there is only no dedicated route or UI.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Connector session TTL 8 h absolute, no idle timeout, no periodic heartbeat from the add-in | Q3 | A Rhino crash leaves «Вкл» until TTL; shorter TTL would force more re-sign-ins |
| A2 | Viewer holding a grant may use the connector's whole route scope (incl. publish), as D-46 allowed | Q3 | If owner wants viewers read-only, add a min-role check on `_CON` write routes |
| A3 | ~400-800 user-visible strings in `ui-v2` (heuristic grep, not an AST count) | Q4 | Sweep effort mis-sized; the coverage test gives the true count on day one |
| A4 | API docs body stays English; only chrome translated | Q4 | Owner may want full RU docs; extra plan |
| A5 | Default language EN when nothing stored (glossary "open point" proposal) | Q4 | Owner may prefer browser-language detection |
| A6 | Per-browser persistence is enough (no server-side user profile) | Q4 | A user switching browsers re-selects |
| A7 | `i18next` would work as an alternative | Alternatives | None; not recommended |
| A8 | Landing summary «Keys issued» is renamed «Grants issued» / «Выдано доступов» because no keys exist after D-49 | Q1 | Owner may keep wording; trivial text change |
| A9 | Masked password dialog for GH deferred; non-persistent Username/Password inputs accepted | Q3 | Password visible in a GH panel on screen |

## Open Questions — Recommendations (RESOLVED)

> All recommendations below were adopted as locked decisions in `1308-CONTEXT.md` (owner instruction 2026-10-12). **Q4 language badge and `dgv2_lang` storage are SUPERSEDED by CONTEXT D-50..D-53** (single language switch in DeGram Settings → Appearance → Language; `ui-v2` has no control and stores no language).

These resolve every open item of the seed; each is a **locked decision** per the owner instruction.

### 1. Landing summaries (scope, "Active", data sources)
**Recommendation:** Per-**current-project** for Graph Viewer and Model Viewer (show «—» and no counts when no project is selected); **system-wide** for «LLM model» and Reasoner; Connectors uses the current project for grants and the caller's visible projects for «Active». No polling; load when the landing becomes active with a signed-in user; any failure renders «—» and never blocks the hero.
**Rationale:** these screens are project-scoped, so a per-project count is what the user will see on entering; LLM and reasoner settings are global.
**Sources (all named):**
- Graph Viewer: classes, properties, rules → **new** `GET /projects/{project}/summary` (`_MEM`, source `path`, viewer; Cypher above) returning `{project, graph:{classes, properties, rules}, connectors:{grantsIssued}}`. Chosen over reusing `GET /graph/{project}` to avoid downloading the whole graph on every landing.
- Model Viewer: validation runs = `runs.length` and Design States = `groupRunsByState(runs).length` from existing `GET /validation/runs/{project}` (extract `ModelScreen.jsx:449-459` into `lib/runGroups.js`; the Model Viewer badge uses `groups.length` including the «No design state» bucket, so the numbers match).
- «LLM model»: Provider, Model → existing `GET /llm/settings` (`session`); «—» when unset. Caption «AI Engine» → «LLM model» / «Модель LLM» (landing label and `AiEngineScreen` title).
- Connectors: «Active» = names of registry connectors with `status === "active"` plus «DeGram» when its card is active, from existing `GET /connectors?project=P` (names come from the registry; there is no «Rhino» connector id, Grasshopper runs inside Rhino); «Grants issued» = `summary.connectors.grantsIssued` = active `connector-access` rows + active DeGram grants of the project (a count only, no names, no secrets; safe for any member).
- Reasoner: «Active» → existing `GET /reasoner/settings`: name of `selected` from `reasoners`, else «—» (HermiT is `integrated`, Pellet `placeholder`; the seed's «Pellet» is the owner's current selection).
- Layout: render each summary as a second line **inside** the existing `.dgl-region-label` element (`textAlign` already follows the ring side; the engine only transforms the label box). Projects and DG API Docs get no summary (not requested).

### 2. Sidebar «Projects» (repository, scope, boundaries)
**Recommendation:** Split across both repositories, delivered as the **last wave**. Component (`apps/degram/apps/desktop`): new row `dg-projects` after `models` and before `dg-menu`, region `projects`; extend `DgRegion`/`DG_REGIONS`/`HOST_GO_FRAGMENT` (`electron/degram/dg-view.ts:26,30,33`), `asRegion` (`ipc.ts`), `sidebar-nav.ts` (`DEGRAM_NAV_IDS`, `REGION_BY_ID`, `degramSidebarNav`), `i18n.ts` (`nav.projects`: «Projects» / «Проекты»), tests `sidebar.test.tsx`. Framework (`ui-v2`): `hostMode.js` `parseHostSignal` regex accepts `projects` (already in `HOST_REGIONS`); test in `host-degram.test.mjs`. The row opens the **DG PROJECTS screen** inside the DG page (the existing `ProjectsScreen`, which already selects the project via `announceProject`).
**Rationale:** the sidebar with «Модели» is DeGram's (D-42); `ui-v2` has no sidebar. Splitting keeps the framework half verifiable and shippable without authorization.
**Boundaries applied:**
- Plan A (framework, no authorization needed): `hostMode.js` + test; works as a no-op until the component ships.
- Plan B (component repo, `checkpoint:human-action` first): owner authorizes a **child commit** on a development branch; tests run locally with `npx vitest run --project ui src/degram/sidebar.test.tsx` (baseline 14 pass, ~25 s; no Desktop launch); the **push to the fork** and the framework **gitlink bump** need separate explicit authorization (CLAUDE.md ordering: child change + tests → child commit → push → gitlink bump → `workspace.py verify` on the exact pair).
- Not in this phase: installer build, Desktop launch, `hermes update`, installed-profile writes. Live acceptance of the row happens in the next DeGram release (0.1.12) under a separate authorization.
- Minor known effect: when the page returns to landing after picking a project the sidebar highlight can lag (`$degramNavRegion` is only written by sidebar clicks); same as existing rows, not a regression.

### 3. D-49: «Вкл», add-in sign-in, retirement, exemptions
**What «Вкл»/On means:** **at least one live connector sign-in session exists** for that connector (not revoked, not expired, within the caller's visible projects; an admin sees all). `derive_status` vocabulary unchanged: `active` = live session; `stale` = sessions existed, none live; `never_connected` = none ever. Add-in sets Connect=false or the component is removed → `DELETE /auth/connector-session` self-revokes → «Выкл» immediately; a crash leaves «Вкл» until the 8 h TTL (A1). DeGram's own card keeps today's rule (grant used within 7 days) because D-45 ties it to its grant exchange; aligning it is a separate decision (deferred). **Rationale:** it is the honest meaning of "someone is signed in with this connector now" and needs no timer inside Grasshopper.
**How DeGram signs in today** `[VERIFIED: auth_routes.py, delegation.py]`: the web page logs in with `POST /auth/login` (cookie `dg_session`, CSRF header), then `POST /auth/degram/session-exchange {project}` → 15-minute `dgd_` token bound to one project; requires stored membership **and** an active DeGram grant (403 `GRANT_REQUIRED`); the grant is re-checked on every request. **The add-in does the same two steps** with `POST /auth/connector-session` (Pattern 1) and then logs the cookie session out.
**Server changes (all behind D-49):**
1. `connector_access.is_exempt(role)` = `role_satisfies(role, "owner")`; replace the four `"editor"` checks (Pitfall 5). `access_state`: owner/admin → `available`; editor/viewer → `available` only with an active row, else `pending`/`requestable`.
2. New `connector_session.py`; `auth.resolve_connector_principal` reads `dgk_` and stops accepting `dgc_`; `Principal` gains `connector_id`; heartbeat and `designstate/capture` use the same resolver. `connectors.get_connector_overview` derives status from sessions, drops `credentials` summaries for registry connectors, adds `active_sessions` count.
3. `POST /connectors/{id}/credentials` → **410 `CONNECTOR_TOKENS_RETIRED`** (tombstone, same precedent as `PAIRING_RETIRED`); keep `DELETE .../credentials/{credential_id}` for one release for cleanup (its `resource:credential` resolver stays), then remove in a later phase.
4. Invalidation: sessions end on password change (`connector_session.revoke_for_user`), membership removal / role demotion below exempt without a grant (live re-check), grant revoke (live re-check), project company reassignment, user deletion; wired next to the existing `delegation.revoke_*` calls in `remove_project_member`, `change_password`, `set_project_company`.
5. Neo4j bundle returned only in the `local` profile, as the heartbeat does today (D-07).
**Add-in changes:** `DG.Core/Data/ConnectorSessionClient` (+ interface, tests with the stub handler pattern) replaces `ConnectorHeartbeatClient`; `DataServiceRequestAuth` accepts `dgk_` (prefix check + message templates in `ErrorMessageTemplates`). `ConnectorComponent` gets a **fresh GUID** (ADR-825-3 pattern: input surface changed; old canvases show a missing-component placeholder, documented in a release note) with inputs `Username`, `Password` (both `NonPersistentStringParam`, never serialized), `Project` (optional; if blank and exactly one eligible project, the server picks it, else 422 listing names), `Connect`; new output `Session` (the `dgk_` token, non-persisted string). `ValidatorComponent` and `ComputgraphPublishComponent` **keep their port order and GUIDs**; the existing optional `Token` input is repurposed (wire `CONNECTOR.Session` into it); its description and the `dgc_`→`dgk_` check change. **Rationale:** minimum GH canvas churn; one sign-in covers all three components.
**Exemptions:** owner (stored role) and admin (`is_admin`, owner of every project, no membership row needed) skip the grant; editor and viewer need a `connector_access` row per connector; a viewer with a grant may use the connector's route scope (A2). Existing editor `asiyagerey94@gmail.com` (degram-uat-c) needs grants after rollout.
**Web UI:** `ConnectorsScreen` removes `TokenRevealPanel`, `CredentialRow`, create-credential form and the `createCredential`/`revokeCredential` calls from `connectorsApi.js`; the card shows access (grants for owner/admin, own state for others) and live sign-in count; `HostedConnectorsTable` drops the «Создать токен» button («Доступен» becomes plain text; editors now see «Запросить доступ»); API docs content pages 01-05 and 07 (all mention `dgc_`/heartbeat, verified by grep) are rewritten around account sign-in. Per-connector grants are issued from the card (`ConnectorAccessAdmin` already does Grant/Revoke); owner/admin also get a "grant to member" action for members who never requested (new small form: member select + connector, calls the existing `POST /projects/{p}/connector-access`).
**Deferred:** masked password dialog in GH (A9).

### 4. D-38 i18n approach (badge/persistence parts SUPERSEDED by CONTEXT D-50..D-53)
**Recommendation:** in-house dictionary + context, **English text as the key**, `LanguageProvider`/`useT()` at `App` root.
- **Library vs in-house:** in-house (zero dependencies, ~100 lines, `Intl.PluralRules` for Russian). Rationale: 2 locales, no installs authorized, fully testable with `node:test`.
- **Persistence/resolution:** inside the DeGram host (`isDegramHost()`): `hostLang()` (`?lang=ru|en`, passed by the fork) wins and the badge is hidden; otherwise `localStorage["dgv2_lang"]` ∈ {en, ru}; default `en` (glossary proposal, A5). No server profile (A6). Also set `document.documentElement.lang` and window title. `KEPT_KEYS` gains `dgv2_lang`.
- **Badge:** small «EN | RU» control fixed top-right of the start screen (landing layer only; the theme toggle is already bottom-right).
- **Strings:** sweep `LandingLayer`, `App`, all screens, `components/display/*`; owner translations hard-coded first; glossary rows for the rest; terms the glossary keeps Latin (Neo4j, Speckle, Grasshopper, Rhino, Revit, DeGram, Pellet, HermiT, Rule_Id, IRI, SWRL, layer names) stay untranslated. `STATUS`/`role` words from the server (`viewer/editor/owner`, `active/stale`) are mapped through keys, never shown raw in RU.
- **Server messages:** `describeError(err)`: `error.<code>` key → RU, else server `error` text. Seed list of codes to cover at minimum: `AUTH_FAILED`, `INVITE_INVALID`, `PASSWORD_POLICY`, `REGISTRATION_INVALID`, `PROJECT_NAME_UNAVAILABLE`, `PROJECT_FORBIDDEN`, `LAST_OWNER`, `MEMBER_NOT_FOUND`, `ROLE_INVALID`, `ADMIN_REQUIRED`, `CONNECTOR_ACCESS_REQUIRED`, `ACCESS_EXISTS`, `NOT_A_MEMBER`, `DEGRAM_POLICY_INVALID`, `CONNECTOR_TOKENS_RETIRED`.
- **API docs:** translate chrome only (A4).
- **Testability (key coverage):** `ui-v2/tests/i18n.test.mjs` (pure Node, imports `src/i18n/*.js`): (a) every literal `t()/tc()/plural` key found by a regex scan of `src/**/*.{js,jsx}` (excluding `specimen/`, `apidocs/content/`) exists in `ru.js`; (b) no unused `ru.js` keys; (c) `{placeholders}` identical EN vs RU; (d) first argument must be a literal; (e) owner-fixed translations asserted verbatim; (f) `resolveLang` order; (g) `KEPT_KEYS` contains `dgv2_lang`; (h) heuristic scan for raw JSX text nodes with an allowlist file for proper nouns (MEDIUM confidence, keep as a warning-level count that cannot grow). Add `"test": "node --test tests/*.test.mjs"` to `ui-v2/package.json`.

### 5. D-37 export policy
**Recommendation:** no server change. **Where it lives:** `data-service/degram_policy.py` (`policy_for_project`, `set_policy`, `_DEFAULT = {providerExportAllowed: True, wholeDefinitionAllowed: False}`, store `degram-policy.json`); routes `GET|PUT /projects/{project}/degram-policy` (`app.py:4766-4793`), policy `_p(_ADM)` with no project source (`route_policy.py:183-184`); PUT merges only the flags sent, 422 `DEGRAM_POLICY_INVALID` when none, `StrictBool` bodies. **UI placement:** a «Project settings» `Panel` on `ProjectsScreen`, below the Members panel, rendered only when `project && user?.isAdmin` (owners who are not admins do not see it). Two toggles with one-line explanations; enabling `wholeDefinitionAllowed` asks a confirm (it still needs a per-request consent in the relay); PUT sends only the flag that changed; a 403 `ADMIN_REQUIRED` shows the mapped message and reloads. New `lib/projectSettingsApi.js` (`getDegramPolicy`, `setDegramPolicy`) + a case in `api-security.test.mjs`-style API tests. **Rationale:** the contract already makes this admin-only; UI visibility is convenience, the route is the control.

### 6. D-36 role change
**Recommendation:** `PUT /projects/{project}/members/{username}` body `{role: viewer|editor|owner}` (Pattern 2); policy `_p(_MEM, source="path", role="owner")` (owner or admin; cookie + CSRF); answers `{project, username, role}`. **Last-owner protection:** 409 `LAST_OWNER` when the target is the only owner and the new role is not owner (covers self-demotion); done under `auth._STORE_LOCK`. Also add the row to the `route-policy` block (`PUT|/projects/{project}/members/{username}|member|path|owner`). Side effects: none to revoke — delegated and connector sessions re-check the stored role live; a demoted editor/owner loses the connector exemption at the next request. **UI:** in the Members panel replace the static role `Badge` with a `Select` (Viewer/Editor/Owner; labels via `t()`), calling the route on change with optimistic rollback on error; disable the control for the sole owner with a tooltip; the `panelScope` guard already in the dirty tree must be committed first (Pitfall 9). **Rationale:** a dedicated route is explicit and auditable; the invite path stays for adding members.

### 7. D-32 image
**Recommendation:** **no blocking work.** Verified this session: the running container holds `HEAD` content for `degram_policy.py` (D-32 default, commit `680fb25`), `app.py`, `auth.py`, `route_policy.py`, `connectors.py`, `connector_access.py` (hash comparison ignoring CRLF); `cypher_allowlist.py` and `dg_context.py` differ from the working tree, i.e. the unrelated WIP is **not** in the image. First task of the rollout plan: re-run that comparison and tick D-32 closed. For the 1308 rebuild: export committed code only (`git archive HEAD` into a temp context, the recipe used for 0.1.11 per `1301-UAT.md`), `docker compose build --no-cache data-service design-grammars`, then `up -d`, behind a `checkpoint:human-verify` (live restart; JSON stores are single-process). The WIP (8 modified + 2 untracked data-service files) is settled or stashed by the owner separately; 1308 commits stage by explicit path. **Rationale:** the seed's concern is moot; the only residual risk is accidentally baking WIP into the new image.

### 8. UAT account/project cleanup
**Recommendation:** include as the **last task of the rollout plan**, behind a `checkpoint:human-verify` (destructive on the live auth store). No delete-user/delete-project route or tool exists (grep), and none should be added for one cleanup. Use a one-off script run via `docker exec` with `MSYS_NO_PATHCONV=1`, built on `auth._STORE_LOCK`/`auth._load/_save` (pattern: `rotate_llm_master_secret.py`), **dry-run default**, printing counts only: remove user row `uat-pw-bd30ce@dg.local`, its membership rows, its sessions, any delegated/connector sessions and grants/requests, and its retired pairing row; confirm project `uat-pw-bd30ce` has no members left and 0 Neo4j nodes (already read-only verified). Run the same script's "retire all `dgc_` credentials" step. Backup `data-service/data/*.json` first. **Rationale:** same maintenance window as the D-49 token retirement; one reviewed script instead of manual JSON edits.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node / npm | `ui-v2` tests/build | ✓ | 20.20.0 / 10.8.2 | — |
| Python + pytest + fastapi (host) | data-service tests | ✓ | 3.14.2 / pytest 9.x | in-container `python -m pytest` (83 test files in image) |
| Docker | rebuild, `docker exec` | ✓ | 29.1.3; 15 containers up | — |
| .NET SDK | `DG.Tests` | ✓ | 10.0.301 | Do not build casually: tracked `bin/obj` get dirty |
| Neo4j / data-service containers | live checks | ✓ | up 3 h | — |
| vitest in fork | sidebar tests | ✓ | 4.1.10 (node_modules present) | — |
| Chrome/Edge (headless) | `ui-v2/tests/run-*.mjs` browser harnesses | ✓ (path probed by the runners) | — | node-only tests |
| Rhino/Grasshopper | live add-in check | ✗ not probed (owner PC) | — | `DG.Tests` stub-handler tests; owner live run |

**Missing dependencies with no fallback:** none for planning/execution; the live Grasshopper sign-in check requires the owner's Rhino session.
**Missing dependencies with fallback:** Rhino → unit tests + owner UAT.

## Validation Architecture

`workflow.nyquist_validation` is absent in `.planning/config.json`, so this section applies.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (data-service); `node:test` (ui-v2); vitest 4.1.10 (fork); xUnit (`DG.Tests`) |
| Config file | none for ui-v2 (add `test` script); `apps/degram/apps/desktop/vitest.config.ts` |
| Quick run command | `node --test ui-v2/tests/*.test.mjs` (231 pass, 2 s) |
| Full suite command | `python -m pytest data-service/tests -q` (host; in-container baseline 1130 pass + 13 env failures per memory, anything else is a regression) + `node --test ui-v2/tests/*.test.mjs` + `npm --prefix ui-v2 run build` + `dotnet test .\DG\tests\DG.Tests\` (4 Neo4j E2E tests are env-dependent) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEBUI-01 | resolveLang order, badge persists, `dgv2_lang` kept on sign-out, host hides badge | unit | `node --test ui-v2/tests/i18n.test.mjs` | ❌ Wave 0 |
| WEBUI-02 | RU coverage, placeholder parity, owner strings verbatim, `describeError` | unit | `node --test ui-v2/tests/i18n.test.mjs` | ❌ Wave 0 |
| WEBUI-03 | role change, last owner, 404/422, admin allowed, editor refused, CSRF | unit/integration | `python -m pytest data-service/tests/test_member_roles.py -q` | ❌ Wave 0 |
| WEBUI-03 (UI) | member API wrapper and Select wiring | unit | `node --test ui-v2/tests/member-roles-api.test.mjs` | ❌ Wave 0 |
| WEBUI-04 | policy panel only for admin; PUT sends changed flag only | unit + harness | `node --test ui-v2/tests/project-settings-api.test.mjs`; `node ui-v2/tests/run-panel.mjs policy` | ❌ Wave 0 (route tests ✅ `test_degram_policy.py`) |
| WEBUI-05 | summary route counts project-scoped; landing builder; rename | integration + unit | `python -m pytest data-service/tests/test_project_summary.py -q`; `node --test ui-v2/tests/landing-summary.test.mjs` | ❌ Wave 0 |
| WEBUI-06 | host regex accepts `projects`; sidebar row order/label EN+RU; `dgGo` | unit | `node --test ui-v2/tests/host-degram.test.mjs`; `npx vitest run --project ui src/degram/sidebar.test.tsx` (in `apps/degram/apps/desktop`) | host ✅ (extend) / sidebar ✅ (extend) |
| WEBUI-07 | session mint/auth/expiry/revoke cascades; exempt vs grant matrix; 410 on credentials; `dgc_` rejected everywhere; status derivation; Neo4j bundle local only | integration | `python -m pytest data-service/tests/test_connector_session.py data-service/tests/test_connector_access.py data-service/tests/test_connectors.py data-service/tests/test_cross_project_matrix.py data-service/tests/test_designstate_capture.py -q` | session ❌ Wave 0; others ✅ (rewrite) |
| WEBUI-08 | two-step sign-in, cookie handling, refusal on remote http, no password in result/log | unit | `dotnet test .\DG\tests\DG.Tests\ --filter "FullyQualifiedName~ConnectorSessionClient\|FullyQualifiedName~DataServiceRequestAuth\|FullyQualifiedName~ErrorMessageTemplate"` | ❌ Wave 0 (rename/replace `ConnectorHeartbeatClientTests`) |
| WEBUI-09 | no token UI/API calls; editors see request; api-docs content free of `dgc_` | unit + build | `node --test ui-v2/tests/connector-access-api.test.mjs ui-v2/tests/api-security.test.mjs`; `npm --prefix ui-v2 run build` | ✅ (update) |
| WEBUI-10 | spec blocks equal route table; routes classified | integration | `python -m pytest data-service/tests/test_security_boundary_spec.py data-service/tests/test_route_inventory.py -q` | ✅ (update constants) |
| WEBUI-11 | image equals committed code; credentials retired; UAT account gone | live/manual | compare script (`sha256sum` after `tr -d '\r'` as run this session); cleanup script `--dry-run` then real | ❌ Wave 0 (script) |

### Sampling Rate
- **Per task commit:** the single relevant file's quick command above.
- **Per wave merge:** `node --test ui-v2/tests/*.test.mjs` + the data-service files touched + `test_route_inventory.py` + `test_security_boundary_spec.py`.
- **Phase gate:** full suite green (data-service baseline rule), `npm --prefix ui-v2 run build`, `python tools/degram/workspace.py verify`, owner live checks (add-in sign-in, DeGram sidebar in 0.1.12 release).

### Wave 0 Gaps
- [ ] `ui-v2/tests/i18n.test.mjs` — WEBUI-01/02; plus `"test"` script in `ui-v2/package.json`
- [ ] `data-service/tests/test_member_roles.py`, `test_project_summary.py`, `test_connector_session.py` — WEBUI-03/05/07
- [ ] Rewrite `data-service/tests/auth_fixtures.py::connector_token_for()` onto `connector_session.issue` (single seam used by ~12 test files); rewrite `test_connectors.py` (39 token references)
- [ ] `ui-v2/tests/{member-roles-api,project-settings-api,landing-summary}.test.mjs`
- [ ] `DG/tests/DG.Tests/ConnectorSessionClientTests.cs`
- [ ] One-off ops script + its dry-run test fixture (WEBUI-11)
- [ ] Precondition commit/stash of the dirty `ui-v2` and `data-service` working tree (Pitfall 9)

## Security Domain

`security_enforcement` is absent in config, so it is enabled.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Add-in reuses `POST /auth/login` (scrypt, per-user and per-IP throttle); no new password path; refuse remote `http://` sign-in |
| V3 Session Management | yes | `dgk_` token: CSPRNG (`secrets.token_urlsafe(32)`), SHA-256 at rest, 8 h TTL, `Cache-Control: no-store`, revoked on password change/membership/grant/company change, self-revoke route |
| V4 Access Control | yes | Role change owner/admin only + last-owner invariant under lock; export policy admin-only route; connector grant re-checked live per request; deny-by-default `ROUTE_POLICIES` rows for every new route; route inventory tests |
| V5 Input Validation | yes | Pydantic models, `StrictBool`, `auth.ROLES` allowlist, `PROJECT_NAME_PATTERN`, `normalize_username`; client: language allowlist (`en`/`ru`), `Object.hasOwn` dictionary lookup, `encodeURIComponent` on path segments |
| V6 Cryptography | yes | Never hand-roll: reuse `hashlib.sha256` + `secrets` as `delegation.py`; no password logged or returned |
| V7/V8 Logging, Data protection | yes | Tokens/passwords never in logs, results, `.gh` (`NonPersistentStringParam`), `GET /connectors` payloads |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Privilege escalation via role change (self-promote, demote last owner) | Elevation / DoS | Route needs owner/admin; `LAST_OWNER` guard; a plain editor gets 403 `PROJECT_FORBIDDEN` |
| Stale access after demotion or grant revoke | Elevation | Live re-check on every `dgk_` request (no cached decision) |
| Connector session reused across projects | Spoofing | Bound-project equality (existing `_CON` rule) + `CAPTURE_PROJECT_MISMATCH` generic message kept |
| Old `dgc_` tokens still in the store | Spoofing | Resolver no longer accepts the prefix; credentials marked retired; create route 410 |
| Password sniffing over http | Information disclosure | Client refuses remote non-loopback http; deployment guidance in `spec/DEPLOYMENT.md` |
| Credential stuffing through the add-in | Spoofing | Existing login throttle applies (add-in goes through `/auth/login`) |
| CSRF on new unsafe routes | Tampering | `require_principal` enforces `X-DG-CSRF: 1` for cookie principals; `apiFetch` sends it |
| XSS via translated/interpolated text | Tampering | React text nodes only; no `dangerouslySetInnerHTML` (none in tree); never interpolate server HTML |
| `?lang=` injection | Tampering | Allowlist, never reflected into the DOM except as `<html lang>` after validation |
| Cross-tenant count leakage via summary | Information disclosure | Route is `_MEM` path viewer; Cypher filters `n.project = $project`; returns counts only |

**Spec updates required in the same commits (`spec/SECURITY-BOUNDARY.md`):** §3 intro (principal precedence: connector Bearer is `dgk_`), §3.2 rewritten as "Connector sign-in session" (mint, exemption, grant matrix, TTL, revocation, bundle rule), §3.4 error table (`CONNECTOR_AUTH_FAILED` text, `CONNECTOR_TOKENS_RETIRED`, `CONNECTOR_ACCESS_REQUIRED`), §4.1 `public-routes` block (heartbeat row removed) and §4.2 `route-policy` block (new rows: `POST /auth/connector-session`, `DELETE /auth/connector-session`, `PUT /projects/{project}/members/{username}`, `GET /projects/{project}/summary`; changed heartbeat; credentials POST), §5 "Connector-self routes" (only capture remains), §6 resource-bound table (keep `credential` row while DELETE stays), §9 step 11 and rotation text, §10 enforcement table (new tests). Also `spec/API.md`, `spec/GRASSHOPPER.md`, `spec/DEPLOYMENT.md` (`DG_CONNECTOR_SESSION_TTL_SECONDS`), a release-notes entry re-wiring GH canvases (`docs/RELEASE-NOTES-v*.md` pattern), and `DG_OBSIDIAN` decision note update.

## Suggested Plan Slices (for the planner; not locked)

1. **Wave 0:** settle dirty trees; test scaffolding + fixture seam (`connector_token_for`); `ui-v2` `test` script.
2. **Wave 1 (data-service, serialize on `app.py`/`route_policy.py`/spec):** (a) D-36 route + D-36 spec row; (b) summary route; (c) D-49 server (grants exemption, `connector_session.py`, resolver, 410, status, cascades) + test rewrite; (d) spec/doc sync (WEBUI-10). **In parallel (disjoint files):** i18n infrastructure + badge + `describeError` + coverage test (`ui-v2/src/i18n/**`, `lib/auth.js`, `App.jsx`, `LandingLayer.jsx` badge slot).
3. **Wave 2 (ui-v2 features, written with `t()`):** ProjectsScreen (role select + policy panel), landing summaries (+ `runGroups.js`), Connectors screen + HostedConnectorsTable + API docs content; `DG.Core` session client + GH components + release notes (disjoint from ui-v2).
4. **Wave 3:** translation sweep of legacy screens; sidebar plan A (framework) then plan B (component, authorization checkpoint).
5. **Wave 4 (live, all `checkpoint:human-verify`):** D-32 verification, image rebuild from clean export, token retirement + UAT cleanup script, owner live check of add-in sign-in.

## Sources

### Primary (HIGH confidence — read or executed this session)
- `data-service/{connector_access,connectors,route_policy,degram_policy,delegation,auth,auth_routes,degram_grants}.py`, `app.py` lines 1676-1819, 2978-3045, 4624-5120, 5194-5200, 5344-5368
- `data-service/tests/{test_security_boundary_spec,test_route_inventory,auth_fixtures}.py` (structure), local pytest run: 1013 passed (`test_connector_access`, `test_degram_policy`, `test_route_inventory`, `test_security_boundary_spec`)
- `ui-v2/src/{App.jsx,landing/LandingLayer.jsx,landing/landingEngine.js,lib/{auth,apiClient,hostMode,connectorsApi,graphApi,modelApi,llmApi,reasonerApi}.js,screens/{ProjectsScreen,ConnectorsScreen,HostedConnectorsTable}.jsx,screens/ModelScreen.jsx 449-459}`; `node --test ui-v2/tests/*.test.mjs` 231 pass; `npm --prefix ui-v2 run build` ok
- `DG/src/DG.Core/Data/{ConnectorHeartbeatClient,DataServiceRequestAuth,IConnectorHeartbeatClient}.cs`, `DG.Core/Models/{HeartbeatResult,ConnectionInfo}.cs`, `DG.Grasshopper/Components/{Connector,Validator,ComputgraphPublish}Component.cs`, `Params/NonPersistentStringParam.cs`, `tests/DG.Tests/ConnectorHeartbeatClientTests.cs`
- `apps/degram/apps/desktop/{electron/degram/{dg-view,ipc,channels}.ts, src/degram/{sidebar-nav,i18n,sidebar.test}.ts*}`; vitest run 14 pass
- `spec/SECURITY-BOUNDARY.md` (full), `1301-CONTEXT.md` (D-32..D-49), `1301-UAT.md` § 0.1.11 / R-2, `1301-D38-GLOSSARY.md`, `1308-SEED.md`, `.planning/ROADMAP.md` Phase 1308
- Live read-only checks: container-vs-HEAD hashes, credential/user/membership counts, Neo4j summary counts, `Intl.PluralRules('ru')`

### Secondary (MEDIUM)
- Memory notes (in-container pytest baseline 1130 + 13; `git archive HEAD` rebuild recipe; Windows/MSYS pitfalls)

### Tertiary (LOW)
- Heuristic string-volume estimate (A3); `i18next` comparison not evaluated (A7)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every tool run this session
- Architecture (D-49 session design, routes, specs): HIGH for codebase fit; MEDIUM for numeric values (A1, A2)
- Pitfalls: HIGH — each tied to a read line or a ran test
- i18n sizing: LOW-MEDIUM (A3)

**Research date:** 2026-10-12
**Valid until:** 2026-10-26 (fast-moving: active 1301 gap rounds and uncommitted WIP in `data-service/` and `ui-v2/` can change the baseline; re-run the container-vs-HEAD comparison and `git status` at plan time)
