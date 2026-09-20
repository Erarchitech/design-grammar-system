---
phase: 40-e2e-validation-and-docs
plan: 03
subsystem: docs
status: complete
requirements-completed: [INTG-04]
---

# Phase 40 Plan 03 Summary

## Outcome

Closed runbook decisions D4 and D5 without changing validation behavior. `spec/DATABASE.md` now documents the Phase 39 auto-validation Run properties, status lifecycle, absent-property semantics, the F-39-01 caveat, and the `IntegrationConfig{provider:'AutoValidation'}` variant. The Phase 39 latency statement remains verbatim and is followed by the D5 annotation. The six surfaces left unaudited by Phase 40 research were rechecked against source; only the real policy/documentation gaps were patched.

## Changes

- `spec/DATABASE.md`
  - Added auto-path examples and documentation for `trigger`, `verdictSource`, `capturedAt`, `completedAt`, `attempts`, `lastError`, and `status`.
  - Recorded writers from `CAPTURE_QUERY`, `COMPLETE_QUERY`, `FAIL_QUERY`, and `COALESCE_QUERY`, including legal status transitions and absent-property semantics.
  - Recorded auto-path `SendStatus=false` initialization and the F-39-01 `RunStatusShape_valid` limitation, with the follow-up-milestone boundary.
  - Added the `IntegrationConfig` subsection, merge key `(graph, provider, project)`, `AutoValidation` discriminator, six guardrail properties, `CONFIG_UPSERT_QUERY`, and `get_auto_validation_config` absent-row semantics.
  - Added a graph-separation cross-reference and Phase 40 changelog entry.
- `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-03-SUMMARY.md`
  - Added the requested one-line D5 annotation after the original latency paragraph; original wording and measured totals remain unchanged.
- `ontology/dg-shapes.ttl`
  - Added comments only at `RunStatusShape` documenting F-39-01. No SHACL target, constraint, severity, message, or shape logic changed.
- `spec/RULE-PARTITION-POLICY.md`
  - Added the real documentation gap: the auto-validation path is on the SHACL side of the partition and its known F-39-01 pre-write self-violation is documented, not repaired by policy or shape changes.

## Six unaudited surfaces: source-backed disposition

1. **`llm/structure_rules.json` — confirmed-correct.** JSON loads successfully with top-level keys `version`, `mappings`, and `inputBindings`; Phase 38's sibling `inputBindings` key is present.
2. **`cypher_template.txt` — confirmed-correct.** The template contains the Computgraph labels `Object`, `Behavior`, `Algorithm`, `Procedure`, `Pattern`, `Parameter`, and `Interface`, plus the expected Computgraph relationships. It is prompt/schema documentation; runtime Computgraph writes are handled by `computgraph_publish.py`.
3. **`training/dataset_schema.json` — confirmed-correct for this plan.** JSON parses successfully and contains the existing schema-v4 `schema_reference` with Computgraph fields and relationships. The file has no missing Phase 39 auto-validation Run/config write shape because it documents the rules-ingest example format, not watcher persistence.
4. **`spec/DG-ID.md` — confirmed-correct.** Its scope and examples cover the five entity labels `Object`, `Procedure`, `Pattern`, `Parameter`, and `Interface`; `Behavior` and `Algorithm` are explicitly structural/excluded from `dgId` provenance by the linked database documentation. No patch required.
5. **`spec/RULE-PARTITION-POLICY.md` — patched.** The ownership boundary was present, but it did not name the Phase 39 auto-validation path or F-39-01. Added one sentence tying the path to SHACL and cross-referencing the database note without changing the policy's validation ownership.
6. **`ontology/dg-shapes.ttl` — patched, comment-only.** `RunStatusShape` was present and unchanged. Added an F-39-01 comment explaining the pre-`ValidStatus` evaluation and follow-up scope; no validation logic changed.

## CLAUDE.md handoff

`CLAUDE.md`'s `IntegrationConfig` row says only “Speckle/project integration settings.” It remains factually valid but does not name the Phase 39 `AutoValidation` variant. Per the plan's ownership boundary, this was not edited here; plan 40-05 should decide whether to amend that row to mention `AutoValidation`.

## Verification

Source-backed checks completed:

- Every documented Run/config property was grepped in `data-service/dsav_watcher.py`.
- `AUTO_VALIDATION_PROVIDER = "AutoValidation"`, all four Cypher writer constants, `get_auto_validation_config`, and `maxAttempts` were traced to source/documentation.
- `llm/structure_rules.json` parsed with `['version', 'mappings', 'inputBindings']`.
- D5 annotation and measured totals `3.427`, `2.801`, and `2.679` are present in the Phase 39 summary.
- The `ontology/dg-shapes.ttl` diff contains zero changed non-comment lines.
- No source validation code or SHACL constraints were modified.

Pre-existing unrelated worktree changes were preserved. Work stopped before v12.0 artifacts or phase work.
