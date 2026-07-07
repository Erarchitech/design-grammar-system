---
phase: 17-graph-access-components
plan: 01
subsystem: testing, models, components
tags: handle-types, graph-access, grasshopper, gh-components, xunit

# Dependency graph
requires:
  - phase: 16-dg-core-state-models-and-state-components
    provides: state model layer (ObjState, ParamState, PropState, DesignState)
provides:
  - 4 typed handle types for Metagraph/Ontograph/ValidGraph/SpecGraph graph layers
  - OntologyClass and OntologyProperty output models
  - CONNECTOR component with Neo4jURI/Neo4jUser/Neo4jPassword/PROJECT NAME/Database/Connect inputs and Database+Project outputs
  - GRAPH DECONSTRUCT synchronous passthrough component
  - Graph-access error messages in ErrorMessageTemplates
  - 3 placeholder PNG icons for GRAPH DECONSTRUCT, ONTOGRAPH, VALIDATION GRAPH
  - 4 public wrapper types in DG namespace
affects:
  - 17-02 METAGRAPH component update
  - 17-03 ONTOGRAPH component
  - 17-04 VALIDATION GRAPH component

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Unsealed handle types with ConnectionInfo { get; init; } = new() pattern
    - Pure synchronous passthrough GH component (no async, no DB calls)
    - 4 typed handle outputs wrapping the same ConnectionInfo reference
    - ErrorMessageTemplates What+Where+How-to-fix pattern for graph-access errors

key-files:
  created:
    - DG/src/DG.Core/Models/MetagraphHandle.cs
    - DG/src/DG.Core/Models/OntographHandle.cs
    - DG/src/DG.Core/Models/ValidGraphHandle.cs
    - DG/src/DG.Core/Models/SpecGraphHandle.cs
    - DG/src/DG.Core/Models/OntologyClass.cs
    - DG/src/DG.Core/Models/OntologyProperty.cs
    - DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs
    - DG/src/DG.Grasshopper/Properties/GraphDeconstruct24.png
    - DG/src/DG.Grasshopper/Properties/OntoGraph24.png
    - DG/src/DG.Grasshopper/Properties/ValidationGraph24.png
    - DG/tests/DG.Tests/MetagraphHandleModelTests.cs
    - DG/tests/DG.Tests/OntographHandleModelTests.cs
    - DG/tests/DG.Tests/ValidGraphHandleModelTests.cs
    - DG/tests/DG.Tests/SpecGraphHandleModelTests.cs
    - DG/tests/DG.Tests/OntologyClassModelTests.cs
    - DG/tests/DG.Tests/OntologyPropertyModelTests.cs
    - DG/tests/DG.Tests/ConnectorComponentPortContractTests.cs
  modified:
    - DG/src/DG.Grasshopper/PublicTypes.cs
    - DG/src/DG.Grasshopper/DgIcons.cs
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs

key-decisions:
  - "Handle types are unsealed to permit public wrapper inheritance in DG namespace"
  - "All 4 handles wrap the SAME ConnectionInfo instance — no per-handle connection logic"
  - "GRAPH DECONSTRUCT is pure synchronous passthrough with no async, no DB calls, no CancellationTokenSource"
  - "CONNECTOR 'Project' output is a string passthrough of the PROJECT NAME input (scopes downstream queries)"
  - "ErrorMessageTemplates follow What+Where+How-to-fix pattern for graph-access error surfaces"
  - "ConnectorComponentPortContractTests validate ErrorMessageTemplates strings rather than GH_Component instantiation (not possible outside GH document)"

patterns-established:
  - "Handle types: unsealed, single ConnectionInfo property with default new() instance, no behavior"
  - "GH passthrough component: #if GRASSHOPPER_SDK guard, synchronous SolveInstance, Unwrap<T> for input casting, ErrorMessageTemplates for user-facing messages"
  - "Public wrapper in DG namespace for each Core model type needing GH output support"
  - "CONNECTOR port names align to port-iri-map-V7.md: Neo4jURI/Neo4jUser/Neo4jPassword/PROJECT NAME/Database/Connect"

requirements-completed: [GHGA-01, GHGA-02]

coverage:
  - id: D1
    description: "4 handle types (MetagraphHandle, OntographHandle, ValidGraphHandle, SpecGraphHandle) with ConnectionInfo { get; init; } pattern"
    requirement: GHGA-02
    verification:
      - kind: unit
        ref: DG/tests/DG.Tests/MetagraphHandleModelTests.cs#DefaultConnectionInfo_ShouldNotBeNull
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/OntographHandleModelTests.cs#DefaultConnectionInfo_ShouldNotBeNull
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/ValidGraphHandleModelTests.cs#DefaultConnectionInfo_ShouldNotBeNull
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/SpecGraphHandleModelTests.cs#DefaultConnectionInfo_ShouldNotBeNull
        status: pass
    human_judgment: false
  - id: D2
    description: "OntologyClass and OntologyProperty output models with Iri + Label fields"
    requirement: GHGA-02
    verification:
      - kind: unit
        ref: DG/tests/DG.Tests/OntologyClassModelTests.cs#ShouldCreateWithIriAndLabel
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/OntologyPropertyModelTests.cs#ShouldCreateWithIriAndLabel
        status: pass
    human_judgment: false
  - id: D3
    description: "CONNECTOR component with ports aligned to port-iri-map-V7.md (Neo4jURI/Neo4jUser/Neo4jPassword/PROJECT NAME/Database/Connect inputs, Database+Project outputs)"
    requirement: GHGA-01
    verification:
      - kind: other
        ref: "grep checks: Neo4jURI, Neo4jUser, Neo4jPassword, PROJECT NAME present in RegisterInputParams; Database and Project present in RegisterOutputParams"
        status: pass
    human_judgment: false
  - id: D4
    description: "GRAPH DECONSTRUCT synchronous passthrough component with 4 typed handle outputs"
    requirement: GHGA-02
    verification:
      - kind: other
        ref: "grep checks: GraphDeconstructComponent class exists, outputs MetagraphHandle/OntographHandle/ValidGraphHandle/SpecGraphHandle"
        status: pass
    human_judgment: false
  - id: D5
    description: "Graph-access error messages in ErrorMessageTemplates (What+Where+How-to-fix pattern)"
    requirement: GHGA-01
    verification:
      - kind: unit
        ref: DG/tests/DG.Tests/ConnectorComponentPortContractTests.cs#ErrorMessage_GraphDeconstructNoInput_ReturnsExpectedFormat
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/ConnectorComponentPortContractTests.cs#ErrorMessage_GraphDeconstructCastFailed_ReturnsExpectedFormat
        status: pass
      - kind: unit
        ref: DG/tests/DG.Tests/ConnectorComponentPortContractTests.cs#ErrorMessage_HandleTypeUnwrapped_ReturnsExpectedFormat
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-04
status: complete
---

# Phase 17 Plan 01: Graph Access Foundation Summary

**Foundation for graph access chain: 4 typed handle types (Metagraph/Ontograph/ValidGraph/SpecGraph), CONNECTOR port alignment to port-iri-map-V7, and synchronous GRAPH DECONSTRUCT component with 4 typed handle outputs**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-04T05:43:00Z
- **Completed:** 2026-07-04T05:55:00Z
- **Tasks:** 3
- **Files modified:** 22

## Accomplishments

- Created 4 unsealed handle types (MetagraphHandle, OntographHandle, ValidGraphHandle, SpecGraphHandle) in DG.Core.Models wrapping ConnectionInfo with { get; init; } pattern
- Created 2 sealed ontology output models (OntologyClass, OntologyProperty) with Iri + Label fields
- Added 4 public wrapper classes (DG.MetagraphHandle etc.) in PublicTypes.cs inheriting Core counterparts
- Added 3 new icon entries (GraphDeconstruct24, OntoGraph24, ValidationGraph24) to DgIcons.cs with placeholder PNGs
- Added 4 graph-access error messages to ErrorMessageTemplates (GraphDeconstructNoInput, GraphDeconstructCastFailed, ConnectorProjectPassthroughFailed, HandleTypeUnwrapped)
- Updated CONNECTOR component: renamed inputs to Neo4jURI/Neo4jUser/Neo4jPassword/PROJECT NAME, renamed output "Connection" to "Database", added "Project" passthrough output
- Created GRAPH DECONSTRUCT component: pure synchronous passthrough, 4 typed handle outputs wrapping the same ConnectionInfo, no async/DB calls
- 26 unit tests across 7 test files, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create 4 handle types, 2 ontology models, public wrappers, icons, and error messages** - `cc227ca` (feat)
2. **Task 2: Update CONNECTOR component and create GRAPH DECONSTRUCT component** - `011dc12` (feat)
3. **Task 3: Create unit tests for handle types, ontology models, CONNECTOR port contract, and GRAPH DECONSTRUCT** - `d6fac65` (test)

## Files Created/Modified

### New files (17 files)
- `DG/src/DG.Core/Models/MetagraphHandle.cs` - Metagraph layer handle type
- `DG/src/DG.Core/Models/OntographHandle.cs` - Ontograph layer handle type
- `DG/src/DG.Core/Models/ValidGraphHandle.cs` - ValidGraph layer handle type
- `DG/src/DG.Core/Models/SpecGraphHandle.cs` - SpecGraph layer handle type
- `DG/src/DG.Core/Models/OntologyClass.cs` - Ontology class output model (IRI + Label)
- `DG/src/DG.Core/Models/OntologyProperty.cs` - Ontology property output model (IRI + Label)
- `DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs` - GRAPH DECONSTRUCT component
- `DG/src/DG.Grasshopper/Properties/GraphDeconstruct24.png` - GDCON icon (24x24)
- `DG/src/DG.Grasshopper/Properties/OntoGraph24.png` - ONTO icon (24x24)
- `DG/src/DG.Grasshopper/Properties/ValidationGraph24.png` - VALID icon (24x24)
- `DG/tests/DG.Tests/MetagraphHandleModelTests.cs` - 3 tests for MetagraphHandle
- `DG/tests/DG.Tests/OntographHandleModelTests.cs` - 3 tests for OntographHandle
- `DG/tests/DG.Tests/ValidGraphHandleModelTests.cs` - 3 tests for ValidGraphHandle
- `DG/tests/DG.Tests/SpecGraphHandleModelTests.cs` - 3 tests for SpecGraphHandle
- `DG/tests/DG.Tests/OntologyClassModelTests.cs` - 3 tests for OntologyClass
- `DG/tests/DG.Tests/OntologyPropertyModelTests.cs` - 3 tests for OntologyProperty
- `DG/tests/DG.Tests/ConnectorComponentPortContractTests.cs` - 8 tests for error messages + handle existence

### Modified files (4 files)
- `DG/src/DG.Grasshopper/PublicTypes.cs` - Added 4 handle type wrappers
- `DG/src/DG.Grasshopper/DgIcons.cs` - Added GraphDeconstruct24, OntoGraph24, ValidationGraph24
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` - Added 4 graph-access methods
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` - Port renames, Project output

## Decisions Made

- All 4 handle types are unsealed to permit public wrapper inheritance, matching the Pattern established in PublicTypes.cs for other model types
- GRAPH DECONSTRUCT is a pure synchronous passthrough — no async, no DB calls, no CancellationTokenSource; this matches the CONTEXT discretion that the component only distributes ConnectionInfo into typed wrappers
- All 4 handle outputs wrap the SAME ConnectionInfo object reference — each downstream component independently uses its handle to scope queries to the correct graph layer via the ConnectionInfo's Database/Project values
- CONNECTOR port "Project" output is a string passthrough of the PROJECT NAME input, matching port-iri-map-V7.md which maps it to dg:project (owl:AnnotationProperty for query scoping)
- Error message template HandleTypeUnwrapped accepts component name and handle type as parameters for reuse across all downstream components
- ConnectorComponentPortContractTests validate ErrorMessageTemplates strings instead of GH_Component port registration — GH_Component cannot be instantiated outside of a Grasshopper document context; this approach is documented in the plan as the fallback strategy

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing using directive in GraphDeconstructComponent.cs**
- **Found during:** Task 2 (build verification)
- **Issue:** GraphDeconstructComponent referenced `ErrorMessageTemplates` without a `using DG.Core.Services;` directive, causing CS0103 compilation errors
- **Fix:** Added `using DG.Core.Services;` to the top of the file
- **Files modified:** DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs
- **Verification:** Build succeeded after fix
- **Committed in:** 011dc12 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was a standard missing-using correction. No scope creep.

## Issues Encountered

- ConnectorComponentPortContractTests could not instantiate GH_Component for port-name validation (Grasshopper SDK DLLs not available in test project). Fallback approach per plan: validated ErrorMessageTemplates string format and handle type structural existence instead. All 26 tests pass.

## Stub Tracking

- The 3 PNG icon files (GraphDeconstruct24.png, OntoGraph24.png, ValidationGraph24.png) are solid-color placeholders at 24x24 resolution. They will be replaced with proper icons in a future plan.
- GraphDeconstructComponent cannot be integration-tested for correct port registration and output types without the Grasshopper SDK runtime environment. Unit tests verify component source code existence and required symbol references.

## Next Phase Readiness

- Downstream plans (17-02 METAGRAPH, 17-03 ONTOGRAPH, 17-04 VALIDATION GRAPH) have the required handle types available in both Core and PublicTypes wrappers
- CONNECTOR component outputs "Database" (ConnectionInfo) and "Project" (string) per port-iri-map-V7.md — ready for GRAPH DECONSTRUCT input and downstream query scoping
- Error messages for graph-access errors are available via ErrorMessageTemplates static methods
- GRAPH DECONSTRUCT outputs 4 typed handle wrappers that downstream reader components (METAGRAPH, ONTOGRAPH, VALIDATION GRAPH) accept via their handle input ports

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The plan's threat model (T-17-01 accept, T-17-02 mitigate via pure passthrough design) is satisfied.

---
*Phase: 17-graph-access-components (Plan 01)*
*Completed: 2026-07-04*
