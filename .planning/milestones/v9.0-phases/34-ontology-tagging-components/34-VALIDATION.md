---
phase: 34
slug: ontology-tagging-components
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-18
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (existing, `DG/tests/DG.Tests/DG.Tests.csproj`) |
| **Config file** | none — standard xUnit project |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotation"` |
| **Full suite command** | `dotnet test DG/tests/DG.Tests/` |
| **Estimated runtime** | ~30-60 seconds (note: 4 DesignStateValidationFlowTests fail fast when Neo4j is down — env-dependent, not regressions) |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotation"`
- **After every plan wave:** Run `dotnet test DG/tests/DG.Tests/` + `dotnet build DG/DG.sln -c Release`
- **Before `/gsd-verify-work`:** Full suite green + Release build clean
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 Grammar constants + consistency test | 34-01 | 1 | TAGC-01/02/03 | — | Parser source untouched (regression gate) | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotationParser\|FullyQualifiedName~CanvasAnnotationNameFactory"` | ❌ Wave 0 | ⬜ |
| 01-T2 NameFactory + round-trip suite | 34-01 | 1 | TAGC-01/02/03 | T-34-01, T-34-02 | ValidateName rejects reserved infix tokens; NN string-concat only | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotationNameFactory"` | ❌ Wave 0 | ⬜ |
| 02-T1 OBJECT MARKER shell | 34-02 | 2 | TAGC-01 | — | Unique documented GUID; #if guard | build | `dotnet build DG/DG.sln -c Release` | ✅ (new) | ⬜ |
| 02-T2 SolveInstance scribble/report + ValueTable | 34-02 | 2 | TAGC-01 | T-34-02 | ValidateName on ObjectName; deferred mutation | build + suite | `dotnet build DG/DG.sln -c Release && dotnet test DG/tests/DG.Tests/` | ✅ (new) | ⬜ |
| 02-T3 Live-Rhino UAT (marker) | 34-02 | 2 | TAGC-01 | T-34-03 (accept) | — | manual (checkpoint:human-verify) | — | N/A | ⬜ |
| 03-T1 CanvasAnnotationStyles + icon | 34-03 | 3 | TAGC-02 | — | — | build | `dotnet build DG/DG.sln -c Release` | ✅ (new) | ⬜ |
| 03-T2 EntityTagComponent | 34-03 | 3 | TAGC-02/03 | T-34-04, T-34-05 | ValidateName on Name; ScheduleSolution-deferred mutation; no RecordAddObjectEvent | build + suite | `dotnet build DG/DG.sln -c Release && dotnet test DG/tests/DG.Tests/` | ✅ (new) | ⬜ |
| 03-T3 Live-Rhino UAT (tag→parse→undo) | 34-03 | 3 | TAGC-02/03 | T-34-03 (accept) | — | manual (checkpoint:human-verify) | — | N/A | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs` — stubs for TAGC-01/02/03 factory logic (name construction, next-free-index, round-trip through existing `CanvasAnnotationParser`)
- [ ] `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs` — shared token constants (prerequisite refactor); existing `CanvasAnnotationParserTests.cs` must still pass unmodified (regression gate)
- [ ] No new test-framework install needed — xUnit already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scribble creation/placement, group creation/coloring, Ctrl+Z undo, selection reading | TAGC-01..03 | `DG.Tests` (net9.0) cannot reference `DG.Grasshopper` (net7.0-windows) — NU1201; GH canvas behavior needs live Rhino | Live-Rhino UAT per plan `checkpoint:human-verify` tasks: tag slider as Var "SpansCount" under proc 11 → pink `11_Var_SpansCount` group; OBJECT MARKER idempotent re-run; Ctrl+Z removes tag group |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned 2026-07-18 — every DG.Core task has an `<automated>` `dotnet test` verify; GH_Component tasks have `dotnet build`/`dotnet test` automated gates + a live-Rhino `checkpoint:human-verify` (NU1201: DG.Tests net9.0 cannot reference DG.Grasshopper net7.0-windows). No 3 consecutive tasks lack an automated verify. Feedback latency < 90s.
