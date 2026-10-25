---
phase: 1205-security-and-tenancy-release-gate
fixed_at: 2026-09-30T08:00:00Z
review_path: .planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md
iteration: 4
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 1205: Code Review Fix Report (iteration 4)

**Fixed at:** 2026-09-30T08:00:00Z
**Source review:** `.planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md` (final delta review, with the orchestrator corrections applied)
**Iteration:** 4

**Summary:**
- Findings in scope: 6 (CR-01, CR-02, WR-01, WR-02, WR-04, WR-05; WR-03 is a note, not a defect)
- Fixed: 6
- Skipped: 0
- Also handled from the fix direction: IN-01 (verified, no defect), IN-03, and the string-escape gap the reviewer did not reach.

Work was done in the main checkout as the single writer, as directed, not in a worktree. Commits are per finding (one commit covers WR-02, WR-04 and WR-05 because their tests and catalog edit cannot be green separately).

## Approach

The earlier rounds were bypassed because the read-profile expression handler was a token walk that skipped anything it did not recognise. Both critical findings were instances of that one flaw, so this iteration replaced the handler instead of adding exceptions:

- Expressions are parsed with an operand/operator grammar. Two operands can never sit side by side, so `a IS Rule`, `(a) (b)` and a smuggled `WITH` are errors rather than skipped words.
- A `(` inside an expression is only a grouping or a function call. A relationship dash after an operand (`--`, `-[`, `<-` followed by `-` or `[`, whatever the whitespace) is rejected, so pattern predicates and pattern expressions cannot be written at all.
- Every node pattern goes through one reader, `read_node_shape`, used by MATCH, OPTIONAL MATCH, MERGE and both ends of a relationship. It accepts only `( [var] [:Label]* [{literal map}] )`.
- `_audit` runs after a parse that found no violation. Every `(` token must be classified (node, call or group) and every node pattern the reader processed must be proven scoped. Otherwise the query is invalid.

## Fixed Issues

### CR-01: `STARTS`/`ENDS` before `WITH` recognised by token text, not role

**Files modified:** `data-service/cypher_allowlist.py`, `data-service/tests/test_cypher_allowlist.py`
**Commit:** 4f21d60
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `STARTS WITH` and `ENDS WITH` are consumed as one operator in `parse_operator`, only after a complete operand. A `WITH` token anywhere else is always `forbidden_clause`, and no exemption depends on the text of the previous token. Tests cover a property named starts or ends, a label, a variable, case variants (`a.STARTS WITH`, `a.eNdS wItH`), `WITH` after other operand kinds, STARTS/ENDS without WITH, and the reviewer's exact reproduction, plus the real operator still parsing (including `a.starts STARTS WITH 'x'`). The write profile is covered too.

### CR-02: Neo4j 5 `IS` label syntax bypasses node-pattern scope checking

**Files modified:** `data-service/cypher_allowlist.py`, `data-service/tests/test_cypher_allowlist.py`
**Commit:** 4f21d60
**Status:** fixed: requires human verification (logic change)
**Applied fix:** Chose rejection. No reference example needs a pattern predicate: `cypher_template.txt`, `llm/cypher_catalog.json`, the n8n graph-query prompt and the tests teach the `OPTIONAL MATCH ... WHERE s IS NULL` form instead. The `EXISTS { }` text in `cypher_template.txt` is for data-service's own internal reads, and the template now says so. Two existing tests that accepted `NOT (r)-[:SUPERSEDED_BY]->(s)` were changed to expect rejection. Tests cover IS syntax in MATCH, OPTIONAL MATCH, relationship brackets, WHERE, RETURN and function arguments, label expressions (`|`, `&`, `!`, `%`), inline WHERE, parameter maps and path quantifiers. A 19-shape by 14-slot matrix checks pattern predicates and expressions in every expression position, and a 21-snippet by 20-slot matrix checks hostile node patterns.

**Structural invariant tests:**
- Every accepted legit query is checked against the audit, using an independent token-level oracle (parenthesis spans, relationship-adjacent parens must be classified as node patterns).
- A seeded mutation fuzz (6000 mutations per run) asserts the same invariant for every accepted mutation. A one-off larger run (180000 mutations, 6204 accepted) found 0 violations.
- Direct unit tests prove `_audit` fails an unclassified paren and an unscoped node pattern.

### WR-01: Unbounded parser recursion raises `RecursionError`

**Files modified:** `data-service/cypher_allowlist.py`, `data-service/app.py`, `data-service/tests/test_cypher_allowlist.py`, `data-service/tests/test_mcp_project_scope.py`
**Commit:** fef4fc1
**Applied fix:** `MAX_NESTING_DEPTH = 64` raises an `unsupported_syntax` violation. `_run` also catches `RecursionError` and any unexpected exception and returns a violation, and text over `MAX_QUERY_CHARS` (200000) is refused. Tests use 1000 levels of parentheses, lists, maps, calls, CASE and index chains, and check the ceiling is exact. `/mcp neo4j_query` now wraps the allowlist call and answers a structured 400 (`QUERY_NOT_PROJECT_SCOPED`) on any exception. Route-level tests confirm: a 1000-level `/mcp` query gives a 400, a raised allowlist exception gives a 400 with no traceback, `/context/generate-cypher` with 1000-level model output gives a 200 with a violation, and a raised exception from the generator gives a structured 502, never a 500.

### WR-02: model-facing examples carry `--` narration and fail the allowlist

**Files modified:** `llm/cypher_catalog.json`, `cypher_template.txt`, `data-service/tests/test_cypher_allowlist.py`
**Commit:** 1b3f4d9
**Applied fix:** The `--` header lines moved out of `worked_example` into a new `narration` field on each shape (the literal `project: 'demo-project'` in one note was reworded to `$project`). `cypher_template.txt` had no `--` lines. Tests run every catalog `cypher_template` and `worked_example` verbatim, with no header stripping, through the write profile (12 of 12 pass), run the instantiated `cypher_template.txt` block through it, run every worked example through the full ingest validator, and assert no model-facing Cypher string contains a comment, narration or interior `;`.

### WR-04: read allowlist accepts a trailing `;`, then n8n appends ` LIMIT 50`

**Files modified:** `data-service/cypher_allowlist.py`, `n8n/workflows/graph-query-mcp.json`, `data-service/tests/test_cypher_allowlist.py`, `data-service/tests/test_n8n_workflow_boundary.py`
**Commit:** 1b3f4d9
**Applied fix:** The read profile rejects every `;`, trailing included. The n8n "Parse Cypher" node strips trailing whitespace and `;` and appends ` LIMIT 50` only when the statement does not already end in `LIMIT <number or $param>` (so a `.limit` property or a LIMIT inside a string no longer suppresses it). The node code is executed under Node in tests (10 cases), and the graph-query prompt now names pattern predicates, IS/&/|/! syntax, semicolons, backslashes and doubled quotes.

### WR-05: `stripStatementSeparators` tracks single quotes only

**Files modified:** `data-service/cypher_allowlist.py`, `n8n/workflows/rules-to-metagraph.json`, `cypher_template.txt`, `llm/cypher_catalog.json`, `data-service/tests/test_cypher_allowlist.py`, `data-service/tests/test_n8n_workflow_boundary.py`
**Commit:** 1b3f4d9
**Applied fix:** The write profile now refuses a `;` anywhere except as the very last token, so the scanner is not needed and was removed from "Prepare Graph Payload". The node only drops one trailing `;` (`dropTrailingSemicolon`), which needs no quoting rules. A `;` inside a single- or double-quoted string is content and survives (tested under Node). The `range` catalog example had an interior `;` between its two rules and lost it (the allowlist treats it identically). The ingest prompt and `cypher_template.txt` tell the model to emit one chained statement.

## Also handled from the fix direction

### IN-03: newer Cypher clause words

**Commit:** 4f21d60 (code), fef4fc1 (tests)
FOR, LET, FILTER, NEXT, OFFSET and CYPHER were added to `FORBIDDEN_CLAUSE_WORDS`, and tests assert they are forbidden as a clause, inside an expression and in the write profile.

### Escapes (lexer versus Neo4j, not reached by the reviewer)

**Commit:** 5876c67
Any string literal containing a backslash is rejected in both profiles (covers escaped quotes, `\n`, `\u`, `\U` and `\x` forms), as are doubled quotes (`'a''b'`) and DEL inside a string. A backslash outside a string was already rejected. The catalog, reference corpus and all 50 recorded cassettes contain no backslash, so nothing legitimate is lost. Raw newlines inside strings stay allowed (Neo4j allows them too) and are tested. The n8n ingest prompt, the graph-query prompt and `cypher_template.txt` now say so.

### IN-01: WR-24 invite path lock analysis (verified, no defect)

**Commit:** 4edcda5 (tests only)
`auth._STORE_LOCK` is a `threading.RLock`, so holding it across `get_role` + `set_membership` (each takes it again) cannot deadlock. `_THROTTLE_LOCK` is a plain `Lock`, but each throttle function takes it exactly once, none calls another, and none touches the membership store, so it is never nested or ordered against `_STORE_LOCK`. The invite path acquires the two locks only sequentially. No code change. Three tests pin this: the lock type, the once-per-call shape, and six concurrent invites for one account converging on the highest role within a timeout.

### Differential probe test

**Commit:** 2a379e1
`data-service/tests/test_cypher_allowlist_probe.py` (marker `neo4j_probe`, skipped unless `DG_ALLOWLIST_PROBE_BOLT` is set). It refuses the compose bolt port 7687, non-loopback hosts and non-empty databases.

### Security boundary spec

**Commit:** 1c367d1
Prose bullet added to `spec/SECURITY-BOUNDARY.md` describing the iteration-4 grammar. No machine-checked block changed and `test_security_boundary_spec.py` passes.

## Verification

- **Host** (`test_cypher_allowlist`, `test_cypher_project_scope`, `test_dg_context`, `test_n8n_workflow_boundary`, `test_review_fix_1205`, plus `test_mcp_project_scope` and the probe): 1045 passed, 17 skipped, 4 failed. The 4 failures are the known `test_dg_context.py` endpoint tests (the `neo4j` hostname resolves only inside compose).
- **Differential check against a real engine** (disposable `neo4j:5.26`, `NEO4J_AUTH=none`, bound to 127.0.0.1:17687, two synthetic tenants P1/P2, every P2 string carrying a marker, plus cross-tenant edges):
  - 168 read queries accepted by the allowlist: 112 executed, 56 refused by the engine for syntax or missing parameters, 100 rows inspected (scalars, maps, lists, nodes, relationships), 0 foreign markers.
  - One-off larger run over accepted fuzz mutations: 2236 distinct accepted queries, 1341 executed, 895 engine-refused, 678 rows, 0 leaks.
  - Control: all 6 of the reviewer's attack queries (CR-01 `starts`/`ends`, CR-02 `IS`, two pattern-predicate oracles) return foreign data or an oracle row when run raw, and all 6 are rejected by the allowlist.
  - 14 write examples (6 catalog templates, 6 worked examples, the `cypher_template.txt` block, `HEIGHT_RULE`) each passed the write allowlist and ran through `EXPLAIN`; a count of 9 nodes before and after proves EXPLAIN wrote nothing.
  - The container was removed (`docker rm -f dg-allowlist-probe`; `docker ps -a` shows none) and the live `neo4j` container was never touched.
- **Container** (`docker compose build data-service`, `up -d --no-deps data-service`, `pytest -q -p no:cacheprovider --ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`): 3875 passed, 52 skipped, 8 deselected, 12 failed. The 12 are the known environmental set: `test_repeat_sweep` (`/tools/de01/report_schema.json` not in the image), ten `test_cq3_attribute_of.py` tests (unmounted fixtures), and `test_evidence_contract.py::test_never_raises_on_garbage_input` (recursion fuzz in `evidence_contract`, not the allowlist). I confirmed the causes for the first two groups by reading the errors; the evidence-contract one is the recursion fuzz named in the baseline. The container also imports the new allowlist (CR-01/CR-02 repros give `forbidden_clause` and `unsupported_syntax`).
- **Live n8n (2.4.8):** both workflows were imported with their live ids preserved (`a1b2c3d4-e5f6-7890-abcd-ef1234567890` rules, `b2c3d4e5-f6a7-8901-bcde-f12345678901` graph query), published with `n8n publish:workflow`, and n8n restarted. Confirmed by node names and boolean checks only: both `active` true, `activeVersionId == versionId`, `Verify Relay Token` present, `dropTrailingSemicolon` present and `stripStatementSeparators` absent in rules "Prepare Graph Payload", the new prompt text present in both, the LIMIT guard present in "Parse Cypher". The rules workflow repo JSON has no `id`, so a temporary copy with the id set was imported from the scratchpad; the repo file is unchanged in that respect. Two harmless copies (`live-rules.json`, `live-graph.json`) remain in n8n's `/tmp`; its user cannot delete them (same as the previous iteration).

## Behaviour changes to be aware of

- Pattern predicates and pattern expressions are no longer accepted in a read query. `WHERE NOT (a)-[:R]->(b)` must be written as `OPTIONAL MATCH (a)-[:R]->(b:Label {project: $project}) WHERE b IS NULL`. Two tests that asserted the old behaviour were changed.
- A `-` followed by `-` or `[` after any operand is refused, so `a - -1` is rejected (`a - 1` and `a < -1` still parse).
- Variables named like Cypher 25 clause words (`for`, `let`, `filter`, `next`, `offset`) are refused as operands.
- The model sees a new `narration` field on each catalog shape; recorded LLM cassettes are keyed on prompts that embed the catalog, so a live re-record would produce new keys. The prompt-freeze test was excluded from the container run as before and was not run.
- The allowlist now refuses any `;` in a read query and any non-final `;` in a write statement. The first-attempt pass rate of a model that habitually emits `;` between statements will drop until the retry feedback teaches it; the catalog and template no longer show one.

## Not addressed (unchanged from the review's "not reached" list)

- The nginx regex location on a live nginx, parsing of `DG_TRUSTED_PROXIES`, and authorisation of the caller-supplied `project` on `/mcp neo4j_query`.
- IN-02 (`find_foreign_project_entities` ignores scalar values): not requested, and the allowlist now closes the paths that returned scalars from foreign nodes.

---

_Fixed: 2026-09-30T08:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 4_
