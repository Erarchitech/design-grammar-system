# Controlled exact-source image build — preparation, not release

## Owner scope

The owner requested «Прситупай к сборке на основе последнего доступного коммита» after the current-cache observation. Latest local framework HEAD checked for this job: `2dedbfb3e138c2b437e781696197105dca93342a`, branch `feature/hosting-dg-pilot`. This is a local HEAD selection, not a claim to have fetched every remote branch. No Git fetch/pull/commit/push, source changes, registry publication or deployment is included.

The runtime build is a manual owner-run job on `DESKTOP-OS4Q8CP` only; no remote access is assumed and no Docker daemon operations occur on the development machine. New preparation tooling is hashed separately and is explicitly **not** represented as committed in that source revision.

## Build and evidence boundary

`build_image_job.py` exports only allowlisted committed source blobs through `assemble.py`, validates each against the Git revision, checks the four effective build contexts and writes a hashed ZIP with `source/`, `support/Run-ImageBuild.ps1` and `build-job-manifest.json`. Runtime never loads the repository/owner `.env` or starts the hosted Compose stack. Uncommitted API/UI/DeGram changes do not enter the source package.

The job builds only the four source-built services: Neo4j, reasoner, data-service, UI. It does not pull or freeze all n8n/Speckle/Caddy runtime images. Each build gets a unique local tag, source revision label, immediate iid-file and fixed-field image inspection; each image is then saved to a target-side tar with SHA-256/size. Local config IDs, registry RepoDigests and tar hashes are different fields. Empty RepoDigests for local builds do not become fabricated registry digests. No `push`, containers/services, ports, network/volume creation, `prune` or resource deletion.

This establishes an agent-prepared controlled build recipe plus owner-returned build/export evidence, not independent observation of that remote run or a signed build attestation. Previous cached-image reports cannot prove these new builds happened. Image tars demonstrate an export artifact, not tested import/boot on another host.

## Operational limits and retained gaps

- Linux/amd64 Docker Desktop; Internet for base images, apt/pip/npm and Neo4j plugin download.
- At least 30 GiB free on output drive; Docker's own disk image also needs adequate capacity. This preflight is not a guaranteed sizing measurement. Four sequential builds with `--pull --no-cache`, up to 45 minutes per command and 3 hours overall; build-time dependencies have outbound network access. No paid inference.
- Images, cache and tar files remain on target for transfer/verification. Do not send multi-gigabyte image archives in chat; return sanitized JSON and process exit code only.
- A timeout kills the Windows CLI process tree but may leave daemon-side build work; report failure and do not automatically prune/cancel unrelated work.
- Dockerfile base tags, apt packages, pip requirements and some downloaded artifacts are not digest/checksum locked. Exact source revision **does not mean bit-reproducible dependency resolution**. `reproducibleDependencies=false` remains explicit. Source Dockerfiles are not silently rewritten.
- The bounded job does not enforce CPU/RAM limits on BuildKit; operator must ensure Desktop resources are suitable before launching. It cannot promise the old three-service test's resource footprint.
- Full hosted runtime, release freeze, all-service digest coverage, transfer/load validation and multi-store recovery remain open. No `FROZEN` manifest or HOST acceptance is produced.

## Offline preparation verification

```text
python deploy/hosted/tests/run_required.py test_image_build_package.py
python deploy/hosted/tests/run_required.py test_image_build_runner.py
python deploy/hosted/build_image_job.py --repo . --revision 2dedbfb3e138c2b437e781696197105dca93342a --output NEW_EXTERNAL_ZIP
python deploy/hosted/build_image_job.py --output NEW_EXTERNAL_ZIP --verify-only
```

## Verified v2 handoff (2026-10-16)

Owner authorized the scoped fix commit and new ZIP, without push. Commit `c82b92b29423c515e353e3fa4f9c17e9b0d83438` contains only `release_core.py` and `tests/test_release_manifest.py`; all 19 unrelated staged paths and their index entries were preserved. Independent review found no blocking security/logic issues. New archive: `DG-controlled-build-c82b92b-v2.zip`, 4,111,030 bytes, SHA-256 `9d391a82f5dac6bf53d8d83e5154c67c448fc4f56ea008e84c01c2f2916c7717`. It contains 187 source files including both root UI files. ZIP verification, exact Git blob validation, actual final-extraction PowerShell preflight (exit 0, `PREFLIGHT_ONLY_COMPLETE`, Docker false) and Vite build of that extraction (exit 0, existing local node_modules; large-chunk warning) passed. Required release/package/runner tests: 18/18, 3/3, 45/45. Package regression now resolves local HEAD rather than pinning the known-defective historical preparation revision; dirty-input guards are unchanged. Newly authored build tooling remains uncommitted and separately hashed. No Docker daemon operations, push or deployment occurred locally.

The target runner rebuilt all four images into a NEW output directory with unique tags. The owner returned all-four `BUILD_EXPORT_COMPLETE`, failureStage null and exit 0; no further build is requested. See `../image-runtime/c82b92b-build-evidence.json` for a labelled projection, not original file bytes. Package/source/runner identity was corroborated locally, not target TAR bytes or Docker execution. Earlier uncommitted/no-replacement statements below describe the v1 diagnosis before this authorization and are superseded only for this fix/ZIP. Full hosted/runtime/load/restore/freeze remain open.

## Owner-returned v1 failure and local diagnosis (2026-10-16)

The owner returned `FAILED`, stage `build:design-grammars`, process exit 1, with three `BUILD_EXPORT_COMPLETE` records (Neo4j, reasoner, API). Those archives/images remain on the target; no removal or repeated build is requested. See `2dedbfb-v1-failure-disposition.json` for a labelled projection, not the original report bytes. UI has no completed image/export. This is partial owner-reported evidence, not release acceptance.

The issued ZIP hash was independently rechecked. It omits committed `ui-v2/src/main.jsx` and `App.jsx`: whole-path `fnmatch` treated `src/**/*` as requiring at least one subdirectory. The actual local Vite build of that ZIP fails resolving `/src/main.jsx` (exit 1). A RED clean-export regression preceded the component-wise recursive matcher fix; release tests now pass 18/18. A new scratch export of 187 exact committed source blobs passed source validation, then Vite built 981 modules (exit 0). Existing local dependencies were used through a temporary junction removed after the probe; this does not exercise target `npm ci`, Alpine or a Docker image. The original target error was discarded by the runner, so no claim is made to have independently identified its only failure cause.

The correction is uncommitted. `build_image_job.prepare` intentionally rejects the dirty preparation input, including the historical-revision package test: do not weaken that guard, relabel modified tooling as committed at `2dedbfb`, patch the old target extraction in place or reissue v1. A separately authorized scoped commit and a newly verified versioned ZIP are needed before another owner-run build. Docker was not invoked locally; no commit/push/deployment occurred. Keep full hosted, load/boot, immutable dependency and restore gates open.

## Historical verified owner handoff (integrity only, UI build defective)

Final ZIP: `DG-controlled-build-2dedbfb-v1.zip`, 4,106,244 bytes; SHA-256 `7be35265add9dcc56494adb0d1b247d522c9df0189c6ab29d4437216d68f02b6`. Local independent package verification and final-archive extraction followed by actual PowerShell 5.1 `-PreflightOnly` returned exit 0, `PREFLIGHT_ONLY_COMPLETE`, `dockerInvoked=false`, 185 source files. Required offline tests: runner 45/45, package 3/3. No target image build is claimed by these results.

The source revision is the latest local HEAD identified above. Newly authored runner tooling remains separately hashed (`49a9e00c1cc856a1f7fd0419735894e598c41ae5d58414e947be7211eca00798`) and uncommitted, not part of that source revision. No commit/push was performed.
