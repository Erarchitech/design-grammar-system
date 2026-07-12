---
phase: 823
slug: shacl-validation-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-12
---

# Phase 823 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (dg-reasoner, data-service) · xUnit (DG.Tests) · none for ui-v2 (manual/browser) |
| **Config file** | dg-reasoner/tests/ · data-service/tests/ · DG/tests/DG.Tests |
| **Quick run command** | `python -m pytest dg-reasoner/tests/ -q -m "not integration"` |
| **Full suite command** | `python -m pytest dg-reasoner/tests/ data-service/tests/ -q` + `DOTNET_ROLL_FORWARD=LatestMajor dotnet test .\DG\tests\DG.Tests\` |
| **Estimated runtime** | ~60 seconds (unit tiers) |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched service
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner fills per-task rows from PLAN.md tasks) | | | SHCL-01, SHCL-02 | — | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `dg-reasoner/tests/test_shacl_report.py` — stubs for SHCL-01 result mapping (severity/message extraction, allow_infos/allow_warnings semantics)
- [ ] `dg-reasoner/tests/test_validgraph_export.py` — stubs for statePayloadJson→ABox minting + owl:AllDifferent
- [ ] Existing pytest/xUnit infrastructure covers the frameworks — no new framework installs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Model screen SHACL section severity treatment (red/orange/yellow chips, states) | SHCL-02 | Visual rendering in browser | Open Model screen for a project with a SHACL-checked run; verify chips, counts, conforms/not-checked/unavailable states |
| Grasshopper VALIDATOR Report lines for SHACL findings | SHCL-02 | Requires Rhino/GH canvas | Publish a run from GH; inspect Report output + runtime message levels |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
