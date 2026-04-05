---
tags: [decision, speckle, validation, 3d]
date: 2026-04-05
---

# Validation Results Publish to Speckle as Overlay Versions

## Decision

When the Grasshopper VALIDATOR component (or any client) sends results to `POST /data-service/validation/publish`, the data-service creates a **new Speckle version** in a dedicated `dg-validation` model within the user's Speckle project.

## Data Structure

```
Speckle Base Object
├── name: "DG Validation {run_id}"
├── dgProject, validationRunId, baseModelId, baseVersionId
├── rules: [{ruleId, ruleName, ruleDescription, passed}]
└── elements: [ValidationEntity]
    └── ValidationEntity
        ├── dgEntityId, displayName
        ├── ruleIds, failedRuleIds, passedRuleIds, overallStatus
        └── displayValue: [Mesh | Point | Line | Polyline]
```

## Flow

1. Grasshopper evaluates rules against bound geometry
2. `ValidationPublishPackageBuilder` aggregates per-entity pass/fail
3. HTTP POST to `/validation/publish` with rules + entities + geometry
4. data-service creates Speckle client, sends objects via `ServerTransport`
5. Creates version in validation model
6. Stores `ValidationRun` + `ValidationEntity` nodes in Neo4j
7. Returns `modelViewerUrl` pointing to Model Viewer

## Rationale

- **Separate model** — validation overlay doesn't pollute the base BIM model
- **Version history** — each validation run is a versioned snapshot
- **3D visualization** — Speckle viewer can overlay validation geometry on base model
- **Metadata in Neo4j** — run history, per-entity status queryable alongside design rules

## Related

- [[Speckle hosts 3D BIM models for validation overlay]]
- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
