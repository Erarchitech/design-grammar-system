# Phase 14: Graph Schema v4 Propagation - Research

**Researched:** 2026-07-03
**Domain:** Neo4j graph-schema propagation across LLM prompts (n8n), NeoVis visualization config, data-service Cypher, a C# read-side patch, and a destructive dev-DB migration
**Confidence:** HIGH (all file locations, line numbers, and live-DB facts below were read or queried directly this session — Docker stack was running throughout)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Run status model (Area 1):**
- D-01: v4 Run schema declares only `Run.ValidStatus` (Boolean list, per-ObjState, index-matched) + `Run.SendStatus` (single Boolean). No stored `Status` text field. Overall pass = `AND(ValidStatus)`, derived at read time.
- D-02: ROADMAP SC#1 / REQUIREMENTS SCHM-07 "Status text" wording is stale — predates Phase 13. Planner should amend/annotate those docs, not build a Status text field.
- D-03: Run and DesignState nodes are created by VALIDATOR-on-publish, not by LLM rule-ingest. In v4 they are document-only in the template's GRAPH SCHEMA reference section but removed from the emitted CYPHER TEMPLATE BLOCK. Ingest emits OntoGraph + Metagraph nodes only. Drops the vestigial DesignState MERGE block at current `cypher_template.txt` lines 113-116.

**Rule-node property names (Area 2):**
- D-04: Full rename now. v4 write side emits `SWRL` (was `text`), `RuleName` (was `title`), `RuleDescription` (new, optional). Not deferred.
- D-05: Casing = ontology PascalCase (`SWRL`, `RuleName`, `RuleDescription`) matching `dgm:SWRL`/`dgm:RuleName`/`dgm:RuleDescription`. Deliberate, not incidental.
- D-06: Readers keep `coalesce(new, old)` for backward-compat. Patches two coalesce lines in `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`:
  - line ~31: `coalesce(r.swrl, r.text, '')` -> `coalesce(r.SWRL, r.swrl, r.text, '')`
  - line ~27: `coalesce(r.title, r.name, r.Rule_Id)` -> `coalesce(r.RuleName, r.title, r.name, r.Rule_Id)`
- D-07: `RuleDescription` is new and optional; absence is valid, readers coalesce to empty.

**kind-migration script (Area 3 — SCHM-13):**
- D-08: Deliver AND execute on a dev Neo4j. Plan includes a Docker/seed/run/verify task capturing before/after node counts as live proof of SC#5.
- D-09: Migration scope = kind rename + layer move: rename `kind` values (DefState->ParamState, ObjectState->ObjState) on all DesignState nodes, and move Run-linked DesignStates from `graph='Metagraph'` -> `graph='ValidGraph'`.
- D-10: Orphan policy = DELETE. DesignState nodes with no linked Run are deleted. Migration MUST first run a dry-run count, print it, and be guarded to dev databases only. Follows `migrations/2026-06-23_var_project_merge_key.cypher` pattern.

**NeoVis config (Area 4 — SCHM-11):**
- D-11: Reconcile to `DatatypeProperty`. Drop dead `DataProperty` entries from `labels` and `visGroups` in `config.template.js`.
- D-12: State-kind colors: `ParamState` inherits DefState blue (`#a8d8ea`), `ObjState` inherits ObjectState orange (`#f4a261`), `PropState` gets a new distinct hue (green/teal, Claude's Discretion). Remove old `DefState`/`ObjectState` kind entries. `DesignState` uses `group:"kind"` so `visGroups` is keyed by kind VALUES, not label.
- D-13: Also update hardcoded Cypher in `graph-viewer/index.html` for old kind values / Rule property names.

### Claude's Discretion
- Exact hex for `PropState` color (D-12) — harmonious with existing palette, avoid clashing with Class green `#78c38a`.
- Exact relationship type/direction/label for the Run->DesignState link when documented in the v4 schema reference (contract is many-Runs-to-one-DesignState).
- Naming of the v4 successor file for `updated_cypher_reference_examples_v3.cypher` — prefer a new v4 file so the v3 reference stays greppable during transition.
- Which n8n JSON files are source-of-truth vs. exports (resolved by this research — see Open Question 1 below).

### Deferred Ideas (OUT OF SCOPE)
- Research flag (not a scope change): confirm n8n file authority before editing — resolved below.
- Research flag: whether dev Neo4j holds v3-kind DesignState data — resolved below (it does not; seeding required).
- No out-of-scope capabilities surfaced during discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHM-07 | `cypher_template.txt` v4 — DesignState kind trio, Run ValidStatus/SendStatus (no Status text), rule-level SWRL | See "Artifact 1: cypher_template.txt" below — exact lines to remove/rewrite identified |
| SCHM-08 | `training/dataset_schema.json` v4 mirrors the template | See "Artifact 2: dataset_schema.json" — current v3.1 JSON structure mapped field-by-field |
| SCHM-09 | n8n `rules-to-metagraph.json` prompts emit v4 | See "Artifact 3" — 4 nodes identified (3 named in CONTEXT + 1 additional found: `Annotate Graph Props`), with exact embedded-string line targets |
| SCHM-10 | n8n `graph-query-mcp.json` Build Cypher Prompt describes v4 | See "Artifact 4" — exact prompt-array lines identified |
| SCHM-11 | NeoVis `config.template.js` + `index.html` updated | See "Artifact 5" and "Artifact 6" — current file read in full, DataProperty duplication and hardcoded Cypher located |
| SCHM-12 | `data-service/app.py` Cypher aligned with v4 | See "Artifact 7" — confirms zero Rule-prop blast radius; surfaces a **critical `ValidationGraph`-vs-`ValidGraph` naming conflict** requiring an explicit decision |
| SCHM-13 | kind-migration script (deliver + execute on dev) | See "Runtime State Inventory" and "Validation Architecture" — live DB queried, confirms zero DesignState nodes exist; seeding sub-step required |
| SCHM-14 | v4 successor of `updated_cypher_reference_examples_v3.cypher` + `test/` fixture audit | See "Artifact 10" and "Artifact 11" — fixture files enumerated, confirmed non-functional (no automated test loads them) |
</phase_requirements>

## Summary

This is a pure propagation phase: no new libraries, no new architecture, just making ~11 already-identified artifacts agree on schema v4 (three DesignState kinds, PascalCase Rule properties, Run.ValidStatus/SendStatus, no Status text). Every artifact was read directly this session with exact line numbers captured below. The Docker stack (`neo4j:5.26.19`, `n8n 2.4.8`, `ollama 0.15.2`, `data-service`) was live and queryable throughout this research, which resolved both open questions CONTEXT.md flagged with hard evidence rather than inference, and surfaced one additional, more consequential finding that CONTEXT.md did not anticipate.

**Both explicitly-flagged open questions are now resolved:**
1. **n8n file authority** — `rules-to-metagraph.json` and `graph-query-mcp.json` are unambiguously canonical. `README.md` and `docs/UPDATED_SYSTEM_SETUP_AND_TEST.md` both document the exact re-import command against these two files by name (`docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json`). The underscore-prefixed files (`_active-graph-query.json`, `_all-workflows-export.json`) carry n8n's own instance-export metadata (`id`, `active`, `updatedAt`, `isArchived`) that the canonical files never have, and `_all-workflows-export.json` contains a workflow marked `"isArchived": true` from Feb 2026 — it is a stale full-instance backup, not a live source.
2. **Dev DB migration state** — Confirmed live via direct Cypher query against the running Neo4j container: **zero `DesignState` nodes exist** (label isn't even registered in the DB yet). The kind-migration script (SCHM-13) will have nothing to migrate unless the plan adds a seeding sub-step. Conversely, `Rule` (5 nodes, all v3-shaped with only `.text`, no `.title`/`.SWRL`/`.swrl`), `ValidationRun` (20 nodes), and `ValidationEntity` (1148 nodes) all already exist with real data, which is valuable for testing the coalesce backward-compat pattern (D-06) and for exercising SCHM-12.

**One critical new finding, not covered by CONTEXT.md, requiring an explicit planner/user decision before Wave assignment:** the ontology's `dgv:Validgraph` / Phase-13 D-01's literal `graph='ValidGraph'` (for future DesignState nodes) **does not match** the graph-property value already live in the database for the conceptually-identical VALIDATION GRAPH layer: `data-service/app.py`, `DG/src/DG.Core/Services/ValidationRunsQueryService.cs`, and `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` all use the literal string **`'ValidationGraph'`** (not `'ValidGraph'`), and this value is live on 1169 real nodes (`ValidationRun` x20, `ValidationEntity` x1148, `IntegrationConfig` x1). See "Critical Finding" section below for the two resolution options and a recommendation.

**Primary recommendation:** Treat this phase as a literal, mechanical propagation task using the exact before/after snippets below — but insert a `checkpoint:human-verify` (or explicit planner decision) for the `ValidationGraph`/`ValidGraph` naming conflict before any data-service or C# edits land, since it is not covered by a Phase-13 or Phase-14 locked decision and picking wrong either creates a second silent layer split or triggers an undocumented 1169-node migration.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM prompt schema description (ingest) | API / Backend (n8n workflow) | — | n8n Function nodes build the LLM system prompt server-side; no client involvement |
| LLM prompt schema description (query) | API / Backend (n8n workflow) | — | Same — `Build Cypher Prompt` runs inside n8n |
| Cypher template / schema doc | Database / Storage (schema contract) | API / Backend (consumed by n8n prompts) | `cypher_template.txt` + `dataset_schema.json` are the canonical schema contract, read by humans and mirrored into n8n prompts |
| Graph visualization config | Browser / Client | CDN / Static (served via nginx) | `config.template.js` is injected into the static SPA and drives NeoVis (client-side rendering library) |
| Hardcoded Cypher in `index.html` | Browser / Client | — | Executed client-side via `executeCypher()` against Neo4j's HTTP transaction endpoint |
| ValidationRun/DesignState persistence | API / Backend (data-service) | Database / Storage (Neo4j) | `data-service/app.py` owns all writes/reads to the ValidGraph/ValidationGraph layer |
| Rule read-side (Grasshopper plugin) | API / Backend (C# plugin, desktop-hosted) | Database / Storage | `Neo4jRuleRepository.cs` runs inside the Grasshopper/Rhino process, talks directly to Neo4j via Bolt driver |
| kind-migration script | Database / Storage | — | One-shot Cypher script run via `cypher-shell`, no application-tier involvement |

## Critical Finding: `ValidationGraph` vs `ValidGraph` Layer-Value Conflict

**This must be resolved explicitly before Wave assignment — it is not addressed by any Phase-13 or Phase-14 locked decision.**

**The conflict:**
- `ontology/port-iri-map-V7.md` line 25 documents the ontology layer as renamed `ValidationGraph` -> `Validgraph` (class name), with PDF port label `ValidGraph`.
- Phase-13 CONTEXT.md D-01 states the DesignState node (future Phase 18 write) lives in **`graph='ValidGraph'`** literally.
- But the **already-shipped, already-populated** runtime code uses the literal string **`'ValidationGraph'`**:
  - `data-service/app.py:41` — `VALIDATION_GRAPH = "ValidationGraph"` (used by `store_validation_run`, `get_validation_run`, `list_validation_runs`, `delete_validation_run_metadata`, `get_validation_entity_sets`, `save_integration_config`)
  - `DG/src/DG.Core/Services/ValidationRunsQueryService.cs:15` — `private const string ValidationGraph = "ValidationGraph";`
  - `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` (lines 78, 127, 187, 204, 221) — hardcoded `graph: 'ValidationGraph'` in live E2E Cypher seeding a real `ValidationRun` node

**Live-DB proof this is not just a naming quirk — it is real, populated data** (queried directly against the running dev Neo4j this session):

```
MATCH (n) RETURN labels(n) AS labels, n.graph AS graph, count(*) AS c ORDER BY c DESC
```

| Label | graph value | Count |
|-------|-------------|-------|
| ValidationEntity | ValidationGraph | 1148 |
| ValidationRun | ValidationGraph | 20 |
| IntegrationConfig | ValidationGraph | 1 |
| DesignState | (none — label doesn't exist yet) | 0 |

**Why it matters:** Phase 17's VALIDATION GRAPH component (GHGA-05) is specified to read `Run` + `DesignState` from the **same** ValidGraph handle. If Phase 18's future DesignState-write Cypher uses literal `'ValidGraph'` (per D-01's wording) while all existing/future ValidationRun writes keep using `'ValidationGraph'`, the two node types will live in **different graph partitions** and no query scoped to one literal will ever see the other — a silent, hard-to-diagnose split that only surfaces in Phase 17/18.

**Two resolution options for the planner:**

- **Option A — Keep `'ValidationGraph'` as the runtime literal (recommended).** Do not touch the existing 1169-node partition. Document in `cypher_template.txt`'s v4 GRAPH SCHEMA reference section that the ontology-facing name is `Validgraph`/`ValidGraph` but the physical Neo4j `graph` property value is `'ValidationGraph'` (unchanged) — exactly the same pattern REQUIREMENTS.md's Out-of-Scope table already establishes for `ValidationRun` staying as the DB label while the ontology calls it `Run` ("Ontology<->DB mapping documented instead; migration cost outweighs benefit"). Zero data migration, zero code risk to the 1169 live nodes. Phase 18 (future DesignState writes) should target `graph='ValidationGraph'`, not `'ValidGraph'`, to land in the same partition as Run.
- **Option B — Rename the runtime literal to `'ValidGraph'` everywhere.** Requires: a migration statement (`MATCH (n {graph:'ValidationGraph'}) SET n.graph = 'ValidGraph'`) touching 1169 live nodes, plus edits to `data-service/app.py` (`VALIDATION_GRAPH` constant), `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` (`ValidationGraph` constant), and `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` (5 hardcoded occurrences). This is comparable in shape/cost to the SPEC-01 KnowledgeGraph->SpecGraph rename already scoped as its own dedicated phase (Phase 15) — arguably this should follow the same pattern rather than being folded into Phase 14's mechanical propagation.

**Recommendation: Option A.** It matches the project's own established precedent (documented-not-enforced ontology<->DB naming gap) and keeps Phase 14 a pure propagation phase rather than introducing a new data migration into a phase whose stated goal is "no runtime code changes to DB migrations beyond the kind-migration script already scoped." If the user prefers Option B, it should be raised as a discussion amendment, not silently decided by the planner.

> **RESOLVED 2026-07-03 — user chose Option B (see CONTEXT.md D-14).** The runtime literal is renamed to `'ValidGraph'` everywhere: a data migration of the 1169 live nodes (`SET n.graph='ValidGraph'` with dry-run + dev-guard), plus edits to `data-service/app.py` (`VALIDATION_GRAPH` const), `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` (`ValidationGraph` const), and `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` (5 occurrences). The kind-migration layer-move targets `graph='ValidGraph'`. Node **labels** stay unchanged — only the `graph` property value literal changes. Planner: treat D-14 as locked; do not re-open.

## Artifact-by-Artifact Findings

### Artifact 1: `cypher_template.txt` (SCHM-07)

**Current state (v3.1, 192 lines, read in full):**
- Line 3: `SCHEMA VERSION: v3.1`
- Lines 20-50: `GRAPH SCHEMA (from dataset_schema v3)` block. Line 22-24 documents `Rule` with `text`, `kind`, `title` (optional). Lines 49-50 document `DesignState — key: StateId + project / props: kind (DefState|ObjectState), project, graph='Metagraph'`.
- Lines 106-116 (`CYPHER TEMPLATE BLOCK`, section `// 2` and `// 2b`):
  ```
  // 2. Metagraph — rule node
  MERGE (r:Rule {Rule_Id: '<RULE_ID>'})
  SET r.text = '<SWRL_EXPRESSION>',
      r.kind = 'violation',
      r.project = '<PROJECT>',
      r.graph = 'Metagraph'

  // 2b. Metagraph — design state node (DefState | ObjectState, single label + kind)
  MERGE (ds:DesignState {StateId: '<STATE_ID>', project: '<PROJECT>'})
  SET ds.kind = '<DefState|ObjectState>',
      ds.graph = 'Metagraph'
  ```
  (This is the exact block CONTEXT.md D-03 references as "lines 113-116" — confirmed; the DesignState MERGE spans 114-116, comment starts 113.)

**Target v4 state:**
- Line 3 -> `SCHEMA VERSION: v4.0` (or `v4`, matching the dataset `"version"` field convention already in dataset_schema.json's `metadata.version: "v3.1"`).
- GRAPH SCHEMA reference section: rewrite Rule props to `SWRL` (SWRL string), `RuleName` (optional), `RuleDescription` (optional, new), `kind`, `project`, `graph='Metagraph'`. Add a **document-only** DesignState/Run reference sub-section (per D-03) describing the three kinds, `graph='ValidationGraph'` (per Critical Finding recommendation — or `'ValidGraph'` if Option B is chosen), `Run.ValidStatus`/`Run.SendStatus`, and the Run->DesignState relationship — but explicitly marked as NOT part of the emitted CYPHER TEMPLATE BLOCK.
- CYPHER TEMPLATE BLOCK section `// 2`: `r.text` -> `r.SWRL`. Add optional `r.RuleName`/`r.RuleDescription` SET lines (LLM may populate; template should show the pattern with a comment that it's optional).
- CYPHER TEMPLATE BLOCK section `// 2b`: **DELETE entirely** (per D-03 — DesignState is not LLM-ingest-emitted in v4).
- QUALITY CHECKS section (lines 183-191): update "Atom key is Atom_Id" style checks to mention `SWRL` naming; the line "DatatypeProperty display property is SWRL_label (not label)" stays unchanged (unrelated to Rule renames).

**Gotcha:** The `SEMANTIC MAPPING` and `RULE SEPARATION PRINCIPLE` and `IDENTIFIERS` prose sections (lines 52-79) contain zero references to `text`/`title`/`kind`(DesignState) — they only discuss SWRL/Rule_Id conventions that are unaffected. Do not touch these sections; keep the diff minimal.

### Artifact 2: `training/dataset_schema.json` (SCHM-08)

**Current state (read in full, 188 lines):** JSON Schema-like example document (not a JSON Schema draft, just an annotated example record). Key fields:
- `metagraph.rule_node.props`: `text`, `kind`, `title` (optional), `project`, `graph`.
- `metagraph.nodes[]` array includes a `DesignState` entry (lines 108-119) with `key.StateId` format `"DS_<hash> | OS_<hash>"` and `props.kind: "DefState | ObjectState"`.
- `metadata.version: "v3.1"`.

**Target v4 state:** Mirror `cypher_template.txt` exactly (SCHM-08's literal requirement):
- `rule_node.props` -> `SWRL`, `RuleName` (optional), `RuleDescription` (optional, new), `kind`, `project`, `graph`.
- Remove the `DesignState` entry from `metagraph.nodes[]` (or move it to a new document-only `metagraph.schema_reference` block outside the emission-relevant `nodes`/`atoms`/`connections` arrays, matching D-03's "document-only" treatment) — whichever the planner picks for `cypher_template.txt`'s structure should be mirrored 1:1 here since this file's whole purpose is exact parity.
- `metadata.version` -> `"v4.0"` (or `"v4"`).

**Gotcha:** This file's `id`, `layer`, `task`, `rule_kind`, `domain`, `input_nl`, `output_formal` top-level fields (lines 1-22) are dataset-record scaffolding unrelated to schema propagation — do not touch them; only `metagraph` and `metadata.version` are in scope.

### Artifact 3: `n8n/workflows/rules-to-metagraph.json` (SCHM-09)

**Confirmed canonical file** (see Open Question 1 resolution above). 523 lines, 17 nodes. Read in full via the n8n node-by-node dump.

**Four nodes need edits (CONTEXT.md named 3; this research found a 4th):**

1. **`Build LLM Prompt`** (Function node, `functionCode`, ~line 78 in the workflow JSON's `nodes[]` array). Exact target strings inside the embedded prompt-building JS:
   - `'SCHEMA CONSTRAINTS (v3):'` -> `(v4)`
   - `'- Allowed node labels: Class, DatatypeProperty, ObjectProperty, Builtin, Rule, Atom, Var, Literal, DesignState.'` -> **remove `DesignState`** from the allowed-labels list (per D-03, ingest no longer emits it): `'- Allowed node labels: Class, DatatypeProperty, ObjectProperty, Builtin, Rule, Atom, Var, Literal.'`
   - `'- DesignState key: StateId + project. Props: kind (DefState|ObjectState).'` -> **delete this bullet entirely**
   - The few-shot example embedded in the same node (`fewShot` variable, mirrors `updated_cypher_reference_examples_v3.cypher` Example 1 verbatim) contains `SET r.text = '...'` -> must become `SET r.SWRL = '...'` to match the new template
   - The `existingRules.push({ rule_id: d.row[0], text: d.row[1], kind: d.row[2] })` line reads columns from the `Fetch Existing Entities` HTTP node's response (see below) — the local variable name `text` can stay as a JS identifier, but must be populated from whichever column the updated query returns (`swrl`/`SWRL` alias)
   - `entityLines.push('  - ' + r.rule_id + ' (' + r.kind + '): ' + r.text);` — uses the same local var, no change needed once the upstream query is fixed
   - Edit-mode ruleDetails builder: `const ruleDetails = matched.map(r => r.rule_id + ': ' + r.text).join('; ');` — same, no change needed once upstream fixed

2. **`Fetch Existing Entities`** (HTTP Request node, NOT named in CONTEXT.md's 3 but is the upstream data source for `Build LLM Prompt`'s existing-rules list). Its `bodyParametersJson` contains a raw Cypher statement:
   ```
   MATCH (r:Rule) WHERE r.graph = 'Metagraph' RETURN r.Rule_Id AS rule_id, coalesce(r.text, '') AS text, coalesce(r.kind, '') AS kind ORDER BY r.Rule_Id
   ```
   Target v4: `coalesce(r.SWRL, r.text, '') AS text` (backward-compat coalesce, same pattern as D-06's C# fix — matters live, since the current DB's 5 real Rule nodes all only have `.text`, zero have `.SWRL`).

3. **`Prepare Graph Payload`** (Function node). Contains the `postProcess` fallback-tagging statements (auto-SET `graph`/`project` on any untagged node the LLM forgot) and edit-mode cleanup statements. No `text`/`title`/`kind`(DesignState)-specific hardcoding was found in this node — it operates generically on label sets (`n:Class OR n:DatatypeProperty OR n:ObjectProperty`, `n:Rule OR n:Atom OR n:Builtin OR n:Var OR n:Literal`). **No edit required here for property renames**, but confirm the `n:Var OR n:Literal` orphan-cleanup line still matches v4's structure (it does — Var/Literal handling is unchanged).

4. **`Annotate Graph Props`** (HTTP Request node — **found during this research, not listed in CONTEXT.md's canonical_refs**). Its `bodyParametersJson` runs a second statement after `postProcess`:
   ```
   MATCH (r:Rule) WHERE r.graph = 'Metagraph' AND (r.description IS NULL OR r.description = '') SET r.description = $description
   ```
   This auto-backfills a lowercase `r.description` fallback from the raw NL rules_text whenever the LLM didn't supply one. Under v4 (D-07: `RuleDescription` is new/optional with the same "LLM may omit" semantics), this is the natural place to backfill `RuleDescription` too: `SET r.RuleDescription = $description WHERE r.RuleDescription IS NULL OR r.RuleDescription = ''`. **Add this node to the SCHM-09 task list** — it was omitted from CONTEXT.md's canonical_refs and would otherwise leave a silent gap where new rules never get a `RuleDescription` fallback.

5. **`Parse LLM Output`** (Function node) — CONTEXT.md's 3rd named node. Read in full; this node only does generic MERGE-statement text cleanup (bracket-nesting validation, quote-balance checks, dedup) via regex over whatever Cypher text the LLM emitted. **Zero hardcoded schema property names found** — it is schema-agnostic by design (operates on `MERGE\s*\(...\)` patterns generically). No edit required for SCHM-09's property-rename requirement, but this is the node responsible for enforcing "no malformed MERGE" — after the template changes, verify its degenerate-pattern blocklist (`MERME|MERX|MER:|...`) doesn't accidentally also need a `DesignState`-specific guard now that D-03 says the LLM should never emit it (optional hardening, not required for SC#2).

### Artifact 4: `n8n/workflows/graph-query-mcp.json` (SCHM-10)

**Confirmed canonical file.** 475 lines. The `Build Cypher Prompt` node (Function node) contains the embedded schema description. Exact target lines (full text captured this session):

- `'Data model (v3 schema):'` -> `(v4 schema)`
- `"- Rules: (:Rule {graph:'Metagraph'}) with properties Rule_Id, text (SWRL expression), kind (violation|compliance), title, project."` -> `"- Rules: (:Rule {graph:'Metagraph'}) with properties Rule_Id, SWRL (SWRL expression), kind (violation|compliance), RuleName, RuleDescription, project."`
- `"- Numeric constraints are stored in Rule.text as SWRL (e.g. swrlb:greaterThan(?h,75))."` -> `"- Numeric constraints are stored in Rule.SWRL as SWRL (e.g. swrlb:greaterThan(?h,75))."`
- `'Key property names (v3):'` -> `(v4)`
- `'- Rule key: Rule_Id (NOT id).'` — unchanged
- Add: `'- Rule display: coalesce(r.SWRL, r.text) for the SWRL body; coalesce(r.RuleName, r.title) for the display name — some existing rules predate the rename.'` (backward-compat guidance so generated read queries don't silently miss the 5 live v3-shaped Rule nodes)
- `'- Use toLower(r.text) CONTAINS <keyword> for matching.'` -> `'- Use toLower(coalesce(r.SWRL, r.text, '')) CONTAINS <keyword> for matching.'`
- `'- For list-all rules, return r.Rule_Id, r.text, r.kind.'` -> `'- For list-all rules, return r.Rule_Id, coalesce(r.SWRL, r.text, '') AS swrl, r.kind.'`
- Both `Example (with project)` and `Example (no project)` lines use `r.text`/`toLower(r.text)` — update both to the coalesce pattern above.

**Gotcha:** The `schema` object populated from `$json?.result?.data` (labels/relationship_types/property_keys/graphs/projects) comes from a **live `db.schema()`-style introspection query upstream** (not hardcoded) — this part auto-adapts and needs no manual edit. Only the hand-written prose/example strings above need changes.

### Artifact 5: `graph-viewer/config.template.js` (SCHM-11, D-11/D-12)

**Current state (61 lines, read in full):**
- `labels` block (lines 17-32): both `DatatypeProperty: { label: "SWRL_label" }` (line 21) and `DataProperty: { label: "SWRL_label" }` (line 22) present — the duplicate D-11 flags.
- `labels.DesignState: { label: "StateId", group: "kind" }` (line 27) — no change needed here (group-by-kind mechanism already supports 3 kinds without edit).
- `visGroups` block (lines 42-59): `DatatypeProperty` (line 44) and `DataProperty` (line 45) both present with identical color `#ffb36b`/`#e5923a` — the duplicate.
- `visGroups.DefState: { color: { background: "#a8d8ea", border: "#6fb3cf" } }` (line 53), `visGroups.ObjectState: { color: { background: "#f4a261", border: "#d4823a" } }` (line 54).
- Comment on line 52 already documents the kind-keyed mechanism correctly — reuse/update this comment, don't remove it.

**Target v4 state:**
- `labels`: delete the `DataProperty:` line (line 22). Keep `DatatypeProperty:` (line 21) — per D-11, DB keeps the `DatatypeProperty` label, no `DataProperty`-labeled nodes exist.
- `visGroups`: delete the `DataProperty:` entry (line 45). Rename `DefState` -> `ParamState` (keep color `#a8d8ea`/`#6fb3cf`), rename `ObjectState` -> `ObjState` (keep color `#f4a261`/`#d4823a`), **add** `PropState: { color: { background: "#7bcfc0", border: "#4fa696" } }` (new mint-teal, distinct from Class green `#78c38a` and from `KnowledgeNote` teal `#4ecdc4` — see Claude's Discretion recommendation below).
- Update the explanatory comment on line 52 to reference the new kind trio (`ParamState`/`ObjState`/`PropState`) instead of `DefState`/`ObjectState`.

**Claude's Discretion recommendation (D-12 color):** `PropState: { color: { background: "#7bcfc0", border: "#4fa696" } }` — a mint/teal hue that sits visually between Class's yellow-green (`#78c38a`) and KnowledgeNote's blue-teal (`#4ecdc4`) without exact collision on either. Verify visually after the config change (quick manual check in the NeoVis viewer) since exact hex harmony is subjective.

**Gotcha:** This file is a **template** — `entrypoint.sh` does sed-based injection of env vars into it at container start (per CLAUDE.md: "NeoVis config (env vars injected at runtime)"). The `labels`/`visGroups`/`relationships` structure is NOT env-templated (only the connection strings at the top are `${VAR}`-style) — confirmed by reading the file: `neo4jUri`, `neo4jPassword`, etc. are already literal values in this "template" (the runtime values appear to be baked in directly rather than actually templated with `${}` placeholders) — worth flagging to the planner that `entrypoint.sh` should be checked to confirm whether `labels`/`visGroups` edits survive the sed injection step, though they are almost certainly untouched by it since sed only targets the connection-string keys.

### Artifact 6: `graph-viewer/index.html` (SCHM-11, D-13)

**Current state:** Single-file React SPA, several thousand lines. Hardcoded Cypher located via grep (exact line numbers):
- Line 1448: `buildCypher("MetaGraph")` view builder — `"MATCH (r:Rule {graph:'Metagraph'" + pf + "}) " + ...` — this query itself doesn't reference `r.text`/`r.title` (it just matches the Rule node and its Atom/Var/Literal subgraph for NeoVis rendering), **no change needed** here.
- Line 1576: `executeCypher("MATCH (r:Rule) WHERE r.graph = 'Metagraph'" + ... + " RETURN r.Rule_Id AS rule_id, coalesce(r.text, '') AS text, coalesce(r.kind, '') AS kind ORDER BY r.Rule_Id")` — **this is the D-13 target**. Update to `coalesce(r.SWRL, r.text, '') AS text` (same backward-compat coalesce pattern used everywhere else in this phase).

**Gotcha:** No other `DefState`/`ObjectState`/`.title` string literals were found via full-file grep in `index.html`. The `buildCypher("KnowledgeGraph")` and default (`OntoGraph`) branches (lines 1439-1466) are untouched by this phase (KnowledgeGraph is Phase 15 scope; OntoGraph Class/property Cypher has no Rule-prop or kind references).

### Artifact 7: `data-service/app.py` (SCHM-12)

**Confirmed: zero `:Rule` label queries exist anywhere in this file** (full-file grep for `:Rule\b|Rule_Id|Rule {` returned no matches) — CONTEXT.md's note that app.py does not read `r.text`/`r.title`/Rule status props is **fully confirmed**, no blast radius there.

**What DOES need v4 alignment (SCHM-12's actual scope):**
- `VALIDATION_GRAPH = "ValidationGraph"` constant (line 41) — see Critical Finding section above; recommend **no change** (Option A).
- `store_validation_run()` (lines 396-439): `MERGE (run:ValidationRun {...}) SET ... run.status = 'completed', ...` (line 420) — this is a **job-completion status** ("completed" vs presumably future "failed"/"running" states used elsewhere, e.g. `WORKFLOW_STATUS` dict), semantically distinct from the removed `Run.Status` pass/fail text field (D-01/D-02). **Do not conflate these** — `run.status='completed'` should stay; it tracks publish-job lifecycle, not validation pass/fail. Add new properties here: `run.ValidStatus` (Boolean list, from `ruleResults`/`entities` pass/fail data already passed into this function via `rules_summary`/`entities` params) and `run.SendStatus` (Boolean, true on successful publish).
- `get_validation_run()` (lines 491-510) and `list_validation_runs()` (lines 548-590): `RETURN` clauses need `run.ValidStatus AS validStatus, run.SendStatus AS sendStatus` added so the read side surfaces the new fields (needed by GHVL-06/Model Viewer work in later phases, but adding the columns now costs nothing and keeps the propagation complete).
- `ValidationPublishEntityPayload.overallStatus: str = "unknown"` (Pydantic model, line 156) is a **request payload field** from the Grasshopper plugin, unrelated to the graph schema — no change needed.
- Comment block at lines 161-164 and 526-529 reference "DefState"/"ObjectState" vocabulary in prose comments only (not executable code) — update these comments to the v4 kind names for documentation accuracy, but they carry zero runtime risk if missed.

**Gotcha:** `store_validation_run`'s `entities` parameter already carries per-entity `failedRuleIds`/`passedRuleIds` (lines 441-463) which is exactly the shape needed to compute a per-ObjState `ValidStatus` Boolean list — but wiring that computation correctly (matching entity order to ObjState order) is Phase 18 (VALIDATOR rework) territory per the requirements traceability table, not Phase 14. **Phase 14's job is schema alignment (add the properties, document the contract) — not full behavioral wiring.** Recommend the plan add `run.ValidStatus`/`run.SendStatus` as settable properties with a sensible default (e.g., `SendStatus` defaults `true` on successful publish call, matching current behavior; `ValidStatus` can default to an empty list or be derived from the existing failed/passed data as a best-effort placeholder) and flag in the SUMMARY that full per-ObjState-index-matched population is Phase 18 work.

### Artifact 8: `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` (D-06)

**Current state confirmed exact-line-accurate against CONTEXT.md's estimate:**
```csharp
// line 27:
coalesce(r.title, r.name, r.Rule_Id) AS name,
// line 31:
coalesce(r.swrl, r.text, '') AS swrl,
```
(Full `RulesQuery` spans lines 23-35; both target lines confirmed present exactly as CONTEXT.md described, off by zero from the "~27"/"~31" estimate.)

**Target v4 state:**
```csharp
coalesce(r.RuleName, r.title, r.name, r.Rule_Id) AS name,
coalesce(r.SWRL, r.swrl, r.text, '') AS swrl,
```

**Gotcha — description property also worth checking:** line 28 already reads `coalesce(r.description, '') AS description` (lowercase). Per Artifact 3 finding #4 above (the `Annotate Graph Props` node), a lowercase `r.description` fallback already exists and a new `RuleDescription` fallback is being added in n8n. **Recommend extending this coalesce too** (not explicitly in D-06's two-line list, but consistent with the same backward-compat pattern and directly enabled by the n8n change): `coalesce(r.RuleDescription, r.description, '') AS description`. Flag this as an additive, low-risk 3rd line for the planner to include alongside D-06's two mandated lines — it completes the same backward-compat contract D-06 establishes and costs one line.

**Test impact:** `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs` was read in full — it only exercises `Neo4jRuleRepository.PopulateVariablesForTesting()` (a pure in-memory helper), never the `RulesQuery`/`AtomsQuery` constant strings against a live DB. **Zero test changes required** for the coalesce-line edit.

### Artifact 9: `migrations/2026-06-23_var_project_merge_key.cypher` (pattern reference for SCHM-13)

Read in full (65 lines). Established pattern to follow for the new kind-migration script:
- Header comment block: PURPOSE / EXECUTION METHOD / WARNING-SCOPE-LIMITATION sections.
- `EXECUTION METHOD` documents the exact invocation: `cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f migrations/<file>.cypher` or manual paste into Neo4j Browser — **not invoked automatically by any application code**.
- Main statement is `idempotent` via `coalesce()` (safe to re-run).
- A separate `AUDIT QUERY` block (commented out, read-only, documentation only — "not auto-executed") for manual pre-migration inspection.
- A `VERIFICATION QUERY` block at the end for post-migration confirmation.

**The new kind-migration script should follow this exact 4-part shape** (dry-run/audit query, main migration statement(s), orphan-deletion statement with its own guard comment, verification query) — plus D-10's additional requirement of an explicit dry-run COUNT that prints before executing the destructive DELETE, and a "dev databases only" guard note (this migration is more destructive than the Var-merge-key one, which only ever adds a missing property — it deletes nodes).

**Naming convention:** `YYYY-MM-DD_description.cypher`, e.g. `migrations/2026-07-03_designstate_kind_and_layer_migration.cypher` (today's date; adjust to actual execution date).

### Artifact 10: `training/updated_cypher_reference_examples_v3.cypher` (SCHM-14)

Read in full (80+ lines, one worked example: `R_URB_HEIGHT_MAX_75_V`). Structurally identical to `cypher_template.txt`'s CYPHER TEMPLATE BLOCK but with concrete values substituted (no `<PLACEHOLDER>` tokens). Uses `r.text`, `r.kind` — no `title`, no `DesignState` block in this particular example (the example predates or simply doesn't exercise the DesignState MERGE).

**Target v4 successor:** Per Claude's Discretion (CONTEXT.md), create a new file `training/updated_cypher_reference_examples_v4.cypher` (new file, v3 stays for greppable history) with the same worked example rewritten: `r.text` -> `r.SWRL`, and optionally add a second worked example showing `RuleName`/`RuleDescription` population (since the v3 file's single example never demonstrates the optional-title case either — worth adding one new example that exercises the full v4 property set, per SCHM-14's "no runtime or LLM few-shot artifact still teaches the old schema").

**Check for consumers:** grep across the repo found no `.py`/`.js`/`.cs` file that loads `updated_cypher_reference_examples_v3.cypher` programmatically — like the `test/` fixtures, this is a **human/LLM-prompt-authoring reference document**, not a wired-in test fixture or training pipeline input (confirmed by inspecting `training/train_lora.py`'s imports is out of this phase's scope, but the filename convention and its sibling `training_dataset.json` strongly suggest this file is copy-pasted into `Build LLM Prompt`'s few-shot section by hand during n8n workflow authoring, matching exactly what Artifact 3 finding #1 already located).

### Artifact 11: `test/` fixtures (SCHM-14)

Full audit of the fixture set CONTEXT.md named, plus a completeness check:

| File | Contains v3 state kinds (DefState/ObjectState)? | Contains v3 Rule props (text/title)? | Loaded by any automated test? |
|------|---|---|---|
| `test/records.json`, `records2.json`, `records3.json`, `records4.json` | No | **Yes** — raw Neo4j export dumps containing `"text": "..."` SWRL-string properties on Rule nodes | Only `test/test_cleanup.js` loads `neo4j_res3.json` (not `records*.json`) — see below |
| `test/neo4j_res.json`..`neo4j_res4.json` | No | Not directly checked for `text`/`title` field content (these are raw query-result dumps, structurally similar to `records*.json`) | `test/test_cleanup.js` loads `neo4j_res3.json` only |
| `test/training_dataset.json` | No | No — uses a **different, older ad hoc convention** (`r.description` for the SWRL text, not `r.text`/`r.SWRL`) and top-level `"dataset_version": "v3"` | Not found to be loaded by any `.py`/`.js` test |
| `test/CaseStudy_LivingUnit/records_LU1/2/3.json` | No | `records_LU2.json`/`records_LU3.json` contain `text`/`title`-shaped fields (1 and 3 hits respectively) | Not found to be loaded by any test |

**Key finding: none of these fixtures reference `DefState`/`ObjectState` kind values at all** — SCHM-14's literal wording ("test/ fixtures referencing v3 state kinds") turns up **zero hits**. What they DO reference is the old `Rule.text` property naming, which is a different (but related) v3-ism. **`test/test_cleanup.js`** is the only fixture consumer found, and it is a **manual debugging script** (hardcoded absolute Windows path `c:/Users/Admin/source/repos/design-grammar-system/...`, not wired into any test runner/CI) that generically parses `MERGE` statement text via regex — it does not assert on property names, so it is unaffected by the Rule-property rename regardless of what's in `neo4j_res3.json`.

**Recommendation:** SCHM-14's test-fixture work here is **documentation/reference-hygiene, not functional risk-mitigation** — no automated test will break. The plan should: (a) confirm this finding (no automated test consumes these files) so the task isn't over-scoped, and (b) either regenerate 1-2 representative fixture files against the new schema (for future manual-debugging usefulness) or add a short header comment to the stale ones noting they capture the pre-v4 schema and are retained for historical/debugging reference only — whichever is lower-effort. Given zero functional risk, this should be a small task, not a full fixture-by-fixture rewrite.

## Package Legitimacy Audit

**Not applicable — this phase installs no new packages.** All work is editing existing files (Cypher templates, JSON prompt configs, JS config, Python Cypher strings, one C# file, one new `.cypher` migration file). No `npm install`/`pip install`/`cargo add` commands are needed anywhere in this phase's scope.

## Architecture Patterns

### System Architecture Diagram (schema-propagation data flow)

```
                    ┌─────────────────────────┐
                    │  cypher_template.txt    │  <- canonical schema contract (human-authored)
                    │  training/dataset_      │     (mirrored 1:1, SCHM-08)
                    │  schema.json            │
                    └─────────┬────────────────┘
                              │ (manually mirrored into embedded prompt strings)
                 ┌────────────┴─────────────┐
                 v                            v
   ┌───────────────────────────┐   ┌───────────────────────────┐
   │ n8n: rules-to-metagraph   │   │ n8n: graph-query-mcp      │
   │  Build LLM Prompt         │   │  Build Cypher Prompt      │
   │  Fetch Existing Entities  │   │  (schema prose + few-shot)│
   │  Annotate Graph Props     │   └──────────┬────────────────┘
   └──────────┬─────────────────┘              │
              │ POST /db/neo4j/tx/commit         │ POST /db/neo4j/tx/commit
              v                                  v
        ┌─────────────────────────────────────────────┐
        │              Neo4j 5 (single DB)             │
        │  OntoGraph | Metagraph | ValidationGraph |   │
        │  KnowledgeGraph  (layer-tagged via `graph=`) │
        └───────┬───────────────────┬─────────────────┘
                │ read (Bolt)        │ read (HTTP tx/commit)
                v                    v
   ┌─────────────────────┐   ┌────────────────────────────┐
   │ DG.Core (C# plugin) │   │ graph-viewer/index.html    │
   │ Neo4jRuleRepository │   │ (NeoVis via config.template│
   │ coalesce(new, old)  │   │  .js) + hardcoded Cypher   │
   └─────────────────────┘   └────────────────────────────┘
                │
                v (publish path, separate from ingest)
        ┌─────────────────────────────┐
        │ data-service/app.py         │
        │ store_validation_run() etc. │  <- ValidStatus/SendStatus added here (SCHM-12)
        └─────────────────────────────┘
```

A reader can trace the primary flow: schema contract (top) is hand-copied into two n8n prompt-builder nodes -> LLM generates Cypher matching that contract -> Cypher is committed to Neo4j via HTTP -> two independent read paths (C# plugin via Bolt, browser SPA via HTTP) both use `coalesce()`-based backward-compat reads to survive the v3->v4 transition -> a separate publish path (data-service) writes validation results into the same DB under a still-undecided-in-this-research graph-partition literal (see Critical Finding).

### Recommended Project Structure
No new files/folders beyond:
```
migrations/
└── YYYY-MM-DD_designstate_kind_and_layer_migration.cypher   # new, follows existing pattern

training/
└── updated_cypher_reference_examples_v4.cypher               # new, v3 file kept alongside
```

### Pattern: Coalesce-based backward-compatible reads
**What:** Every read query touching a renamed property uses `coalesce(newProp, oldProp, ...fallbacks..., defaultValue)` rather than assuming the new property exists.
**When to use:** Any read path (C# repository, n8n prompt-builder queries, `index.html` hardcoded Cypher, future data-service reads) touching `Rule.SWRL`/`RuleName`/`RuleDescription` while old v3-shaped nodes (confirmed: all 5 live Rule nodes) still exist.
**Example (already-established pattern in this codebase, from `Neo4jRuleRepository.cs`):**
```cypher
-- Source: DG/src/DG.Core/Data/Neo4jRuleRepository.cs (existing pattern this phase extends)
RETURN coalesce(r.RuleName, r.title, r.name, r.Rule_Id) AS name,
       coalesce(r.SWRL, r.swrl, r.text, '') AS swrl
```

### Pattern: Dry-run-then-execute destructive migration
**What:** A migration script that deletes data (D-10's orphan-DesignState deletion) must print a dry-run count before executing, and be scoped with an explicit dev-only guard comment.
**When to use:** The new kind-migration script (SCHM-13).
**Example (structure to follow, adapted from `migrations/2026-06-23_var_project_merge_key.cypher`):**
```cypher
// --- Step 0: DRY-RUN — count orphan DesignStates that WILL be deleted ------
// Run this first and review the count before running Step 2.
MATCH (ds:DesignState) WHERE NOT (ds)<-[]-(:Run)
RETURN count(ds) AS orphansToDelete;

// --- Step 1: Rename kind values + move layer -------------------------------
MATCH (ds:DesignState) WHERE ds.kind = 'DefState'
SET ds.kind = 'ParamState', ds.graph = 'ValidationGraph';   // or 'ValidGraph' per Critical Finding resolution
MATCH (ds:DesignState) WHERE ds.kind = 'ObjectState'
SET ds.kind = 'ObjState', ds.graph = 'ValidationGraph';

// --- Step 2: DELETE orphans (destructive — dev databases only) -------------
MATCH (ds:DesignState) WHERE NOT (ds)<-[]-(:Run)
DETACH DELETE ds;

// --- Verification ------------------------------------------------------------
// MATCH (ds:DesignState) WHERE ds.kind IN ['DefState','ObjectState'] RETURN count(ds) -- expect 0
```

### Anti-Patterns to Avoid
- **Renaming a live-populated graph-partition literal as a side-effect of an unrelated propagation task:** the `ValidationGraph`/`ValidGraph` conflict must be a deliberate, scoped decision (see Critical Finding), not an incidental find-and-replace during Rule-property renaming.
- **Assuming n8n picks up edited JSON files automatically:** it does not (see Validation Architecture below) — editing `rules-to-metagraph.json` on disk has zero effect on the running workflow until re-imported.
- **Conflating `ValidationRun.status` (job-completion lifecycle string) with the removed `Run.Status` (pass/fail text enum, per D-01/D-02):** these are different fields with different owners; do not delete or repurpose `run.status='completed'`.

## Don't Hand-Roll

Not directly applicable — no complex algorithmic problems in this phase (bracket-nesting validation, coalesce reads, and dry-run-guarded migrations are all *already* the codebase's own established, hand-rolled-but-proven patterns; this phase extends them rather than introducing anything new). **Key insight:** resist the urge to introduce a schema-migration framework (e.g., Neo4j's APOC migrations, Liquigraph) for a single one-shot script — the existing plain-`.cypher`-file-plus-`cypher-shell` pattern is intentional and proportionate to this project's scale (one migration file exists total, run manually, once).

## Runtime State Inventory

**Trigger confirmed: this phase renames property names (`text`->`SWRL`, `title`->`RuleName`) and enum-like values (`DefState`->`ParamState`, `ObjectState`->`ObjState`) across code AND live data.**

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **Neo4j `Rule` nodes: 5 live nodes, all v3-shaped (`.text` present, `.title`/`.SWRL`/`.swrl` absent on all 5).** Queried live: `MATCH (r:Rule) RETURN count(r) AS total, count(r.text) AS hasText, count(r.SWRL) AS hasSWRL` -> `{total:5, hasText:5, hasSWRL:0}`. | Code edit only (coalesce reads) — no data migration needed/possible without breaking the "readers keep coalesce" design (D-06 explicitly chose NOT to migrate existing Rule nodes; new ingests get the new shape, old nodes stay readable via coalesce). |
| Stored data | **Neo4j `DesignState` nodes: ZERO exist** (label not registered in DB — confirmed via live query, `UnknownLabelWarning` returned). | Data migration (SCHM-13 kind-migration script) has nothing to act on as-is — **plan must add a seeding sub-step** (insert a handful of `DefState`/`ObjectState`-kind, `graph='Metagraph'`-tagged DesignState nodes, with a mix of Run-linked and orphaned ones) before the migration script's dry-run/execute/verify cycle can meaningfully demonstrate SC#5. |
| Stored data | **Neo4j `ValidationRun`: 20 nodes, `ValidationEntity`: 1148 nodes, `IntegrationConfig`: 1 node — all `graph='ValidationGraph'`.** | No migration needed if Critical Finding Option A (keep `'ValidationGraph'` literal) is chosen. Full-partition migration (1169 nodes) required only if Option B is chosen — flag as a go/no-go decision, not a default action. |
| Live service config | **n8n workflows are NOT auto-loaded from `n8n/workflows/*.json` at container start** — the `./n8n:/files` volume mount makes files available inside the container filesystem only; the actual running workflow definitions live in n8n's own SQLite DB (`n8n_data` named volume). Editing the JSON files on disk has **zero runtime effect** until manually re-imported. | Manual re-import required after every edit: `docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json` (and the graph-query-mcp.json equivalent) — **documented gotcha**: n8n's `import:workflow` command requires a top-level `"id"` field in the JSON or it fails with `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id` (per `DG_OBSIDIAN/sessions/2026-06-23 New PC Docker setup and n8n workflow fix.md`). The canonical files as committed do NOT have this top-level `id` (confirmed: only per-node `"id": "1"` etc. exist). The documented workaround: inject an `id` into a scratch copy before import, `docker cp` it in, then `n8n update:workflow --active=true`, then `docker restart n8n`. This must be a named step in the plan's live-validation task (SC#2), not assumed to "just work" via editing the repo file. |
| OS-registered state | None found — no Windows Task Scheduler, pm2, launchd, or systemd artifacts reference this schema's property/kind names (this project has no such OS-level registrations at all, per prior phase research/CLAUDE.md). | None. |
| Secrets/env vars | None affected — no secret or env-var NAME references `text`/`title`/`DefState`/`ObjectState`/`SWRL`/etc. (grepped `docker-compose.yml` and `config.template.js`; only unrelated credential vars like `NEO4J_PASSWORD`, `SPECKLE_WRITE_TOKEN` exist). | None. |
| Build artifacts | None found — no compiled/packaged artifact embeds these string literals at build time (the C# plugin's coalesce strings are compiled into `DG.Core.dll`/`DG.Grasshopper.dll` but that's the normal edit-recompile cycle covered by the D-06 code-edit task itself, not a stale-artifact problem). | Recompile `DG.Core`/tests after the `Neo4jRuleRepository.cs` edit (standard `dotnet build`), no special reinstall step. |

## Common Pitfalls

### Pitfall 1: Editing n8n workflow JSON files without re-importing
**What goes wrong:** The plan edits `rules-to-metagraph.json`/`graph-query-mcp.json` on disk, commits the change, and assumes SC#2's live-ingest test will exercise the new prompt — but the running n8n instance still executes the old, pre-edit workflow definition from its SQLite DB.
**Why it happens:** The `./n8n:/files` Docker volume mount is a one-way filesystem bridge for manual import tooling, not a live-reload mechanism. This is easy to miss because it "looks like" bind-mount hot-reload setups common in other stacks.
**How to avoid:** The plan's live-ingest validation task (SC#2) must explicitly include the `docker exec -it n8n n8n import:workflow --input=/files/workflows/<file>.json` step (with the documented `id`-field workaround) before testing, every time either workflow file changes.
**Warning signs:** A live test "passes" but the response/generated Cypher still shows v3-schema artifacts (e.g., `r.text` instead of `r.SWRL`) — that's the tell that the old workflow definition is still active.

### Pitfall 2: Coalesce-ordering mistakes silently masking the rename
**What goes wrong:** Writing `coalesce(r.text, r.SWRL, '')` (old-before-new) instead of `coalesce(r.SWRL, r.text, '')` (new-before-old) — for nodes that somehow have both properties set (e.g., during a transitional edit-in-place), the wrong-order coalesce would silently prefer stale data.
**Why it happens:** Easy to transpose when copy-pasting across the ~6 places this pattern needs to appear (C# repository x2, `Fetch Existing Entities` Cypher, `graph-query-mcp.json` prompt guidance x2-3, `index.html` line 1576).
**How to avoid:** Standardize on "new property always listed first" and grep-verify after editing: `grep -n "coalesce(r\." <every touched file>` and manually eyeball the argument order in each hit.
**Warning signs:** A newly-ingested v4 rule (with both `.SWRL` populated and, hypothetically, a leftover `.text` from a re-ingest-over-old-node scenario) displays stale SWRL text in the UI/query results.

### Pitfall 3: Ollama cold-start timing during live-ingest validation
**What goes wrong:** The live-ingest test (SC#2) times out or appears to hang on the first request after the stack has been idle.
**Why it happens:** Documented in `DG_OBSIDIAN/sessions/2026-06-23...md`: Ollama's cold start (after `OLLAMA_KEEP_ALIVE` idle timeout) takes 40-70s due to GPU discovery on some NVIDIA driver/CUDA combinations — not an error, just latency. Confirmed live this session: `ollama --version` returned promptly (`0.15.2`), but that doesn't test generation latency.
**How to avoid:** The plan's validation task should either warm Ollama first (`docker exec ollama ollama run llama3.1 "test" ` or similar) or simply set an appropriately long timeout/retry expectation in the verification step, not treat >10s as a failure signal.
**Warning signs:** n8n workflow execution stuck at "Ollama Generate" step for >60s on the very first call after a stack restart — expected, not a regression.

### Pitfall 4: Treating `run.status` and the removed `Run.Status` as the same field
**What goes wrong:** A well-meaning edit deletes or repurposes `data-service/app.py`'s `run.status = 'completed'` line while implementing D-01/D-02 ("no Status text field"), breaking the publish-job-completion tracking that `run.status` actually serves.
**Why it happens:** Name collision between two conceptually different fields — the ontology's removed `Run.Status` (pass/fail enum, superseded by `ValidStatus`) and data-service's pre-existing, unrelated `ValidationRun.status` (job lifecycle: presumably `pending`/`running`/`completed`/`failed`, though only `'completed'` is currently ever SET in the codebase).
**How to avoid:** Keep `run.status` untouched; add `ValidStatus`/`SendStatus` as new, additional properties alongside it.
**Warning signs:** Any diff that removes or renames the `run.status = 'completed'` line — should trigger a second look before merging.

### Pitfall 5: Assuming `DesignState` kind-migration has real data to migrate
**What goes wrong:** The plan writes and "successfully" runs the kind-migration script against the dev DB, gets a trivial `0 nodes affected` result, and reports SC#5 satisfied without ever having exercised the rename/layer-move/orphan-delete logic paths.
**Why it happens:** The live dev DB genuinely has zero `DesignState` nodes right now (confirmed this session) — a script that runs cleanly against empty data proves syntactic correctness but not behavioral correctness.
**How to avoid:** Add an explicit seeding sub-step (a handful of `MERGE (:DesignState {...})` statements creating a realistic mix: some `DefState`-kind + `graph='Metagraph'` + linked to a fake `Run` node, some `ObjectState`-kind similarly linked, and at least one **orphaned** DesignState with no Run link) before running the dry-run/migrate/verify cycle, so before/after counts are meaningfully non-trivial.
**Warning signs:** SUMMARY.md reporting "0 nodes migrated, 0 orphans deleted" as evidence of success — that's a red flag, not proof.

## Code Examples

### Before/after: Rule node write (`cypher_template.txt` CYPHER TEMPLATE BLOCK section `// 2`)
```cypher
-- v3 (current, cypher_template.txt lines 106-111)
MERGE (r:Rule {Rule_Id: '<RULE_ID>'})
SET r.text = '<SWRL_EXPRESSION>',
    r.kind = 'violation',
    r.project = '<PROJECT>',
    r.graph = 'Metagraph'
```
```cypher
-- v4 target
MERGE (r:Rule {Rule_Id: '<RULE_ID>'})
SET r.SWRL = '<SWRL_EXPRESSION>',
    r.kind = 'violation',
    r.project = '<PROJECT>',
    r.graph = 'Metagraph'
    // r.RuleName and r.RuleDescription are optional — LLM sets them when the
    // NL rule text supplies a name/description; omit the SET clause otherwise.
```

### Before/after: read-side coalesce (repeat this exact transform in all ~6 locations enumerated above)
```cypher
-- Before
coalesce(r.text, '') AS swrl
-- After
coalesce(r.SWRL, r.text, '') AS swrl
```

## State of the Art

| Old Approach (v3) | Current Approach (v4, this phase) | When Changed | Impact |
|--------------------|-------------------------------------|---------------|--------|
| `Rule.text`, `Rule.title` | `Rule.SWRL`, `Rule.RuleName`, `Rule.RuleDescription` (PascalCase, ontology-exact) | Phase 13 locked the names; Phase 14 propagates them | All new-ingest Rule nodes match the port<->IRI contract; readers must coalesce for the 5 pre-existing v3-shaped nodes |
| `DesignState.kind` in `{DefState, ObjectState}`, `graph='Metagraph'` | `DesignState.kind` in `{ParamState, ObjState, PropState}`, `graph='ValidationGraph'` (or `'ValidGraph'` if Option B) | Phase 13 D-01/ONTO-03 | No live data affected today (0 DesignState nodes exist) — matters once Phase 18 starts writing them |
| Vestigial DesignState MERGE in the LLM ingest template | DesignState removed from ingest emission entirely, documented separately | Phase 13 D-03 | LLM prompt gets simpler/safer (one less node type it could hallucinate incorrectly) |
| `Run.Status` (text, PDF-proposed) vs `Run.ValidStatus` (Boolean, PDF-proposed) — internally conflicting in the source PDF | Single `Run.ValidStatus` (Boolean list, per-ObjState) + `Run.SendStatus` (Boolean); no stored Status text | Phase 13 D-06/D-07 | REQUIREMENTS.md SCHM-07 wording is stale and should be annotated, not implemented literally |

**Deprecated/outdated:**
- The `SCHEMA VERSION: v3.1` / `"dataset_version": "v3"` / `(v3 schema)` markers scattered across `cypher_template.txt`, `dataset_schema.json`, and both n8n prompt nodes are all simultaneously stale as of this phase and should bump together.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `ValidationGraph`/`ValidGraph` naming conflict should default to Option A (keep `'ValidationGraph'`) if the user doesn't explicitly weigh in | Critical Finding | If the user actually wants full alignment (Option B), a follow-up migration phase is needed later — low risk either way since this research explicitly surfaces the choice rather than silently picking one |
| A2 | `PropState` recommended hex `#7bcfc0`/`#4fa696` is visually harmonious | Artifact 5 | Purely cosmetic — trivial to adjust post-hoc, explicitly marked as Claude's Discretion in CONTEXT.md |
| A3 | `SCHEMA VERSION` should read `v4.0` (not just `v4`) to match the existing `v3.1` two-part convention | Artifact 1 / State of the Art | Cosmetic; either format works, planner can pick either |
| A4 | `Run.ValidStatus`/`Run.SendStatus` full population logic (per-ObjState-index-matched) is out of Phase 14 scope and belongs to Phase 18 | Artifact 7 | Low risk — this is directly stated in REQUIREMENTS.md's traceability table (GHVL-05 owns "the publish path persists a Run with ValidStatus/SendStatus" -> Phase 18); Phase 14 only needs the schema-level property to exist and be documented |

## Open Questions

1. **ValidationGraph vs ValidGraph literal (the Critical Finding above) — requires an explicit answer before Wave assignment.**
   - What we know: the ontology-facing name is `Validgraph`/`ValidGraph`; the live runtime literal (1169 real nodes) is `'ValidationGraph'`; Phase 13 D-01's wording ("graph='ValidGraph'") predates this research's discovery of the mismatch.
   - What's unclear: whether the user intends a full rename (Option B, comparable in scope to Phase 15's SpecGraph rename) or the documented-gap approach already used for the `ValidationRun`->`Run` label (Option A).
   - Recommendation: default to Option A in the plan unless the user explicitly requests Option B during `/gsd-discuss-phase` follow-up or plan review; document the choice explicitly in `cypher_template.txt`'s v4 schema reference section either way so it's never ambiguous again.

2. **Exact `ValidStatus`/`SendStatus` default values for Phase 14's schema-alignment-only scope in `data-service/app.py`.**
   - What we know: full per-ObjState population is explicitly Phase 18 work (GHVL-05).
   - What's unclear: whether Phase 14 should add these as always-empty/always-null placeholder properties (pure schema presence, no computed value) or make a best-effort computation from the already-available `failedRuleIds`/`passedRuleIds` data in `store_validation_run`.
   - Recommendation: pure schema presence (e.g., `SendStatus` = `true` on successful publish call since that's directly knowable today; `ValidStatus` = omitted/null until Phase 18 wires real per-ObjState binding) — avoids Phase 14 accidentally doing Phase 18's binding-logic work.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Desktop / running containers | Live n8n ingest test (SC#2), migration execution (SC#5) | Yes — confirmed running throughout this research session (`docker ps` showed all 14 containers Up) | Docker stack up 46 min at time of research | — |
| Neo4j | All artifacts | Yes | 5.26.19 (community edition) — confirmed via live HTTP endpoint | — |
| n8n | SC#2, workflow re-import | Yes | 2.4.8 (confirmed via `docker exec n8n n8n --version`) | — |
| Ollama | SC#2 (LLM generation) | Yes | 0.15.2 | Cold-start latency 40-70s on first call after idle — not a blocker, just a timing expectation (Pitfall 3) |
| `cypher-shell` (inside neo4j container) or Neo4j Browser | Migration script execution | Not directly probed this session, but `neo4j:5` official image ships `cypher-shell` by default | — | Neo4j Browser (http://localhost:7474) as documented fallback in the existing migration file's header |
| `dotnet` CLI (for `Neo4jRuleRepository.cs` recompile) | D-06/Artifact 8 verification | Not probed this session (prior STATE.md notes .NET SDK 10.0.109 installed, `DOTNET_ROLL_FORWARD=LatestMajor` needed for net9.0 target) | Per STATE.md Blockers/Concerns | Verify once before executing this artifact's edit, per existing STATE.md flag |

**Missing dependencies with no fallback:** None — everything this phase needs was confirmed live and running.

**Missing dependencies with fallback:** `cypher-shell` availability unconfirmed but has a documented fallback (Neo4j Browser) already established by the existing migration file's own header comment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | xUnit (`DG.Tests` project) for C#; no automated framework covers n8n/Cypher/config-file changes — those are validated via live manual/scripted HTTP calls against the running Docker stack |
| Config file | `DG/tests/DG.Tests/DG.Tests.csproj` |
| Quick run command | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~Neo4jRuleRepositoryVariableKindTests"` (unaffected by this phase's edit, but cheap smoke check that nothing else broke) |
| Full suite command | `dotnet test .\DG\tests\DG.Tests\` (per CLAUDE.md Common Commands) — note `DesignStateValidationFlowTests` is tagged `[Trait("Category", "E2E")]` and requires the live Docker stack; run separately or with a category filter |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHM-07/08 | `cypher_template.txt`/`dataset_schema.json` textually declare v4 schema (kinds, Run props, SWRL prop) | manual (file-diff review) | N/A — text-content check, not executable | ✅ (this research read both files in full) |
| SCHM-09 | Live rule ingest through n8n webhook generates Cypher matching v4 template | smoke (live HTTP) | `curl -s -X POST http://localhost:8080/n8n/webhook/dg/rules-ingest -H "Content-Type: application/json" -d '{"rules_text":"Maximum height of each Warehouse must be 40 m.","project_name":"phase14-smoke"}'` then poll the workflow status / inspect the Neo4j-written Rule node for `.SWRL` presence | ❌ — new smoke script needed, Wave 0 gap |
| SCHM-10 | NL graph-query returns results using v4 vocabulary | smoke (live HTTP) | `curl -s -X POST http://localhost:8080/n8n/webhook/dg/graph-query -H "Content-Type: application/json" -d '{"prompt_text":"List all rules with their SWRL text","project_name":"phase14-smoke"}'` — inspect the generated Cypher in the response for `r.SWRL` usage | ❌ — new smoke script needed, Wave 0 gap |
| SCHM-11 | NeoVis renders 3 state kinds with distinct colors; no `DefState`/`ObjectState` remain | manual (visual check in browser at `http://localhost:8080`) + `grep -rn "DefState\|ObjectState" graph-viewer/` returning zero hits post-edit | manual + `grep` | ✅ grep check trivially automatable |
| SCHM-12 | data-service Cypher aligned; `ValidationRun` carries `ValidStatus`/`SendStatus` | integration (live HTTP + Cypher verify) | `curl -s http://localhost:8000/validation/runs/<project>` then verify the JSON response includes the new fields; cross-check via direct Cypher: `MATCH (r:ValidationRun) WHERE r.ValidStatus IS NOT NULL RETURN count(r)` after a fresh publish | ❌ — needs at least one fresh publish call to exercise |
| SCHM-13 | kind-migration script: dry-run count, execute, zero `DefState`/`ObjectState` remain | live migration run against dev DB | `MATCH (n:DesignState) WHERE n.kind IN ['DefState','ObjectState'] RETURN count(n)` before/after via `curl ... /db/neo4j/tx/commit`, expect nonzero-before (after seeding) / 0-after | ❌ — seeding script + before/after count script needed, Wave 0 gap |
| SCHM-14 | v4 successor file exists; `test/` fixtures have no v3 state kinds | file-existence + grep | `test -f training/updated_cypher_reference_examples_v4.cypher && grep -rL "DefState\|ObjectState" test/*.json` | ✅ trivially automatable |

### Sampling Rate
- **Per task commit:** targeted grep/file-diff checks (near-instant) for the text-content artifacts (1, 2, 3, 4, 5, 6, 10, 11); C# unit test filter run for artifact 8.
- **Per wave merge:** full live smoke pass — n8n re-import (both workflows), one live ingest call, one live query call, one Neo4j direct-Cypher spot-check of the resulting nodes.
- **Phase gate:** the kind-migration script's full dry-run -> seed -> execute -> verify cycle (SC#5) plus a final `grep -rn "DefState\|ObjectState"` across the whole repo (excluding `.git`, `graphify-out`, and any archived `.planning/milestones` — those are historical and expected to retain old terminology) returning zero hits in live/runtime files.

### Wave 0 Gaps
- [ ] A small smoke-test script (bash or a `test/` `.sh`/`.py` file) that POSTs a live rule to `/n8n/webhook/dg/rules-ingest` and asserts the resulting Neo4j `Rule` node has `.SWRL` set — covers SCHM-09.
- [ ] A small smoke-test script for `/n8n/webhook/dg/graph-query` asserting the returned/generated Cypher references `r.SWRL` not `r.text` — covers SCHM-10.
- [ ] A seeding script (Cypher, run once before the migration demo) inserting a handful of v3-kind DesignState nodes (some Run-linked, some orphaned) — covers SCHM-13's precondition (Pitfall 5).
- [ ] No xUnit test framework gap — `DG.Tests` already covers the one C# behavior this phase touches at the unit level (indirectly, via not needing new tests since `RulesQuery`/`AtomsQuery` strings aren't unit-tested today and this phase doesn't change that surface).

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (key absent entirely — only `workflow` settings present) — treating as enabled per the default policy, though this phase's actual security surface is minimal.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase touches no authentication logic (existing Neo4j basic-auth / n8n basic-auth / Speckle tokens are unchanged) |
| V3 Session Management | No | Not applicable |
| V4 Access Control | No | Not applicable — no new endpoints, no new permission surface |
| V5 Input Validation | Yes | The kind-migration script's destructive `DELETE` (D-10) is the one real input-validation-adjacent risk in this phase — mitigated by the required dry-run count + dev-database-only guard comment, following the existing `migrations/2026-06-23_var_project_merge_key.cypher` pattern |
| V6 Cryptography | No | No new secrets, tokens, or crypto operations introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via LLM-generated statements (pre-existing risk, not introduced by this phase) | Tampering | Already mitigated by `Parse LLM Output`'s bracket-nesting/quote-balance validator (unchanged by this phase) — worth noting the validator's schema-agnostic design means it needs no update for the property rename |
| Destructive migration accidentally run against production data | Tampering / Repudiation | D-10's dry-run-first + explicit dev-only guard comment (already a locked decision) — this research confirms the existing migration-file pattern already establishes this convention correctly |
| Credential exposure in n8n workflow JSON (basic-auth header computed via a Function node from env-sourced creds, not stored inline) | Information Disclosure | Pre-existing, unchanged pattern — `Compute Neo4j Auth` node builds the auth header at runtime from `neo4j_user`/`neo4j_password` inputs rather than storing a literal credential in the workflow JSON; this phase's edits do not touch that node |

## Sources

### Primary (HIGH confidence — read directly this session)
- `cypher_template.txt` (full file, 192 lines)
- `training/dataset_schema.json` (full file, 188 lines)
- `graph-viewer/config.template.js` (full file, 61 lines)
- `migrations/2026-06-23_var_project_merge_key.cypher` (full file, 65 lines)
- `docker-compose.yml` (full file)
- `n8n/workflows/rules-to-metagraph.json` (all 17 nodes enumerated; `Build LLM Prompt`, `Fetch Existing Entities`, `Parse LLM Output`, `Prepare Graph Payload`, `Annotate Graph Props` read in full)
- `n8n/workflows/graph-query-mcp.json` (`Build Cypher Prompt` read in full)
- `n8n/workflows/_active-graph-query.json`, `_all-workflows-export.json` (metadata/structure diffed against canonical files)
- `graph-viewer/index.html` (targeted grep + line-range read around 1437-1600)
- `data-service/app.py` (lines 1-50, 120-200, 380-620 read directly; full-file grep for `:Rule`/`Rule_Id`/`ValidationGraph`)
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` (full file, 284 lines)
- `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` (targeted grep)
- `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs` (full file)
- `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` (lines 1-100 read directly)
- `training/updated_cypher_reference_examples_v3.cypher` (first 80 lines read)
- `test/` directory listing + targeted greps across `records*.json`, `neo4j_res*.json`, `training_dataset.json`, `CaseStudy_LivingUnit/*.json`, `test_cleanup.js`
- `ontology/port-iri-map-V7.md` (full file, 95 lines)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md`, `.planning/phases/14-graph-schema-v4-propagation/14-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` (full files)
- `DG_OBSIDIAN/sessions/2026-06-23 New PC Docker setup and n8n workflow fix.md` (full file — n8n import gotcha)
- `README.md`, `docs/UPDATED_SYSTEM_SETUP_AND_TEST.md` (grep-confirmed n8n import commands)
- **Live Docker stack** (confirmed running, queried directly): `docker ps` (14 containers up), live Cypher queries against `http://localhost:7474/db/neo4j/tx/commit` (node/label/property counts), `curl http://localhost:7474/` (Neo4j version), `curl http://localhost:11435/api/version` (Ollama version), `docker exec n8n n8n --version` (n8n version), `docker exec n8n n8n --help` (import:workflow command confirmation)

### Secondary (MEDIUM confidence)
- None — this phase required no external/web research; every fact needed was directly readable from the codebase or the live running stack.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new libraries this phase
- Architecture/artifact locations: HIGH — every file was read directly, every line number confirmed against actual file content, live DB was queried directly
- Pitfalls: HIGH — sourced from a real prior debugging session document (`DG_OBSIDIAN/sessions/2026-06-23...md`) plus live-verified environment facts, not speculation
- Critical Finding (ValidationGraph/ValidGraph): HIGH confidence on the *facts* (literal strings, live node counts all directly queried); the *recommendation* (Option A) is a judgment call flagged explicitly for planner/user confirmation, not asserted as locked

**Research date:** 2026-07-03
**Valid until:** Effectively pinned to this session — the live-DB node counts (0 DesignState, 5 Rule, 20 ValidationRun, 1148 ValidationEntity) will drift the moment anyone uses the running dev stack again (e.g., via further manual testing before this phase executes). Re-verify counts immediately before running the kind-migration script's dry-run step if execution happens more than a few days after this research.
