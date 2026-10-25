# Multi-store identity inventory — read-only, not recovery

Scope approved by owner: local image/config IDs, RepoDigests, Docker client/server
and Compose versions on physical target DESKTOP-OS4Q8CP. No data export, containers,
volumes, environment, credentials, SQL, queues or runtime image versions inspected.
This first inventory cannot determine queue/catalog schema or native tool versions
inside images. Config ID is not a registry digest or historical-run provenance.

## Safety boundaries

- Explicit local Windows named-pipe Docker endpoint only; no remote connection.
- Fixed Docker Desktop executable path; report records executable SHA256.
- Schema3 uses empty config for version/images, a separate private Compose config
  with only the fixed cliPluginsExtraDirs, and a cleared child environment. Owner's
  Docker config is not loaded. No login/pull or registry access. Installed Docker/Compose code
  must be trusted; observed digest metadata is a local declaration, not provenance.
- Fixed12 image references from current offline candidate/base Compose, including
  floating tags. Missing image/daemon/version produces UNRESOLVED, not auto-start.
- No container inspect/exec, start/stop/build/pull/export/restore/cleanup of services.
- Collector writes ONLY a new report, owned temporary config directories and one
  config.json beside it; deletes only its known file and owned empty directories,
  never recursively. Report must
  be in an existing private local NTFS directory, not shared/cloud-synced/untrusted.
- Per CLI call10s plus bounded stream waits/cleanup, overall240s admission. Native
  stdout capture is time-limited, not hard memory quota; trusted local CLI required.
- PreflightOnly validates output/collector behavior without invoking Docker.
- Do not launch Docker Desktop without separate owner startup-risk approval.
  Starting it may autostart containers; an observation permission alone is not
  permission for startup. No schema3 target run/startup is currently approved.

## Manual target command (only after exact package review AND target approval)

No admin elevation needed. Use Windows PowerShell in a freshly extracted private
folder. Do not run inside the development repository. The packaged collector must
match the supplied manifest/hash before execution.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\Collect-MultiStoreInventory.ps1 -ReportPath "$PWD\inventory.json"
$inventoryExit = $LASTEXITCODE
Write-Output "Inventory exit: $inventoryExit"
```

Every manual run requires a separate bounded approval. Use a new ReportPath for
another approved attempt; existing files are never overwritten.
Exit0=OBSERVED_NOW (all requested metadata observed), exit2=UNRESOLVED (report still
useful), exit1=BLOCKED/error. No status is recovery PASS. Return inventory.json and
the recorded exit only; never send Docker raw outputs/config/.env/full inspect.
Parent will validate field types/schema and reconcile observations before native
adapter work. Expanded native test still requires a separate package and approval.

## Latest checkpoint — owner inventory v4, 2026-10-18

Owner-returned schema3 report is OBSERVED_NOW / exit0 at
2026-10-18T11:20:12.1329249Z. The exact fixed12 references, config-ID/digest syntax,
linux/amd64 platforms and accepted tool hash pair were reconciled offline.
Docker client/server29.8.2 and Compose5.6.0 are reported runtime observations under
the new pair, not merely file-resource metadata. Evidence is a labelled
chat-supplied summary, NOT an independently witnessed target run:
`evidence/multistore-inventory-v4-owner-observation.json`.

The ONE v4 target permission is consumed. No retry, daemon startup/shutdown,
container command, data/schema access or recovery is now authorized. This closes
only the fixed current-image/tool metadata observation gate, not registry/source
provenance, historical two-store binding or the full stack/native recovery gates.
Detailed identity-update and v4 disposition follows the historical entries below.

## Historical checkpoints

Issued v1 source review `deleg_ef0cd9a8`: PASS4/4; exact ZIP review
`deleg_7307a0ac`: PASS. The issued ZIP remains unchanged.
Owner supplied v1 UNRESOLVED/exit2 report: all12 image inspections, combined
client/server version and Compose version unresolved; executable hash observed,
not image identities. Owner confirmed Docker was stopped. This explains unavailable
daemon observations; Compose failure cause is still unknown. No auto-start or pull.

SchemaVersion2 was issued as the immutable v2 ZIP after exact-package review
`deleg_bc8abd1e` PASS, SHA256
`2d2a5978965a6bec3b03bedc37dce3725303ebd362c90f9e4ce7769932a10424`.
Owner authorized and completed one manual diagnostic run with Docker remaining OFF.
Sanitized per-request diagnostics include phase, started/timeout flags, exit code,
elapsed milliseconds, output counts
and a fixed error category. No raw outputs, paths, exception messages or environment
values are published. Child environment/commands unchanged; no speculative home or
plugin fallback. Classifications are hints, not proof of root cause. ReadToEndAsync
still captures trusted CLI output in memory; this is not a hard output quota.

Offline strict tests8/8, including full synthetic executable success/failure and
actual synthetic timeout, zero skips. Independent schema2 review
`deleg_1fc283ae`: PASS8/8, zero failures/errors/skips; no blocking findings.
Full17-suite baseline repeated133/133 PASS. Earlier concurrent run had one composed
suite error, not reproduced in isolated2/2 or full repeat; cause remains unknown.
Owner-returned v2 report (2026-10-17T07:02:13.4979814Z), exit2: version and all12
image commands exited1/LOCAL_ENDPOINT_UNAVAILABLE, consistent with stopped daemon.
Compose exited125/UNCLASSIFIED, stdout0/stderr107 chars, no timeout. Failure is at
CLI EXIT, not report/schema parsing; exact Compose cause remains unknown. Missing
plugin, plugin discovery under isolated env and unsupported invocation are hypotheses,
not established facts. No image IDs observed. See evidence/multistore-inventory-v2-owner-observation.json
for a labelled summary of user-supplied facts (not a saved original report).
The one-run permission is consumed. Any further target command or Docker startup
requires a separate decision. Native recovery/image bindings/queue schemas stay open.

### Compose discovery comparison — owner returned 2026-10-18

Separate one-run Compose-only and then A/B permissions were granted and consumed.
A/B exact ZIP review `deleg_33d1d438`: PASS6/6, extracted preflight exit0/no Docker.
Owner returned COMPARISON_COMPLETE / exit0 at 2026-10-18T07:28:03.8078134Z,
Docker OFF owner-stated/not probed, exactly two top-level CLI launches:

| Private config | Compose version | Exit | Category |
|---|---|---|---|
| Empty | unresolved | 125 | CLI_ARGUMENT_REJECTED |
| Explicit fixed plugin directory | 5.0.1 | 0 | VERSION_OBSERVED |

Both CLI and plugin hashes matched the approved observations. For these bytes and
isolated environment, explicit cliPluginsExtraDirs enabled discovery; --short
works once discovery succeeds. Exact internal fallback/error text was not collected.
This is not evidence that the installation is broken, nor native recovery or
release acceptance. Docker CLI client/server version and image identities remain
unobserved. See evidence/compose-discovery-ab-v1-owner-observation.json (labelled
chat-supplied summary, not original report file).

Offline source candidate schema3 now uses a separate fresh private Compose config
with only cliPluginsExtraDirs for the fixed hash-bound installed plugin directory.
Version/images retain empty config. No owner config/env/data reads are added. Both
CLI/plugin hashes are pinned; mismatch/missing plugin blocks before CLI launch.
Only collector-owned config files/directories are cleaned; prior issued ZIPs are
unchanged. This source change is not a new target execution permission or proof
of image identities. No further target command or daemon startup is authorized.

Schema3 independent source review `deleg_15d8a26d`: PASS9/9, zero failures/errors/
skips, no blocking findings. Parent rechecked exact reviewed source/patch hashes
and unchanged HEAD/index. Separate fixed17 recovery baseline: 133/133 PASS.
Evidence: evidence/multistore-inventory-schema3-offline.json. Explicit synthetic
assertions for seeded owner-like environment variables/working directory remain a
nonblocking test-hardening suggestion; do not claim that runtime assertion exists.
At that source-review checkpoint no schema3 ZIP existed. Source review alone
is not exact-package review.

### Inventory v3 package — reviewed, awaiting target approval

The nonblocking environment/cwd suggestion is now addressed with full compiled
synthetic-child assertions and deliberately broken scratch-only isolation mutants.
Unchanged production collector; strengthened strict tests still9/9, zero skips.
Independent source/test-hardening AND exact ZIP review `deleg_88629524`: PASS9/9,
no findings; independent extracted preflight exit0/schema3/dockerInvoked=false.

New immutable ZIP DG-multistore-inventory-535eb30-v3.zip, 7824 bytes, SHA256
`a6834dc1de9a78ea8680027953bf4458c483b167d83c58223eaa74b14a5716f4`.
Exactly collector/README/manifest; CRC, hashes and source equality rechecked after
review. HEAD and exact original staged entries remain unchanged. All older issued
archives remain immutable. Evidence: evidence/multistore-inventory-v3-package.json.

README and manifest explicitly separate preparation from permission. Target
startup and one bounded inventory are NOT yet authorized. Proposed next scope is
owner-manual Docker startup on DESKTOP-OS4Q8CP with disclosed restart-policy
container-autostart risk, then ONE read-only collector run (maximum14 top-level
CLI launches: version, Compose version, 12 local image projections). No registry
request, container inspection/exec, SQL, queue/data/key reads, pull or recovery.
No actual Docker/service execution occurred on the development PC.

### Inventory v3 owner result — BLOCKED at CLI identity continuity

Owner subsequently selected option1, approving manual target Docker startup with
restart-policy autostart risk and ONE v3 run. That manual run is now consumed.
Owner returned schema3 BLOCKED / exit1, failureStage tool-guard, dockerInvoked=false,
observedAtUtc=null, empty images/diagnostics. Observed docker.exe SHA256:
`6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896`,
not approved pin
`70c9fbdfb6318c2aa910581cdbe1cf4237a600177cabedcd83e95f1dac7f5db5`.
Get-InventoryPlugin checks that pin first, before plugin hashing or any CLI launch.
This explains the fail-closed guard; no plugin hash, versions or image identities
were collected. Update/repair/other change cause and current daemon state are not
established by this report. The old Compose5.0.1 observation remains historical
for the previous hashes; it does not qualify the changed CLI.

See evidence/multistore-inventory-v3-owner-observation.json (chat-supplied summary).
No automatic hash replacement, rerun, new startup, container inspection or recovery
is authorized. Ask for owner knowledge of an update/change before proposing a
new bounded identity observation. Preserve original ZIP/source pins unchanged.

### Update, file-only identity and inventory v4 — owner returned 2026-10-18

Owner confirmed an installation update. A separately approved file-only collector
was exact-ZIP reviewed (`deleg_75e10cf9` PASS3/3), then returned FILES_OBSERVED /
exit0 at 2026-10-18T10:45:01.0309056Z: zero native commands, new CLI SHA256
`6c699720bb9523dedb9eb5d22a49951ea9210dbdb1314a3554029eee9be76896`,
44829104 bytes, FileVersion/ProductVersion29.8.2; new Compose plugin SHA256
`e6176502e836a7fee8d71cab5fcda736c8dacc79ccefdf9659af977f7eae2375`,
33362864 bytes, version resources absent or rejected by the allowlist. Null file
metadata was not interpreted as a broken plugin. File-only permission consumed;
these observations did not themselves approve new pins or runtime execution.

A new candidate v4 changed only both production pins, kept schema3/config/env/cwd
behavior and retained old issued archives. RED old/mixed-identity regression then
GREEN10/10 strict tests; only new/new accepted. Independent source AND exact ZIP
review `deleg_ab790ce4`: PASS10/10, no findings, extracted preflight exit0/no Docker.
ZIP DG-multistore-inventory-535eb30-v4.zip,7967 bytes,SHA256
`6b96d215107bd4fb581858265d2e27e8e78866ded95e091d8d2eff04066b3591`.

Owner chose option1: accept the new pair and ONE inventory with the already-running
target daemon; NO startup/shutdown permission. Returned OBSERVED_NOW / exit0 at
2026-10-18T11:20:12.1329249Z, Docker client/server29.8.2, Compose5.6.0, explicit
plugin-directory discovery, accepted tool hashes and all12 fixed image references.
All12 have linux/amd64, syntactically valid IDs and one RepoDigest each, no duplicate
references, no diagnostics or failure stage. Parent reconciled counts, exact list,
platforms and hash binding in code; no target command was repeated.

Every reported RepoDigest suffix equals its image configId field. Preserve both
as returned, do not derive one from the other or treat equality as registry lookup,
image-manifest verification or source provenance. Collector projects .Id and
.RepoDigests separately. Current local metadata is NOT historical two-store image
binding; floating tags are not semantic application versions. Queue/catalog
schemas, versions inside images and complete stack inventory remain unobserved.
The new Compose5.6.0 result qualifies discovery for this new pair/environment;
old Compose5.0.1 remains historical evidence for its old pair.

Evidence: labelled chat summaries `evidence/docker-file-identity-v1-owner-observation.json`
and `evidence/multistore-inventory-v4-owner-observation.json`; approval/review and
consumed permission in `evidence/multistore-inventory-v4-package.json`. No original
report file or independent target attestation claimed. No current target invocation,
service change or retry permission remains. Two-store PASS is not repeated; native
PG/MinIO/n8n recovery, HOST-04, actual retained-key encryption/off-machine restore
and release/freeze remain open. Next native work needs a separately reviewed,
version-bound harness and explicit bounded owner approval; dev Docker stays forbidden.

