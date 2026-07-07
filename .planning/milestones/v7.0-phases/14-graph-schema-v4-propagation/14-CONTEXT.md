# Phase 14: Graph Schema v4 Propagation - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Make every artifact that hard-codes the Neo4j graph schema speak **v4** — the three DesignState kinds (`ObjState`/`ParamState`/`PropState`), the Phase-13 Run validation model (`ValidStatus`/`SendStatus`), and rule-level SWRL — so LLM ingest, querying, NeoVis visualization, and the data-service all agree **before** any Grasshopper component code changes (Phases 16–18).

**In scope (SCHM-07..14):** `cypher_template.txt` v4, `training/dataset_schema.json` v4, both n8n workflow prompts (`rules-to-metagraph.json`, `graph-query-mcp.json`), NeoVis `config.template.js` + `index.html` hardcoded Cypher, `data-service/app.py` Cypher, a kind-migration script, the v4 successor of `updated_cypher_reference_examples_v3.cypher`, and `test/` fixtures. Plus a narrow C# read-side patch (the two coalesce lines in `Neo4jRuleRepository.cs`) needed to keep interim validation reads working under the Rule-property rename.

**This is a propagation phase, not a design phase.** The names are locked by Phase 13 (V7 rename + conflict resolutions). Discussion clarified HOW to propagate, not WHAT to name.

**Already locked upstream (do NOT re-open):**
- DesignState `kind` ∈ {ObjState, ParamState, PropState} (renames DefState→ParamState, ObjectState→ObjState) — Phase 13 D-06, ONTO-03
- DesignState lives in `graph='ValidGraph'`, written only by VALIDATOR on publish, no-orphan invariant — Phase 13 D-01/D-03/D-05
- `Run.ValidStatus` = per-ObjState **Boolean list** (index-matched to ObjState order); `Run.SendStatus` = single Boolean — Phase 13 D-06/D-08
- **No separate `Status` text enum** — unified to `ValidStatus` read-back — Phase 13 D-07
- DB keeps existing node labels except Knowledge*→Spec* (that rename is Phase 15) — PROJECT.md
- Port↔IRI contract: `ontology/port-iri-map-V7.md`

**Roadmap note:** The ROADMAP Phase-14 detail section erroneously shows "*Plans: 4/4 complete*" listing 13-01…13-04 (a copy-paste of Phase 13). Phase 14 is genuinely **not started** (progress table confirms 0/?). Fix during planning.

</domain>

<decisions>
## Implementation Decisions

### Run status model (Area 1 — resolves a stale roadmap/requirements contradiction)
- **D-01:** The v4 Run schema declares **only** `Run.ValidStatus` (Boolean list, per-ObjState, index-matched) + `Run.SendStatus` (single Boolean). **No stored `Status` text field.** Overall pass = `AND(ValidStatus)`, derived at read time. This follows Phase 13 D-07 and `ontology/port-iri-map-V7.md` (VALIDATION GRAPH `Status` port → `dgv:ValidStatus`, "not a separate text enum").
- **D-02:** ROADMAP SC#1 and REQUIREMENTS SCHM-07 both still list "`Status text`" as a Run property — that text **predates the Phase 13 investigation and is stale**. The planner should amend/annotate those docs so success criteria match D-01 (do not build a `Status` text field to satisfy the literal wording).
- **D-03:** Run and DesignState nodes are created by **VALIDATOR-on-publish**, not by LLM rule-ingest. In v4 they are **document-only** in the template's GRAPH SCHEMA reference section (so the LLM understands the full graph) but are **removed from the emitted CYPHER TEMPLATE BLOCK**. The ingest emits OntoGraph + Metagraph (rule/atom/var/literal/builtin) nodes only. (Drops the vestigial DesignState MERGE block at current `cypher_template.txt` lines 113–116.)

### Rule-node property names (Area 2)
- **D-04:** **Full rename now.** The v4 write side (cypher_template, dataset_schema, both n8n prompts) emits the canonical Rule props: **`SWRL`** (was `text`), **`RuleName`** (was `title`), **`RuleDescription`** (new, optional). Not deferred, not documentation-only.
- **D-05:** **Casing = ontology PascalCase** to match the port↔IRI contract exactly: `SWRL`, `RuleName`, `RuleDescription` (matching `dgm:SWRL`/`dgm:RuleName`/`dgm:RuleDescription`). Neo4j property names are case-sensitive — this is deliberate, not incidental.
- **D-06:** **Readers keep `coalesce(new, old)`** for backward-compat with pre-v4 nodes. Phase 14 patches the two coalesce lines in `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`:
  - line ~31: `coalesce(r.swrl, r.text, '')` → `coalesce(r.SWRL, r.swrl, r.text, '')`
  - line ~27: `coalesce(r.title, r.name, r.Rule_Id)` → `coalesce(r.RuleName, r.title, r.name, r.Rule_Id)`
  This keeps current-component validation reads working in the interim before Phases 17/18 rebuild the readers. (Rationale: under full rename a new rule has `r.SWRL` but no `r.text`, so the existing lowercase-`r.swrl` coalesce would otherwise read empty for new rules.)
- **D-07:** `RuleDescription` is **new and optional** — the LLM may emit it when the NL rule carries a description, but absence is valid; readers coalesce to empty.

### kind-migration script (Area 3 — SCHM-13)
- **D-08:** **Deliver AND execute** on a dev Neo4j. The plan includes a Docker/seed/run/verify task that captures before/after node counts as live proof of SC#5 (zero nodes with `kind` ∈ {DefState, ObjectState}). Research should first confirm whether a dev DB actually holds v3-kind DesignState data (may need seeding).
- **D-09:** Migration scope = **kind rename + layer move** (SCHM-13 mandates both): rename `kind` values (DefState→ParamState, ObjectState→ObjState) on all DesignState nodes, and move Run-linked DesignStates from `graph='Metagraph'` → `graph='ValidGraph'` (Phase 13 D-01).
- **D-10:** **Orphan policy = DELETE.** DesignState nodes with no linked Run are **deleted** to cleanly enforce the no-orphan invariant (Phase 13 D-05). Because this is destructive: the migration MUST first run a **dry-run count** of what it will delete, print it, and be **guarded to dev databases only** (never auto-run against a database presumed to be production). Follows the `migrations/` file pattern (`migrations/2026-06-23_var_project_merge_key.cypher`).

### NeoVis config (Area 4 — SCHM-11)
- **D-11:** **Reconcile to `DatatypeProperty`.** Drop the dead `DataProperty` entries from both `labels` and `visGroups` in `config.template.js` — NeoVis reads DB node labels and the DB keeps the `DatatypeProperty` label (no DataProperty-labeled nodes exist). This resolves the SCHM-11 duplicate.
- **D-12:** **State-kind colors:** `ParamState` inherits the existing DefState blue (`#a8d8ea`), `ObjState` inherits the existing ObjectState orange (`#f4a261`), and `PropState` gets a new distinct harmonious hue (green/teal — see Claude's Discretion). Remove the old `DefState`/`ObjectState` kind entries. Note the existing config comment: `DesignState` uses `group:"kind"`, so `visGroups` is keyed by kind VALUES, not by label.
- **D-13:** Also update the hardcoded Cypher in `graph-viewer/index.html` for any references to old kind values / Rule property names.

### ValidationGraph→ValidGraph layer-literal rename (Area 5 — added post-research 2026-07-03)
- **D-14 (user decision, Option B):** Research surfaced a conflict CONTEXT.md did not anticipate: Phase-13 D-01 wrote the DesignState layer literal as `graph='ValidGraph'`, but the **shipped runtime already uses `graph='ValidationGraph'`** on **1169 live nodes** (ValidationEntity ×1148, ValidationRun ×20, IntegrationConfig ×1). Left unresolved, Phase 18's future DesignState writes at `'ValidGraph'` would silently split from Run at `'ValidationGraph'`. **The user chose to rename the runtime literal to `'ValidGraph'` everywhere** (honoring D-01 literally) rather than keep `'ValidationGraph'` (the researcher's Option A). This makes `'ValidGraph'` the single canonical layer value.
- **D-14 scope (all must land in Phase 14):**
  1. **Data migration** of the 1169 live nodes: `MATCH (n {graph:'ValidationGraph'}) SET n.graph='ValidGraph'`. Follow the same safety pattern as the kind-migration (D-10): dry-run count first, dev-only guard. Consider whether this belongs in the same migration file as the kind-migration or a separate dated `migrations/` file — planner's call, but both must be delivered AND executed on the dev DB with before/after counts as proof.
  2. `data-service/app.py` — `VALIDATION_GRAPH = "ValidationGraph"` constant (line 41) → `"ValidGraph"`.
  3. `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` — `private const string ValidationGraph = "ValidationGraph"` (line 15) → `"ValidGraph"`.
  4. `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` — 5 hardcoded `graph: 'ValidationGraph'` occurrences (lines 78, 127, 187, 204, 221) → `'ValidGraph'`.
  5. The kind-migration's layer-move (D-09) targets `graph='ValidGraph'` (consistent with D-14, not `'ValidationGraph'`).
- **D-14 caveat — DB node labels unchanged:** This renames only the `graph` **property value** literal, NOT node labels. The `ValidationRun`/`ValidationEntity`/`IntegrationConfig` labels stay as-is (label renames are out of scope; the ontology↔DB label gap for `Run` remains documented-not-enforced per REQUIREMENTS Out-of-Scope). D-14 changes one string value, propagated consistently.
- **D-14 note:** This is a data-migration-bearing change folded into an otherwise mechanical propagation phase. Because it touches `app.py`, C# service + E2E tests, and 1169 live nodes, treat its verification with the same rigor as the kind-migration (SC#5-style before/after proof). Amend ROADMAP SC and REQUIREMENTS wording if they imply `'ValidationGraph'` anywhere.

### Claude's Discretion
- Exact hex for the new `PropState` color (D-12) — pick one harmonious with the existing palette (green/teal suggested); avoid clashing with Class green `#78c38a`.
- Whether the ValidationGraph→ValidGraph data migration (D-14.1) shares a `migrations/` file with the kind-migration or is a separate dated file — either is acceptable if both run with dry-run + dev-guard safety.
- Exact relationship **type/direction/label** for the Run→DesignState link when documented in the v4 schema reference (Phase 13 D-04 left physical modeling to Phase 14; contract is many-Runs-to-one-DesignState).
- Naming of the v4 successor file for `updated_cypher_reference_examples_v3.cypher` (e.g. `updated_cypher_reference_examples_v4.cypher`) — new file, following the v3 naming, vs. in-place; prefer a new v4 file so the v3 reference stays greppable during transition.
- Which n8n JSON files are source-of-truth vs. exports (see Deferred / research flag).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-13 locked contract (the source of every v4 name)
- `ontology/port-iri-map-V7.md` — the authoritative, greppable component-port → V7-IRI contract for all 14 components; names `dgv:ValidStatus`, `dgv:SendStatus`, `dgm:SWRL`/`RuleName`/`RuleDescription`, `dg:ObjState`/`ParamState`/`PropState`, and the ValidGraph layer placement. **MUST read.**
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (a) ValidStatus vs Status, (b) DesignState storage layer, (c) version marker; final state-kind names.
- `ontology/V6-to-V7-mapping.md` — old→new IRI recovery table.
- `.planning/milestones/v7.0-phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — decisions D-01..D-11 that flow directly into this phase (Run.ValidStatus per-object list, no-orphan invariant, DesignState→ValidGraph).

### Artifacts to propagate (the edit targets)
- `cypher_template.txt` — current v3.1 template; rewrite to v4 (D-01/D-03/D-04/D-05).
- `training/dataset_schema.json` — mirror the template exactly (SCHM-08).
- `n8n/workflows/rules-to-metagraph.json` — Build LLM Prompt / Prepare Graph Payload / Parse LLM Output prompts emit v4 (SCHM-09).
- `n8n/workflows/graph-query-mcp.json` — Build Cypher Prompt describes v4 data model (SCHM-10).
- `graph-viewer/config.template.js` — labels / visGroups reconciliation + state colors (SCHM-11, D-11/D-12).
- `graph-viewer/index.html` — hardcoded Cypher (SCHM-11, D-13).
- `data-service/app.py` — Cypher aligned with v4 (SCHM-12). NOTE: grep shows app.py does NOT currently read `r.text`/`r.title`/Rule status props — confirm blast radius before editing.
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — the two coalesce lines to patch (D-06); already forward-reads `r.swrl`.
- `migrations/2026-06-23_var_project_merge_key.cypher` — the migration file pattern to follow (SCHM-13).
- `training/updated_cypher_reference_examples_v3.cypher` — needs a v4 successor (SCHM-14).
- `test/` fixtures referencing v3 state kinds (`test/training_dataset.json`, `test/records*.json`, `test/neo4j_res*.json`, etc.) — audit + update (SCHM-14).

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — SCHM-07..14 (note: SCHM-07's "Status text" is superseded by D-01/D-02).
- `.planning/ROADMAP.md` — Phase 14 goal + 5 success criteria (SC#1's "Status" is stale per D-02; detail section's "4/4 plans" is a copy-paste bug).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`Neo4jRuleRepository.cs` coalesce pattern** — already reads `coalesce(r.swrl, r.text)` and `coalesce(r.title, r.name, r.Rule_Id)`; the read-side is *already* partially forward-migrated. The rename (D-04/D-06) extends this pattern rather than inventing it.
- **`migrations/` file pattern** — one existing dated `.cypher` file (`2026-06-23_var_project_merge_key.cypher`); the kind-migration follows the same convention (dated filename, self-contained Cypher).
- **`DesignStateIdGenerator`** (DG.Core, shipped v3.0 Phase 7) — `DS_/OS_/OI_` prefixes; state-kind naming this phase propagates matches its id scheme.

### Established Patterns
- **Layer-tagging via `graph=` property** on every node (`OntoGraph`/`Metagraph`/`ValidGraph`/`SpecGraph`) — the DesignState layer move (D-09) operates on this property.
- **Index-matched list contract** across components — the per-object `ValidStatus` array reuses it.
- **Neo4j keeps existing labels; ontology↔DB naming is documented, not enforced** (PROJECT.md) — drives the `DatatypeProperty` reconciliation (D-11); note this is about node LABELS, whereas Rule *property* names ARE renamed (D-04) since SCHM-07 requires the SWRL property.
- **Schema change propagation checklist** (CLAUDE.md): when changing structure, update cypher_template.txt, dataset_schema.json, n8n prompts, config.template.js, and any Cypher in Python/JS — this phase IS that checklist.

### Integration Points
- Phase 17 (VALIDATION GRAPH / graph-access) reads `Run`/`ValidStatus`/`DesignState` from the ValidGraph handle per D-01/D-09.
- Phase 18 (VALIDATOR rework, RULE DECONSTRUCT) reads real `SWRL`/`RuleName`/`RuleDescription` Rule props (D-04) instead of port-only names, and writes the `ValidStatus` array + `SendStatus`.
- Phase 15 (SpecGraph rename) touches the same config.template.js / n8n / data-service files — sequenced after 14 to avoid conflicts.

</code_context>

<specifics>
## Specific Ideas

- **Do not build a `Status` text field.** The user explicitly confirmed the Phase-13 resolution wins over the stale roadmap/SCHM-07 wording — carry D-01/D-02 verbatim; the "Status text" phrasing in REQUIREMENTS/ROADMAP is a documentation artifact to amend, not a spec to satisfy.
- **PascalCase is deliberate.** The user chose ontology-exact casing (`SWRL`, not `swrl`) precisely so DB property names match the port↔IRI contract — worth a one-time C# coalesce patch to keep interim reads alive rather than compromising the casing.
- **The migration deletes orphans and must be safe.** The user accepted destructive orphan deletion to enforce the no-orphan invariant — so the migration's dry-run count + dev-only guard (D-10) are hard requirements, not nice-to-haves.

</specifics>

<deferred>
## Deferred Ideas

- **Research flag (not a scope change):** confirm which n8n JSON files are source-of-truth vs. exports/backups before editing. `n8n/workflows/` contains `rules-to-metagraph.json` + `graph-query-mcp.json` (canonical, per CLAUDE.md) alongside `_active-graph-query.json` and `_all-workflows-export.json` (likely exports). The researcher should verify so v4 edits land in the authoritative files, not a stale export.
- **Research flag:** whether a dev Neo4j actually holds v3-kind DesignState / Metagraph-placed DesignState data to exercise the migration (D-08); if not, the execute step needs a seeding sub-step.
- No out-of-scope capabilities surfaced — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-graph-schema-v4-propagation*
*Context gathered: 2026-07-03*
