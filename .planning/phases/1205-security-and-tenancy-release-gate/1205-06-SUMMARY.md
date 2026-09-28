---
phase: 1205-security-and-tenancy-release-gate
plan: "06"
subsystem: api
tags: [cypher, tenancy, security-validator, neo4j, llm, regex]

# Dependency graph
requires:
  - phase: 1205-05
    provides: "n8n graph-query prompt already restates the 1205-06 scope rule; Run Cypher (MCP) sends parameters.project unconditionally"
provides:
  - "SHARED_VOCABULARY_LABELS frozenset (Class/DatatypeProperty/ObjectProperty/Builtin/Literal)"
  - "check_query_project_scope(cypher) -- static inline-map project-scope prover for graph_query Cypher (missing_project_scope, anonymous_node_pattern, project_literal, forbidden_clause)"
  - "check_foreign_project_literals(cypher, project) -- rule_ingest/rule_edit foreign literal detector"
  - "find_cross_project_key_collisions(cypher, project, session=None) -- bound-parameter Rule_Id/Atom_Id collision finder, fails closed on schema v4's id-only keys"
  - "find_foreign_project_entities(values, project) -- duck-typed recursive result-side counter for /mcp"
  - "validate_cypher(cypher, request_type, *, project=None) and generate_validated_cypher(prompt, request_type, max_retries=2, *, project=None) -- backwards-compatible project kwarg wiring both new checks into the existing retry loop"
affects: [1205-14, 1205-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Node-pattern regex requires the closing ')' immediately after the optional '{...}' map, so a function call's argument list (count(n), collect(DISTINCT n), toLower(r.name)) never false-matches as a node pattern"
    - "Only a variable's FIRST occurrence in text order is checked for inline {project: $project} scoping; later bare references to the same variable (inside function calls, RETURN clauses) are skipped once seen"
    - "String-literal stripping runs on a de-quoted copy of the Cypher for forbidden-clause/node-pattern checks, but on the ORIGINAL text for project_literal/foreign_project_literal (which need the quoted literal itself)"
    - "find_cross_project_key_collisions/find_foreign_project_entities never name the other project in a violation message -- anti-enumeration house style (T-39-06 precedent), same as CAPTURE_PROJECT_MISMATCH"

key-files:
  created:
    - data-service/tests/test_cypher_project_scope.py
  modified:
    - data-service/dg_context.py

key-decisions:
  - "D-03/T-1205-06: the scope guard never fails open -- an anonymous or unlabeled tenant-owned node pattern without an inline {project: $project} map is always a violation (anonymous_node_pattern/missing_project_scope), even when a WHERE predicate appears to constrain it (WHERE can be widened with OR)"
  - "D-08: check_query_project_scope wires into validate_cypher only for graph_query, and check_foreign_project_literals only for rule_ingest/rule_edit -- both gated on the new project kwarg being non-None, so every existing call site (which never passes project) sees byte-identical behavior to before this plan"
  - "Shared vocabulary labels (Class/DatatypeProperty/ObjectProperty/Builtin/Literal) are exempt from inline project scoping when ALL of a node's labels are in that set -- documented residual, T-1205-06-04, to be recorded in spec/SECURITY-BOUNDARY.md by 1205-16"
  - "find_cross_project_key_collisions fails closed on schema v4's id-only Rule/Atom MERGE keys (no project qualification exists yet) rather than allowing silent cross-project overwrite -- transferred risk per T-1205-06-06, flagged to the owner as a future Schema Change Propagation item"

requirements-completed: []  # ALGN12-17 is a phase-level gate closed across 1205-06/1205-14; this plan adds the checks only -- wiring into /context/generate-cypher and /mcp happens in 1205-14

coverage:
  - id: D1
    description: "check_query_project_scope() statically proves or rejects project-scoping for graph_query Cypher: missing_project_scope, anonymous_node_pattern, project_literal, and forbidden_clause (CALL/UNION/LOAD CSV/FOREACH/USE/apoc./db.) all covered with positive and negative cases, including the WHERE-predicate-bypass and function-call-argument false-positive traps"
    requirement: ALGN12-17
    verification:
      - kind: unit
        ref: "data-service/tests/test_cypher_project_scope.py::TestScopeValidatorValid, TestScopeValidatorMissingProjectScope, TestScopeValidatorAnonymousNodePattern, TestScopeValidatorProjectLiteral, TestScopeValidatorForbiddenClause, TestScopeValidatorFunctionCallsSafe"
        status: pass
    human_judgment: false
  - id: D2
    description: "validate_cypher/generate_validated_cypher accept a keyword-only project param that is fully backwards compatible (omitted, behavior is byte-identical to pre-1205-06) and wires check_query_project_scope (graph_query) / check_foreign_project_literals (rule_ingest, rule_edit) when supplied; project is passed through every retry attempt"
    requirement: ALGN12-17
    verification:
      - kind: unit
        ref: "data-service/tests/test_cypher_project_scope.py::TestValidateCypherGraphQueryProjectWiring, TestValidateCypherRuleIngestProjectWiring, TestGenerateValidatedCypherProjectWiring"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_context.py -k \"validate or generate\" (6/6, unchanged)"
        status: pass
    human_judgment: false
  - id: D3
    description: "check_foreign_project_literals (rule_ingest/rule_edit foreign literal detection), find_cross_project_key_collisions (bound-parameter Rule_Id/Atom_Id collision finder, fails closed, never string-interpolates ids, never names the other project), and find_foreign_project_entities (duck-typed recursive result-side counter over nodes/relationships/paths/lists/dicts, shared-vocabulary exempt, fails closed on a missing project property) are pure, injectable, and tested with fake sessions/fake graph-value classes -- no live Neo4j needed"
    requirement: ALGN12-17
    verification:
      - kind: unit
        ref: "data-service/tests/test_cypher_project_scope.py::TestCheckForeignProjectLiterals, TestFindCrossProjectKeyCollisions, TestFindForeignProjectEntities"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 06: Cypher project-scope validator for graph_query and rule ingest Summary

**A deterministic static validator proves LLM-generated graph_query Cypher is project-scoped via inline `{project: $project}` maps (rejecting WHERE-predicate bypasses, literal project values, and CALL/UNION/LOAD CSV/FOREACH/USE/apoc./db. escape hatches), plus rule-ingest foreign-literal detection, a fail-closed Rule/Atom key-collision finder, and a result-side foreign-entity counter -- all pure functions ready for 1205-14's route wiring.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-28T22:14:39Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- `check_query_project_scope(cypher)` statically proves whether graph_query Cypher is project-scoped: every tenant-owned or unlabeled node pattern must carry an inline `{project: $project}` map at its FIRST occurrence in text order (a `WHERE r.project = $project OR true` bypass does not count); anonymous patterns need the same inline map unless the pattern's entire label set is shared vocabulary (`Class`/`DatatypeProperty`/`ObjectProperty`/`Builtin`/`Literal`); any literal `project` value (inline map or `.project` comparison/assignment) is rejected outright; `CALL`, `UNION`, `LOAD CSV`, `FOREACH`, `USE`, `apoc.`, and `db.` are rejected as escape hatches, matched outside string literals only.
- Function-call parentheses (`count(n)`, `collect(DISTINCT n)`, `toLower(r.name)`) never produce false violations -- the node-pattern regex requires the closing `)` directly after the optional `{...}` map, so none of these shapes match as a node pattern in the first place, and even where a bare `(var)` reference recurs (e.g. `count(r)` after `r` was already correctly scoped), only the variable's first text occurrence is checked.
- `validate_cypher`/`generate_validated_cypher` gained a keyword-only `project: str | None = None` parameter, fully backwards compatible: every existing call site (which never passes `project`) sees byte-identical behavior, confirmed by the unchanged `test_dg_context.py -k "validate or generate"` suite (6/6 passing). When `project` is supplied, `graph_query` requests run `check_query_project_scope`, and `rule_ingest`/`rule_edit` requests run `check_foreign_project_literals`; `generate_validated_cypher` threads `project` through every retry attempt, so corrective feedback teaches the model the exact scoping rule it violated.
- `check_foreign_project_literals(cypher, project)` flags any quoted `project` literal (inline map key or `.project` assignment/comparison) that differs from the relayed project -- one violation per distinct offending literal; a literal matching the current project is not flagged.
- `find_cross_project_key_collisions(cypher, project, session=None)` extracts every `Rule_Id`/`Atom_Id` a rule-ingest/edit Cypher would `MERGE`, and (via one bound-parameter read query, never string-interpolated) reports any key already owned by a different project as `cross_project_key_collision` -- fails closed on schema v4's id-only MERGE keys rather than allowing silent cross-project overwrite. Returns `[]` without touching Neo4j when the Cypher merges no `Rule`/`Atom` key at all. The violation message names the offending key but never the other project (anti-enumeration house style, `CAPTURE_PROJECT_MISMATCH` precedent).
- `find_foreign_project_entities(values, project)` recursively walks arbitrary neo4j graph-value results (duck-typed nodes via `.labels`, relationships via `.type` + mapping access, paths via `.nodes`/`.relationships`, and any nesting of lists/tuples/sets/dicts) and counts entities whose `project` property is missing (fails closed) or differs from the bound project, skipping nodes whose entire label set is shared vocabulary.
- New `data-service/tests/test_cypher_project_scope.py` (42 tests) covers every violation code with positive and negative cases, the backward-compatibility contract, the retry-loop project pass-through, and all four Task 2 functions with fake sessions/fake graph-value classes -- zero live Neo4j required.

## Task Commits

Each task was committed atomically:

1. **Task 1: Static project-scope validator for graph_query and its wiring into validate_cypher** - `b1b847f` (feat)
2. **Task 2: Rule-ingest foreign-literal and key-collision checks, and the result-side foreign-entity counter** - `8600bb3` (feat)

## Files Created/Modified
- `data-service/dg_context.py` - `SHARED_VOCABULARY_LABELS`, `check_query_project_scope`, `check_foreign_project_literals`, `find_cross_project_key_collisions`, `find_foreign_project_entities`; `project` kwarg on `validate_cypher`/`generate_validated_cypher`, wired for `graph_query` (Task 1) and `rule_ingest`/`rule_edit` (Task 2)
- `data-service/tests/test_cypher_project_scope.py` - new: 42 tests, one per behavior bullet plus the backward-compatibility and wiring assertions

## Decisions Made
- Placed all new project-scope code in one contiguous section immediately before `validate_cypher` in `dg_context.py`, so the file's existing "schema validator → retry loop" structure is preserved and the new checks read as a self-contained unit.
- Reused the same `_PROJECT_MAP_LITERAL_PATTERN`/`_PROJECT_DOT_LITERAL_PATTERN` regex pair for both `project_literal` (graph_query, any literal is a violation) and `foreign_project_literal` (rule_ingest/edit, only a literal that disagrees with the bound project is a violation) -- the two functions apply different accept/reject logic to the same extraction.
- Committed the two tasks separately even though both touch the same two files: Task 1's commit contains only `check_query_project_scope` + the `graph_query` wiring branch + the `project` kwarg signatures + the matching test classes; Task 2's commit adds `check_foreign_project_literals`/`find_cross_project_key_collisions`/`find_foreign_project_entities` + the `rule_ingest`/`rule_edit` wiring branch + their test classes. Verified both intermediate states independently (25/25 tests green after Task 1, 42/42 after Task 2) before each commit, matching the plan's per-task commit protocol despite the single-pass implementation.

## Deviations from Plan
None - plan executed exactly as written. Both tasks' `<behavior>` bullets and `<acceptance_criteria>` are satisfied by direct test coverage; no Rule 1-3 auto-fixes and no Rule 4 architectural questions arose.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. This plan adds pure functions only; wiring into live routes (and any resulting environment/config needs) is 1205-14's scope.

## Next Phase Readiness
- `check_query_project_scope`, `check_foreign_project_literals`, `find_cross_project_key_collisions`, and `find_foreign_project_entities` are all pure/injectable and ready for 1205-14 to wire into `/context/generate-cypher` (`generate_validated_cypher(..., project=payload.project)`) and `/mcp` (`check_query_project_scope` + `find_foreign_project_entities` at execution time).
- The shared-vocabulary exemption (`SHARED_VOCABULARY_LABELS`) still needs to be recorded as an accepted low-severity residual in `spec/SECURITY-BOUNDARY.md`, per this plan's `must_haves` -- flagged for 1205-16.
- Schema v4's id-only Rule/Atom MERGE keys remain a transferred risk (T-1205-06-06): `find_cross_project_key_collisions` fails closed on the collision today, but project-qualified keys are a separate Schema Change Propagation item for the owner to schedule.
- No blockers for downstream plans in this phase.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created/modified files found on disk (`data-service/dg_context.py`, `data-service/tests/test_cypher_project_scope.py`, this SUMMARY.md). Both task commits (`b1b847f`, `8600bb3`) confirmed present in git log.
