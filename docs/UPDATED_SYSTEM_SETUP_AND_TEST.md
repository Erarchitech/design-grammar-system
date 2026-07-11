# Updated Design Grammars System: Setup And Test Guide

This guide covers the full local setup and test flow for the updated Design Grammars system, including:

- Neo4j
- n8n
- Ollama
- `data-service`
- DG web UI
- local Speckle server
- Grasshopper validation publishing
- DG `Model Viewer`

It is written for the implementation currently in this repository.

## 1. What The Updated System Does

The updated stack has two parallel outputs:

1. Semantic validation in Grasshopper.
   - Rules are still evaluated only against `BindingRow.ValuesByVar`.
   - Geometry does not affect pass/fail logic.

2. Visual validation overlay in Speckle and DG `Model Viewer`.
   - `BindingRow.ElementRefsByVar` carries `dgEntityId` plus optional geometry.
   - When `VALIDATOR.SendRules = True`, Grasshopper posts a validation package to `data-service`.
   - `data-service` publishes a DG validation overlay model to Speckle and stores run metadata in Neo4j.
   - DG `Model Viewer` loads the captured base model version and the DG validation overlay version for the selected rule.

## 2. Prerequisites

Required:

- Windows with PowerShell
- Docker Desktop with Docker Compose v2
- Internet access to pull Docker images
- .NET SDK 9.x for DG build/tests

Required for Grasshopper validation testing:

- Rhino 8
- Grasshopper

Required for full Revit-to-Speckle overlay testing:

- Revit
- A Speckle connector that can publish your Revit model to the local Speckle server

Recommended:

- At least 16 GB RAM, because Neo4j, n8n, Ollama, and Speckle all run at once
- A GPU for Ollama

If Ollama cannot run with your current Docker/GPU setup, you can still test the Speckle integration path after rules already exist in Neo4j.

## 3. Repository Build Verification

From the repository root:

```powershell
dotnet test .\DG\DG.sln
python -m compileall .\data-service
docker compose build data-service design-grammars
```

Optional frontend-only verification:

```powershell
Set-Location .\graph-viewer\model-viewer
npm install
npm run build
Set-Location ..\..
```

Expected result:

- DG tests pass
- Python compile check finishes without syntax errors
- Docker images for `data-service` and `design-grammars` build successfully

## 4. Environment Variables

The updated stack reads these values at runtime:

- `SPECKLE_WRITE_TOKEN`
- `SPECKLE_READ_TOKEN`
- `SPECKLE_SESSION_SECRET`

For local development, you have two supported options:

1. Set them in PowerShell before starting containers:

```powershell
$env:SPECKLE_WRITE_TOKEN = "31df8a9e0d172f8e26170a4bd3082381fa281f1beb"
$env:SPECKLE_READ_TOKEN = "40bfcd23e349f33a5fc9f074bf65decba0fcce5d33"
$env:SPECKLE_SESSION_SECRET = "design-grammars-to-speckle"
```

2. Or save the write/read tokens once in the DG home page `Speckle Settings` card after the stack is running. `data-service` persists them in `data-service/data/speckle-settings.json` and reuses them after restarts.

Notes:

- You can use the same token for both read and write in local development if that token can both read and write the target project/model.
- The exact access-token scope labels in Speckle may vary by release. For local testing, the safe requirement is that the token must be able to read the base model and create/update versions in the DG validation model.

## 5. Start The Full Stack

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

The important local URLs are:

- DG UI: `http://localhost:8080`
- Speckle: `http://localhost:8090`
- data-service: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474`
- n8n: `http://localhost:5678`
- MinIO console: `http://localhost:9001`

Basic smoke tests:

```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-WebRequest http://localhost:8080 | Select-Object StatusCode
Invoke-WebRequest http://localhost:8090 | Select-Object StatusCode
```

Expected result:

- `data-service` returns `{ "status": "Data Service is running" }`
- DG UI returns HTTP 200
- Speckle returns HTTP 200

## 6. Bootstrap n8n And Ollama

### 6.1 Pull the Ollama model

```powershell
docker exec -it ollama ollama pull llama3.1
```

### 6.2 Import the n8n workflows

```powershell
docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json
docker exec -it n8n n8n import:workflow --input=/files/workflows/graph-query-mcp.json
```

### 6.3 Activate the workflows

Open:

- `http://localhost:5678`

Log in with the credentials from `docker-compose.yml`, then enable both imported workflows.

## 7. Create A Local Speckle Account And Base Model

### 7.1 First login

Open:

- `http://localhost:8090`

Because this self-hosted stack uses local auth, create the first local user directly in the Speckle UI.

### 7.2 Create a project and a base model

Create one project for your DG test case. Then create or publish at least one base model version into that project.

You need a real base model version because DG `Model Viewer` overlays DG validation geometry onto a captured base model version. If the base model has no versions, validation publish will fail.

Ways to create the base model:

- Preferred: publish from Revit to local Speckle
- Acceptable for testing: publish from Rhino/Grasshopper or another Speckle connector

### 7.3 Record the Speckle IDs

After opening the model page in Speckle, copy:

- `projectId`
- `modelId`

They are visible in the model URL:

```text
http://localhost:8090/projects/<projectId>/models/<modelId>
```

### 7.4 Create Speckle access tokens

Create the tokens you want to use for:

- backend write access
- viewer read access

Then export them again in PowerShell if needed and restart the affected services:

```powershell
docker compose up -d data-service design-grammars
```

## 8. Configure DG Project To Speckle Mapping

You can do this in the DG UI or directly through the API.

### 8.1 Option A: configure from the DG UI

Open:

- `http://localhost:8080`

Then open the DG project you want to configure. In that project's graph view, use the left sidebar `Model Viewer` card and fill:

- `Speckle Project Id`
- `Base Model Id`
- `Base Model Name` (optional)
- `Validation Model Id` (optional)

Then click:

- `Save Speckle Link`

Leave `Validation Model Id` empty for the first run. The backend will create or reuse a model named `dg-validation`.

The DG UI accepts either raw Speckle ids or full Speckle project/model URLs in these fields. `data-service` normalizes full URLs to ids automatically.

### 8.2 Option B: configure by API

Example:

```powershell
$project = "urban-block-case-study"
$body = @{
  speckleProjectId = "<projectId>"
  baseModelId = "<modelId>"
  baseModelName = "Revit Base Model"
  validationModelId = $null
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Put `
  -Uri "http://localhost:8000/integration/speckle/project/$project" `
  -ContentType "application/json" `
  -Body $body
```

Verify:

```powershell
Invoke-RestMethod "http://localhost:8000/integration/speckle/project/$project"
```

Expected result:

- the DG project returns the saved Speckle linkage

## 9. Ingest Rules Into DG

Use a project name that matches the project you will use in Grasshopper and in the Speckle link config.

Example:

```powershell
$user = "<n8n_user>"
$pass = "<n8n_password>"
$token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${user}:$pass"))
$headers = @{ Authorization = "Basic $token" }

$body = @{
  project_name = "urban-block-case-study"
  ollama_model = "llama3.1"
  rules_text = "maximum height of each building is 20 meters; minimum gross floor area of each building is 200 square meters."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:5678/webhook/dg/rules-ingest" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Wait for the ingestion run to finish. Then verify in Neo4j:

```cypher
MATCH (r:Rule {graph:'Metagraph', project:'urban-block-case-study'})
RETURN r.id, r.name, r.swrl, r.project
ORDER BY r.id;
```

Expected result:

- rules exist for the selected DG project

## 10. Build And Install The DG Grasshopper Plugin

### 10.1 Build

```powershell
dotnet build .\DG\DG.sln
```

If Rhino 8 is not installed in the default location, use:

```powershell
dotnet build .\DG\DG.sln -p:RhinoInstallDir="D:\Apps\Rhino 8"
```

### 10.2 Install

Copy the DG Grasshopper build output into your Rhino/Grasshopper plugin location, or load the built assembly manually in Rhino during development.

If Rhino SDK DLLs are not present, `DG.Grasshopper` builds as a placeholder assembly and you will not get working Grasshopper components. In that case, fix the Rhino install path first.

## 11. Prepare The Grasshopper Definition

The updated test definition should use these DG components:

- `CONNECTOR`
- `METAGRAPH`
- `RULE DECONSTRUCT`
- `CLASSIFICATOR`
- `VALIDATOR`

### 11.1 `CONNECTOR`

Configure:

- Neo4j URL: `bolt://localhost:7687`
- User: `neo4j`
- Password: `12345678`

### 11.2 `METAGRAPH`

Load the rules for the DG project used during ingestion:

- project: `urban-block-case-study`

### 11.3 `RULE DECONSTRUCT`

Use this to inspect:

- rule ids
- rule descriptions
- variables

This step is important because the order of variables determines how you build the `Values` and `ElementRefs` trees for `CLASSIFICATOR`.

### 11.4 `CLASSIFICATOR`

Inputs:

- `Variables`
- `Values`
- `ElementRefs` (optional, but required for model overlay publishing)

Rules for the `Values` tree:

- one branch per variable
- branch index must match variable index from `RULE DECONSTRUCT`
- item order across branches must align by row

Example if variables are:

```text
?b, ?h, ?a
```

Then:

- branch 0 contains entity keys for `?b`
- branch 1 contains heights for `?h`
- branch 2 contains areas for `?a`

Rules for the `ElementRefs` tree:

- branch index must match the corresponding entity variable branch
- item order must match the row order in `Values`
- you only need branches for variables that represent mapped entities

Accepted `ElementRefs` values:

- `DG.ElementRef`
- a plain string representing `dgEntityId`
- an object or dictionary with:
  - `DgEntityId`
  - `Geometry` (optional)
  - `DisplayName` (optional)

Supported geometry serialization types:

- `Mesh`
- `Brep`
- `Surface`
- `Extrusion`
- `Curve`
- `Polyline`
- `Line`
- `Point3d`
- `Rhino.Geometry.Point`
- collections of the above

Important:

- `dgEntityId` must match the ID you use to relate the Grasshopper element to the Speckle/Revit element.
- Geometry is used only for the DG validation overlay model.
- Pass/fail still depends only on the scalar values sent in `Values`.

### 11.5 `VALIDATOR`

Inputs:

- `Rules`
- `Variables`
- `Run`
- `SendRules`
- `DataServiceUrl`

Use:

- `Run = True`
- `SendRules = True`
- `DataServiceUrl = http://localhost:8000`

Outputs to inspect:

- `Pass`
- `RuleName`
- `RuleDescription`
- `Report`
- `FailingBindings`
- `PublishStatus`
- `ValidationRunId`
- `ModelViewerUrl`

Expected result:

- semantic validation still works exactly as before
- `PublishStatus` returns `published`
- `ValidationRunId` is a non-empty value
- `ModelViewerUrl` points to DG `Model Viewer`

## 12. API-Level Validation Checks

After a successful Grasshopper publish, verify the backend state directly.

### 12.1 Latest validation manifest

```powershell
Invoke-RestMethod "http://localhost:8000/validation/view/urban-block-case-study"
```

Expected fields:

- `runId`
- `baseModelId`
- `baseVersionId`
- `validationModelId`
- `validationVersionId`
- `rules`
- `objectSets`

### 12.2 Rule-specific manifest

```powershell
Invoke-RestMethod "http://localhost:8000/validation/view/urban-block-case-study/<runId>/<ruleId>"
```

Expected result:

- `objectSets.failed` contains the DG entity ids failing that rule
- `objectSets.passed` contains the DG entity ids passing that rule

### 12.3 Neo4j validation-run check

Run in Neo4j Browser:

```cypher
MATCH (run:ValidationRun {graph:'ValidationGraph', project:'urban-block-case-study'})
RETURN run.runId, run.baseVersionId, run.validationVersionId, run.createdAt
ORDER BY run.createdAt DESC;
```

And:

```cypher
MATCH (ve:ValidationEntity {graph:'ValidationGraph', project:'urban-block-case-study'})
RETURN ve.runId, ve.ruleId, ve.dgEntityId, ve.status
ORDER BY ve.runId DESC, ve.ruleId, ve.dgEntityId;
```

Expected result:

- one `ValidationRun` node per publish
- one or more `ValidationEntity` nodes per published entity/rule pair

## 13. Test The DG Model Viewer

### 13.1 Open the returned URL

The preferred path is the `ModelViewerUrl` output from `VALIDATOR`.

You can also open the generic project route:

```text
http://localhost:8080/model-viewer/?project=urban-block-case-study
```

### 13.2 What to verify in the viewer

Verify all of the following:

- the page loads without a backend error
- the base Speckle model is visible
- the DG validation overlay is visible
- selecting a rule changes the highlighted overlay set
- failing elements are highlighted by default
- passing elements can be toggled on and off
- rules with no geometry show the empty mapped-geometry message

### 13.3 Open from the main DG page

From `http://localhost:8080`, open the `Model Viewer` card and click:

- `Open Model Viewer`

This confirms that the DG UI is correctly loading the saved Speckle integration config and routing to the new viewer.

## 14. Recommended End-To-End Test Matrix

Run these tests in order.

### Test A: stack startup

Goal:

- all containers start
- DG UI, Speckle, and `data-service` are reachable

Pass criteria:

- `docker compose ps` shows all required services running
- the three main URLs return successfully

### Test B: rules ingestion

Goal:

- rules are written into Neo4j for one DG project

Pass criteria:

- `Rule` nodes exist in `Metagraph`

### Test C: project-to-Speckle mapping

Goal:

- the DG project can resolve its base Speckle model

Pass criteria:

- `GET /integration/speckle/project/{project}` returns the saved model ids

### Test D: semantic validation only

Goal:

- existing validation behavior is unchanged when `SendRules=False`

Pass criteria:

- `Pass`, `Report`, and `FailingBindings` behave as before

### Test E: validation publish

Goal:

- Grasshopper publishes one DG validation overlay version to Speckle

Pass criteria:

- `PublishStatus = published`
- `ValidationRunId` is returned
- `validationModelId` and `validationVersionId` exist in API response

### Test F: viewer overlay

Goal:

- DG `Model Viewer` correctly filters and highlights published entities by rule

Pass criteria:

- failing entities show in the viewport
- passing entities can be toggled
- switching rule updates the overlay without republishing

## 15. Common Failure Cases

### `POST /validation/publish` returns 404

Cause:

- no Speckle config exists for that DG project

Fix:

- save the DG project mapping in the DG UI or `PUT /integration/speckle/project/{project}`

### `POST /validation/publish` returns 500 and mentions write token

Cause:

- no Speckle write token is available to `data-service`

Fix:

- open `http://localhost:8080`
- save the token in the home page `Speckle Settings` card, or set `SPECKLE_WRITE_TOKEN` in PowerShell
- if you changed PowerShell env vars instead of using the UI, restart `data-service`

### publish fails because the base model has no versions

Cause:

- the Speckle base model exists, but nothing has been published to it

Fix:

- publish at least one base-model version from Revit, Rhino, or another connector

### overlay geometry does not appear

Cause:

- `SendRules=False`
- `ElementRefs` tree is empty
- `ElementRefs` contain ids but no geometry
- geometry type is unsupported by the serializer

Fix:

- set `SendRules=True`
- provide `ElementRefs` for the mapped entity variables
- make sure each entity has both a `dgEntityId` and publishable Rhino geometry

### viewer opens but shows no highlighted elements

Cause:

- DG entity ids in the rule-specific manifest do not match the ids stored on published overlay objects
- the selected rule has no mapped geometry

Fix:

- verify `dgEntityId` consistency from Grasshopper through publish payload
- check `GET /validation/view/{project}/{runId}/{ruleId}`

### project creation in Speckle succeeds in the dialog but no project appears

Cause:

- the local Speckle seed created the internal web app token without `workspace:read`
- the `CreateProject` GraphQL response then fails on the `workspace` field and the project is not returned to the UI

Fix:

- use the patched compose stack from this repository
- run:

```powershell
docker compose up -d speckle-postgres speckle-server speckle-frontend-2 speckle-ingress
```

- refresh `http://localhost:8090/projects`
- if you were already logged in before the fix, sign out and sign in again

### Grasshopper publish works but base Revit model does not match overlay context

Cause:

- the base model in Speckle does not use the same DG entity ids or stable mapping you assumed

Fix:

- ensure the GH entity mapping and the Speckle/Revit mapping use the same shared IDs

## 16. Useful Commands

View logs:

```powershell
docker logs -f data-service
docker logs -f design-grammars
docker logs -f speckle-ingress
docker logs -f speckle-server
docker logs -f neo4j
```

Restart only changed services:

```powershell
docker compose up -d --build data-service design-grammars
```

Rebuild the DG solution:

```powershell
dotnet build .\DG\DG.sln
dotnet test .\DG\DG.sln
```

## 17. External References

These official Speckle docs are useful for the parts that happen outside this repository:

- Self-hosting / Docker Compose: `https://docs.speckle.systems/developers/server/docker-compose`
- Server architecture: `https://docs.speckle.systems/developers/server/architecture`
- Getting started with self-hosted Speckle: `https://docs.speckle.systems/developers/server/getting-started`
- Speckle Viewer docs: `https://docs.speckle.systems/developers/viewer`
- Speckle Python SDK docs: `https://docs.speckle.systems/developers/sdks/python`
