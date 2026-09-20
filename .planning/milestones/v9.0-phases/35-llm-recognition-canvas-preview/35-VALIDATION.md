---
phase: 35
slug: llm-recognition-canvas-preview
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (data-service, in-container) + xUnit (DG.Tests, net9.0) |
| **Config file** | data-service/requirements.txt (pytest) / DG/tests/DG.Tests/DG.Tests.csproj |
| **Quick run command** | `docker compose exec -T data-service python -m pytest tests/ -q -k recognition` and `dotnet test .\DG\tests\DG.Tests\ --filter "FullyQualifiedName~Preview|FullyQualifiedName~StructureConfirm"` |
| **Full suite command** | `docker compose exec -T data-service python -m pytest tests/ -q` and `dotnet test .\DG\tests\DG.Tests\` |
| **Estimated runtime** | ~120 seconds combined |
| **Known env caveats** | 4 DesignStateValidationFlowTests fail fast when Neo4j is down; 4 test_dg_context.py fail from host (`neo4j` hostname resolves only inside compose) — env-dependent, not regressions |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched side (pytest -k recognition / dotnet test filtered)
- **After every plan wave:** Run both full suite commands
- **Before `/gsd-verify-work`:** Full suite must be green (modulo documented env-dependent failures)
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 35-01 | 1 | RCGN-01, RCGN-04 | T-35-01, T-35-02 | validator hard-rejects unknown/tagged-overlap ids + DoS bounds; _extract_json never 500s | unit | `docker compose exec -T data-service python -m pytest tests/test_cg_recognition.py::TestValidator tests/test_cg_recognition.py::TestExtractJson -q` | ❌ created in task | ⬜ pending |
| 35-01-02 | 35-01 | 1 | RCGN-01 | T-35-02 | bounded retry, corrective feedback on original prompt, never re-POSTs | unit | `docker compose exec -T data-service python -m pytest tests/test_cg_recognition.py -q` | ❌ created in task | ⬜ pending |
| 35-01-03 | 35-01 | 1 | RCGN-01, RCGN-04 | T-35-04 | thin recognize route; no Neo4j write (source assertion) | integration | `docker compose exec -T data-service python -m pytest tests/test_gh_bridge.py tests/test_cg_recognition.py -q` | ✅ app.py / ❌ recognize | ⬜ pending |
| 35-02-01 | 35-02 | 1 | RCGN-02, RCGN-03 | T-35-07 | shared PreviewRegistry thread-safe (ConcurrentDictionary + snapshot) | build (source) | `dotnet build DG/DG.sln -c Release` | ❌ new file | ⬜ pending |
| 35-02-02 | 35-02 | 1 | RCGN-03 | T-35-03 | additive ValueTable read (dg.recognized.<guid>) | build (source) | `dotnet build DG/DG.sln -c Release` | ✅ additive | ⬜ pending |
| 35-02-03 | 35-02 | 1 | RCGN-03 | T-35-03 | Source propagation additive; classification regex untouched; regression green | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotationParser"` | ❌ W0 (new test) | ⬜ pending |
| 35-03-01 | 35-03 | 2 | RCGN-02 | T-35-05 | UI-thread write marshalling (InvokeOnCanvasWrite), never background thread | build (source) | `dotnet build DG/DG.sln -c Release` | ✅ modified | ⬜ pending |
| 35-03-02 | 35-03 | 2 | RCGN-02 | T-35-05, T-35-08 | one GH_UndoRecord wraps all groups+legend; guard-and-continue on bad ids | build + test | `dotnet build DG/DG.sln -c Release && dotnet test DG/tests/DG.Tests/` | ✅ modified | ⬜ pending |
| 35-03-03 | 35-03 | 2 | RCGN-02 | T-35-05 | single Ctrl+Z wipes all; clear_preview leaves no residue; concurrent-solve safe | manual (live Rhino) | — checkpoint:human-verify | N/A | ⬜ pending |
| 35-04-01 | 35-04 | 2 | RCGN-03 | — | unique GUID; #if guard; Pending readout stub | build (source) | `dotnet build DG/DG.sln -c Release` | ❌ new file | ⬜ pending |
| 35-04-02 | 35-04 | 2 | RCGN-03 | T-35-06, T-35-09 | read-before-write name re-derivation; no persistence call (source assertion) | build + test | `dotnet build DG/DG.sln -c Release && dotnet test DG/tests/DG.Tests/` | ❌ new file | ⬜ pending |
| 35-04-03 | 35-04 | 2 | RCGN-03 | T-35-06 | accept→permanent+source:recognized survives reopen; reject clean; partial accept | manual (live Rhino) | — checkpoint:human-verify | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/test_cg_recognition.py` — stubs for RCGN-01 (pipeline contract, schema validation, bounded retry, unrecognized report)
- [ ] DG.Tests: `PreviewRegistryTests.cs` / `StructureConfirmComponentTests.cs` stubs for RCGN-02..04 (pure-logic parts in DG.Core where possible)

*Existing infrastructure (pytest in data-service, xUnit in DG.Tests) covers the frameworks — no new framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Preview groups render in preview style; Ctrl+Z wipes every trace | RCGN-02 | Requires live Rhino/Grasshopper canvas | Open Frame definition, run recognize + preview_structure, inspect canvas, Ctrl+Z |
| Accept converts preview → permanent convention group visually identical to Phase 34 manual tags | RCGN-03 | Requires live Rhino/Grasshopper canvas | Accept one proposal via DG STRUCTURE CONFIRM, compare group style/name, re-serialize and diff |
| End-to-end recognition quality on Frame definition (majority member-set match) | RCGN-01 | Requires live LLM + live canvas context | POST /computgraph/recognize on Frame canvas context, compare to reference annotation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
