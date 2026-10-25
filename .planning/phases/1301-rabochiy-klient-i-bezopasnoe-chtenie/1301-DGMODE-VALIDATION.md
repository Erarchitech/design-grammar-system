---
phase: 1301
slug: rabochiy-klient-i-bezopasnoe-chtenie
scope: DGMODE-01..04
status: draft
nyquist_compliant: false
wave_0_complete: false
---

# DGMODE validation strategy (supplement)

Additive to historic 1301-VALIDATION.md; does not overwrite prior verification/UAT or mark requirements complete. Plans 42–47 only. Structural planning self-check is not execution or independent review.

## Test infrastructure

Planning host reports Node v20.20.0, below Desktop package.json engines (^22.22.0 || ^24.11.0 || >=26.0.0). Before implementation tests, select an already installed supported Node runtime or report a prerequisite blocker; do not install or waive engines implicitly.

Existing Desktop Vitest projects: electron/node and ui/jsdom, verified in apps/degram/apps/desktop/vitest.config.ts. Existing scripts: test and typecheck. Actual Python suites are under apps/degram/tests/degram/. Use existing installed dependencies only; missing runtime/dependency is a blocker, not permission to install. All runtime homes are disposable; never installed Hermes/DeGram, no user PATH-writing upstream test.

## Wave 0 / new test files

These are planned outputs, NOT present/passing tests:
- 42: dg-target-config.test.ts, environment-storage.test.ts.
- 43: tests/degram/test_profiles_environment.py.
- 44: environment-controller.test.ts, tests/degram/test_environment_activity.py.
- 45: dg-target-selector.test.tsx, environment-scope.test.tsx.
- 46: environment-real-path.test.ts, environment-switch-race.test.ts.

Create tests in the owning implementation plan before accepting that seam. No separate blanket test-infrastructure rewrite.

## Sampling and requirement map

| Requirement | Plan/task | Automated check | Live evidence |
|---|---|---|---|
| DGMODE-01 | 42/1–2, 44/2, 45/2 | Config/env/default/fail-closed tests; selector preauth/ready/error; restart real-path | Existing install, both targets and restart |
| DGMODE-02 | 43/1–2, 45/3, 46/1 | Same-home equal-ID collision; actual Python profiles CLI; journal interruption; scoped purge; cache/history/bindings | A→B→A preserves original local state |
| DGMODE-03 | 44/1–2, 45/3, 46/2 | Main/backend busy barrier; stale generation; no replay/fallback; target failure/TLS/grants; bridge loopback | Explicit Stop/retry and authorized target failure/grant checks |
| DGMODE-04 | 46/all, 47/all | Production imports plus actual temp filesystem and bounded regressions; exact revisions/results | Owner-authorized versioned localhost/Contabo matrix; stock Hermes unaffected |

Per-task selectors are in PLAN files. Run focused checks immediately after each seam, then complete bounded suite in 46 before publication. A failed release/credential-clear check blocks all new-target auth. No sleeps for deterministic race tests.

## Full bounded commands

Framework cwd C:/Users/Admin/source/repos/design-grammar-system:

```text
python tools/degram/workspace.py verify
python -m unittest discover -s tools/degram/tests -v
npm --prefix apps/degram/apps/desktop test -- --project electron electron/degram
npm --prefix apps/degram/apps/desktop test -- --project ui src/degram
npm --prefix apps/degram/apps/desktop run typecheck
```

Child cwd C:/Users/Admin/source/repos/design-grammar-system/apps/degram:

```text
python -m pytest tests/degram/test_profiles.py tests/degram/test_profiles_environment.py tests/degram/test_environment_activity.py tests/degram/test_credentials_provider.py tests/degram/test_relay_error_mapping.py tests/degram/test_lockdown.py -q
```

Actual CLI subprocess test must use an existing interpreter and explicit temp home/child cwd. No installs/shims/conftest bypass. Launcher/PATH-mutating upstream suites are excluded. A missing optional prerequisite is a named skip/blocker, never pass.

## Manual-only gates

Plan 47 requires separate commit/push/build/install/launch/live authorizations. Visual placement versus native embedded view, actual TLS rejection, deployed version agreement, real login/grant behavior and stock installation nonmutation require appropriate observed runtime evidence. Paid inference/CAD mutations/revocation/server changes are separately gated. Required but unauthorized cases stay pending. Mock TLS failures test error handling, not actual production certificate verification.

## Reporting

Keep offline and live evidence separate. Expected/actual, exact versions/hashes/cwd, failures/skips and causes are required. Build success is not target propagation or live acceptance. Do not set nyquist_compliant/wave_0_complete true until actual tests and mapping exist and pass. DGCL/HOST-05/recovery/Phase 1301 are not closed by this supplement.
