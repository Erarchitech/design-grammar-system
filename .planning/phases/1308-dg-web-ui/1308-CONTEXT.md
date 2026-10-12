# Phase 1308: DG Web UI — Context

**Gathered:** 2026-10-12
**Status:** Ready for planning
**Scope:** WEBUI-01..11 (`.planning/REQUIREMENTS.md`, section «DG Web UI»).
**Authority:** owner instruction 2026-10-12: «skip discussing, approve all recommendations». There was no discuss-phase. The decisions below are the owner decisions from `1301-CONTEXT.md` and `1308-SEED.md`, plus every recommendation and assumption in `1308-RESEARCH.md` (`## Open Questions — Recommendations`, `## Assumptions Log`), adopted as locked. D-NN numbering is local to 1308; references to 1301 decisions are written «1301 D-NN».
**Ordering:** the owner chose (2026-10-12) to execute Phase 1308 before Phase 1302.

<domain>
## Phase Boundary

DG admins and project members use the DG Web UI (`ui-v2`) in EN or RU. A DG admin changes a project's export policy. A project owner or admin changes a member's role. The landing screen shows module summaries. Connector access works only by per-connector grant: connector tokens are replaced by a connector sign-in session with the user's own account (server, Web UI, Grasshopper add-in). DeGram's sidebar gets a «Projects» row. The phase ends with a checkpointed live rollout.

Not in scope: Desktop build or launch, `hermes update`, installed-profile writes, package installs, graph schema changes, the DeGram 7-day status rule, translating the API-docs body, a masked password dialog in Grasshopper.
</domain>

<decisions>
## Implementation Decisions

### Owner decisions carried in (not re-discussed)
- **D-01:** Member role change in DG Web UI (1301 D-36): data-service route plus Web UI action; the last owner is never demoted.
- **D-02:** Export policy (`providerExportAllowed`, `wholeDefinitionAllowed`) is visible to and changed by a DG admin only (1301 D-37); a project owner does not see it.
- **D-03:** RU makes the whole interface Russian (DeGram and every DG Web UI screen); owner-fixed strings «Грамматика.», «Граф правил проекта.», «Система инициализирована»; rest per `1301-D38-GLOSSARY.md` (1301 D-38; the start-screen badge is replaced by D-50, owner 2026-10-12).
- **D-04:** Connector access only by per-connector grant, no connector tokens, add-in signs in with the user account, owner and DG admin exempt, editor and viewer need a grant (1301 D-49, amends 1301 D-46).
- **D-05:** D-32 default (export allowed, whole definition off, malformed store fails closed) is already committed; 1308 only verifies the running image and closes D-32.

### i18n (WEBUI-01, WEBUI-02)
- **D-06:** In-house i18n in `ui-v2/src/i18n/` with English text as the key, `LanguageProvider` and `useT()` at the App root, `Intl.PluralRules` for Russian; no new packages.
- **D-07:** Language resolution in `ui-v2`: inside DeGram the host language wins (live `#degram-lang=` signal, else `?lang=` at load); outside DeGram the browser's primary language (`navigator.languages[0]`, else `navigator.language`; starts with `ru` → RU, else EN); no `dgv2_lang` storage and no `KEPT_KEYS` change (amended 2026-10-12 by D-50).
- **D-08:** `ui-v2` renders no language control on any screen (the start-screen «EN | RU» badge is withdrawn by D-50); the resolved language sets `document.documentElement.lang`.
- **D-09:** Server errors are translated by `code` through `describeError(err)` (`error.<CODE>` keys), falling back to server text; at minimum the 15 codes listed in RESEARCH Q4.
- **D-10:** API-docs body content stays English; only its chrome is translated (assumption A4 adopted).
- **D-11:** No server-side language profile; DeGram keeps its choice in its own renderer storage (`degram.display.language`, `locale-config.ts`) (assumption A6 adopted, amended by D-50).
- **D-12:** A pure-Node key-coverage test `ui-v2/tests/i18n.test.mjs` enforces literal keys, no missing or unused RU keys, placeholder parity, owner strings verbatim and the D-07 resolution order (host signal, `?lang=`, browser language); `ui-v2/package.json` gains a `test` script.
- **D-13:** Proper nouns stay Latin in RU (Neo4j, Speckle, Grasshopper, Rhino, Revit, DeGram, Pellet, HermiT, Rule_Id, IRI, SWRL, layer names); server enum words (roles, statuses) are always mapped through keys.

### Member roles and export policy (WEBUI-03, WEBUI-04)
- **D-14:** New route `PUT /projects/{project}/members/{username}` with body `{role: viewer|editor|owner}`, policy member/path/owner (owner or admin, cookie plus CSRF), answers `{project, username, role}`.
- **D-15:** Last-owner protection returns 409 `LAST_OWNER` under `auth._STORE_LOCK`, including self-demotion; no session revocation is needed because delegated and connector sessions re-check the role live.
- **D-16:** Members panel replaces the static role badge with a role `Select` (optimistic update with rollback), disabled for the sole owner with a tooltip.
- **D-17:** Export policy needs no server change; a «Project settings» panel on `ProjectsScreen` below Members, rendered only for `user.isAdmin`, uses the existing `GET|PUT /projects/{project}/degram-policy` via new `lib/projectSettingsApi.js`; turning on `wholeDefinitionAllowed` asks for confirmation; PUT sends only the changed flag.

### Landing summaries (WEBUI-05)
- **D-18:** Graph Viewer and Model Viewer summaries are per current project (shown as «—» without a project); LLM model and Reasoner are system-wide; Connectors use the current project.
- **D-19:** New route `GET /projects/{project}/summary` (member/path/viewer) returns `{project, graph:{classes, properties, rules}, connectors:{grantsIssued}}` with Cypher filtered by `n.project = $project`.
- **D-20:** Model Viewer counts come from existing `GET /validation/runs/{project}`: runs = `runs.length`, Design States = `groupRunsByState(runs).length`, with the grouping extracted from `ModelScreen.jsx` into `lib/runGroups.js` so the numbers match the Model Viewer badge.
- **D-21:** «AI Engine» is renamed «LLM model» / «Модель LLM» (landing label and screen title); its summary is Provider and Model from `GET /llm/settings`.
- **D-22:** Reasoner summary is the selected reasoner name from `GET /reasoner/settings`.
- **D-23:** Connectors summary «Active» lists registry connectors whose status is `active` plus DeGram when its card is active; «Keys issued» is renamed «Grants issued» / «Выдано доступов» (assumption A8 adopted).
- **D-24:** Summaries render as a second line inside the existing `.dgl-region-label`, load once when the landing becomes active for a signed-in user, never poll, and render «—» on any failure without blocking the hero.

### Connector access, D-49 (WEBUI-07, WEBUI-08, WEBUI-09, WEBUI-10)
- **D-25:** The connector sign-in session is a `dgk_` Bearer minted by `POST /auth/connector-session` from a login cookie, in two steps mirroring the DeGram session exchange; `DELETE /auth/connector-session` revokes it.
- **D-26:** The `dgk_` session resolves to the existing `connector` principal kind (with `connector_id`), so `_CON` and connector-self route rows stay; heartbeat and `designstate/capture` use the same resolver; `dgc_` is no longer accepted anywhere.
- **D-27:** Session TTL is 8 hours absolute, no idle timeout, no periodic heartbeat from the add-in, configurable via `DG_CONNECTOR_SESSION_TTL_SECONDS` (assumption A1 adopted).
- **D-28:** Sessions are stored hash-only (SHA-256, `secrets.token_urlsafe(32)`), served with `Cache-Control: no-store`, and the grant and exemption are re-checked live on every request.
- **D-29:** `connector_access.is_exempt(role)` becomes owner-or-admin (`role_satisfies(role, "owner")`), replacing all four editor checks; editor and viewer need an active per-connector row.
- **D-30:** A viewer holding a grant may use the connector's full route scope, including publish, as D-46 allowed (assumption A2 adopted).
- **D-31:** `POST /connectors/{id}/credentials` returns 410 `CONNECTOR_TOKENS_RETIRED`; `DELETE .../credentials/{credential_id}` stays for one release for cleanup.
- **D-32:** Status «Вкл» / `active` means at least one live connector session exists for that connector in the caller's visible projects; `stale` means sessions existed but none is live; `never_connected` means none ever; the DeGram card keeps its 7-day grant rule.
- **D-33:** Sessions are invalidated on password change, membership removal, demotion below exempt without a grant, grant revoke, project company reassignment and user deletion; they are wired next to the existing `delegation.revoke_*` calls.
- **D-34:** The Neo4j bundle is returned only in the `local` deployment profile, as the heartbeat does today.
- **D-35:** `DG.Core/Data/ConnectorSessionClient` (with interface and stub-handler tests) replaces `ConnectorHeartbeatClient`; `DataServiceRequestAuth` accepts `dgk_`; the client refuses sign-in over remote non-loopback `http://`.
- **D-36:** `ConnectorComponent` gets a fresh GUID with non-persistent `Username` and `Password` inputs, optional `Project`, `Connect`, and a new `Session` output; old canvases show a placeholder documented in a release note.
- **D-37:** `ValidatorComponent` and `ComputgraphPublishComponent` keep their GUIDs and port order; their `Token` input is repurposed to take `CONNECTOR.Session`.
- **D-38:** A masked password dialog in Grasshopper is deferred (assumption A9 adopted).
- **D-39:** Web UI `ConnectorsScreen` drops the token panels and the create/revoke credential calls, shows access and live sign-in count, and owner/admin get a «grant to member» form using the existing `POST /projects/{p}/connector-access`.
- **D-40:** DeGram-hosted `HostedConnectorsTable` drops «Создать токен»; API-docs content pages that mention `dgc_` or heartbeat tokens are rewritten around account sign-in.
- **D-41:** `spec/SECURITY-BOUNDARY.md` §3, §3.2, §3.4, §4.1, §4.2, §5, §6, §9 and §10 plus `spec/API.md`, `spec/GRASSHOPPER.md`, `spec/DEPLOYMENT.md` and a release note change in the same commits as the routes they describe; `test_route_inventory.py` and `test_security_boundary_spec.py` must stay green.

### DeGram sidebar «Projects» (WEBUI-06)
- **D-42:** The framework half is a `ui-v2` change: `hostMode.js` `parseHostSignal` accepts `projects`, with a test in `host-degram.test.mjs`; it needs no authorization.
- **D-43:** The component half (`apps/degram/apps/desktop`) adds row `dg-projects` after `models` opening the DG PROJECTS screen, with i18n «Projects» / «Проекты»; it starts with a `checkpoint:human-action` for the child commit, and fork push and gitlink bump each need separate explicit authorization.
- **D-44:** No installer build or Desktop launch in this phase; live acceptance of the sidebar row happens in the next DeGram release under a separate authorization.

### Live rollout (WEBUI-11)
- **D-45:** The first rollout task re-runs the image-vs-HEAD hash comparison and closes D-32.
- **D-46:** Images are rebuilt from committed code only (`git archive HEAD` export), `docker compose build --no-cache data-service design-grammars`, behind `checkpoint:human-verify`.
- **D-47:** A one-off dry-run-by-default ops script (pattern `rotate_llm_master_secret.py`, under `auth._STORE_LOCK`) retires all `dgc_` credentials and removes UAT user `uat-pw-bd30ce@dg.local` with its memberships, sessions, grants and pairing row, after a backup of `data-service/data/*.json`, behind `checkpoint:human-verify`.
- **D-48:** Editor `asiyagerey94@gmail.com` (degram-uat-c) needs connector grants after rollout; the rollout plan lists it as an owner action.

### Owner amendment 2026-10-12 (after planning): one language switch in DeGram
- **D-50:** The interface language of every element and every screen (DeGram and the embedded DG Web UI) is switched in one place only: DeGram Settings → Appearance → Language (`appearance-settings.tsx`, `LanguageSwitcher`) [owner 2026-10-12].
- **D-51:** In the `degram` variant the Language switcher offers only «Русский» (`ru`) and «English» (`en`); other bundled, plugin or backend locales are not listed, and a stored other locale is coerced to English on load [owner 2026-10-12].
- **D-52:** A language change in DeGram reaches the open DG page live, without reload, through a new host signal fragment `#degram-lang=ru|en` (allowlisted in `dg-view.ts` `signal` and `ui-v2` `parseHostSignal`), and `setLocale` keeps `&lang=` for later full loads.
- **D-53:** A DG Web UI opened in a plain browser outside DeGram has no language control and follows the browser language (recommendation adopted under the owner instruction; owner may redirect).
- **D-54:** The `degram` variant RU catalog is complete for every surface DeGram shows (existing `catalog-completeness.test.ts` pattern), so switching to «Русский» leaves no English text in visible DeGram chrome apart from the D-13 proper nouns.

### Working tree hygiene
- **D-49:** Uncommitted v12 offline-repair changes in `ui-v2/src/screens/ProjectsScreen.jsx`, `ui-v2/src/lib/auth.js`, untracked `ui-v2/tests/*`, and the data-service WIP are settled by the owner before tasks that edit those files; 1308 commits stage by explicit path only.

### Claude's Discretion
- Plan split and wave layout, exact file names for new tests, translation wording beyond the glossary and the owner-fixed strings.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/1308-dg-web-ui/1308-SEED.md`
- `.planning/phases/1308-dg-web-ui/1308-RESEARCH.md`
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-CONTEXT.md` (D-32, D-36, D-37, D-38, D-42, D-45, D-46, D-49)
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-D38-GLOSSARY.md`
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md` (R-2)
- `spec/SECURITY-BOUNDARY.md`, `spec/degram/WORKSPACE.md`, `CLAUDE.md` (DeGram boundaries)
</canonical_refs>

<deferred>
## Deferred Ideas

- Aligning DeGram's 7-day status rule with the session-based «Вкл» meaning.
- Removing `DELETE /connectors/{id}/credentials/{credential_id}` (next release).
- Full Russian API-docs body; masked password dialog in Grasshopper.
</deferred>
