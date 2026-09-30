---
tags: [debugging, security, cypher, llm, phase-1205]
date: 2026-09-30
---

# Blocklist checks over LLM-written Cypher were bypassed three times

## Symptom

The Phase 1205 project-scope guard for LLM-written Cypher (1205-06, in `dg_context.py`) passed its tests, but independent code reviews kept finding queries it accepted that read or wrote another project's data:

- **Iteration 1 (CR-03/CR-04):** each of these supplied a fake scope proof or slipped past the checks: backticked variables, a `/* (n {project:$project}) */` comment, nested braces, a `subproject:` key, a double-quoted `Rule_Id`, a variable-less `MERGE`, and `SET r['project']`.
- **Iteration 2:** a `WITH` clause re-binding a variable after scoping it, Unicode identifiers skipped by an ASCII tokenizer, `'R_'+'X'` key concatenation, unlabeled `STARTS WITH` matches, and `MATCH (n) DETACH DELETE n`. With the last one, a single prompt-injected ingest could wipe every tenant.
- **Iteration 3 (first allowlist):** the final deep review found two more.
  - An exemption for `WITH` keyed on the preceding token's text (`STARTS`/`ENDS`) let a real `WITH` reset scope.
  - Neo4j 5 `IS` label syntax skipped the node-shape reader. Both were confirmed leaking against a disposable Neo4j.

## Root cause

Every version treated unrecognised syntax as neutral: skip it and keep scanning. Each fix closed only the construct just reported. A result-side guard (`find_foreign_project_entities`) inspected only node, relationship and path objects, so scalar and map returns leaked unseen.

## Fix

Replace pattern matching with a real grammar that treats any unclassified token as a violation. See [[knowledge/decisions/LLM-written Cypher is guarded by a grammar allowlist, not a blocklist|decision]]. Also add a differential probe that *executes* accepted queries on a seeded two-tenant engine and looks for foreign markers in the results, rather than relying on static reasoning alone.

## Lessons

- A security check over attacker-influenced code must fail closed: unknown means reject.
- Tests written by the same author as the checker confirm the author's model of the language, not the language. Independent review and execution against the real engine found what unit tests could not.
- Wait for Neo4j readiness with `cypher-shell "RETURN 1"`, not a TCP port check. The Bolt port opens several seconds before queries succeed.
