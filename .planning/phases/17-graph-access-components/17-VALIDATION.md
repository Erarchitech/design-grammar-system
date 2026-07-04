---
phase: 17
slug: graph-access-components
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | xUnit 2.9.2 + Microsoft.NET.Test.Sdk 17.12.0 |
| **Config file** | none — xUnit discovers facts automatically |
| **Quick run command** | `dotnet test DG/tests/DG.Tests/ --no-restore --filter "FullyQualifiedName~{TestClass}"` |
| **Full suite command** | `dotnet test DG/tests/DG.Tests/` |
| **Estimated runtime** | ~4 seconds |

---

## Sampling Rate

- **After every task commit:** Run `dotnet test DG/tests/DG.Tests/`
- **After every plan wave:** Run `dotnet test DG/tests/DG.Tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 4 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | GHGA-01/02 | — | Handle types are immutable, ConnectionInfo wrapping is lossless | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~HandleModel"` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | GHGA-01 | — | CONNECTOR outputs Database handle with renamed ports (Neo4jURI, Neo4jUser, Neo4jPassword) | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ConnectorComponent"` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | GHGA-02 | — | GRAPH DECONSTRUCT splits ConnectionInfo into 4 typed handles | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~GraphDeconstructComponent"` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | GHGA-03 | — | IRuleRepository.GetObjectsAsync returns deduplicated Class IRIs via REFERS_TO query | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ObjectsQuery"` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 2 | GHGA-03 | — | METAGRAPH outputs Rules + Objects, lists are internally stable across solves | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~MetagraphComponent"` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | GHGA-04 | — | IOntoGraphRepository queries OntoGraph layer for Class/ObjProperties/DataProperties | integration | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~OntoGraphRepository"` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 2 | GHGA-04 | — | ONTOGRAPH component outputs 3 typed lists from repository result | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~OntoGraphComponent"` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 2 | GHGA-05 | T-04-01 | IValidGraphRepository handles v1 (ParamState-only) and v2 (3-part) payloads without crash | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ValidGraphRepository"` | ❌ W0 | ⬜ pending |
| 17-04-02 | 04 | 2 | GHGA-05 | — | VALIDATION GRAPH outputs Run + Status (IReadOnlyList\<bool\>) + DesignState (deduplicated by StateId) | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ValidationGraphComponent"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `DG/tests/DG.Tests/MetagraphHandleModelTests.cs` — handle type immutability and default values
- [ ] `DG/tests/DG.Tests/OntographHandleModelTests.cs` — handle type
- [ ] `DG/tests/DG.Tests/ValidGraphHandleModelTests.cs` — handle type
- [ ] `DG/tests/DG.Tests/SpecGraphHandleModelTests.cs` — handle type
- [ ] `DG/tests/DG.Tests/OntologyClassModelTests.cs` — model IRI+label
- [ ] `DG/tests/DG.Tests/OntologyPropertyModelTests.cs` — model IRI+label
- [ ] `DG/tests/DG.Tests/Neo4jOntoGraphRepositoryTests.cs` — Cypher query for Classes, ObjProperties, DataProperties
- [ ] `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` — Run/Status/DesignState output, v1/v2 compat, deduplication
- [ ] `DG/tests/DG.Tests/ObjectsQueryTests.cs` — METAGRAPH Objects extraction via REFERS_TO→Class, dedup by IRI
- [ ] Error message unit tests for new `ErrorMessageTemplates` entries (if any added)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VALIDATION RUNS component absent from Grasshopper toolbar | GHGA-05 | Requires live Rhino 8 + Grasshopper to verify component GUID not registered | Load the plugin, open Grasshopper, search for "VALIDATION RUNS" — component should not appear; "VALIDATION GRAPH" should appear instead |
| CONNECTOR port labels visible on canvas | GHGA-01 | Requires live Rhino 8 to verify Grasshopper input/output nicknames | Place CONNECTOR on canvas, verify input nicknames are "Neo4jURI", "Neo4jUser", "Neo4jPassword", output nickname is "Database" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
