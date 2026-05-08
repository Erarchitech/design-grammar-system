---
phase: 3
slug: n8n-knowledge-workflows-llm-ingest-and-query
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python (requests-based integration tests, same pattern as `test/test_knowledge_crud.py`) |
| **Config file** | None — standalone scripts run against live services |
| **Quick run command** | `python test/test_phase03_knowledge_llm.py` |
| **Full suite command** | `python test/test_knowledge_crud.py && python test/test_phase03_knowledge_llm.py` |
| **Estimated runtime** | ~90 seconds (includes Ollama inference + polling timeouts) |

---

## Sampling Rate

- **After every task commit:** Run `python test/test_phase03_knowledge_llm.py`
- **After every plan wave:** Run `python test/test_knowledge_crud.py && python test/test_phase03_knowledge_llm.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | ALL | — | N/A | scaffold | `test -f test/test_phase03_knowledge_llm.py` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | INFR-02 | — | N/A | integration | `python test/test_phase03_knowledge_llm.py::test_sc4_webhook_ack` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | INSK-01 | T-3-02 | Prompt text used as Cypher param, not interpolated | integration | `python test/test_phase03_knowledge_llm.py::test_sc1_ingest_prompt` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 2 | QRYK-01, QRYK-02 | T-3-02 | Query text used as Cypher param, not interpolated | integration | `python test/test_phase03_knowledge_llm.py::test_sc2_query_answer` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 2 | INSK-04, QRYK-03, HSTY-01 | — | N/A | integration | `python test/test_phase03_knowledge_llm.py::test_sc3_session_insert && python test/test_phase03_knowledge_llm.py::test_sc5_sessions_endpoint` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test/test_phase03_knowledge_llm.py` — integration test file covering all 7 requirements (SC-1 through SC-5)

*(No framework install needed — `requests` is already used in `test/test_knowledge_crud.py`)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM produces sensible title/tags from NL prompt | INSK-01 | Subjective quality of LLM output | Submit a descriptive prompt, verify the extracted title and tags are semantically appropriate |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
