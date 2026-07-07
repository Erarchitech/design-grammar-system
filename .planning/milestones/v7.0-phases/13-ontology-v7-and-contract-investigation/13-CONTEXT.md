# Phase 13: Ontology V7 and Contract Investigation - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock every V7 name and resolve the `GH_DesignGrammars.pdf`-internal conflicts so phases 14–20 build on a stable contract. This is an **investigation + rename + mapping** phase — no runtime code changes.

Deliverables: `DesignGrammar-V7.owl` (via `apply_v7_rename.py`), `V6-to-V7-mapping.md` recovery file, regenerated extension facades + `catalog-v001-V7.xml` + `DesignGrammar-V7.md`, an investigation note resolving the three flagged conflicts, and a port↔IRI map for all 14 components.

**Already locked upstream (do NOT re-open):**
- Full V6→V7 rename to schema notation; `apply_v7_rename.py` follows the `apply_v6_*.py` script pattern — *ONTO-01, decision note*
- State-trio names `ObjState` / `ParamState` (was DefState) / `PropState`; rule-level `SWRL`/`RuleName`/`RuleDescription` — *ONTO-03/04*
- `V6-to-V7-mapping.md` recovery file; V6 owl left untouched — *ONTO-02, decision note*
- Port policy: update where overlapping, keep where not; DB not relabeled beyond Knowledge→Spec — *PROJECT.md Key Decisions*
- OWL files are documentation-only (zero runtime consumers) — rename has no runtime coupling — *session note*

</domain>

<decisions>
## Implementation Decisions

### DesignState Layer Placement — resolves conflict (b)
- **D-01:** A `DesignState` node lives in **`graph='ValidGraph'`** (corrected from the v3 template's `graph='Metagraph'`). ValidGraph is canonical because DesignState is run/validation data, and the PDF's `VALIDATION GRAPH` component reads it from the ValidGraph handle. The investigation note records the PDF-internal conflict resolution: cypher_template v3 stored DesignState with `graph='Metagraph'` (lines 49-50, 113-116); the PDF's read wiring wins.
- **D-02:** The PDF statement *"New Design State can only pass to Metagraph through Validator"* is recorded as **superseded on destination only** — in v7.0 the destination is **ValidGraph**, but the *"only through Validator"* constraint is **preserved**: no direct-insert path for DesignState.
- **D-03:** DesignState is written **only by VALIDATOR on publish**, `MERGE`'d by `StateId + project` (dedup across runs).
- **D-04:** **Cardinality — one DesignState ↔ many Runs.** The same DesignState (same `StateId`) validated against different rules produces multiple Runs, all linked to the single shared DesignState node. Each Run references exactly one DesignState; a DesignState may be referenced by many Runs. (Exact relationship type/direction is Phase 14 cypher design — see Claude's Discretion.)
- **D-05:** **No orphan DesignStates.** A DesignState exists in ValidGraph only with **≥1 Run linked** — a direct consequence of D-02 (it can only arrive via the Validator publish path, which always creates a Run).

### Run Status Model — resolves conflict (a)
- **D-06:** **`Run.ValidStatus` = a Boolean array** (Neo4j list property on the Run node), **one element per `ObjState`** in the validated DesignState, **index-matched** to the DesignState's ObjState order. Each element = that object's pass/fail against the rule. This deliberately replaces the ONTO-04-proposed *single overall boolean* — the user reshaped it to per-object.
- **D-07:** **No separate `Status` text enum.** VALIDATION GRAPH's `Status` output is the read-back of the same `ValidStatus` array — naming unified to **`ValidStatus`**. The PDF's `ValidStatus`(Boolean at VALIDATOR)-vs-`Status`(text at VALIDATION GRAPH) is a **cosmetic naming inconsistency**, resolved to one field named `ValidStatus` typed as a Boolean list. Overall pass = `AND(ValidStatus)` — **derived, not stored**.
- **D-08:** **`Run.SendStatus` = a single Boolean** per Run (publish-to-Speckle/data-service success). Orthogonal to `ValidStatus`; set true when `SendValid=true` and the publish succeeds. Publishing is one operation per run, so it is **not** per-object.

### Port↔IRI Contract Format — ONTO-06 (auto-locked, not discussed)
- **D-09:** The port↔IRI map is delivered as **`ontology/port-iri-map-V7.md`** (successor of the non-machine-readable `GH-mapping.png`) — a single greppable master markdown table with columns **`Component | Port | Direction (in/out) | V7 IRI | Layer | Notes`**, covering every output port (and inputs that carry IRIs) of all 14 components. Markdown so the planner can read/diff it directly and phases 14/17/18 can grep it.

### Ontology Version Marker & Investigation-Note Home — resolves conflict (c) (auto-locked, not discussed)
- **D-10:** V7 owl carries **`owl:versionInfo = "7.0"`**; the stale `rdfs:comment "Schema version: v3"` (V6 owl line ~46) is **removed** (or replaced with `"Schema version: v7"` — either satisfies the policy). Single source of version truth = `versionInfo`; no schema-version comment drift. Applied by `apply_v7_rename.py`.
- **D-11:** The investigation note lives at **`ontology/V7-INVESTIGATION.md`** (next to the ontology artifacts, referenced by the port↔IRI map). It records the resolution of conflicts (a)/(b)/(c), the final state-kind names, and every superseded PDF statement. A condensed decision note is mirrored to `DG_OBSIDIAN/knowledge/decisions/` at session-save per project convention.

### Claude's Discretion
- Exact relationship **type, direction, and label** for the Run→DesignState link (contract is many-Runs-to-one-DesignState; physical modeling is Phase 14).
- Column ordering/formatting details of `port-iri-map-V7.md` within the stated column set.
- Whether the stale `v3` comment is deleted vs. rewritten to `v7` (both satisfy D-10).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Component contract & ontology source
- `ontology/GH_DesignGrammars.pdf` — the 14-component schema; source of truth for ports, VALIDATION GRAPH / VALIDATOR wiring, and the flagged conflicts
- `ontology/DesignGrammar-V6.owl` — rename source (V6→V7); version markers at line ~46 (stale `Schema version: v3`) and line ~48 (`versionInfo 6.1`)
- `ontology/DesignGrammar-V6.md` — V6 docs; regenerated as `DesignGrammar-V7.md`

### Rename / regeneration script pattern (`apply_v7_rename.py` follows these)
- `ontology/apply_v6_restructure.py` — main OWL-transformation script pattern to mirror
- `ontology/apply_v6_extensions.py` — extension-facade (standards / BOT / Topologic) regen pattern
- `ontology/make_docs_v6.py`, `ontology/make_export_v6.py`, `ontology/export_to_markdown_v6.py` — doc/markdown export pattern for `DesignGrammar-V7.md`
- `ontology/catalog-v001-V6.xml` — catalog pattern → `catalog-v001-V7.xml`

### Conflict spots (read to write the investigation note)
- `cypher_template.txt` lines 49-50 and 113-116 — current `DesignState … graph='Metagraph'` placement corrected to ValidGraph by D-01

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — ONTO-01..06 (esp. ONTO-04's full conflict list a/b/c)
- `.planning/ROADMAP.md` — Phase 13 goal + 4 success criteria

### Prior decisions (project vault)
- `DG_OBSIDIAN/knowledge/decisions/Ontology V7 full rename over incremental.md` — rename rationale, zero runtime coupling, mapping-file purpose
- `DG_OBSIDIAN/sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema.md` — PDF analysis, 61/43/64 entity inventory, SpecGraph drift finding

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`apply_v6_*.py` transformation scripts**: idempotent OWL/XML transform pattern (load owl → apply renames → write V7). `apply_v7_rename.py` reuses this structure. OWL files are documentation-only — never loaded at runtime (confirmed in session note) — so the rename has zero runtime coupling.
- **`DesignStateIdGenerator`** (DG.Core, shipped v3.0 Phase 7): `DS_/OS_/OI_` id prefixes; extended in v7.0 for ObjState/ParamState/PropState — informs the state-kind naming this phase locks.
- **`VariableTypeInferrer`** (DG.Core.Parsing): read-time Object/Property partition; not modified here, but the port↔IRI map must name the `DataProperty`/`ObjProperty` V7 IRIs it partitions into (RULE DECONSTRUCT, Phase 18).

### Established Patterns
- **Layer-tagging via `graph=` property** on every node (`OntoGraph`/`Metagraph`/`ValidGraph`/`SpecGraph`) — the DesignState layer decision (D-01) extends this pattern.
- **Index-matched list contract** across components (OBJECT STATE, DESIGN STATE) — the per-object `ValidStatus` array (D-06) reuses it.
- **Neo4j keeps existing labels; ontology↔DB naming is documented, not enforced** (PROJECT.md) — `port-iri-map-V7.md` is where V7 IRIs meet DB labels.

### Integration Points
- `cypher_template.txt` v4 (Phase 14) consumes D-01 (DesignState layer) + D-06/07/08 (Run fields)
- VALIDATION GRAPH (Phase 17) reads `Run` / `ValidStatus` / `DesignState` from the ValidGraph handle per D-01/D-07
- VALIDATOR persistence (Phase 18) writes the `ValidStatus` array + `SendStatus` + Run→DesignState link (D-05..D-08)
- Model Viewer read path GHVL-06 (Phase 18) consumes the per-object results

</code_context>

<specifics>
## Specific Ideas

- The user **deliberately reshaped `ValidStatus`** from a single overall boolean to a **per-object boolean list, index-matched to `ObjState`** — carry this verbatim into Phases 14/17/18; it is not an implementation guess.
- The user emphasized the **no-orphan invariant** as a hard constraint: *"DesignState passes to ValidGraph only through Validator, so at least one Run must be linked when DesignState is stored in ValidGraph."* Treat it as an enforced rule, not a guideline.

</specifics>

<deferred>
## Deferred Ideas

- **Research flag for Phase 18 (not a scope change):** per-object `ValidStatus` *population* semantics — does the array cover **all** `ObjState`s in the DesignState, or only those matching the rule's target Class? Phase 13 locks the array **shape** (Boolean list) + **index-matching** (to the ObjState order); the population/binding rule belongs to Phase 18 (VALIDATOR variable binding from the composed DesignState). Resolve there before persistence.
- No out-of-scope capabilities surfaced — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-ontology-v7-and-contract-investigation*
*Context gathered: 2026-07-03*
