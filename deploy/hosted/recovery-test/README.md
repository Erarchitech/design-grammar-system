# Synthetic two-store recovery exercise — not full hosted recovery

Preparation tooling is separately hashed; product source/images are exact `c82b92b29423c515e353e3fa4f9c17e9b0d83438`. Run only on `DESKTOP-OS4Q8CP` under a separate explicit recovery approval. No runtime approval is inferred from preparation or earlier smoke. Default mode is package preflight only, without Docker.

## Intended exercise and limits

Two unique initially vacant Compose projects, internal IPv4-only networks, no published ports/build/pull/push/image removal/paid calls. Source synthetic Neo4j and API state are seeded through approved test paths; API and Neo4j are stopped and inspected stopped before offline native Neo4j dump and complete API state export. A bounded encrypted snapshot includes dump, API tree and synthetic verification state. Ciphertext alone crosses into a new destination helper; wrong-key/corruption checks precede restore. Native load and application/graph assertions distinguish actual recovery from an empty healthy service.

Two application images already verified in the prior smoke must exist in the target daemon. No TAR reload or rebuild. Source/destination helper containers use those same IDs with no network. At most one active application stack: Neo4j 1500 MiB, API1250 MiB, two maintenance helpers768 MiB each =4286 MiB maximum configured running RAM, 1 CPU/service. Docker>=6GiB, disk>=20GiB. 40min main plus at most3min cleanup/project (6min total). Helpers root only inside disposable containers; no privileged mode, Docker socket or broad host mounts. Single API worker retained.

Only newly created labelled project resources are cleaned. Existing stacks/images/TARs are retained. `backup.enc` remains in output but ephemeral RECOVERY_KEY and application secrets do not persist on host or in chat: this ciphertext is a test artifact, not an operational recoverable backup/key escrow. It demonstrates same-host source-to-new-project recovery, **not** off-machine backup, RPO/RTO, reboot, registry portability or full HOST-04. PostgreSQL/MinIO/Speckle/n8n/Redis and their keys remain open. Encrypted in-memory data limits:128MiB synthetic input,1024 files,64MiB/file; not production-scale streaming backup.

## Modes

Run `support/Run-Recovery.ps1` with mandatory PackageZip, ExpectedZipSha256, and fresh external OutputDirectory. Default validates package/extraction only. `-RunRecovery` starts the separately approved exercise. Preserve old outputs; never retry into an existing output or delete unrelated resources after a failure. Return only sanitized `recovery-report.json` and `process-exit.json`. Do not return backup ciphertext, logs, config, inspect output, environment or test secrets.

Process exit must be captured by an outer launcher immediately after powershell.exe returns; the launcher writes process-exit.json even on runtime failure and refuses to label null exit zero. Package/report write failure remains a failure. Parent issuing the package supplies a tested one-click launcher so no manual LASTEXITCODE recovery is needed.

## Offline verification and evidence vocabulary

Required suites run with the already installed Python 3.13 + cryptography: package 3, execution 9, runner 2, probe 17, snapshot 20 = 51 package/recovery tests; standalone diagnostic 2 and cleanup 3 add 5 offline contracts (56 total), zero skips. Runner coverage includes the actual generated ZIP, Windows PowerShell 5.1 default launcher/child preflight, persisted exit 0/1, extraction tampering and both real config-only Compose outputs with rejected unsafe mutations. Lifecycle fixtures test command order/failure handling, not native database behavior. Snapshot tests perform real encryption/decryption of synthetic files, including a >8 MiB dump fixture; that fixture is not a native database dump.

`checks.seed` records creation/ingest/CSRF assertions at the source. In `checks.restore`, `seed_projects_created`, `seed_authenticated_ingests` and `seed_csrf_denied` are historical seed expectations, not repeated writes or destination CSRF tests. Destination assertions freshly test login/membership/isolation/revocation, graph content hashes and settings decryption. `cleanup=not-started` and `cleanupVerified=false` are required when no project activation was attempted. Only owned-project down plus verified vacancy may report removal.

## V3 probe correction and retry boundary

V2 owner attempt returned FAILED at seed, process exit 1 and verified owned-project cleanup. Offline exact-source audit identified a deterministic probe defect: foreign individual-note reads must return 404 (conceal existence), not 403; project-scoped list denial remains 403. Pinned product factory regression caught the mismatch before correction. Source contract audit found no earlier deterministic mismatch, but the coarse target report does not prove which seed substep failed. Probe final logout now attempts both sessions and cannot overwrite an earlier exception; a logout-only failure still fails closed. CLI remains generic and secret-free. V3 changes tooling only; product/image/Compose/resource bounds are unchanged. Preserve v1/v2 ZIPs, extractions and reports. V3 requires fresh scoped owner approval and fresh directories; v2 approval is not reused.

## V2 correction and retry boundary

V1 stopped at helper ownership admission because PS5 concatenation/comma precedence produced one allowlist entry rather than four. Each name expression is now parenthesized; a real ownership-validator regression accepts each exact volume and rejects a foreign name. Primary exercise failure is preserved independently of cleanupFailureStage. Source/image/model/resource bounds are unchanged. V1 owner cleanup returned OWNED_CLEANUP_COMPLETE and exit 0; this is owner-reported cleanup evidence only, not recovery acceptance. A v2 target attempt requires a fresh explicit approval for the new ZIP and fresh extraction/output directories; do not retry v1 or overwrite its evidence. Standalone diagnostic/cleanup scripts are not part of the v2 execution payload.

## Pending target evidence

Offline fixture/PowerShell/Compose tests do not establish native command availability, daemon cancellation or successful actual recovery. The actual run can fail closed at any stage. No cleanup or release claim precedes the target report. Rights/source inclusion follow the existing issued package; no new publication/commit permission is inferred.
