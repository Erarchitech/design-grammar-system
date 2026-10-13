---
phase: 1309-dg-hosting-package-without-local-ollama
plan: 02
subsystem: infra
tags: [caddy, https, docker-compose, synthetic-black-box]
requires:
  - phase: 1309-01
    provides: CPU-only hosted Compose overlay
provides:
  - Three-origin loopback HTTPS edge wired into the three-file hosted Compose model
  - Explicit DG/Speckle/S3 route allowlist, default deny and origin contract
  - Sanitized Compose assertions and owner-executed synthetic Caddy route evidence
affects: [1309-03, hosted-pilot]
actuals:
  tokens: 0
  tasks: 2
  commits: 9
tech-stack:
  added: [Caddy-v2.10.2-synthetic-test]
  patterns: [last-applied-hosted-overlay, loopback-only-synthetic-black-box]
key-files:
  created: [deploy/hosted/ORIGINS.md, deploy/hosted/edge/Caddyfile, deploy/hosted/edge/Run-Edge-Test.ps1, deploy/hosted/edge/build_test_zip.py, deploy/hosted/edge/TEST-PACKAGE.md, deploy/hosted/tests/test_edge_routes.py]
  modified: [docker-compose.hosted.yml, deploy/hosted/tests/test_compose_profile.py]
key-decisions:
  - "The single hosted edge publishes only 127.0.0.1:443; no public ingress, real DNS or certificate cutover is authorized."
  - "Object upload is excluded from invited pilot pending actual signed URL, CORS, ETag and Speckle import proof."
  - "Synthetic black-box ran on owner-selected Windows 11 machine with disposable certificates and loopback upstreams, not Docker or real applications."
patterns-established:
  - "Require scoped owner approval before running even isolated network processes; preserve the boundary between synthetic route tests and deployment acceptance."
requirements-completed: [HOST-03]
coverage:
  - id: D1
    description: "Hosted merged Compose model and HTTPS origin boundary reject invalid configurations and unintended published ports."
    requirement: HOST-03
    verification:
      - kind: integration
        ref: "python deploy/hosted/tests/run_required.py test_compose_profile.py"
        status: pass
      - kind: integration
        ref: "python deploy/hosted/tests/run_required.py test_edge_routes.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Owner-executed synthetic Caddy fixture validates allowed routing, preserved object request shape, spoof reset and denial of unlisted hosts/paths."
    requirement: HOST-03
    verification:
      - kind: manual_procedural
        ref: "Owner-provided dg-edge-synthetic-v1 JSON, DESKTOP-OS4Q8CP, 2026-10-13T16:11:54Z, 32/32; V6 SHA-256 1ba512a85b9728dd775ab86232ac204b5e90be766b46a7263a53f39f13964b99"
        status: pass
    human_judgment: true
    rationale: "Report was supplied by owner in chat; target host and command exit were not observed directly by the executor."
  - id: D3
    description: "Real signed S3 URL/CORS/import flow, Linux Compose runtime and public deployment remain unproven and outside the authorized test."
    requirement: HOST-03
    verification: []
    human_judgment: true
    rationale: "Requires pinned Speckle/MinIO images, approved isolated runtime and separate public ingress authorization; uploads remain excluded."
completed: 2026-10-13
status: complete
---
# Phase 1309 Plan 02: Hosted HTTPS edge summary

**Three-origin Caddy edge routes were checked offline and in a scoped synthetic loopback run, without opening public ingress.**

## Accomplishments
- The merged hosted Compose configuration wires a single loopback-only TLS edge for DG, Speckle and path-style object requests, with explicit route allowlists and denied unlisted hosts/paths.
- Local offline verification passed: `test_compose_profile.py` 4/4 and `test_edge_routes.py` 8/8; sanitized fixtures do not read working `.env`.
- After approval for an isolated test on the second Windows 11 PC, the owner returned `dg-edge-synthetic-v1` report at 2026-10-13T16:11:54.6447460Z for `DESKTOP-OS4Q8CP`: `total=32`, `passed=32`, `failed=0`, `blackBoxComplete=true`. Report covers Caddy validation/start, DG/Speckle routing, synthetic object PUT/GET with Host/path/query/body preservation, spoof reset and unlisted-host/path denials. The command exit code and target machine were not independently observed.

## Task commits
- Origin/edge wiring: `04c3697`.
- Scoped fixture and regression fixes: `fdabec8`, `a089cda`, `18b74ec`, `b9fa140`, `bc54bd5`, `d802f9f`, `f9ae548`.
- Owner report and boundary update: `000e8db`.

## Verification and limits
- Owner-tested V6 ZIP exists locally with SHA-256 `1ba512a85b9728dd775ab86232ac204b5e90be766b46a7263a53f39f13964b99`. Earlier V5 stopped at `validate` because PowerShell 5.1 elevated Caddy stderr warnings to `NativeCommandError`; the V6 runner handles native stderr while still checking `$LASTEXITCODE`.
- This is **synthetic Caddy+loopback only**. No real Speckle/MinIO, S3 signature/CORS/import proof, Docker services, public deployment, real DNS/certificates or paid calls. Object upload remains excluded from invited pilot until a separately authorized real-stack proof.
- The owner approval applied to the named synthetic test only. Plan 03 has its own sandbox-runtime checkpoint; this report cannot satisfy that permission. Concurrent phase 1308 owns shared `.planning/STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` and `config.json`; these were not edited here.

## Next phase readiness
Plan 03 can begin its allowlist/manifest static preparation. Docker, n8n or data-service runtime integration must wait for its named sandbox authorization; release freeze and public ingress remain separate gates.
