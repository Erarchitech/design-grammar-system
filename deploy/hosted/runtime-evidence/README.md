# Owner-returned candidate capability evidence

## Scope and origin

`2dedbfb-owner-report.json` is a transcription of the sanitized JSON supplied by the owner in this conversation. The owner separately supplied `PS C:\DG-test> $LASTEXITCODE` → `0`. It is not a report independently collected by this development machine, a signed attestation, or a fresh runtime test. No target runtime timestamp was provided; none is inferred from the source revision or this note.

The earlier returned `FAIL` at `disk-and-docker-preflight` remains historical; it is not merged into or substituted for this later complete PASS report.

## Identity validation performed locally

```text
python deploy/hosted/accept_runtime_evidence.py --report deploy/hosted/runtime-evidence/2dedbfb-owner-report.json --zip C:/Users/Admin/Downloads/DG-candidate-test-2dedbfb-DESKTOP-OS4Q8CP.zip --exit-code 0
```

Result: `OWNER_REPORTED_CAPABILITY_PASS`, `independentlyObservedRuntime=false`, `releaseAccepted=false`, exit 0. The validator compared the entire typed report and all ZIP members with the issued package identity, not merely the word PASS.

- Framework: `2dedbfb3e138c2b437e781696197105dca93342a`.
- ZIP SHA-256: `1e032824fbb3006d3e001a3460185a97e1d4661941910671f6f4f62ecc4af87e`.
- Candidate manifest SHA-256: `864878de1e60aadc79211f20e574f32cb5f97a096c06dac696a1f52215f04810`.
- Transcribed report file SHA-256: `69b5a5fb8942a779af065ccdd27ab8c0b027c420a3f92d42217fb48bc9b40995` (not a claim about the original file's whitespace/encoding).

## Supported conclusions

Owner reports passing package integrity, Compose/disk/isolation/vacancy checks; administrator login, CSRF denial, one inserted synthetic note and one scoped Neo4j observation, four denied paths, n8n named/denied read, and verified project/volume cleanup. This is the actual-candidate **three-service subset**, distinct from the old V11 synthetic package.

## Not supported

No image IDs/registry digests were recorded by that runner, and its images/cache remain after cleanup. Inspecting cache now can identify current cached images only; it cannot retroactively prove those bytes were the images used in the completed run. Built-image source provenance requires a separately controlled exact-source build and image capture. No full hosted UI/edge/reasoner/Speckle/LLM test, backup/restore, release freeze or HOST requirement acceptance follows from this report. `test_bundle_runtime.py` remains a distinct blocked integration gate; do not set environment overrides on the development PC to turn it green.
