---
phase: 5
slug: ui-mode-restructuring-insert-and-query-panels
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Browser-based manual + curl endpoint verification |
| **Config file** | none — no test framework for single-file SPA |
| **Quick run command** | `curl -s http://localhost:8080/data-service/knowledge/notes/test_project` |
| **Full suite command** | `bash test/phase-05-verify.sh` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Rebuild container (`docker compose build --no-cache design-grammars && docker compose up -d design-grammars`), hard refresh, verify sidebar renders
- **After every plan wave:** Run full verification script
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | UIST-01 | — | N/A | manual | Verify sidebar has DesignRules tab with Insert/Query/Edit Rules modes | — | ⬜ pending |
| 05-01-02 | 01 | 1 | UIST-02 | — | N/A | manual | Verify sidebar has Specs&Notes tab with Insert/Query Knowledge modes | — | ⬜ pending |
| 05-01-03 | 01 | 1 | UIST-03 | — | N/A | integration | `curl -s -X POST http://localhost:8080/data-service/knowledge/ingest/folder -H 'Content-Type: application/json' -d '{"path":"/data/repo","project":"test"}'` | — | ⬜ pending |
| 05-01-04 | 01 | 1 | UIST-03 | — | N/A | integration | Verify NL prompt insert triggers polling with workflow key `knowledge-ingest` | — | ⬜ pending |
| 05-01-05 | 01 | 1 | UIST-05 | — | N/A | integration | Verify Query Knowledge submits to `/knowledge/query` and displays response | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test/phase-05-verify.sh` — verification script checking sidebar structure and endpoint connectivity

*Existing backend infrastructure (data-service endpoints, n8n workflows) already covers integration verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tab switching persists state | D-06 | Visual UI behavior in single-file SPA | Switch tabs, verify prompt text and response persist |
| Graph View hidden in Specs&Notes | D-07 | Visual UI behavior | Switch to Specs&Notes tab, verify OntoGraph/MetaGraph dropdown not visible |
| Insert Knowledge sub-tabs | D-08 | Visual UI behavior | In Insert Knowledge mode, verify From Folder / From Prompt tabs work |
| Folder path placeholder hint | D-09 | Visual UI behavior | In From Folder sub-tab, verify placeholder shows example path |

*Primary phase is UI restructuring — most verifications are visual/manual.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
