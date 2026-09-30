---
tags: [decision, security, cypher, llm, phase-1205]
date: 2026-09-30
---

# LLM-written Cypher is guarded by a grammar allowlist, not a blocklist

## Context

Graph queries and rule ingest execute Cypher that an LLM wrote. That Cypher can be prompt-injected, and it runs against one shared Neo4j where tenancy is a `project` property. The first guard used regex and blocklist static analysis. Reviews bypassed it three times: see [[knowledge/debugging/Blocklist checks over LLM-written Cypher were bypassed three times|debugging note]].

## Decision

`data-service/cypher_allowlist.py` is the only gate. It lexes and parses against a small grammar, and anything it does not positively recognise is a violation.

- **Lexer:** rejects backticks, comments, non-ASCII outside strings, backslashes and doubled-quote escapes inside strings, and every `;`. A single trailing `;` is allowed on the write path only.
- **Read profile:** allows only `MATCH`, `OPTIONAL MATCH`, `WHERE`, `RETURN`, `ORDER BY`, `SKIP`, `LIMIT` and a fixed function list.
  - Expressions use an operand/operator grammar. `STARTS WITH` and `ENDS WITH` are single operators, recognised only in operator position.
  - Pattern predicates and label expressions (`IS`, `&`, `|`, `!`, `%`) are rejected.
  - Every node pattern must bind a variable and carry `project: $project`.
  - An audit proves every `(` was classified.
- **Write profile:** allows only `MERGE`, `MATCH` (no `WHERE`) and `SET var.prop = literal`.
  - Each node has one schema label, a complete literal key and `project: $project`.
  - `project` and `graph` can never be `SET`. `DELETE`, `REMOVE` and `CALL` are rejected.
- **Retries:** violations feed the generator's retry loop, and the catalog and template teach the grammar.

## Why

A blocklist has to anticipate every construct Cypher allows. An allowlist only has to understand what is legitimate. Rejection is safe because the LLM can retry.

## Verification

- 156+ unit tests, plus pattern and hostile-node matrices, and a 180,000-mutation fuzz with 0 violations.
- An opt-in differential probe, `tests/test_cypher_allowlist_probe.py`. Set `DG_ALLOWLIST_PROBE_BOLT` and run it against a **disposable** two-tenant Neo4j 5.26 (never the live one). Every accepted query runs, and the test asserts that no foreign-tenant marker appears in any scalar, map or entity.

## Consequences

- Legitimate queries lose pattern predicates, backslash string escapes and `;` chaining.
- OntoGraph labels are MERGEd per project.
- Anything that extends the grammar must add probe cases.
