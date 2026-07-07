---
phase: 15
slug: specgraph-runtime-rename
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-03
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> This is a mechanical rename phase: validation is a **static grep gate** (deterministic,
> per-file) backed by **live seed→migrate→verify** DB proof and manual webhook/visual checks.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep + `python -m json.tool` (JSON parse) + cypher-shell (seed/verify). No new unit framework. |
| **Config file** | none — reuses existing `test/` scripts + `migrations/` convention |
| **Quick run command** | `grep -rin "KnowledgeGraph\|KnowledgeNote\|KnowledgeTag\|KnowledgeSession\|KnowledgeClass" data-service/ n8n/workflows/ graph-viewer/ spec_schema.cypher` (expect: no output) |
| **Full suite command** | quick grep (phase-wide) + `python -m json.tool` on each edited `n8n/workflows/*.json` + migration seed→verify on dev Neo4j |
| **Estimated runtime** | ~5 seconds (grep + JSON parse); ~30 seconds incl. dev-DB seed/verify |

---

## Sampling Rate

- **After every task commit:** Run the quick grep scoped to that plan's files (expect zero Knowledge* graph-layer hits).
- **After every plan wave:** Run the phase-wide quick grep + `json.tool` on all edited n8n JSON.
- **Before `/gsd-verify-work`:** Phase-wide grep = 0; migration seed→verify counts captured; live webhook + NeoVis visual check passed.
- **Max feedback latency:** 5 seconds (static gate).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | SPEC-01 | T-15-MIG / — | Migration is dev-DB-guarded + idempotent | integration | `cypher-shell -f migrations/2026-07-03_knowledge_to_spec_rename.cypher` then verify `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` = 0 | ✅ | ⬜ pending |
| 15-01-02 | 01 | 1 | SPEC-01 | — | Seed→migrate→verify before/after counts captured | integration | run seed `.cypher` → migration → verification block; assert Spec* labels present | ✅ | ⬜ pending |
| 15-02-01 | 02 | 1 | SPEC-02 | — | N/A | static | `grep -rin "KnowledgeGraph\|KnowledgeNote\|KnowledgeTag\|KnowledgeSession\|KnowledgeClass" data-service/app.py` = 0; `python -c "import ast; ast.parse(open('data-service/app.py').read())"` | ✅ | ⬜ pending |
| 15-02-02 | 02 | 1 | SPEC-02 | — | N/A | static | grep clean over `spec_schema.cypher`; `grep -c ensure_knowledge_indexes data-service/app.py` = 0 | ✅ | ⬜ pending |
| 15-03-01 | 03 | 1 | SPEC-03 | — | Node renames keep `connections` intact | static | grep clean over `n8n/workflows/spec-*.json`; `python -m json.tool` on each; no dangling `connections` name | ✅ | ⬜ pending |
| 15-03-02 | 03 | 1 | SPEC-03 | — | Webhook paths preserved | static | `grep -c '"path": "dg/knowledge-' n8n/workflows/spec-*.json` unchanged; export files absent | ✅ | ⬜ pending |
| 15-04-01 | 04 | 1 | SPEC-04 | — | N/A | static | grep clean over `graph-viewer/config.template.js` + `graph-viewer/index.html` (graph-layer tokens only) | ✅ | ⬜ pending |
| 15-05-01 | 05 | 2 | SPEC-01..04 | — | N/A | static | **phase-wide** grep gate = 0 over runtime surfaces (SC#4) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* No new framework install — validation is grep + JSON-parse + the existing dev-DB seed/verify Cypher convention. The seed `.cypher` for SC#1 proof is a **deliverable of 15-01**, not a Wave 0 stub.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Knowledge ingest/query round-trip via unchanged `/knowledge/*` URLs against Spec* labels | SPEC-02 | Requires running data-service + Neo4j stack | `docker compose up -d`; folder-ingest a note; list + retrieve it; confirm node stored with `Spec*` label + `graph:'SpecGraph'` |
| Live n8n webhook writes/reads Spec* nodes | SPEC-03 | Requires running n8n + Neo4j | POST to `dg/knowledge-ingest` and `dg/knowledge-query`; confirm SpecNote/SpecSession created |
| NeoVis "Specs&Notes" view renders Spec* labels with preserved colors | SPEC-04 | Visual check in browser | open UI; switch to Specs&Notes; confirm nodes render (teal/yellow/purple/pink unchanged) |
| Migration before/after node counts (SC#1 live proof) | SPEC-01 | Requires dev Neo4j | seed Knowledge* nodes → run migration → capture counts (should show N→0 KnowledgeGraph, N SpecGraph) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify (static grep/JSON-parse) or a documented manual proof
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every plan has a grep gate)
- [x] Wave 0 covers all MISSING references (none — existing infra)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
