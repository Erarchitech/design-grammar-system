---
phase: 4
slug: update-flow-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no existing test framework in data-service — Wave 0 installs) |
| **Config file** | None — Wave 0 creates `data-service/tests/` |
| **Quick run command** | `docker exec data-service python -m pytest tests/ -x -q` |
| **Full suite command** | `docker exec data-service python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker exec data-service python -m pytest tests/ -x -q`
- **After every plan wave:** Run `docker exec data-service python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | — | — | N/A | setup | `docker exec data-service python -m pytest --co -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | UPDK-01 | — | Parameterized Neo4j queries only | unit | `pytest tests/test_update_flow.py::test_match_returns_candidates -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | UPDK-01 | — | N/A | unit | `pytest tests/test_update_flow.py::test_match_no_results -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | UPDK-03 | — | N/A | unit | `pytest tests/test_update_flow.py::test_word_diff_html -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 2 | UPDK-02 | — | N/A | integration | `pytest tests/test_update_flow.py::test_propose_returns_diffs -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 2 | UPDK-04 | — | N/A | unit | `pytest tests/test_update_flow.py::test_propose_no_changes -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 3 | UPDK-05 | — | 409 on stale updatedAt | unit | `pytest tests/test_update_flow.py::test_confirm_409_on_stale -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | 01 | 3 | UPDK-05 | — | N/A | integration | `pytest tests/test_update_flow.py::test_confirm_writes -x` | ❌ W0 | ⬜ pending |
| 04-01-09 | 01 | 3 | UPDK-06 | — | N/A | integration | `pytest tests/test_update_flow.py::test_confirm_creates_session -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/__init__.py` — test package
- [ ] `data-service/tests/test_update_flow.py` — test stubs for UPDK-01 through UPDK-06
- [ ] `data-service/tests/conftest.py` — shared fixtures (Neo4j mock or test container)
- [ ] `pytest` added to `data-service/requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Propose returns sensible LLM-generated edits | UPDK-02 | Requires live Ollama; LLM output non-deterministic | Submit update prompt, verify returned diff is coherent |
| n8n workflow responds to webhook trigger | UPDK-02 | Requires running n8n + Ollama stack | POST to /n8n/webhook/dg/knowledge-update, check execution-result |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
