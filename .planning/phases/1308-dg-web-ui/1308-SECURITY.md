---
phase: 1308
slug: dg-web-ui
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-10-14
---

# Phase 1308 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| working tree → repository history | uncommitted local edits enter history only by explicit staging (plan 01) | see register |
| browser → data-service | cookie principal with CSRF header crosses into role mutation and summary reads (plan 02) | see register |
| data-service → Neo4j | Cypher with a path-derived project parameter (plan 02) | see register |
| add-in Bearer → data-service | an untrusted `dgk_` string is hashed and looked up (plan 03) | see register |
| session store on disk | JSON under DG_DATA_DIR holds hashes only (plan 03) | see register |
| Rhino/Grasshopper process → data-service | account password and session token cross the network (plan 04) | see register |
| client memory → logs/.gh | secrets must not leave the request path (plan 04) | see register |
| DeGram host (URL query ?lang= and hash #degram-lang=) → page | untrusted input selects the language (plan 05) | see register |
| browser navigator.languages → page | browser-supplied preference (plan 05) | see register |
| server error text → DOM | API `{error, hint, code}` rendered in the UI (plan 05) | see register |
| cookie user → mint route | a browser/add-in session cookie with CSRF header becomes a bearer credential (plan 06) | see register |
| connector Bearer → connector routes | an untrusted dgk_ value selects a principal (plan 06) | see register |
| GH canvas / .gh file → disk | inputs may be serialized with the definition (plan 07) | see register |
| GH runtime messages → screen | text shown to the user and in screenshots (plan 07) | see register |
| operator shell → auth stores | a privileged one-off script rewrites live JSON stores (plan 08) | see register |
| project member → connector access decision | role and grant decide connector scope (plan 09) | see register |
| browser UI → data-service | role and policy mutations with cookie + CSRF (plan 10) | see register |
| data-service answers → landing DOM | counts and names rendered as text (plan 11) | see register |
| graph data and LLM answers → DOM/canvas | untrusted text rendered by the Graph screen (plan 12) | see register |
| connector Bearer → heartbeat/capture/publish | the last places that accepted legacy tokens (plan 13) | see register |
| validation/Speckle data → DOM | untrusted model text rendered (plan 14) | see register |
| browser UI → connector-access routes | owner/admin grant mutations with cookie + CSRF (plan 15) | see register |
| DeGram host page → hosted table | untrusted host page renders the table (display only) (plan 15) | see register |
| server messages → DOM | untrusted text rendered (plan 16) | see register |
| DeGram main process ↔ remote DG page | fragment signals cross an Electron view boundary (plan 17) | see register |
| component repo → public fork | publishing boundary (not crossed in this plan) (plan 17) | see register |
| local component repo → public fork | publication (plan 18) | see register |
| framework gitlink → fork object | the pinned object must exist publicly (plan 18) | see register |
| working tree → container image | only committed code may cross (plan 19) | see register |
| operator → live services | restarts affect users (plan 19) | see register |
| operator → live auth stores | destructive rewrite of production JSON stores (plan 20) | see register |
| DeGram main process → remote DG page | the language travels as a URL fragment / query to an untrusted page (plan 21) | see register |
| renderer storage → I18nProvider | stored locale value read on load (plan 21) | see register |
| DeGram host query/hash → DOM | host language parameter and live signal (plan 22) | see register |
| server error text and user data → landing DOM | rendered as text (plan 23) | see register |
| access changes → live sessions | revocation must reach existing sessions (plan 24) | see register |
| live test harness → running stack | real account credentials used by live tests (plan 24) | see register |

---

## Threat Register

Built from the `<threat_model>` blocks of all 24 plans (92 threats: 85 mitigate, 4 transfer, 3 accept; 30 high, 40 medium, 22 low). Every SUMMARY `## Threat Flags` section reports no surface beyond the register.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-1308-01-01 | Tampering | settlement commit | medium | mitigate | stage by explicit path only; diff captured before and compared after | closed |
| T-1308-01-02 | Information disclosure | accidental staging of `.secrets/` or data stores | high | mitigate | explicit path list excludes `data-service/data/`, `.secrets/`, `bin/`, `obj/`; `git show --stat HEAD` checked | closed |
| T-1308-01-03 | Repudiation | lost owner work | low | mitigate | option B uses a named stash; option A keeps the diff in history | closed |
| T-1308-02-01 | Elevation of privilege | PUT members route | high | mitigate | policy `_MEM path owner` (owner or admin only); editor/viewer 403 tested | closed |
| T-1308-02-02 | Denial of service | last owner demotion | high | mitigate | `_last_owner_guard` under `auth._STORE_LOCK`; 409 LAST_OWNER tested incl. self-demotion | closed |
| T-1308-02-03 | Tampering | CSRF on PUT | medium | mitigate | `require_principal` enforces X-DG-CSRF for cookie principals; test without header | closed |
| T-1308-02-04 | Information disclosure | summary route | medium | mitigate | `_MEM path viewer`; Cypher filters `n.project = $project` (parameterized); counts only, key set asserted | closed |
| T-1308-02-05 | Tampering | Cypher injection via project | low | mitigate | `_check_project_name` + parameter binding, never string interpolation | closed |
| T-1308-03-01 | Spoofing | token guessing | high | mitigate | `secrets.token_urlsafe(32)` (CSPRNG, 256 bit); lookup by SHA-256 | closed |
| T-1308-03-02 | Information disclosure | store file | high | mitigate | hash-only storage; test asserts the raw token is absent from the file | closed |
| T-1308-03-03 | Elevation of privilege | stale access after demotion/grant revoke | high | mitigate | live `is_authorized` re-check on every authenticate; `revoke_unauthorized` for status honesty | closed |
| T-1308-03-04 | Spoofing | session after user deletion / company move | medium | mitigate | user and company re-checked; row marked revoked | closed |
| T-1308-03-05 | Tampering | concurrent writes | medium | mitigate | all read-modify-write under `auth._STORE_LOCK` with `auth._save` atomic replace | closed |
| T-1308-04-01 | Information disclosure | password over http | high | mitigate | refuse remote non-loopback http before any request; tested with zero captured requests | closed |
| T-1308-04-02 | Information disclosure | secrets in ToString/exceptions | high | mitigate | redacted `PrintMembers`; password only in the login body; tests assert absence | closed |
| T-1308-04-03 | Spoofing | credential stuffing via add-in | medium | transfer | server-side `/auth/login` throttle applies (Throttled outcome surfaced) | closed |
| T-1308-04-04 | Tampering | CSRF header missing | low | mitigate | X-DG-CSRF: 1 on login, mint and logout; asserted in tests | closed |
| T-1308-04-05 | Denial of service | hung request blocks GH | low | mitigate | 6 s per-request timeout via WaitAsync | closed |
| T-1308-05-01 | Tampering | `?lang=` / `#degram-lang=` / navigator.languages | medium | mitigate | closed vocabulary {en, ru} in parseHostSignal, resolveLang and setLang; host signals honoured only in host mode; only the validated value reaches `<html lang>` | closed |
| T-1308-05-02 | Tampering | XSS via translated/interpolated text | medium | mitigate | React text nodes only; interpolation is plain string replace; no HTML injection API (canon XSS: also covered by /gsd-secure-phase) | closed |
| T-1308-05-03 | Tampering | prototype keys in dictionary lookup | low | mitigate | `Object.hasOwn` lookups; test for "toString"/"__proto__" keys | closed |
| T-1308-05-04 | Elevation of privilege | new host signal grants capability | low | mitigate | `#degram-lang` only changes display language; no API, storage or navigation capability (hostMode.js header) | closed |
| T-1308-05-SC | Tampering | package installs | low | mitigate | none added (RESEARCH Package Legitimacy Audit: none); package.json diff limited to scripts | closed |
| T-1308-06-01 | Elevation of privilege | mint without grant | high | mitigate | `is_authorized` (owner/admin exempt, else active row) before issue; tests for each role | closed |
| T-1308-06-02 | Spoofing | dgd_/dgk_ minting sessions | high | mitigate | mint route is `_SES` (cookie users only); tests with both Bearer classes | closed |
| T-1308-06-03 | Information disclosure | token cached by proxies | medium | mitigate | `Cache-Control: no-store` on the mint answer, asserted | closed |
| T-1308-06-04 | Information disclosure | Neo4j credentials in multi-user | high | mitigate | `_neo4j_bundle_or_none` withholds the bundle unless the profile is local (D-34), tested with DG_DEPLOYMENT=multi-user | closed |
| T-1308-06-05 | Tampering | CSRF on mint | medium | mitigate | `require_principal` enforces X-DG-CSRF for cookie principals; test without header | closed |
| T-1308-06-06 | Information disclosure | PROJECT_REQUIRED hint | low | accept | lists only the caller's own eligible projects | closed |
| T-1308-06-07 | Repudiation | spec drift | medium | mitigate | fenced blocks + tests in the same commit (D-41) | closed |
| T-1308-07-01 | Information disclosure | password/session in .gh | high | mitigate | NonPersistentStringParam for Username and Password; Session is an output (never serialized) | closed |
| T-1308-07-02 | Information disclosure | secrets in messages | medium | mitigate | messages come from ErrorMessageTemplates without secret parameters; acceptance greps | closed |
| T-1308-07-03 | Information disclosure | password visible in a GH panel | medium | accept | masked dialog deferred by owner (D-38); documented in the release note | closed |
| T-1308-07-04 | Repudiation | session left live after Connect=false | low | mitigate | SignOutAsync on Connect=false and on removal; TTL 8 h bounds a crash (D-27) | closed |
| T-1308-08-01 | Tampering | wrong account deleted | high | mitigate | targets hard-coded, no CLI override; refusal when the project has other members; tests assert other rows unchanged | closed |
| T-1308-08-02 | Tampering | partial write on malformed store | high | mitigate | plan everything first, abort before any write (exit 3) | closed |
| T-1308-08-03 | Tampering | race with the live service | medium | mitigate | --apply documented to run with data-service stopped; lock held within the script | closed |
| T-1308-08-04 | Information disclosure | secrets in output | medium | mitigate | counts and status words only; stdout test | closed |
| T-1308-08-05 | Repudiation | no audit of retirement | low | mitigate | `retired: "D-49"` + `revoked_at` on each retired credential; backup in 1308-20 | closed |
| T-1308-09-01 | Elevation of privilege | editor exemption left in one caller | high | mitigate | single helper `is_exempt` in all callers; grep gate for the old rank check; matrix tests | closed |
| T-1308-09-02 | Spoofing | new tokens minted after D-49 | high | mitigate | 410 tombstone without minting; policy row session; test for every role | closed |
| T-1308-09-03 | Denial of service | legitimate clients break | medium | accept | owner-approved one-way change (Task 2), re-wire guide in release note (1308-07) | closed |
| T-1308-09-04 | Repudiation | spec/route drift | medium | mitigate | same-commit spec rows + test_security_boundary_spec | closed |
| T-1308-10-01 | Elevation of privilege | hiding controls as the only defence | high | transfer | the server routes are the control (owner/admin for roles, admin for policy, tested in 1308-02 and test_degram_policy.py); UI visibility is convenience | closed |
| T-1308-10-02 | Tampering | CSRF | medium | mitigate | all calls via `apiFetch` (credentials include + X-DG-CSRF), asserted in the API tests | closed |
| T-1308-10-03 | Tampering | path injection via usernames/projects | low | mitigate | `encodeURIComponent` on every path segment, tested with `'A/B ?#'` | closed |
| T-1308-10-04 | Information disclosure | policy visible to owners | medium | mitigate | `shouldShowProjectSettings` guard + unit test (D-02) | closed |
| T-1308-11-01 | Information disclosure | cross-tenant counts | medium | transfer | the server route is member-only and project-filtered (1308-02); the UI requests only the current project | closed |
| T-1308-11-02 | Information disclosure | LLM API key on the landing | medium | mitigate | builder reads only provider and model fields; test asserts no other field is rendered | closed |
| T-1308-11-03 | Denial of service | polling load | low | mitigate | one load per activation, no interval (grep gate) | closed |
| T-1308-11-04 | Tampering | XSS through names | low | mitigate | React text nodes only | closed |
| T-1308-12-01 | Tampering | XSS through translated or interpolated text | medium | mitigate | text nodes and canvas fillText only; interpolation is plain replacement; no HTML injection API | closed |
| T-1308-12-02 | Information disclosure | translation changes data meaning | low | mitigate | data values never pass through t() (D-13) | closed |
| T-1308-13-01 | Spoofing | leaked legacy token | high | mitigate | resolver refuses the prefix; route sweep test; credentials retired by 1308-20 | closed |
| T-1308-13-02 | Information disclosure | Neo4j bundle in multi-user | high | mitigate | `_neo4j_bundle_or_none` in the heartbeat; test_deployment_profile bundle tests on sessions | closed |
| T-1308-13-03 | Repudiation | spec drift on public routes | medium | mitigate | block + spec test change in the same commit | closed |
| T-1308-13-04 | Tampering | tests silently weakened during migration | medium | mitigate | each migrated test keeps its assertion intent; Task 1 runs green on the old and the new server | closed |
| T-1308-14-01 | Tampering | XSS via interpolated data | medium | mitigate | React text nodes only; interpolation is plain replacement | closed |
| T-1308-14-02 | Repudiation | status meaning changed by translation | low | mitigate | statuses mapped one-to-one through keys; codes stay data (spec/EVIDENCE-CONTRACT.md vocabulary unchanged) | closed |
| T-1308-15-01 | Information disclosure | token display | high | mitigate | all token UI and API calls removed; grep gates; harness asserts no token button | closed |
| T-1308-15-02 | Elevation of privilege | grant form shown to editors | medium | transfer | server route is owner/admin only (`_MEM path owner`); UI shows the form only to owner/admin | closed |
| T-1308-15-03 | Tampering | CSRF on grant/revoke | medium | mitigate | `apiFetch` with X-DG-CSRF, asserted in connector-access-api.test.mjs | closed |
| T-1308-15-04 | Information disclosure | member list exposure | low | mitigate | members are fetched only for owner/admin (same route the Projects screen uses) | closed |
| T-1308-16-01 | Tampering | XSS via translated text | medium | mitigate | React text nodes only; no HTML injection API in ui-v2/src | closed |
| T-1308-16-02 | Information disclosure | API key hints on the LLM model screen | low | mitigate | only labels are translated; key handling unchanged | closed |
| T-1308-17-01 | Tampering | navigation fragment injection | medium | mitigate | closed vocabulary on both sides (regex + DG_REGIONS + asRegion), tests for an unknown region | closed |
| T-1308-17-02 | Elevation of privilege | new region grants capability | low | mitigate | the signal is display-only navigation; no API or storage capability (hostMode.js header) | closed |
| T-1308-17-03 | Information disclosure | publishing to the public fork | high | mitigate | no push in this plan; owner pushes in 1308-18; only the seven component files are committed | closed |
| T-1308-17-04 | Tampering | installed Hermes profile | high | mitigate | no Desktop launch/build, no hermes update (D-44) | closed |
| T-1308-18-01 | Information disclosure | private material on the public fork | high | mitigate | owner pushes; the two commits hold only the files of 1308-17 and 1308-21 (their acceptance criteria) | closed |
| T-1308-18-02 | Tampering | dangling gitlink | medium | mitigate | ls-remote equality before staging; workspace.py verify after | closed |
| T-1308-19-01 | Tampering | WIP baked into images | high | mitigate | build only from `git archive HEAD` export; excluded files listed | closed |
| T-1308-19-02 | Denial of service | restart without consent | medium | mitigate | checkpoint:human-verify before build/restart | closed |
| T-1308-19-03 | Information disclosure | secrets in probes/records | medium | mitigate | probes without credentials; records hold ids and status codes only | closed |
| T-1308-19-04 | Repudiation | stale image served | medium | mitigate | image-id equality + in-container grep + bundle string check | closed |
| T-1308-20-01 | Tampering | wrong rows removed | high | mitigate | reviewed script with hard-coded targets (1308-08), dry run approved by the owner | closed |
| T-1308-20-02 | Tampering | lost data on failure | high | mitigate | verified backup before any write; restore procedure in the task | closed |
| T-1308-20-03 | Tampering | race with live writes | medium | mitigate | apply with data-service stopped | closed |
| T-1308-20-04 | Information disclosure | secrets in records | medium | mitigate | counts and status words only; backup outside the repository, never committed | closed |
| T-1308-21-01 | Tampering | fragment injection through the signal path | medium | mitigate | closed `HOST_LANG_FRAGMENT` allowlist and `DgLocale` validation; tests for invalid values | closed |
| T-1308-21-02 | Tampering | tampered stored locale | low | mitigate | coerced to `en` unless `ru`/`en` (D-51) | closed |
| T-1308-21-03 | Elevation of privilege | language signal grants capability | low | mitigate | display-only fragment, in-page navigation of the already-loaded host page only | closed |
| T-1308-21-04 | Information disclosure | publishing to the public fork | high | mitigate | no push here; owner pushes in 1308-18; only this plan's files are committed | closed |
| T-1308-21-05 | Tampering | installed Hermes profile | high | mitigate | no Desktop launch/build, no hermes update (D-44) | closed |
| T-1308-22-01 | Tampering | XSS via translated text | medium | mitigate | React text nodes only; no HTML injection API in ui-v2/src | closed |
| T-1308-22-02 | Tampering | host `?lang=` / `#degram-lang` | low | mitigate | closed vocabulary in resolveLang and parseHostSignal (1308-05) | closed |
| T-1308-23-01 | Tampering | XSS via interpolated names or errors | medium | mitigate | React text nodes only; `describeError` returns plain strings | closed |
| T-1308-23-02 | Denial of service | listener leak on remount | low | mitigate | `dg-lang` listener removed on engine teardown | closed |
| T-1308-24-01 | Elevation of privilege | session after demotion via invite path | high | mitigate | `revoke_unauthorized` after every role-changing `set_membership`; tests per path | closed |
| T-1308-24-02 | Information disclosure | cross-project status | medium | mitigate | status_for filtered by the caller's visible projects; test | closed |
| T-1308-24-03 | Spoofing | legacy token minted by a forgotten helper | high | mitigate | helpers deleted; grep gate | closed |
| T-1308-24-04 | Information disclosure | live test credentials in artifacts | medium | mitigate | read from env only, never written to evidence; skip when unset | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Transfers (all CLOSED with the receiving control verified): T-1308-04-03 (server login throttle, `auth_routes.py:142-172`), T-1308-10-01 (server role/admin routes, `route_policy.py:146,192-193`), T-1308-11-01 (member-only, project-filtered summary route), T-1308-15-02 (owner-only grant route, `route_policy.py:203-206`).

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-1308-01 | T-1308-06-06 | The no-membership hint lists the caller's own eligible projects only; documented in spec/SECURITY-BOUNDARY.md:69; app.py:1834-1848 filters by the caller's projects. | owner (plan-time register) | 2026-10-12 |
| AR-1308-02 | T-1308-07-03 | Accepted per D-38 (1308-CONTEXT.md:66); stated in docs/RELEASE-NOTES-v13.0.md:29-30 and spec/GRASSHOPPER.md:102. | owner (plan-time register) | 2026-10-12 |
| AR-1308-03 | T-1308-09-03 | One-way switch to grant-only connector access, approved by the owner at plan time (1308-09-SUMMARY key decisions); re-wire guide in docs/RELEASE-NOTES-v13.0.md. | owner (plan-time register) | 2026-10-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-14 | 92 | 92 | 0 | gsd-security-auditor (sonnet), orchestrated by `/gsd-secure-phase 1308` |

## Security Audit 2026-10-14

| Metric | Count |
|--------|-------|
| Threats found | 92 |
| Closed | 92 |
| Open | 0 |

Method: each mitigation read at its cited code location (data-service, ui-v2, DG C#, DeGram fork, specs), not taken from SUMMARYs. Tests re-run by the auditor: data-service pytest 1302 passed (security-boundary spec, connector session and routes, member roles, project summary, d49 cleanup, connector access, connectors, route inventory, deployment profile, degram policy; `DG_DATA_DIR` redirected to a scratch dir); ui-v2 node tests 194 passed. C# mitigations verified statically (a build would rewrite tracked bin/obj); recorded runs in 1308-04/07 SUMMARYs. Live, read-only: running image ids equal `1308-ROLLOUT.md`; backup `C:/dgbackup1308/20261013T223918Z/` `sha256sum -c` 19/19 OK; live `connector-credentials.json` 0 active, 13 `retired: "D-49"`; no store mentions `uat-pw-bd30ce`. Global grep finds no HTML injection API (`dangerouslySetInnerHTML`, `innerHTML`, `eval`, …) in `ui-v2/src`.

Notes: T-1308-21-05 closed with a note — the unpacked `win-unpacked` test build for the group F UAT ran under a separate owner authorization (`1301-BUILD.md`, "1308 UAT build"); the installed Hermes profile was untouched and nothing was launched by the agent. `DELETE /auth/connector-session` (self-revoke, plan 06) has no separate row; it revokes only the session matching the presented Bearer (`app.py:1896-1904`) and is in the spec route block.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-14
