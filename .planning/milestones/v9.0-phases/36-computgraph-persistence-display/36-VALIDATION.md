---
phase: 36
slug: computgraph-persistence-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (DG.Tests, .NET) + pytest (data-service) + Vite build (ui-v2) |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj` / `data-service/` (pytest discovery) |
| **Quick run command** | `dotnet test .\DG\tests\DG.Tests\ --filter Computgraph` |
| **Full suite command** | `dotnet test .\DG\tests\DG.Tests\` + data-service pytest + `npm --prefix ui-v2 run build` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command scoped to the touched surface (dotnet filter / pytest -k / vite build)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | CGPD-01..05 | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] data-service publish endpoint tests — stubs for CGPD-01/02/03 (Cypher generation, MERGE idempotency assertions runnable without live Neo4j where possible)
- [ ] Existing DG.Tests infrastructure covers plugin-side additions

*Note: 4 DesignStateValidationFlowTests and 4 test_dg_context.py tests fail fast when Neo4j/compose is down — environment-dependent, not regressions.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Publish from live Grasshopper canvas | CGPD-04 | Requires Rhino 8 + GH runtime | Open canvas, confirm structure, trigger DG COMPUTGRAPH PUBLISH, inspect Neo4j |
| ui-v2 Computgraph layer rendering | CGPD-05 | Visual verification in browser | Rebuild design-grammars container (--no-cache), hard-refresh, check layer + per-project filter |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
