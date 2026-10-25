---
phase: 1309-dg-hosting-package-without-local-ollama
plan: 03
subsystem: infra
tags: [hosting, allowlist, release-manifest, sandbox, blocked]
requires:
  - phase: 1309-02
    provides: Hosted Compose overlay and synthetic edge test
provides:
  - Offline allowlisted source assembler and draft manifest integrity validator
  - Owner-reported synthetic ingest and n8n file-access capability evidence, distinct from hosted-bundle integration
affects: [1309-04, 1309-05, HOST-02]
key-files:
  created: [deploy/hosted/release-allowlist.json, deploy/hosted/assemble.py, deploy/hosted/release_core.py, deploy/hosted/validate_manifest.py, deploy/hosted/tests/test_release_manifest.py, deploy/hosted/tests/test_bundle_runtime.py, deploy/hosted/build_sandbox.py]
  modified: [docker-compose.hosted.yml, deploy/hosted/RELEASE.md]
key-decisions:
  - "Only the named second PC was authorized for the disposable synthetic sandbox; this is not a hosted release runtime or a production deployment."
  - "A BLOCKED source candidate is not a FROZEN release, and owner-reported V11 evidence cannot satisfy test_bundle_runtime.py."
coverage:
  - id: D1
    description: "Offline release allowlist, clean export and unsafe mount/digest rejection"
    requirement: HOST-02
    verification:
      - kind: integration
        ref: "python deploy/hosted/tests/run_required.py test_release_manifest.py (15/15, 2026-10-14; reviewed-font regression included)"
        status: pass
    human_judgment: true
    rationale: "Current HEAD clean export fails on a newly tracked TTF, and no frozen image provenance exists."
  - id: D2
    description: "Hosted bundle runtime fixture ingest and n8n file read"
    requirement: HOST-02
    verification:
      - kind: integration
        ref: "python deploy/hosted/tests/run_required.py test_bundle_runtime.py (1/1 BLOCKED, 2026-10-14)"
        status: fail
    human_judgment: true
    rationale: "Approved synthetic V11 is a different harness; this hosted-bundle integration harness is absent and has not run on its authorized target."
  - id: D3
    description: "Immutable frozen candidate with exact per-service image digests and build/registry provenance"
    requirement: HOST-02
    verification: []
    human_judgment: true
    rationale: "No frozen 1301/1308 release candidate or real image digests supplied; freeze belongs to plan 05."
completed: 2026-10-14
status: halted
---
# Phase 1309 Plan 03 — partial reconciliation, designed halt

## Latest owner-run image smoke — successful report, missing process exit

Owner returned runtime v2 `LOAD_AND_ISOLATED_SMOKE_COMPLETE`, all four image identities and all readiness/smoke/cleanup/retention checks. The preceding v2 daemon-preflight failure was explained by the owner as Docker not running; subsequent complete report supersedes it for this scope. Retained chat transcription and actual offline disposition: `deploy/hosted/image-runtime/evidence/`. Exact ZIP/source/image/report checks match; process exit is **unknown**, since `$LASTEXITCODE` produced no output. Reconciler exit 2 explicitly preserves successful report checks with `evidenceComplete=false`; it is not the target exit. Four evidence tests pass. Do not repeat a mutating smoke only for the lost exit.

This updates only the four-image subset; status remains `halted`, HOST IDs unchecked, no full hosted/fresh-daemon/registry/recovery/freeze acceptance. Offline recovery preparation remains possible under plan 04's own contract, but its live checkpoint requires distinct approval. No commit/push/deployment or development Docker occurred.

## Image-runtime correction (2026-10-16)

Owner reports all four images loaded/identity verified, then runtime v1 `FAILED`/`compose-config`, exit1, no project startup. Local offline actual Compose normalization reproduces validator failure; fixed safe empty ipam/null image defaults plus StrictMode empty-object enumeration, regression RED->GREEN. Runtime suites25/25, final new ZIP preflight0 and actual Compose admission0; no development daemon/services. Runtime v2 ZIP `6fc3b7ad060db3e79a1452e2a2868f87e339aed8bfa70c39b2f3c82b1fa8199f`, 4,134,782 bytes; same images/source/Compose input, preserved v1. Target exception unavailable, no sole-cause claim. Runtime retry pending; no commit/push, status halted and all full-hosted/recovery/freeze gates retained.

## Owner-returned v2 complete; next-step preparation (2026-10-16)

Owner report: four `BUILD_EXPORT_COMPLETE`, failureStage null, process exit 0 on the named second PC. Issued ZIP/source manifest/187 source files/runner identity corroborated locally, not target daemon/TAR observation. Labelled projection: `deploy/hosted/image-runtime/c82b92b-build-evidence.json`; original report bytes not transferred, runtime timestamp unknown. Four-image archive-verification and isolated-smoke tooling is prepared: `DG-image-runtime-c82b92b-v1.zip`, SHA-256 `ddf133c1cecbfabc22e0d32a6a77d44a96149b96eda40185c59b99236e41c99b`, 4,134,290 bytes/198 members/187 source files. Runtime offline suites 24/24, source Git-blob comparison, actual final-ZIP PS5.1 package preflight exit0/Dockerfalse, missing archives and tampered-extraction failures checked; target runtime not executed. No Docker invoked on development PC, no runtime permission inferred, no commit/push. These observations supersede target-build-pending statements below only. Full hosted runtime, off-machine/cross-daemon load, immutable registry availability, recovery and release freeze remain open; status stays `halted`.

## Corrected controlled-build v2 prepared (historical pre-target state, 2026-10-16)

Owner authorized only the scoped fix commit and new ZIP, no push. Commit `c82b92b29423c515e353e3fa4f9c17e9b0d83438` changes matcher and its regressions only, preserving all 19 unrelated staged paths/entries. ZIP `DG-controlled-build-c82b92b-v2.zip`, SHA-256 `9d391a82f5dac6bf53d8d83e5154c67c448fc4f56ea008e84c01c2f2916c7717`, has 187 exact source inputs including main/App. Final archive verification, Git blob validation, PowerShell preflight (exit 0, Docker false) and Vite build (exit 0, existing local dependencies) passed; release/package/runner suites 18/18, 3/3, 45/45. No Docker image build or push/deploy locally. This supersedes only the uncommitted/no-new-ZIP statements of the v1 diagnosis below. No full target image success, load/runtime, restore or freeze accepted; status remains halted.

## Controlled build update — partial export, UI blocker (2026-10-16)

Owner report for controlled ZIP `7be35265add9dcc56494adb0d1b247d522c9df0189c6ab29d4437216d68f02b6`: `FAILED` at `build:design-grammars`, exit 1; Neo4j/reasoner/API report `BUILD_EXPORT_COMPLETE`. Preserve those target artifacts. Local Vite reproduction from the issued ZIP fails resolving `/src/main.jsx`: recursive matching omitted both committed root `src/main.jsx` and `App.jsx`. RED export regression preceded component-wise glob fix; release tests 18/18 pass. Corrected scratch export has 187 source files, passes Git blob validation and local Vite build (981 modules, exit 0 using existing dependencies, no Docker). This is not target image acceptance. The fix is uncommitted; the controlled packager/historical-revision package test intentionally fail at the dirty-preparation guard until a separately authorized scoped commit. No replacement ZIP or commit/push/deployment occurred. See `deploy/hosted/build-job/README.md` and labelled projection `2dedbfb-v1-failure-disposition.json`. All full-runtime/images/restore/freeze gates and halted status remain.

## Latest evidence update — candidate subset PASS, release gates open

This section supersedes stale pending/uncommitted/current-HEAD statements below **only for the ALNST/source-integrity fixes and three-service candidate handoff**. Historical reconciliation is retained; plan status remains `halted`, HOST-02 unchecked, and no dependent plan is accepted or automatically advanced. The owner requested further preparation; offline recovery/tool work is not completion of plans 04–06.

- Scoped commit `2dedbfb3e138c2b437e781696197105dca93342a` contains the preparation fixes/runner. ZIP SHA-256 `1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e`, candidate manifest SHA-256 `864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810`.
- The owner returned a complete actual-candidate subset `PASS` on `DESKTOP-OS4Q8CP` and separately process exit `0`: package/Compose/isolation, login/CSRF, one ingest and scoped note, four denied paths, n8n named/denied reads and verified cleanup. This supersedes the earlier preflight FAIL for the later successful run; no unprovided runtime timestamp is inferred.
- `deploy/hosted/runtime-evidence/2dedbfb-owner-report.json` is the owner-report transcription, not an independently fetched or signed report. `accept_runtime_evidence.py` compared report identity and complete checks against the issued ZIP and all member hashes: `OWNER_REPORTED_CAPABILITY_PASS`, `independentlyObservedRuntime=false`, `releaseAccepted=false`, exit 0.
- Separate `test_bundle_runtime.py`, full hosted edge/UI/reasoner/Speckle/LLM runtime, immutable images/build provenance and backup/restore remain open. Cached image inspection now cannot retroactively attest image bytes used in the completed run.
- The offline recovery inventory/contract is in `deploy/hosted/RECOVERY.md`. No Docker or service mutation on the development PC; no live recovery exercise, freeze, staging, commit or push is authorized by this update.

**Not complete.** Tasks 1 and the offline portion of Task 2 were implemented in earlier scoped commits. The checkpoint allowed only a disposable synthetic sandbox on `DESKTOP-OS4Q8CP`; the hosted-bundle runtime requirement remains BLOCKED. HOST-02 is not accepted and plans 04–08 must not start on this summary.

## Verified on this reconciliation

- `test_release_manifest.py`: originally 13/13 pass; after the allowlist regression tests and fix, 15/15 pass. `test_sandbox_package.py`: 17/17 pass. Hosted Compose and edge suites: 4/4 and 8/8 pass. These are offline tests; no Docker/service operation was performed in this reconciliation.
- A fresh clean export of the exact earlier commit `80b1bde03c835ccf5a380ff2bf5be10f8a59a7db` assembled 179 hashed files under Hermes scratch. `validate_manifest.py --allow-blocked --source .` passed; the unqualified frozen-release validator failed as intended. This is a draft source bundle, not a runnable immutable release.
- The owner-reported V11 synthetic sandbox at commit `1503710bdbcc05d4fd5d638d927481706b545908` returned `PASS`, including ingest, n8n positive/denied file-read markers and cleanup. See `DG_OBSIDIAN/sessions/2026-10-14 Phase 1309 sandbox V11 runtime verified release open.md`. This evidence is not independently observed hosted-bundle runtime evidence and cannot be substituted for `test_bundle_runtime.py`.
- `python tools/degram/workspace.py verify` succeeded: DeGram HEAD and gitlink both `c476c236ad04be8aa28f42410ed20f2e1372858e`, component context installed; product acceptance remains false.

## Open and newly detected

- `test_bundle_runtime.py`: 1/1 fails nonzero with `BLOCKED: named owner sandbox runtime permission required` in this development session. Its separate `run_bundle_runtime.py` target harness does not exist; do not set an approval variable to bypass the host guard. A new scope-specific target run and sanitized evidence are required.
- A fresh clean export of **current** HEAD `1503710bdbcc05d4fd5d638d927481706b545908` fails `ASSEMBLY BLOCKED: ValueError` (`unknown UI source suffix`) because the allowlist in that commit predates the newly tracked `ui-v2/src/styles/tokens/fonts/alnst-400-normal.ttf`. The working-tree policy now excludes that exact path from the recursive suffix gate and admits it as a separate reviewed input; its bytes match the owner-supplied `ALNST_0.ttf` (SHA-256 `b817d148a0726887fd20f2ec8161ed422e2ae77fbf29dcd0b7f4ad632cc385f8`). Two RED tests preceded the fix. The 15/15 release tests now pass, including a clean synthetic Git export of the exact font and fail-closed rejection of another `.ttf`; sandbox 17/17, Compose 4/4 and edge 8/8 pass. This fix is uncommitted: the assembler correctly rejects a dirty policy when building from current HEAD, so a fresh real-revision bundle is not yet built. Do not silently omit the font or claim current-HEAD release validation.
- No exact per-service `repository@sha256:` digests, built-image provenance or pinned merged Compose candidate exist. `validate_manifest.py` therefore cannot certify a release. Real frozen candidate validation remains a later gate (1309-05), not implied by the draft integrity pass.
- Rehashed source drift was also found: the previous `--allow-blocked --source` checked revision existence but did not compare selected file bytes with that revision. A new regression first failed on a rehashed modification, then `validate_manifest.py` was tightened to compare every selected file with its committed Git blob; the assembler now disables Windows archive CRLF conversion to preserve those bytes. Offline release tests pass 16/16. This still does not produce a frozen bundle or runtime evidence.
- ALNST web-use rights checkpoint resolved by owner attestation (2026-10-16): «Я подтверждаю права на веб-использование. Лицензию ALNST не проверять». No further licence investigation is requested. The design decision and RELEASE.md record this confirmation; it does not itself authorize a public-repository push or deployment.
- Target access clarified by the owner (2026-10-16): physical access to `DESKTOP-OS4Q8CP` is available; remote access is not. Use a manual transfer/owner-run ZIP/returned sanitized JSON evidence path, not remote login and not Docker on the development machine. Do not ask the owner to repeat the old V11 as a substitute for hosted-bundle integration. The candidate-capability builder and target-only runner are implemented and offline-tested in `deploy/hosted/build_bundle_test.py`, `bundle-test/` and `tests/test_bundle_package.py` (5/5). Review fixes: no nested test mounts into a read-only n8n candidate bind; bounded process-tree termination is exercised against disposable PowerShell parent/child processes; CRLF checkout policy/support are accepted only as EOL conversions while archive and policy interpretation use committed bytes. Latest offline suites: package 5/5, release 16/16, sandbox 17/17, Compose 4/4, edge 8/8 (50/50); compile and diff checks pass. No Docker services were launched. A synthetic committed fixture exercised actual Windows PowerShell preflight and changed/extra-file rejection without Docker operations. This is a three-service candidate subset, not a frozen/full hosted acceptance harness. Final target ZIP and runtime evidence remain pending an authorized scoped commit and exact-source build; do not substitute the fixture ZIP.
- Provider budget gate: the public Timeweb Cloud Netherlands page lists NL-15 (1 GiB, 1,820 ₽/month), NL-30 (2 GiB, 2,860 ₽/month) and NL-40 (2 GiB, 3,760 ₽/month). These published small tiers cannot be assumed to run the full graph/UI/Speckle/n8n stack; a capacity/budget measurement and Russian-network HTTPS check have not been performed. No VPS purchase or deployment is authorized by this summary.

## Commit provenance and next step

The scoped code/test sequence includes `2a6cd2e` (RED inventory), `d783eb4` (runtime guard), `80b1bde` (assembler/validator), `22ab3ce` (synthetic package), and `1503710` (isolated n8n evidence volume), with intermediate correction commits listed by `git log --grep='1309-03'`. This reconciliation does not amend those commits, touch shared `STATE.md`/`ROADMAP.md`/`REQUIREMENTS.md`, or publish a release.

Resolve the TTF clean-export regression under a failing test; implement and run the separate authorized hosted-bundle integration harness on the named target; then replace this halted summary only after all acceptance criteria pass. Until then, dependency propagation must keep 1309-04 and later plans blocked.

## Self-Check: FAILED

The offline subset passed; the plan-level required runtime integration is nonzero and current-HEAD assembly fails. The new source-blob regression passes, but this does not change the halted status. This is an intentionally halted partial record, not a completion claim.
