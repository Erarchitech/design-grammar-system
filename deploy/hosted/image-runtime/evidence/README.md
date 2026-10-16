# Four-image owner smoke evidence — report checks matched, process exit unknown

`c82b92b-v2-owner-smoke-report.json` is a manual transcription of the owner's chat JSON, **not the original target file**, a signature or an independently observed run. Its SHA-256 describes this transcription only. The target timestamp was not provided. The target is contextual owner-run `DESKTOP-OS4Q8CP`; it is not a field in the returned report.

Owner returned `LOAD_AND_ISOLATED_SMOKE_COMPLETE`, all four image identities, readiness, bounded synthetic API/UI/reasoner checks, verified project/volume cleanup and retained images/TAR. The first v2 failure was daemon-preflight with Docker not running according to the owner; the later completed report supersedes that attempt only for these checks. After the completed run `$LASTEXITCODE` printed nothing. **Process exit is unknown, never inferred to be zero.** Do not rerun a mutating smoke merely to recover it.

`c82b92b-v2-disposition.json` is actual output of the offline reconciler against the issued ZIP. It binds the entire report with typed JSON comparison, package SHA, source manifest/revision, all image IDs and member hashes. It preserves `evidenceComplete=false`, `processExitCode=null`, `releaseAccepted=false`. This does not erase successful semantic report checks.

Reproduce locally (no Docker):

```text
python deploy/hosted/reconcile_image_runtime.py --report deploy/hosted/image-runtime/evidence/c82b92b-v2-owner-smoke-report.json --zip C:/Users/Admin/Downloads/DG-image-runtime-c82b92b-v2.zip --exit-unknown
python -B deploy/hosted/tests/run_required.py test_image_runtime_evidence.py
```

The reconciler exits **2 by design** for a matching report with unknown process exit; malformed/mismatched evidence returns 1, a matching report with an actually supplied observed exit zero returns 0. Do not supply `--exit-code 0` for this historical run. Exit 2 is not the owner's runtime exit code.

No n8n, Speckle, HTTPS/browser, paid LLM, off-machine restore or fresh-daemon portability claim is added. The source manifest remains BLOCKED. The issued ZIP is unchanged; no replacement package or runtime operation is needed to record this evidence.
