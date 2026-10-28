---
phase: quick-261028-jug
plan: 01
status: complete
date: 2026-10-28
implementation_commit: 07dd8a9
---

# Remember DG sign-in in WebUI and DeGram

Implemented the owner's request and explicit approval of the 30-day remembered-login policy. Source and offline checks are complete; deployment and installed-client restart acceptance remain open.

## Delivered

- Shared landing login: unchecked native “Remember me” checkbox, Russian/English label, personal-device warning, 30-day hint. Only shown in login mode, not invitation acceptance or registration.
- Client sends a strict boolean `rememberMe`; no username, password, hash or token is saved to browser storage.
- Opt-in sessions use a 30-day persistent HttpOnly/SameSite=Strict cookie (Secure in HTTPS deployments) and matching absolute server expiry, without the ordinary two-hour idle timeout.
- Ordinary login uses a browser-session cookie and existing server absolute/idle limits. Existing registration/invitation cookie semantics and legacy session records are preserved.
- Direct authentication and delegated-parent checks agree. Logout revokes remembered sessions; password change revokes other remembered sessions while retaining the current session under existing policy.
- DeGram already embeds the hosted landing in an origin-isolated persistent cookie partition. No component changes, child commit, gitlink bump or Desktop build is required.
- Security boundary contract updated. All unrelated working changes, including environment-selector work in shared files, were excluded from the commit through a temporary isolated Git index.

## Verification

- `python -m pytest data-service/tests/test_auth_tracer.py data-service/tests/test_auth_store.py data-service/tests/test_delegated_token.py -q`: **201 passed**, four existing per-request-cookie deprecation warnings. Tests cover both deployment profiles, strict opt-in, cookie attributes, ordinary/remembered expiry, failed login, logout and password-change revocation with synthetic temporary stores.
- `python -m pytest data-service/tests/test_security_boundary_spec.py -q`: **16 passed**.
- `node --no-experimental-global-navigator --test "ui-v2/tests/*.test.mjs"`: **392 passed**, zero skips. Unmodified `browser-language.test.mjs:14` fails under default Node24 because it assigns to the built-in getter-only navigator; the runtime flag restores that test's expected environment.
- `node ui-v2/tests/run-remember-login.mjs`: **12/12 passed**, mounted real landing and auth client, WebUI/DeGram host modes, opt-in on/off, RU/EN live labels, login-only option, two requested window widths (1280/390). Network is replaced by synthetic responses under a deny-network CSP and a fresh temporary browser profile. Initial harness assertions ran before the async login finished; waiting for completion fixed the harness, not product code.
- `npm --prefix ui-v2 run build`: **passed**; existing large-chunk warning. Initial `node --test ui-v2/tests/` fails directory resolution on Node24; used explicit glob instead.
- Browser harness emits an existing duplicate `Run check` dictionary warning from unrelated changes in screens.js; that file was not modified by this task.
- `python tools/degram/workspace.py verify`: **passed**, child/gitlink unchanged at `5a535a5910c28eaa93f2a7c34c7ec9ff239fa721`.
- `graphify update .`: **passed**, AST-only; missing optional SQL parser warning, no package install. Generated graph changes are local and excluded from this task's commit.
- Scoped `git diff --check`: passed; changed source files have no UTF-8 BOM.

## Decisions and limits

- Owner chose “Вход на 30 дней” after the environment correctly required explicit approval to remove the two-hour idle timeout for opt-in sessions.
- No workers/subagents/worktrees/branches; executed inline in the current checkout.
- No push, server update, Docker recreation, installed-profile write or Desktop launch. Newly built WebUI assets are not the running stack.
- Remaining live acceptance: deploy committed backend and WebUI, sign in with the option in a browser and installed DeGram, close/reopen each, then verify sign-out. Browser session restore can restore even ordinary session cookies; server limits remain authoritative.
