---
phase: 1308-dg-web-ui
verified: 2026-10-14T12:00:00Z
status: passed
score: 191/191 plan truths verified (11 via recorded owner overrides); 11/11 WEBUI requirements satisfied
behavior_unverified: 0
overrides_applied: 11
overrides:
  - must_have: "1308-05 D-50/D-08: ui-v2 renders no language control on any screen (no EN|RU element, nothing next to the theme toggle)"
    reason: "Owner UAT amendment: a global Русский/English dropdown is shown upper-right only in a plain browser, never inside DeGram (CONTEXT D-08 'UAT amendment', D-53 'redirected by owner during UAT', UI-SPEC §1b). Implemented at ui-v2/src/App.jsx:262-267 behind !isDegramHost(); UAT F3 (no control in DeGram) and C pass."
    accepted_by: "owner (recorded in 1308-CONTEXT.md D-08/D-53, commit adc602b)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 D-07/D-11: ui-v2 stores no language (no dgv2_lang key, no KEPT_KEYS change); lib/auth.js not touched"
    reason: "Same amendment (CONTEXT D-07 'UAT amendment'): a validated dgv2_lang browser choice persists and survives sign-out via KEPT_KEYS. ui-v2/src/i18n/index.js:44,112-121; ignored inside DeGram (chooseBrowserLang returns when isDegramHost())."
    accepted_by: "owner (1308-CONTEXT.md D-07)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 D-07 resolution order: host signal, ?lang=, then navigator.languages, then en (and the matching EDGE ordering truth)"
    reason: "Amended order inserts the stored browser choice before navigator.languages outside DeGram only; host precedence unchanged (resolveLang, ui-v2/src/i18n/index.js:79-84; browser-language.test.mjs)."
    accepted_by: "owner (1308-CONTEXT.md D-07)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 D-53: in a plain browser outside DeGram there is no language control and the UI follows the browser language"
    reason: "Redirected by the owner during UAT (CONTEXT D-53): plain browser has its own dropdown; browser language is the fallback."
    accepted_by: "owner (1308-CONTEXT.md D-53)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 UI populated: ui-v2 in a plain browser renders no control; no storage is involved"
    reason: "Superseded by the same D-07/D-08/D-53 amendment; UI-SPEC row 'populated' rewritten accordingly."
    accepted_by: "owner (1308-UI-SPEC.md §1b, row 384)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 D-03: dict/core.js holds owner-fixed RU strings «Грамматика.», «Граф правил проекта.», «Система инициализирована» verbatim"
    reason: "Owner SVOD rebrand (commit 28fa6f6, decision note 'SVOD name, ALNST and Tektur design system, drawn landing hero'): OWNER_FIXED now 'Encode Design Grammars' -> «Свод правил проекта» and «Система инициализирована» (ui-v2/src/i18n/index.js:37-40). 1308-19 truth already expects «Свод правил проекта» in the served bundle."
    accepted_by: "owner (commit 28fa6f6 decision note)"
    accepted_at: "2026-10-13"
  - must_have: "1308-23 D-03: with RU resolved the landing hero reads «Грамматика.», «Граф правил проекта.» and «Система инициализирована»"
    reason: "Same SVOD rebrand; served bundle verified to contain «Свод правил проекта» and no «Грамматика.» (1308-ROLLOUT.md, 1308-19-SUMMARY)."
    accepted_by: "owner (commit 28fa6f6 decision note)"
    accepted_at: "2026-10-13"
  - must_have: "1308-23 D-08/D-50: the landing renders no language control (nothing added top-right or next to the theme toggle)"
    reason: "Landing itself adds no control; the plain-browser global dropdown floats above all layers per the D-08 amendment (UI-SPEC landing row)."
    accepted_by: "owner (1308-CONTEXT.md D-08)"
    accepted_at: "2026-10-13"
  - must_have: "1308-05 prohibition: MUST NOT add any language control, language storage key or second language source to ui-v2"
    reason: "Superseded by the D-07/D-08/D-53 amendment for the plain browser only; inside DeGram there is still no control and no second source (UAT F3 pass)."
    accepted_by: "owner (1308-CONTEXT.md D-07/D-08/D-53)"
    accepted_at: "2026-10-13"
  - must_have: "1308-21 D-54: ru-catalog-completeness.test.ts proves the RU catalog is complete for every degram surface"
    reason: "The committed test fails 1/66 (first failure settings.plugins.installModal.repoPlaceholder, 1308-21-SUMMARY:33). Owner explicitly replaced it as acceptance criterion with in-app review; UAT F6 'D-54 in-app translation review' passed."
    accepted_by: "owner (1308-UAT.md test 6, 1308-21-SUMMARY:25)"
    accepted_at: "2026-10-13"
  - must_have: "1308-18: the gitlink bump is committed alone (only apps/degram staged) after the fork push"
    reason: "The bump 7edf519c -> c476c236 landed in session commit adc602b together with 17 other files. Substantive invariants hold: ls-remote origin degram/phase-1308 = c476c236 = child HEAD = git ls-tree HEAD apps/degram; workspace.py verify exit 0. A fix would require rewriting history."
    accepted_by: "owner (verify-work decision, 2026-10-14)"
    accepted_at: "2026-10-14"
human_verification_resolved:
  - item: "1308-18 commit-shape deviation"
    resolution: "Owner accepted as override (2026-10-14)."
  - item: "REQUIREMENTS.md WEBUI-01 wording"
    resolution: "Owner chose to update the text (2026-10-14): DeGram — Settings → Appearance → Language; plain browser outside DeGram — own Русский/English dropdown upper right, choice persisted, browser language as default; no control inside the embedded DG page. WEBUI-01..11 ticked and ROADMAP plan list closed in the phase-close commit."
---

# Phase 1308: DG Web UI Verification Report

**Phase Goal:** администратор и участники проекта работают с DG Web UI на выбранном языке (EN/RU), админ управляет политикой экспорта проекта, владелец меняет роли участников, а главный экран показывает сводные данные модулей.
**Verified:** 2026-10-14
**Status:** passed (two owner decisions resolved 2026-10-14; no code gaps)
**Re-verification:** No (initial verification)

## Method

- Read all 24 PLAN frontmatters (191 truths, 29 prohibitions, artifacts, key_links), ROADMAP §Phase 1308, REQUIREMENTS WEBUI-01..11, CONTEXT, UI-SPEC, UAT, ROLLOUT.
- Code checked at HEAD `99c2801`; none of the 1308 source files is modified in the working tree (remaining WIP is unrelated v12/owner work: cypher_allowlist.py, dg_context.py, recognition_eval, spec DATABASE/EVIDENCE/SWRL-SUBSET).
- Tests run by the verifier:
  - `node --test ui-v2/tests/*.test.mjs` (14 files): **286 pass, 0 fail**.
  - Host `python -m pytest` over 16 1308 files (test_member_roles, test_project_summary, test_connector_session, test_connector_session_routes, test_d49_store_cleanup, test_connector_access, test_connectors, test_route_inventory, test_security_boundary_spec, test_cross_project_matrix, test_deployment_profile, test_auth_store, test_degram_pairing, test_degram_policy, test_auth_tracer, test_review_fix_1205): **2723 passed, 1 skipped, 0 failed**.
  - `python tools/degram/workspace.py verify`: exit 0; gitlinkCommit = componentHead = `c476c236…`.
  - `git -C apps/degram ls-remote origin degram/phase-1308` → `c476c236ad04be8aa28f42410ed20f2e1372858e` (on the fork).
  - Read-only live: `docker inspect` data-service `sha256:c1e018ee…`, design-grammars `sha256:3b790ebb…`; `/app/app.py` holds 5 × `auth/connector-session`; `git rev-parse HEAD:data-service HEAD:ui-v2` = `b787ca84…` / `9b2c05e4…` = the trees recorded in 1308-ROLLOUT.md as the build source, so the running images still equal HEAD code.
- Not run: `dotnet test` (DG/src/*/bin and obj are tracked and would be rewritten). C# truths are verified statically plus owner UAT E (plugin rebuilt, Rhino 8, live sign-in and publish).

## Requirements Coverage

| Req | Plans | Status | Evidence |
|-----|-------|--------|----------|
| WEBUI-01 | 05, 18, 21, 22, 23 | SATISFIED (override on plain-browser wording) | DeGram LanguageSwitcher two options (component `language-switcher.test.tsx:91`), `dg-view.ts:34` HOST_LANG_FRAGMENT and `:412` live `#degram-lang` load; `ui-v2/src/lib/hostMode.js:32` parse; `App.jsx:83` `setLang(signal.lang)`; plain-browser Select `App.jsx:262-267` (amended D-08/D-53). UAT F1-F3, C pass. **Requirement text at REQUIREMENTS.md:103 still says no switcher in the plain browser.** |
| WEBUI-02 | 05, 10, 12, 14, 15, 16, 21, 22, 23 | SATISFIED | i18n core `src/i18n/index.js` (t/tc/tp/describeError/formatDate/formatTime, Intl.PluralRules); 8 dict modules; 8 `tests/i18n-swept/*.json` manifests; `i18n.test.mjs:574` "every source file is covered by exactly one manifest", `:621` raw-text guard, `:593` font fallback — all pass; no `toLocale*` in `ui-v2/src`. UAT C, F6 pass. |
| WEBUI-03 | 01, 02, 10 | SATISFIED | `data-service/app.py:5137-5167` change_project_member_role (ROLE_INVALID 422, MEMBER_NOT_FOUND 404, `_last_owner_guard` 409 LAST_OWNER under `auth._STORE_LOCK`); `route_policy.py:146` owner row; `ProjectsScreen.jsx:76,93,114` role Select via `memberApi.changeMemberRole`; test_member_roles.py pass; UAT D. |
| WEBUI-04 | 10 | SATISFIED | `projectSettingsApi.js:36` `shouldShowProjectSettings` = `user.isAdmin === true`; `ProjectsScreen.jsx:654`; whole-definition confirm `:305-315`; admin-only route (test_degram_policy.py pass); UAT D. |
| WEBUI-05 | 02, 11, 16, 23 | SATISFIED | `app.py:4718` PROJECT_SUMMARY_QUERY (single CASE, Metagraph rules, `$project`), `:5076` counts-only answer; `LandingLayer.jsx:86,98` load + `buildLandingSummaries`; `landingSummary.js` Graph/Model/LLM/Reasoner/Connectors lines; `LandingLayer.jsx:416` `t("LLM model")`; no "AI Engine" UI text in `ui-v2/src`. UAT C. |
| WEBUI-06 | 17, 18 | SATISFIED | `apps/degram/apps/desktop/src/degram/sidebar-nav.ts:29,54` `dg-projects` after `models`, before `dg-menu`; `dg-view.ts:33` `projects` in HOST_GO_FRAGMENT; `hostMode.js:28`; component commits `5f1d3aa8`, `c476c236` on the fork; UAT F4. |
| WEBUI-07 | 03, 06, 09, 13, 15, 24 | SATISFIED | `connector_session.py` (dgk_, 28800 TTL, hash-only store, live re-check `:219` `is_authorized`, `status_for`, revoke_*); `connector_access.py:223-233` is_exempt/is_authorized; `app.py:1729-1745` credentials POST → 410; `auth.py:471` dgk_ resolver; `connectors.py:233-243` status from sessions; cascades `app.py:5166,5198,5246,5293`. Tests pass; UAT D, E. |
| WEBUI-08 | 04, 07, 20 | SATISFIED | `ConnectorSessionClient.cs` login → connector-session → logout with X-DG-CSRF, InsecureTransport refusal; `ConnectorComponent.cs:47` GUID EF2E6F2A…, Username/Password NonPersistentStringParam, Session output; `DataServiceRequestAuth.cs:23` `dgk_`; no `dgc_` and no ConnectorHeartbeatClient in DG/src; VALIDATOR/COMPUTGRAPH PUBLISH Token → CONNECTOR.Session. UAT E pass. |
| WEBUI-09 | 15, 16 | SATISFIED | No `/credentials` call or `dgc_` in `ui-v2/src` (only the 410 warning note in apidocs 03); `ConnectorsScreen.jsx:49` GrantToMemberForm, `:113-116` On/Off + sign-in caption, `:208` issueConnectorAccess; `HostedConnectorsTable.jsx:132` caption, no token button; apidocs 02/03/07 describe POST /auth/connector-session. UAT D, F5. |
| WEBUI-10 | 02, 06, 09, 13, 24 | SATISFIED | `spec/SECURITY-BOUNDARY.md:68-75` (§3.2 session), `:96-115` error rows, `:187-188,213-214,268-270` policy block rows, `:364` §6 retired route; `spec/API.md:508-536`; `spec/DEPLOYMENT.md:45` TTL; `spec/GRASSHOPPER.md:99-103`; `docs/RELEASE-NOTES-v13.0.md:3-21`; test_route_inventory.py and test_security_boundary_spec.py pass. |
| WEBUI-11 | 08, 19, 20 | SATISFIED | `d49_store_cleanup.py` (dry-run default, `--apply`, `_STORE_LOCK`, hard-coded UAT targets); 1308-ROLLOUT.md: D-32 closed, `git archive HEAD` export build, running ids equal, probes 401, in-container suite environmental-only, verified backup with sha256, dry run → owner-run apply (data-service stopped) → `nothing-to-do`; Neo4j count 0. UAT A, B pass; live image ids re-confirmed read-only. |

No orphaned WEBUI IDs: every WEBUI-01..11 is claimed by at least one plan.

## Per-plan Must-have Results

| Plan | Truths | Result | Key evidence / exceptions |
|------|--------|--------|---------------------------|
| 01 owner-WIP settlement | 3 | 3/3 VERIFIED | Named paths (ProjectsScreen.jsx, auth.js, api-security.test.mjs, ValidatorComponent.cs, test_auth_store.py) clean at HEAD; later plans edited them. |
| 02 member role + summary routes | 10 | 10/10 | app.py:4718, 5076-5095, 5125-5167; route_policy.py:146-147; spec rows 268-270, 113-115; tests pass. |
| 03 connector_session store | 7 | 7/7 | connector_session.py 381 lines (≥180): `dgk_`, 28800 + env override, expiry `current >= expires_at` (:206), `%Y-%m-%dT%H:%M:%SZ` (:330), status_for, revoke_*; key link `is_authorized(` at :219, :298. |
| 04 DG.Core ConnectorSessionClient | 7 | 7/7 (static + UAT E) | ConnectorSessionClient.cs:24,53,65,98,146,305; ConnectorSessionResult redacted ToString (:59-61); PublishTokenRejected text (ErrorMessageTemplates.cs:272-275). |
| 05 i18n core | 17 | 10 VERIFIED + 7 PASSED (override) | Overridden: no-control (D-50/D-08), D-03 strings, D-07 order, D-07/D-11 storage, D-53, EDGE ordering, UI populated. Remaining verified: host signal `#degram-lang`, html[lang], describeError + errors.js codes, PROPER_NOUNS, no new dependency, i18n.test gate. |
| 06 connector-session routes | 10 | 10/10 | app.py:1820-1900 mint/revoke, `_neo4j_bundle_or_none` :1768; auth.py:471 `connector_session.authenticate`; spec rows 187-188; DEPLOYMENT.md:45. |
| 07 GH CONNECTOR | 7 | 7/7 (static + UAT E) | ConnectorComponent.cs:47,58-80,186,195,285; heartbeat client/templates removed; GRASSHOPPER.md + RELEASE-NOTES-v13.0.md. |
| 08 d49_store_cleanup | 8 | 8/8 | Script + test_d49_store_cleanup.py pass; live run in ROLLOUT. |
| 09 exemption + 410 | 6 | 6/6 | connector_access.py:223-291; connectors.py:52-62 `tokens_retired`; app.py:1745 `raise connectors.tokens_retired(` (key link). |
| 10 Projects role Select + settings | 14 | 14/14 | ProjectsScreen.jsx:5-7,66-114,223-335,592,654; memberApi/projectSettingsApi/memberRoles exports; member-roles-api/project-settings-api tests pass; UAT D. |
| 11 landing summaries | 14 | 14/14 (2 backstops via UAT C) | landingSummary.js, runGroups.js, summaryApi.js; ModelScreen.jsx:465 `groupRunsByState`; landing-summary.test.mjs pass. |
| 12 Graph translation | 4 | 4/4 | GraphScreen.jsx:22 imports, :215 `useT()`, :1519 `formatTime`; graph.json manifest; guard passes. |
| 13 legacy-token refusal, heartbeat on sessions | 6 | 6/6 | app.py:1788-1800 heartbeat `connector_session.touch(`; capture :3064-3108 via resolver; spec §4.1/§4.2 rows; seed_legacy_credential fixture; tests pass. |
| 14 Model translation | 4 | 4/4 | model.json manifest (15 lines); ModelScreen keeps runGroups. |
| 15 Connectors screen | 14 | 14/14 | ConnectorsScreen.jsx:39 `tp`, :49, :113-116, :208; HostedConnectorsTable.jsx:31,66,86,132; apidocs content; UAT D, F5. |
| 16 Reasoner/LLM model/API docs | 6 | 6/6 | AiEngineScreen.jsx:170 `t("Region · LLM model")`; screens.json manifest; no toLocale*. |
| 17 DeGram sidebar Projects | 8 | 8/8 | sidebar-nav.ts:29,38,54; dg-view.ts:26,30,33; hostMode.js:28; host-degram.test.mjs:53; waiver closed by 18. |
| 18 fork push + gitlink | 4 | 3 VERIFIED + 1 UNCERTAIN | ls-remote = child HEAD = gitlink = `c476c236`; verify exit 0. **UNCERTAIN:** "framework commit stages only the apps/degram gitlink" — gitlink moved inside mixed session commit `adc602b` (18 files). Owner decision requested. |
| 19 D-32 + rebuild | 5 | 5/5 | 1308-ROLLOUT.md; image ids and tree hashes re-confirmed read-only. |
| 20 cleanup rollout | 8 | 8/8 (2 backstops via UAT C, E) | ROLLOUT backup/sha256, dry run, owner apply with service stopped, nothing-to-do, Neo4j 0, D-48 owner actions listed. |
| 21 DeGram single language setting | 11 | 10 VERIFIED + 1 PASSED (override) | dg-view.ts:34,385,412; LanguageSwitcher degram variant test; component commit c476c236 on fork. Override: D-54 completeness test fails 1/66, replaced by UAT F6. Note: a separately authorized unpacked (non-installer, not launched) build is recorded in 1308-21-SUMMARY:38 / 1301-BUILD.md. |
| 22 shell translation + gate | 7 | 7/7 (font backstop via UAT C) | shell.json manifest; i18n.test.mjs:574, :593; no "AI Engine" UI text; no toLocale*. |
| 23 landing translated | 6 | 4 VERIFIED + 2 PASSED (override) | LandingLayer.jsx:416; landingEngine.js:189/197 add/remove `dg-lang`; core.json manifest. Overrides: D-03 hero strings (SVOD), D-08/D-50 no control. |
| 24 session-based status, cascades | 5 | 5/5 | connectors.py:233-243 `status_for(`; legacy helpers gone (only load/save/revoke_credential remain); app.py `revoke_unauthorized(` at :5166, :5198, :5246, :5293; DSAV live tests use DSAV_USERNAME/PASSWORD + /auth/connector-session. |

**Total:** 191 truths: 180 VERIFIED, 11 PASSED (override; 1308-18 commit shape accepted by the owner 2026-10-14).

## Prohibitions (29)

- Test-tier style safety/privacy prohibitions (02, 03, 04, 06, 08, 09, 13, 15, 24): each names a test that asserts it; the named test files pass in the verifier's run (pytest 2723 passed; node 286 passed). C# prohibitions (04, 07) rely on ConnectorSessionClientTests (not re-run) plus source review: password only in the login body, token redacted in ToString, InsecureTransport refusal before any request.
- Transparency prohibitions (05#2, 12, 14, 16, 22, 23 — no translation of data/proper nouns): judgment items, resolved by owner UAT C (RU visual pass) and F6.
- Process prohibitions (01, 17, 18, 19, 20, 21 — no push by agent, no Desktop launch, backup before write, no uncommitted code in images): recorded in SUMMARYs/ROLLOUT; push done by the owner; export-only build confirmed by tree hashes; backup verified before apply.
- 1308-05#1 (no language control/storage): superseded by the owner amendment (override above).

No prohibition is left unresolved.

## Key Link Verification

| From | To | Status |
|------|----|--------|
| route_policy.py PUT members row | app.py change_project_member_role | WIRED (:146 / :5137) |
| app.py get_project_summary | Neo4j `n.project = $project` | WIRED (:4719, :5082) |
| connector_session.authenticate | connector_access.is_authorized | WIRED (:219) |
| ConnectorSessionClient | POST /auth/connector-session + X-DG-CSRF | WIRED |
| App.jsx host signal | i18n setLang; LanguageProvider wraps root | WIRED (:83, :46) |
| auth.resolve_connector_principal | connector_session.authenticate | WIRED (auth.py:471) |
| app.py mint | connector_access.is_authorized | WIRED (:1842, :1874) |
| ConnectorComponent | SignInAsync / SignOutAsync | WIRED (:186, :195, :285) |
| d49_store_cleanup | auth._STORE_LOCK | WIRED |
| create_connector_credential | connectors.tokens_retired | WIRED (:1745) |
| ProjectsScreen | changeMemberRole / setDegramPolicy | WIRED (:76, :261) |
| ModelScreen / LandingLayer | runGroups / landingSummary | WIRED (:465 / :98) |
| GraphScreen | useT | WIRED (:215) |
| connector_heartbeat | connector_session.touch | WIRED (:1799) |
| ConnectorsScreen | issueConnectorAccess, active_sessions | WIRED (:208, :114) |
| AiEngineScreen | "LLM model" | WIRED (:170) |
| dg-view.ts HOST_GO/HOST_LANG | hostMode.parseHostSignal | WIRED (same closed vocabulary both sides) |
| framework gitlink | origin degram/phase-1308 | WIRED (ls-remote equality) |
| git archive HEAD export | running containers | WIRED (image ids + tree hashes) |
| d49 --apply | data/*.json via compose run --rm --no-deps | WIRED (ROLLOUT owner-run apply) |
| i18n.test.mjs | tests/i18n-swept/*.json | WIRED |
| landingEngine | dg-lang | WIRED (:189/:197) |
| connectors.get_connector_overview | connector_session.status_for | WIRED (:233) |
| invite paths / role change | connector_session.revoke_unauthorized | WIRED |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ui-v2 i18n gate, landing summary, role/settings API, host signals | `node --test ui-v2/tests/*.test.mjs` | 286 pass / 0 fail | PASS |
| Role change, last-owner guard, summary, sessions, cascades, 410, route inventory/spec parity, cleanup script | host pytest over 16 files | 2723 passed, 1 skipped | PASS |
| Workspace pair | `python tools/degram/workspace.py verify` | exit 0 | PASS |
| Fork holds the pinned commit | `git -C apps/degram ls-remote origin degram/phase-1308` | c476c236… | PASS |
| Live stack = HEAD code | `docker inspect` + `git rev-parse HEAD:data-service HEAD:ui-v2` | c1e018ee / 3b790ebb; trees b787ca84 / 9b2c05e4 | PASS |

## Probe Execution

No `scripts/*/tests/probe-*.sh` is declared by the 1308 plans. The rollout HTTP probes (401 AUTH_REQUIRED on the three new routes) are recorded in 1308-ROLLOUT.md; not re-run (read-only constraint satisfied by the image-id and in-container grep check).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (103 non-build files touched by 1308 commits) | — | TBD / FIXME / XXX | none found | — |
| apps/degram/apps/desktop/src/degram/ru-catalog-completeness.test.ts | — | committed failing test (1 failed / 65 passed per 1308-21-SUMMARY:33) | WARNING | Owner-accepted (UAT F6), but leaves a red test in the component suite at c476c236 |

## Warnings (non-blocking)

1. **REQUIREMENTS.md:103 (WEBUI-01) contradicts the implemented and owner-amended behavior.** The text says DG Web UI has no switcher of its own and follows the browser language outside DeGram. `ui-v2/src/App.jsx:262-267` renders a global language Select outside DeGram, and `ui-v2/src/i18n/index.js:44,112-121` persists `dgv2_lang`. That behavior matches CONTEXT D-07/D-08/D-53 (UAT amendment), so the requirement text is stale. Owner decision 2 above.
2. **Planning bookkeeping is stale.** In ROADMAP.md:459, "Plans: 17/24 plans executed" and plans 15, 22, 17, 19, 21, 18 and 20 are unchecked (:497-518). WEBUI-01, 02, 06, 07, 09 and 11 are unchecked in REQUIREMENTS.md. Close these at phase completion. The git index already holds another session's staged edits to both files.
3. **CONTEXT D-03 (1308-CONTEXT.md:23) and UI-SPEC copy rows still list «Грамматика.» / «Граф правил проекта.».** The code uses the SVOD strings. This is documentation drift only. **Resolved 2026-10-14:** CONTEXT D-03 and the UI-SPEC rows now carry SVOD / «Свод правил проекта» and the ALNST/Tektur faces; PLAN, SUMMARY and RESEARCH files keep the original strings as historical records.
4. **1308-18 commit shape.** See owner decision 1.
5. **DG.Tests not re-run by the verifier**, because tracked bin/obj would be rewritten. WEBUI-08 rests on a static review plus owner UAT E.

## Human Verification Required — resolved 2026-10-14

Both items below were decided by the owner during `/gsd-verify-work 1308`: (1) override accepted; (2) WEBUI-01 text updated and bookkeeping closed.


### 1. Accept the 1308-18 commit-shape deviation

**Test:** Review commit `adc602b`. It moves the gitlink `7edf519c` → `c476c236` together with 17 other files.
**Expected:** The owner records an override. The substantive invariants already hold: the object is on the fork, the gitlink equals the child HEAD, and verify is green.
**Why human:** The truth fails as written, and the only fix would be a history rewrite.

### 2. Amend WEBUI-01 wording and close the bookkeeping

**Test:** Update REQUIREMENTS.md:103 to match D-07/D-08/D-53, then tick the WEBUI and ROADMAP plan boxes.
**Expected:** The requirement text matches the shipped plain-browser dropdown and says DeGram has no in-page control.
**Why human:** Changing the requirement contract is an owner decision.

## Gaps Summary

No code or behavior gaps. All 11 WEBUI requirements have codebase evidence. The 1308 test files pass on host: node 286/286 and pytest 2723 passed. The live stack runs images built from the current HEAD trees, and owner UAT groups A to F pass.

The deviations from the plan text are of two kinds:
- **Already recorded owner decisions, applied as overrides:** the plain-browser language dropdown, the SVOD rebrand of the owner-fixed strings, and the D-54 completeness test replaced by in-app review.
- **One process deviation needing an owner override:** the gitlink bump landed in a mixed commit.

Both owner decisions were made on 2026-10-14 (override accepted; WEBUI-01 text updated), so the status is `passed`.

---

_Verified: 2026-10-14_
_Verifier: Claude (gsd-verifier)_
