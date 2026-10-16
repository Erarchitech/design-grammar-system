# Four-image archive verification and isolated smoke (not a release)

Target: **DESKTOP-OS4Q8CP only**, Windows PowerShell 5.1 / Docker Desktop Linux containers.
Source commit: `c82b92b29423c515e353e3fa4f9c17e9b0d83438`.
The source files come from the issued v2 controlled-build ZIP; new tooling is separately hashed, uncommitted preparation, not part of that source commit.

## v2 normalization correction

The owner-run v1 loaded and verified all four image IDs/platform/revision labels, then failed at compose-config before project startup (exit 1, cleanup not-started). Local reproduction of the issued v1 ZIP with actual offline Compose config succeeded but its model was rejected: Compose emits empty ipam and null command/entrypoint. v2 admits only empty ipam and null defaults (not empty arrays/strings or executable overrides), and fixes PS5 StrictMode enumeration of empty objects. The exact target exception was not retained, so local reproduction is not a claim of independently diagnosing its sole cause. Image/source/Compose inputs and runtime scope are unchanged; no image rebuild is needed. Preserve v1 ZIP/extraction/output and all existing TARs.

## Modes and permissions

- `-PackagePreflightOnly`: check this ZIP and extraction only; **no Docker, no TAR access**. Works on the development PC for offline verification.
- Default with `-ArchiveDirectory`: check the four TAR sizes and SHA-256, original build-report identity/source/member maps and complete image records; **no Docker**. Preserve all originals.
- `-RunIsolatedSmoke`: explicit additional owner approval required before use. On named target only: verify all archives first, load four TARs, inspect exact image IDs/platform/revision labels, create a unique project on an internal IPv4-only network, no published ports, build, pull, registry push, paid model calls or user data. Bounded one CPU per service, total container RAM <= 5250 MiB, pids <=256 each, 20 GiB free disk, Docker memory >=6 GiB; total main-command deadline 30 minutes, cleanup bounded separately to 5 minutes. All four existing loaded images and all TARs remain. Only the uniquely owned project's disposable containers, networks and volumes are removed.

Four-image subset: Neo4j, API, reasoner, UI; synthetic ingest/auth/CSRF/private-path negatives, reasoner DB reachability and HTTP UI/assets/proxy tombstones. **Not a visual browser test**, full HermiT/SHACL workload, n8n/Speckle/HTTPS/provider test, frozen release, backup/restore or off-machine/cross-daemon portability proof. API cookie Secure=false only for the internal HTTP probe; no ingress.

A load on the same Docker daemon where images already exist cannot establish cold-cache portability. Report flags retain that limitation. No image/tag deletion or rollback of `docker image load` is attempted. Verified TAR hashes establish bytes against owner report, not independently attested exporter identity.

## Handoff

Use new extraction and output directories outside one another. Keep original `build-output-c82b92b-v2` intact. Supply its path as `-ArchiveDirectory`; it must contain original `build-report.json` and all four TAR files (other old `.iid`/docker-config files are ignored, never read).

Return only the sanitized `runtime-report.json` and immediate `$LASTEXITCODE`, not Docker logs, env, credentials or build output. On failure stop; preserve artifacts and report, do not restart or remove unrelated services. Timeout kills the CLI process tree; daemon-side cancellation is unproven. Cleanup status must be checked before any PASS claim.
