---
phase: 18
slug: rules-and-validator-rework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit (existing in DG.Tests) |
| **Config file** | `DG/tests/DG.Tests/DG.Tests.csproj` |
| **Quick run command** | `cd DG && dotnet test tests/DG.Tests/ --no-restore --verbosity normal` |
| **Full suite command** | `dotnet test DG/tests/DG.Tests/ -c Release --verbosity normal` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/ --no-restore --filter "DesignStateBindingService*|ValidStatus*"`
- **After every plan wave:** Run `dotnet test DG/tests/DG.Tests/ -c Release --verbosity normal`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | GHVL-01 | — | N/A | unit | `dotnet test --filter "DesignStateBindingService*"` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | GHVL-01 | — | N/A | unit | same as above | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | GHVL-01 | — | N/A | unit | same as above | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | GHVL-03 | — | N/A | unit | `dotnet test --filter "ValidStatus*"` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 2 | GHVL-04 | — | N/A | unit | `dotnet test --filter "DesignStateBindingService*"` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 2 | GHVL-05 | — | N/A | unit | `dotnet test --filter "DesignStatePayloadV2Serializer*"` | ✅ | ⬜ pending |
| 18-03-01 | 03 | 3 | GHVL-06 | — | N/A | unit (Python) | `pytest tests/test_app.py -k "state_summary"` | ❌ W0 | ⬜ pending |
| 18-03-02 | 03 | 3 | GHVL-02 | — | N/A | build | `dotnet build DG/DG.sln` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DG/tests/DG.Tests/DesignStateBindingServiceTests.cs` — covers GHVL-01, GHVL-04
- [ ] `DG/tests/DG.Tests/ValidStatusBindingTests.cs` — covers D-01, D-02 index matching
- [ ] `data-service/tests/test_state_summary.py` — covers GHVL-06 v2 envelope detection
- No existing test infrastructure changes needed (xUnit is set up, test patterns exist)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLASSIFICATOR absent from built plugin | GHVL-02 | Requires Grasshopper runtime | Load plugin in Rhino 8, verify CLASSIFICATOR not in component palette |
| RULE DECONSTRUCT wired to rule shows Objects + DataProperties outputs | GHVL-01 | Requires Grasshopper canvas | Wire METAGRAPH Rules → RULE DECONSTRUCT, inspect outputs |
| VALIDATOR publish round-trip | GHVL-05 | Requires live Neo4j + data-service | Full run with SendValid=true, query Neo4j for persisted Run node |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
