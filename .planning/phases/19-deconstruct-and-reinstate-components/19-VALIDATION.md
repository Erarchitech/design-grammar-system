---
phase: 19
slug: deconstruct-and-reinstate-components
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-05
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit 2.9.2 |
| **Config file** | none — xUnit auto-discovers tests in DG.Tests.dll |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~(DesignStateDeconstruct\|ObjectDeconstruct\|ParameterReinstate\|ReinstatementService)"` |
| **Full suite command** | `dotnet test DG/tests/DG.Tests/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~(DesignStateDeconstruct|ObjectDeconstruct|ParameterReinstate|ReinstatementService)"`
- **After every plan wave:** Run `dotnet test DG/tests/DG.Tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | GHST-05 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DesignStateDeconstruct"` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | GHST-05 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | GHST-05 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 1 | GHST-06 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ObjectDeconstruct"` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 1 | GHST-06 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-03-01 | 03 | 1 | GHST-07 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ParameterReinstate"` | ❌ W0 | ⬜ pending |
| 19-03-02 | 03 | 1 | GHST-07 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-03-03 | 03 | 1 | GHST-07 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-03-04 | 03 | 1 | GHST-07 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ReinstatementService"` | ✅ | ⬜ pending |
| 19-03-05 | 03 | 1 | GHST-07 | — | N/A | unit | same filter | ✅ | ⬜ pending |
| 19-03-06 | 03 | 1 | GHST-07 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |
| 19-03-07 | 03 | 1 | GHST-07 | — | N/A | unit | same filter | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DG/tests/DG.Tests/DesignStateDeconstructComponentTests.cs` — covers GHST-05 (3 test cases: split into lists, null/missing warning, empty bag passthrough)
- [ ] `DG/tests/DG.Tests/ObjectDeconstructComponentTests.cs` — covers GHST-06 (2 test cases: property extraction, null/missing warning)
- [ ] `DG/tests/DG.Tests/ParameterReinstateComponentTests.cs` — covers GHST-07 (6-8 test cases: rising-edge, index-matched output, all-params output, Status summary, deferred write, assembly-mismatch fallback)
- [ ] `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` — EXTEND existing test class with new deconstruct/reinstate message templates

*Existing test infrastructure (xUnit, Microsoft.NET.Test.Sdk) is already configured — no framework install needed. Only new test files are required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Canvas wiring: PARAMETER REINSTATE Target input | GHST-07 | Wire-traversal requires live GH document graph | Wire PARAMETER STATE → PARAMETER REINSTATE Target; verify upstream discovery finds sliders/toggles |
| Deferred slider write via ScheduleSolution | GHST-07 | ScheduleSolution callback executes in GH runtime, not test harness | Toggle Reinstate; verify slider values change in GH canvas after solution completes |
| E2E round-trip: VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → OBJECT DECONSTRUCT | GHST-05, GHST-06 | Cross-component wire chain requires GH runtime | Wire chain in GH canvas; verify Object/Geometry/Label outputs match stored values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
