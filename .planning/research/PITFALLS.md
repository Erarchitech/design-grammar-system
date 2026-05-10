# Pitfalls Research: v3.0 Typed Variables and Composable Design State

**Domain:** Parametric rule-based architectural compliance system — SWRL ontology, Grasshopper plugin, Neo4j metagraph
**Researched:** 2026-05-11
**Confidence:** HIGH — all pitfalls grounded in direct codebase inspection, v2.0 retrospective evidence, and SWRL/GH/Neo4j architectural constraints. No speculative claims.

---

## Critical Pitfalls

### Pitfall 1: Variable Type Inference False Positives from Shared Variables

**What goes wrong:**
The inference rule "ClassAtom predicate → Object variable, DataPropertyAtom predicate → Property variable" produces wrong answers when a variable appears in both atom types within the same rule. In the canonical pattern `Building(?b) ^ hasHeightM(?b,?h) ^ swrlb:greaterThan(?h,75)`, `?b` is the subject of a ClassAtom AND the first arg of a DataPropertyAtom. The current `SwrlRuleParser.ResolveAtomType` classifies by arg count (≤1 arg = ClassAtom, ≥2 = DataPropertyAtom), not by the atom the variable is first introduced in. If inference is "variable is Object if it ever appears in pos-1 of a ClassAtom," `?b` is correctly classified. But if a variable appears only in pos-1 of a DataPropertyAtom (e.g. `?b` in a rule with no class atom in the body), it will be silently typed as Property when it is semantically an Object.

**Why it happens:**
The bespoke regex parser (no OWL type system backing) has no access to the ontology's declared ranges. It can only see atom structure, not the declared `owl:Class` vs. `owl:DatatypeProperty` distinction. Variables that appear exclusively inside BuiltinAtoms (e.g. `?h` in `swrlb:greaterThan`) are neither Object nor Property by structural analysis alone — they are intermediate bound values and would be misclassified as Property (the default fallback) or would produce ambiguous results if the inference rule is simply "anything not in a ClassAtom is a Property."

**How to avoid:**
Define type inference as a strict priority chain with explicit "indeterminate" category:
1. If the variable appears at pos-1 of any ClassAtom in body or head → **Object**.
2. Else if it appears at pos-2+ of any DataPropertyAtom → **Property**.
3. Else if it appears only in BuiltinAtom args → **Builtin-bound** (not exposed as Object or Property to the canvas).
4. Else if it appears in head atoms only → check head predicate IRI to decide.

Write this as a dedicated `VariableTypeInferrer` class in `DG.Core.Parsing`, not inline in the parser. Unit-test every category separately, including the case where a single variable crosses multiple atom types.

**Warning signs:**
- A `?h` (numeric value variable) gets typed as Object and surfaces in the OBJECT STATE component's input list.
- A `?b` (entity variable) gets typed as Property and is routed to the Values DataTree in CLASSIFICATOR.
- Rules with no explicit ClassAtom (e.g. purely-datatype rules) produce zero Object variables — check that Variables output from RULE DECONSTRUCT is non-empty before wiring.

**Phase to address:** Phase 1 (Variable Type Inference and DesignState Schema). Type inference logic must be complete and unit-tested before any downstream component relies on it, because OBJECT STATE, RULE DECONSTRUCT's new outputs, and CLASSIFICATOR's input restructure all depend on the inferred type.

---

### Pitfall 2: Missing Inverse Mapping — Variables Typed at Parse Time, Stale After Rule Edit

**What goes wrong:**
Variable type is inferred at METAGRAPH load time by parsing the SWRL expression string. If the rule is subsequently edited in the web UI (n8n ingest → edit mode → new SWRL atoms written to Neo4j), the SWRL string stored in `r.text` / `r.swrl` changes. But a Grasshopper canvas loaded before the edit still holds the old variable type classification from the previous `METAGRAPH.Refresh`. The CLASSIFICATOR will continue routing `?b` as Property if the edit changed the rule structure from a class-first to property-first atom ordering — wrong wiring, wrong validation output, no error message.

**Why it happens:**
The current `Neo4jRuleRepository.PopulateVariables` re-parses `rule.Swrl` on every `GetRulesAsync` call, but the GH component's cached `_latestRules` is only refreshed when `Refresh=true` is pulsed. A canvas that was loaded before the edit and not refreshed continues using the stale type mapping. The CLASSIFICATOR component has no mechanism to detect that the upstream Rule object it received at solve-time has a different variable structure than what is currently in Neo4j.

**How to avoid:**
1. METAGRAPH component: add a `LastUpdated` timestamp to the Rule object (read from `r.updatedAt` if present, or a hash of the SWRL text). Surface it on the component message.
2. After a rule edit, the Rule object's hash changes. Any downstream component that caches a Rule reference should detect the hash change and emit a warning.
3. In the near term: document that "edit a rule → pulse METAGRAPH Refresh → re-run RULE DECONSTRUCT" is the required workflow, and add this to the component tooltip.

**Warning signs:**
- Canvas shows correct validation pass/fail counts but CLASSIFICATOR `MissingVariables` output lists a variable that was previously mapped — means the variable was renamed by a rule edit.
- OBJECT STATE outputs `ObjectRef` for a variable that is now a Property after edit — silent wrong classification.

**Phase to address:** Phase 1 (the SWRL text hash should be added to the Rule model as part of the type-inference phase). Phase 3 (CLASSIFICATOR rework) must include a staleness check or at least a clear warning when variable count changes after a Refresh.

---

### Pitfall 3: Neo4j Class Hierarchy Label Proliferation Breaks NeoVis Captions

**What goes wrong:**
v3.0 introduces `DesignState`, `DefState`, and `ObjectState` as graph node classes. If these are stored as new Neo4j labels (`MERGE (n:DesignState {…})`), NeoVis immediately renders them as unlabelled grey blobs because `config.template.js` has no entry in `labels` or `visGroups` for these new labels. The node appears in the graph with no caption — users see anonymous nodes and cannot distinguish `DesignState` from `DefState`. Additionally, if the Grasshopper plugin also queries the graph for rule/atom data (e.g. METAGRAPH loads `Rule` and `Atom` nodes), a Cypher that uses `MATCH (n)` without label filtering will now return DesignState nodes interleaved with metagraph nodes, corrupting rule loading in edge cases.

**Why it happens:**
The `config.template.js` `labels` map uses Neo4j label as the key. Every new Neo4j label that can be returned by NeoVis Cypher queries must have an entry or it falls back to no caption. The `visGroups` map is similarly exhaustive — missing keys mean default grey. This was previously benign (all labels were known at project start) but v3.0 adds three new label types mid-project.

**How to avoid:**
Before writing any new node to Neo4j, add entries to `config.template.js`:
```javascript
labels: {
  DesignState: { label: "StateId" },
  DefState:    { label: "StateId" },
  ObjectState: { label: "ObjectRef" },
  // ... existing labels unchanged
}
visGroups: {
  DesignState: { color: { background: "#a8d8ea", border: "#6fb3cf" } },
  DefState:    { color: { background: "#a8d8ea", border: "#6fb3cf" } },
  ObjectState: { color: { background: "#b8e8d0", border: "#6fba94" } },
}
```
Add the `config.template.js` update to the definition-of-done for the schema migration phase. Rebuild the `design-grammars` container with `--no-cache` after this change. This is the mandatory schema propagation step documented in `Graph schema v3 is the canonical data model`.

**Warning signs:**
- NeoVis graph renders nodes with no text label — open browser devtools, inspect the NeoVis config object, check if `window.GRAPH_CONFIG.labels` is missing the new label.
- New nodes appear identical in color to existing Atom nodes (default grey) — missing `visGroups` entry.

**Phase to address:** Phase 1 (DesignState schema definition). The `config.template.js` update is part of the mandatory schema-propagation checklist and must ship in the same phase that introduces the new Neo4j labels, not as a follow-up.

---

### Pitfall 4: Object Variable Cross-Rule Identity Collision Across Projects

**What goes wrong:**
The v3.0 design stores cross-rule Object variable identity — the same `?b` (Building) variable used in `R_URB_HEIGHT_MAX_75_V` and `R_URB_FAR_MAX_3_V` is represented as a shared entity in the graph. If the identity resolution uses only the variable name `?b` as the key (a `Var` node with `name: "?b"`), then a variable named `?b` in `project-A` and a variable named `?b` in `project-B` would share the same `Var` node in Neo4j, because the existing `MERGE (v:Var {name: '?b'})` Cypher pattern does NOT include `project` in the merge key.

**Why it happens:**
`Var` nodes in the current v3 schema are keyed only by `name`. The `project` property is set via `SET` (not part of `MERGE`) so it can be overwritten by a cross-project write. `cypher_template.txt` line: `MERGE (vEntity:Var {name: '?<ENTITY_VAR>'}) SET vEntity.project = '<PROJECT>'` — the MERGE succeeds on name-only match, then the SET overwrites the project tag of the already-existing node. Two projects sharing a variable name silently share the same Var node.

Concrete consequence for v3.0: if cross-rule Object variable identity is built on top of `Var` nodes (or a new `ObjectVar` node) using the same name-only merge key, the cross-rule identity becomes cross-project identity — a serious isolation violation.

**How to avoid:**
Change the `Var` node merge key to include `project`:
```cypher
MERGE (v:Var {name: '?<VAR>', project: '<PROJECT>'})
SET v.graph = 'Metagraph'
```
This is a **breaking schema change** to the existing v3 Cypher template. Update `cypher_template.txt`, `dataset_schema.json`, n8n ingest workflow "Prepare Graph Payload" node, and the AtomsQuery in `Neo4jRuleRepository.cs` (`OPTIONAL MATCH (a)-[arg:ARG]->(av)` where `av` is now filtered by project). Run a one-time Cypher migration to back-fill `project` into existing `Var` nodes that are missing it.

**Warning signs:**
- METAGRAPH loads a rule from project-A that has a `?b` variable, and the Var node returned has `project = 'project-B'` — wrong ownership. Query: `MATCH (v:Var {name: '?b'}) RETURN v.project` and verify it returns only one project.
- Two projects' rules appear to share variable bindings in the CLASSIFICATOR — cross-contamination.

**Phase to address:** Phase 1 (schema definition and Cypher template update). The merge-key fix must land before any cross-rule identity feature is built, or the identity mechanism will be built on a broken foundation. Include a migration script in the phase deliverables.

---

### Pitfall 5: StateId Hash Collision After DefState Changes — Stale IdRefs

**What goes wrong:**
v3.0 specifies that `Element Ids` stored on `DesignState` persist cross-rule and regenerate only when `DefState` changes. The DESIGN STATE component already computes a `StateId` as a SHA-256 hash of sorted `ParameterId=value` pairs (16 hex chars). If the new `DesignState` schema uses this `StateId` as the key for "has DefState changed?" detection, and two different DefState snapshots produce the same 16-character truncated hash (birthday probability ~1-in-2^64, negligible), IdRefs would not regenerate when they should. More practically: if the user adds a new slider to the DESIGN STATE component (adding a new ParameterId), but the hash computation only covers the existing parameters (omitting the new one due to a bug), the StateId appears unchanged and IdRefs are not regenerated despite the DefState being different.

**Why it happens:**
The current `ComputeStateId` in `DesignStateComponent.cs` iterates `parameters.OrderBy(x => x.ParameterId)`. If a new parameter is wired but GH does not trigger `SolveInstance` for the new input before the hash is consumed, the hash reflects the old parameter set. In Grasshopper, `SolveInstance` is called when all required inputs are satisfied — optional inputs may not trigger a new solve if not yet connected.

**How to avoid:**
1. Make IdRef regeneration conditional on `DefState` reference equality (object-level, not hash equality) within a single canvas session. Hash equality is sufficient for cross-session identity matching (for filtering), but within-session "did DefState change?" should use reference inequality or a monotonic counter.
2. Add a unit test: create two `DesignStateSnapshot` instances with the same parameters but different counts → assert different `StateId`. This catches the "new parameter excluded from hash" bug.
3. Document clearly: DESIGN STATE re-hashes on every solve. Users should always re-pulse Refresh after adding parameters.

**Warning signs:**
- IdRefs output from DESIGN STATE does not update after adding a new slider — StateId unchanged despite parameter set change.
- REINSTATE component applies old values after DefState change — IdRef not regenerated.

**Phase to address:** Phase 1 (DesignState schema and DESIGN STATE component rework). The hash computation and regeneration trigger logic are core contracts that all subsequent components depend on.

---

### Pitfall 6: VALIDATION RUNS → RUN DECONSTRUCT Rename Silently Breaks Existing Canvases

**What goes wrong:**
Renaming the `VALIDATION RUNS` component to `RUN DECONSTRUCT` (new `ComponentGuid` or same Guid with new internal name) causes any existing `.gh` file saved with the v2.0 plugin to open in Grasshopper with "Component not found" orange warning bubbles on every previously-placed VALIDATION RUNS component. The component's wires are severed — all downstream panels and scripted components that read `Runs`, `Results`, `States`, `Status` outputs receive null. Because the v2.0 canvas had `Refresh=true` default, removing the VALIDATION RUNS component and replacing it with RUN DECONSTRUCT means the user must manually re-wire every connection.

**Why it happens:**
Grasshopper identifies a component by its `ComponentGuid`. The current `ValidationRunsComponent` has `Guid = "A7F2C3E1-B849-4D6A-9F0E-3C2D1E5B8A94"`. If RUN DECONSTRUCT is a new class with a new Guid, GH cannot match the saved instance to the new class — the component appears as "Obsolete" or "Unknown." If the same Guid is reused with a renamed class, GH finds the component but the parameter name changes (`Runs` → `passing items`, `failing items`) sever existing named-parameter wires.

**How to avoid:**
Two options, in order of preference:
1. **Keep old Guid, add `[Obsolete]` migration shim.** Override `AppendAdditionalMenuItems` on the old `ValidationRunsComponent` to show "Upgrade to RUN DECONSTRUCT." In `Read(GH_IReader)`, detect the old parameter layout and emit a migration warning. This preserves existing wires for one release cycle.
2. **Keep backward-compatible outputs alongside new outputs.** Add new `passing items` / `failing items` outputs but keep `Runs`, `Results`, `States`, `Status` as non-breaking pass-throughs (hidden or marked deprecated). Remove them in v4.0 when user canvases have been upgraded.

The migration story must be documented in a user-facing release note. The release note should state: "VALIDATION RUNS component replaced by RUN DECONSTRUCT. Open existing canvases, delete VALIDATION RUNS, drop RUN DECONSTRUCT, re-wire Connection → ValidRun."

**Warning signs:**
- Opening a v2.0 `.gh` file with the v3.0 plugin shows orange "Component missing" bubbles where VALIDATION RUNS was placed.
- REINSTATE component's `States` input is unwired after upgrade — user's reinstatement workflow is broken silently.

**Phase to address:** Phase 2 (RUN DECONSTRUCT component implementation). The migration story (Guid decision, shim or not) must be settled before writing the new component, not after. Include a "can open v2.0 canvas without data loss" test in the verification checklist.

---

### Pitfall 7: CLASSIFICATOR Input Rename Breaks Wires — ElementRefs → GeoRefs

**What goes wrong:**
The v2.0 CLASSIFICATOR has input index 2 named `ElementRefs`. v3.0 renames it to `GeoRefs` and changes the source — it must now come from `DESIGN STATE.GeoRefs` rather than the user-constructed DataTree. Grasshopper wires to inputs by index (not by name) when loading saved files. However, if the v3.0 CLASSIFICATOR changes the number of inputs (adds `Rule`, `Objects`, `Properties`, `PropValues`, `IdRefs`, `GeoRefs`, `DefState`) and changes existing input positions, index-based wire resolution produces garbage: a slider wired to old input index 3 (State) would now arrive at the new input index 3 (Objects), which expects a DG.Rule object — causing a cast failure on every solve.

**Why it happens:**
The v2.0 CLASSIFICATOR has 4 inputs: `Variables`(0), `Values`(1), `ElementRefs`(2), `State`(3). The v3.0 design adds inputs between indices 2 and 3, shifting the old `State` input from index 3 to a higher index. GH saves wire connections by index. Any `.gh` file wired with v2.0 will silently misroute all wires at indices 2+.

**How to avoid:**
1. New inputs must be appended at the end (after all existing inputs) to preserve index-based wire resolution for existing wires. Reorder inputs in documentation order only — physical parameter registration order must be additive.
2. Alternatively: override `Read(GH_IReader)` in the component to detect the old parameter layout (checking `Params.Input.Count == 4`) and emit a "canvas was created with v2.0 — re-wire required" error message. This at minimum alerts the user rather than silently computing wrong results.
3. The `EnsureOutputLayout` pattern already used in `RuleDeconstructComponent` can be adapted: check if the input layout matches the v3.0 expected layout; if not, rebuild inputs and report migration needed.

**Warning signs:**
- CLASSIFICATOR `MissingVariables` output is never empty even when sliders are wired — wrong value type arriving at Variables input.
- CLASSIFICATOR shows a cast error on `Rule` input because the old State connection landed at the wrong index.

**Phase to address:** Phase 3 (CLASSIFICATOR rework). The input layout decision (append-only vs rebuild with migration detection) must be the first design decision for this phase. Include "open v2.0 canvas → see clear migration message, not silent wrong results" as an explicit verification step.

---

### Pitfall 8: RULE DECONSTRUCT Removes Variables/VariableName Outputs — Downstream Wires Severed

**What goes wrong:**
The v2.0 `RuleDeconstructComponent` has outputs: `Rule`(0), `Variables`(1), `VariableName`(2), `SWRL`(3), `RuleName`(4), `RuleDescription`(5). v3.0 removes `Variables` and `VariableName` and adds `Objects`, `Properties`, `Runs`. Any existing canvas that wires `Variables` output to CLASSIFICATOR's `Variables` input will silently break: the new output at index 1 is `Objects` (not `Variables`), and the wire now delivers a list of Object-typed variables where the CLASSIFICATOR expects the full variable list.

**Why it happens:**
Same mechanism as Pitfall 7, but on the output side. The `EnsureOutputLayout` method already in `RuleDeconstructComponent` would re-create outputs to match the new `ExpectedOutputNames` array, which would destroy the old wire connections on canvas load.

**How to avoid:**
1. Keep `Variables` as a deprecated output for one release cycle, appended at the end rather than removed. Mark it with `[Obsolete]` in the description: "Deprecated in v3.0 — use Objects + Properties instead. Will be removed in v4.0."
2. Update `ExpectedOutputNames` to include the deprecated output, so `EnsureOutputLayout` does not destroy it.
3. Document in release notes: "RULE DECONSTRUCT Variables output is deprecated. Wire RULE DECONSTRUCT.Objects → CLASSIFICATOR.Objects and RULE DECONSTRUCT.Properties → CLASSIFICATOR.Properties instead."

**Warning signs:**
- CLASSIFICATOR receives a list of Object-type variables at its `Variables` input where it previously received all variables — classification now misses Property variables.
- `EnsureOutputLayout` on canvas load destroys existing wires silently — user opens file, all outputs are empty, no error message.

**Phase to address:** Phase 2 (RULE DECONSTRUCT rework). Deprecation strategy must be settled before the component is modified.

---

### Pitfall 9: LLM Cypher Template Desync After Schema Migration — Silently Generates Invalid Cypher

**What goes wrong:**
v3.0 adds new node labels (`DesignState`, `DefState`, `ObjectState`) and potentially new relationships. The n8n ingest workflow's "Build LLM Prompt" node embeds the full schema from `cypher_template.txt`. If `cypher_template.txt` is updated but the n8n workflow is not re-imported, the LLM receives the old schema and generates Cypher using old node labels and relationship types. The resulting Cypher is syntactically valid but semantically wrong — it creates nodes with the old schema while the application expects the new one. Because LLM Cypher generation does not validate output against the current graph schema, this failure is completely silent until a downstream query returns unexpected results.

**Why it happens:**
The n8n workflow's "Build LLM Prompt" node stores the prompt text inline in the workflow JSON (`n8n/workflows/rules-to-metagraph.json`). Updating `cypher_template.txt` does not automatically propagate to the n8n workflow — the workflow JSON must be re-exported from the n8n UI or the Function node edited directly. This propagation step is documented in `Graph schema v3 is the canonical data model` but has no enforcement mechanism.

Additionally, if new node types (DesignState, DefState, ObjectState) are introduced by Grasshopper writes directly to Neo4j (bypassing n8n), the ingest workflow might not know about them and will fail to create or reference them correctly in generated Cypher.

**How to avoid:**
1. Add a schema version stamp to `cypher_template.txt` (e.g., `# SCHEMA VERSION: v3.1`) and mirror it in the n8n workflow JSON as a comment in the Function node. The phase verification checklist must confirm these match.
2. The phase that introduces new node types must include an explicit task: "Update n8n rules-to-metagraph.json Function node prompt to include new node labels and example Cypher."
3. After any schema change, test with a new NL rule submission and inspect the generated Cypher in n8n's execution log to confirm it uses the updated schema.

**Warning signs:**
- NeoVis graph shows Rule nodes but no DesignState nodes connected — n8n ingest didn't create them.
- `METAGRAPH` loads rules but `DesignStates` output is always empty despite runs existing in Neo4j.
- n8n execution log shows generated Cypher using `Var` node labels where `ObjectVar` or `DesignState` is expected.

**Phase to address:** Phase 1 (schema definition must include the n8n prompt update as a deliverable). Every subsequent phase that changes the schema must include "update n8n prompt and verify with a live ingest test" as a mandatory verification step — not optional.

---

### Pitfall 10: Component Contract Churn Cascades into Training Dataset Obsolescence

**What goes wrong:**
`training/dataset_schema.json` and `training/updated_cypher_reference_examples_v3.cypher` are the training/prompt ground truth. If v3.0 adds new node types and the dataset is updated (adding `DesignState`, `DefState`, `ObjectState` examples), but the Grasshopper component contracts change mid-phase (e.g. CLASSIFICATOR input renames happen in Phase 3 after the dataset was updated in Phase 1), the dataset's example rules may reference property names or relationship structures that no longer match the current component expectations. The dataset becomes inconsistently versioned — some examples reflect v3.1 schema, others reflect v3.0-draft.

**Why it happens:**
The training dataset is a static file that accumulates examples. There is no mechanism to validate that an existing example still produces Cypher compatible with the current component expectations. A schema change that invalidates 3 of 15 examples is invisible until the LLM generates Cypher based on the obsolete examples during prompt-constrained inference.

**How to avoid:**
1. Treat `training/dataset_schema.json` as a contract file, not a data file — it changes only when the schema changes, not incrementally. Pin it to a version identifier.
2. Write a validation script (`validate_dataset.py` or a test) that parses each example's `metagraph` section and checks: all node labels exist in the allowed label set, all relationship types are in the allowed relationship set, all key properties match the schema. This script runs in CI on every PR that touches `cypher_template.txt` or `dataset_schema.json`.
3. When component contracts change (Phase 2, 3), explicitly audit which training examples are affected and update them atomically in the same commit.

**Warning signs:**
- LLM generates `(v:Variable {...})` instead of `(v:Var {...})` — training example used the old label.
- LLM omits `project` from a new node type — the new node type's example was added without `project` property.
- Dataset has a mix of v3 and v3.0-draft schemas that produce conflicting examples for the LLM.

**Phase to address:** Phase 1 (schema definition must freeze the v3.0 node label set and relationship type set before examples are added). Phase 3 and beyond: every component contract change must include a dataset audit step.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use variable name only (not name+project) as Var merge key | Simpler Cypher template | Cross-project variable node sharing; isolation violation | Never — fix in Phase 1 |
| Infer variable type inline in `SwrlRuleParser` | Less code | Untestable, no explicit "indeterminate" category, breaks when rules evolve | Never — extract to `VariableTypeInferrer` |
| Copy `ComponentGuid` from old to new component on rename | Avoids obsolete-component warning on canvas load | Silent input/output layout mismatch when parameter count differs | Only if parameter layout is strictly backward-compatible (additive only) |
| Defer `config.template.js` NeoVis update to "later" | Faster schema phase | New nodes render as unlabelled grey blobs; users see broken graph immediately | Never — must ship in same commit as new node labels |
| Skip migration shim for VALIDATION RUNS → RUN DECONSTRUCT | Less code | Every v2.0 canvas file is immediately broken on upgrade | Never — at minimum add a "re-wire required" error message |
| Update n8n workflow prompt manually via n8n UI (not in workflow JSON) | Quick | Prompt is not in version control; next container restart loses the change | Never — edit must be committed to `n8n/workflows/*.json` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Neo4j + NeoVis | Add new node labels without updating `config.template.js` `labels` and `visGroups` | Always add label config in the same commit as the schema change; rebuild container with `--no-cache` |
| SWRL parser + type inference | Classify variable type inside `SwrlRuleParser.Parse()` as a side effect | Extract to a separate `VariableTypeInferrer.Infer(ParsedSwrlRule)` call; keeps parser single-responsibility |
| Grasshopper + existing canvas | Change parameter name/count mid-index causing silent wire misrouting | Only append new parameters at the end; detect old layouts in `Read()` and emit migration messages |
| n8n ingest workflow + schema | Embed schema inline in Function node; update `cypher_template.txt` but forget to re-import workflow | Add schema version stamp to both files; verify with live ingest test after every schema change |
| LLM prompt + new node types | Add new labels to `cypher_template.txt` but not to the few-shot example Cypher block | The few-shot example is what the LLM actually follows — update it first, `SCHEMA` section second |
| DesignState / DefState / ObjectState + Neo4j | Merge DesignState nodes without including `project` in the merge key | All new node types must follow the established `{project: $project}` merge key pattern from day one |
| Cross-rule Object variable identity + project isolation | Use `Var.name` alone as cross-rule identity anchor | Cross-rule identity must be scoped to `{name, project}` — same variable name in two projects is not the same object |

---

## "Looks Done But Isn't" Checklist

- [ ] **Variable type inference:** Implemented and unit-tested for the "variable appears in multiple atom types" case — verify test exists for `?b` typed Object even when `?b` also appears in DataPropertyAtom at pos-1.
- [ ] **NeoVis config:** New node labels (`DesignState`, `DefState`, `ObjectState`) have entries in both `labels` and `visGroups` in `config.template.js` — verify by opening the Graph Viewer and confirming new nodes render with captions.
- [ ] **n8n prompt sync:** `cypher_template.txt` schema version matches the Function node content in `rules-to-metagraph.json` — verify by diffing the schema section in both files.
- [ ] **Var merge key:** `MERGE (v:Var {name: '?x', project: $project})` pattern used in all new Cypher — verify by running `MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` and confirming zero results.
- [ ] **VALIDATION RUNS migration:** Opening a v2.0 `.gh` file with the v3.0 plugin shows a clear migration error message, not silent null outputs — verify by loading a saved v2.0 canvas.
- [ ] **RULE DECONSTRUCT Variables output:** Deprecated `Variables` output still present at the end of the output list — verify `ExpectedOutputNames` array in the component source.
- [ ] **CLASSIFICATOR input ordering:** All new inputs are appended after the existing 4 — verify index 0=Variables, 1=Values, 2=GeoRefs (renamed ElementRefs), 3=State (or DefState) remain at their original indices.
- [ ] **StateId regeneration:** Adding a new slider to DESIGN STATE component and re-solving produces a different StateId — verify with a before/after comparison.
- [ ] **Training dataset validation:** `dataset_schema.json` examples pass the schema validation script — verify by running the script and confirming zero violations.
- [ ] **Schema propagation completeness:** After any schema change, all five propagation targets updated: `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompt, `config.template.js`, Python/JS Cypher templates in `data-service/app.py`.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1 — Type inference false positives | Phase 1: Variable Type Inference | Unit tests for all 4 variable categories including multi-atom-type variables |
| P2 — Stale type after rule edit | Phase 1 (hash in Rule model) + Phase 3 (CLASSIFICATOR staleness warning) | Manually edit a rule in web UI → METAGRAPH without Refresh shows stale-type warning |
| P3 — NeoVis label proliferation | Phase 1: DesignState schema definition | Graph Viewer renders DesignState/DefState/ObjectState nodes with captions and distinct colors |
| P4 — Cross-project Var collision | Phase 1: Cypher template Var merge key fix | `MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` returns 0 after migration |
| P5 — StateId stale after DefState change | Phase 1: DESIGN STATE component rework | Unit test: snapshot with N params ≠ snapshot with N+1 params |
| P6 — VALIDATION RUNS rename breaks canvases | Phase 2: RUN DECONSTRUCT component | Load v2.0 `.gh` file → see "re-wire required" message, not null outputs |
| P7 — CLASSIFICATOR input index shift | Phase 3: CLASSIFICATOR rework | Load v2.0 `.gh` file with old wiring → old indices 0–3 still resolve correctly |
| P8 — RULE DECONSTRUCT Variables removal | Phase 2: RULE DECONSTRUCT rework | Deprecated Variables output present at last index; downstream wires intact |
| P9 — n8n prompt desync after schema change | Phase 1 (stamp) + every schema-touching phase | Schema version stamp matches; live ingest test generates Cypher with new node labels |
| P10 — Training dataset obsolescence | Phase 1 (freeze label set) + Phase 3 (audit) | Dataset validation script passes with zero violations |

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| P3 — NeoVis caption breakage | LOW | Update `config.template.js`; rebuild `design-grammars` container with `--no-cache`; hard-refresh browser |
| P4 — Cross-project Var collision | MEDIUM | Run one-time Cypher migration: `MATCH (v:Var) SET v.project = coalesce(v.project, 'default-project')`; then change merge key in template; re-ingest affected rules |
| P6 — Canvas breakage from rename | HIGH | Provide migration instructions (delete VALIDATION RUNS, drop RUN DECONSTRUCT, re-wire); or implement Guid-preserving shim in a hotfix |
| P7 — CLASSIFICATOR index shift | HIGH | Re-wire all CLASSIFICATOR instances in affected canvases; no automated recovery path |
| P9 — n8n prompt desync | LOW | Edit n8n Function node content in UI to match `cypher_template.txt`; export and commit updated workflow JSON |
| P10 — Dataset obsolescence | MEDIUM | Audit all examples against current schema; update invalid examples; run validation script to confirm |

---

## Sources

- Direct codebase inspection (HIGH confidence):
  - `DG/src/DG.Core/Parsing/SwrlRuleParser.cs` — `ResolveAtomType` uses arg-count heuristic, not atom classification
  - `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — `AtomsQuery` and `PopulateVariables` reveal current variable loading logic
  - `DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs` — `EnsureOutputLayout` pattern and `ExpectedOutputNames` fragility
  - `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` — v2.0 input index layout (0–3)
  - `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` — `ComponentGuid` and parameter names to be renamed
  - `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` — `ComputeStateId` SHA-256 hash implementation
  - `graph-viewer/config.template.js` — `labels` and `visGroups` maps (all current labels enumerated)
  - `cypher_template.txt` — `MERGE (vEntity:Var {name: '?<ENTITY_VAR>'})` without project in merge key
  - `training/dataset_schema.json` — schema version field absent; no validation mechanism
- `.planning/v2.0-GAP-CLOSURE.md` — retrospective on the broken-chain pattern (plans claiming completeness without verifying full data flow)
- `DG_OBSIDIAN/knowledge/debugging/Edit mode requires cleanup of old atoms before re-creation.md` — orphan-ref precedent
- `DG_OBSIDIAN/knowledge/decisions/SWRL parsing is bespoke regex not vendor OWL library.md` — parser limitation scope
- `DG_OBSIDIAN/atlas/Graph schema v3 is the canonical data model.md` — mandatory propagation checklist

---
*Pitfalls research for: v3.0 Typed Variables and Composable Design State*
*Researched: 2026-05-11*
