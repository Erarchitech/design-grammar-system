---
phase: 07-schema-foundation
fixed_at: 2026-06-23T11:45:00Z
review_path: .planning/milestones/v3.0-phases/07-schema-foundation/07-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 4
skipped: 1
status: partial
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-06-23T11:45:00Z
**Source review:** .planning/milestones/v3.0-phases/07-schema-foundation/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 Critical + 4 Warnings; `fix_scope: critical_warning` excludes the 4 Info items)
- Fixed: 4
- Skipped: 1

## Fixed Issues

### CR-01: `Neo4jRuleRepository.PopulateVariables` can silently merge distinct rules' atoms when `?varName` collides across rules — cross-project `Var` leak via unconstrained `ARG` target

**Files modified:** `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`
**Commit:** `6b13c38`
**Applied fix:** Added `WHERE av IS NULL OR av.project IS NULL OR av.project = $project` to `AtomsQuery`, immediately after the `OPTIONAL MATCH (a)-[arg:ARG]->(av)` clause. Previously only the `Atom` (`a`) node was constrained by `project`; the `ARG` target (`av`, the `Var`/`Literal` node) was unconstrained, so a cross-project `ARG` relationship could leak a foreign project's `Var` name into `PopulateVariables`'s `HashSet<string>` with no error or filtering. This closes the read-side counterpart to the write-side fix already applied by `migrations/2026-06-23_var_project_merge_key.cypher`. Verified via `dotnet build` (0 errors/warnings) and `dotnet test --filter Neo4jRuleRepository` (3/3 passing).

### WR-01: `argLabels` with both `Var` and `Literal` labels (or unexpected/missing labels) silently picked `Var` without validating exclusivity

**Files modified:** `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`
**Commit:** `076fef3`
**Applied fix:** Added an explicit `isLiteral` check alongside the existing `isVariable` check in `LoadAtomsAsync`; when `isVariable == isLiteral` (both true — malformed dual-labeled node — or both false — neither label present), the arg is now skipped via early `return` instead of silently falling through to be misclassified as a `Literal`. Matches the fix exactly as proposed in REVIEW.md. Verified via `dotnet build` (0 errors/warnings) and `dotnet test --filter Neo4jRuleRepository` (3/3 passing).

### WR-02: New `DefState`/`ObjectInstance`/`ObjectState` model classes have zero call sites anywhere in the reviewed code or the rest of the C# codebase

**Files modified:** `DG/src/DG.Core/Models/DefState.cs`, `DG/src/DG.Core/Models/ObjectInstance.cs`, `DG/src/DG.Core/Models/ObjectState.cs`
**Commit:** `24b14f4`
**Applied fix:** Added a `/// <summary>` doc comment to each of the three classes, mirroring the existing comment style in `DesignStateIdGenerator.cs`, explicitly stating each is unused scaffolding for the v3.0 DesignState hierarchy pending Phase 9/11 wiring, with a `<see cref>` back-reference to `DesignStateIdGenerator`. Verified via `dotnet build` (0 errors/warnings).

### WR-03: `Variable.InferredDatatype` is read by 5 downstream Grasshopper call sites but never populated by any code in this phase

**Files modified:** `DG/src/DG.Core/Models/Variable.cs`
**Commit:** `c1e8c38`
**Applied fix:** Confirmed via repo-wide grep that `InferredDatatype` has exactly one write site (the `init`-only property declaration itself) and five read sites, all in `DG.Grasshopper` — `GhCastingHelpers.cs:67`, `MetagraphComponent.cs:205`, `RuleDeconstructComponent.cs:97/111/147`. No other code path in the repository sets this field, and `VariableTypeInferrer` (the only inference logic introduced this phase) only computes `VariableKind`, never a datatype. Wiring real datatype inference would be a new feature requiring product decisions (e.g. which `Atom.Args[].Datatype` to attribute per variable name) and was judged out of scope for a fix-pass. Per REVIEW.md's second fix option, documented the gap explicitly via an XML doc comment on the property noting it is always null from the Neo4j-backed pipeline as of Phase 7. Verified via `dotnet build` (0 errors/warnings).

## Skipped Issues

### WR-04: n8n `Build LLM Prompt` function node duplicates the Var-merge-key schema text across two independent string blocks that must stay manually in sync

**File:** `n8n/workflows/rules-to-metagraph.json:75`
**Reason:** REVIEW.md's own Fix section explicitly states this is "Out of scope to refactor in this phase" and the only concrete suggestion is to "consider adding a lightweight test/lint step" — a net-new tooling script, not a patch to existing code. The duplicated schema text lives inside a single large hand-escaped JS string embedded in a JSON workflow file (`functionCode`), with no natural seam to add an inline comment without either breaking JSON validity or touching functional logic the reviewer flagged as risky to refactor here. Given the fix itself is marked out-of-scope by the reviewer, no code change was applied; flagging for a future phase to add the suggested drift-detection lint script (e.g. asserting the `Var key:` line in the n8n JSON, `cypher_template.txt`, and `dataset_schema.json` all mention `project` consistently).
**Original issue:** The fix in this phase updates both the `fewShot` few-shot example and the `NODE KEY PROPERTIES` text independently inside one hand-maintained JS string blob with no shared source of truth, mirroring the CLAUDE.md "Schema Change Propagation" manual-discipline risk already called out for `cypher_template.txt` / `dataset_schema.json` / this n8n prompt.

---

_Fixed: 2026-06-23T11:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
