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

<!-- gsd:write-continue -->
