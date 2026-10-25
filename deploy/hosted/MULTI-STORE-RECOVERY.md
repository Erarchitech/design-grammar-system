# Multi-store recovery — offline checkpoint preparation

Status: **PREPARATION ONLY; runtime BLOCKED pending a separate approved harness**.
Authority remains framework `.planning/phases/1309-dg-hosting-package-without-local-ollama/1309-04-PLAN.md` and HOST-04. This is a technical contract, not a second roadmap. Two-store v3 PASS is preserved; no retry is needed.

## Continuation increment — offline modules, not an executable native harness

The next six module slices were implemented test-first and exercised on synthetic
files/providers only:

- `recovery_sequence.py`: explicit backup/restore order, failure/interruption latch,
  reentrant callback rejection; no automatic resume, service calls or completion
  marker. This is an ordering engine, **not** the trusted outer attestation runner.
- `recovery_n8n.py`: complete stopped 2.4.8 SQLite `.n8n` tree including config/key,
  WAL/SHM, binary data and empty directories; inventory/hash validation before
  exclusive publication. External DB config, links/reparse points/hardlinks and
  NTFS streams fail closed. Matching effective config/key and stopped state still
  require independent target enforcement. POSIX modes/ACLs/xattrs and native n8n
  recovery are unqualified; conservative ASCII path subset rejects unsupported
  names rather than skipping them. No native activation occurs.
- `recovery_objects.py`: bounded byte/metadata streams and read-back verification
  using a synthetic provider, portable numeric filenames for arbitrary S3 keys.
  Only **never-versioned, no bucket policy/lifecycle/encryption/lock/replication/
  notifications** qualification subset. Unsupported configuration is rejected,
  not omitted. Native MinIO client, complete pagination/version/tool binding,
  PostgreSQL object-reference reconciliation and full metadata coverage remain open.
- `recovery_queues.py`: two strict empty samples bound to independently supplied
  image/probe/schema identities and Redis/PostgreSQL/n8n-SQLite backend coverage.
  No actual physical queue queries or qualified profiles are provided; increasing
  sequence numbers are not a time/quiescence proof.
- `recovery_pg_init.py`: pure standalone restore-model generation; only fresh
  PGDATA, no `bootstrap-local.sql`, application services, published ports or pulls.
  Do not merge this model into owner compose. Role/extension/client/server native
  qualification remains required before use.
- `recovery_transport.py`: pure invocation plan for upstream age 1.2.1 plus the
  synthetic-tested process wrapper described below. No age binary installed or
  distribution hash asserted; no real age encryption/key read/ciphertext transfer.
  It must not be called a working transport. Distribution verification and
  exhaustive authenticated decrypt-before-restore still need implementation.
  Recipient encryption does not authenticate the exporter. Retained-key custody,
  protected current-PC path/retention and transfer route remain owner decisions.

### Follow-up process-wrapper increment (fix review PASS)

`recovery_transport.encrypt_file` now exercises an argv-only, empty-environment,
SHA-checked direct-child wrapper against a synthetic Python passthrough child.
Initial missing-function test was RED; transport suite is now5/5 zero skips,
including nonzero/timeout/oversize/empty output, denied admission, existing target
and staging collision. New six-suite repetition is28/28 zero skips, with exact
original index entries still preserved (19 staged paths). This does NOT execute
age or establish cryptographic/transfer acceptance. No decrypt/key access occurs.

Output size monitoring is not a hard OS quota; approved private quota-backed
parent, qualified no-descendant binary/version, framing/provenance, retained-key
custody, trusted outer authorization and actual age validation remain required.
Source plaintext is deliberately retained, not claimed cleaned. Initial review
`deleg_f129789c` found whole-stat equality rejecting access-time-only changes.
Parent reproduced RED and now compares dev/inode/mode/nlink/size/mtime_ns at open
and completion. Regression accepts changed atime and rejects changed content or
identity. Fix re-review `deleg_efee5d1e`: PASS, no new findings; independent
transport5/5 zero skips. Parent repeated original90 plus
increment28 =118 tests zero skips; dedicated evidence:
`recovery-test/evidence/offline-transport-wrapper-tests.json`. Earlier continuation
evidence JSON records the preceding114-test reviewed slice, not this increment.

### Queue-drain polling increment (review PASS)

`recovery_queues.wait_drained` adds synthetic-tested polling of complete,
version-bound samples while consumers remain running. Missing-function regression
was RED; queues4/4 and the six increment suites31/31 are now GREEN, zero skips.
Unsupported/missing backend/group/schema, unknown queues, boolean/negative/overflow
counts fail immediately instead of becoming zero. Loop enforces increasing sample
sequence, finite nondecreasing clock, deadline and max-read cap; late zero rejected.

Per-reader timeout and actual producer-block/consumer state are outer-runner duties:
synchronous callbacks cannot be preempted by this helper. A drain success still
requires writer stop plus two stable empty samples before export. Physical probes
and native queue completeness remain unqualified. Review `deleg_2907e9b8`: PASS,
independent queues4/4 plus10 additional checks, no findings;
HEAD/index unchanged,19 staged paths preserved. Latest synthetic evidence:
`recovery-test/evidence/offline-queue-drain-tests.json`.

### Seven-role queue identity qualification subset (review PASS)

The original two-image `speckle`/`n8n` binding is now rejected. Exact keys are
`speckle-server`, `speckle-preview-service`, `speckle-webhook-service`,
`speckle-fileimport-service`, `n8n`, `postgres`, `valkey`. Missing/extra roles and
changed/malformed IDs fail closed; incomplete expected bindings stop before the
attestation callback or reader. Probe/schema hashes are still independently
required; there is no builtin native-qualified profile or physical query.

This is a minimum version-binding subset, **not complete producer discovery**.
The trusted runner must still block/qualify frontend/API/other producers and bind
actual source/destination runtime identity. The existing backend label `redis`
is retained as a logical probe category, not evidence that Valkey is compatible
with an unobserved schema. Current local image metadata alone cannot fill that gap.
`recovery-test/evidence/offline-queue-image-candidates-v1.json` preserves the seven
owner-reported candidate config IDs with exact source-summary hash and separately
returned RepoDigests; probe/schema hashes remain null. It is deliberately not an
admissible binding and grants no runtime permission.

Baseline strict17 suites133/133; after the role-contract change135/135 zero skips,
exit0. Queue6/6 and composed synthetic2/2 also passed separately. Independent
review `deleg_9ddba3c2`: PASS, no security/logic findings; reviewer repeated6+2
synthetic tests with zero skips and verified complete/delta patch round-trips.
Parent checked the saved review/logs and exact reviewed source/patch hashes.
Nonblocking suggestions for explicit swapped-ID and legacy/extra drain cases
remain optional coverage, not unresolved defects. Evidence:
`recovery-test/evidence/offline-queue-seven-role-binding-tests.json`.
No Docker/services/owner data/keys/SQL/queue probes were used. This changes only
unreleased offline preparation, not the completed two-store v3 or issued ZIPs.

### S3 listing pagination increment (fix review PASS)

`recovery_objects.iter_s3_keys` exercises ListObjectsV2-shaped response pagination
using a synthetic client only (no SDK/network). Continuation cycles, duplicate
keys, filtered/encoded pages, malformed truncation/count and page/object caps are
rejected. Missing-function RED became GREEN; objects10/10 and all six increment
suites34/34 zero skips. Normal index entries and HEAD remain unchanged.

This is not full MinIO provider/native acceptance. Approved client endpoint/bucket,
never-versioned feature check, SDK parsing/retry/socket bounds and actual complete
server snapshot remain outer-provider duties. Native SDK auto URL encoding may
need explicit configuration (encoded response rejected, never silently decoded).
Independent review `deleg_8e3dfebf` found accepted nonempty `StartAfter` responses;
parent reproduced RED, then added per-page absent/empty-only guard. Objects10/10
and six suites34/34 repeated GREEN zero skips. Fix re-review `deleg_f244d80f`:
PASS, independent objects10/10 plus16 first/later-page cases; evidence:
`recovery-test/evidence/offline-s3-pagination-tests.json`.

### Common dispatcher increment (review PASS)

`recovery_sequence.run_sequence` preflights exact adapter coverage/callability,
freezes the caller map, then drives the fixed backup/restore order. Missing late
adapters reject before any callback; errors/interruptions stop all later steps.
RED missing-function test became GREEN; sequence7/7 and all six increment
suites37/37 zero skips. No native adapters, approval enforcement, ownership proof,
deadlines or services are wired; this is NOT the trusted outer runner or native
acceptance. Evidence: `recovery-test/evidence/offline-common-dispatcher-tests.json`;
independent review `deleg_caec32fa`: PASS, sequence7/7 zero skips and no findings.
HEAD/index preserved,19 staged paths.

### Composed subset exercise (review PASS)

`recovery_bundle.verify_bundle` read-only verifies exact object+n8n package pair
against independent manifest hashes, before restore mutation. It is NOT the full
five-class checkpoint. New `test_recovery_multistore_offline.py` drives the common
dispatcher with actual synthetic SQLite file/tree and injected object provider,
then checks DB integrity/rows, config bytes, binary data, object metadata/bytes and
source preservation. Schema is a synthetic workflow table, NOT a native n8n DB.
PG init is a pure model check; all unsupported native/crypto/service steps are
explicit synthetic callbacks and are not acceptance. Corrupt object/tree,
missing config key, extra entry and wrong hash stop dispatcher before init/restore.

RED missing verifier then GREEN2/2; six earlier suites repeated37/37 zero skips.
HEAD/index still unchanged,19 staged paths. Native integration remains BLOCKED.
Review `deleg_8f36a7dc`: PASS, composed2/2 zero skips, no findings; full input
`bundle-review.patch` SHA256
`afc3dccd2d8b05c959d2832ad860b39333f8a30d1b72102eccaa8148aad456e8`
in external continuation scratch. No owner data/keys/services/network used.

### Destination restore phases in the latent flow (2026-10-24, review PASS with remarks)

`Invoke-MultiLatentFlow` now continues after the Neo4j load with MinIO `restore-objects`, API
`restore-tree` into `/state` and the n8n restore + verify. The destination starts ONLY storage and
maintenance services (`--no-deps`; no n8n, data-service, Speckle or Neo4j are created there) so its
state volumes stay empty. `multistore_exchange.py restore-tree` fills an EXISTING EMPTY directory
(hidden entries count; `..` is normalised; links, missing, nested and non-empty targets rejected
before any write; failure removes only entries it created). The synthetic n8n key, expected report,
fixture state and decrypted export travel source -> private host output -> destination and are
SHA256-compared on both sides BEFORE restore; the key is the owner-approved synthetic
`ephemeral-exercise-only` key, not custody. Everything is trace/offline tested only; nothing here is
native-qualified. Independent review: PASS with remarks (no blocking logic defect).

Open items found while reviewing (NOT fixed here; each is a model/package change):

1. CLOSED (offline): the `snapshot` service now carries `RECOVERY_S3_*` (endpoint
   `http://speckle-minio:9000`, root credentials by reference, `RECOVERY_S3_ALLOW_HTTP=1`, bucket
   `speckle-source` / `speckle-destination` per side). Model test added; unverified natively.
2. CLOSED (offline): `multistore_native.py create-bucket` creates ONE new bucket (body-less PUT, no
   LocationConstraint; existing bucket = HTTP 409 = fail closed) and then runs the normal private /
   never-versioned `bucket_check`; the orchestrator calls it before `restore-objects`. Tested against
   the signed-wire fake only; real MinIO bucket-create/ACL behaviour is unverified.
3. `native.checked_directory` requires owner = euid and no group/other bits; a fresh Docker volume
   root is usually 0755, so `restore-tree` into `/state` (and `tree --source /state`) may refuse.
4. `n8n-fixture/fixture-state.json` and `reports/n8n-decrypted-source.json` are consumed but nothing
   in the flow produces them before the n8n snapshot.
5. Staged key/expected/decrypted files stay in the host private output directory after cleanup.
6. `transfer_tree` still uses `Path.absolute()` (no `..` normalisation); only `restore_tree` was fixed.

## Repeatable strict offline verification

From repository root with the existing Python3.13 toolchain:

```text
python3 -B deploy/hosted/verify_multistore_offline.py
```

Fixed17-suite allowlist, max90s per child/max600s total; rejects missing/duplicate
summary, zero tests, discovered/run mismatch, skips, failures and child nonzero.
No wildcard native discovery. Parent executed actual CLI exit0,132/132 zero skips;
JSON labels the result offline-only and lists exclusions. Native integration and
known legacy archive skip are EXCLUDED/OPEN, not converted to PASS. No source
exports, Docker/services/owner data/keys are accessed by this command.

Verifier implemented RED→GREEN; self-tests3/3. Independent CLI review
`deleg_f1e39444`: PASS, self-tests3/3 zero skips; reviewer did not repeat all17
suites. Exact HEAD/index preserved,19 staged paths; no commit/push.

## Pristine PostgreSQL catalog declaration (review PASS)

`recovery_pg_init.admit_pristine_catalog` rejects wrong version/database/role/owner,
nondefault schema/extension declarations, user objects, other sessions or prepared
transactions, and bool-as-int counters. RED missing function then GREEN PG-init2/2;
full repeatable offline command now133/133 zero skips, exit0. Evidence:
`recovery-test/evidence/offline-strict-verification-tests.json`.

This is declaration validation, not SQL enumeration or runtime restore permission.
No PostgreSQL process/connection was invoked. A qualified catalog probe must cover
all user-owned objects (not just tables), bind actual target identity/ownership
and prevent concurrent clients; native clean PG restore remains BLOCKED. Review
`deleg_946d923e`: PASS, independent PG-init2/2 zero skips; exact review patch
matched both files. HEAD/index unchanged;19 staged paths preserved.

Parent strict verification: original nine recovery suites **90/90**, six new suites
**24/24** (4+10+7+1+1+1), failures/errors/skips zero. Regression fixes reproduced before
correction: reentrant ordering bypass; n8n external-DB config admission; n8n/object
staging-name collision deleting pre-existing tree; cleanup errors exposing private
exception text. Staging is owned only after successful exclusive creation; partial
cleanup failure rejects the operation and must not be reported as cleanup success.
Independent review `deleg_86832dd2` found metadata-dict aliasing and eager n8n
directory enumeration. Parent reproduced both RED, snapshots metadata before stream
reads and now bounds `os.scandir` consumption before sorting. Python3.13
`Path.iterdir` itself eagerly materializes entries, so a second OS-consumption
regression was also RED before the `scandir` fix. Focused17/17 and all six new
suites24/24 pass. Independent fix re-review `deleg_062216bb`: PASS, no security/
logic findings or suggestions; reviewer reran objects7+n8n10 zero skips. This is
not native acceptance. Prior
180/180 is historical: the other 90 image/build/evidence checks were not repeated
in this increment. Legacy archive skip remains open. HEAD `535eb30` and the exact
normal-index entries (19 staged paths) were verified unchanged. No commit/push.

## Working artifact

`recovery_checkpoint.py` reads a previously exported directory. It verifies strict declaration shape, exact revision and recipient fingerprint supplied independently, distinct synthetic project identities, fixed image config-ID syntax, stopped-writer declarations, zero queue declarations in BOTH Redis and PostgreSQL, required escrow-reference labels, complete five-class file inventory, file sizes/SHA256 and unsafe path/link rejection. It streams file hashing in <=1 MiB chunks (64 GiB total/4096 entries/1 MiB JSON bounds). No Docker, services, network, key generation, export, restore or file writes.

CLI: `python3 -B deploy/hosted/recovery_checkpoint.py --export-directory <synthetic-export> --revision <40-hex> --recipient-fingerprint <64-hex>`.

Success is **OFFLINE_CHECKPOINT_VALIDATED_NOT_RECOVERY**, with `nativeRecoveryProven`, `offMachineRestoreProven`, `releaseAccepted` all false. Exit 0 means only that these checks passed. A hand-written declaration with internally consistent bogus native dump bytes can pass; the tool cannot recognize native formats or independently prove quiescence, queue discovery, complete object metadata/versions, escrow availability, recipient ownership, or restore. It MUST NOT gate real mutation or generate `export-complete.json` by itself. Hashes do not authenticate the exporter. Image config IDs are not registry digests.

Schema v2 (unreleased preparation; v1 aggregate queue declaration rejected) is a deliberately strict synthetic producer contract in the implementation/tests, NOT the old encrypted archive schema. Root marker `export-checkpoint.json`; exact five directories `neo4j/`, `postgres/`, `objects/`, `n8n/`, `api/`; every regular file individually listed with `bytes`/`sha256`, no extras, links or reparse points. Empty files are supported. Stored secret material belongs inside the later encrypted protected export; this JSON carries only opaque `escrow:...` references, never actual values. It is not an exhaustive secret scanner. Trusted local filesystem/no hostile concurrent mutation is assumed. No plaintext production export should be fed into this preparation exercise.

Required stop declarations: data-service, dg-reasoner, n8n, speckle-server, speckle-frontend-2, speckle-preview-service, speckle-webhook-service, speckle-fileimport-service, neo4j. This conservative schema stops n8n and Neo4j completely and admits only declared empty Redis state that is NOT replayed. Pending/active/retry or scheduled jobs are not silently dropped. Counters are declarations until a version-specific producer demonstrates actual queue enumeration. Schema v2 requires six separate logical groups: previewRequest and previewResponse (waiting/active/delayed); fileImport (queued/processing/retry); webhook (pending/processing/retry); legacyUpload (pending/processing); n8nExecution (new/running/waiting). Every counter is an exact integer zero. These are required recovery categories, NOT asserted physical table/key/status names. Unknown schemas and unexamined queues must block the producer, never become zeroes. First block new producers, drain with consumers running, then stop all writers and repeat a stable read; stopping consumers alone does not drain jobs.

## PostgreSQL helper — offline exercised, native qualification pending

`recovery_postgres.py` provides a module-only export/restore adapter and read-only integrity CLI. Export uses exclusive private output, bounded streaming/hash, fixed pg_dump custom arguments, timeout/own-partial cleanup. Restore checks file/hash before attestation and rehashes afterwards before pg_restore with single transaction/exit-on-error. Mutations require a trusted outer-runner callback proving authorized scope, actual source/destination mapping, empty owned destination, pinned versions, protected scratch and quiescence. This callback is not implemented by the helper and cannot be replaced by a user-supplied true flag. Names/hashes do not establish ownership or safe SQL provenance. All reports keep nativeRecoveryProven=false.

Parent verification reproduced and fixed three classes beyond the child implementation: official Alpine binary install-prefix mismatch (/usr/local/bin, not Debian /usr/lib/postgresql/16/bin), interrupted export retaining plaintext, and Windows timestamp-cached mutation after attestation (now second full hash). NTFS named streams were reproduced as unlisted content in checkpoint and PostgreSQL input/output paths; shared recovery_filesystem.py rejects streams on files, marker, directories/ancestors and explicit stream destinations. No hostile concurrent mutation guarantee, no non-Windows xattr coverage, no Windows ACL certification.

CLI `python3 -B deploy/hosted/recovery_postgres.py --archive <synthetic-file> --expected-sha256 <64-hex>` is read-only and refuses mutation flags. Offline tests use disposable Python processes in place of native binaries; real pg_dump/pg_restore, role/migration ordering and clean database restore are untested. No executable full multi-store runner/package has been issued. Independent review deleg_119a1570 reproduced reader-start process leakage and checkpoint CLI argument echo. Parent reproduced RED, extended process cleanup across reader setup and sanitized parser errors; all90 tests now pass. Native qualification remains pending.

## Runtime mechanisms that remain to implement and exercise

| Class | Required mechanism | Important boundary |
|---|---|---|
| Neo4j | Existing proven native offline dump/load pattern | Exact image/plugin identity; source writers and DB stopped |
| PostgreSQL | Native custom pg_dump and clean pg_restore | Role/config dependencies; version and all Speckle job tables must be identified |
| MinIO/S3 | Object bytes + metadata + bucket policy/config/version disposition | A volume tar or successful object GET alone does not prove coverage; reconcile DB references |
| Valkey/Redis | Enumerate all supported job queues, drain to zero, restore empty | Redis DB size alone is not a queue proof; PostgreSQL file-import queues also exist |
| n8n 2.4.8 | Stop executions, complete quiesced .n8n state including SQLite sidecars/config/binary data | Workflow JSON alone omits credentials/users/execution data and key; no activation on destination |
| API | Existing proven entire quiesced /app/data tree | Exactly one worker/replica; secret/settings key must match |

The four earlier custom image archives do not establish identities of PostgreSQL/MinIO/Valkey/Speckle/n8n images needed for the full test. Current base has floating MinIO/Speckle tags. No pull/build/inventory inspection of an existing owner stack is implied.

## Audited version boundaries and cold-start hazards

Repository evidence (parent-read): `docker-compose.yml:167-199` selects PostgreSQL16.4/Valkey8.1 by tags and floating MinIO; `201-310` selects floating Speckle images. `233-234` enables next-gen PostgreSQL fileimport; `272-297` supplies PostgreSQL to webhook/import workers. Thus Redis-only drain cannot establish consistency. Parent independently fetched the following exact public source blobs, without service calls:

- [Speckle preview queue](https://github.com/specklesystems/speckle-server/blob/51d43b91c4681a75bff8b285da7f443a4599da67/packages/server/modules/previews/queues/previews.ts#L72): drain count includes waiting + active + delayed.
- [Speckle webhook worker](https://github.com/specklesystems/speckle-server/blob/51d43b91c4681a75bff8b285da7f443a4599da67/packages/webhook-service/src/main.js#L16-L29): `webhooks_events` PostgreSQL pending0 → processing1, later success2/failure3. These status numbers are not installed as target assumptions.
- [Speckle fileimport queue](https://github.com/specklesystems/speckle-server/blob/51d43b91c4681a75bff8b285da7f443a4599da67/packages/server/modules/fileuploads/queues/fileimports.ts#L51): queue shutdown is a no-op, not drain proof.
- [n8n exact 2.4.8 source](https://github.com/n8n-io/n8n/blob/e040ab67e5acf63df4438a7f9352ab91cd43ccc4/packages/%40n8n/config/src/configs/database.config.ts#L135-L167): SQLite default, pool3, WAL enabled by default; full stopped state and matching config/encryption key required, not workflow-only export. Repo compose does not explicitly set DB_TYPE/EXECUTIONS_MODE/N8N_ENCRYPTION_KEY; no inference that Speckle PostgreSQL/Valkey serves n8n.

The audited Speckle commit is **NOT bound to the floating target images**. Physical schemas/queue names and version-specific probes remain unresolved. The six logical queue groups in schema2 are a minimum declaration contract, not a runtime query implementation or proof that no other job categories exist.

`docker-compose.yml:177` mounts `speckle/bootstrap-local.sql` into first-init PostgreSQL. Parent read `speckle/bootstrap-local.sql:1-17`: INSERTs reference scopes/server_apps_scopes/token_scopes/user_server_app_tokens without creating tables. A virgin restore project must omit that application bootstrap until restored schema exists; existing-volume startup cannot prove cold-start safety. Do not change the owner's base compose to work around a restore-only initialization problem. Prepare a new isolated restore model with clean PostgreSQL init, perform native restore before application startup, then explicitly validate post-restore migrations/role configuration.

MinIO mechanism stays unresolved: do not assume `mc mirror` preserves version history/metadata or `mc replicate export` exports objects (it exports rules). A first synthetic unversioned-bucket qualification would be a declared limitation, not a production version-aware backup. Pin MinIO and helper first, inspect supported API/version metadata semantics and verify every seeded object/metadata field against PostgreSQL references.

## Retained-key and current-PC transfer contract (not provisioned)

- Use a reviewed streaming authenticated-encryption tool for full exports, not expanded custom crypto or the legacy 8 MiB in-memory prototype. Pin and verify its distribution before packaging; currently none selected/installed.
- Encryption recipient public fingerprint is independently approved. The private recipient key stays in owner-controlled protected custody, never chat/repo/report or beside ciphertext. A target-generated ephemeral discarded key is insufficient for operational recovery.
- Include the exact n8n encryption key/config, LLM master secret and required DB/object/service identities in an approved protected key-escrow mechanism. A reference label alone proves nothing. Verify decrypt/mismatch failure before destination creation; do not silently regenerate keys.
- Only ciphertext travels to the selected current PC; exact protected directory, retention and transfer route are still owner gates. Verify hash on both endpoints; preserve original reports and immediately saved process exits. This is not yet off-machine evidence.
- No completion marker until native exports, inventory, encryption, transferred-ciphertext verification and cleanup have succeeded. Do not modify the previous v3 package or output.

## Validation performed

RED: new test failed with the targeted absent-checkpoint assertion before implementation. Added empty-file and hardlink regressions failed before their fixes. GREEN: strict `test_recovery_checkpoint.py` initially **10/10, zero skips**, including real NTFS hardlink and junction rejection, corruption, absent store/key reference, PostgreSQL active jobs, bool-as-int, duplicate JSON keys, bounds, non-echoing CLI rejection and real CLI success. Probe **17/17** and two-store snapshot **20/20** regression tests also passed. These are offline synthetic checks only; legacy archive symlink skip remains unchanged. No services/daemon/deployment/commit/push or owner data/key access. After the queue audit, aggregate-zero rejection regression was RED before the schema-v2 correction; checkpoint now **12/12**, with every group missing and all 17 counters independently tested against positive/negative/bool/string/null values. Seven two-store strict suites rerun **56/56** with zero skips; total **68/68** offline. Legacy archive suite is excluded and its previous skip is not hidden. Latest parent run after NTFS/path/interruption/hash fixes: checkpoint14 + PostgreSQL20 + seven two-store suites56 = **90/90**, zero skips, all exits0. Actual local run summaries retained at `recovery-test/evidence/offline-multistore-preparation-tests.json`; this is agent-observed offline evidence, NOT a native runtime report.
