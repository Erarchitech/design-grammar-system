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
| **dg-reasoner** | Reachable and holding the `./fixtures:/app/fixtures:ro` mount added in plan 1200-02's `docker-compose.yml` change, **and** `fixtures/golden/seed.cypher` applied against the same Neo4j the leg targets (Phase 1201 D-09: this leg now posts `run_id`, so it needs the seeded `Run`/ValidGraph ABox the same way the replay leg does). **dg-reasoner has no host-exposed port** — it is reachable only from inside the `docker compose` network by default; pass `--dg-reasoner-url` if you have published one. | `error` — connection refused/timeout when unreachable from the host, or `{conforms: None, error: "timeout"}` when the SHACL pipeline itself times out (dg-reasoner's own D-09 shape, `reasoning.py::run_shacl`). A zero-result `conforms=true` report now means the seed was not applied or the run id did not match — not that the population is genuinely empty (Phase 1201 fix; see below). |
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

## Phase 1201 fixes: dg-reasoner run_id (D-09/D-10) and report-level hash fallback (D-12)

**D-09 — dg-reasoner leg now sends `run_id`.** Before this phase, `run_leg_dg_reasoner`
posted `{"project": project}` only. `dg-reasoner/reasoning.py::run_shacl`'s own
docstring states that *without* `run_id` it validates the project-level
Metagraph/OntoGraph export only — the run's ValidGraph ABox
(`build_valid_graph`) is unioned in *only* when `run_id` is supplied. The
seeded golden `Object` nodes (`OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`) live in that
ABox, so the missing argument made `dgc:ObjectShape` target a class absent
from the graph pySHACL actually validated: zero focus nodes, `conforms=true`,
every row misreported as `no_population`. The leg now posts `run_id`, sourced
from the fixture with a fallback to the seeded value in
`fixtures/golden/seed.cypher` (`FIXTURE_RUN_ID = "RUN_GOLD_1200"` in
`tools/de01/legs.py`, since the frozen `fixture.json` carries no run id field
of its own).

**Consequence: the dg-reasoner leg now shares the replay leg's seed precondition.**
Run `fixtures/golden/seed.cypher` first, or this leg reports `no_population`
for a different, now-genuine reason (unseeded graph / mismatched run id) —
see the precondition table above.

**D-10 — a conforming report against a non-empty target set maps to `not_evaluated`,
never `passed`.** SHACL validates *structural* conformance; it cannot express
the golden fixture's quantitative rule ("height > 75") —
`spec/RULE-PARTITION-POLICY.md` reserves quantitative rules to the SWRL
VALIDATOR. Claiming `passed` here would assert the business rule was
evaluated and satisfied, which would be false. Every such row carries a
non-empty warning naming the partition-policy reason. A SHACL violation
naming a focus node still maps that object to `failed` — a genuine
structural finding is still a verdict.

**Known, empirically-verified limit of this fix (not a defect, a fact about
`compare_legs`'s classification guard).** `tools/de01/report.py`'s
`_DECLARABLE_STATUSES` is `{unsupported, error, not_evaluated, indeterminate}`
— `passed` and `failed` are deliberately excluded (CR-02, 1200-REVIEW.md: "any
non-declarable status participating in a difference makes that difference
silent, regardless of ... what the other legs reported"). This means
dg-reasoner's `not_evaluated` on `OBJ_GOLD_FAIL` against another leg's genuine
`failed` verdict is **unconditionally `silent_disagreement`**, not
`declared_non_equivalence` — no warning on the `not_evaluated` side changes
this, because the guard fires on the presence of *any* non-declarable status
in the differing set, and `failed` is one. Mapping to `not_evaluated` is still
the correct, honest status per D-10 (the alternative, `passed`, is equally
non-declarable and would produce the identical silent classification) — but
it does not by itself reach `silent_disagreement_count = 0` against the
golden fixture. Plan 06's live DE-01 re-run is expected to still show this one
declared silent disagreement on `OBJ_GOLD_FAIL`, unless the fixture happens to
route the C# leg's row for that pair through its own `unsupported`
ObjectPropertyAtom row rather than a `failed` verdict row for that exact
(rule, object) pair — that is a live-stack question this phase's Python-only
changes cannot settle from source alone.

**D-12 — the report now falls back to the envelope-level hash.** Row-level
`inputHash`/`outputHash` are populated by no call site today (only the
envelope-level hash is real, computed by the C# harness via
`CanonicalJsonWriter.HashCanonical`, `DG/tools/DG.De01Harness/Program.cs:284,294`).
`tools/de01/report.py`'s `compare_legs` now falls back to the envelope's
`inputHash`/`outputHash` when a row carries none; a row-level value, if ever
populated by a future call site, wins over the envelope's. This is a
**declared, known gap, not a closed one**: genuine row-level hash granularity
remains unpopulated by every call site (`data-service/app.py`'s `EvidenceRow`
construction and the C# harness's own row emission), and
`spec/EVIDENCE-CONTRACT.md` § 3 defines the row-level hash as *optional*
("where the envelope-level hash is insufficiently granular"), not required. A
reader comparing two rows from the *same* envelope is comparing the *same*
hash after this fallback, and should not read per-row agreement into it.

## Fixture freeze rule (phases 1201–1205)

`fixtures/golden/` is frozen once committed (spec/EVIDENCE-CONTRACT.md section 7,
D-09/D-10/D-11). **Phases 1201–1205 re-run DE-01 against this same frozen
fixture to verify their own work — they do not edit it to make their own gates
pass.** If a phase's implementation cannot yet satisfy an expectation the
fixture encodes, the correct response is a typed, disclosed non-result in that
phase's own evidence (exactly as this phase discloses the C# leg's
`ObjectPropertyAtom` case above), never editing the fixture to make the gap
disappear.
