# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture - Pattern Map

**Mapped:** 2026-09-20
**Files analyzed:** 11 (new) + 3 (touched, non-structural)
**Analogs found:** 8 strong / 2 partial / 1 explicit no-analog

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `spec/EVIDENCE-CONTRACT.md` | config/spec (normative doc) | transform (defines shape/semantics consumed by 4 legs) | `spec/RULE-PARTITION-POLICY.md` | exact (structural doc pattern) |
| `spec/evidence-contract.schema.json` | config (JSON Schema) | transform | none in-repo (new artifact class) | no analog — see below |
| `data-service/canonical_json.py` (or similar; hashing helper) | utility | transform | `data-service/dg_identity.py::compute_dg_id` | exact (cross-language hash precedent) |
| `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` (or similar) | utility | transform | `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` | exact (C# mirror of the same hash contract) |
| `DG/src/DG.Core/Contracts/EvidenceStatus.cs` (typed status enum) | model | transform | `DG/src/DG.Core/Models/ReinstatementStatus.cs` | exact (plain C# enum, switch-consumed by a Services helper) |
| `DG/src/DG.Core/Contracts/EvidenceEnvelope.cs` (envelope DTO) | model | transform | `DG/src/DG.Core/Models/DesignStateParameter.cs` (small DTO) + `data-service` Pydantic models below | role-match |
| `data-service/evidence_envelope.py` (Pydantic envelope models) | model | transform | `data-service/app.py` `ValidationPublishEntityPayload`/`ValidationPublishRequest` (lines 264-287) | exact (Pydantic response/request model style) |
| `data-service` publish-path additive write of envelope sidecar | service (persistence) | CRUD (write) | `data-service/app.py::_persist_shacl_report` (lines 2085-2103) | exact (identical sidecar-JSON pattern) |
| `data-service` publish-path additive read of envelope sidecar | service (persistence) | CRUD (read) | `data-service/app.py::_parse_shacl_report` (lines 874-887) + its use at line 910 | exact |
| `fixtures/golden/fixture.json` | fixture data | file-I/O | `dg-reasoner/tests/fixtures/metagraph_fixture.json` (structure) + `test/fixture_geometry.json`/`test/fixture_rules_v7.txt` (ad-hoc precedent D-09 explicitly supersedes) | role-match |
| `fixtures/golden/seed.cypher` | migration/seed script | batch (Cypher seed) | `test/seed_designstates.cypher`, `test/seed_validation_run.cypher` | exact |
| `tools/de01/run_de01.py` (DE-01 runner) | service (standalone harness) | event-driven / batch (drives 4 legs, emits report) | none in-repo — explicitly new (RESEARCH.md: "no existing cross-service harness exists to extend") | no analog — see below |
| `tools/de01/report_schema.json` + Markdown report emitter | utility (report emitter) | transform | `dg-reasoner/reasoning.py::run_shacl` (envelope shape) + `data-service/app.py::_persist_shacl_report`/`_parse_shacl_report` pair (closest "structured report artifact" precedent) | partial |
| `data-service/tests/test_evidence_contract.py` | test | request-response (schema validation) | `data-service/tests/test_validation_runs_state.py` | role-match |
| `DG/tests/DG.Tests/EvidenceContractTests.cs` (+ fixture wiring) | test | transform | `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` (golden-vector test style) + `DG.Tests.csproj` fixture-copy rule | exact |
| `docker-compose.yml` (dg-reasoner fixture mount, additive) | config | file-I/O | existing `./ontology:/app/ontology:ro` line on the `dg-reasoner` service | exact |

## Pattern Assignments

### `spec/EVIDENCE-CONTRACT.md` (config/spec)

**Analog:** `spec/RULE-PARTITION-POLICY.md`

**Structure to copy** (verified full read):
- Title + one-paragraph **Overview** naming exactly what normative contract this document is and which requirement IDs it satisfies (RULE-PARTITION-POLICY.md lines 1-5: "This document is the **normative partition contract**... It fulfills requirement **SHCL-01**"). EVIDENCE-CONTRACT.md should open the same way, citing ALGN12-01..04.
- A **table-of-contents-as-anchor-list** immediately after Overview (lines 7-14), each bullet a `[Section](#anchor)` — do the same for Status Vocabulary / Envelope Shape / Canonical Hashing / Golden Fixture / DE-01 Acceptance / v11.0 1105 Handoff.
- A **decision-table pattern** for "what belongs where" (lines 37-51: `| Rule Category | Example | System | Rationale |`) — EVIDENCE-CONTRACT.md's status table already exists verbatim in CONTEXT.md D-05 and should be transplanted in this exact table shape (`| Situation | Canonical status |`).
- **Cross-reference discipline**: RULE-PARTITION-POLICY.md's final section "Consistency & Propagation" (lines 172-175) explicitly states which other spec files/CLAUDE.md sections must be reviewed when this doc's subject changes — EVIDENCE-CONTRACT.md needs an equivalent closing section per D-15 (the v11.0 1105 handoff), naming `CLAUDE.md` § Schema Change Propagation explicitly, exactly as RULE-PARTITION-POLICY.md does not do but per D-15 should.
- **Addendum convention**: sections added after the original phase without a lettered decision use "This is an addendum, not a new numbered decision -- no `D-` number is assigned" (lines 74-76, 95-97, 122-126) — reuse this phrasing verbatim if 1200 needs to append anything post-hoc.
- **Enforcement section names the mechanism honestly** (lines 144-150): "documentation and review discipline... An automated linter is explicitly deferred... this is a known, accepted gap." EVIDENCE-CONTRACT.md should state equally plainly that DE-01 is the *only* mechanical enforcement (per D-01's own text: "DE-01 validates every leg's output against the schema mechanically rather than by reading").
- **CLAUDE.md cross-reference**: RULE-PARTITION-POLICY.md is referenced from `CLAUDE.md` § Schema Change Propagation ("consult it before adding a new SHACL shape..."). `CLAUDE.md` must gain an equivalent line for `spec/EVIDENCE-CONTRACT.md` (this is itself a propagation-list touch mandated by D-16 as "1200's own additive changes require").

**No analog for the JSON Schema annex** (`spec/evidence-contract.schema.json`): no JSON Schema file exists anywhere in this repo today (confirmed by RESEARCH.md's Wave-0 gap list — "nothing can be schema-validated until this exists"). Build it fresh per D-01 using the status/envelope field tables already fully specified in CONTEXT.md — there is no in-repo shape to imitate, only the general "$defs for {Status, Envelope}" structure RESEARCH.md's Recommended Project Structure section already lays out.

---

### Cross-language deterministic hashing (D-07 scalar-join portion)

**Analog pair — read in full both sides:**

**Python** — `data-service/dg_identity.py:52-63`:
```python
def compute_dg_id(project: str, definition_id: str, cg_id: str) -> str:
    """Mint a deterministic dgId from the pipe-joined triple ``project|definitionId|cgId``.

    Byte-identical to DG.Core ``DgIdMintingService.Mint``: SHA-256 the UTF-8 input,
    render the digest as UPPERCASE hex (matching .NET ``Convert.ToHexString``), take
    the first 16 hex chars, and prefix with ``dg:``.
    """
    input_str = f"{project}|{definition_id}|{cg_id}"
    digest = hashlib.sha256(input_str.encode("utf-8")).hexdigest().upper()
    return DGID_PREFIX + digest[:16]
```

**C#** — `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` (full file, 51 lines):
```csharp
public static class DgIdMintingService
{
    private const string DgIdPrefix = "dg:";

    public static DgId Mint(string project, string definitionId, string cgId)
    {
        if (string.IsNullOrWhiteSpace(project))
            throw new ArgumentException("project must be a non-empty value.", nameof(project));
        // ... same guard for definitionId, cgId ...

        var input = $"{project}|{definitionId}|{cgId}";
        return new DgId(DgIdPrefix + HashToHex16(input));
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
```

**How the two are kept in sync today:** the C# XML-doc comment (lines 17-21) states the parity contract explicitly in prose ("Any change to the hash-input contract here breaks cross-platform identity parity with the data-service `compute_dg_id` implementation and is guarded by the golden-vector test") and the Python docstring's module header (`dg_identity.py:17-20`) states the mirror-image claim. **There is no shared test-data file** — parity is asserted by two independently-written test suites each pinning the *same literal* golden vector as a hardcoded string/assertion, not a shared fixture. RESEARCH.md cites the concrete golden vector already in use: `(p1|frame.gh|cg:1:proc:11_Proc) -> dg:BC8E62EE137E2B56` (per STATE.md). **This is exactly the model to copy for the new envelope hash**, per RESEARCH.md's own recommendation: write 3-5 fixed input/output pairs as literal test data duplicated (not shared via a file import) into both `DG.Tests` and `data-service/tests`, mirroring this existing golden-vector convention rather than inventing file-sharing infrastructure.

**Divergence for the envelope's nested-payload hash (D-07's harder half):** neither side has a precedent for canonical-JSON-of-a-nested-object hashing — this must be hand-rolled per RESEARCH.md's normalization spec (sorted keys, decimal-not-double, NFC, `ensure_ascii=False`/`UnsafeRelaxedJsonEscaping`). The `RuleEvaluator.cs::TryToDecimal` convention (never `double`) is the one existing precedent worth copying forward for the numeric-formatting rule (`RuleEvaluator.cs` uses `decimal` throughout, confirmed at lines 120-132 read this session).

**Security pattern to copy for `fixtures/golden/seed.cypher`'s executing code:** every `dg_identity.py` function passes identifiers as a parameter dict, never string-interpolated — e.g. `mint_identity` (lines 176-190): `session.run("""MERGE (e {cgId: $cgId, ...})""", {"project": project, ...})`. The seed-script executor for D-10 must follow this exact discipline.

---

### Sidecar JSON property on `Run` (D-08)

**Analogs — WRITE side:** `data-service/app.py:2085-2103` (`_persist_shacl_report`):
```python
def _persist_shacl_report(project: str, run_id: str, report_json: str) -> None:
    """Persist a SHACL status dict as `shaclReportJson` on the ValidationRun node.

    Additive, second write after `store_validation_run` -- ordering of the
    Speckle publish + store_validation_run is unchanged (D-06). Parameterized
    MERGE/SET keyed by {graph, project, runId}; never string-interpolated.
    """
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET run.shaclReportJson = $shaclReportJson
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id, "shaclReportJson": report_json},
    )
```
This is the exact shape to copy for writing `evidenceEnvelopeJson` (or whatever field name the planner picks): same MERGE-by-key, same SET-only-the-new-property, same docstring convention naming which existing write it is additive *after*.

**Analog — READ side:** `data-service/app.py:874-887` (`_parse_shacl_report`) and its use at `app.py:910`:
```python
def _parse_shacl_report(shacl_report_json: str | None) -> dict[str, Any] | None:
    """Parse a persisted `shaclReportJson` string into a dict for the view payload.

    Returns None for absent/empty/malformed JSON or a non-object payload --
    never raises. Pre-823 runs (no shaclReportJson property) and corrupt data
    both degrade to the same quiet not-checked state (D-17), never an error.
    """
    if not shacl_report_json:
        return None
    try:
        parsed = json.loads(shacl_report_json)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None
```
Used at the view-assembly site: `"shaclReport": _parse_shacl_report(run.get("shaclReportJson"))`. **This is the exact "absence means not-recorded, never an error" pattern D-08 explicitly requires** — copy the try/except-returns-None shape verbatim for the new evidence-envelope reader, and copy the docstring's "degrade to the same quiet not-checked state" phrasing for consistency.

**Cypher shape reference (schema comment, not code):** `spec/DATABASE.md:108,114-115`:
```
(:Run {Run_Id: "VRUN_abc123", ValidStatus: [true, false, true], SendStatus: true,
       statePayloadJson: '{...}', shaclReportJson: '{...}', graph: "ValidGraph", project: "1"})
```
`spec/DATABASE.md:115` documents the "absence = not checked" rule at the schema-doc level too — the new envelope property needs an equivalent line in `spec/DATABASE.md` under the same `Run` node section (this is itself a D-16-mandated propagation touch, not optional).

**Second write site** (Cypher session, not query_write wrapper): `data-service/dsav_watcher.py:193,530` shows the same property name reused in a different write path (`run.shaclReportJson = $shaclReportJson` inside a larger MERGE) — if the envelope is written from more than one stage boundary (D-06 requires per-stage emission), `dsav_watcher.py`'s multi-field SET clause is the pattern for adding the new property alongside others in one write rather than a second round-trip.

---

### Seed-script pattern (D-10)

**Analog:** `test/seed_designstates.cypher` (read in full for header + first block):
```cypher
// ============================================================================
// Seed: 14-03 DesignState seeding — Wave 0 precondition for SCHM-13
// ============================================================================
//
// PURPOSE
//   Inserts a realistic mix of pre-v4 DesignState nodes into the dev
//   database so the 14-06 kind-migration script (D-09/D-10) has real data
//   to exercise rename, layer-move, and orphan-delete against.
//
// EXECUTION METHOD
//   This script is for dev databases only. Run it as a single block in
//   Neo4j Browser (paste all + Ctrl+Enter). Each statement is separated
//   by a semicolon followed by a blank line — Neo4j Browser recognizes
//   this pattern as multi-statement input.
//
//   Alternatively: cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f test/seed_designstates.cypher
//
// WARNING — DEV DATABASES ONLY
// ============================================================================

MERGE (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke', graph: 'Metagraph'})
  SET r1.SendStatus = false, r1.ValidStatus = []
;
```
**Invocation model confirmed:** there is **no runner/pytest fixture** that executes these — the header block is explicit that it's manual (`cypher-shell -f ...` or paste into Neo4j Browser). This is the precedent D-10 should follow for `fixtures/golden/seed.cypher`: a documented manual/scripted invocation, not a hidden pytest fixture. If DE-01's persisted-replay leg needs it invoked programmatically, wrap this exact file with a thin subprocess call (`cypher-shell -f fixtures/golden/seed.cypher`) rather than reimplementing the seed logic inline in Python — same "file is the source of truth" principle D-09/D-10 state for the fixture itself.

**Parameterization note:** unlike `dg_identity.py`'s runtime queries, `seed_designstates.cypher` embeds literal values directly (`'seed-run-01'`, `'phase14-smoke'`) because it is a static, checked-in dev-only script, not a parameterized runtime query — this is consistent with RESEARCH.md's threat-model note ("the `.cypher` file itself is static and checked in, so the injection risk is only in whatever Python/C# code executes it with fixture-derived parameters"). `fixtures/golden/seed.cypher` should follow the same static-literal style; only the *executor* code (if any wraps it with parameters) needs the parameterized-query discipline.

---

### Typed-outcome / status enum in C# (D-05's canonical status type)

**Analog:** `DG/src/DG.Core/Models/ReinstatementStatus.cs` (full file, 12 lines) — **this is the closest existing precedent and should be copied verbatim in shape:**
```csharp
namespace DG.Core.Models;

public enum ReinstatementStatus
{
    Applied,
    MissingTarget,
    TypeMismatch,
    AmbiguousTarget,
    OutOfRange,
    Unchanged,
    WouldApply,
}
```
A plain C# `enum`, no `[JsonConverter]` attribute, no explicit string values — serialization to/from JSON string names is left to the caller. Consuming code switches on it exhaustively: `DG/src/DG.Core/Services/ErrorMessageTemplates.cs:24-33` (`ReinstatementBlocked`):
```csharp
public static string ReinstatementBlocked(string parameterId, ReinstatementStatus status, string detail)
{
    var fix = status switch
    {
        ReinstatementStatus.MissingTarget => "Reconnect the original slider or toggle.",
        ReinstatementStatus.TypeMismatch => "Reconnect a matching slider or recapture state.",
        ReinstatementStatus.AmbiguousTarget => "Ensure only one slider has this NickName.",
        ReinstatementStatus.OutOfRange => "Adjust slider domain to include the saved value.",
        _ => "Check the parameter connection.",
    };
    return $"Reinstatement blocked: parameter '{parameterId}' {detail}. {fix}";
}
```
**Recommendation for the new `EvidenceStatus` enum:** copy this exact shape — a bare `public enum EvidenceStatus { Passed, Failed, Unknown, NotEvaluated, NoPopulation, Unsupported, Indeterminate, Error }` in `DG.Core.Models` (or a new `DG.Core.Contracts` namespace per Open Question #1 in RESEARCH.md) — **no existing enum in this codebase uses `System.Text.Json`'s `[JsonStringEnumConverter]` or any custom converter**, confirmed by grep of all 10 enum files in `DG.Core/Models`. If the JSON Schema annex requires exact lower-snake-case string values (`no_population`, not `NoPopulation`), a `JsonStringEnumConverter` with a naming policy (or explicit `[JsonPropertyName]`-style per-value mapping via a converter) will be **new infrastructure**, not a copy of an existing pattern — flag this explicitly to the planner as a gap: **there is no existing serialization-mapping precedent for enum-to-non-PascalCase-string in this codebase.**

`SerializationError.cs` and `AtomSide.cs` were also checked (both are bare enums, same shape, no converters) — confirms the "no analog" finding is not an oversight of one file but a house-wide absence of custom enum JSON mapping.

---

### Structured report artifact pair (D-12, DE-01 emits JSON + Markdown)

**Closest analog — the sidecar-JSON envelope pair itself** (`_persist_shacl_report`/`_parse_shacl_report`, shown above) is the nearest "structured report artifact" precedent, but it is a **single JSON blob persisted to Neo4j**, not a **JSON + separate human-readable Markdown pair** — the Markdown half has no analog anywhere in the repo (confirmed: no `.md` report-generation code found in `data-service`, `dg-reasoner`, or `DG.Core`).

**Second-closest analog — `dg-reasoner/reasoning.py:473-521`'s `run_shacl`** is the best precedent for the *report's internal shape* (not its file format): a function that returns one of two typed envelope shapes — success `{conforms, results, counts}` or typed-failure `{conforms: None, error: "timeout", timeout_seconds: ...}` — and the caller never has to guess which shape it got by inspecting exceptions:
```python
result = _run_shacl_with_timeout(data_graph, shapes_graph, DG_REASONER_TIMEOUT_SECONDS)
if result.get("timeout"):
    return {"conforms": None, "error": "timeout", "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS}
findings = [_enrich_shacl_result(raw, data_graph, shapes_graph) for raw in result["raw_results"]]
counts = {"violation": 0, "warning": 0, "info": 0}
for finding in findings:
    counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
conforms = not any(finding["severity"] == "violation" for finding in findings)
return {"conforms": conforms, "results": findings, "counts": counts}
```
This dual-shape-return convention (counts dict built by iterating findings and incrementing a per-severity bucket) is exactly the shape DE-01's own report should use for its per-status tally, and its typed-failure branch (`{conforms: None, error: "timeout", ...}`) is the direct precedent D-13 cites for per-leg graceful degradation.

**GSD reconciliation ledger** (`.planning/reconciliation/GSD-ALIGN-RECONCILIATION.md`, referenced but not read this session — out of scope for source-code pattern extraction) is a **Markdown-only** artifact with no JSON sibling; it is not a strong analog for a JSON+Markdown *pair* but confirms the repo's general willingness to produce a narrative Markdown ledger alongside a machine-readable JSON register (`gsd-proposed-updates.json`) for the same underlying facts — this pairing convention (one JSON, one prose Markdown, both describing the same reconciliation) is the closest structural precedent for DE-01's own JSON-report + Markdown-summary pairing, even though it lives in `.planning/` tooling rather than application code.

**Verdict: partial match only.** No file in the runtime codebase produces a JSON+Markdown report pair. The planner should treat `tools/de01/`'s report emitter as build-from-spec against `reasoning.py`'s typed-envelope convention for the JSON side, and accept there is no in-repo Markdown-report-generation code to imitate for the human-readable side.

---

### Pydantic response/request models (envelope shape in Python)

**Analog:** `data-service/app.py:264-287` (`ValidationPublishEntityPayload`, `ValidationPublishRequest`):
```python
class ValidationPublishEntityPayload(BaseModel):
    dgEntityId: str
    displayName: str | None = None
    geometry: ValidationGeometryPayload | None = None
    ruleIds: list[str] = Field(default_factory=list)
    failedRuleIds: list[str] = Field(default_factory=list)
    passedRuleIds: list[str] = Field(default_factory=list)
    overallStatus: str = "unknown"


class ValidationPublishRequest(BaseModel):
    project: str
    statePayloadJson: str | None = None
    validStatus: list[bool] | None = None
    rules: list[ValidationPublishRulePayload] = Field(default_factory=list)
    ruleResults: list[ValidationPublishRuleResultPayload] = Field(default_factory=list)
    entities: list[ValidationPublishEntityPayload] = Field(default_factory=list)
```
Note line 271: `overallStatus: str = "unknown"` is the exact **untyped string** field RESEARCH.md flags as one of the three dialects DE-01 must reconcile — this is a live example of the defect, not just a style precedent. The new envelope's Pydantic model should replace this free-string pattern with a `Literal["passed","failed","unknown","not_evaluated","no_population","unsupported","indeterminate","error"]` type (or a Python `Enum`) — copy the **field-composition style** (nested payload models, `Field(default_factory=list)` for arrays, `str | None = None` for optional cross-references) but not the untyped-string status field itself.

---

### xunit test layout / fixture wiring (D-09's shared fixture path)

**Analog:** `DG/tests/DG.Tests/DG.Tests.csproj:27-28`:
```xml
<None Include="Fixtures\**\*.json">
  <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
</None>
```
This only copies fixtures from a project-local `Fixtures\` folder — it does **not** reach a top-level repo `fixtures/golden/` directory outside `DG/tests/DG.Tests/`. **D-09 requires all four legs read the same bytes from one top-level location**, so this `.csproj` rule needs a **new, additive** `<None Include>` entry pointing at the repo-root fixture path (e.g. `<None Include="..\..\..\fixtures\golden\**\*.json"><Link>Fixtures\golden\%(RecursiveDir)%(Filename)%(Extension)</Link><CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory></None>`) — copy the existing line's `CopyToOutputDirectory` value and glob style, but the `..\..\..\` relative-path climb out of `DG/tests/DG.Tests/` to repo root is new territory with no existing analog (no `.csproj` in this repo currently reaches outside its own project directory for fixtures).

**Golden-vector test style analog:** `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` (test names only, confirmed via graphify + grep, not fully read this session — names are self-describing and consistent with the file's role): tests like `.ComputeParamStateId_ShouldBeDeterministic_RegardlessOfInputOrder()` and `.ComputeObjectStateId_ShouldHaveExactlyThreeStringParameters_ProvingCrossRuleIdentity()` establish the **"ShouldBeDeterministic" / "ShouldChange_When..."** naming convention to copy for the new canonical-hashing golden-vector tests (`EvidenceEnvelopeHash_ShouldBeDeterministic_ForSameInputs`, etc.).

---

### `ErrorMessageTemplates` What+Where+How-to-fix pattern (warnings field)

**Analog:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs:1-45` (read in full):
```csharp
public static class ErrorMessageTemplates
{
    public static string SerializationFailed(string parameterId, SerializationError error)
    {
        return error switch
        {
            SerializationError.NoStateProvided =>
                $"State capture failed: no state provided for parameter '{parameterId}'. Connect a DESIGN STATE component upstream.",
            SerializationError.MalformedStatePayload =>
                $"State serialization failed: parameter '{parameterId}' produced invalid payload. Disconnect and reconnect the parameter input.",
            // ...
        };
    }
    // ReinstatementBlocked, ValidationInputMissing, PublishFailed follow the same
    // "What failed : Where (parameter/rule/project id) : How to fix" sentence template
}
```
Every method here follows one fixed sentence grammar: **`"<What> failed: <Where, quoted> <detail>. <How-to-fix imperative sentence>."`** This is exactly the shape CONTEXT.md wants carried into the envelope's `warnings` field (per `spec/RULE-PARTITION-POLICY.md:166`'s cross-reference to this same file for SHACL findings — "every SHACL finding is translated through the same **What+Where+How-to-fix** pattern used by `ErrorMessageTemplates`"). The new envelope's `warnings: list[str]` entries should be generated through a new `EvidenceMessageTemplates`-style static class following this identical switch-per-status-with-embedded-fix-imperative structure, not ad-hoc string formatting scattered across the four legs.

## Shared Patterns

### Additive-not-breaking (repo house style)
**Source:** D-03's own citations — `spec/DATABASE.md:114-115` (`shaclReportJson` added Phase 823), Phase 824's additive heartbeat, Phase 38's nullable `reinstateParameterId`.
**Apply to:** every new field in the envelope, the new sidecar property, and the new `EvidenceStatus` field — always a new parallel field/property, never a rename or removal of an existing boolean surface (`Passed`, `Run.ValidStatus`, `conforms`).

### Absence-means-not-recorded, never an error
**Source:** `data-service/app.py:874-887` (`_parse_shacl_report`), `spec/DATABASE.md:115`.
**Apply to:** the new envelope sidecar reader; the DE-01 runner's per-leg degradation (D-13); any consumer of a pre-1200 `Run` node lacking the new envelope property.

### Parameterized Cypher, never string-interpolated
**Source:** `data-service/dg_identity.py:34-36` (module docstring) and every function body in that file (e.g. `mint_identity`, lines 176-190).
**Apply to:** `fixtures/golden/seed.cypher`'s executor code (if any), and any new envelope-persistence query in `data-service`.

### What+Where+How-to-fix message template
**Source:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`.
**Apply to:** the envelope's `warnings` field content, wherever generated (C# leg, Python legs).

### Bare C# enum, no custom JSON converter
**Source:** `DG/src/DG.Core/Models/ReinstatementStatus.cs`, `SerializationError.cs`, `AtomSide.cs` (10/10 enum files checked, none use a converter).
**Apply to:** `EvidenceStatus.cs` — but flag the naming-convention gap explicitly (see below).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `spec/evidence-contract.schema.json` | config (JSON Schema) | transform | No JSON Schema file exists anywhere in this repo today; there is no in-repo shape convention to imitate, only RESEARCH.md's own recommended `$defs`-based structure |
| `tools/de01/run_de01.py` (the DE-01 runner itself) | service (standalone harness) | event-driven/batch | RESEARCH.md confirms explicitly: "no existing cross-service harness exists to extend" — no `.github/workflows`, no existing `tools/` or `scripts/` cross-service test driver found anywhere in the repo |
| DE-01's JSON+Markdown report pair (the Markdown half specifically) | utility (report emitter) | transform | No Markdown-report-generation code exists in `data-service`, `dg-reasoner`, or `DG.Core`; nearest adjacent things are `_persist_shacl_report`'s JSON-only sidecar and the `.planning/reconciliation/` ledger's Markdown-only + separate-JSON-register pairing (a planning-tooling artifact, not application code) — neither is a real match for one component emitting both formats together |
| C# enum → non-PascalCase JSON string serialization (`EvidenceStatus` → `"no_population"`) | model (serialization mapping) | transform | Zero existing enums in `DG.Core` use `[JsonStringEnumConverter]`, a naming policy, or any custom converter; this is new infrastructure the planner must design from scratch, not copy |
| `.csproj` fixture reference reaching outside its own project directory to a repo-root `fixtures/golden/` | test config | file-I/O | No `.csproj` in the repo currently reaches above its own project folder for `<None Include>`/fixture copying; the existing pattern (`DG.Tests.csproj:27-28`) is same-directory-relative only |

## Metadata

**Analog search scope:** `data-service/` (app.py, dg_identity.py, dsav_watcher.py), `DG/src/DG.Core/` (Models/, Validation/, Services/, Models/Identity/), `DG/tests/DG.Tests/` (csproj, test file names via graphify), `dg-reasoner/reasoning.py`, `spec/` (RULE-PARTITION-POLICY.md, DATABASE.md), `test/*.cypher` seed scripts.
**Files scanned (read in full or targeted range):** `data-service/dg_identity.py` (full), `spec/RULE-PARTITION-POLICY.md` (full), `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` (full), `data-service/app.py` (lines 238-287, 870-912, 2080-2104), `DG/src/DG.Core/Models/ReinstatementStatus.cs` (full), `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` (lines 1-45), `dg-reasoner/reasoning.py` (lines 470-521), `test/seed_designstates.cypher` (header + first block), `DG/src/DG.Core/Validation/RuleEvaluator.cs` (lines 1-140), `spec/DATABASE.md` (grep hits at 90-115), `DG.Tests.csproj` (fixture rule grep).
**Pattern extraction date:** 2026-09-20
