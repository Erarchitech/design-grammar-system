# Plan 1204-01 Summary — Deterministic Projection-Hash Tracer

## What was built

Plan 1204-01 ships the one projection primitive the rest of phase 1204 depends on:
a benchmark-computed verdict projection hash over DE-01 leg envelopes, with a closed
exclusion list (D-04), plus the negative controls that make "repeatable" measurable.

Two new files, and nothing else:

- `tools/de01/projection_hash.py`
  - `PROJECTION_VERSION = 1` (int) — bump required, with a recorded reason, for any
    change to the exclusion list (D-04 one-way reversibility).
  - `EXCLUSION_FIELDS = frozenset({"emittedAt", "generatedAt", "definitionId"})` — the
    closed D-04 list as one explicit module-level constant.
  - `project_verdict(envelope: dict) -> dict` — deep-copies the envelope, drops exactly
    the excluded keys, and sorts `rows` ascending by `objectId` with `ruleId` tiebreak
    per `spec/EVIDENCE-CONTRACT.md` §4. A missing or empty `rows` key stays that way.
  - `verdict_projection_hash(envelope: dict) -> str` —
    `canonical_json.hash_canonical(project_verdict(envelope))`, 64-char uppercase SHA-256 hex.
  - Module docstring records: the Correction 2 purpose (no producer emits an output
    hash), the three recorded exclusion reasons (`emittedAt` wall clock at
    `evidence_contract.py:253`; `generatedAt` report-level wall clock at `report.py:354`;
    `definitionId` carries the run id on the data-service leg, Correction 3), the
    change discipline (recorded contract reason + `PROJECTION_VERSION` bump), and an
    explicit instruction never to import or call the pipe-joined scalar-tuple helper
    named in Correction 10.
  - Imports `canonical_json` only, via the `legs.py:29-35` sys.path bootstrap. It never
    validates the envelope (legs validate before returning, `legs.py:10-13`), never
    mutates its input, and contains no run-id literal.

- `tools/de01/tests/test_repeat_runner.py` — 26 tests in exactly three classes:
  - `TestProjectionHash` (5) — tracer slice: stability across repeated calls, the three
    exclusions invisible to the hash, status-flip negative control, input never mutated,
    and schema validity of the baseline through `evidence_contract.validate_envelope`.
  - `TestProjectionHashNegativeControl` (16) — 12 parametrized single-field inclusion
    mutations (row `canonicalStatus`, row `warnings` text, row `warnings` appended, row
    `detail`, envelope `canonicalStatus`, `stage`, `serviceName`, `serviceVersion`, and
    `inputHash`/`outputHash` added and changed), reorder-invariance, the empty-vs-populated
    warnings arm, and the three closed-set pinning tests (exact `EXCLUSION_FIELDS`,
    `PROJECTION_VERSION == 1`, row-order parity with `evidence_contract._sort_key`).
  - `TestProjectionHashCrossProcess` (4) — a fresh `python -c` subprocess receiving the
    envelope as JSON on stdin (`shell=False`, no tmp file) must reproduce the in-process
    hash under the default environment and under two forced distinct `PYTHONHASHSEED`
    values, plus a status-mutated divergence arm proving the subprocess computes rather
    than echoes.

## Key decisions

- **Row sorting lives in the projection, not in the hash call.** Section 4 ordering is
  canonicalized inside `project_verdict`, so a scrambled `rows` input hashes identically
  while any payload mutation (including warning text) always moves the hash.
- **Exclusion is by field name only.** No run-id literal exists anywhere in the module
  (Correction 3): a hardcoded id would silently stop excluding the day the run-id scheme
  changes. Verified count of `RUN_GOLD_1200` in the module: 0.
- **Pinning tests were folded into `TestProjectionHashNegativeControl`** rather than
  living in a fourth `TestProjectionHashContract` class. The plan permitted either, but
  the final acceptance criterion requires exactly the three `TestProjectionHash*` class
  names with no runner class — so the closed-set pins sit as a commented group inside the
  negative-control class, keeping exactly three `^class Test` lines.
- **The parity test compares identity order, not full row dicts.**
  `evidence_contract._sort_key` operates on the Pydantic row model, and the model fills
  in optional defaults (`warnings`, `inputHash`, `outputHash`, `detail`) that the
  projection deliberately does not invent. The parity claim is therefore the
  `(objectId, ruleId)` order over model-typed rows plus a length check.
- **Baseline schema validity is proven through the model constructor.**
  `validate_envelope` takes an `EvidenceEnvelope` model, so the test builds
  `evidence_contract.EvidenceEnvelope(**_baseline_envelope())` and validates that.
- **Cross-plan seam preserved for 1204-05.** `_envelope`, `_row`, and
  `_baseline_envelope` are module-level (not class attributes), the module docstring
  documents the append contract, and the projection-hash classes import nothing heavier
  than the module under test, `evidence_contract`, and the standard library.

## Verification results

Run from the repo root. `python -m pytest` commands as specified:

| # | Command | Result |
|---|---------|--------|
| 1 | `python -m pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"` | **PASS** — `26 passed`, exit 0 |
| 2 | `python -m pytest tools/de01/tests/ -x -q` | **BLOCKED BY PRE-EXISTING ENVIRONMENT DEFECT** — `54 passed, 1 error`, exit 1. The single error is `TestReportJsonValidatesAgainstSchemaWithStateHashSection::…` in the untouched legacy `tools/de01/tests/test_de01_runner.py`, failing at setup with `PermissionError: [WinError 5]` on the ACL-denied stale repo-root directory `pytest-of-Admin` (pytest's `tmp_path` factory root). **Proven independent of this plan:** with both of this plan's new files moved out of the tree, the same command fails identically (`54 passed, 1 error`, same test). With the two `tmp_path`-dependent legacy tests deselected and `live` excluded, the suite is `87 passed`, exit 0. |
| 3 | `grep -rEc -i "hash_scalar_tuple\|hashscalartuple" …` | **0** (PASS) |
| 4 | `grep -rEc "\.secrets" …` | **0** (PASS) |
| 5 | `grep -rEc -i "api[_-]?key\|bearer\|credentialed" …` | **0** (PASS) |
| 6 | `grep -rEc -i "abstained\|valid_after_retry\|truncated\|refused\|provider_error" …` | **0** (PASS) |
| 7 | `grep -rEc -i "universal.{0,20}determin\|canvas" …` | **0** (PASS) |
| 8 | `git status --porcelain -- <frozen inputs>` | **empty** (PASS) — every frozen input is byte-identical to HEAD |

**Tooling note on rows 3–7.** `grep` is not on `PATH` in this sandbox, and Git's bundled
`C:\Program Files\Git\usr\bin\grep.exe` aborts with
`*** fatal error - couldn't create signal pipe, Win32 error 5` — it cannot start at all
here. The five prohibition patterns were therefore evaluated with PowerShell
`Select-String` over the same two files with the same case-insensitive regular
expressions; every pattern reports 0 matching lines in both files. The commands should be
re-run with a working `grep` by the orchestrator for the formal gate.

**Additional plan acceptance checks:**

- `def verdict_projection_hash` count: 1 · `def project_verdict` count: 1.
- `EXCLUSION_FIELDS` occurrences: 6 (≥ 2 required) · `PROJECTION_VERSION` occurrences: 2.
- `^class Test` lines: exactly 3 — `TestProjectionHash`, `TestProjectionHashNegativeControl`,
  `TestProjectionHashCrossProcess` — no runner class.
- Negative-control arms: 12 parametrized mutations (≥ 10 required) + reorder invariance +
  empty-warnings arm.
- Cross-process spawns: 3 equality spawns (default env plus two forced hash seeds) plus
  1 divergence arm.
- Zero new dependencies; `python -m py_compile` clean on both files.

**Not done, by instruction:** no `git commit`/`push`/publish. Both new files remain
untracked in the working tree (`?? tools/de01/projection_hash.py`,
`?? tools/de01/tests/test_repeat_runner.py`); no other file was modified. Nothing under
`.secrets/` was read.