---
phase: quick-261028-jug
plan: 01
type: execute
status: planned
files_modified:
  - data-service/auth.py
  - data-service/auth_routes.py
  - data-service/tests/test_auth_tracer.py
  - ui-v2/src/lib/auth.js
  - ui-v2/src/landing/LandingLayer.jsx
  - ui-v2/src/landing/landing.css
  - ui-v2/src/i18n/dict/landing.js
  - ui-v2/tests/auth-security.test.mjs
  - spec/SECURITY-BOUNDARY.md
autonomous: true
must_haves:
  truths:
    - Landing login in the browser and embedded DeGram offers an unchecked Remember me option.
    - Only an explicit opt-in creates a persistent 30-day cookie and a matching server session that survives overnight inactivity.
    - Passwords and tokens are never copied to localStorage; logout and revocation still work.
    - Ordinary and legacy sessions retain their server absolute and idle limits.
---

# Remember DG sign-in in WebUI and DeGram

Owner explicitly approved “Вход на 30 дней” on 2026-10-28: remembered sessions omit the two-hour idle timeout; ordinary sessions keep it.

Execution is inline in the current checkout per owner preference; no workers, branches, worktrees, publication, services or installed-profile writes. Framework repository only: DeGram embeds the same hosted landing and already owns persistent, origin-isolated Electron cookie partitions. No component source change, child commit or gitlink bump is needed.

## Task 1 — Server remember-me policy

**Files:** data-service/auth.py, auth_routes.py, tests/test_auth_tracer.py

**Action:** Accept an optional strict boolean rememberMe on login, default false. With opt-in issue a 30-day HttpOnly/SameSite=Strict cookie and hashed-token server record marked remember_me. Honor the same 30-day absolute bound on direct and delegated-parent authentication, without the normal 2-hour idle limit. Ordinary login gets a browser-session cookie and existing server limits. Existing registration/invitation callers and old records retain their prior semantics. Keep revocation and no-token response contracts.

**Verify:** pytest auth tracer/store/delegated suites, synthetic temporary stores only.

**Done:** Both deployment profiles prove opt-in persistence, ordinary/legacy expiry, exact expiry boundaries, failed-login behavior, Secure cookie attributes, logout, and password revocation.

## Task 2 — Shared landing option

**Files:** ui-v2/src/lib/auth.js, landing/LandingLayer.jsx, landing/landing.css, i18n/dict/landing.js, tests/auth-security.test.mjs

**Action:** Add a keyboard-accessible native checkbox styled with tokens, unchecked by default, visible only in login mode, with Russian/English copy and a 30-day/shared-device hint. Send rememberMe only with login; never persist form credentials or tokens in browser storage. Use the same path for WebUI and embedded DeGram.

**Verify:** node --test ui-v2/tests/; npm --prefix ui-v2 run build; focused mounted browser check where available.

**Done:** Option is wired to the request in both host modes and translations exist; no new credential storage or Electron permissions.

## Task 3 — Contract, checks and GSD bookkeeping

**Files:** spec/SECURITY-BOUNDARY.md, quick PLAN/SUMMARY, .planning/STATE.md

**Action:** Document the opt-in policy. Run focused and integration checks, workspace preflight and graphify update. Preserve all existing unrelated edits, including in LandingLayer, SECURITY-BOUNDARY and STATE; commit only this quick task's hunks using an isolated temporary Git index if necessary. No push/deploy/build of Desktop.

**Done:** Honest summary distinguishes source/test completion from live deployed-browser/Desktop acceptance, and STATE quick-task table references the scoped code commit. ROADMAP is untouched.
