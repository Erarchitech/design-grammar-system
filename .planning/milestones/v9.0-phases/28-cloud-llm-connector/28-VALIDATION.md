---
phase: 01
slug: cloud-llm-connector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs `tests/` |
| **Quick run command** | `docker compose exec data-service pytest tests/ -x --tb=short` |
| **Full suite command** | `docker compose exec data-service pytest tests/ -v --tb=long` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec data-service pytest tests/ -x --tb=short`
- **After every plan wave:** Run `docker compose exec data-service pytest tests/ -v --tb=long`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | LLMC-01 | T-01-01 | Encrypted key at rest, never in logs/Neo4j/localStorage | unit | `pytest tests/test_llm_gateway.py -k test_key_masking -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLMC-02 | T-01-02 | Gateway resolves provider, n8n sends null | unit | `pytest tests/test_llm_gateway.py -k test_adapter_routing -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLMC-03 | T-01-03 | Garbled API key → fallback to Ollama; timeout → actionable error | unit | `pytest tests/test_llm_gateway.py -k test_fallback -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLMC-04 | — | 6 n8n Ollama nodes → gateway; 0 direct Ollama calls | integration | `grep -r "11435\|ollama" n8n/workflows/` | — | ⬜ pending |
| TBD | TBD | TBD | LLMC-05 | — | Settings CRUD + key masking in responses | unit | `pytest tests/test_llm_settings.py -k test_settings -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLMC-06 | — | Provider/model select, key input (masked), test button, status indicator | manual | Open UI → LLM Settings tab | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_llm_gateway.py` — stubs for LLMC-01/02/03 (adapter routing, fallback, key masking)
- [ ] `tests/test_llm_settings.py` — stubs for LLMC-05 (settings CRUD, key masking)
- [ ] `tests/conftest.py` — shared fixtures (FastAPI TestClient, mock provider responses)
- [ ] pytest installed in data-service container (verify with `docker compose exec data-service pip list | grep pytest`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI settings panel renders with masked key | LLMC-06 | Browser DOM inspection needed | Open graph-viewer, click "LLM Settings" tab, verify key is masked (•) |
| n8n workflows produce valid graphs after rewiring | LLMC-04 | Requires live Neo4j + Ollama | Submit a rule via webhook, verify graph in Neo4j browser |
| Settings persist across data-service restart | LLMC-05 | Docker restart cycle | Save key, `docker compose restart data-service`, verify key still present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
