# Read-only image observation — issued candidate only

`Collect-ImageInventory.ps1` is a standalone companion, **not a replacement for
Run-BundleTest.ps1**. Keep it outside the extracted package; do not repackage or
edit the issued ZIP. It does not run the capability test again.

## Identity and scope

The collector accepts only these compiled-in pins:

- Original ZIP SHA256: `1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e`
- Framework revision: `2dedbfb3e138c2b437e781696197105dca93342a`
- Candidate manifest SHA256: `864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810`

Before any Docker call it verifies the ZIP hash, ZIP member hashes, extracted
member hashes including both manifests, candidate membership, absence of extra
files and linked paths. Use a clean extraction, not a directory containing prior
reports or `.env`. The collector never loads `.env` and never invokes Compose.

The authenticated **bundle-test `compose.json`** selects exactly:

| Service | Local image reference |
|---|---|
| neo4j | `dg-hosted-1309-sandbox-neo4j:latest` |
| data-service | `dg-hosted-1309-sandbox-data-service:latest` |
| n8n | `n8nio/n8n:2.4.8` |

The first two are implicit Compose build names derived from the original runner's
fixed project `dg-hosted-1309-sandbox`, not registry-pinned release images. No
production/full hosted-stack inventory is attempted.

## Offline preflight (no Docker, any machine)

Example paths below are placeholders for the operator's actual existing paths.
The report parent must exist and the output file must not exist.

```powershell
powershell.exe -NoProfile -NonInteractive -File C:\DG-tools\Collect-ImageInventory.ps1 `
  -PackageZip C:\DG-input\DG-candidate-test-2dedbfb-DESKTOP-OS4Q8CP.zip `
  -PackageRoot C:\DG-input\candidate-test-extracted `
  -ReportPath C:\DG-reports\inventory-preflight-001.json -PreflightOnly
$LASTEXITCODE
```

Expected: `PREFLIGHT_ONLY`, `dockerInvoked=false`, exit 0, no observed images.
This means file checks only, not image availability or runtime acceptance.

## Owner-run observation — scope authorized

The owner answered «Разрешаю» to the explicit request for a read-only three-image inventory on `DESKTOP-OS4Q8CP` in this conversation. This authorizes manual execution of this collector only: three image-inspect requests, no pull/build/run/removal, no replay of the earlier capability test, and no operations on the development PC. It does not authorize commit/push, recovery, deployment or release acceptance.

Only on **DESKTOP-OS4Q8CP**, omit `-PreflightOnly` and choose a **different new**
external report filename. Do not run this mode on the developer machine.

The only native commands permitted by the collector are three bounded
`docker.exe --host npipe:////./pipe/docker_engine image inspect --format ...`
requests, one per exact image above. The format requests **only** `Id`,
`RepoDigests`, `Os`, `Architecture`. There are no pulls, builds, container runs,
up/down, network/volume operations, config/context inspections or log reads.
Endpoint/config/TLS/API environment overrides are rejected, never printed;
there is no endpoint or host override parameter. Native stderr is discarded.

Outputs contain fixed metadata plus validated image fields; they do not contain
native stdout, exceptions, paths, env, labels, container config or logs. Report
creation uses `FileMode.CreateNew`; existing files are never overwritten.

## Interpretation / return codes

- Exit **0**, `PREFLIGHT_ONLY`: file preflight only.
- Exit **0**, `OBSERVED_NOW`: all three current local images had valid fields and
  nonempty registry RepoDigests. **Not release PASS.**
- Exit **2**, `UNRESOLVED`: at least one missing/unreadable image, malformed
  inspection, or missing registry digest. Other valid observations are retained.
- Exit **1**, `BLOCKED`: identity/path/host failure, or report write failure.
  A report cannot be created when its path is unsafe or already exists. A write
  failure may leave an incomplete new file; exit code remains authoritative.

`localConfigImageId` is Docker's **config SHA256 ID**, not a registry manifest
RepoDigest. `registryRepoDigests` is never filled from that ID. Local builds
commonly have no RepoDigests: this remains `UNRESOLVED_REGISTRY_DIGEST`, not a
reason to pull, push, rebuild or invent provenance.

These are **observations at collection time only**. Tags can change. Cached
images do not establish which images were used by the earlier owner-run PASS.
`historicalRunImageBinding` and `buildProvenance` stay `not-established`;
`releaseAcceptance` and `fullStackInventory` stay false even if all three have
RepoDigests. No freeze/release or full-stack gate is closed by this report.

## Offline checks

```text
python deploy/hosted/tests/run_required.py test_image_inventory.py
```

Requires real Windows PowerShell (or PowerShell), and the issued ZIP in Downloads
or located by `DG_IMAGE_INVENTORY_PACKAGE`. Tests fail rather than silently skip
if either is missing. They parse actual PowerShell, execute the real no-Docker
preflight and negative paths, and test the pure argument/sanitizer functions with
explicitly synthetic data; those fixtures are **not collected image evidence**.
All temporary extractions/reports live under Hermes scratch and are cleaned up.
No Docker executable is invoked by this test suite.
