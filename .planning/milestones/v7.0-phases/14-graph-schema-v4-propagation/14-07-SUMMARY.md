---
phase: 14-graph-schema-v4-propagation
plan: 07
subsystem: "training, test-fixtures, planning-docs"
tags: ["reference-hygiene", "documentation", "schema-propagation", "schm-14", "d-02"]
requires: ["14-01"]
provides: ["SCHM-14", "D-02"]
affects: ["training/", "test/", ".planning/ROADMAP.md", ".planning/REQUIREMENTS.md"]
tech-stock:
  added: []
  patterns: []
key-files:
  created:
    - training/updated_cypher_reference_examples_v4.cypher
  modified:
    - test/training_dataset.json
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "training/updated_cypher_reference_examples_v4.cypher created as new file (v3 kept for transition-period grep history)"
  - "test/training_dataset.json annotated as pre-v4/superseded — no automated test consumes these fixtures"
  - "ROADMAP SC#1 and REQUIREMENTS SCHM-07: removed stale Status-text Run property wording per D-01/D-02"
metrics:
  duration: "~8min"
  completed_date: "2026-07-03"
  tasks: 3
  files_created: 1
  files_modified: 3
status: complete
---

# Phase 14 Plan 07: Reference Hygiene — v4 successor file, fixture markers, stale-wording amendment

**One-liner:** Finished the v4 propagation by creating the LLM few-shot reference (`updated_cypher_reference_examples_v4.cypher` with `r.SWRL`, `RuleName`, `RuleDescription` — no DesignState MERGE), annotating the `test/training_dataset.json` fixture as pre-v4/superseded, and removing the stale "Status text" Run-property wording from ROADMAP SC#1 and REQUIREMENTS SCHM-07 per D-02.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create `training/updated_cypher_reference_examples_v4.cypher` (SCHM-14) | `4bbde7b` | `training/updated_cypher_reference_examples_v4.cypher` |
| 2 | Fixture hygiene — annotate `test/training_dataset.json` as pre-v4 (SCHM-14) | `633fc3b` | `test/training_dataset.json` |
| 3 | Amend stale "Status text" wording in ROADMAP + REQUIREMENTS (D-02) | `ef39e6f` | `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` |

## Details

### Task 1 — v4 Cypher reference examples

Created `training/updated_cypher_reference_examples_v4.cypher` as the v4 successor of the v3 few-shot reference file. The v3 file (`updated_cypher_reference_examples_v3.cypher`) is retained for transition-period grep history as instructed.

The v4 file contains four worked examples:

1. **R_URB_HEIGHT_MAX_75_V** — adapted from v3 Example 1, `r.text` → `r.SWRL`, minimal Rule node (no RuleName/RuleDescription).
2. **R_SUNLIGHT_MIN_2_8H_V** — adapted from v3 Example 2, `r.text` → `r.SWRL`, `r.title` → `r.RuleName`, demonstrating optional name property.
3. **R_URBANBLOCK_GRID_MIN_12M_V** — adapted from v3 Example 3, `r.text` → `r.SWRL`, minimal Rule node.
4. **R_ENERGY_WWR_MAX_40_V** — **NEW** in v4, exercises the full v4 Rule property set (`SWRL`, `RuleName`, `RuleDescription`) demonstrating a window-to-wall ratio energy rule with descriptive properties populated by the LLM.

No DesignState MERGE statements are present (D-03: ingest emits OntoGraph + Metagraph only). The file mirrors the v4 CYPHER TEMPLATE BLOCK from `cypher_template.txt`.

### Task 2 — Fixture annotation

`test/training_dataset.json` was annotated:
- `dataset_version` changed from `"v3"` to `"v3 (pre-v4 — superseded)"`
- `description` amended to note the file captures the pre-v4 schema and is retained for historical/debugging reference only, with a pointer to the v4 successor file

**No automated test consumes `test/training_dataset.json`** — confirmed via repo-wide grep for the filename in `.py`, `.js`, `.cs`, and `.sh` files returning zero matches. Other `test/*.json` files (`records*.json`, `neo4j_res*.json`) are raw Neo4j export dumps that do not present schema versioning information and were left untouched per the plan's "do NOT rewrite every fixture record" directive.

### Task 3 — Stale wording amendment (D-02)

- **ROADMAP.md Phase 14 SC#1**: Removed `"Status"` from the Run-properties list. The line now reads `Run properties (ValidStatus, SendStatus — no stored Status text field; overall pass = AND(ValidStatus) derived at read time per D-01/D-02)`.
- **REQUIREMENTS.md SCHM-07**: Removed `"Status text"` from the Run properties. The line now reads `Run properties (ValidStatus Boolean, SendStatus Boolean — per D-01/D-14 the prior Status-string property was removed; overall pass = AND(ValidStatus) derived at read time)`.

No functional `Status` field was introduced anywhere — only documentation corrections.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all tasks produced complete, production-ready artifacts. The v4 reference file is a self-contained worked example; the fixture annotation is a marker-only change; the ROADMAP/REQUIREMENTS amendments are complete.

## Fixture Consumer Note

Per RESEARCH finding (confirmed again during execution): **no automated test (`.py`, `.js`, `.cs`) loads `test/training_dataset.json`**. The file is a human/LLM-prompt-authoring reference document only. This means the annotation-only approach (not rewriting fixture records) is proportionate to the actual risk — zero test breakage possible from stale fixture content.

## Threat Flags

None — no new threat surface introduced. All changes are documentation/reference hygiene.

## Self-Check: PASSED

- `training/updated_cypher_reference_examples_v4.cypher` — exists, contains `r.SWRL`, `RuleName`, `RuleDescription`, no DesignState MERGE
- `test/training_dataset.json` — carries v4/superseded marker
- `.planning/REQUIREMENTS.md` — no occurrences of `"Status text"`, has `SendStatus`
- `training/updated_cypher_reference_examples_v3.cypher` — untouched (verified via git status)
