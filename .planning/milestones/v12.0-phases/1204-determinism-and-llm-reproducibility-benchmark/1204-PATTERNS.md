# Phase 1204: Determinism and LLM Reproducibility Benchmark - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 18 (12 new, 6 extended/modified; plus 3 implied discretion-level artifacts)
**Analogs found:** 18 / 18 (every file has at least a role-match analog; two planner-visible corrections recorded in §Research Discrepancies)

## How to read this map

Every analog below was verified on disk in this session. Excerpts carry exact `file:line`
anchors read from current file contents (not from CONTEXT.md/RESEARCH.md citations alone).
Two RESEARCH.md paths are corrected against disk in the last section — read those before
assigning plans.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tools/de01/run_de01_repeat.py` | controller (CLI driver) | batch orchestration: subprocess + HTTP request-response | `tools/de01/run_de01.py` | exact |
| `tools/de01/projection_hash.py` | utility | transform (envelope dict → SHA-256) | `data-service/canonical_json.py` | role-match (reuses `hash_canonical` verbatim) |
| `tools/de01/report_schema_repeat.json` | config (JSON Schema) | validation | `tools/de01/report_schema.json` + `spec/evidence-contract.schema.json` | exact |
| `tools/de01/tests/test_repeat_runner.py` | test | file I/O (fixtures) + subprocess mocking | `tools/de01/tests/test_de01_runner.py` | exact |
| `tools/de01/tests/test_reproducibility_scope_drift.py` | test | file I/O (spec fenced-block parse vs source scan) | `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs` | role-match (same drift-guard, different language) |
| `data-service/tests/recognition_eval/repeat_sweep.py` | driver/service | request-response + file I/O (cassette record) | `data-service/tests/recognition_eval/live_sweep.py` | exact |
| `data-service/tests/recognition_eval/outcome_taxonomy.py` | utility | transform/classification | `data-service/cg_recognition.py` + `data-service/dg_context.py` (violation codes) | role-match (classification logic is spread across two producers today) |
| `data-service/tests/recognition_eval/test_outcome_taxonomy.py` | test | in-memory classification | `data-service/tests/test_recognition_eval.py` | exact |
| `data-service/tests/recognition_eval/test_provenance.py` | test | dict-field validation | `data-service/tests/recognition_eval/corpus.py` (`assert_provenance`) | exact |
| `spec/REPRODUCIBILITY.md` | spec/config | n/a (normative doc + machine-checked block) | `spec/SWRL-SUBSET.md` | exact |
| `fixtures/llm_repeatability/` (rule_ingest_prompts/ + cassettes/) | fixture data | file I/O | `fixtures/golden/` (freeze manifest) + `data-service/fixtures/recognition_eval/cassettes/` | role-match |
| `CLAUDE.md` (modified, governing-spec pointer) | config/doc | n/a | `CLAUDE.md:210-214` (existing pointer trio) | exact |
| `data-service/tests/recognition_eval/cassette.py` (EXTENDED, sample_index) | utility | file I/O (hash-keyed cassette store) | itself, `cassette_key` at `cassette.py:69-99` | exact |
| `data-service/tests/recognition_eval/report.py` (EXTENDED or sibling, D-17 aggregation) | utility/report | transform | itself, `render_markdown`/`wilson_interval` at `report.py:352-406` | exact |
| `data-service/tests/test_recognition_eval.py` (EXTENDED, sample_index tests) | test | file I/O | itself, `TestCassette` at `test_recognition_eval.py:63-200` | exact — **corrects RESEARCH.md, which names a nonexistent `test_cassette.py`** |
| `data-service/llm_gateway.py` (EXTENDED, D-20 fields) | model/service | request-response | itself, `GenerateResponse` at `llm_gateway.py:47-71` | exact |
| `data-service/tests/test_llm_gateway.py` (EXTENDED, D-20 field tests) | test | request-response (mocked adapters) | itself, `TestGenerate` at `test_llm_gateway.py:238-267` | exact |
| `spec/API.md` (MODIFIED, D-20 field docs) | spec | n/a | itself (route tables at `spec/API.md:3-68`; **no `/llm/generate` section exists today** — additive) | exact |

### Implied discretion-level artifacts (planner chooses, per CONTEXT.md "Claude's Discretion")

| Artifact | Role | Data Flow | Closest Analog |
|---|---|---|---|
| D-06 pinned-replay variant function (hosted in `run_de01_repeat.py` or a small sibling) | utility (leg adapter) | request-response | `tools/de01/legs.py:835-858` (`run_leg_replay`) + pinned-route call already made by the data-service leg at `legs.py:230` |
| D-12 frozen-prompt rendering script (one-off, per discretion) | script | request-response + file I/O | `tools/de01/legs.py:190-207` (httpx POST pattern) + `n8n/workflows/rules-to-metagraph.json` "Build LLM Prompt" node (read-only source) |
| Repeat report emitter (JSON+MD, D-24) — fold into `run_de01_repeat.py` or sibling | utility/report | file I/O | `tools/de01/report.py:347-406` (`emit_json_report` / `emit_markdown_report`) |

---

## Pattern Assignments

---

### `tools/de01/run_de01_repeat.py` (controller, batch orchestration)

**Analog:** `tools/de01/run_de01.py` (verified on disk, 178 lines)

**Imports / sys.path bootstrap** (`run_de01.py:23-31`) — the repeat driver must use the
same bootstrap so `import legs` / `import report` / `import projection_hash` resolve:

```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DE01_DIR = Path(__file__).resolve().parent
if str(TOOLS_DE01_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DE01_DIR))

import legs  # noqa: E402
import report as report_module  # noqa: E402

ALL_LEG_NAMES = ("data-service", "dg-reasoner", "csharp", "replay")

_LEG_RUNNERS = {
    "data-service": legs.run_leg_data_service,
    "dg-reasoner": legs.run_leg_dg_reasoner,
    "csharp": legs.run_leg_csharp,
    "replay": legs.run_leg_replay,
}
```

**Leg-runner dispatch table** (`run_de01.py:33-38`, above) — D-01 forbids re-implementing any
leg. The repeat driver copies this dict exactly, swapping only the replay entry for the D-06
pinned variant.

**argparse CLI shape** (`run_de01.py:41-96`) — repeat-mode adds batch count, restart command,
and pinned-run-id args alongside `--fixture`, `--out-dir`, `--data-service-url`,
`--dg-reasoner-url`, `--legs` (all existing). The single-pass CLI stays untouched (D-06:
additive, and RESEARCH.md Open Question 3 recommends a sibling file, not a `--repeat` flag).

**Exit-code contract** (`run_de01.py:139-174`) — non-zero only on a gate failure (here:
D-08's N/N-hash gate), never on a typed leg unavailability:

```python
    return 1 if comparison.silent_disagreement_count > 0 else 0
```

**Gate-decision shape** (RESEARCH.md's own pattern, validated against `legs.py`): the D-08
gate is a pure set-equality check per leg:

```python
gate_passed = all(len(set(hashes)) == 1 for hashes in all_hashes.values())
```

**Fresh-process-per-batch** — the batch boundary calls `docker compose restart data-service
dg-reasoner` via `subprocess.run` with `check=True, timeout=120`, exactly the subprocess
discipline of the C# leg (`legs.py:680-697`, verified: `shell=False`, `capture_output=True`,
`text=True`, `timeout=120`). The C# leg is already fresh-process-per-iteration, so it needs
no restart.

**Pinned-replay variant (D-06)** — copy `run_leg_replay` (`legs.py:835-858`) and change only
line 858's URL. The pinned route already exists (`data-service/app.py:2796`,
`GET /validation/view/{project}/{run_id}`) and is already called by the data-service leg
(`legs.py:230`). Import `FIXTURE_RUN_ID` from `legs` (defined at `legs.py:47`, with its
`:Run` vs `:ValidationRun` drift warning at `legs.py:41-47`) — never re-hardcode the literal
(RESEARCH.md Anti-Pattern #3; also Open Question 1: verify which seeded id the route
resolves before freezing the wrapper's contract).

---

### `tools/de01/projection_hash.py` (utility, transform)

**Analog:** `data-service/canonical_json.py` (verified on disk, 183 lines) — import, never
reimplement. `legs.py` already shows the path-bootstrap pattern for importing it from
`tools/de01/` (`legs.py:29-35`):

```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
if str(DATA_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_SERVICE_DIR))

import canonical_json  # noqa: E402  (path-dependent import, see sys.path insert above)
import evidence_contract  # noqa: E402
```

**Core hashing primitive to call** (`canonical_json.py:180-183`, verified):

```python
def hash_canonical(value: Any) -> str:
    """Canonicalize ``value``, SHA-256 the UTF-8 bytes, return uppercase hex."""
    canonical = canonicalize(value)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
```

D-04/Correction 10: **never** call `canonical_json.hash_scalar_tuple` (line 59, still the
naive pipe-join, diverged from the Phase 1203 D-09 length-prefix encoding). The exclusion
list is the module's own data (RESEARCH.md Pattern 3):

```python
_EXCLUDED_TOP_LEVEL = {"emittedAt"}
_EXCLUDED_REPORT_LEVEL = {"generatedAt"}
_RUN_DERIVED_FIELDS = {"definitionId"}   # Correction 3: data-service's definitionId == run_id
```

**Canonicalization contract** the projection inherits: `spec/EVIDENCE-CONTRACT.md:294-342`
(the six nested-payload rules, versioned by `canonicalizationVersion`; the stale
scalar-tuple paragraph is at `:285-292` — do not copy it). `emittedAt` is wall-clock per
`data-service/evidence_contract.py:253` (verified) — that is why D-04 excludes it, not
`definitionId`'s sibling fields.

**Negative control (D-04, tested in `test_repeat_runner.py`)**: mutate one `canonicalStatus`
or one `warnings` entry in a copied envelope → hash must change; re-order rows → hash must
NOT change (rows are normatively sorted by `objectId`/`ruleId`, `evidence_contract.py:245-251`
and `EVIDENCE-CONTRACT.md` §4). This mirrors the negative-control practice already proven in
`tools/de01/tests/test_de01_runner.py` (`TestCompareLegsHashFallback` at line 644,
`_csharp_wrapper_stdout` fixtures at 702-714).

---

### `tools/de01/report_schema_repeat.json` (config, validation)

**Analog:** `tools/de01/report_schema.json` (verified on disk, 236 lines) — sibling, NOT a
verbatim reuse (D-24 + Wave 0: the repeat report carries per-iteration hash lists the
single-pass schema has no field for).

**Copy these three mechanics:**
1. **Draft + `$id` + title/description header** (`report_schema.json:2-5`), including the
   long-form `description` explaining *why* a local `$defs` is a pinned mirror rather than a
   cross-file `$ref` (`report_schema.json:5` — jsonschema 4.18+ cannot resolve cross-file
   refs without a caller-supplied Registry).
2. **Pinned `$defs.CanonicalStatus` enum mirror** (`report_schema.json:6-21`) — the repeat
   schema needs this only if it embeds comparison rows; its own novelty is `leg_role:
   evaluator|relay` (D-02) and per-iteration `projectionHash` lists (D-04).
3. **Typed-absence idiom** — `{present: false, reason}` vs `{present: true, ...}` used in
   `perLeg` (`report_schema.json:92-134`) and `state_hash_comparison.perLeg`
   (`report_schema.json:180-204`). The repeat report's per-leg hash list should use the same
   idiom for an unavailable leg, never omit the key.

**Drift guard to keep working:** `tools/de01/tests/test_de01_runner.py:318`
(`TestReportSchemaCanonicalStatusPinning`) asserts `report_schema.json`'s enum stays
byte-identical to `spec/evidence-contract.schema.json`'s `$defs.CanonicalStatus.enum`
(that file verified on disk). If the repeat schema copies the enum, extend that pinning test
to it — a pinned mirror is only safe while it is mechanically checked.

---

### `tools/de01/tests/test_repeat_runner.py` (test)

**Analog:** `tools/de01/tests/test_de01_runner.py` (verified on disk; ~1300 lines; imports
at 10-27, class map from grep).

**Imports / bootstrap** (`test_de01_runner.py:20-27`):

```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# (sys.path inserts for tools/de01 + data-service follow)
import legs  # noqa: E402
from legs import LegResult, run_leg_dg_reasoner, run_leg_replay  # noqa: E402
from report import compare_legs, compare_state_hashes  # noqa: E402
```

**Fixture-builder helpers as module-level functions** — `_envelope(...)` (line 30),
`_row(...)` (line 45), `_minimal_fixture(...)` (line 338), `_mock_response(...)` (line 359),
`_mock_subprocess_result(...)` (line 694). The repeat-runner tests need the same envelope
builders plus a mutation helper for the D-04 negative control.

**Subprocess mocking pattern** (`test_de01_runner.py:694-714`, verified shapes) — the D-05
`docker compose restart` call and the C# leg are mocked via `MagicMock` `subprocess.run`
results; the live-stack path stays `-k "not live"`-excluded, mirroring the existing
`TestLiveRecordSweep` double gate (env var + marker) at
`data-service/tests/test_recognition_eval.py:810-831`.

**End-to-end test naming precedent:** `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements`
(line 1297) — the repeat analog is `test_repeat_runner_N_iterations_has_single_hash_per_leg`
plus the negative-control test, both hermetically unit-testable (no live stack), per
RESEARCH.md's Wave 0 command `python -m pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"`.

---

### `tools/de01/tests/test_reproducibility_scope_drift.py` (test, D-26 drift guard)

**Analog:** `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs` (verified on disk, 310
lines) — the repo's only existing drift-guard precedent. **Location note:** RESEARCH.md
proposes a Python test under `tools/de01/tests/`, but the only shipped drift guard is xUnit
in C#. The planner chooses: a Python sibling of the same shape (scanning
`data-service/*.py` for `get_adapter(` / `adapter.generate(` call sites) or a C# xUnit
counterpart. RESEARCH.md's confirmed call-site counts to enumerate: `app.py` (6),
`cg_recognition.py` (5), `dg_context.py` (10), `cg_input_generation.py` (4).

**Fenced-block loader to mirror** (`SwrlSubsetConformanceTests.cs:217-246`, verified):

```csharp
const string startMarker = "<!-- swrl-subset:supported-builtins:start -->";
const string endMarker = "<!-- swrl-subset:supported-builtins:end -->";

var startIndex = text.IndexOf(startMarker, StringComparison.Ordinal);
var endIndex = text.IndexOf(endMarker, StringComparison.Ordinal);

if (startIndex < 0 || endIndex < 0 || endIndex <= startIndex)
{
    throw new InvalidOperationException(
        $"SwrlSubsetConformanceTests.LoadDocumentedBuiltins: could not locate the machine-readable "
            + $"builtin block between '{startMarker}' and '{endMarker}' in spec/SWRL-SUBSET.md.");
}
```

**Both-directions assertion to mirror** (`SwrlSubsetConformanceTests.cs:248-263`):

```csharp
var documentedOnly = documented.Except(actual, StringComparer.OrdinalIgnoreCase).ToList();
var codeOnly = actual.Except(documented, StringComparer.OrdinalIgnoreCase).ToList();

Assert.True(
    documentedOnly.Count == 0 && codeOnly.Count == 0,
    "spec/SWRL-SUBSET.md's documented builtin list and DG.Core.Validation.SupportedBuiltins.Names "
        + $"disagree. Documented-but-not-in-code: [{string.Join(", ", documentedOnly)}]. "
        + $"In-code-but-not-documented: [{string.Join(", ", codeOnly)}]. Edit whichever side is "
        + "missing an entry so the two match exactly.");
```

**Discipline note** from `spec/SWRL-SUBSET.md:168-186` (verified): the drift guard was
proven to fail on an induced mismatch before being reverted — the planner should schedule
the same negative-control proof for the D-26 guard (add a fake call site, watch it fail,
revert).

---

### `data-service/tests/recognition_eval/repeat_sweep.py` (driver, request-response + cassette record)

**Analog:** `data-service/tests/recognition_eval/live_sweep.py` (verified on disk, 549
lines) — RESEARCH.md's own word: "modeled on `live_sweep.py`'s record/replay/cost-tracking
pattern".

**Outcome-status vocabulary pattern** (`live_sweep.py:282-305`) — every (provider, item)
combo lands in exactly one typed status, never a silent drop; copy this shape for the
D-13/D-14 k-sampling driver:

```python
OUTCOME_STATUSES = frozenset(
    {
        "recorded",
        "failed",
        "skipped_credentials",
        "skipped_invalid",
        "skipped_corpus_load_failed",
    }
)

@dataclass
class LiveSweepResult:
    outcomes: "list[ArmCorpusOutcome]"
    costs: "list[AttemptCost]"
```

**Cost accounting with named unpriced volume** (`live_sweep.py:308-343`) — D-13's
"provider availability recorded, unconfigured = not measured with reason" maps onto this
exact "flag, never silently free" discipline (`USD_PER_MTOK` at line 76, `priced` flag at
170-197).

**Mode gating** (`live_sweep.py:346-371`) — the driver refuses `replay` immediately
(`run_live_sweep` requires `RECOGNITION_EVAL_MODE=record|live`); the repeat driver mirrors
this: k>1 recording is its entire purpose, so a silent replay fallback must be impossible.

**Secret hygiene at the boundary** — reuse `resolve_live_adapter_and_key` (line 116) and
`mask_url` (line 82); never serialize `settings`/`LLMSettingsPayload` wholesale
(RESEARCH.md Security Domain: construct a minimal DTO of adapter name + host + models +
hashes).

**Adapter-resolve-once rule** (RESEARCH.md Anti-Pattern #2, verified at its sources):
resolve the adapter once per (provider, item) pair, then loop `adapter.generate()` k times
— exactly the documented contract of `recognize_structure`
(`data-service/cg_recognition.py:977-979`) and `generate_validated_cypher`
(`data-service/dg_context.py:960-964`):

```python
    Resolves the active provider/adapter ONCE before the Tier-1 loop and
    calls `adapter.generate()` in-process each attempt -- NEVER re-POSTs to
    `/llm/generate` (RESEARCH.md Anti-pattern guard): a re-POST re-reads
```

---

### `data-service/tests/recognition_eval/outcome_taxonomy.py` (utility, classification)

**Analogs (split across two producers today — this module is the first single home for the
D-14 taxonomy):**
- recognition violation codes: `data-service/cg_recognition.py` guard stack (`bad_json`,
  `schema_violation`, relational codes, G7/G8) around `validate_proposed_structure`,
  sampled at `cg_recognition.py:1235-1259` (verified) — including the G10 demotion
  (`:1236`) and G11 flag (`:1243-1244`).
- rule-ingest violation codes: `data-service/dg_context.py` `validate_cypher` (10 codes,
  cited at `dg_context.py:674`), called inside the retry loop at `dg_context.py:989`.

**Retry-shape the taxonomy must observe (D-15)** — both paths use `max_retries=2` with
corrective feedback; the taxonomy distinguishes first-attempt from final-result outcomes,
so it must be fed per-attempt data:

```python
def generate_validated_cypher(
    prompt: str, request_type: str, max_retries: int = 2
) -> dict[str, Any]:
```

(`dg_context.py:953-955`; the recognition twin is `cg_recognition.py:966-970`.)

**Truncated/refused inputs already exist** — `GenerateResponse.truncated` and
`finish_reason` (including the synthesized OpenAI `'refusal'` value) are documented at
`data-service/llm_gateway.py:55-63` (verified); D-14's `truncated` and `refused` classes
read these fields, never re-derive them from text heuristics.

**Abstention channel (D-16):** recognition's `unrecognized[]` entries — G6-autofilled is
NOT model abstention; the split lives in `cg_recognition.py`'s G6/G10 handling
(`:1088-1231` per CONTEXT.md citation, G10 demotion verified at `:1236`). Rule-ingest has
no channel → report `"not supported by output contract"`.

---

### `data-service/tests/recognition_eval/test_outcome_taxonomy.py` (test)

**Analog:** `data-service/tests/test_recognition_eval.py` (verified on disk, 979 lines) —
the module pattern for testing pure, hermetic classification functions.

**Pure-function-under-test convention** (`test_recognition_eval.py:366-401`) — the SC1
gate is a module-level pure function asserted with synthetic numbers; the D-14 taxonomy
tests copy this: one pure `classify(sample) -> str` per subject, parametrized over
violation codes, no adapter needed:

```python
def assert_sc1_gate(
    *,
    m1: float,
    e1_violations: int,
    ...
) -> None:
    ...
    if failing:
        raise AssertionError("SC1 gate FAILED -- conjunct(s) not satisfied: " + "; ".join(failing))
```

**Import bootstrap** (`test_recognition_eval.py:26-41`): `sys.path.insert` of the parent
and tests dir, `os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")`, then
`from recognition_eval import cassette as cassette_module` etc. New test files in
`recognition_eval/` (or `tests/`) must follow this exact bootstrap so the
path-dependent imports resolve.

---

### `data-service/tests/recognition_eval/test_provenance.py` (test, D-19 void rule)

**Analog:** `data-service/tests/recognition_eval/corpus.py` (verified on disk) — the
provenance-enforcement precedent D-19 explicitly mirrors (35-AI-SPEC E9).

**Required-fields tuple + void guard to extend** (`corpus.py:71-106`):

```python
REQUIRED_PROVENANCE_FIELDS = (
    "promptVersion",
    "provider",
    "model",
    "temperature",
    "negotiatedMode",
    "contextSha256",
    "frozenAtCommit",
    "corpusVersion",
)

def assert_provenance(result_row: dict) -> None:
    missing = [
        field
        for field in REQUIRED_PROVENANCE_FIELDS
        if field not in result_row or result_row[field] is None
    ]
    if missing:
        raise ProvenanceError(
            f"result row is missing required provenance field(s): {missing} -- "
            "the harness refuses to score a run whose provenance block is "
            "incomplete (35-AI-SPEC.md 5, freeze protocol item 3)."
        )
```

D-19's field list is longer (served model id, response id, system fingerprint, endpoint
host, prompt sha256, rendered-request sha256, sampling-params-as-sent, sample index,
timestamps/usage/finish_reason) — the planner extends the tuple + guard, keeping the
`ProvenanceError` refusal semantics and the "`None` = missing" rule. The existing refusal
test precedent is `TestProvenanceRefusal` at `test_recognition_eval.py:543-556`.

**SHA-pinning precedent for D-12's frozen prompts** (`corpus.py:109-123`):

```python
def assert_context_unchanged(corpus: Corpus) -> None:
    context_path = FIXTURES_DIR / f"{corpus.name}.context.json"
    on_disk_sha256 = hashlib.sha256(context_path.read_bytes()).hexdigest()

    if on_disk_sha256 != corpus.context_sha256:
        raise ProvenanceError(...)
```

---

### `spec/REPRODUCIBILITY.md` (spec, machine-checked scope table)

**Analog:** `spec/SWRL-SUBSET.md` (verified on disk, 198 lines) — the third
machine-checked-fenced-block spec after it.

**Fenced-block marker convention** (`spec/SWRL-SUBSET.md:55-70`, verified):

```markdown
The evaluator implements exactly six `swrlb:`-prefixed comparison builtins. This is the D-15
machine-checkable allow-list — the fenced block immediately below is read verbatim by
`SwrlSubsetConformanceTests.DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections`,
which asserts it matches `DG.Core.Validation.SupportedBuiltins.Names` exactly, in both directions.

<!-- swrl-subset:supported-builtins:start -->
```
swrlb:lessThan
...
```
<!-- swrl-subset:supported-builtins:end -->
```

REPRODUCIBILITY.md's D-26 scope table uses its own marker pair (e.g.
`<!-- reproducibility:llm-call-sites:start/end -->`), one call site per line, read
verbatim by the drift test.

**Spec skeleton to mirror** — the §5 "Enforcement" section (`SWRL-SUBSET.md:168-186`)
states precisely what is mechanically enforced vs documentation discipline; the D-25
non-claims list ("temperature 0 is not determinism", "cassette replay is not model
repeatability", "relay legs are not validator determinism") mirrors §3 "Non-Claims"
(`:111-128`).

**Governing-spec pointer (CLAUDE.md, D-25)** — the existing trio the new paragraph joins
(`CLAUDE.md:210-214`, verified):

```markdown
**Rule partition policy:** `spec/RULE-PARTITION-POLICY.md` governs which validation system ...
**Evidence and status contract:** `spec/EVIDENCE-CONTRACT.md` governs the canonical validation-outcome ...
**SWRL subset boundary:** `spec/SWRL-SUBSET.md` governs which SWRL atom types the parser ...
```

---

### `fixtures/llm_repeatability/` (fixture data, file I/O)

**Analogs (both verified on disk):**
- `fixtures/golden/MANIFEST.md` — the sibling-path freeze precedent: the frozen trio is
  `fixture.json`/`seed.cypher`/`canonical-vectors.json`, while `cq3-attribute-of/` sits
  beside it under "an additive sibling corpus under its own lighter change-reason
  discipline" (`MANIFEST.md:6-9`); freeze policy at `MANIFEST.md:41-57` (version bump +
  change-reason row; "Phases 1201–1205 verify their own work against this fixture. They do
  not edit it.").
- `data-service/fixtures/recognition_eval/` — verified on disk with
  `urbanblock_slice.context.json` + `.expected.json`, `frame_ablated.*`, and the frozen
  `cassettes/A0..A4/` tree that D-21 must NOT touch (sibling location per 1200 D-11 /
  1202 D-17).

**Per-item provenance triplet** — each frozen rule-ingest prompt ships as
`<name>.prompt.txt + .sha256 + .provenance.json`, mirroring `corpus.py`'s
`contextSha256`/`frozenAtCommit`/`corpusVersion` trio (`corpus.py:71-80`) plus the D-12
additions (workflow file + commit, assemble-response hash).

**Cassette storage shape** — `_cassette_path` at `cassette.py:115-116` (verified):
`_FIXTURES_ROOT / arm_id / f"{key}.json"` — the repeat cassettes keep
`<arm_id>/<sample-indexed-key>.json`, the only change being the key function.

---

### `data-service/tests/recognition_eval/cassette.py` (EXTENDED, D-21 sample_index)

**Analog:** itself — extend `cassette_key` (`cassette.py:69-99`, verified). The extension
is strictly additive: `sample_index=0` must produce a byte-identical key to today's
eight-part digest (D-21, RESEARCH.md Pattern 2):

```python
def cassette_key(
    *,
    provider: str,
    model: "str | None",
    prompt_version: str,
    system: "str | None",
    user_prompt: str,
    temperature: "float | None",
    negotiated_mode: str,
    max_tokens: "int | None",
) -> str:
    parts = [
        provider or "",
        model or "",
        prompt_version or "",
        system or "",
        user_prompt or "",
        "" if temperature is None else repr(float(temperature)),
        negotiated_mode or "",
        "" if max_tokens is None else str(int(max_tokens)),
    ]
    digest_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()
```

Add `str(int(sample_index))` as the ninth part (default 0). Keep `CassetteMissError` /
`CassetteWriteError` and the `(req, api_key, options=None)` signature untouched —
`test_generate_signature_matches_llm_adapter` (`test_recognition_eval.py:189-193`)
asserts the signature by `inspect.signature` and must keep passing.

**Key-collision test to extend** — the existing flip test
`test_cassette_key_changes_when_any_single_input_flips`
(`data-service/tests/test_recognition_eval.py:75-93`, parametrized over all 8 fields)
gains a `("sample_index", 1)` parameter row and a byte-identity assertion for the
`sample_index=0` default against a recorded pre-D-21 key.

---

### `data-service/tests/recognition_eval/report.py` (EXTENDED or sibling, D-17 aggregation)

**Analog:** itself — `render_markdown`/`render_json` at `report.py:352-445` (verified
portion 352-406), with the D-17-named Wilson CI already in use:

```python
for row in scored:
    lo, hi = scoring_module.wilson_interval(row.m1_successes, row.n_blocks)
```

`wilson_interval` itself is `scoring.py:420` (verified via grep:
`def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]`) —
reuse verbatim, never reimplement (RESEARCH.md "Don't Hand-Roll").

**D-17's two normalization levels are new data, not new machinery:** raw byte identity is
`==` on `text`; level-2 uses `canonical_json.hash_canonical` for recognition proposals and
a declared whitespace/line normalization for Cypher (discretion, must be declared in the
report). Modal-agreement rate and distinct-output count are plain dict aggregations.

**Provenance-void guard placement** — a sample missing any D-19 field is void; call
`assert_provenance` (extended) before a row can be scored, exactly as
`test_recognition_eval.py:658` does (`corpus_module.assert_provenance(outcome["provenance"])
# refuses to score an incomplete row`).

**D-24 report separation** — the LLM report's emitter is this module's (or a sibling's)
job; the deterministic report's emitter is the de01-side one. Never one file, never one
schema.

---

### `data-service/llm_gateway.py` (EXTENDED, D-20 additive fields)

**Analog:** itself — `GenerateResponse` (`llm_gateway.py:47-71`, verified):

```python
class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: dict
    truncated: bool = False
    finish_reason: str | None = None
```

Additive, optional, default-`None` fields (D-20; names at planner discretion,
RESEARCH.md Open Question 2 suggests `served_model`, `response_id`,
`system_fingerprint`). Each adapter's `.generate()` already parses `data = resp.json()`
and discards everything but content/choices/usage — the new fields are read from that
same parsed dict, with `.get(...)` + `None` defaults (RESEARCH.md Security Domain: the
provider response is a partially-trusted external boundary; never assume a key is
present).

**Adapter return-site pattern to extend** — the three `.generate()` bodies (Anthropic
`llm_gateway.py:361-439`, OpenAI `:449-528`, Ollama `:538-586` per RESEARCH.md; the
`model=req.model` requested-not-served defect at `:421,510,582`) are the only places
that populate the new fields. `get_adapter` (`:599-620`, verified) is unchanged.

**Documentation target** — D-20 requires `spec/API.md` to document the fields. Verified on
disk: `spec/API.md` has **no `/llm/generate` or GenerateResponse section today** (grep
over `llm|generate|fingerprint|served` found only `/computgraph/consult` LLM mentions at
`:64,128`). The planner must add a new subsection (e.g. under the data-service block
starting `spec/API.md:3`) rather than edit an existing route doc.

---

### `data-service/tests/test_llm_gateway.py` (EXTENDED, D-20 field tests)

**Analog:** itself — `TestGenerate` (`test_llm_gateway.py:238-267`, verified) patches
`app.get_adapter` / `app.load_persisted_llm_settings` and asserts the response body
field-by-field:

```python
response = client.post(
    "/llm/generate",
    json={"prompt": "Say hello", "provider": "anthropic", "model": "claude-sonnet-5"},
)
assert response.status_code == 200
body = response.json()
assert body["text"] == "Hello from Claude"
assert body["provider"] == "anthropic"
assert body["model"] == "claude-sonnet-5"
```

New tests: per-adapter population of `served_model`/`response_id`/`system_fingerprint`
from a mocked provider JSON, and the omission case — a provider response lacking the
field yields `None`, never a synthesized guess (RESEARCH.md's exact
`-k "served_model or response_id or fingerprint"` command).

---

### `spec/API.md` (MODIFIED, D-20 documentation)

**Analog:** itself — route-table format at `spec/API.md:3-68` (verified headers: Health,
MCP Protocol, Execution Tracking, Speckle Settings, Validation, Computgraph). The D-20
fields are documented as a **new additive subsection** (the gateway route has no existing
doc block — see correction in the `llm_gateway.py` entry above). No other route table
changes.

---

## Shared Patterns

### 1. Typed non-result degradation (never raise, never silently skip)

**Source:** `tools/de01/legs.py:1-14, 50-110` (`LegResult.available=False` +
`_synthesize_error_envelope` + `derive_valid_status` "Never raises" house style).
**Apply to:** `run_de01_repeat.py` (every leg, every iteration), the D-06 pinned-replay
variant, and the repeat report emitter — an unavailable leg per iteration is a typed
`error` row whose projection hash is still computed and listed, never an omitted key.

### 2. sys.path bootstrap for path-dependent imports

**Source:** `tools/de01/legs.py:29-35`, `tools/de01/run_de01.py:23-28`,
`tools/de01/tests/test_de01_runner.py:20-27`,
`data-service/tests/test_recognition_eval.py:26-41`.
**Apply to:** every new `tools/de01/` file (which imports `canonical_json`,
`evidence_contract` from `data-service/`) and every new test file. Same for the
recognition-eval files importing `recognition_eval.*` and the
`LLM_MASTER_SECRET`-test-default env line.

### 3. Canonical hashing discipline

**Source:** `data-service/canonical_json.py:180-183` (`hash_canonical`, uppercase hex);
contract rules at `spec/EVIDENCE-CONTRACT.md:294-342`.
**Apply to:** `projection_hash.py`, the D-17 level-2 normalization, the D-21 cassette key
extension (keep its own pipe-join — it is a key, not a canonicalization), and every place
the benchmark computes a hash of committed evidence. **Never** `hash_scalar_tuple`
(Correction 10 divergence).

### 4. Provenance-void refusal

**Source:** `data-service/tests/recognition_eval/corpus.py:71-106`
(`REQUIRED_PROVENANCE_FIELDS` + `assert_provenance` + `ProvenanceError`), with
`test_recognition_eval.py:543-556` and `:658` as the refusal call sites.
**Apply to:** the extended D-19 field tuple, `test_provenance.py`, and the LLM report
row pipeline — a sample missing any required field is void, never scored.

### 5. Machine-checked fenced block + both-directions drift guard

**Source:** `spec/SWRL-SUBSET.md:55-70, 117-128` (marker pairs) +
`DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs:215-309` (loader + both-directions
assert) + the enforcement prose at `SWRL-SUBSET.md:168-186`.
**Apply to:** `spec/REPRODUCIBILITY.md`'s D-26 scope table and the new drift test,
whatever its language. Include the induced-mismatch proof step.

### 6. Dual-format report emission

**Source:** `tools/de01/report.py:347-406` (`emit_json_report` +
`emit_markdown_report`, JSON indented+`ensure_ascii=False`, Markdown with verdict
header and per-leg table); LLM-side twin `recognition_eval/report.py:352-445`
(`render_markdown` with Wilson CI + `render_json`).
**Apply to:** both 1204 reports (deterministic repeat report and LLM repeatability
report), each with its own schema per D-24.

### 7. Secret hygiene (D-28 + RESEARCH.md Security Domain)

**Source:** `data-service/llm_gateway.py:637-668` (Fernet `encrypt_value`/
`decrypt_value` — never a second path to plaintext; `mask_key` at 668);
`cassette.py:197-204` (refuse placeholder keys at the live boundary);
`test_recognition_eval.py:159-187` (prompt bodies stored only for `ip_class="own"`);
`live_sweep.py:82` (`mask_url`).
**Apply to:** `repeat_sweep.py`, the provenance-block emitter, and every live-run
task: keys enter only via the LLM settings panel/`/llm/settings`; reports and cassettes
never contain keys, credential-bearing URLs, or third-party prompt bodies.

### 8. Frozen-fixture sibling-path discipline

**Source:** `fixtures/golden/MANIFEST.md:41-57` (freeze policy, change-reason log) and
`:6-9` (additive sibling under its own lighter discipline).
**Apply to:** `fixtures/llm_repeatability/` — new material in a sibling path, the frozen
1200 fixtures and Phase 35 cassettes (`data-service/fixtures/recognition_eval/cassettes/`,
verified on disk A0-A4) never edited; every frozen prompt carries sha256 + provenance.

### 9. Adapter-resolve-once, generate-in-loop

**Source:** `data-service/cg_recognition.py:977-979` and
`data-service/dg_context.py:960-988` (both verified): resolve provider/adapter once,
call `adapter.generate()` in-process per attempt — never re-POST `/llm/generate`.
**Apply to:** `repeat_sweep.py` (k samples per (provider, item)), including for the
rule-ingest subject where `options=None` (D-10, "not sent — provider default").

---

## Research Discrepancies (planner must act on these)

| RESEARCH.md claim | Disk truth (verified 2026-09-23) | Impact |
|---|---|---|
| "extend existing test file `data-service/tests/recognition_eval/test_cassette.py`" | **No `test_*.py` exists under `data-service/tests/recognition_eval/`.** Cassette tests live in `data-service/tests/test_recognition_eval.py` (`TestCassette` at :63, the flip test at :88). | The sample-index tests extend `test_recognition_eval.py`, not a new/existing `test_cassette.py`. |
| Wave 0 lists `test_outcome_taxonomy.py` and `test_provenance.py` as new files in `recognition_eval/` | Correct as *new* files, but they must follow the `test_recognition_eval.py` bootstrap (sys.path + `LLM_MASTER_SECRET`), since no sibling test-file precedent exists in that directory. | No per-module test-file precedent inside `recognition_eval/`; use the `tests/`-level file's bootstrap. |
| D-26 drift test placed at `tools/de01/tests/test_reproducibility_scope_drift.py` (Python) | The repo's only drift-guard precedent is **xUnit**: `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`. | Planner chooses Python (scanning `data-service/*.py`) or C#; either is defensible, but "modeled on the existing guard" means that C# file, and its both-directions + induced-mismatch discipline. |
| "`spec/API.md` documents the new fields" (D-20) | `spec/API.md` exists (verified) but contains **no `/llm/generate` or GenerateResponse documentation at all** — grep over `llm/generate|GenerateResponse|response_id|fingerprint|served` found nothing; LLM appears only via `/computgraph/consult` (`:64,128`). | The D-20 docs are a new subsection, not an edit of an existing route doc. |

---

## No Analog Found

None — every file in the classification table has at least a role-match analog verified on
disk. Three partials, for the planner's attention:

| File | Reason |
|---|---|
| `data-service/tests/recognition_eval/outcome_taxonomy.py` | No single existing module holds the D-14 taxonomy; the classification logic is spread across `cg_recognition.py`'s guard stack and `dg_context.py`'s `validate_cypher` codes. This is the one genuinely new *aggregation* module — its inputs, not its patterns, are new. |
| D-12 frozen-prompt rendering script (discretion) | No committed one-off rendering script exists to copy; assemble the pattern from `legs.py:190-207` (httpx POST) + the read-only `n8n/workflows/rules-to-metagraph.json` "Build LLM Prompt" node. |
| Repeat report emitter | No repeat-report emitter exists (the report is new); copy the dual-emission *mechanics* from `report.py:347-406` but author the repeat schema fields from D-02/D-04/D-07. |

---

## Metadata

**Analog search scope:** `tools/de01/` (all files), `data-service/` (`canonical_json.py`,
`evidence_contract.py`, `llm_gateway.py`, `cg_recognition.py`, `dg_context.py`, `app.py`
routes), `data-service/tests/` (incl. `recognition_eval/` and `fixtures/`),
`DG/tests/DG.Tests/`, `spec/`, `fixtures/golden/`, `n8n/workflows/`, `CLAUDE.md`.
**Files scanned:** 24 analog files read in full or targeted ranges; every cited path
verified to exist on disk first.
**Pattern extraction date:** 2026-09-23
**Frozen inputs (do NOT propose modifying):** `tools/de01/legs.py`, `tools/de01/report.py`
(`compare_legs`), `data-service/canonical_json.py`, `cassette.py`'s eight-part key core,
`fixtures/golden/*`, `data-service/fixtures/recognition_eval/cassettes/`,
`spec/EVIDENCE-CONTRACT.md` §6 nested-payload rules.
