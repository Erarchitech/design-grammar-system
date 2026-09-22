# Phase 1203: Identity Convergence and `ATTRIBUTE_OF` Decision - Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 15 (new/modified, both workstreams)
**Analogs found:** 13 / 15

**Graphify caveat honored:** `graphify query`/`graphify explain` were run first per the mandatory hook (queries for "PARAM_LINK derivation" and "ATTRIBUTE_OF"). Both confirmed useless for this phase's actual targets — the graph is missing `ComputeObjectStateIdFromRef`/`ComputeCaptureEventStateId` entirely, has no node for `_publish_param_links`/`_paramlinks_from_wires`, and `ATTRIBUTE_OF` only resolves to the ontology markdown/OWL declarations, not the Cypher precedent. All excerpts below were extracted from direct disk reads, each verified against the live file in this session (line numbers may drift by 1-2 vs. CONTEXT.md/RESEARCH.md's citations — this file uses the freshly re-verified numbers).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/computgraph_publish.py` — new `_attribute_of_from_bindings()` | service (derivation function) | transform | `_paramlinks_from_wires()` (`computgraph_publish.py:414-434`, same file) | exact |
| `data-service/computgraph_publish.py` — new `_publish_attribute_of()` | service (Cypher writer) | CRUD (MERGE) | `_publish_param_links()` (`computgraph_publish.py:689-703`, same file) | exact |
| `data-service/cg_input_bindings.py` — no new code, read-only reuse of `classify_rule`/`read_rule_limit` | service (resolver, unchanged) | transform | itself — reused as-is per D-02 | n/a (no new file) |
| `ontology/dg-shapes.ttl` — new `dgsh:AttributeOfShape` (or similar relation/property shape) | config (SHACL schema) | — | `dgsh:ParameterShape` (`:461-503`) as target-node template; no existing relation-level shape exists — see "No Analog Found" | role-match (node shape only) |
| `spec/RULE-PARTITION-POLICY.md` — new decision-table row for cross-layer bridge relations | config (doc) | — | existing table rows (`:39-51`) | exact (same table, new row) |
| `spec/DG-ID.md` — new DesignState-ID section (D-06) | config (spec doc) | — | existing `dgId` sections (`:34-90`) in the same file | exact |
| `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — D-08 (project-in-hash) + D-09 (length-prefix) applied to 4 functions | utility (pure hashing) | transform | itself, `ComputePropStateId` (`:142-160`) is the best in-file template (already folds an optional extra field) | exact |
| `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` — D-09 length-prefix on `Mint` | utility (pure hashing) | transform | itself (`:32-43`) | exact |
| `data-service/dg_identity.py` — `compute_dg_id` D-09 fix; `mint_identity` D-10 (CR-01 label-aware) + D-11 (WR-01 graph tag) | service (identity persistence) | CRUD | itself (`:52-63`, `:166-189`) | exact |
| `data-service/dg_context.py` — delete `ALLOWED_PROPERTIES` (D-11) | utility (dead code removal) | — | n/a — deletion only | n/a |
| `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — new project-in-hash + collision regression facts | test | unit | existing file's own golden-vector fact style (see `DgIdMintingServiceTests.cs` below as sibling template) | exact |
| `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs` — updated golden vector + new collision regression fact | test | unit | itself (`:16-65`) | exact |
| `data-service/tests/test_dg_identity.py` — updated golden vector + collision + mint→bind→publish-coincidence regression | test | unit/integration | itself (existing golden vector block, confirmed byte-identical companion to the C# file) | exact |
| `data-service/tests/test_computgraph_publish.py` (new or extended) — forward/reverse `ATTRIBUTE_OF` tests | test | integration | `test_dg_identity.py`'s `FixtureSession`/`FakeGraph` mocking style (per RESEARCH.md) | role-match |
| `fixtures/golden/<sibling-path>/` (e.g. `fixtures/golden/attribute-of/` or `cq3/`) — README + seed Cypher + result JSON | fixture (test data) | file-I/O | `fixtures/golden/replay/` (README.md, seed-replay.cypher, mixed-verdicts.json) — confirmed on disk, same sibling-path shape | exact |

## Pattern Assignments

### `data-service/computgraph_publish.py` — new `_attribute_of_from_bindings()` + `_publish_attribute_of()`

**Analog:** `_paramlinks_from_wires()` + `_publish_param_links()`, same file.

**Derivation pattern** (`computgraph_publish.py:414-434`):
```python
def _paramlinks_from_wires(wires: list[dict], parameter_rows: list[dict], interface_rows: list[dict]) -> list[dict]:
    """Derive Parameter->Interface PARAM_LINK pairs from wire adjacency.

    The envelope carries no direct Parameter<->Interface reference -- for each
    wire, if one endpoint's node id is a member of a Parameter and the other
    endpoint's node id is a member of an Interface (in either direction), emit
    one {paramCgId, interfaceCgId} link row. Deduplicated.
    """
    param_by_member: dict[str, str] = {}
    for row in parameter_rows:
        for member_id in row.get("memberIds") or []:
            param_by_member[member_id] = row["cgId"]

    iface_by_member: dict[str, str] = {}
    for row in interface_rows:
        for member_id in row.get("memberIds") or []:
            iface_by_member[member_id] = row["cgId"]

    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    for wire in wires:
        ...  # (dedup + row emission)
```
The `ATTRIBUTE_OF` equivalent (`_attribute_of_from_bindings`) follows this exact shape: pure function, no Neo4j session, takes the loaded `inputBindings` (via `cg_input_bindings.classify_rule()` results, reused unchanged per D-02) plus published `:Parameter` rows, and returns `{atomId, paramCgId, derivedFrom}` rows, deduplicated the same way.

**MERGE writer pattern** (`computgraph_publish.py:689-703`, the direct precedent — copy this structure verbatim, changing only labels/relation name):
```python
def _publish_param_links(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MATCH (p:Parameter {cgId: row.paramCgId, definitionId: $definitionId, project: $project})
          MATCH (i:Interface {cgId: row.interfaceCgId, definitionId: $definitionId, project: $project})
          MERGE (p)-[:PARAM_LINK]->(i)
        // op=PUBLISH_PARAM_LINK
        """,
        {
            "rows": params["paramLinkRows"],
            "definitionId": params["definitionId"],
            "project": params["project"],
        },
    )
```
New `_publish_attribute_of(tx, params)` matches an `:Atom {Atom_Id: row.atomId, project: $project}` (Metagraph — no `definitionId` scoping key, since `Atom` is keyed by `Atom_Id` per `cypher_template.txt:237-262`) against a `:Parameter {cgId: row.paramCgId, definitionId: $definitionId, project: $project}` (Computgraph) and `MERGE (a)-[rel:ATTRIBUTE_OF]->(p) SET rel.derivedFrom = row.derivedFrom`. **Never** f-string-interpolate the Cypher — always parameterized `UNWIND $rows`, matching the existing security pattern (`dg_identity.py`'s own docstring states every `session.run` uses parameterized dicts, never string interpolation).

**Where to wire it in:** alongside the existing call to `_publish_param_links` in whatever orchestrates the publish/accept sequence (search for its call site to find the exact insertion point — not read in this session, low risk since it's a straightforward addition of one more `_publish_X` call following the same pattern).

---

### `data-service/cg_input_bindings.py` — `read_rule_limit`'s atom-type-discriminating traversal (reused, not modified)

**Analog:** itself, `read_rule_limit` (`cg_input_bindings.py:292-304`).

```python
result = session.run(
    """
    MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
    OPTIONAL MATCH (r)-[hb:HAS_BODY]->(a:Atom {type: 'BuiltinAtom'})
    OPTIONAL MATCH (a)-[:ARG {`pos`: 1}]->(vArg:Var)
    OPTIONAL MATCH (a)-[:ARG {`pos`: 2}]->(litArg:Literal)
    RETURN a.iri AS builtinIri, hb.`order` AS bodyOrder,
           vArg.name AS variableName, litArg.lex AS lex, litArg.datatype AS datatype
    ORDER BY bodyOrder
    // op=READ_RULE_LIMIT
    """,
    {"ruleId": rule_id, "project": project},
)
```

**This is the template for D-04's forward/reverse `ATTRIBUTE_OF` queries** — filter `Atom` by `type` (here `'DataPropertyAtom'`, per `cypher_template.txt`'s A1/A2/A3 numbering where A2 is always the property-carrying atom) rather than relying on `HAS_BODY.order` position alone. RESEARCH.md's Code Examples section already has the exact forward/reverse Cypher shape — copy from there, using this file's `OPTIONAL MATCH` + labeled-property-filter style as the syntactic convention (backtick-quoted `pos`, named relationship variables like `hb`).

---

### `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — D-08 (project-in-hash) + D-09 (length-prefix)

**Analog:** itself — `ComputePropStateId` (`:142-160`) is the best in-file template since it already conditionally folds an extra field into the hash input:

```csharp
public static string ComputePropStateId(
    string ruleIri,
    string dataPropertyIri,
    DesignStateParameter propValue,
    string? objectRef = null)
{
    var lex = propValue.Type switch { ... };

    var input = string.IsNullOrWhiteSpace(objectRef)
        ? $"{ruleIri}|{dataPropertyIri}|{lex}"
        : $"{ruleIri}|{dataPropertyIri}|{lex}|{objectRef}";
    return PropStatePrefix + HashToHex16(input);
}
```

**The two other pipe-joined functions to change identically** — `ComputeObjectStateId` (3-arg, `:94-98`):
```csharp
public static string ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)
{
    var input = $"{projectId}|{objectInstanceId}|{variableName}";
    return ObjectStatePrefix + HashToHex16(input);
}
```
and `ComputeObjectStateIdFromRef` (`:128-133`, currently has NO `project` parameter at all — D-08 requires adding one):
```csharp
public static string ComputeObjectStateIdFromRef(string objectRef, string? classIri)
{
    const string NoClassIriSentinel = "\u0000no-class-iri\u0000";
    var input = $"{objectRef}|{classIri ?? NoClassIriSentinel}";
    return ObjectStatePrefix + HashToHex16(input);
}
```
`ComputeParamStateId` (`:68-87`) folds no `project` today either (loops over sorted `parameters`, no project field) — same fix needed there.

**`HashToHex16`** (`:212-216`, unchanged by this phase, just the *input* to it changes):
```csharp
private static string HashToHex16(string input)
{
    var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
    return Convert.ToHexString(hash)[..16];
}
```

**Length-prefix format (D-09, Claude's Discretion):** apply consistently as `len:value|len:value|...` (e.g. `$"{project.Length}:{project}|{definitionId.Length}:{definitionId}|{cgId.Length}:{cgId}"`) to every pipe-joined input in this file and in `DgIdMintingService.Mint`/`compute_dg_id` — must be byte-identical across C#/Python.

---

### `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` — D-09 length-prefix on `Mint`

**Analog:** itself (`:32-43`):
```csharp
public static DgId Mint(string project, string definitionId, string cgId)
{
    if (string.IsNullOrWhiteSpace(project))
        throw new ArgumentException("project must be a non-empty value.", nameof(project));
    if (string.IsNullOrWhiteSpace(definitionId))
        throw new ArgumentException("definitionId must be a non-empty value.", nameof(definitionId));
    if (string.IsNullOrWhiteSpace(cgId))
        throw new ArgumentException("cgId must be a non-empty value.", nameof(cgId));

    var input = $"{project}|{definitionId}|{cgId}";
    return new DgId(DgIdPrefix + HashToHex16(input));
}
```
Only line 41 (`var input = ...`) changes to the length-prefixed form; validation/exception-throwing pattern is untouched and should be preserved as the template for any new argument validation elsewhere in this phase (e.g., if `/identity/mint` gains an entity-kind argument, D-10).

---

### `data-service/dg_identity.py` — D-09 (`compute_dg_id`), D-10 (CR-01 `mint_identity` label-aware), D-11 (WR-01 graph tag)

**Analog:** itself (`:52-63`, `:166-189`):
```python
def compute_dg_id(project: str, definition_id: str, cg_id: str) -> str:
    """Mint a deterministic dgId from the pipe-joined triple ``project|definitionId|cgId``. ..."""
    input_str = f"{project}|{definition_id}|{cg_id}"
    digest = hashlib.sha256(input_str.encode("utf-8")).hexdigest().upper()
    return DGID_PREFIX + digest[:16]
```
Line `input_str = ...` gets the same length-prefix transform, byte-identical to the C# `Mint`.

**`mint_identity` — the CR-01/WR-01 target:**
```python
def mint_identity(session: Any, project: str, definition_id: str, cg_id: str) -> str:
    """Idempotently mint + persist a dgId for a Computgraph entity; return the dgId.

    Upserts on the anchor key ``(cgId, definitionId, project)`` and SETs ``dgId``.
    ...
    """
    dg_id = compute_dg_id(project, definition_id, cg_id)
    session.run(
        """
        MERGE (e {cgId: $cgId, definitionId: $definitionId, project: $project})
        SET e.dgId = $dgId
        // op=MINT
        """,
        {
            "project": project,
            "definitionId": definition_id,
            "cgId": cg_id,
            "dgId": dg_id,
        },
    )
```
**D-10 fix:** the `MERGE (e {...})` label-less anchor must become label-aware/kind-aware (e.g. `MERGE (e:Parameter {...})` when kind is known) so it coincides with `_publish_parameters`'s own `MERGE (p:Parameter {cgId: ..., definitionId: ..., project: ...})` (`computgraph_publish.py:624`) instead of creating an orphaned unlabeled node.
**D-11/WR-01 fix:** add `SET e.dgId = $dgId, e.graph = 'Computgraph'` (mirroring the `graph: 'Computgraph'` tag every other publish writer sets, e.g. `_publish_parameters` line 640: `p.graph = 'Computgraph'`).
**MintRequest model** (`:93-98`) will need an entity-kind field if D-10 resolves to an explicit argument — follow the existing `field_validator` pattern used on `BindRepresentationRequest.platform`/`native_id_kind` (`:111-123`) for any new enum-constrained field.

---

### Test files — golden vector pattern (both languages)

**Analog (C#):** `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs:1-66` (full file read, small enough for one pass):
```csharp
private const string Project = "p1";
private const string DefinitionId = "frame.gh";
private const string CgId = "cg:1:proc:11_Proc";

[Fact]
public void Mint_KnownVector_MatchesExpectedDgId()
{
    var dgId = DgIdMintingService.Mint("p1", "frame.gh", "cg:1:proc:11_Proc");
    Assert.Equal("dg:BC8E62EE137E2B56", dgId.Value);
}
```
Other facts in the same file worth copying verbatim as templates for new DesignStateIdGenerator tests: `Mint_SameInputsTwice_ProducesIdenticalDgId`, `Mint_DifferentProjectsSameEntity_ProducesDifferentDgId` (idempotence + project-isolation assertions — exactly what D-08's new tests need), `Mint_Always_ReturnsDgPrefixedSixteenHex` (format assertion via regex `^[0-9A-F]{16}$`).

**Analog (Python):** `data-service/tests/test_dg_identity.py` — confirmed (RESEARCH.md, byte-identical companion):
```python
GOLDEN_PROJECT = "p1"
GOLDEN_DEFINITION_ID = "frame.gh"
GOLDEN_CG_ID = "cg:1:proc:11_Proc"
GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"

def test_compute_dg_id_matches_dotnet_golden_vector():
    assert dg_identity.compute_dg_id(GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID) == GOLDEN_DG_ID
```
**Both literals must change together** post-D-09 (compute the new post-length-prefix hash once, paste into both files in the same commit — this is Pitfall 1 from RESEARCH.md).

---

### `ontology/dg-shapes.ttl` — new SHACL shape

**Analog:** `dgsh:ParameterShape` (`:461-503`, full block read) — closest existing node-target shape since `ATTRIBUTE_OF`'s range is `Parameter`:
```turtle
dgsh:ParameterShape
    a sh:NodeShape ;
    sh:targetClass dgc:Parameter ;
    sh:property dgsh:ParameterShape_parameterName,
                dgsh:ParameterShape_paramKind,
                dgsh:ParameterShape_dataType,
                dgsh:ParameterShape_project .

dgsh:ParameterShape_project
    sh:path dgc:project ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:severity sh:Violation ;
    sh:message "A Parameter node is missing the project property — every node must carry project isolation." ;
    dgsh:howToFix "Set project on the Parameter node to the owning project." .
```
**Caveat:** this is a node-property shape (`sh:targetClass` + `sh:property` sub-shapes), not a relationship shape — SHACL's native idiom for constraining a *relationship's* existence/cardinality is `sh:targetClass` on the source node with an `sh:qualifiedValueShape`/`sh:path` pointing through the predicate, or (simpler, matching this file's existing style) a property shape on `Atom` asserting `sh:path dgc:attributeOf` with `sh:class dgc:Parameter`. No existing shape in this file does relation-target-class validation today (confirmed via grep — zero `attributeOf`/`paramLink` matches) — the planner/implementer should model the new shape as a property on the `Atom`-analog shape (there is no `AtomShape` yet either; check `ontology/dg-shapes.ttl` fully before this task for whether one needs to be added first). **18 total `sh:NodeShape` blocks confirmed on disk** (17 numbered section comments; `RepresentationShape` and `SharedPropertyShape` sections likely each split into 2 — verify exact count immediately before writing the propagation checklist, per RESEARCH.md Pitfall 4; do not trust "20" from CONTEXT.md).

---

### `spec/RULE-PARTITION-POLICY.md` — new decision-table row

**Analog:** existing table rows (`:39-51`), e.g.:
```markdown
| Rule-mapped script-structure requirement | "A Frame `Algorithm` must contain a *Truss* `Procedure`" | **Cypher, referencing a Metagraph `Rule` by id (`llm/structure_rules.json`)** | Architect-authored intent like SWRL but evaluated against Computgraph shape rather than BIM geometry or parameters; the SWRL violation-inverted-body-atom machinery has no Computgraph equivalent, and `Rule_Id` is reused as a foreign key only, never SWRL semantics |
```
This is the closest existing row (also a Metagraph→Computgraph bridge via `llm/structure_rules.json`) — the new `ATTRIBUTE_OF` row should follow the same 4-column shape: Rule Category | Example | System | Rationale, naming "Cypher (`ATTRIBUTE_OF` edge)" as the owning system and citing that it persists `inputBindings` resolution rather than SWRL/SHACL judgment.

---

### `fixtures/golden/<sibling-path>/` — new CQ3 fixture directory

**Analog:** `fixtures/golden/replay/` — confirmed on disk this session (per RESEARCH.md Discrepancy #3), containing `README.md`, `seed-replay.cypher`, `mixed-verdicts.json`. Mirror this exact 3-file shape for the new sibling path (e.g. `fixtures/golden/attribute-of/` or `fixtures/golden/cq3/`): a `README.md` describing the fixture's purpose and PAPER-C-032 traceability, a `seed-<name>.cypher` populating exactly one rule/atom/parameter triple (`R_BUILDING_MIN_DISTANCE_12_V` / `A2` / `hasDistanceM` → `SepDist`) scoped to its own project namespace, and a result JSON capturing the expected forward+reverse query rows. **`fixtures/golden/fixture.json` stays frozen — do not touch it (1200 D-11 / 1202 D-17).**

## Shared Patterns

### Parameterized Cypher (never string-interpolated)
**Source:** `data-service/dg_identity.py` module docstring + every `_publish_*` function in `computgraph_publish.py` (e.g. `:620-654`, `:689-703`)
**Apply to:** `_attribute_of_from_bindings`/`_publish_attribute_of`, any modified `mint_identity` Cypher
```python
tx.run(
    """
    UNWIND $rows AS row
      MERGE (p:Parameter {cgId: row.cgId, definitionId: $definitionId, project: $project})
      SET p.parameterName = row.name, ...
    // op=PUBLISH_PARAMETER
    """,
    {"rows": params["parameterRows"], "definitionId": params["definitionId"], ...},
)
```

### Project-scoped MERGE key on every Computgraph/Metagraph write
**Source:** every `_publish_*` function in `computgraph_publish.py`; `mint_identity`'s anchor key
**Apply to:** the new `ATTRIBUTE_OF` MERGE (D-03 mandate) — both `MATCH` clauses (Atom, Parameter) must include `project: $project`, never rely on `Atom_Id`/`cgId` alone.

### `graph: 'Computgraph'` / `graph: 'Metagraph'` tagging on publish
**Source:** `_publish_parameters` (`computgraph_publish.py:640`: `p.graph = 'Computgraph'`), `_publish_interfaces` (`:672`)
**Apply to:** any new node this phase's `mint_identity` fix (D-11/WR-01) writes.

### Additive-never-rewrite for identity/state changes
**Source:** `DesignStateIdGenerator.cs`'s own class doc-comment (`:37-42`): "historical states are treated additively with no rewrite: existing rows stay as-is and are documented as pre-contract; only new captures adopt the [new] key."
**Apply to:** D-08 (project-in-hash) and D-09 (length-prefix) — no migration script; document historical IDs as pre-contract in `spec/DG-ID.md`'s new DesignState section (D-06).

### Doc-comment-as-rationale convention (C# side)
**Source:** `DesignStateIdGenerator.cs:100-127` (the "why this exists alongside" block on `ComputeObjectStateIdFromRef`)
**Apply to:** any new/retained dual-form function (D-07's retained 3-arg `ComputeObjectStateId`) — the project convention is an XML-doc `<para>` block explicitly justifying why a second overload coexists, not a bare summary.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `ontology/dg-shapes.ttl` new relation-cardinality shape (if `Atom`→`Parameter` edge itself needs a shape, not just `ParameterShape`'s node properties) | config (SHACL) | — | No existing shape in this file validates a cross-partition relationship's existence/class; `ParameterShape` only validates target-node properties. Planner should read one more full shape (e.g. `RepresentationShape`, `:188-239`, not fully read this session) before authoring, and may need to introduce the first relation-level shape in this file. |
| `spec/API.md` `/identity/mint` route documentation | config (API spec) | — | Confirmed by RESEARCH.md: zero existing mentions of `/identity/mint` in `spec/API.md`. This is a first-write, not a revision — no analog exists in this file for this specific route (other `/identity/*` or `/computgraph/*` routes may serve as structural templates but were not read in this session). |

## Metadata

**Analog search scope:** `data-service/` (computgraph_publish.py, cg_input_bindings.py, dg_identity.py, dg_context.py), `DG/src/DG.Core/` (Services/, Models/Identity/), `DG/tests/DG.Tests/` (root + Identity/), `data-service/tests/`, `ontology/dg-shapes.ttl`, `spec/RULE-PARTITION-POLICY.md`, `fixtures/golden/`
**Files scanned:** 11 read directly (full or targeted), plus 2 graphify queries (both confirmed unhelpful — stale/off-target)
**Pattern extraction date:** 2026-09-22
