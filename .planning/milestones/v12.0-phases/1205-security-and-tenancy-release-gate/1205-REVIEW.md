---
phase: 1205-security-and-tenancy-release-gate
reviewed: 2026-09-30T06:40:32Z
depth: deep
diff_base: 382a865
files_reviewed: 11
files_reviewed_list:
  - data-service/cypher_allowlist.py
  - data-service/dg_context.py
  - data-service/app.py
  - data-service/auth.py
  - data-service/auth_routes.py
  - ui-v2/nginx.conf
  - ui-v2/entrypoint.sh
  - ui-v2/Dockerfile
  - docker-compose.yml
  - .env.example
  - cypher_template.txt
  - llm/cypher_catalog.json
  - n8n/workflows/rules-to-metagraph.json
  - n8n/workflows/graph-query-mcp.json
  - tools/security/check_env_file.py
  - spec/SECURITY-BOUNDARY.md
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 1205: Code Review Report (Final, iteration 4)

**Reviewed:** 2026-09-30T06:40:32Z
**Depth:** deep
**Files Reviewed:** 15
**Status:** issues_found

## Scope

This is the delta review requested for the final gate: only code changed **after** the iteration-2 review, i.e. the diff `382a865..HEAD`, which is the full contents of `data-service/cypher_allowlist.py` (new file, the tokenizer/parser replacing the regex-based `dg_context.py` checks), the corresponding thinning of `dg_context.py` down to thin delegating wrappers, the WR-22/23/24 changes in `app.py`/`auth.py`/`auth_routes.py`/`nginx.conf`/`entrypoint.sh`, and the prompt/template text updates in `cypher_template.txt`, `llm/cypher_catalog.json` and the two n8n workflow JSON files.

**Carried forward, not re-reviewed (per instructions):**
- CR-01/CR-02 — closed in iteration 1.
- CR-05 — accepted by design (D-07).
- The full iteration-2 accepted-by-design list (see `1205-REVIEW.iter2.md` and `1205-REVIEW.iter3.md` for detail) — not re-litigated here except where the iteration-3 fix (`cypher_allowlist.py` itself) reopens the question, which it does, hence this review's primary focus.

**Method:** `cypher_allowlist.check_read_allowlist()` / `check_write_allowlist()` were imported directly from `data-service/` on the host and executed against adversarial Cypher strings. A disposable `neo4j:5.26` container (`NEO4J_AUTH=none`, no compose, no volumes, destroyed after the session) was seeded with two synthetic tenants (`project:'pa'`, `project:'pb'`) carrying obviously-fake marker property values, and every allowlist-accepted query that looked suspicious was actually executed against it via `cypher-shell` to confirm real cross-tenant data return, not just a theoretical parse gap. Every finding below marked "reproduced" was executed this way; the exact input and exact Neo4j output are quoted.

---

## Critical Issues

### CR-01 (this review): `STARTS`/`ENDS` before `WITH` is recognised by token text, not by role — lets a smuggled top-level `WITH` clause reset pattern scope and return another project's live data

**File:** `data-service/cypher_allowlist.py:735-737` (`parse_expr`, the `WITH` special-case)

```python
if up == "WITH":
    if not (prev is not None and prev.kind == "IDENT" and prev.upper in ("STARTS", "ENDS")):
        raise self.forbidden("WITH")
```

**Issue:** This guard exists to let the legitimate `STARTS WITH` / `ENDS WITH` string operators through the expression parser without their `WITH` half being mistaken for the forbidden `WITH` clause. It decides whether the previous token was really the `STARTS`/`ENDS` *operator* by comparing the token's **uppercased text** only — it never checks that the previous token was reached via the operator path rather than via a **property-access chain** (`.starts`, `.ends`). A property literally named `starts` or `ends` (an attacker only needs the LLM, prompt-injected, to emit such a property reference — no real graph property of that name needs to exist) produces the exact same token sequence, so `a.starts WITH ...` sails through as if it were `a STARTS WITH ...`.

Once that guard passes, the tokens `WITH a` are consumed as ordinary identifiers by the fallback branch at the end of the `IDENT` case (`self.i += 1; continue`) — the parser has no notion that it just walked past a real Cypher `WITH` clause boundary. The **top-level** `while` loop that drives `parse_read()` then reaches the next `IDENT`, sees `MATCH`, and happily starts a **second** `MATCH` clause. Any node variable name reused from the first (comma-joined) `MATCH` is treated by `read_node()` as "a bare reference to an already-scoped variable" (`if var in self.node_vars: return`) and skipped entirely — but in **real Cypher semantics**, the smuggled `WITH a` (carrying forward only `a`) has already dropped `b` from scope, so the second `MATCH (b)` is a **brand-new, completely unconstrained** binding of `b` that happens to reuse the name. The allowlist gives it a pass anyway because it only tracks variable *names*, never whether a `WITH` boundary has silently discarded the previous scoping guarantee for that name.

**Reproduced input** (run through `check_read_allowlist`, zero violations returned — i.e. the allowlist **accepts** it):

```
MATCH (a:Rule {project: $project}), (b:Rule {project: $project})
WHERE a.project = $project OR a.starts WITH a
MATCH (b)
RETURN b.secret
```

Executed against the seeded Neo4j (two tenants `pa`/`pb`, `$project='pa'`), `cypher-shell` returned:

```
b.secret
"pa-secret"
"pb-SECRET-FOREIGN"
NULL
```

The middle row is `pb`'s node, whose owning project is never the caller's `pa`. This is a live cross-tenant read: exactly the invariant CR-03/CR-04 in `cypher_allowlist.py`'s own docstring claims to close ("the query can only read nodes whose `project` equals `$project`"). `ENDS WITH` reproduces identically (`a.ends WITH a`).

**Fix:** Track *why* the previous token is `STARTS`/`ENDS` structurally, not just by spelling — e.g. record on the token stream (or on a small piece of parser state) whether the previous identifier was consumed via the `.` property-access branch (`prev = nxt` at the `.` handling site) versus reached as a bare top-level identifier, and only honour the `STARTS`/`ENDS` exception when the previous token was **not** the target of a property access. Concretely: in the `.` handling branch, tag the produced identifier token (or track a `just_saw_property_access` flag) so the `WITH` check can require `prev is a bare identifier token`, not merely `prev.upper in (...)`. Add a regression test asserting `a.starts WITH b` and `a.ends WITH b` are rejected as `forbidden_clause: WITH` while `a.name STARTS WITH 'x'` (the real operator, with a literal string operand next) still parses.

---

### CR-02 (this review): Neo4j 5's `IS` label syntax is unrecognised by `read_node_shape()`, so a pattern-predicate written with `IS` instead of `:` bypasses node-pattern scope checking entirely — graph-wide property-existence oracle, unauthenticated by project

**File:** `data-service/cypher_allowlist.py:388-416` (`read_node_shape`), `797-815` (`parse_paren`)

**Issue:** `read_node_shape()` only recognises the `(var:Label)` label syntax (`while self.is_punct(":")`); Neo4j 5 also accepts `(var IS Label)` as an alternative spelling of the same thing, and Neo4j accepts it inside a WHERE pattern-predicate too. When `read_node_shape()` meets `IS` it isn't a `:`, not `{`, not `)`, so it raises `_Fatal`. Inside `parse_paren()` — the code path used for a `(` **appearing inside an expression**, i.e. a WHERE pattern-predicate — that `_Fatal` is caught:

```python
try:
    self.read_node_shape()
    is_pattern = self.at_rel_start()
except _Fatal:
    is_pattern = False
self.i = save
if is_pattern:
    self.read_pattern_chain(declare=False)
    return
self.i += 1
if self.parse_expr(closers=")") == 0: ...
```

Because the speculative parse raised, `is_pattern` is forced `False`, and the parser falls back to treating the whole `(a IS Rule)-->({...})` construct as an ordinary **grouping expression + arithmetic operators** (`-->` tokenises as `-`, `-`, `>`), never as the node/relationship pattern it actually is to Neo4j. Nothing in that fallback path ever calls `check_project_entry()` on the trailing anonymous node's property map — it is just a map literal inside a parenthesised sub-expression, which `parse_map_literal()` accepts unconditionally when `prev is None` (freshly opened paren). The result: **any pattern-predicate written with `IS` instead of `:` is invisible to every scope check in this module.**

**Reproduced inputs** (both accepted with zero violations by `check_read_allowlist`, both executed live):

```
MATCH (a:Rule {project: $project})
WHERE (a IS Rule)-->({secret:'pb-SECRET-FOREIGN'})
RETURN 'x' AS r
```
→ `r = "x"` (row returned) when the literal matches the **other** tenant's real secret value, no row when it doesn't — a working boolean oracle over the whole graph, keyed on any property the attacker chooses, with **no project constraint on the target node at all**.

Even more severe — no bound tenant node is required at either end:
```
MATCH (a:Rule {project: $project})
WHERE (IS Rule)-->({secret:'pb-atom-secret'})
RETURN 'GLOBAL-ORACLE' AS r
```
→ returns a row (`r = "GLOBAL-ORACLE"`) purely because *some* `Rule` node anywhere in the graph has an outgoing relationship to a node carrying that property value — completely independent of `$project`. This lets an attacker (or an LLM whose output was prompt-injected) binary-search any property of any node belonging to any tenant, one bit of information per query, entirely through the "allowlisted" read path.

**Fix:** `read_node_shape()` must recognise `IS` as an alternate label-introducer (`var (":"| IS) Label ("|" Label)*`) so the speculative parse in `parse_paren()` succeeds and the normal `check_project_entry`/anonymous-node checks run on it — or, more conservatively given this module's stated fail-closed philosophy ("anything the grammar does not positively recognise is a violation, never accepted"), make the catch in `parse_paren()` distinguish "this really is not a pattern" from "this looks pattern-shaped but uses a variant this grammar doesn't parse" and reject the latter outright (`unsupported_syntax`) rather than silently reinterpreting it as an inert expression. The second option is safer and matches the module's own stated design principle. Either way, add `IS` to the read-only prompt's forbidden-construct list in the n8n prompt text as defence in depth (it currently is not mentioned) and add a regression test.

---

## Warnings

### WR-01 (this review): Unbounded parser recursion on deeply nested input raises an uncaught `RecursionError`

**File:** `data-service/cypher_allowlist.py` — `parse_expr`/`parse_paren` recurse directly on nested `(`/`[`/`{` with no depth guard.

**Issue:** `check_read_allowlist("MATCH (a:Rule {project: $project}) WHERE " + "("*1000 + "a.x = 1" + ")"*1000 + " RETURN a")` raises Python's `RecursionError` rather than returning a violation list — confirmed locally at ~400 nested groups (passes) vs. 1000 (raises), well within one HTTP request body's size budget and well within what a prompt-injected LLM response could plausibly contain (the invariant list explicitly names "very long queries / catastrophic backtracking" as an attack class to check). `post_context_generate_cypher()` in `app.py` does wrap `generate_validated_cypher()` in a bare `except Exception`, so that specific call site degrades to a mapped 502 rather than crashing the worker — but `/mcp`'s `neo4j_query` tool calls `dg_context.check_query_project_scope(cypher)` directly on **caller-supplied** Cypher (not LLM output) with no enclosing `try/except` visible around that call in `app.py`, so the same crash there is unhandled by this module and depends entirely on FastAPI's default 500 handler to avoid taking down the request — still an availability gap the module's own "never raises, always a violation" design principle (stated in its docstring) explicitly promises not to have.

**Fix:** Add an explicit nesting-depth counter (increment/decrement around `parse_paren`/list/map recursion, raise a normal `_Fatal("unsupported_syntax", ...)` past a fixed ceiling, e.g. 60) so oversized input is turned into an ordinary rejected-violation response instead of an interpreter-level exception, consistent with the module's "never raises on malformed input" contract.

### WR-02 (this review): `cypher_template.txt` / `llm/cypher_catalog.json` prose examples no longer match the shipped grammar, so the model's own worked examples fail its retry loop on the first attempt

**File:** `cypher_template.txt` (comment lines using `--`), `llm/cypher_catalog.json` (`worked_example` narration)

**Issue:** Several `worked_example` fields and template comment lines use `--` line comments (SQL style, not Cypher) as narration mixed into the same string that gets shown to the model, and the new grammar in `cypher_allowlist.py` rejects **any** `//` or `/* */` comment outright — the templates avoid that, correctly — but several `worked_example` strings still trip `unsupported_syntax`/`missing_project_scope` when run whole through `check_write_allowlist` (verified: 5 of 6 `worked_example` entries fail when passed as-is, because they interleave prose/pitfall commentary with the Cypher rather than being pure statements; the pure `cypher_template` fields all pass cleanly). This isn't a security hole — it only affects the few-shot prompt text, never the validator itself — but it means the "worked example" the LLM is shown as a positive pattern is not, in fact, itself valid input to the very allowlist that will grade its output, undermining the stated purpose of showing worked examples ("so the LLM's first attempt already conforms").

**Fix:** Strip prose/pitfall narration out of the string that is shown as the worked Cypher (keep it in a separate `notes` field, or move it to genuine `--`-prefixed lines that are stripped before display), and add a catalog-level test that runs every `worked_example` through `check_write_allowlist` and asserts zero violations.

### WR-03 (this review): `find_cross_project_key_collisions` / `find_foreign_project_entities` remain regex/duck-typed defence-in-depth behind the new allowlist, but are now dead code on the paths the allowlist already blocks first

**File:** `data-service/dg_context.py:830-892` (kept, per comment, intentionally as defence-in-depth)

Not a defect — flagged only so the reviewer record is complete: with CR-01/CR-02 above open, this defence-in-depth layer is exactly what should have caught the collision case (a MERGE landing on another project's `Rule_Id`) but it does **not** cover the READ-side leak (CR-01/CR-02 are both `graph_query`, not `rule_ingest`/`rule_edit`) — `find_foreign_project_entities()` only runs on `/mcp neo4j_query`'s **result rows**, and both CR-01 and CR-02's reproductions above return the foreign node's **scalar property** (`b.secret`, not the node itself), which `find_foreign_project_entities()`'s duck-typed walk (`getattr(value, "labels", None)`) cannot see — a bare string has no `.labels`. This is why the reproduced exploits above return real data even though the result-side check is live in the codebase: it is exactly the "return no value derived from another project's nodes" invariant in the task's own primary directive, and it is bypassed for the same structural reason (returning a property value, not the node/relationship/path object) rather than any flaw in `find_foreign_project_entities()` itself. No separate fix requested here beyond CR-01/CR-02; recorded for traceability so a future reviewer does not assume the result-side check would have caught this class.

---

## Info

### IN-01: WR-22/WR-23/WR-24 delta re-review — no regression found

- **WR-22** (`ui-v2/nginx.conf` credential-route rate limiting): the regex location `~ ^/data-service/auth/(login|password|accept-invite)/?$` is evaluated against the decoded, slash-merged URI per nginx's normal location-selection algorithm (longest non-`^~` prefix match still allows regex locations to be tried; `merge_slashes` defaults on, so `//auth/login` collapses; nginx location regexes are case-sensitive and so is the FastAPI route being proxied to, so a case-varied path fails the same way on both sides — not a bypass). No new gap found in the delta.
- **WR-23** (`auth.py: ip_throttle_limit`/`trusted_proxies_configured`, `auth_routes.py`, `entrypoint.sh`): with `DG_TRUSTED_PROXIES` unset, `ip_throttle_limit()` returns 0, `ip_key` is `None` end-to-end in both `auth_routes.login` and `app.py:_accept_invite_for_existing_account`, and the per-address counter is skipped entirely rather than keying on a spoofable `X-Forwarded-For`; `entrypoint.sh` validates every configured entry against `[0-9a-fA-F:./]` and hard-fails container start on anything else. Confirmed consistent with the stated design; the per-username throttle remains the primary control regardless.
- **WR-24** (`app.py: accept_invite`/`_accept_invite_for_existing_account` role monotonicity): the new `auth._STORE_LOCK`-guarded compare-and-set (`ROLE_RANK.get(invite["role"], -1) > ROLE_RANK.get(current, -1)`) correctly refuses to downgrade an existing higher role and correctly adds a missing membership; verified by reading `auth.ROLE_RANK`/`get_role`/`set_membership` call shapes — no lock-free race window observed between the `get_role` read and `set_membership` write since both happen under the same `with auth._STORE_LOCK:` block.

No regression identified in this delta for these three items.

---

_Reviewed: 2026-09-30T06:40:32Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

## Orchestrator corrections from the reviewer's final handback (2026-09-30)

The reviewer's rewrite of this file was blocked, so the corrections below come from its final report and override the sections above where they conflict.

- **Scope:** `ui-v2/Dockerfile`, `docker-compose.yml`, `.env.example`, `tools/security/check_env_file.py` and `spec/SECURITY-BOUNDARY.md` were **not** reviewed. `auth.py` and `auth_routes.py` were reviewed only cursorily. `files_reviewed` is set to 11 to match.
- **Critical:** CR-01 and CR-02 stand as written. Both were verified against a disposable seeded Neo4j 5.26.
- **Warnings (final list of 4):**
  1. **WR-01:** unbounded parser recursion raises `RecursionError` instead of a violation. Verified on the host. Fix: add a nesting-depth ceiling that raises `unsupported_syntax`.
  2. **WR-02 (narrowed):** the catalog and template examples fail `check_write_allowlist` **only because of their `--` header lines**. With those removed, every example passes (verified). Fix: keep narration out of the Cypher the model sees, and add a test that runs every catalog example through the allowlist.
  3. **WR-04 (new):** the read allowlist accepts a trailing `;`, then the n8n "Parse Cypher" node in `graph-query-mcp.json` appends ` LIMIT 50`, which gives an invalid statement. Verified by code reading. Fix: reject a trailing `;` in the read profile, or strip it before appending.
  4. **WR-05 (new):** `stripStatementSeparators` in the "Prepare Graph Payload" node of `rules-to-metagraph.json` tracks single quotes only, while the lexer also handles double quotes and backslash escapes. Not executed. Fix: use the lexer's quote and escape rules, or let the allowlist normalise separators.
- **WR-03 above is a note, not a defect** (defence-in-depth helpers behind the allowlist).
- **Info:**
  - **IN-01:** WR-22, WR-23 and WR-24 show no regression. The WR-24 lock analysis is **unverified**: only the diff was read, not `auth.get_role` / `set_membership`, so a non-reentrant-lock deadlock is not excluded.
  - **IN-02:** `find_foreign_project_entities` inspects only node, relationship and path objects, not scalar values.
  - **IN-03:** `FORBIDDEN_CLAUSE_WORDS` does not list the newer clause words FOR, LET, FILTER, NEXT and OFFSET. No impact on 5.26 (not tested on newer versions).
- **Not reached:**
  - lexer versus Neo4j handling of string escapes and `\u` escapes
  - the nginx regex location on a live nginx
  - parsing of `DG_TRUSTED_PROXIES`
  - authorisation of the caller-supplied `project` on `/mcp neo4j_query`
