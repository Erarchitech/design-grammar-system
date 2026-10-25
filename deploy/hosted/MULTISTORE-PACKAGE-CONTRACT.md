# Full-multistore candidate package contract v2

This is a technical package contract, not a roadmap or runtime approval.
Framework `.planning/` retains HOST-02/HOST-04 ownership. Two-store recovery v3
and previously issued archives/evidence are unchanged.

## Required inputs and membership

`build_multistore_package.py` emits `multistore-manifest.json` schemaVersion 2.
The Python exact-input verifier and self-contained PowerShell 5.1 bootstrap
accept the new exact member set; the bootstrap rejects the old schema rather
than silently upgrading it. Source remains 187 exact Git blobs with the existing
product/preparation revisions and source-manifest hash.

The ten `AGE_FILES` inputs remain mandatory and retain their existing SHA256:
six Linux/Windows executable/license files plus `CONTRACT.md`,
`signature-verification.json`, `download-provenance.json`, `extracted-tools.json`.
No nullable pin or verification-bypass flag is provided. The bootstrap carries
these same fixed pins independently of the package's manifest declarations.
A rehashed changed binary/provenance record still fails preflight.

The full mutable GitHub API snapshot `github-release-v1.2.1.json` is no longer a
package input or member. Fresh API observations may be retained separately with
their acquisition evidence, but are never presented as the lost historical
snapshot. Presence or absence of that filename in the external input directory
does not change package bytes. Adding it to the ZIP, even with recomputed
manifest hashes, is rejected by both verifiers.

## Current inventory versus historical evidence

The builder generates a new `provenance/age/delivery-manifest.json` containing:

- schemaVersion 2;
- kind `current-package-age-inputs-not-historical-delivery`;
- verificationEvidence `historical-pinned-report-not-reverified`;
- `files`: the exact ten package-member names and SHA256 values of the pinned
  age inputs, excluding the generated inventory itself.

The old recovered delivery manifest remains external and unchanged. It is not
read, rewritten or repackaged as a current inventory. The new inventory has no
machine-local paths, timestamps, test/release approval or missing API dependency.
Its hash is covered by both outer manifest maps and the independently supplied
ZIP hash; PowerShell additionally checks its exact fields and fixed pin map.

`ageTrust.verificationEvidence` explicitly labels the preserved signature report
as historical, not a fresh cryptographic check. The publisher-signature Boolean
refers only to that pinned report. No signature verification is rerun by this
package change; Sigsum log/witness quorum remains unverified. No bundled age
executable is run by package construction or default integrity preflight.

## Admission remains blocked

`prepare()` still requires an independently reviewed coherent runtime profile.
Offline tests call the raw ZIP writer for labelled lifecycle fixtures only.
Default PowerShell mode checks integrity without Docker or importing runtime
support; native mode still requires separate external approval and queue/profile
qualification. An offline PASS is not native recovery, release, freeze or staging
acceptance. New runtime, tool execution, image/service operation and commit/push
permissions are not implied by this contract.

## Verification

With the existing Python 3.13 and Windows PowerShell 5.1:

`python3 -B deploy/hosted/tests/run_required.py test_multistore_package.py`

The strict runner rejects failures, errors, skips and zero discovery. Coverage
includes deterministic assembly without either historical metadata file, exact
Python verification, actual extracted PowerShell preflight, changed/missing age
inputs, rehashed binary/provenance/inventory tampering, false fresh-evidence
labels, old schema, extra API member, ZIP/extraction safety and unchanged
production admission refusal. These are offline synthetic/lifecycle checks,
not full-runner or native transport qualification.
