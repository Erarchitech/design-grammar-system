# DG v7.0 End-to-End Validation Checklist

> **Purpose:** Verify the full v7.0 DG pipeline end-to-end on live Docker infrastructure, from rule ingest through PARAMETER REINSTATE. Both a development QA tool and a release artifact for architect installation verification.
>
> **Milestone:** v7.0 Update of DG Addin for Grasshopper
> **Phase:** 20-e2e-validation-and-docs | Plan 20-01
>
> **Instructions:** Run each step sequentially. Check the box when the step passes. If any step fails, consult the Troubleshooting section and fix before proceeding. The full chain must pass for a clean sign-off.

---

## Prerequisites

- [ ] Docker Desktop is running
- [ ] Docker stack is up: `docker compose ps` shows neo4j, n8n, ollama, data-service, design-grammars as healthy
- [ ] Ollama model pulled: `docker exec ollama ollama pull llama3.1` (skip if already present)
- [ ] n8n workflow `rules-to-metagraph.json` imported and ACTIVE
  - `docker exec n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json`
  - `docker exec n8n n8n update:workflow --active=true --id=<workflow-id>` (get ID from n8n UI at http://localhost:5678)
  - `docker restart n8n`
- [ ] n8n workflow `graph-query-mcp.json` imported and ACTIVE (same procedure)
- [ ] Ollama is responding: `curl http://localhost:8080/n8n/webhook/dg/rules-ingest -X POST -H "Content-Type: application/json" -d '{"rules_text":"test","project_name":"e2e-prep-check"}'` returns a response (may take 40-70s on cold start)
- [ ] Neo4j is reachable: `curl -u neo4j:12345678 -X POST http://localhost:7474/db/neo4j/tx/commit -H "Content-Type: application/json" -d '{"statements":[{"statement":"RETURN 1 AS test"}]}'` returns `{"results":[...]}`
- [ ] Data service is reachable: `curl http://localhost:8000/` returns `{"status":"Data Service is running"}`
- [ ] Speckle tokens configured (optional — publish verification only):
  - `SPECKLE_WRITE_TOKEN` and/or `SPECKLE_READ_TOKEN` set on data-service container
- [ ] Rhino 8 is installed with the DG v7.0 plugin (`.gha`)

---

## Fresh Baseline Setup

- [ ] Create a new DG project via the web UI at http://localhost:8080/ (or use the `CreateProject` n8n webhook if available)
- [ ] Verify the project appears in Neo4j: `MATCH (p:Project {name: 'e2e-v7-test-{timestamp}'}) RETURN p`
- [ ] Run Docker-side automation: `bash test/smoke_e2e.sh` — confirms infrastructure is functional
- [ ] Open Rhino 8, load the DG plugin (check `GrasshopperDeveloperSettings` for the plugin folder)
- [ ] Create a new Grasshopper definition (`.gh` file)

---

## Step-by-Step Test Flow

### Step 1: Rule Ingest via n8n Webhook

**Action:**
```bash
curl -s --max-time 210 -X POST http://localhost:8080/n8n/webhook/dg/rules-ingest \
  -H "Content-Type: application/json" \
  -d '{
    "rules_text": "Maximum height of buildings is 75 meters. Minimum area of living units is 28 square meters. All residential buildings must be at least 10 meters apart.",
    "project_name": "e2e-v7-test-{timestamp}"
  }'
```

**Expected output:**
- Response contains `executionId` (UUID)
- After ~15s wait, Neo4j contains Rule nodes for the fixture project:
  ```cypher
  MATCH (r:Rule {project: 'e2e-v7-test-{timestamp}'})
  RETURN r.Rule_Id, r.SWRL, r.kind
  ```
- Expected Rule IDs: `R_URB_HEIGHT_MAX_75_V`, `R_RES_AREA_MIN_28_V`, `R_RES_SEPARATION_MIN_10_V`
- Each Rule has non-empty `.SWRL`, `.RuleName`, `.kind` properties
- Atom nodes created with `HAS_BODY`/`HAS_HEAD` relationships
- Var and Literal nodes created with `ARG` relationships
- All nodes have `project='e2e-v7-test-{timestamp}'` and correct `graph` assignment

- [ ] **PASS** — executionId returned
- [ ] **PASS** — Rule nodes created with v4 schema properties (SWRL, RuleName, RuleDescription)
- [ ] **PASS** — Atom/Var/Literal nodes with correct relationships
- [ ] **PASS** — `graph` property correctly assigned (Metagraph for rules/atoms, OntoGraph for classes/properties)

---

### Step 2: METAGRAPH Read

**Action (Grasshopper):**
1. Place CONNECTOR component on canvas
2. Set Neo4jURI = `bolt://localhost:7687`, Neo4jUser = `neo4j`, Neo4jPassword = `12345678`, Project = `e2e-v7-test-{timestamp}`
3. Place GRAPH DECONSTRUCT, connect CONNECTOR Database output → GRAPH DECONSTRUCT input
4. Place METAGRAPH, connect GRAPH DECONSTRUCT Metagraph output → METAGRAPH input
5. Run the definition (F5 or Recompute)
6. Inspect the METAGRAPH outputs: Rules list, Objects list

**Expected output:**
- Rules output is a list of Rule objects, one per ingested rule
- Objects output is a list of Class entities referenced by the rules via REFERS_TO
- Both lists are index-matched (rule at index N references class at index N)
- Each Rule has: `Rule_Id`, `SWRL`, `RuleName`, `RuleDescription`, `kind`
- Objects contains only Class IRIs (no DatatypeProperty / ObjectProperty / Builtin)

- [ ] **PASS** — Rules list non-empty with correct properties
- [ ] **PASS** — Objects list non-empty with Class IRIs only
- [ ] **PASS** — Lists are index-matched
- [ ] **PASS** — No DatatypeProperty/Builtin leaked into Objects output

---

### Step 3: RULE DECONSTRUCT Partition

**Action (Grasshopper):**
1. Connect METAGRAPH Rules output (list) → RULE DECONSTRUCT Rule input
2. Connect METAGRAPH Objects output (list) → RULE DECONSTRUCT Objects input
3. Optionally: select one specific rule by indexing the Rules list
4. Inspect RULE DECONSTRUCT outputs: Objects, DataProperties, SWRL, RuleName, RuleDescription

**Expected output:**
- Objects output contains only Class IRIs and ObjectProperty IRIs (things with `REFERS_TO` → Class/ObjectProperty)
- DataProperties output contains only DatatypeProperty IRIs
- Builtin variables are EXCLUDED from both outputs (per v7.0 D-07)
- Each variable appears in exactly ONE output (Objects or DataProperties, never both)
- SWRL, RuleName, RuleDescription passthrough intact from input
- Empty outputs? Metadata missing? → Warning-level message per ErrorMessageTemplates

- [ ] **PASS** — Objects output contains Class/ObjProperty IRIs only
- [ ] **PASS** — DataProperties output contains DatatypeProperty IRIs only
- [ ] **PASS** — Builtin variables excluded from both outputs
- [ ] **PASS** — Each variable appears in exactly one output
- [ ] **PASS** — SWRL/RuleName/RuleDescription passthrough intact
- [ ] **PASS** — Warning-level messages for missing/unexpected metadata

---

### Step 4: OBJECT STATE

**Action (Grasshopper):**
1. Place OBJECT STATE component on canvas
2. Connect an Object variable (e.g., a Building geometry from Rhino) → Object input
3. Connect the same geometry → Geometry input (or use fixture_geometry.json via a geometry loader)
4. Connect a Label string (e.g., `"Building-01"`) → Label input
5. Run the definition
6. Inspect OBJECT STATE output: ObjState

**Expected output:**
- ObjState output is a single ObjState object
- `StateId` starts with `OS_` prefix
- Object reference preserved (matches the input)
- Geometry preserved (or null if not serializable — Rhino geometry is in-process handle)
- Label matches the input string
- No errors or warnings

- [ ] **PASS** — ObjState output non-null with correct StateId (OS_ prefix)
- [ ] **PASS** — Object reference matches input
- [ ] **PASS** — Geometry reference preserved (or null for non-serializable types)
- [ ] **PASS** — Label matches input
- [ ] **PASS** — No component errors

---

### Step 5: PARAMETER STATE

**Action (Grasshopper):**
1. Place PARAMETER STATE component on canvas
2. Connect a Parameters list (mix of Number slider, Integer slider, Boolean toggle) → Parameters input
3. Run the definition
4. Inspect PARAMETER STATE output: ParamState

**Expected output:**
- ParamState output is a single ParamState object
- `StateId` starts with `DS_` prefix
- `CapturedAtUtc` is a valid UTC timestamp
- `Parameters` list preserves ALL inputs in order
- Each parameter typed correctly (Number/Integer/Boolean)
- Deterministic StateId: same inputs produce same StateId across runs

- [ ] **PASS** — ParamState output non-null with correct StateId (DS_ prefix)
- [ ] **PASS** — CapturedAtUtc is valid timestamp
- [ ] **PASS** — Parameters list matches input order and values
- [ ] **PASS** — Each parameter preserves type (Number/Integer/Boolean)
- [ ] **PASS** — Deterministic StateId across repeated solves

---

### Step 6: PROPERTY STATE

**Action (Grasshopper):**
1. Place PROPERTY STATE component on canvas
2. Connect a Rule object (from RULE DECONSTRUCT or METAGRAPH) → Rule input
3. Connect a DataProperty reference (from RULE DECONSTRUCT DataProperties output) → DataProperty input
4. Connect a PropValue (typed as DesignStateParameter — e.g., a Number value) → PropValue input
5. Run the definition
6. Inspect PROPERTY STATE output: PropState

**Expected output:**
- PropState output is a single PropState object
- `StateId` starts with `PS_` prefix
- Rule reference preserved
- DataProperty reference matches input
- PropValue typed as DesignStateParameter (Number/Integer/Boolean)
- No index-mismatch errors (single input, single output)

- [ ] **PASS** — PropState output non-null with correct StateId (PS_ prefix)
- [ ] **PASS** — Rule reference preserved
- [ ] **PASS** — DataProperty reference matches input
- [ ] **PASS** — PropValue typed as DesignStateParameter
- [ ] **PASS** — No component errors

---

### Step 7: DESIGN STATE Composition

**Action (Grasshopper):**
1. Place DESIGN STATE component on canvas
2. Connect ObjState(s) from OBJECT STATE → ObjStates input
3. Connect ParamState(s) from PARAMETER STATE → ParamStates input
4. Connect PropState(s) from PROPERTY STATE → PropStates input
5. Run the definition
6. Inspect DESIGN STATE output: DesignState

**Expected output:**
- DesignState output is a single DesignState object
- `StateId` is derived deterministically from sorted member IDs (DS_ prefix)
- `ObjStates` contains all connected ObjState items
- `ParamStates` contains all connected ParamState items
- `PropStates` contains all connected PropState items
- 3-part bag composition: independent lists, no cross-index alignment
- If lists have mismatched counts, explicit component error (not silent misalignment)

- [ ] **PASS** — DesignState output non-null with deterministic StateId
- [ ] **PASS** — ObjStates list matches inputs
- [ ] **PASS** — ParamStates list matches inputs
- [ ] **PASS** — PropStates list matches inputs
- [ ] **PASS** — Independent bag semantics (no cross-index alignment)
- [ ] **PASS** — Index-mismatch produces explicit component error

---

### Step 8: VALIDATOR Publish

**Action (Grasshopper):**
1. Place VALIDATOR component on canvas
2. Connect Rule (from RULE DECONSTRUCT) → Rule input
3. Connect DesignState (from DESIGN STATE) → DesignState input
4. Set `Run = true` (Boolean toggle)
5. Set `SendValid = true` (Boolean toggle)
6. Ensure DataServiceUrl input is set: `http://data-service:8000`
7. Ensure Speckle config is complete (project ID, base model ID via integration config)
8. Run the definition
9. Inspect VALIDATOR outputs: ValidStatus, RuleName, RuleDescription, SendStatus

**Expected output:**
- ValidStatus is a list of Booleans, one per ObjState
- RuleName matches the input Rule's RuleName
- RuleDescription matches the input Rule's RuleDescription (may be empty)
- SendStatus = true (publish succeeded)
- Report output indicates any failing bindings
- ValidationRunId is non-empty
- ModelViewerUrl is non-empty (if Speckle configured)

- [ ] **PASS** — ValidStatus output: Boolean list (index-matched to ObjStates)
- [ ] **PASS** — RuleName and RuleDescription passthrough intact
- [ ] **PASS** — SendStatus = true
- [ ] **PASS** — ValidationRunId non-empty
- [ ] **PASS** — No binding errors for correctly configured inputs
- [ ] **PASS** — ModelViewerUrl populated (if Speckle configured)

---

### Step 9: Neo4j Verification of Published Run

**Action:**
```bash
curl -s --max-time 15 -X POST http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -u neo4j:12345678 \
  -d '{
    "statements": [{
      "statement": "MATCH (run:ValidationRun {project: '\''e2e-v7-test-{timestamp}'\''}) RETURN run.runId, run.ValidStatus, run.SendStatus, run.statePayloadJson, run.createdAt ORDER BY run.createdAt DESC LIMIT 3"
    }]
  }'
```

**Expected output:**
- At least one ValidationRun node exists for the test project
- `ValidStatus` is a Boolean array
- `SendStatus` = true
- `statePayloadJson` is a v2 JSON string with keys: `version`, `stateId`, `capturedAtUtc`, `objStates`, `paramStates`, `propStates`
- `statePayloadJson.objStates` contains the published ObjState items with StateId, ObjectRef, Label
- `statePayloadJson.paramStates` contains the published ParamState items with StateId, Parameters
- `statePayloadJson.propStates` contains the published PropState items with StateId, RuleName, DataProperty, PropValue
- `run.ValidStatus` array length matches `statePayloadJson.objStates` count

- [ ] **PASS** — ValidationRun node exists
- [ ] **PASS** — ValidStatus is Boolean array, SendStatus = true
- [ ] **PASS** — statePayloadJson is v2 format with objStates/paramStates/propStates keys
- [ ] **PASS** — ValidStatus array length matches ObjState count
- [ ] **PASS** — statePayloadJson contains all expected state data

---

### Step 10: VALIDATION GRAPH Read-Back

**Action (Grasshopper):**
1. Wire CONNECTOR → GRAPH DECONSTRUCT → VALIDATION GRAPH (connect ValidGraph handle)
2. Run the definition
3. Inspect VALIDATION GRAPH outputs: Run, Status, DesignState

**Expected output:**
- Run output: RunInfo with runId matching the published run
- Status output: List of per-ObjState Booleans (same as ValidStatus)
- DesignState output: DesignState matching what was published
- DesignState ObjStates/ParamStates/PropStates match the statePayloadJson content
- All outputs are read from the ValidGraph layer (graph='ValidGraph')
- No component errors

Alternatively via data-service REST:
```bash
curl http://localhost:8000/validation/view/e2e-v7-test-{timestamp}
```

Should return the validation view payload with run, rules, and objectSets.

- [ ] **PASS** — Run output matches published run
- [ ] **PASS** — Status matches ValidStatus from Neo4j
- [ ] **PASS** — DesignState read-back matches published statePayloadJson
- [ ] **PASS** — No component errors
- [ ] **PASS** — Data-service REST endpoint returns correct validation view

---

### Step 11: MODEL VIEWER Render

**Action:**
1. Open `http://localhost:8080/model-viewer/?project=e2e-v7-test-{timestamp}` in a browser
2. Observe the validation run strip

**Expected output:**
- Model Viewer loads without errors
- Validation run appears in the run strip
- Run shows rule name and status indicators
- State grouping works: clicking group-by-State shows the correct state groups
- Model viewer canvas renders with correct colors per validation status (if geometry published)
- No console errors in browser DevTools

- [ ] **PASS** — Model Viewer loads without errors
- [ ] **PASS** — Validation run listed in run strip
- [ ] **PASS** — State grouping produces correct groups
- [ ] **PASS** — No console errors

---

### Step 12: PARAMETER REINSTATE

**Action (Grasshopper):**
1. Place PARAMETER REINSTATE component on canvas
2. Connect ParamState (from a stored run via VALIDATION GRAPH, or from a fresh PARAMETER STATE) → ParamState input
3. Connect Target parameters (matching sliders/toggles) → Target input (Input 1)
4. Set `Reinstate = false` (no action yet)
5. Run definition — observe no changes
6. Set `Reinstate = true` (rising edge)
7. Run definition again (rising edge trigger fires)
8. Inspect PARAMETER REINSTATE outputs: Parameters, StateStatus

**Expected output:**
- With `Reinstate = false`: no parameter changes, no output
- With `Reinstate = true` (first solve after false→true):
  - Parameters output: list of parameters with values applied from ParamState
  - StateStatus: 7-value ReStatus per parameter (index-matched to Parameters)
    - ReStatus values: NotAttempted, InvalidSource, Success, TypeMismatch, RangeError, TargetUnavailable, Exception
  - Each source slider/toggle updates to match the ParamState value
- Subsequent solves with `Reinstate = true` (no rising edge): no re-application
- Toggle `Reinstate → false → true` again: re-applies (rising edge detected)

- [ ] **PASS** — Reinstate=false: no action, no output
- [ ] **PASS** — First true rising edge: Parameters output matches ParamState values
- [ ] **PASS** — StateStatus reports Success for each parameter
- [ ] **PASS** — Slider/toggle values updated on canvas
- [ ] **PASS** — No re-application on subsequent true solves (no rising edge)
- [ ] **PASS** — Toggle false→true re-applies correctly
- [ ] **PASS** — StateStatus correctly reports errors for unreachable targets

---

### Step 13: Existing Project Smoke Test

**Action:**
1. Open an existing `.gh` file built with v2.0/v3.0 components (CLASSIFICATOR, VALIDATION RUNS, old REINSTATE, DESIGN STATE)
2. Observe the canvas

**Expected output:**
- Missing-component placeholders appear for:
  - CLASSIFICATOR (component removed in v7.0)
  - VALIDATION RUNS (replaced by VALIDATION GRAPH)
  - OLD REINSTATE (replaced by PARAMETER REINSTATE, new GUID)
- Geometry and other standard GH components unaffected
- No crashes or errors from the missing components (graceful placeholders)
- Create a NEW .gh file adjacent to the old one and re-wire per release notes:
  - Replace CLASSIFICATOR chain with OBJECT STATE + PROPERTY STATE + DESIGN STATE
  - Replace VALIDATION RUNS with VALIDATION GRAPH
  - Replace old REINSTATE with PARAMETER REINSTATE
- Verify the full chain works on the existing project data
- Run `bash test/smoke_e2e.sh` again to confirm no regression

- [ ] **PASS** — Old .gh file loads without crashes
- [ ] **PASS** — Missing-component placeholders render correctly
- [ ] **PASS** — Re-wired .gh file produces correct results for existing data
- [ ] **PASS** — Smoke test still passes after re-wiring

---

## Troubleshooting

### Step 1 Failures

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `curl: (28) connection timed out` after 210s | Ollama cold start | Wait for Ollama: `docker logs ollama -f --tail 20` |
| No `executionId` in response | n8n workflow not active | Import and activate via n8n UI or CLI |
| Rule nodes have empty/null SWRL | Old v3 workflow definition | Re-import rules-to-metagraph.json per GOTCHA above |
| "No Rule nodes created" | Project name mismatch or workflow error | Check n8n execution logs: `docker logs n8n --tail 50` |

### Step 2-7 Failures (Grasshopper)

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| CONNECTOR shows "Unable to connect" | Neo4j unreachable from Rhino | Verify `bolt://localhost:7687` is correct; check Neo4j is running: `docker compose ps neo4j` |
| METAGRAPH returns empty Rules | Project name mismatch | Verify CONNECTOR Project input matches the project name used in Step 1 |
| RULE DECONSTRUCT wrong partition | VariableTypeInferrer issue | Check if builtins appear in outputs; may need VariableTypeInferrer debug |
| OBJECT STATE errors | Geometry type not supported | Ensure Rhino geometry is a Brep/Mesh/Extrusion |
| Index-mismatch errors | List count mismatch between inputs | Verify all list inputs have same number of elements |

### Step 8-9 Failures (Validator/Publish)

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `SendStatus = false` | Speckle config missing | Set speckleProjectId and baseModelId via web UI |
| `SPECKLE_CONFIG_MISSING` error | No IntegrationConfig in DB | POST /integration/speckle/project/{project} via data-service |
| ValidStatus all false | Binding errors | Check VALIDATOR Report output for failing bindings |
| statePayloadJson is v1 format | Old VALIDATOR code path | Verify VALIDATOR receives composed DesignState (not DefState) |

### Step 10 Failures

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| VALIDATION GRAPH returns empty | No runs in ValidGraph for this project | Verify Step 9 showed a ValidationRun node |
| Data-service 404 | Wrong project name | Double-check project name matches |
| DesignState read-back doesn't match | v1-v2 compatibility issue | Check run.statePayloadJson schema version |

### Step 11 Failures (Model Viewer)

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Empty run strip | _project_state_summary returns null | Check run has statePayloadJson v2 |
| Grouping doesn't work | stateId missing or wrong format | Verify stateId is populated in statePayloadJson |
| Model viewer blank | Speckle version not published | Check Speckle server logs for publish errors |

### Step 12 Failures (PARAMETER REINSTATE)

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Nothing happens on Reinstate=true | No rising edge | Toggle Reinstate false→true (rising edge required) |
| StateStatus all NotAttempted | Target wire not on Input 1 | Verify Target parameters connected to Input 1 (Parameter input, not Target) |
| TypeMismatch errors | Parameter type doesn't match target | Ensure ParamState Number→Number slider, Boolean→Boolean toggle |
| Wrong parameters applied | ParamState contains different parameters | Verify ParamState was captured from the same canvas configuration |

### General

| Check | Command |
|-------|---------|
| Docker compose status | `docker compose ps` |
| n8n workflow status | `docker exec n8n n8n list:workflows` |
| Neo4j console | Open http://localhost:7474 in browser (neo4j/12345678) |
| Ollama logs | `docker logs ollama -f --tail 50` |
| data-service logs | `docker logs data-service -f --tail 50` |
| n8n execution logs | `docker exec n8n n8n executions --all` |
| Check published runs | `curl http://localhost:8000/validation/runs/{project}` |

---

## Final Sign-Off

### All Steps Passed

- [ ] Step 1: Rule Ingest
- [ ] Step 2: METAGRAPH Read
- [ ] Step 3: RULE DECONSTRUCT Partition
- [ ] Step 4: OBJECT STATE
- [ ] Step 5: PARAMETER STATE
- [ ] Step 6: PROPERTY STATE
- [ ] Step 7: DESIGN STATE Composition
- [ ] Step 8: VALIDATOR Publish
- [ ] Step 9: Neo4j Verification
- [ ] Step 10: VALIDATION GRAPH Read-Back
- [ ] Step 11: MODEL VIEWER Render
- [ ] Step 12: PARAMETER REINSTATE
- [ ] Step 13: Existing Project Smoke Test

### Docker Automation

- [ ] `bash test/smoke_e2e.sh` exits 0 (all PASS)

### Unit Tests

- [ ] `dotnet test DG/tests/DG.Tests/` passes all tests

### Known Issues

<!-- Document any deferred bugs or known limitations here -->

---

### Sign-Off

**Date:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Tester:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Result:** All checkboxes checked — no critical bugs remaining

---

*Generated for Phase 20 (20-01) E2E Validation. Revision 1.*
