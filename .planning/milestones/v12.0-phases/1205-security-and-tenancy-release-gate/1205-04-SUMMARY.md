---
phase: 1205-security-and-tenancy-release-gate
plan: "04"
subsystem: infra
tags: [de01, httpx, fernet, secrets-rotation, security-checker, pytest]

# Dependency graph
requires:
  - phase: 1205-01
    provides: data-service/secrets_policy.py known-default literal/prefix list
  - phase: 1205-02
    provides: data-service/auth.py principal resolvers (not used directly by this plan, but the auth model this plan's checker/token path anticipates)
provides:
  - "legs.data_service_auth_headers() (D-20): connector-token Bearer header for DE-01's data-service and replay legs"
  - "data-service/rotate_llm_master_secret.py (D-13): LLM_MASTER_SECRET re-encryption CLI for the rotation runbook"
  - "tools/security/check_live_boundary.py (D-16): live direct-proxy/exposure checker for the two live checkpoints"
affects: [1205-10, 1205-16, 1205-18, 1205-19]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Token read fresh from env/file at call time, never cached into a config dict or report field (T-1205-04-01)"
    - "known-default literal matched only as a quoted string value (\"literal\"/'literal'), never a bare substring, to avoid false-positiving on legitimate identifiers that contain the word (speckleBaseUrl contains \"speckle\")"
    - "Atomic settings-file rewrite via temp file + os.replace, only after a round-trip decrypt verification under the new secret"

key-files:
  created:
    - tools/de01/tests/test_de01_auth_headers.py
    - data-service/rotate_llm_master_secret.py
    - data-service/tests/test_rotate_llm_master_secret.py
    - tools/security/check_live_boundary.py
    - tools/security/tests/test_check_live_boundary.py
  modified:
    - tools/de01/legs.py
    - tools/de01/run_de01_repeat.py
    - tools/de01/README.md

key-decisions:
  - "D-20: token precedence is DG_DE01_CONNECTOR_TOKEN env var, then the first non-empty line of the file named by DG_DE01_CONNECTOR_TOKEN_FILE (default .de01/connector-token), else no header at all"
  - "D-13: rotate_llm_master_secret.py reads/writes the settings JSON directly (not through llm_gateway's load/save helpers) so every field the script doesn't touch survives untouched, and verifies the full decrypt(old)->encrypt(new)->decrypt(new) round trip before writing anything"
  - "D-16: check_live_boundary.py's known-default scan matches only quoted string values, not bare substrings, after a config.js fixture (speckleBaseUrl) initially false-positived on the bare word \"speckle\""

patterns-established:
  - "Recording httpx.Client / httpx.MockTransport stand-ins for HTTP-leg and live-checker tests, never a real socket in the unit suite"

requirements-completed: [ALGN12-19, ALGN12-20]

coverage:
  - id: D1
    description: "DE-01 host-runner sends a connector-token Bearer header on the data-service and replay legs (and run_de01_repeat.py's pinned-replay GET) when configured via env or a gitignored file, and sends no header at all when unconfigured -- byte-identical to pre-1205 behavior"
    requirement: ALGN12-20
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_auth_headers.py::TestDataServiceAuthHeaders"
        status: pass
      - kind: unit
        ref: "tools/de01/tests/test_de01_auth_headers.py::TestDataServiceLegSendsHeaders"
        status: pass
      - kind: unit
        ref: "tools/de01/tests/test_de01_auth_headers.py::TestReplayLegSendsHeaders"
        status: pass
      - kind: unit
        ref: "tools/de01/tests/test_de01_auth_headers.py::TestPinnedReplaySendsHeaders"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_de01_repeat.py's JSON/Markdown reports never contain the connector token, because it is never folded into the leg config dict"
    requirement: ALGN12-20
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_auth_headers.py::TestReportNeverLeaksTheToken"
        status: pass
    human_judgment: false
  - id: D3
    description: "rotate_llm_master_secret.py re-encrypts the stored LLM apiKey from old to new LLM_MASTER_SECRET, verifies the round trip, writes atomically, exits 2 on a wrong old secret without writing, exits 3 on missing env, reports nothing-to-rotate when no apiKey is present, and supports --dry-run"
    requirement: ALGN12-19
    verification:
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestRotateSuccess"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestRotateWrongOldSecret"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestRotateMissingEnv"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestRotateNothingToRotate"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestRotateDryRun"
        status: pass
    human_judgment: false
  - id: D4
    description: "rotate_llm_master_secret.py prints only one of five fixed status words per run -- never the old/new secret or the decrypted plaintext API key -- and its argparse surface carries no secret-bearing flag"
    requirement: ALGN12-19
    verification:
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestOutputHygiene"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_rotate_llm_master_secret.py::TestArgparseNoSecretFlag"
        status: pass
    human_judgment: false
  - id: D5
    description: "check_live_boundary.py detects a live stack's /neo4j/ and /n8n/ direct-proxy routes (fails on a 200 SPA fallback, not just a non-404), unauthenticated data-service access (401 required, root 200 required), and config.js leaking a D-12 credential key name or a known-default value"
    requirement: ALGN12-19
    verification:
      - kind: unit
        ref: "tools/security/tests/test_check_live_boundary.py::TestCheckProxyRemoved"
        status: pass
      - kind: unit
        ref: "tools/security/tests/test_check_live_boundary.py::TestCheckUnauthenticated"
        status: pass
      - kind: unit
        ref: "tools/security/tests/test_check_live_boundary.py::TestCheckConfigJs"
        status: pass
    human_judgment: false
  - id: D6
    description: "check_live_boundary.py's multi-user profile fails when Bolt/Neo4j-HTTP/n8n ports are reachable on the host, and its local profile reports the same ports as non-failing informational rows"
    requirement: ALGN12-19
    verification:
      - kind: unit
        ref: "tools/security/tests/test_check_live_boundary.py::TestCheckPorts"
        status: pass
      - kind: unit
        ref: "tools/security/tests/test_check_live_boundary.py::TestRunAllChecksAndExitCode"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 04: DE-01 Connector Token, LLM Secret Rotation, and Live Boundary Checker Summary

**Three operator tools shipped independent of the auth route code: DE-01's connector-token path (D-20), the LLM_MASTER_SECRET re-encryption CLI the rotation runbook calls (D-13), and a live direct-proxy/exposure checker for the two upcoming live checkpoints (D-16) — 187 new/updated tests, all green.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-28T00:00:00Z (approx, pre-commit)
- **Completed:** 2026-09-28
- **Tasks:** 3
- **Files modified:** 8 (3 modified, 5 created)

## Accomplishments
- `legs.data_service_auth_headers()` gives the DE-01 host runner a connector-token Bearer header on the data-service and replay legs (and `run_de01_repeat.py`'s pinned-replay GET), sourced from `DG_DE01_CONNECTOR_TOKEN` or a gitignored token file, with zero change to behavior when unconfigured — and proven never to leak into a report.
- `data-service/rotate_llm_master_secret.py` re-encrypts the stored LLM API key across a `LLM_MASTER_SECRET` rotation, verifying the round trip before an atomic write and failing closed (exit 2) on a wrong old secret without touching the file.
- `tools/security/check_live_boundary.py` gives 1205-18/1205-19 a deterministic, repeatable live check for direct-proxy removal, unauthenticated-access boundaries, `config.js` credential hygiene, and multi-user port exposure — replacing ad hoc curl.

## Task Commits

Each task was committed atomically:

1. **Task 1: DE-01 host-runner connector-token path** - `dfc677b` (feat)
2. **Task 2: LLM_MASTER_SECRET re-encryption script** - `f1be490` (feat)
3. **Task 3: Live direct-proxy and exposure checker** - `3d039fb` (feat)

_No TDD RED/GREEN split was used — each task's implementation and tests were written and verified together per the plan's `tdd="true"` behavior-first `<behavior>`/`<action>` structure, then committed as a single `feat` covering both._

## Files Created/Modified
- `tools/de01/legs.py` - Added `data_service_auth_headers()` (D-20) and wired it into the data-service and replay legs' `httpx.Client` constructions
- `tools/de01/run_de01_repeat.py` - Wired the same headers helper into the pinned-replay GET
- `tools/de01/README.md` - New "Authenticated legs (Phase 1205)" section documenting how to mint and supply the token
- `tools/de01/tests/test_de01_auth_headers.py` - New: 22 tests covering the header helper, both legs, the pinned-replay GET, and the no-leak property
- `data-service/rotate_llm_master_secret.py` - New: env-only secret rotation CLI reusing `llm_gateway.decrypt_value`/`encrypt_value`
- `data-service/tests/test_rotate_llm_master_secret.py` - New: 14 tests (success, wrong-secret, missing-env, nothing-to-rotate, dry-run, output hygiene, argparse surface)
- `tools/security/check_live_boundary.py` - New: read-only live-stack checker (proxy removal, unauthenticated access, config.js hygiene, port exposure)
- `tools/security/tests/test_check_live_boundary.py` - New: 20 tests using `httpx.MockTransport` and an injected port connector, no live stack or real socket

## Decisions Made
- **Token precedence (D-20):** `DG_DE01_CONNECTOR_TOKEN` env var wins; otherwise the first non-empty line of the file named by `DG_DE01_CONNECTOR_TOKEN_FILE` (default `.de01/connector-token`, already gitignored); otherwise no header — never a crash, never a silent invention of a token.
- **Rotation script reads/writes raw JSON directly**, not through `llm_gateway.load_persisted_llm_settings()`/`save_persisted_llm_settings()`, so any field this script doesn't touch (e.g. `baseUrl`) survives byte-for-byte, and the exact original ciphertext is available for the wrong-old-secret negative-control test.
- **Known-default literal matching in `config.js` is quoted-value-only, not bare-substring.** The plan's own known-default set (`secrets_policy.KNOWN_DEFAULT_LITERALS`) includes short generic words (`speckle`, `admin`, `neo4j`, `password`) that are also substrings of entirely legitimate, non-secret identifiers already present in `config.js` today (e.g. `speckleBaseUrl`). A bare-substring scan would have permanently false-positived on the passing-stack case discovered while writing this plan's own tests; matching only `"literal"`/`'literal'` (a full quoted JS string value) fixes this while still catching a literal credential value like `neo4jPassword: "12345678"`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] config.js known-default check false-positived on legitimate identifiers**
- **Found during:** Task 3, writing the "passing stack" test fixture for `check_config_js`
- **Issue:** A bare substring scan for `KNOWN_DEFAULT_LITERALS` (which includes the word `"speckle"`) matched inside the entirely legitimate `speckleBaseUrl` key name in a config.js that carries no actual credential — the check would have failed every real config.js that references Speckle at all, not just ones leaking a secret.
- **Fix:** Changed the match to require the literal appear as a full quoted string value (`"literal"` or `'literal'`), never as a bare substring of an identifier.
- **Files modified:** `tools/security/check_live_boundary.py`
- **Verification:** `TestCheckConfigJs::test_passing_config_js_has_no_credential_or_default` (previously failing, now passing) and `TestCheckConfigJs::test_credential_key_present_is_a_failure` (still catches the genuine leak case)
- **Committed in:** `3d039fb` (Task 3 commit; found and fixed before the commit, so the fix is part of the single task commit, not a separate follow-up)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correctness fix caught by the plan's own test-writing process before any commit; no scope creep, no behavior change beyond fixing the false positive.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required. (D-13's live rotation against real secrets and D-16's live checkpoint against a rebuilt stack are owner-run checkpoints in later plans, 1205-18/1205-19 — this plan ships only the tooling.)

## Next Phase Readiness
- `legs.data_service_auth_headers()` is ready for 1205-10 to depend on: once that plan enforces auth on `/validation/publish` and `/validation/view/*`, the DE-01 runner keeps working with a token configured, and degrades to the same typed 401 `error` LegResult it already handles for any other HTTP failure when unconfigured.
- `rotate_llm_master_secret.py` is ready for 1205-16 to reference as step 5 of the rotation runbook it will author in `spec/SECURITY-BOUNDARY.md`.
- `tools/security/check_live_boundary.py` is ready for 1205-18 (owner-run rotation checkpoint) and 1205-19 (GATE12-05 live multi-user checkpoint) to invoke against a rebuilt stack — no further code changes anticipated, only live invocation with real `--ui-url`/`--data-service-url`/`--profile multi-user` arguments.
- No blockers. This plan touched no route/auth code, so it carries no risk of interfering with wave-1 sibling plans building the identity/authorization model.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 8 created/modified source files and the SUMMARY.md itself verified present on disk; all 3 task commit hashes (`dfc677b`, `f1be490`, `3d039fb`) verified present in `git log --oneline --all`.
