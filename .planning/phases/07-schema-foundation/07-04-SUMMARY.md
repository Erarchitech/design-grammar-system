---
phase: 07-schema-foundation
plan: 04
subsystem: schema-propagation
tags: [neo4j, n8n, neovis, cypher, training-data, data-service, schema-propagation]

# Dependency graph
requires:
  - phase: 07-01
    provides: VariableKind enum, VariableTypeInferrer
  - phase: 07-02
    provides: DefState/ObjectState/ObjectInstance C# model hierarchy, DS_/OS_ ID prefixes
  - phase: 07-03
    provides: cypher_template.txt fixed Var MERGE key (name+project), DesignState{kind} MERGE block, SCHEMA VERSION v3.1 stamp
provides:
  - training/dataset_schema.json DesignState node schema entry + corrected Var key block (v3.1)
  - training/updated_cypher_reference_examples_v3.cypher with project-scoped Var MERGE pattern across all 3 examples
  - n8n/workflows/rules-to-metagraph.json embedded LLM prompt synced to cypher_template.txt v3.1 (Var key, DesignState vocabulary)
  - graph-viewer/config.template.js DesignState NeoVis labels/visGroups with kind-based distinct coloring
  - data-service/app.py DS_/OS_ vocabulary-aligned docstrings (no behavior change)
affects: [Phase 8 (OBJECT STATE component), Phase 9 (DesignState node writes), Phase 10 (CLASSIFICATOR), Phase 11 (statePayloadJson OS_ extension)]

# Tech tracking
tech-stack:
  added: []
  patterns: [NeoVis group property keying for single-label multi-kind node coloring]

key-files:
  created: []
  modified:
    - training/dataset_schema.json
    - training/updated_cypher_reference_examples_v3.cypher
    - n8n/workflows/rules-to-metagraph.json
    - graph-viewer/config.template.js
    - data-service/app.py

key-decisions:
  - "DesignState added to metagraph.nodes[] array (not as a rule_node-style singular top-level key) — it is a generic reusable node-type template like Var/Literal/Atom, matching the structural placement guidance from the plan's read_first notes"
  - "config.template.js DesignState labels entry uses group: \"kind\" so NeoVis keys visGroups by the kind property's VALUES (DefState/ObjectState) rather than by the DesignState label itself — confirmed via PITFALLS.md Pitfall 3 as the correct mechanism, not a fallback"
  - "data-service/app.py vocabulary alignment limited strictly to comments/docstrings near statePayloadJson field and _project_state_summary() docstring — no change to function body, Pydantic type, or any of the 4 call sites, per CONTEXT.md's Phase 11 deferral note"

patterns-established:
  - "NeoVis single-label multi-kind coloring: labels.<Label>.group: \"<propertyName>\" + visGroups keyed by that property's values, not the label name — reusable for any future Rule.kind-style discriminated node type needing distinct NeoVis colors per kind"

requirements-completed: [SCHM-04, SCHM-06]

# Metrics
duration: 12min
completed: 2026-06-23
status: complete
---

# Phase 7 Plan 04: Schema Propagation — Training Data, n8n Prompt, NeoVis Config, Data-Service Vocabulary Summary

**Propagated the Var merge-key fix and new DesignState{kind} node shape (locked in 07-01/07-02/07-03) across the five remaining CLAUDE.md schema-propagation surfaces: dataset_schema.json, the cypher training examples, the n8n-embedded LLM prompt, NeoVis config, and data-service vocabulary**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-06-23
- **Tasks:** 2 completed
- **Files modified:** 5

## Accomplishments
- `training/dataset_schema.json`: `Var` node's `"key"` block now documents `project` alongside `name`; new `DesignState` entry added to `metagraph.nodes[]` with `kind` documented as `DefState | ObjectState`; `metadata.version` bumped to `"v3.1"` to match `cypher_template.txt`'s stamp from 07-03
- `training/updated_cypher_reference_examples_v3.cypher`: all 6 `Var` MERGE occurrences across the file's 3 example walkthroughs (Example 1: `vb`/`vh`; Example 2: `vb`/`vs`; Example 3: `vub`/`vg`) now include `project` inside the MERGE braces, eliminating the old bare-name-only MERGE pattern entirely
- `n8n/workflows/rules-to-metagraph.json`'s "Build LLM Prompt" function node: `fewShot` array's `vb`/`vh` MERGE lines restructured to the project-scoped pattern; `SCHEMA CONSTRAINTS` text's `Var key` line updated to `name + project`; new `DesignState key` line added to `NODE KEY PROPERTIES`; `DesignState` appended to the `Allowed node labels` list — closes the Pitfall 9 desync gap between the n8n-embedded prompt and `cypher_template.txt`
- `graph-viewer/config.template.js`: `DesignState: { label: "StateId", group: "kind" }` added to `labels`; `DefState`/`ObjectState` entries added to `visGroups` with visibly distinct colors (`#a8d8ea` vs `#f4a261`), keyed by the `kind` property's values per the `group: "kind"` directive — closes the Pitfall 3 unlabelled-grey-blob gap
- `data-service/app.py`: docstring/comment additions near `statePayloadJson` field declaration and `_project_state_summary()` referencing the `DS_`/`OS_` ID-prefix vocabulary — purely documentation, no behavior, type, or call-site changes

## Task Commits

Each task was committed atomically:

1. **Task 1: dataset_schema.json and training cypher reference examples** - `5bc7af7` (feat)
2. **Task 2: n8n LLM prompt sync, NeoVis config, data-service vocabulary alignment** - `b874147` (feat)

## Files Created/Modified
- `training/dataset_schema.json` - `Var` key block includes `project`; new `DesignState` node entry; `metadata.version` → `"v3.1"`
- `training/updated_cypher_reference_examples_v3.cypher` - all `Var` MERGE statements include `project` in the MERGE key
- `n8n/workflows/rules-to-metagraph.json` - "Build LLM Prompt" function node's embedded prompt text (fewShot, SCHEMA CONSTRAINTS, NODE KEY PROPERTIES, allowed-labels list) synced to project-scoped Var pattern and DesignState vocabulary
- `graph-viewer/config.template.js` - `labels.DesignState` with `group: "kind"`; `visGroups.DefState` and `visGroups.ObjectState` with distinct colors
- `data-service/app.py` - docstring/comment additions referencing DS_/OS_ vocabulary near `statePayloadJson` and `_project_state_summary()`

## Decisions Made
- Placed the new `DesignState` schema entry inside `metagraph.nodes[]` (the generic reusable node-type array) rather than as a `rule_node`-style singular top-level key, matching the plan's structural guidance that DesignState behaves like Var/Literal/Atom, not like the singular Rule template
- Used NeoVis's `group: "kind"` directive on the `DesignState` labels entry, which makes `visGroups` key off the `kind` property's runtime values (`DefState`/`ObjectState`) instead of the label name — this is the documented Pitfall 3 mechanism, not a workaround
- Kept the `data-service/app.py` change strictly to comments/docstrings, leaving `_project_state_summary()`'s logic, the `statePayloadJson` Pydantic field type, and all 4 call sites byte-identical, per CONTEXT.md's explicit Phase 11 deferral

## Deviations from Plan

### Auto-fixed Issues

None requiring Rule 1-4 intervention. One minor scope correction (not a deviation from intent, just a count correction):

**1. [Plan accuracy note] training/updated_cypher_reference_examples_v3.cypher had 6 Var MERGE occurrences, not "at least 2" as the plan's read_first stated**
- **Found during:** Task 1
- **Issue:** The plan's read_first note said "there are at least 2 in the file's Example 1 walkthrough" — on full read, the file contains 3 examples, each with 2 Var MERGE statements (6 total: vb/vh, vb/vs, vub/vg)
- **Fix:** Applied the identical restructuring to all 6 occurrences across all 3 examples, consistent with the plan's stated intent ("find every MERGE (<var>:Var {name: '?<name>'}) occurrence")
- **Files modified:** training/updated_cypher_reference_examples_v3.cypher
- **Commit:** 5bc7af7

## Issues Encountered

**Python interpreter unavailable in execution environment:** The plan's `<verify>` step for `data-service/app.py` specifies `python -c "import ast; ast.parse(open('data-service/app.py').read())"` to confirm valid Python syntax after the docstring edit. No Python interpreter (`python`, `python3`, `py -3`) is available in this execution environment — consistent with the prior .NET SDK gap noted in 07-01-SUMMARY.md (tooling availability gap, not a code issue). The edit was instead verified by direct inspection: the added lines are a properly indented `#`-prefixed comment block (Pydantic field) and an extension to an existing triple-quoted docstring with consistent indentation, with the function body below the docstring left completely untouched (confirmed via diff). This is a deferred manual verification step, not a blocker — same precedent as 07-03's live-Neo4j migration verification deferral.

## User Setup Required

To complete deferred verification in a live environment:
1. Run `python -c "import ast; ast.parse(open('data-service/app.py').read())"` to confirm the docstring/comment edits did not introduce a Python syntax error (expected: exits 0, no output)
2. Optionally rebuild the `design-grammars` container with `--no-cache` and hard-refresh the browser to visually confirm `config.template.js`'s `DesignState` NeoVis entries render once `:DesignState` nodes exist in Neo4j (no such nodes exist yet — this is schema propagation ahead of Phase 9's actual writes)
3. Optionally submit a test NL rule via the n8n ingest webhook and inspect the n8n execution log to confirm the LLM prompt now reflects the project-scoped Var key text (live ingest test per Pitfall 9's recommended verification)

## Next Phase Readiness

- All six CLAUDE.md schema-propagation surfaces (C# models, `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompt, `config.template.js`, `data-service/app.py`) are now consistent on the `DS_`/`OS_` prefix vocabulary and the single-label `:DesignState{kind}` pattern — Phase 7 ROADMAP success criterion 3 satisfied in full
- NeoVis is pre-configured to render `DefState`/`ObjectState` nodes in distinct colors as soon as Phase 9 starts writing `:DesignState` nodes to Neo4j — Phase 7 ROADMAP success criterion 4 satisfied in full, no fallback path used
- `training/dataset_schema.json` and the n8n-embedded prompt are both stamped/aligned to schema v3.1, closing the Pitfall 9 desync risk before any further schema changes land in Phase 8+
- This is the final plan in Phase 7 (Schema Foundation) — phase transition / `/gsd-transition` is the next step

---
*Phase: 07-schema-foundation*
*Completed: 2026-06-23*

## Self-Check: PASSED

All 5 modified files verified present on disk; both commit hashes (5bc7af7, b874147) verified present in git log.
