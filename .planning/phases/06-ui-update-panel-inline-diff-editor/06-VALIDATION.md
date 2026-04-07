---
phase: 6
slug: ui-update-panel-inline-diff-editor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Browser smoke test (no automated test runner) |
| **Config file** | None — single-file SPA with no test infrastructure |
| **Quick run command** | `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` |
| **Full suite command** | Manual walkthrough of all three Update Knowledge views (Match → Propose → Confirm) |
| **Estimated runtime** | ~30 seconds (build + restart) + manual verification |

---

## Sampling Rate

- **After every task commit:** Run `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` + browser load check
- **After every plan wave:** Full manual walkthrough of the views built in that wave
- **Before `/gsd-verify-work`:** All four views exercised end-to-end with a real project
- **Max feedback latency:** 30 seconds (rebuild + container restart)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | UIST-04 | — | N/A | manual | `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` | N/A | ⬜ pending |
| 06-01-02 | 01 | 1 | UIST-04 | — | N/A | manual | Same | N/A | ⬜ pending |
| 06-01-03 | 01 | 1 | UIST-04 | T-06-01 | diffHtml rendered via dangerouslySetInnerHTML from trusted backend only | manual | Same | N/A | ⬜ pending |
| 06-01-04 | 01 | 1 | UIST-04 | — | N/A | manual | Same | N/A | ⬜ pending |
| 06-01-05 | 01 | 1 | UIST-04 | — | N/A | manual | Same | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework installation needed — manual smoke testing is the established pattern for this project's SPA.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Candidate list renders with checkboxes and score badges | UIST-04 | No automated frontend test runner | Submit prompt in Update Knowledge mode; verify checkbox list appears |
| Diff panel shows red/green highlights | UIST-04 | Visual verification required | Select notes → Edit; verify diff-del (red bg) and diff-ins (green bg) spans are styled |
| Sequential note navigation works | UIST-04 | Stateful multi-step UI flow | Select 2+ notes → Edit; use Next/Previous/Skip buttons |
| Summary view shows changed/skipped badges | UIST-04 | Visual verification required | Navigate through all notes; verify summary view before Confirm |
| Confirm writes to backend and shows success | UIST-04 | End-to-end flow | Click Confirm All; verify success notification and panel reset |
| 409 conflict handled gracefully | UIST-04 | Requires external note modification | Modify note via API between Propose and Confirm; verify error message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
