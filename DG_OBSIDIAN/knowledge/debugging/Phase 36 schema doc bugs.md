---
tags: [debugging, schema, doc-bug, computgraph]
date: 2026-07-19
status: fixed
---

# Phase 36 schema doc bugs — HAS_INTERFACE, PARAM_LINK, Algorithm merge key

**Context:** Post-verification check after Phase 36 execution. Verifier (gsd-verifier) cross-checked 8 schema propagation surfaces against the runtime code and found 3 consistent documentation bugs.

## Bug 1: HAS_INTERFACE direction

- **Where:** All 6 doc surfaces (CLAUDE.md, spec/DATABASE.md, cypher_template.txt, training/dataset_schema.json, .github/copilot-instructions.md, README.md)
- **Wrong:** `HAS_INTERFACE (Pattern→Interface)`
- **Correct:** `HAS_INTERFACE (Procedure→Interface)`
- **Root cause:** Template copy from a pre-Phase-32 understanding where Pattern was the owner; runtime `computgraph_publish.py:563` correctly links Procedure→Interface.
- **Fix:** `4e441d3` — 6 files patched.

## Bug 2: PARAM_LINK direction

- **Where:** Same 6 doc surfaces
- **Wrong:** `PARAM_LINK (Parameter→Parameter)`
- **Correct:** `PARAM_LINK (Parameter→Interface, wire-derived)`
- **Root cause:** Misunderstood PARAM_LINK as cross-procedure parameter linking; actual semantics is wire-derived Parameter→Interface links.
- **Fix:** `4e441d3` — 6 files patched.

## Bug 3: Algorithm merge key

- **Where:** `cypher_template.txt:111`, `spec/DATABASE.md:192`, `claude.md`, `.github/copilot-instructions.md`
- **Wrong:** `(cgId, definitionId, project)`
- **Correct:** `(algIndex, definitionId, project)`
- **Root cause:** Algorithm has no cgId per DGID-01 scope — only Object/Procedure/Pattern/Parameter/Interface get dgId. Algorithm uses `algIndex` as its unique key within a definition.
- **Fix:** `4e441d3` — 4 files patched.

## Key Takeaway

The **verifier detected these bugs** by cross-referencing doc assertions against grep+read of `computgraph_publish.py`. Runtime code was correct in all 3 cases — only schema/docs were stale. This validates the 6-surfaced Schema Change Propagation checklist (CLAUDE.md standing rule) as a real effective detection mechanism.

## Related

- [[decisions/Phase 36 Computgraph publish avoids mint_identity]]
