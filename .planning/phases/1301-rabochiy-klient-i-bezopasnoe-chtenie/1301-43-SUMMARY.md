---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 43
subsystem: degram-environment-owned-profiles
status: complete
completed: 2026-10-26
requires: [1301-42]
provides:
  - versioned origin-owned profile identity and environment-scoped destructive operations
  - restartable local legacy profile migration behind backend-release barrier
  - filesystem preservation and Electron environment-boundary regression tests
affects: [1301-44, 1301-45, 1301-46, 1301-47]
requirements-completed: []
---

# Phase 1301 Plan 43: Environment-owned profiles and local migration

**Profile persistence now separates equal user/company/project IDs by canonical origin. Proven localhost history migrates locally through a restartable journal; ambiguous history is preserved. Implementation and bounded offline checks are complete, not runtime/product acceptance.**

## Execution scope

- Invocation: `/gsd-execute-phase 1301 --wave 2 --no-transition`.
- GSD computes this plan in DAG wave 2 although its frontmatter declares wave 30. Historical plans 04/07/08 in computed wave 2 already had summaries; only 43 was executed here.
- Inline execution on the existing checkout; no workers, worktrees, commits, pushes, dependency installs, Desktop builds/installs/launches, live server calls, installed-profile access or phase transition.
- Component and framework gitlink remain `b619e02e3725869b1ab5125951d3311e3656dc9a`. All source edits remain uncommitted; pre-existing plan-42 and unrelated workspace edits were retained.

## Delivered

| Area | Result |
| --- | --- |
| Identity | Scope includes canonical `origin` and matching `environmentId`. Profile identity uses versioned UTF-8 SHA-256 input and 32 lowercase hex characters. |
| Manifests | Version 2 binds user/company/project/origin/environmentId together. Invalid or conflicting ownership cannot authorize ensure or destructive operations. |
| Destructive operations | `purge` validates the exact owner; `purge-project` spans company keys only inside the requested environment and verifies the directory hash. Legacy cleanup reports ambiguous records instead of deleting them. |
| Compatibility | CLI calls without environment resolve only through the persisted, validated Developer loopback ownership journal. No unowned destructive default. |
| Migration | Uses the plan-42 legacy ownership claim, not the currently selected target; detects old names and valid legacy manifests, moves directories only locally, preserves history/memory/logs/config/bindings, and never uploads history. |
| Electron seam | Environment flags use argv-bound `--flag=value` on ensure/purge/purge-project/cleanup. Conflicting scope/environment is rejected before subprocess execution. Returned ensure profile must equal the locally computed scope identity before backend use. |
| Backend barrier | Adapter enumerates migration candidates, awaits release for each, then invokes migration with `--backend-stopped`. Failed release/migration blocks profile ensure and backend start; explicit retry is possible. Heartbeat errors are handled without skipping membership revocation. |
| Existing access boundary | Membership/grant checks and memory-only delegated credentials remain covered by the existing scope/IPC tests. |

## Journal and preservation semantics

1. Validate `dg-environment-ownership.json`: version 1, claimed/adopted legacy partition, canonical Developer loopback owner.
2. Enumerate 16-hex legacy directories and pending migration entries; Electron releases related backend candidates before migration.
3. Resolve ownership from a valid legacy manifest, or authenticated current scopes for manifest-less history under the proven legacy origin. Unknown/malformed state remains in place.
4. Detect source/destination collisions before mutation; preserve both directories on conflict.
5. Atomically write a `pending` entry to `degram-profile-migration.json` before renaming within the same local profiles root.
6. Backfill the version-2 environment manifest, then atomically persist `complete`.
7. Restart after an interrupted rename resumes using the recorded identity; malformed/conflicting destination metadata is not overwritten. Repeated completion leaves state bytes unchanged.

Real-filesystem tests cover `state.db`, `memories/note.md`, `logs/agent.log`, `documents/binding.json`, and `config.yaml`; A→B→A and B purge-project preserve A byte-for-byte. Traversal, malformed journals/manifests, collision and linked-directory cases preserve unrelated state. These offline fixtures do not prove a live SQLite/backend shutdown or a packaged migration.

## Cross-language identity vector

- Canonical origin: `https://dg.example.test` (also `HTTPS://DG.EXAMPLE.TEST:443/`).
- Environment: `dg-env-v1-` + full lowercase SHA-256 of UTF-8 `dg-env-v1:https://dg.example.test`.
- Profile input: `dg-profile-v2`, origin, `alice`, `acme`, `tower`, joined with U+001F, encoded UTF-8.
- Python and Electron expected profile: `scope-d882f6d4f1a222fd5d31569011e990ef`.
- Mode labels are not part of the identity. Different origins or ports produce different profiles.

## Files (component repository, uncommitted)

- `degram_variant/profiles.py`
- `tests/degram/test_profiles.py`
- `tests/degram/test_profiles_environment.py` (new)
- `apps/desktop/electron/degram/profiles-cli.ts` and `.test.ts`
- `apps/desktop/electron/degram/scope.ts` and `.test.ts`
- `apps/desktop/electron/degram/ipc.ts` and `.test.ts`
- `apps/desktop/electron/main.ts`
- Adjacent required seams: `apps/desktop/electron/degram/main-wiring.ts` and `.test.ts`, `scope-gate.ts` and `.test.ts`.

Framework: this SUMMARY plus bounded progress notes in STATE/ROADMAP. Offline generated code indexes were refreshed separately.

## Verification

| Check | Result |
| --- | --- |
| Existing child `.venv/Scripts/python.exe -m pytest tests/degram/test_profiles.py tests/degram/test_profiles_environment.py -q --tb=short` (child cwd) | Passed: 69 tests. |
| Plan's exact Electron selector: `npm --prefix apps/degram/apps/desktop test -- --project electron electron/degram/profiles-cli.test.ts electron/degram/scope.test.ts` | Passed: 2 files, 79 tests. |
| `npm --prefix apps/degram/apps/desktop test -- --project electron electron/degram/ electron/desktop-profile.test.ts` | Passed: 16 files, 295 tests. |
| `npm --prefix apps/degram/apps/desktop run typecheck` | Passed: all four configured TypeScript checks, no emit. |
| `git -C apps/degram diff --check` | Passed; Git reports existing CRLF→LF normalization notices, not whitespace failures. |
| Encoding inspection | Changed source files are UTF-8 without BOM; each is consistently CRLF or LF (no mixed line endings). |
| `python tools/degram/workspace.py verify` | Passed; gitlink/HEAD agree and component context is installed; product acceptance remains false. |
| GSD `verify.schema-drift` | No drift, non-blocking. |
| GSD `verify.codebase-drift` | Skipped by tool with `git-diff-failed`; not claimed as verified. |
| GSD `ui.safety-gate` | `hasUiFiles: false`, `block: false`. |
| `python tools/degram/index_code.py` | Final offline AST refresh completed with exit 0 (manifest `2026-10-26T00:31:49Z`, task `bhde34x8h`); no paid inference. Optional SQL grammar missing; SQL extraction remains incomplete. |
| Build / full upstream test suite / live UAT | Not run: explicitly outside this plan's authority. Typecheck and bounded tests are the integration gate used here. |

## Failures encountered and resolved / retained limitations

- PATH Python initially produced 65 setup errors because `ruamel.yaml` is absent. Reused the documented existing component venv; installed nothing.
- Initial focused Electron run exposed an old expectation that cleanup failure could still open a profile; changed to fail closed and added explicit-retry coverage.
- New tests initially used an incorrect expected hash, omitted the newly logged migration stage, and called `.some` on the log wrapper rather than `entries`. Corrected those test defects; final suite/typecheck pass above.
- Initial TypeScript seam errors (environment forwarding, profile mock migration method, random UUID reference) were fixed without optional identity fallbacks or suppressed checks.
- Relative npm prefix once resolved under the child cwd twice and failed ENOENT; final verification uses absolute prefixes.
- `index_code.py --help` does not implement argument parsing and ran the offline refresh rather than showing help; it only generated the documented code indexes. A deliberate refresh followed the final edits.

## Plan deviations (necessary adjacent fixes)

1. Updated `main-wiring.ts` and its test to forward required environment identity and migration collaborator. This keeps the real existing composition independently typecheckable.
2. Updated `scope-gate.ts` and its test to recognize both legacy 16-hex and new 32-hex scope profiles. Without this, new profiles would bypass the inactive-scope backend-start guard. No generic non-DeGram profile behavior changed.
3. Main config reads now treat only ENOENT as absent, rather than converting permission/read failures into a default target/ownership claim.
4. Shared STATE primary phase/counters and historical phase progress were not reset; appended only bounded plan-level evidence. Requirement completion remains empty.

## Follow-up and acceptance boundaries

- Next is plan 1301-44, computed DAG wave 3: safe target switch coordinator and real session/view/runtime rebinding. This run stops after selected wave 2.
- `DEGRAM_DG_PARTITION` remains the current fixed runtime partition until plan 44; this summary does not claim cookie/runtime isolation or safe dynamic switching is delivered.
- Plan 46 owns composed real-path/offline switching acceptance; plan 47 owns separate publication/build/install/live permissions and exact-version acceptance evidence.
- DGMODE-01..04, DGCL, HOST-05, 1301-16 and Phase 1301 remain open. No installed application or hosted service was changed.

## Self-Check: PASSED

Source/test artifacts exist, bounded checks pass, and uncommitted status is intentional under the plan's explicit no-commit instruction. This is plan-level offline completion only.
