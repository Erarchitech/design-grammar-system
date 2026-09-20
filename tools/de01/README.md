# DE-01: Cross-Service Evidence Runner

DE-01 is the standalone runner that drives the frozen golden fixture
(`fixtures/golden/fixture.json`) through all four evaluation legs — Python
`data-service`, `dg-reasoner`, the C# `DG.Core` evaluator, and the persisted-replay
path — and compares their canonical statuses per (rule, object) pair. It is Phase
1200's proof artifact: the contract (`spec/EVIDENCE-CONTRACT.md`) and the fixture
(`fixtures/golden/`) are definitions; DE-01 is the evidence that the four legs can
be compared at all.

## Invocation

```bash
python tools/de01/run_de01.py
```

With defaults, this drives `fixtures/golden/fixture.json` through all four legs and
writes `.de01/de01-report.json` and `.de01/de01-report.md`.

### Flags

| Flag | Default | Meaning |
|---|---|---|
| `--fixture` | `fixtures/golden/fixture.json` | Path to the frozen golden fixture. |
| `--out-dir` | `.de01/` | Directory the two reports are written into. |
| `--data-service-url` | `http://localhost:8000` | Base URL for the data-service leg and the persisted-replay leg. |
| `--dg-reasoner-url` | `http://localhost:8001` | Base URL for the dg-reasoner leg. dg-reasoner has **no host-exposed port** in `docker-compose.yml` by default — see the precondition table below. |
| `--legs` | all four | Run only a subset: `data-service dg-reasoner csharp replay` (space-separated). |

Exit code: **non-zero only when `silent_disagreement_count > 0`**. A leg being
unavailable never by itself changes the exit code — that is a typed outcome
recorded in the report (D-13), not a runner failure.

## Output files

| File | Format | Contents |
|---|---|---|
| `<out-dir>/de01-report.json` | JSON, validates against `tools/de01/report_schema.json` | Run metadata, per-leg availability/service/version, ordered comparison rows, declared non-equivalences, per-status tallies, `silent_disagreement_count`. |
| `<out-dir>/de01-report.md` | Markdown | Human-readable sibling: verdict header, per-leg availability table, one comparison-table row per (rule, object) pair with one column per leg, a declared non-equivalences section, and a warnings appendix. |

## Per-leg preconditions

| Leg | What must be running | A typed non-result from this leg means |
|---|---|---|
| **data-service** | Reachable at `--data-service-url` (default `http://localhost:8000`), started via `docker compose up -d data-service`, with a Speckle project configured (`SPECKLE_PROJECT_ID`/`SPECKLE_BASE_MODEL_ID` or the DG home page's Speckle Settings card) and a write token. | `error` — connection refused (service not running), or `SPECKLE_CONFIG_MISSING`/token-missing from `/validation/publish` (data-service/app.py). Neither is a DE-01 defect; it is the leg's own documented precondition being unmet. |
| **dg-reasoner** | Reachable and holding the `./fixtures:/app/fixtures:ro` mount added in plan 1200-02's `docker-compose.yml` change. **dg-reasoner has no host-exposed port** — it is reachable only from inside the `docker compose` network by default; pass `--dg-reasoner-url` if you have published one. | `error` — connection refused/timeout when unreachable from the host, or `{conforms: None, error: "timeout"}` when the SHACL pipeline itself times out (dg-reasoner's own D-09 shape, `reasoning.py::run_shacl`). |
| **csharp** | `dotnet build DG/DG.sln` succeeds, producing `DG/tools/DG.De01Harness/DG.De01Harness.csproj`'s output. | `error` — `dotnet` not on `PATH`, the harness exits non-zero, or its stdout is not parseable JSON. A *successful* harness run reporting `unsupported` for the `ObjectPropertyAtom` case (see below) is not an error — that is the pre-declared, by-design outcome. |
| **replay** | `fixtures/golden/seed.cypher` applied against a running Neo4j, then read back through data-service's `/validation/view/{project}` route. Apply it with: `cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/seed.cypher` | `error` — data-service unreachable, no run exists yet for project `DG-1200-GOLDEN` (404), or the persisted run has no `evidenceEnvelopeJson` (unseeded, or predates Phase 1200's additive sidecar). The replay leg reads only the canonical envelope, never `Run.ValidStatus` (D-04). |

## Acceptance rule

The run **passes** when `silent_disagreement_count` is `0`. **Declared
non-equivalences are expected and do not fail the run.** A **silent disagreement
does** fail the run (spec/EVIDENCE-CONTRACT.md section 8, D-14).

**Expected declared non-equivalence, by design:** the C# leg reports the fixture's
`ObjectPropertyAtom` (`R_GOLD_HEIGHT_MAX_75_V_A4`, `belongsToDistrict(?b, ?d)`) as
`unsupported`, because `DG.Core.Parsing.SwrlRuleParser.ResolveAtomType` has no
branch for that atom type (it resolves only `BuiltinAtom`/`ClassAtom`/
`DataPropertyAtom`). Phase 1201's **ALGN12-05** adds the missing branch. This is
pre-declared in `fixtures/golden/MANIFEST.md`'s "Expected non-results by design"
section — a DE-01 report showing this divergence is confirmation the fixture and
the frozen contract are working as designed, not a bug to chase.

## Environment caveats

- **`neo4j` hostname resolution.** The `neo4j` hostname used by `NEO4J_URI` in
  `docker-compose.yml` resolves only inside the compose network. Running the
  replay leg from the host against an unreachable graph produces a typed `error`
  row — this is environment-dependent, not a regression.
- **Host vs. container Python.** The host's Python may be a different minor
  version than the containers' (the containers run Python 3.11; host versions
  vary by machine). Anything version-sensitive in `data-service`/`dg-reasoner`
  should be exercised in-container or over HTTP (as every leg adapter in
  `tools/de01/legs.py` does) rather than by importing service modules directly
  from the host for behavior that depends on the exact interpreter.
- **dg-reasoner has no default host port.** Unlike `data-service` (published at
  `8000:8000`), `dg-reasoner` in `docker-compose.yml` has no `ports:` mapping.
  From a bare host shell, the dg-reasoner leg will report a typed `error`
  (connection refused/timeout) unless you publish a port and pass
  `--dg-reasoner-url`, or run this script from inside the compose network.

## No CI pipeline

**No CI pipeline exists in this repository**, and creating one is deliberately
out of scope for Phase 1200 (`.github/workflows/` does not exist and this plan
does not add it). The wrapper test in `tools/de01/tests/test_de01_runner.py` is
written to be runnable by a future CI and easy to invoke manually today:

```bash
python -m pytest tools/de01/tests/test_de01_runner.py -x -q -k "not live"
```

runs the comparison unit tests with no live services, and

```bash
python -m pytest tools/de01/tests/test_de01_runner.py -x -q -k "live"
```

runs the full wrapper test against the dev stack, failing (never skipping
silently) with a message naming the missing precondition if the report cannot be
produced.

## Fixture freeze rule (phases 1201–1205)

`fixtures/golden/` is frozen once committed (spec/EVIDENCE-CONTRACT.md section 7,
D-09/D-10/D-11). **Phases 1201–1205 re-run DE-01 against this same frozen
fixture to verify their own work — they do not edit it to make their own gates
pass.** If a phase's implementation cannot yet satisfy an expectation the
fixture encodes, the correct response is a typed, disclosed non-result in that
phase's own evidence (exactly as this phase discloses the C# leg's
`ObjectPropertyAtom` case above), never editing the fixture to make the gap
disappear.
