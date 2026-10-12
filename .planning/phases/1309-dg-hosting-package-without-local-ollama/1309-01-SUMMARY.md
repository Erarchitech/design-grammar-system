---
phase: 1309-dg-hosting-package-without-local-ollama
plan: 01
subsystem: infra
tags: [docker-compose, hosted, cpu-only, unittest]
requires:
  - phase: 1205-security-boundary
    provides: Multi-user Compose overlay and server-side security boundary
provides:
  - CPU-only hosted Compose structural overlay with no Ollama service or volume
  - Required stdlib test runner and merged-model regression checks
affects: [1309-hosting, hosted-pilot]
actuals:
  tokens: 4900
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [Last-applied Compose reset/override, sanitized offline merged-model test]
key-files:
  created: [docker-compose.hosted.yml, deploy/hosted/tests/run_required.py, deploy/hosted/tests/test_compose_profile.py]
  modified: []
key-decisions:
  - "Apply hosted after base and multi-user, removing Ollama via !reset and retaining data-service via !override."
  - "Bind inherited UI and Speckle ingress to loopback pending a separately approved TLS edge."
patterns-established:
  - "Inspect sanitized docker compose config JSON; reject zero, skipped, or absent required tests."
requirements-completed: [HOST-01]
coverage:
  - id: D1
    description: "Hosted merged model removes Ollama service, volume, n8n dependency/environment and GPU reservation, retaining non-Ollama graph and loopback-only publications."
    requirement: HOST-01
    verification:
      - kind: integration
        ref: "deploy/hosted/tests/test_compose_profile.py#test_hosted_model_excludes_ollama_and_preserves_graph"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two-file local/multi-user model still includes Ollama, its volume, and n8n dependency."
    requirement: HOST-01
    verification:
      - kind: integration
        ref: "deploy/hosted/tests/test_compose_profile.py#test_local_two_file_model_retains_ollama_and_dependency"
        status: pass
    human_judgment: false
  - id: D3
    description: "Required runner fails on empty and skipped tests and nonexistent requested module."
    verification:
      - kind: unit
        ref: "deploy/hosted/tests/test_compose_profile.py#test_required_runner_rejects_zero_tests_and_skips"
        status: pass
      - kind: other
        ref: "python deploy/hosted/tests/run_required.py test_missing.py (expected exit 2)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Portable hosted behavior on an approved Linux engine and remote-provider denial remain unproven."
    requirement: HOST-01
    verification: []
    human_judgment: true
    rationale: "Windows Compose JSON parsing is not Linux staging or runtime/provider acceptance; separate authorization is required."
duration: 3 min
completed: 2026-10-12
status: complete
---
# Phase 1309 Plan 01: CPU-only hosted Compose tracer Summary

**A last-applied hosted overlay removes Ollama/GPU from the effective model while preserving the two-file local graph.**

## Performance
- **Duration:** approximately 3 min (task commits 20:09:04–20:10:53 UTC)
- **Completed:** 2026-10-12T20:11:14Z
- **Tasks:** 2
- **Files modified/created:** 3 implementation/test files, plus this summary

## Accomplishments
- Hosted merged model has 14 services versus local 15, no Ollama service or volume, no n8n Ollama dependency/env, no GPU reservation, and only loopback publications; non-Ollama service inventory retained.
- Two-file local/multi-user model still has Ollama and n8n's existing dependency.
- Stdlib required-test runner rejects empty, skipped and nonexistent requested modules; all 3 required tests passed (0 failures/errors/skips).

## Task Commits
1. **Task 1, failing contract:** `a09fe984a61330868a8e098fcedc51b84a67a502` (test)
2. **Task 2, hosted override:** `e147542246e6beaca98d671d0e7191bf5e3349b5` (feat)

## Files Created/Modified
- `deploy/hosted/tests/run_required.py` — required unittest discovery and fail-closed accounting.
- `deploy/hosted/tests/test_compose_profile.py` — sanitized, offline effective JSON checks and runner negative checks.
- `docker-compose.hosted.yml` — last-applied Compose reset/override and loopback binds.

## Verification and limits
- **RED:** `python deploy/hosted/tests/run_required.py test_compose_profile.py` before the overlay exited 1: local test OK; hosted test failed specifically `hosted overlay absent: create docker-compose.hosted.yml` (2 discovered, 1 failure, 0 errors/skips). `test_missing.py` request exited 2.
- **GREEN:** same command after the overlay exited 0: 3 discovered/ran, 0 failures/errors/skips. `docker compose version`: v2.40.3-desktop.1; Compose >=2.24.4 required for `!override` (target Linux parser still to verify). Actual `config --no-interpolate --format json` loaded with a generated harmless fixture outside the repository; no `.env` or credentials read. `git diff --check` passed.
- No service start/build, Docker network action, paid inference, remote-provider test, Linux staging, TLS/public ingress, or backup acceptance. The overlay is not a deployable production package by itself; base URLs remain localhost and later plans/gates own the release, ingress and live acceptance.

## Deviations from Plan
- Added last-file loopback replacements for UI and Speckle ingress because their inherited all-interface ports violated the plan's hosted port assertion. No shared base/runtime files changed.
- The test runner's negative paths are exercised with temporary modules. Editor YAML diagnostics do not understand Compose `!reset`/`!override`; Compose CLI v2.40.3 parsed the merged model successfully.

## Issues Encountered
- Initial `git commit --only` refused untracked files; staged exactly the two new test paths, then committed with `--only` to protect the preexisting unrelated index. The Git hook launched a background graphify rebuild; it was not used as verification.
- Concurrent Phase 1308 owns `.planning/STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`, and `.planning/config.json`; none was edited or committed here. Orchestrator must reconcile plan progress and requirement status without incorporating their preexisting staged changes.

## Next Phase Readiness
Ready for 1309-02 only under its own scope. HOST-01 is structurally demonstrated on Windows; Linux/runtime and remote-provider acceptance remain gated. No push/publication.
