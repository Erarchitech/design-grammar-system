---
phase: 29
slug: dg-aware-context-layer-swrl-ontology-cypher-awareness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-12
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (unversioned in `requirements.txt`) with FastAPI `TestClient` |
| **Config file** | none found — no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section in `data-service/`; tests rely on `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))` boilerplate per file (see `test_reasoner.py:18`) |
| **Quick run command** | `docker compose exec data-service pytest tests/test_dg_context.py -x` |
| **Full suite command** | `docker compose exec data-service pytest` |
| **Estimated runtime** | ~60 seconds (full `data-service/tests/` suite, estimate — includes existing reasoner/connector tests) |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec data-service pytest tests/test_dg_context.py -x`
- **After every plan wave:** Run `docker compose exec data-service pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, plus manual inspection of `GET /context/debug` for a "maximum height" rule (success criterion 1) and a deliberately-corrupted-Cypher validator run (success criterion 2)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CTXA-01 | V5 | `/context/assemble` returns V7 concept subset per graph layer for `rule_ingest`/`rule_edit`/`graph_query` | unit + integration | `pytest tests/test_dg_context.py::TestContextAssemble -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CTXA-02 | — | `llm/cypher_catalog.json` loads and exposes all 6 shapes with worked examples | unit | `pytest tests/test_dg_context.py::TestCypherCatalog -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CTXA-03 | — | SWRL convention block (violation-inverted semantics, atom ordering, Var/Literal rules) is machine-readable and included in assembled context | unit | `pytest tests/test_dg_context.py::TestSwrlConventions -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CTXA-04 | V5 (LLM-Cypher injection / prompt injection via rules_text) | Validator catches corrupted Cypher (wrong label, bad `kind` enum, disallowed verbs) and returns structured violations; retry loop bounded at 2 retries | unit + integration (mocked adapter) | `pytest tests/test_dg_context.py::TestValidator tests/test_dg_context.py::TestRetryLoop -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CTXA-05 | — | Context selection is deterministic (no embeddings) — same request twice yields byte-identical assembled context | unit (idempotency assertion) | `pytest tests/test_dg_context.py::TestDeterminism -x` | ❌ W0 | ⬜ pending |

*Task ID / Plan / Wave columns are TBD until `gsd-planner` assigns tasks — this table seeds the requirement→test mapping the plan's tasks must honor.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/test_dg_context.py` — new test file, follow `test_reasoner.py`'s structure exactly (`isolated_store` fixture pattern only if `dg_context.py` gains persistence; likely not needed since the catalog/SWRL/Computgraph blocks are read-only)
- [ ] `llm/cypher_catalog.json` — the artifact itself must exist before any test can load it; first task in the plan
- [ ] Fixture: reuse the real `DesignGrammar-V7.owl` file (already checked into the repo) for parser tests rather than authoring a synthetic fixture, so parser tests catch real-file parsing issues
- [ ] Mock/stub for `adapter.generate()` in retry-loop tests — no existing fixture for this specific mock; follow `TestReasonerConsistencyProxy`'s `monkeypatch.setattr` pattern but targeting `llm_gateway.get_adapter` or the adapter instance's `.generate` method instead of `httpx.post`

---

## Manual-Only Verifications

*All phase behaviors have automated verification. `GET /context/debug` and the corrupted-Cypher validator run (success criteria 1–2) are covered by `TestContextAssemble`/`TestValidator` above; a live end-to-end pass through Docker is a sanity-check addition at `/gsd-verify-work` time, not a manual-only requirement.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
