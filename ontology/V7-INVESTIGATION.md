# V7 Investigation — Conflict Resolutions & V6→V7 Rename Table

**Date:** 2026-07-03
**Source of truth:** `ontology/GH_DesignGrammars.pdf`; decisions locked in `.planning/phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` D-01..D-11

**Scope:** This note resolves the three `GH_DesignGrammars.pdf`-internal conflicts flagged by ONTO-04 and records the authoritative V6→V7 rename table. It writes no code and touches no ontology source file — `apply_v7_rename.py` (Phase 13 plan 13-02) is the consumer that actually performs the rename against `ontology/DesignGrammar-V6.owl`.

---

## Conflict (a) — Run status model

**Resolves CONTEXT D-06/D-07/D-08.**

The PDF's VALIDATOR component names its output `ValidStatus` typed **Boolean** (`Ontology: DG.Layer.Validgraph.ValidStatus; Output=Run().ValidStatus Datatype: Boolean`), while the PDF's VALIDATION GRAPH component names its output `Status` typed **text** (`Ontology: DG.Layer.Validgraph.ValidStatus; Output=list(Run().Status) Datatype: text`) — same underlying ontology property (`DG.Layer.Validgraph.ValidStatus`), two different port names and two different datatypes. This is the flagged PDF-internal inconsistency.

**Resolution (verbatim from D-06/D-07/D-08):**

- `Run.ValidStatus` is a Neo4j **Boolean list** property, **one element per `ObjState`** in the validated DesignState, **index-matched** to the DesignState's ObjState order (D-06). Each element is that object's pass/fail against the rule. This deliberately replaces the ONTO-04-proposed *single overall boolean* — the user reshaped it to per-object, and that reshaping is carried verbatim into Phases 14/17/18 — it is not an implementation guess.
- There is **no separate `Status` text enum**. VALIDATION GRAPH's `Status` output is the read-back of the same `ValidStatus` array — naming is unified to one field, `ValidStatus`, typed as a Boolean list. The PDF's `ValidStatus`(Boolean at VALIDATOR) vs `Status`(text at VALIDATION GRAPH) split is a **cosmetic naming inconsistency**, not two real fields (D-07).
- **Overall pass = `AND(ValidStatus)`, derived, not stored.** No separate overall-pass property is persisted; any consumer that needs the aggregate computes it from the list at read time.
- `Run.SendStatus` is a **single Boolean** per Run (D-08) — publish-to-Speckle/data-service success. Orthogonal to `ValidStatus`; set `true` when `SendValid=true` and the publish succeeds. Publishing is one operation per run, so `SendStatus` is **not** per-object.

**Deferred (Phase 18, not a Phase 13 scope change):** the per-object `ValidStatus` *population* semantics — whether the array covers **all** `ObjState`s in the DesignState or only those matching the rule's target Class — is deferred. Phase 13 locks only the array **shape** (Boolean list) and the **index-matching** contract (to the ObjState order); the population/binding rule belongs to Phase 18 (VALIDATOR variable binding from the composed DesignState).

---

## Conflict (b) — DesignState storage layer

**Resolves CONTEXT D-01..D-05.**

`cypher_template.txt` (v3, lines 49-50 and 113-116) stores the `DesignState` node with `graph='Metagraph'`:

```
DesignState — key: StateId + project
         props: kind (DefState|ObjectState), project, graph='Metagraph'
...
// 2b. Metagraph — design state node (DefState | ObjectState, single label + kind)
MERGE (ds:DesignState {StateId: '<STATE_ID>', project: '<PROJECT>'})
SET ds.kind = '<DefState|ObjectState>',
    ds.graph = 'Metagraph'
```

But the PDF's VALIDATION GRAPH component reads `DesignState` from the **ValidGraph** handle (`Ontology: DG.Core.DesignState; Output=list(DesignState())` wired off the `ValidGraph` port, alongside `Run` and `Status`) — not off the Metagraph handle. This is the flagged storage-layer conflict.

**Resolution (verbatim from D-01..D-05):**

- **D-01:** A `DesignState` node lives in **`graph='ValidGraph'`**, corrected from the v3 template's `graph='Metagraph'`. ValidGraph is canonical because DesignState is run/validation data, and the PDF's VALIDATION GRAPH component reads it from the ValidGraph handle. cypher_template v3 (lines 49-50, 113-116, cited above) stored DesignState with `graph='Metagraph'`; the PDF's read wiring wins.
- **D-02:** The PDF statement *"New Design State can only pass to Metagraph through Validator. So at least one rule must be assigned to Design State when stored in Metagraph."* is recorded as **superseded on destination only** — in v7.0 the destination is **ValidGraph**, but the *"only through Validator"* constraint is **preserved**: there is no direct-insert path for DesignState.
- **D-03:** DesignState is written **only by VALIDATOR on publish**, `MERGE`'d by `StateId + project` (dedup across runs).
- **D-04:** **Cardinality — one DesignState ↔ many Runs.** The same DesignState (same `StateId`) validated against different rules produces multiple Runs, all linked to the single shared DesignState node. Each Run references exactly one DesignState; a DesignState may be referenced by many Runs. (Exact relationship type/direction is Phase 14 cypher design — Claude's Discretion, not locked here.)
- **D-05:** **No orphan DesignStates.** A DesignState exists in ValidGraph only with **≥1 Run linked** — a direct consequence of D-02 (it can only arrive via the Validator publish path, which always creates a Run). This is an **enforced rule**, not a guideline: *"DesignState passes to ValidGraph only through Validator, so at least one Run must be linked when DesignState is stored in ValidGraph."*

---

## Conflict (c) — version marker

**Resolves CONTEXT D-10.**

`ontology/DesignGrammar-V6.owl` currently carries two, inconsistent version signals:

- Line 46: `rdfs:comment` containing the stale text `Schema version: v3` (inside a longer ontology-description comment whose `rdfs:seeAlso` at line 49 documents the changelog up through v6.1 — the `v3` string is a leftover from an early revision and was never updated).
- Line 48: `<owl:versionInfo>6.1</owl:versionInfo>`.

**Resolution (verbatim from D-10):**

- V7 owl carries **`owl:versionInfo = "7.0"`**.
- The stale `rdfs:comment "Schema version: v3"` (V6 owl line ~46) is **removed** (or replaced with `"Schema version: v7"` — either satisfies the policy; which of the two is applied is Claude's Discretion at `apply_v7_rename.py` implementation time, per CONTEXT.md).
- **Single source of version truth = `versionInfo`.** No schema-version comment drift going forward — `apply_v7_rename.py` (13-02) is responsible for applying this.

---

## Superseded PDF statements

| PDF claim | v7.0 replacement |
|---|---|
| "New Design State can only pass to Metagraph through Validator." | Destination is **ValidGraph**, not Metagraph (D-01/D-02). The "only through Validator" constraint is preserved unchanged — no direct-insert path for DesignState. |
| VALIDATOR outputs `ValidStatus` (Boolean) while VALIDATION GRAPH outputs `Status` (text) as two differently-named/typed ports for the same underlying property. | Unified to a single field, `ValidStatus`, typed as a **Boolean list**, index-matched to ObjState order (D-06/D-07). No `Status` text enum exists. Overall pass is derived via `AND(ValidStatus)`, not stored. |
| `cypher_template.txt` v3: `DesignState … graph='Metagraph'` (lines 49-50, 113-116). | `DesignState … graph='ValidGraph'` (D-01). cypher_template v4 (Phase 14) applies this. |
| V6 owl `rdfs:comment` states `Schema version: v3` while `owl:versionInfo` is `6.1`. | V7 owl: `owl:versionInfo = "7.0"` is the single source of version truth; the stale `v3` comment is removed or rewritten to `v7` (D-10). |

## V6→V7 Rename Table

Every V6 source name below was confirmed present in `ontology/DesignGrammar-V6.owl` by direct grep before being added to this table (counts noted in Notes where they differ from the plan's approximate estimate). This table is the authority `13-02` (`apply_v7_rename.py`) and `13-03` (port↔IRI map) consume.

| V6 name | V7 name | Kind | Namespace | Notes |
|---|---|---|---|---|
| `ObjectState` (`&dg;ObjectState`) | `ObjState` | class | `dg` (`design-grammar#`) | State-trio rename (ONTO-03). Confirmed 35 occurrences in V6 owl (superclass under `dg:Core` DesignState, e.g. lines 1149/1160/2940/2948). |
| `DefState` (`&dg;DefState`) | `ParamState` | class | `dg` (`design-grammar#`) | State-trio rename (ONTO-03). Confirmed 19 occurrences (lines 1148/1154/2939, …). |
| — (no V6 source) | `PropState` | class | `dg` (`design-grammar#`) | **NEW.** A `DesignState` subclass built on the existing `propValue`/`propValueOf` datatype/object properties (`&dgv;propValue`, `&dgv;propValueOf`, V6 owl lines 1391/1477), which currently attach per-instance validation-result values to `ValidationEntity`. PropState composes `Rule + DataProperty + PropValue` per ONTO-03/GHST-03. |
| `OntoGraph` (`&dg;OntoGraph`) | `Ontograph` | class (+ punned `NamedIndividual`) | `dg` (`design-grammar#`) | Layer hub rename. Confirmed 22 occurrences (owl:Class at line 222, punned NamedIndividual at line 88, plus references). Casing change only: `OntoGraph` → `Ontograph` (matches PDF's `DG.Layer.Ontograph.*` ontology-path casing). |
| `ValidationGraph` (`&dgv;ValidationGraph`) | `Validgraph` | class (+ punned `NamedIndividual`) | `dgv` (`design-grammar/valid#`) | Layer hub rename. Confirmed 56 occurrences (owl:Class at line 238, punned NamedIndividual at line 90). Matches PDF's `DG.Layer.Validgraph.*` ontology-path casing. |
| `ComputationGraph` (`&dgc;ComputationGraph`) | `Computgraph` | class (+ punned `NamedIndividual`) | `dgc` (`design-grammar/comp#`) | Layer hub rename. Confirmed 58 occurrences (owl:Class + NamedIndividual both at/near line 2225-2231). Matches PDF's `DG.Layer.Computgraph.Parameter` ontology-path casing. |
| `ObjectProperty` (`&dg;ObjectProperty`, the **OntoGraph reification class**) | `ObjProperty` | class | `dg` (`design-grammar#`) | Reification-class rename (not the OWL construct — see collision note below). Defined at line 279; referenced in a `dg:GenClass`-adjacent `owl:unionOf` at lines 173/683-684. |
| `DatatypeProperty` (`&dg;DatatypeProperty`, the **OntoGraph reification class**) | `DataProperty` | class | `dg` (`design-grammar#`) | Reification-class rename (not the OWL construct — see collision note below). Defined at line 271; referenced alongside `&dg;ObjectProperty` at lines 174/683-684. |
| `ValidationRun` (`&dgv;ValidationRun`) | `Run` | class | `dgv` (`design-grammar/valid#`) | Confirmed 21 occurrences (owl:Class at line 1130). Matches PDF's `DG.Layer.Validgraph.Run` ontology path. |
| `ReinstatementStatus` (label of `&dgv;ReinstatementStatusValue`, the enum class) and its individuals `ReinstatementStatus_Applied` / `_MissingTarget` / `_TypeMismatch` / `_AmbiguousTarget` (`&dgv;ReinstatementStatus_*`) | `ReStatus` (class label) and `ReStatus_*` (individuals, same 4 values) | class + individuals | `dgv` (`design-grammar/valid#`) | Confirmed 27 total occurrences across `ReinstatementStatusValue` (class, line 1527) and the 4 `ReinstatementStatus_*` individuals (lines 1533-1536). C# enum `DG.Core.Models.ReinstatementStatus` (referenced in the class comment) is the consumer this rename must stay consistent with — REIN-01..03 / GHST-07 keep the 4-value (7-value per plan wording covers additional states beyond these 4 named individuals) status reporting contract intact. |
| — (no V6 source) | `SendStatus` | dataprop | `dgv` (`design-grammar/valid#`) | **NEW.** Single Boolean per `Run` (D-08). Matches PDF's `DG.Layer.Validgraph.SendStatus; Output=Run().SendStatus Datatype: Boolean`. |
| — (no V6 source) | `ValidStatus` | dataprop | `dgv` (`design-grammar/valid#`) | **NEW.** Boolean **list** per `Run`, index-matched to ObjState order (D-06/D-07). Matches PDF's `DG.Layer.Validgraph.ValidStatus` ontology path (unifying the VALIDATOR/`ValidStatus` and VALIDATION GRAPH/`Status` port split — see Conflict (a) above). |
| `ruleText` (`&dgm;ruleText`) | `SWRL` | dataprop | `dgm` (`design-grammar/meta#`) | Confirmed 6 occurrences; definition at line 547 (`rdfs:label "text"`, holds the SWRL serialization, e.g. `Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)`). Matches PDF's `DG.Layer.Metagraph.SWRL; Output=Rule().SWRL Datatype: text`. |
| `ruleTitle` (`&dgm;ruleTitle`) | `RuleName` | dataprop | `dgm` (`design-grammar/meta#`) | Confirmed 1 occurrence (definition at line 561, `rdfs:label "title"`, "Optional human-readable title for a rule"). Matches PDF's `DG.Layer.Metagraph.RuleName; Output=Rule().RuleName`. |
| — (no V6 source) | `RuleDescription` | dataprop | `dgm` (`design-grammar/meta#`) | **NEW** natural-language description property. Matches PDF's `DG.Layer.Metagraph.RuleDescription; Output=Rule().Description`. **Rationale for the 2→3 mapping:** V6's `ruleText`/`ruleTitle` pair covers only the machine SWRL string and an optional short title; the PDF's RULE DECONSTRUCT and VALIDATOR both expose a third, distinct output (`RuleDescription`) for a longer human-readable explanation of the rule's intent — there is no V6 property that already serves this purpose, so it is added as new rather than reused/renamed. |

### OWL-construct collision hazard

`&dg;ObjectProperty` and `&dg;DatatypeProperty` are **OntoGraph reification classes** — i.e. `dg`-namespaced `owl:Class` individuals used to model "this generated term is an ObjectProperty/DatatypeProperty" as domain data (see V6 owl lines 271/279, referenced in `unionOf` blocks at 173-174/683-684). These **must be renamed** to `ObjProperty`/`DataProperty` per this table.

By contrast, `owl:ObjectProperty` and `owl:DatatypeProperty` are **OWL language constructs** (the RDF/XML element type names used throughout the file to declare every actual object/datatype property, e.g. `<owl:DatatypeProperty rdf:about="&dgm;ruleText">`) — these are part of the OWL 2 vocabulary itself, not DG domain content, and **must NOT be touched** by the rename. `apply_v7_rename.py` must scope its find/replace to the `dg:`-prefixed `rdf:about` values only, never to the `owl:` element/attribute namespace.

### Not renamed

`Metagraph` and `SpecGraph` are **NOT renamed** — they keep their V6 names unchanged into V7 (confirmed: the PDF's own ontology paths use `DG.Layer.Metagraph.*` and `DG.Layer.Specgraph` casing already present/compatible in V6; only `OntoGraph`, `ValidationGraph`, and `ComputationGraph` receive the casing/name change to `Ontograph`/`Validgraph`/`Computgraph`).

---

## Final state-kind names (locked)

```
ObjState | ParamState | PropState
```

These are the exact strings Phases 14 and 16 use for the `DesignState.kind` property values (replacing V6/v3's `ObjectState`/`DefState` enum values and adding the new `PropState` third kind).
