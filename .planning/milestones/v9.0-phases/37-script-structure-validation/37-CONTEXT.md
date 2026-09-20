# Phase 37 Context: Script Structure Validation MVP

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** SVAL-01..03
**Depends on:** Phase 36 (published Computgraph to validate).

## What this phase is

Design Grammars applied to the *structure of the Grasshopper script itself*: deterministic Cypher checks over the published Computgraph, Design-Rule-mapped structural requirements, and a read-only LLM consult endpoint. This is the v9.0 endpoint of the pipeline and the seam that v10 Script Intelligence (generate/edit parts of scripts, full consulting assistant) builds on — see `.planning/milestones/v10.0-SEED.md`.

## Decided

1. **`data-service/cg_structure_checks.py`** + `POST /computgraph/validate` `{project, definitionId?}`:
   Deterministic, LLM-free checks, each returning `{checkId, severity, message, entities[]}`:
   - convention compliance (names parse; normalized variants like `Emr` flagged info-level)
   - orphan `Pattern` (no `HAS_PATTERN` from any Procedure)
   - `Procedure` without any `Interface`
   - `Parameter` without `dataType`
   - dangling `PARAM_LINK` (link to an Interface outside the parameter's procedure chain)
   - `Algorithm` without `Procedure`; `Object` without `HAS_BEHAVIOR` chain
2. **Rule-mapped structural checks:** a declarative mapping shape (JSON, versioned alongside `llm/cypher_catalog.json`) linking a Metagraph `Rule` (by `Rule_Id`) to structural requirements over the Computgraph, e.g.:
   - `requiresProcedure`: name pattern must exist under the Object's Algorithm ("a Frame algorithm must contain a *Truss* procedure")
   - `requiresParameter`: a parameter with given kind/dataType must exist ("height must be a VariableParam")
   - `forbidsOrphan`, `requiresInterface` variants
   Evaluated via parameterized Cypher; report pass/fail per rule with the satisfying/offending entities. This is intentionally a small vocabulary — v10 grows it; the mapping file format is the extension point.
3. **`POST /computgraph/consult`** `{project, definitionId, question}`: assembles the published Computgraph subgraph (via `dg_context.py`) + the question → LLM gateway → answer that cites entity names present in the graph. Strictly read-only; no Cypher execution from LLM output in this phase. This endpoint is the consulting-assistant seed.
4. **Report surface:** validation report JSON consumable by ui-v2 (Graph screen panel) and printable to a GH panel via the bridge (`get_preview_status`-style command or plain HTTP from a small component — decide in planning; lowest-cost option wins, this is MVP).

## Constraints

- SVAL-01/02 checks are deterministic and reproducible — no LLM in the validate path; only `/consult` calls the gateway.
- Checks operate on the *published* Computgraph (Neo4j), not the live canvas — canvas freshness is the architect's responsibility (re-publish first); the report carries `publishedAt` so staleness is visible.
- Rule mapping must not require ontology changes — it references existing `Rule` nodes by id and Computgraph entities by label/property.
- Consult answers must be grounded: prompt instructs citation of entity names; response post-check verifies cited names exist in the subgraph (flag, don't block, on miss).

## Open for planning

- Rule-mapping file location and shape (`llm/structure_rules.json` vs per-project Neo4j nodes — leaning file-first for MVP, graph-native in v10).
- Severity taxonomy alignment with the existing validation report conventions (ValidGraph runs).
- Whether structure validation results are persisted (as a lightweight `Run`-like record) or ephemeral (leaning ephemeral for MVP; persistence when v10 workflows need history).

## Verification sketch

Remove an Interface tag from Frame, re-publish → `/computgraph/validate` flags Procedure-without-Interface naming `11_Proc`; rule mapped to `requiresProcedure: *Footer*` passes on full Frame, fails on a copy published without `12_Proc`; "Which parameters drive the truss height?" → `/consult` cites `11_Var_HTotal`; all validate-path responses identical across repeated runs (determinism).
