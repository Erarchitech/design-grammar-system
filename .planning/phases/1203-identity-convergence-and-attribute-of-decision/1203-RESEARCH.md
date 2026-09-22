# Phase 1203: Identity Convergence and `ATTRIBUTE_OF` Decision - Research

**Researched:** 2026-09-22
**Domain:** Cross-layer graph schema (Metagraph→Computgraph bridge), deterministic identity minting (C#/Python parity), Neo4j Cypher patterns, xUnit/pytest golden-vector testing
**Confidence:** HIGH

## Summary

This phase's CONTEXT.md is unusually complete: 14 decisions (D-01…D-14), all evidenced with file:line citations dated 2026-09-22. **Every citation checked against disk in this research session holds** (see verification table below) with two minor drift points and zero contradictions of substance. The graphify snapshot, by contrast, is confirmed stale exactly as CONTEXT.md's R-15 warns — it is missing `ComputeObjectStateIdFromRef`, `ComputeCaptureEventStateId`, and shows wrong line numbers for the methods it does know about. Do not trust graphify's line numbers for this phase; disk reads were used throughout.

The phase has two independent workstreams that share a re-derivation event:

1. **`ATTRIBUTE_OF` implementation (D-01 through D-05, D-14):** persist the rule→parameter join that `cg_input_bindings.py`'s `classify_rule`/`read_rule_limit` already performs in memory, as a real `(:Atom)-[:ATTRIBUTE_OF]->(:Parameter)` edge. This is additive: no existing writer changes behavior, `inputBindings` stays the sole authoring source, and the edge is a derived projection written at the same publish/accept moment `PARAM_LINK` already is. The schema propagation sweep (D-05) is the largest surface — `ontology/dg-shapes.ttl` needs a new SHACL shape (18 node shapes today, not 20 as CONTEXT.md states — see discrepancy below), and `spec/RULE-PARTITION-POLICY.md`'s decision table needs a new row for this cross-layer bridge category (it currently has no "cross-layer bridge relation" row — everything there is either SWRL, SHACL, or Cypher-structure).

2. **Identity minting convergence (D-06 through D-13):** extend `spec/DG-ID.md` to cover DesignState IDs; fold `project` into the DesignState hash inputs (D-08); apply length-prefix encoding to fix CR-02 in **six** functions across two languages simultaneously (D-09); fix CR-01's label-less MERGE and WR-01's missing `graph` tag (D-10/D-11); delete dead `ALLOWED_PROPERTIES` (confirmed dead — `validate_cypher` only does bracket-balance checking, never references it). D-08+D-09 must be sequenced as **one** coordinated re-derivation because both change every newly minted ID's byte value, and the golden vectors that pin them live in two languages (`DgIdMintingServiceTests.cs`↔`test_dg_identity.py`, confirmed byte-identical pair `dg:BC8E62EE137E2B56` for triple `p1/frame.gh/cg:1:proc:11_Proc`; `DesignStateIdGeneratorTests.cs` has 5 more regression-pinned literals with no Python counterpart file — new work).

**Primary recommendation:** Sequence the phase as (a) identity-minting fixes first (D-06→D-13, self-contained, no schema propagation), producing the coordinated D-08/D-09 re-derivation wave with all golden vectors updated together across C#+Python; then (b) the `ATTRIBUTE_OF` bridge (D-01→D-05, D-14) as a second wave that depends on nothing from (a) but shares the "full test suite green" gate. The CQ3 fixture (D-14) is the single piece of exit evidence for the ROADMAP gate and should be the last task, consuming both waves' schema state.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `ATTRIBUTE_OF` edge derivation + MERGE | API / Backend (`data-service`, Python) | Database (Neo4j Computgraph) | Same tier as `PARAM_LINK` derivation (`computgraph_publish.py`) — a publish/accept-time Cypher write, not a client concern |
| `inputBindings` resolution (`classify_rule`, `read_rule_limit`) | API / Backend | — | Already implemented, reused unchanged (D-02) |
| SHACL shape for the new edge | Database / Storage (schema definition) | — | `ontology/dg-shapes.ttl` constrains the LPG schema server-side; no runtime tier owns it, it's a static contract artifact |
| DesignState ID minting (ObjState/ParamState/PropState/DesignState) | Client / Plugin (Grasshopper, C#) | API / Backend (Python mirror for parity) | Minted at canvas-capture time inside the GH plugin; the Python side only needs parity for cross-language identity checks, not primary minting |
| `dgId` minting | Client / Plugin (C#, canvas-extraction) AND API / Backend (Python, publish/mint-endpoint) | — | Genuinely dual-minted by design — both must agree byte-for-byte (golden vector), neither is authoritative over the other |
| `/identity/mint`, `/identity/bind` HTTP surface | API / Backend | Database | FastAPI routes in `data-service/app.py`, backed directly by Neo4j MERGE |
| CQ3 fixture (forward + reverse query) | Database (Neo4j fixture data + Cypher) | API / Backend (fixture loader/test harness) | Single-service evidence per D-14 — no cross-language DE-01 leg mandated |
| Platform conflict/detach/provenance tests (ALGN12-13) | API / Backend (`dg_identity.py` helpers) | Database | Existing spec (`spec/DG-ID.md`) already assigns this to the Python identity module; D-12 only adds tests, no new tier |

## Package Legitimacy Audit

No external packages are introduced by this phase. All work is internal C#/Python/Cypher/TTL/Markdown changes to existing modules (`DesignStateIdGenerator.cs`, `DgIdMintingService.cs`, `dg_identity.py`, `cg_input_bindings.py`, `computgraph_publish.py`, `ontology/dg-shapes.ttl`, `spec/*.md`). Existing dependencies (`neo4j` driver, `pydantic`, `xUnit`, `pytest`) are already vetted in prior phases. **Skip — no legitimacy gate applies.**

## Verification of CONTEXT.md's Cited Anchors (disk check, 2026-09-22)

All citations below were read directly from disk in this session. **No substantive contradiction found.** Two minor drift points noted.

| Citation | CONTEXT.md claim | Disk (verified) | Status |
|---|---|---|---|
| `ontology/DesignGrammar-V7.md:707-713` | `dgc:attributeOf` domain `dgm:Atom`, range `dgc:Parameter` | Confirmed verbatim at that location | MATCH |
| `ontology/DesignGrammar-V7.owl:2621-2626` | Same in OWL serialization | Confirmed verbatim (`rdf:about="&dgc;attributeOf"`, domain `&dgm;Atom`, range `&dgc;Parameter`) | MATCH |
| `paper-claims.json` PAPER-C-032 | CQ3's single-row demonstration, R_BUILDING_MIN_DISTANCE_12_V/A2/hasDistanceM→SepDist | Confirmed verbatim at line 560-575; also cross-references PAPER-C-031/PAPER-C-045 as dependencies | MATCH |
| `data-service/dg_identity.py:178-181` | Label-less MERGE, CR-01 open | Confirmed: `MERGE (e {cgId: ..., definitionId: ..., project: ...})` — no label | MATCH (CR-01 confirmed OPEN) |
| `DgIdMintingService.cs:41` | Unescaped pipe join, CR-02 open | Confirmed: `var input = $"{project}\|{definitionId}\|{cgId}";` | MATCH (CR-02 confirmed OPEN) |
| `dg_identity.py:61` | Same defect, Python side | Confirmed: `input_str = f"{project}\|{definition_id}\|{cg_id}"` | MATCH (CR-02 confirmed OPEN, both languages) |
| `dg_identity.py:179` | No `graph` tag set on mint (WR-01) | Confirmed: only `SET e.dgId = $dgId` | MATCH (WR-01 confirmed OPEN) |
| `computgraph_publish.py:415,695` | PARAM_LINK derive-then-MERGE precedent | Confirmed: `_paramlinks_from_wires()` derives from wire adjacency; `_publish_param_links()` MERGEs `(p)-[:PARAM_LINK]->(i)` scoped by `definitionId`+`project` | MATCH |
| `cg_input_bindings.py:293-302` (`read_rule_limit`) | Atom-type-discriminating Cypher traversal | Confirmed: `MATCH (r:Rule)... OPTIONAL MATCH (r)-[hb:HAS_BODY]->(a:Atom {type:'BuiltinAtom'})` | MATCH (line numbers close: actual 292-304) |
| `cg_input_bindings.py:369-427` (`classify_rule`) | Resolves ruleId→parameterNames, forces limit=None for geometry-required | Confirmed exactly, including the D-09-referenced "single line that makes it structural" comment | MATCH |
| `dg_context.py:546-559` (`ALLOWED_PROPERTIES`) | Dead constant | Confirmed: defined at 550-559, and `validate_cypher` (verified at :655-670) does ONLY bracket-balance checking — never references `ALLOWED_PROPERTIES` | MATCH (WR-03 disposition of DELETE is sound) |
| `DesignStateIdGenerator.cs:68-86` (`ComputeParamStateId`) | member function bounds | Actual: `:68-87` | MINOR DRIFT (1 line, immaterial) |
| `DesignStateIdGenerator.cs:94-97` (`ComputeObjectStateId` 3-arg) | no production callers | Actual: `:94-98`; confirmed zero production callers (only test references found) | MINOR DRIFT (1 line), claim MATCH |
| `DesignStateIdGenerator.cs:98-131` (`ComputeObjectStateIdFromRef` + rationale) | | Actual: doc-comment `:100-127`, method body `:128-133` | DRIFT (~5-8 lines, likely from doc-comment reflow); content MATCH |
| `DesignStateIdGenerator.cs:142-160` (`ComputePropStateId`) | | Actual: `:142-160` | MATCH |
| `DesignStateIdGenerator.cs:169-177` (`ComputeDesignStateId`) | | Actual: `:169-178` | MINOR DRIFT (1 line) |
| `DesignStateIdGenerator.cs:198-209` (`ComputeCaptureEventStateId`) | | Actual: `:198-210` | MINOR DRIFT (1 line) |
| `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs:13` | golden vector uses `"frame.gh"` | Confirmed: `DefinitionId = "frame.gh"` at line 13; golden vector test at :60-65 returns `dg:BC8E62EE137E2B56` | MATCH (WR-04 ambiguity confirmed live) |
| `data-service/tests/test_dg_identity.py` | Python golden-vector counterpart | Confirmed: `GOLDEN_DEFINITION_ID = "frame.gh"`, `GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"` — **byte-identical to the C# vector**, confirming cross-language parity currently holds | MATCH |
| `ontology/dg-shapes.ttl` — "no `attributeOf` or `paramLink` shape exists today" | | Confirmed via grep: zero matches for either term | MATCH |
| `ontology/dg-shapes.ttl` — "20 node shapes" (D-05) | | **Actual count: 18 `sh:NodeShape` declarations** | **DISCREPANCY — see below** |
| `dg_context.py:661` (`validate_cypher`) | | Actual: function body starts ~:655, bracket-matching logic confirmed at :655-666 | MATCH (close) |
| `spec/DATABASE.md:336` (WR-02 wrong route/verb) | | Line 336 in current disk state falls inside the Object node's provenance-transport paragraph, not a route/verb declaration — **the file has been edited since this citation was written** (Phase 36 UAT F6 content now occupies that region) | **DISCREPANCY — see below** |

### Discrepancies worth flagging to the planner

1. **`ontology/dg-shapes.ttl` node-shape count is 18, not 20** (CONTEXT.md D-05 says "20 node shapes"). This is off by 2. It does not change the recommendation (still "add ~1-2 shapes for the new edge/relation"), but the planner should not treat "20" as a hard count to reconcile against — verify the actual count again immediately before writing the propagation checklist, since the file may have changed further since this session.
2. **`spec/DATABASE.md:336` no longer shows a route/verb declaration** — the file has evidently been edited since Phase 32.1's WR-02 finding was written (most likely by the Phase 36 UAT F6 provenance-transport documentation that now occupies nearby lines). **This means WR-02 may already be stale or may have moved to a different line.** The planner should re-grep `spec/DATABASE.md` for the specific wrong route/verb text (Phase 32.1-era `/identity/...` or `/computgraph/...` route documentation errors) before writing a task to fix it — do not assume line 336 is still the target. This is a genuine "verify before planning" flag, not a blocker.
3. **`fixtures/golden/replay/` already exists** (created 2026-09-21/22, i.e. during or just before this research session) containing `README.md`, `seed-replay.cypher`, `mixed-verdicts.json` — this is Phase 1202's D-16/D-17 sibling-path precedent, already on disk and not mentioned in CONTEXT.md's file listing. **This is the template to follow for D-14's new CQ3 fixture material** — a sibling directory (e.g. `fixtures/golden/attribute-of/` or `fixtures/golden/cq3/`) with its own README + seed Cypher + result JSON, exactly mirroring this existing precedent.

None of these discrepancies contradict a D-01…D-14 decision or its rationale. All are either off-by-a-few-lines drift (expected given same-day edits) or newly created artifacts the planner should be aware of.

## Standard Stack

No new libraries. This phase operates entirely within the existing stack:

### Core (unchanged, in scope for this phase's edits)
| Component | Version | Purpose | Why relevant here |
|---|---|---|---|
| Neo4j Python driver | (existing, per `data-service/requirements.txt`) | Cypher execution for `ATTRIBUTE_OF` MERGE, identity registry | `mint_identity`, `_publish_param_links`, new `_publish_attribute_of` (or similar) all use `session.run` |
| xUnit | (existing, `DG.Tests.csproj`) | C# identity/DesignState golden-vector tests | D-08/D-09 re-derivation lands here |
| pytest | (existing, `data-service/tests/`) | Python identity + input-bindings + structure-check tests | Same re-derivation; also new `ATTRIBUTE_OF` tests |
| pydantic | (existing) | Request/response models for `/identity/mint` (D-10's kind-argument decision touches `MintRequest`) | — |

### Alternatives Considered
None — this phase makes no new technology choices; it implements decisions already locked in CONTEXT.md.

**Installation:** N/A — no new packages.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌─────────────────────────────────────────┐
                          │   llm/structure_rules.json               │
                          │   inputBindings[] (authoring source)     │
                          │   {ruleId, determinability, parameters,  │
                          │    metricExpression, monotoneIn}         │
                          └───────────────────┬───────────────────────┘
                                              │ loaded by
                                              ▼
                   ┌──────────────────────────────────────────────────┐
                   │  cg_input_bindings.py                             │
                   │  classify_rule() ──► RuleClassification            │
                   │    (ruleId, determinability, parameterNames, ...)  │
                   │  read_rule_limit() ──► Cypher traversal over        │
                   │    (:Rule)-[:HAS_BODY]->(:Atom{BuiltinAtom})       │
                   └───────────────────┬────────────────────────────────┘
                                       │ resolved parameter names
                                       ▼
              ┌───────────────────────────────────────────────────────┐
              │  computgraph_publish.py  (publish / accept time)       │
              │  ── existing: _publish_parameters(), _publish_param_   │
              │     links() [PARAM_LINK from wire adjacency]           │
              │  ── NEW (D-01/D-02): _publish_attribute_of()           │
              │     derives (:Atom)-[:ATTRIBUTE_OF]->(:Parameter)      │
              │     from classify_rule()'s resolved parameterNames,    │
              │     MERGEd project-scoped (D-03), carrying provenance  │
              │     (which inputBindings entry derived it)             │
              └───────────────────┬───────────────────────────────────┘
                                  │ MERGE, project-scoped
                                  ▼
         ┌───────────────────────────────────────────────────────────────┐
         │  Neo4j — Metagraph ←──ATTRIBUTE_OF──→ Computgraph               │
         │  (:Atom {type:'DataPropertyAtom', Atom_Id:'RULE_A2'})           │
         │      -[:ATTRIBUTE_OF {derivedFrom: 'inputBindings[ruleId]'}]->  │
         │  (:Parameter {cgId, definitionId, project, parameterName})     │
         └───────────────────────────────┬─────────────────────────────────┘
                                         │ queried both directions
                       ┌─────────────────┴──────────────────┐
                       ▼                                    ▼
        FORWARD (rule/atom → parameter)        REVERSE (parameter → governing rules)
        MATCH (r:Rule)-[:HAS_BODY]->(a:Atom)    MATCH (p:Parameter {...})
              -[:ATTRIBUTE_OF]->(p:Parameter)         <-[:ATTRIBUTE_OF]-(a:Atom)
        WHERE r.Rule_Id = $ruleId                      <-[:HAS_BODY]-(r:Rule)
        RETURN p.parameterName                  RETURN r.Rule_Id, a.Atom_Id
                       │                                    │
                       └─────────────────┬──────────────────┘
                                         ▼
                     CQ3 fixture (D-14) — both directions evidenced
                     against `fixtures/golden/<sibling-path>/`
                     mirrors PAPER-C-032's shape exactly
```

**Parallel, independent flow — identity minting (D-06…D-13):**

```
Grasshopper canvas capture                    Computgraph extraction/publish
       │                                                │
       ▼                                                ▼
DesignStateIdGenerator.cs                     DgIdMintingService.cs (C#)
  .ComputeObjectStateIdFromRef()  ◄─ authoritative for   ▲  byte-identical
  .ComputeObjectStateId() (3-arg) ◄─ per-rule-variable,   │  golden vector
                                     CMPST-07, no          │
                                     production caller     │
  .ComputeParamStateId()                                  │
  .ComputePropStateId()                                   │
  .ComputeDesignStateId() (content-addressed, unchanged)  │
  .ComputeCaptureEventStateId() (D-01 layer-1 node key)   │
       │                                                  │
       │  D-08: fold `project` into hash (additive,       │
       │        new IDs only, historical IDs untouched)   │
       │  D-09: length-prefix encoding fixes CR-02          │
       │        (applies to ALL SIX functions above +      │
       │        DgIdMintingService.Mint + compute_dg_id)    │
       ▼                                                  ▼
   Neo4j DesignState nodes                    data-service/dg_identity.py
   (StateId as key)                             .compute_dg_id() (Python mirror)
                                                 .mint_identity() ◄─ D-10: fix CR-01
                                                     (label-less MERGE), make
                                                     label-aware / kind-aware
                                                 .bind_representation()
                                                 .detach_representation() ◄─ D-12/13:
                                                 .write_shared_property()   tests only,
                                                                            spec unchanged
```

### Recommended Project Structure

No new directories. Files touched:

```
DG/src/DG.Core/Services/DesignStateIdGenerator.cs      # D-08 (project-in-hash), D-09 (length-prefix)
DG/src/DG.Core/Models/Identity/DgIdMintingService.cs   # D-09 (length-prefix)
DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs       # D-08/D-09 golden vectors re-derived
DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs  # D-09 golden vector re-derived, WR-04 naming addressed
DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs  # no change expected (D-07 retains both forms)

data-service/dg_identity.py                # D-09 (length-prefix), D-10 (CR-01 label-aware mint), D-11 (WR-01 bundled)
data-service/cg_input_bindings.py           # unchanged (D-02 reuses as-is) — read-only dependency for ATTRIBUTE_OF
data-service/computgraph_publish.py         # D-01/D-02: new _publish_attribute_of() alongside _publish_param_links()
data-service/dg_context.py                  # D-11: delete ALLOWED_PROPERTIES (:546-559 approx)
data-service/tests/test_dg_identity.py      # D-09 golden vector re-derived in lockstep with C#
data-service/tests/test_computgraph_publish.py  # new ATTRIBUTE_OF publish tests
data-service/tests/test_cg_input_bindings.py    # (if exists) or new file — attachment-atom tests for D-04

ontology/dg-shapes.ttl                      # D-05: new SHACL shape for ATTRIBUTE_OF edge
spec/RULE-PARTITION-POLICY.md               # D-05: new decision-table row for cross-layer bridge relations
spec/DG-ID.md                               # D-06: extended to cover DesignState IDs; D-08/D-09 documented
spec/DATABASE.md                            # D-05 (ATTRIBUTE_OF schema); D-11 (WR-02 fix, re-verify target line)
spec/API.md                                 # D-10 (/identity/mint signature, if entity-kind arg added); currently has NO /identity/mint entry at all
cypher_template.txt                         # D-05: ATTRIBUTE_OF MERGE pattern alongside existing Atom/PARAM_LINK patterns
training/dataset_schema.json                # D-05: schema propagation
.github/copilot-instructions.md             # D-05: schema propagation
README.md                                   # D-05: schema propagation
CLAUDE.md                                   # D-05: Relationships list gains ATTRIBUTE_OF

fixtures/golden/<sibling-path>/             # D-14: new CQ3 fixture (NOT fixture.json — frozen)
  README.md
  seed-cq3.cypher  (or similar name)
  <result>.json
```

### Pattern 1: Derive-then-MERGE for cross-layer Computgraph edges
**What:** A relationship connecting two graph partitions (here, Metagraph `Atom` → Computgraph `Parameter`) is never hand-authored; it is computed from an existing authoritative source at publish/accept time and MERGEd project-scoped.
**When to use:** Any time a new structural fact needs to become queryable in Neo4j but already has a single source of truth elsewhere (a config file, a wire-adjacency computation, an LLM classification).
**Example:**
```python
# Source: data-service/computgraph_publish.py:415-424 (existing PARAM_LINK precedent)
def _paramlinks_from_wires(wires: list[dict], parameter_rows: list[dict], interface_rows: list[dict]) -> list[dict]:
    """Derive Parameter->Interface PARAM_LINK pairs from wire adjacency.
    The envelope carries no direct Parameter<->Interface reference -- for each
    wire, if one endpoint's node id is a member of a Parameter and the other
    endpoint's node id is a member of an Interface (in either direction), emit
    one {paramCgId, interfaceCgId} link row. Deduplicated.
    """
    # ... (pattern to follow for _attribute_of_from_bindings())
```
The `ATTRIBUTE_OF` equivalent should follow this exact shape: a pure function taking the loaded `inputBindings` + `classify_rule()` results + the published `:Parameter` rows, returning `{atomId, parameterCgId, derivedFrom}` rows, then a `_publish_attribute_of(tx, params)` MERGE function mirroring `_publish_param_links` (`computgraph_publish.py:689-700`).

### Pattern 2: Atom-type-discriminating Cypher traversal
**What:** Rules have multiple body atoms of different `type` (`ClassAtom`, `DataPropertyAtom`, `BuiltinAtom`); code that needs "the atom that carries X" filters by `type` in the `MATCH` clause rather than by position/order alone.
**When to use:** D-04's attachment rule — deciding which atom `ATTRIBUTE_OF` attaches to.
**Example:**
```cypher
-- Source: data-service/cg_input_bindings.py:293-299 (read_rule_limit, existing pattern)
MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
OPTIONAL MATCH (r)-[hb:HAS_BODY]->(a:Atom {type: 'BuiltinAtom'})
OPTIONAL MATCH (a)-[:ARG {`pos`: 1}]->(vArg:Var)
OPTIONAL MATCH (a)-[:ARG {`pos`: 2}]->(litArg:Literal)
RETURN a.iri AS builtinIri, hb.`order` AS bodyOrder, vArg.name AS variableName, litArg.lex AS lex
ORDER BY bodyOrder
```
The `cypher_template.txt` rule pattern (verified lines 237-262) numbers atoms `A1` (ClassAtom), `A2` (DataPropertyAtom), `A3` (BuiltinAtom), `H1` (head/violation atom). `PAPER-C-032` cites `A2` — the `DataPropertyAtom` — as the CQ3 attachment point. **This is structurally consistent with the template's own numbering**: A2 is always the property-carrying atom in DG's standard two-rule pattern, giving the planner a stable, generalizable attachment rule: *`ATTRIBUTE_OF` attaches to the rule's `DataPropertyAtom` (the atom whose `type = 'DataPropertyAtom'` and whose `iri` matches the property the `inputBindings` entry's parameter set is checking)*.

### Pattern 3: Additive-only DesignState ID re-derivation with dual-language golden vectors
**What:** Any change to a minting hash-input contract is applied to new records only; historical records are documented as pre-contract, never rewritten; both C# and Python test suites gain matching updated literals in the same commit/wave.
**When to use:** D-08 (project-in-hash) + D-09 (length-prefix) — sequenced as one coordinated re-derivation per CONTEXT.md's explicit instruction.
**Example:** The existing golden-vector precedent to mirror:
```csharp
// Source: DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs:59-65
[Fact]
public void Mint_KnownVector_MatchesExpectedDgId()
{
    var dgId = DgIdMintingService.Mint("p1", "frame.gh", "cg:1:proc:11_Proc");
    Assert.Equal("dg:BC8E62EE137E2B56", dgId.Value);
}
```
```python
# Source: data-service/tests/test_dg_identity.py:36-39, 235-244 — MUST stay byte-identical
GOLDEN_PROJECT = "p1"
GOLDEN_DEFINITION_ID = "frame.gh"
GOLDEN_CG_ID = "cg:1:proc:11_Proc"
GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"

def test_compute_dg_id_matches_dotnet_golden_vector():
    assert dg_identity.compute_dg_id(GOLDEN_PROJECT, GOLDEN_DEFINITION_ID, GOLDEN_CG_ID) == GOLDEN_DG_ID
```
After D-09's length-prefix fix, BOTH literals (`GOLDEN_DG_ID` and the C# assertion) must change to the new post-fix value, computed once and pasted into both files. Any wave that lands only one side breaks parity silently until CI runs both suites.

### Anti-Patterns to Avoid
- **Hand-authoring a second rule→parameter list.** D-02 explicitly forbids this. Any task suggesting a new YAML/JSON file mapping rules to parameters directly (bypassing `inputBindings`) violates the locked decision.
- **Rewriting historical DesignState IDs in place.** D-08 is additive-only. A migration script that UPDATEs existing `:DesignState` nodes' `StateId` property is explicitly forbidden — this would violate the same additive-no-rewrite principle that governs 1200 D-03/D-04 and 1202 D-03.
- **Synthesizing fake inputs to force one ObjState minting signature.** D-07 explicitly forbids fabricating a `projectId` or `variableName` to route `ObjectStateComponent` through the 3-arg `ComputeObjectStateId` instead of `ComputeObjectStateIdFromRef`.
- **Rejecting length-prefix-eligible input outright instead of prefixing it.** D-09 chose length-prefixing over reject-on-`|` specifically because `cgId` derives from user-authored Grasshopper nicknames that may legitimately contain `|`-adjacent characters; a reject-based fix would turn a legal name into a hard failure.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rule→parameter join | A new resolver or duplicate join logic in `computgraph_publish.py` | `cg_input_bindings.classify_rule()` + `read_rule_limit()`, called as-is | Already handles determinability classing, missing-parameter reporting (WR-02 vocabulary), and forbidden-key validation; reimplementing risks drifting from the safe-default (`geometry-required`) semantics D-08 established in Phase 38 |
| Cross-layer edge MERGE pattern | A bespoke MERGE shape for `ATTRIBUTE_OF` | Mirror `_publish_param_links()`'s exact shape (MATCH both endpoints scoped by project+definitionId, MERGE the relation) | `PARAM_LINK` is the established precedent in this exact codebase for exactly this problem class |
| Length-prefix / delimiter-safety encoding | A custom escape scheme (e.g. backslash-escaping `\|`) | Length-prefixing (`len:value|len:value` per CONTEXT.md's Claude's Discretion suggestion) | Escaping is a well-known source of double-escaping bugs across two languages; length-prefixing is total and trivially portable between C# and Python string operations |
| SHACL shape authoring | Freehand TTL without checking existing shape conventions | Follow the existing 18-shape file's naming/structure convention exactly (check an existing cross-partition-adjacent shape, e.g. the `Representation`/`SharedProperty` shapes added in Phase 32.1, as the template) | `ontology/dg-shapes.ttl` has an established per-node-label shape pattern; a new shape that doesn't match risks inconsistent validation severity mapping |

**Key insight:** Every piece of "new" logic this phase needs already has a structurally identical precedent shipped in this exact codebase (`PARAM_LINK` for derive-then-MERGE, `read_rule_limit` for atom-type discrimination, the existing golden-vector harness for cross-language parity). The work is applying established patterns to a new edge/field, not inventing new mechanisms.

## Runtime State Inventory

> This phase is neither a rename nor a wholesale refactor, but D-08/D-09 change minted ID *values* going forward and D-01 introduces a brand-new relation type — both are identity/schema changes with runtime-state implications. Applying the inventory discipline here because "every new ObjState/ParamState/PropState ID changes value" (CONTEXT.md D-08) is exactly the kind of runtime-state fact a grep audit would miss.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Every historical `:DesignState`/`:ObjState`/`:ParamState`/`:PropState` node's `StateId` was minted WITHOUT `project` in the hash and WITHOUT length-prefix encoding. These rows are NOT rewritten (D-08 explicit). Neo4j MERGE keys for these rows continue to resolve against the OLD id format for old data; NEW captures resolve against the NEW format. | Document explicitly in `spec/DG-ID.md`'s new DesignState section: "IDs minted before [phase 1203 ship date] used hash input without `project` and without length-prefixing; they remain valid and are not migrated." No Cypher migration script needed (mirrors precedent: `migrations/2026-06-23_var_project_merge_key.cypher` was a schema fix, not this — this phase's rule is explicitly "no new migration," per D-08's own text) |
| Live service config | None found. No n8n workflow, Datadog dashboard, or external service config references `DesignStateIdGenerator`'s hash format or `dgId`'s value format directly — these are internal identity strings, not externally configured names. | None — verified by reading `dg_identity.py`/`DesignStateIdGenerator.cs` module docstrings; no external-service coupling documented or found |
| OS-registered state | None. Identity minting is pure in-process computation (SHA-256 over a string); no OS Task Scheduler, pm2, systemd, or launchd artifact references a specific ID value or hash format. | None — verified by inspection; this is a pure algorithmic change with no OS-level registration surface |
| Secrets/env vars | None. No SOPS key, `.env` variable, or CI secret name encodes a `dgId` or `StateId` value or references the hash-input format. | None |
| Build artifacts | The Grasshopper plugin `.gh` files in `test/` fixtures and any developer's local `.gh` canvases were built against the OLD `DesignStateIdGenerator`/`DgIdMintingService` binaries. Any captured/published DesignState data inside a `.gh` file's saved state reflects pre-D-08/D-09 IDs. A rebuilt plugin (post-D-08/D-09) minting a NEW capture on the SAME canvas will produce DIFFERENT IDs for what is conceptually "the same" design, by design (D-08's stated consequence). | Rebuild `DG.sln` (Release) after D-08/D-09 land, per the existing "Grasshopper plugin needs a dotnet rebuild for any `DesignStateIdGenerator` change" gotcha; no data migration for the plugin binaries themselves — they are build artifacts, replaced by rebuild, not migrated |

**Nothing found in three of five categories** — stated explicitly per protocol, not left blank.

## Common Pitfalls

### Pitfall 1: Landing D-08 or D-09 without the other, in separate commits
**What goes wrong:** If D-08 (project-in-hash) ships alone, or D-09 (length-prefix) ships alone, the golden vectors change TWICE in two different waves, doubling the cross-language-parity verification burden and creating an intermediate state where C# and Python temporarily disagree if one language's fix lands before the other's.
**Why it happens:** They touch the same functions and look like separable concerns (one closes a collision-policy gap, one closes an escaping bug) but CONTEXT.md explicitly says "Sequence D-08 and D-09 as ONE coordinated re-derivation, not two."
**How to avoid:** Plan a single wave/task that applies both hash-input changes to all six affected functions (four `DesignStateIdGenerator` methods + `DgIdMintingService.Mint` + `compute_dg_id`) in both languages, computes the new golden-vector literals once, and updates both test files in the same commit.
**Warning signs:** A plan with separate tasks titled "close project-in-hash gap" and "fix CR-02 pipe delimiter" as independently completable/committable units.

### Pitfall 2: Treating `/identity/mint`'s missing spec/API.md entry as pre-existing documentation to "update"
**What goes wrong:** `spec/API.md` currently has ZERO mentions of `/identity/mint` (confirmed by grep — the search returned no matches at all). A planner assuming this route is documented and just needs a signature tweak will silently skip writing the base documentation.
**Why it happens:** CONTEXT.md's "Reversibility: costly — the /identity/mint signature is a published API surface (spec/API.md)" phrasing implies existing documentation exists to be revised.
**How to avoid:** Confirm the `/identity/mint` route needs its FIRST spec/API.md entry, not a revision — write the full route documentation (method, path, request body, response, error codes DGID_NOT_FOUND/DGID_AMBIGUOUS_BINDING) as part of D-10's task, including whatever kind-argument decision is made.
**Warning signs:** A task phrased as "update /identity/mint's documented signature" without first verifying the route has any documentation to update.

### Pitfall 3: Assuming `spec/DATABASE.md:336` still names the WR-02 defect
**What goes wrong:** Disk verification in this session found line 336 currently falls inside unrelated Phase 36 UAT F6 provenance-transport prose, not a route/verb declaration. The file has been edited since the 32.1-REVIEW.md citation was written.
**Why it happens:** Multi-phase docs drift; `spec/DATABASE.md` is a large, frequently-edited file and WR-02's original line anchor is now stale.
**How to avoid:** Before writing the WR-02 fix task, re-grep `spec/DATABASE.md` for the actual wrong-route/verb text (search for `/identity/` or `/computgraph/` route references near Phase 32.1-era content) to relocate the real defect, rather than assuming line 336.
**Warning signs:** A plan step that edits `spec/DATABASE.md:336` without first re-verifying what's there.

### Pitfall 4: Building a new SHACL shape without re-verifying the current shape count
**What goes wrong:** CONTEXT.md says "20 node shapes" but disk shows 18. Referencing the wrong count in a propagation checklist could cause a false-complete signal (e.g., "shapes now number 20, done" when the actual target was different).
**Why it happens:** The count may have been accurate at CONTEXT.md's authoring moment but drifted, or was mis-transcribed.
**How to avoid:** Treat "N node shapes" as informational context only; the actual verification criterion should be "an `attributeOf` shape exists and is syntactically valid TTL, tested by the existing SHACL validation test suite," not a specific count.
**Warning signs:** A verification step that asserts an exact shape count rather than checking for the specific new shape's presence and correctness.

### Pitfall 5: Conflating `ATTRIBUTE_OF`'s reverse query with a full graph traversal that also returns unrelated Atom types
**What goes wrong:** A naive reverse query (`parameter → governing rules`) that does `MATCH (p:Parameter)<-[:ATTRIBUTE_OF]-(a:Atom)<-[:HAS_BODY]-(r:Rule) RETURN r` without also filtering the CQ3 fixture's expected shape could return multiple unrelated results if more than one rule's DataPropertyAtom attaches to the same parameter, silently changing the fixture's single-row expectation into a multi-row result that then needs disambiguation.
**Why it happens:** The CQ3 fixture is deliberately a single-row proof (per `paper.md:13,46,54`'s disclaimer — representation, not solver equivalence); a schema that permits N:1 or N:N `ATTRIBUTE_OF` edges (which D-03's project-scoped MERGE does not forbid) could produce ambiguous fixture results if the fixture data isn't carefully scoped to exactly the PAPER-C-032 triple.
**How to avoid:** The CQ3 fixture's seed data should contain exactly one rule/atom/parameter triple matching PAPER-C-032's shape, isolated in its own project namespace, so forward and reverse queries each return exactly one row — proving representation without needing to handle multiplicity in the fixture itself. Multiplicity handling (if ever needed) is future scope, not this phase's.
**Warning signs:** A reverse-query test that asserts `len(results) >= 1` instead of `len(results) == 1`.

## Code Examples

### Forward query pattern (rule/atom → parameter)
```cypher
-- Derived from cypher_template.txt's atom-numbering convention (A2 = DataPropertyAtom)
-- and cg_input_bindings.py's read_rule_limit traversal pattern
MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom', project: $project})
MATCH (a)-[:ATTRIBUTE_OF]->(p:Parameter {project: $project})
RETURN r.Rule_Id AS ruleId, a.Atom_Id AS atomId, a.SWRL_label AS property,
       p.cgId AS parameterCgId, p.parameterName AS parameterName
```

### Reverse query pattern (parameter → governing rules)
```cypher
MATCH (p:Parameter {cgId: $paramCgId, definitionId: $definitionId, project: $project})
MATCH (a:Atom {project: $project})-[:ATTRIBUTE_OF]->(p)
MATCH (r:Rule {project: $project})-[:HAS_BODY]->(a)
RETURN p.parameterName AS parameterName, r.Rule_Id AS ruleId, a.Atom_Id AS atomId
```

### Derive-then-MERGE for ATTRIBUTE_OF (following the PARAM_LINK precedent)
```python
# Source pattern: data-service/computgraph_publish.py:689-700 (_publish_param_links, existing)
def _publish_attribute_of(tx: Any, params: dict) -> None:
    tx.run(
        """
        UNWIND $rows AS row
          MATCH (a:Atom {Atom_Id: row.atomId, project: $project})
          MATCH (p:Parameter {cgId: row.paramCgId, definitionId: $definitionId, project: $project})
          MERGE (a)-[rel:ATTRIBUTE_OF]->(p)
          SET rel.derivedFrom = row.derivedFrom
        // op=PUBLISH_ATTRIBUTE_OF
        """,
        {
            "rows": params["attributeOfRows"],
            "definitionId": params["definitionId"],
            "project": params["project"],
        },
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Rule→parameter join computed in memory only, at generation time, never persisted | Same join, now ALSO persisted as `ATTRIBUTE_OF` at publish/accept time | This phase (D-01/D-02) | CQ3 becomes directly queryable via Cypher instead of only reconstructible by re-running the generation code path |
| DesignState hash inputs omit `project` (single-layer collision defense) | `project` folded into DesignState hash inputs, restoring the two-layer "belt-and-suspenders" defense `spec/DG-ID.md` already specifies for `dgId` | This phase (D-08) | New DesignState IDs cannot collide across projects even if the Neo4j MERGE key scoping were ever bypassed; historical IDs remain single-layer-protected (documented, not migrated) |
| Pipe-joined hash inputs vulnerable to cross-value collision when a field itself contains `\|` | Length-prefixed encoding applied to all six pipe-joined identity hash inputs | This phase (D-09) | Closes CR-02 in both `dgId` and DesignState ID families simultaneously; a Grasshopper nickname containing `\|` no longer risks an identity collision |
| `mint_identity`'s anchor MERGE is label-less | Label-aware / kind-aware MERGE, coinciding with publish | This phase (D-10) | Pre-mint-before-publish (the intended workflow per `spec/DG-ID.md:55-64`) no longer risks orphaning a pre-minted registry node when the entity is later published |

**Deprecated/outdated:** None — this phase adds capability and fixes defects; it does not retire any existing mechanism except the dead `ALLOWED_PROPERTIES` constant (D-11).

## Assumptions Log

> Per the provenance rule, package names and any claim not directly read from disk in this session are logged here. This phase introduces no new external packages, so this log is short.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact SHACL shape structure/naming convention to follow for the new `ATTRIBUTE_OF` shape was not independently re-verified against every existing shape in `ontology/dg-shapes.ttl` in this session (only the absence of `attributeOf`/`paramLink` and the total count were checked). | Don't Hand-Roll / Architecture Patterns | If the file's per-shape convention differs meaningfully from what's assumed, the planner should read a representative existing shape (e.g., the `Representation` or `SharedProperty` shape from Phase 32.1) directly before writing the new one, rather than trusting this summary. |
| A2 | `spec/DATABASE.md`'s actual current WR-02 defect location (post-drift) was not re-located in this session — only the fact that line 336 no longer matches was confirmed. | Common Pitfalls #3 | The planner must re-grep before planning the WR-02 fix task; if skipped, the task may target the wrong line or miss the defect entirely. |
| A3 | Whether any OTHER test file besides `DesignStateIdGeneratorTests.cs` / `test_dg_identity.py` carries a DesignState-ID or `dgId` golden-vector literal was checked via targeted file search but not an exhaustive repo-wide grep for every hex-looking literal. | D-08/D-09 blast radius | If another test file (e.g., a DE-01 fixture, `fixtures/golden/canonical-vectors.json`, or an integration test) pins a DesignState ID or dgId literal not surfaced here, the coordinated re-derivation wave could miss it and leave a silently-broken test. **Recommend:** planner runs `grep -rn "OS_\|DS_\|PS_\|dg:" fixtures/golden/ data-service/tests/ DG/tests/` as a Wave-0 verification step before starting the re-derivation task. |

**If this table is empty:** N/A — see above; risks are procedural (verify-before-planning), not package-legitimacy risks.

## Open Questions (RESOLVED)

> Both questions below are closed procedurally: each is operationalized as a Wave 0 task in
> `1203-01-PLAN.md` (Task 1 covers question 1, Task 2 covers question 2), and both appear in
> `1203-VALIDATION.md` § Wave 0 Requirements. Planning did not need the answers up front — the
> plans read the answer off disk before any dependent work starts.

1. **Does `fixtures/golden/canonical-vectors.json` contain any DesignState ID or dgId literal that D-08/D-09 would invalidate?**
   - **Resolved by:** `1203-01-PLAN.md` Task 1. Planner reported the file carries no identity literals, confirming the blast radius is the two test files plus plan 01's repo-wide sweep.
   - What we know: `fixtures/golden/fixture.json` is explicitly frozen (1200 D-11/1202 D-17) and out of scope for edits. `canonical-vectors.json` is a sibling file whose contents were not read in this session.
   - What's unclear: Whether `canonical-vectors.json` pins any hash-derived ID literal that would break under D-08/D-09's re-derivation.
   - Recommendation: Planner reads `fixtures/golden/canonical-vectors.json` and `fixtures/golden/MANIFEST.md` as a Wave-0 task before starting the D-08/D-09 re-derivation, to confirm it is unaffected (likely — it's described elsewhere in the corpus as canonicalization vectors, not identity-minting vectors) or needs its own update.

2. **What is the current, correct line/location of the WR-02 defect in `spec/DATABASE.md`?**
   - **Resolved by:** `1203-01-PLAN.md` Task 2. Planner relocated it: `spec/DATABASE.md:518` documents
     `PATCH /identity/bind` while `app.py:2084` is `@app.post`. `1203-05-PLAN.md` closes the whole
     defect class mechanically with a script diffing documented `/identity/*` routes against live
     decorators by verb+path, rather than patching one line.
   - What we knew: Line 336 no longer contains a route/verb declaration; the file has been edited since Phase 32.1-REVIEW.md's citation was written.
   - What's unclear: Whether the wrong-route/verb text still exists elsewhere in the file, or was already fixed by an intervening edit (in which case WR-02 may already be closed and D-11's bundling of it needs adjustment).
   - Recommendation: Planner re-greps `spec/DATABASE.md` for `/identity/` and `/computgraph/` route documentation near the Phase 32.1 identity-registry section before writing the WR-02 fix task; if no wrong-route/verb text is found anywhere, mark WR-02 as already-resolved and note this explicitly rather than silently dropping the task.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Neo4j (live, in compose) | CQ3 fixture live evaluation, DE-01 runner (if a leg is added per D-14) | Not verified live in this session (no docker exec run) | — (compose service, per CLAUDE.md service map) | Fixture-only / mocked-session tests (the pattern `test_dg_identity.py`'s `FakeGraph`/`FixtureSession` already uses) can validate Cypher shape without a live database; live confirmation still needed before claiming the CQ3 gate is met with a running stack |
| dotnet SDK (net7.0/net9.0) | Rebuilding `DG.sln` after `DesignStateIdGenerator.cs`/`DgIdMintingService.cs` changes | Not verified in this session | — | None — a rebuild is mandatory per the phase's own known gotcha; no fallback exists for this |
| Python 3.14 (per pytest cache dirs observed: `cpython-314-pytest-9.0.2`) | Running `data-service/tests/` | Confirmed indirectly (pytest cache artifacts present) | 3.14 (inferred) | — |
| `MSYS_NO_PATHCONV=1` (Git Bash env, Windows) | Any `docker exec`/`docker cp` command touching `/tmp` or `/app` paths | Environmental, not a tool — must be set per-command | — | None — must be remembered per the project's own documented gotcha |

**Missing dependencies with no fallback:**
- Live Neo4j confirmation for the CQ3 gate — the planner must schedule a live-stack verification step (matching the "verify a running container holds the code before trusting a live evidence run" caveat) as part of the CQ3 fixture task, not skip straight to a mocked-session-only claim of gate satisfaction.

**Missing dependencies with fallback:**
- Live Neo4j for early development/unit testing — `FixtureSession`/`FakeGraph`-style mocking (already established in `test_dg_identity.py`) is a viable fallback for TDD-style development before a live-stack confirmation pass.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (C#) | xUnit, via `dotnet test DG/tests/DG.Tests/` |
| Framework (Python) | pytest, via `python -m pytest data-service/tests -q` |
| Config file | None found in `data-service/` (no `pytest.ini`/`pyproject.toml` test section detected); `DG.Tests.csproj` governs the C# side |
| Quick run command (C#, scoped) | `cd DG/tests/DG.Tests && dotnet test -v minimal --filter "FullyQualifiedName~Identity\|FullyQualifiedName~DesignStateIdGenerator"` |
| Quick run command (Python, scoped) | `python -m pytest data-service/tests/test_dg_identity.py data-service/tests/test_cg_input_bindings.py data-service/tests/test_computgraph_publish.py -q` |
| Full suite command (C#) | `dotnet test DG/tests/DG.Tests/ -v minimal` |
| Full suite command (Python) | `python -m pytest data-service/tests -q` |

**Known environment-dependent failures (not regressions, per project memory):** 4 `DesignStateValidationFlowTests` (C#) fail fast when Neo4j is down; 4 `test_dg_context.py` tests (Python) fail from the host because `neo4j` hostname resolves only inside compose. Baseline per 1202-CONTEXT.md: "823 passed / 1 skipped / 1 pre-existing-failed" for the Python suite pre-this-phase — planner should re-establish this baseline count immediately before starting work (it may have shifted since 1202).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-12 | ObjState/core identity minting uses one documented authority + migration policy | doc + unit | `dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests` (regression pins for both minting forms) | ✅ `DesignStateIdGeneratorTests.cs` exists; new D-08/D-09 assertions needed |
| ALGN12-12 | Both ObjState minting forms retained, contract states authority per case | doc | Manual review of `spec/DG-ID.md`'s new DesignState section | ❌ Wave 0 — `spec/DG-ID.md` DesignState section does not exist yet (D-06) |
| ALGN12-12 | project-in-hash gap closed additively (D-08) | unit | New xUnit fact: `ComputeParamStateId_ShouldChange_WhenProjectDiffers` (or per-function equivalent) in both C# and Python | ❌ Wave 0 — needs new test methods added to `DesignStateIdGeneratorTests.cs` and a new/extended Python identity test file for DesignState IDs (no current Python counterpart to `DesignStateIdGeneratorTests.cs` — new file needed, e.g. `data-service/tests/test_design_state_ids.py`, IF Python ever mirrors DesignState minting; else document that DesignState minting is C#-only and no Python parity test applies) |
| ALGN12-12 | CR-02 fixed by length-prefix in all six functions, cross-boundary regression test in both languages | unit | `dotnet test ... --filter "FullyQualifiedName~PipeCollision"` + `pytest data-service/tests/test_dg_identity.py -k collision` (both new) | ❌ Wave 0 — collision regression tests do not exist yet in either language |
| ALGN12-13 | Platform conflict/detach/provenance specified AND tested (D-12) | integration | `pytest data-service/tests/test_dg_identity.py -k "conflict or detach or provenance"` | ✅ Partially — `test_detach_preserves_dgid_and_frees_binding`, `test_write_shared_property_is_idempotent` (last-write-wins) already exist and pass; D-12/D-13 mainly need documentation confirmation, not new test infra |
| ALGN12-13 | CR-01 fixed: mint→bind→publish→assert binding survives | integration | New pytest: mint→bind→simulate publish MERGE coinciding on `(cgId, definitionId, project)`→assert same node | ❌ Wave 0 — this specific regression test does not exist; `test_mint_identity_idempotent` exists but does not exercise the publish-coincidence scenario |
| ALGN12-14 | `ATTRIBUTE_OF` implemented, both query directions evidenced | integration (fixture) | New: `python -m pytest data-service/tests/test_computgraph_publish.py -k attribute_of` + a live-stack CQ3 fixture run | ❌ Wave 0 — `_publish_attribute_of` and its tests do not exist |
| ALGN12-14 | Full schema propagation (D-05) | doc audit | Manual checklist walk of CLAUDE.md's Schema Change Propagation list | ❌ Wave 0 — no automated check; recommend a grep-based "does `ATTRIBUTE_OF` appear in every listed file" verification step as the closest thing to automation |

### Sampling Rate
- **Per task commit:** scoped pytest/xUnit filter matching the touched module (see Quick run commands above)
- **Per wave merge:** full suite both languages (`dotnet test DG/tests/DG.Tests/ -v minimal` AND `python -m pytest data-service/tests -q`)
- **Phase gate:** both full suites green (modulo the documented environment-dependent Neo4j-down failures) before `/gsd-verify-work`; additionally, a live-stack CQ3 fixture run proving both query directions, per the ROADMAP gate wording

### Wave 0 Gaps
- [ ] `data-service/tests/test_dg_identity.py` (or a new sibling file) — needs collision-regression test for D-09's length-prefix fix, plus the mint→bind→publish-coincidence regression test for D-10/CR-01
- [ ] `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — needs project-in-hash assertions (D-08) and pipe-collision regression assertions (D-09) for all four `DesignStateIdGenerator` functions
- [ ] `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs` — needs updated golden vector post-D-09, plus a collision regression test
- [ ] A new or extended `data-service/tests/test_computgraph_publish.py` (or a new `test_attribute_of.py`) — needs forward+reverse query tests for the new `ATTRIBUTE_OF` edge, mirroring PAPER-C-032's exact shape
- [ ] New fixture directory `fixtures/golden/<sibling-path>/` (name at planner's discretion, e.g. `fixtures/golden/attribute-of/` or `fixtures/golden/cq3/`) — README + seed Cypher + expected-result JSON, following the exact structure of the existing `fixtures/golden/replay/` precedent (confirmed on disk: `README.md`, `seed-replay.cypher`, `mixed-verdicts.json`)
- [ ] Framework install: none — all frameworks (xUnit, pytest) are already present and configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase touches no auth surface; Phase 1205 owns authorization/tenancy |
| V3 Session Management | No | N/A |
| V4 Access Control | No | Project-scoping (already enforced via bound Cypher parameters) is a multi-tenancy isolation control, not an access-control/authz control; out of scope here per the phase boundary (Phase 1205 owns authorization) |
| V5 Input Validation | Yes | `pydantic` models (`MintRequest`, `BindRepresentationRequest`) already validate platform/native_id_kind enums; D-10's entity-kind decision (if added) should follow the same `field_validator` pattern already used for `platform`/`native_id_kind` |
| V6 Cryptography | Yes (narrow) | SHA-256 is used for deterministic content-addressing (identity minting), explicitly NOT as an authenticity/integrity control (the `DesignStateIdGenerator.cs` docstring itself states this: "SHA-256 here is content-addressing, not an authenticity control"). No new cryptographic requirement is introduced by this phase; the existing non-cryptographic-use framing must be preserved in any new documentation (D-06's `spec/DG-ID.md` extension) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via unparameterized identity strings | Tampering | Already mitigated — `dg_identity.py`'s module docstring states every `session.run` receives parameters as a dict, never f-string/`.format` interpolated (T-32.1-03a); D-01/D-02's new `_publish_attribute_of` MUST follow the identical pattern (parameterized `UNWIND $rows` as the existing `_publish_param_links` does) |
| Cross-project data leakage via unscoped MERGE | Information Disclosure | Already mitigated — every Cypher touching Computgraph/Metagraph entities scopes by `project` in the MATCH/MERGE key (D-03 requires this for the new `ATTRIBUTE_OF` edge explicitly, citing the `migrations/2026-06-23_var_project_merge_key.cypher` precedent) |
| Silent identity re-binding (native id hijack) | Spoofing / Tampering | Already mitigated for the existing binding flow — `bind_representation`'s anti-misbinding guard (T-32.1-03b) rejects a repoint with `DGID_AMBIGUOUS_BINDING` rather than silently reassigning; D-10's CR-01 fix must preserve this guard's semantics when making `mint_identity` label/kind-aware |
| Hash-input delimiter collision (CR-02) | Tampering (identity collision, not classic injection) | D-09's length-prefix fix is the standard mitigation being applied this phase — this is the primary security-relevant defect this phase closes |

## Sources

### Primary (HIGH confidence — direct disk reads, this session)
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` (full file read) — all four minting functions, doc-comments, `HashToHex16`
- `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` (full file read) — `Mint`, hash-input contract
- `data-service/dg_identity.py` (full file read) — `compute_dg_id`, `mint_identity`, binding/detach/shared-property helpers
- `spec/DG-ID.md` (full file read) — the normative identity spec D-06 extends
- `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` (full file read) — existing golden-vector regression pins
- `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs` (full file read) — C# golden vector
- `data-service/tests/test_dg_identity.py` (full file read) — Python golden vector, confirmed byte-identical to C# side
- `data-service/cg_input_bindings.py` (partial, 1-130 and 280-527 read) — `read_rule_limit`, `classify_rule`, `select_parameters`
- `data-service/computgraph_publish.py` (targeted reads, PARAM_LINK derivation + MERGE) — the derive-then-MERGE precedent
- `data-service/cg_structure_checks.py` (targeted read, dangling-PARAM_LINK check)
- `data-service/dg_context.py` (targeted reads, `ALLOWED_PROPERTIES` + `validate_cypher`)
- `data-service/app.py` (targeted read, `/identity/mint`, `/identity/resolve`, `/identity/bind` routes)
- `ontology/DesignGrammar-V7.md`, `ontology/DesignGrammar-V7.owl` (targeted reads, `attributeOf`/`ATTRIBUTE_OF` TBox declaration)
- `ontology/dg-shapes.ttl` (grep + count) — confirmed no `attributeOf`/`paramLink` shape, 18 node shapes (not 20)
- `spec/RULE-PARTITION-POLICY.md` (partial read) — decision table, no cross-layer-bridge row exists yet
- `spec/DATABASE.md` (targeted read around cited line 336) — confirmed drift from CONTEXT.md's citation
- `cypher_template.txt` (targeted read, Atom MERGE pattern) — A1/A2/A3/H1 atom-type convention
- `llm/structure_rules.json` (full file read) — `inputBindings` shape, current 2 entries
- `docs/reviews/theory-implementation-alignment/evidence/paper-claims.json` (targeted reads) — PAPER-C-032 confirmed verbatim
- `fixtures/golden/` directory listing — confirmed `replay/` sibling-path precedent exists on disk
- `fixtures/golden/replay/` directory listing — confirmed README.md/seed-replay.cypher/mixed-verdicts.json structure
- `.planning/phases/1203-.../1203-CONTEXT.md` (full file read) — the 14-decision context this research verifies against
- `.planning/REQUIREMENTS.md` (targeted read, lines 25-44) — ALGN12-12/13/14 requirement text
- `.planning/ROADMAP.md` (targeted read, lines 155-184) — Phase 1203 deliverables and gate
- `tools/de01/` directory listing — confirmed DE-01 runner location for D-14's discretionary decision

### Secondary (MEDIUM confidence)
- graphify query/explain output — used only for initial orientation; confirmed STALE against disk (missing `ComputeObjectStateIdFromRef`, `ComputeCaptureEventStateId`, wrong line numbers) and NOT relied upon for any claim in this document

### Tertiary (LOW confidence)
- None — every substantive claim in this document was checked against disk in this session or is a direct quote from CONTEXT.md's own already-verified citations

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new technology; all existing patterns confirmed present and functioning on disk
- Architecture: HIGH — the derive-then-MERGE and atom-type-discrimination patterns are confirmed shipping precedents in this exact codebase, not external best practices
- Pitfalls: HIGH — each pitfall is grounded in a specific disk-verified fact (missing API.md entry, stale DATABASE.md line, shape-count discrepancy, existing fixture precedent)

**Research date:** 2026-09-22
**Valid until:** Recommend re-verification if planning is deferred more than 3-5 days — this codebase shows same-day drift on cited line numbers (per the `spec/DATABASE.md` discrepancy found in this very session), so anchors should be re-checked immediately before task-writing regardless of this estimate.
