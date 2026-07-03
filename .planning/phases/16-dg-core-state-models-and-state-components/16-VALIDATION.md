---
phase: 16
slug: dg-core-state-models-and-state-components
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (C# .NET) |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj` |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~StateModel"` |
| **Full suite command** | `dotnet test DG/DG.sln` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/`
- **After every plan wave:** Run `dotnet test DG/DG.sln`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CORE-01 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "ObjState"` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | CORE-02 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "ParamState"` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | CORE-03 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "PropState"` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 1 | CORE-04 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "DesignState"` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | CORE-05 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/ --filter "Serializer"` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 1 | CORE-01..04 | — | N/A | unit | `dotnet test DG/tests/DG.Tests/` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 2 | GHST-02 | — | N/A | integration | `dotnet test DG/DG.sln` | ❌ W0 | ⬜ pending |
| 16-05-01 | 05 | 2 | GHST-01 | — | N/A | integration | `dotnet test DG/DG.sln` | ❌ W0 | ⬜ pending |
| 16-06-01 | 06 | 2 | GHST-03 | — | N/A | integration | `dotnet test DG/DG.sln` | ❌ W0 | ⬜ pending |
| 16-07-01 | 07 | 2 | GHST-04 | — | N/A | integration | `dotnet test DG/DG.sln` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DG/tests/DG.Tests/Models/ObjStateTests.cs` — stubs for CORE-01
- [ ] `DG/tests/DG.Tests/Models/ParamStateTests.cs` — stubs for CORE-02
- [ ] `DG/tests/DG.Tests/Models/PropStateTests.cs` — stubs for CORE-03
- [ ] `DG/tests/DG.Tests/Models/DesignStateTests.cs` — stubs for CORE-04
- [ ] `DG/tests/DG.Tests/Serialization/StatePayloadSerializerTests.cs` — stubs for CORE-05
- [ ] `DG/tests/DG.Tests/Services/DesignStateIdGeneratorTests.cs` — stubs for D-15 ID generator changes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grasshopper component wiring in canvas | GHST-01..04 | Requires Rhino 8 + GH SDK runtime | Wire each component manually; verify output types match IRIs from port-iri-map-V7.md |
| statePayloadJson v2 round-trip with real data | CORE-05 | Unit test covers model round-trip; manual verifies payload shape against downstream consumers | Serialize → inspect JSON → deserialize → compare |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
