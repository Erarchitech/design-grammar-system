# Phase 1303 MVP slice — Mapping API contract (v0.1)

Shared contract for plans 1303-01 (engine), 1303-02 (routes/persistence), 1303-03 (Grasshopper script), 1303-04 (Revit read adapter) and 1303-05 (Web UI). Any change to these shapes is made here first and announced to every dependent plan. JSON keys are camelCase. All numbers in SI (metres, square metres) unless a field name says otherwise.

## 1. ElementDescriptor (input)

```json
{
  "nativeId": "string, required, unique within one request",
  "platform": "grasshopper | revit (optional; defaults to the session platform)",
  "source": "GH stream / output nickname, e.g. \"HU\" (optional)",
  "category": "Revit category name, e.g. \"Generic Models\" (optional)",
  "family": "Revit family name (optional)",
  "type": "Revit type name (optional)",
  "name": "free label (optional)",
  "ifc": { "entity": "IfcBuildingElementProxy", "predefinedType": null },
  "geometry": {
    "kind": "curve | surface | brep | mesh | box | point | other",
    "vertexCount": 6,
    "gapCount": 0,
    "closed": true,
    "planarityDeviationM": 0.0004,
    "zMinM": 0.0,
    "zMaxM": 3.2,
    "areaM2": 1.1,
    "widthM": 1.2,
    "heightM": 3.1
  },
  "properties": { "hasVertexCount": 6, "hasGapCount": 0 },
  "parameters": { "Mark": "A-01" }
}
```

- `properties` are measured values keyed by the **local name of a DG DatatypeProperty** (e.g. `hasVertexCount`, `hasAspectRatio`, `hasPlanarityDeviationM`, `hasWidthM`, `hasTotalHeightM`, `hasGapCount`, `hasLevelOffsetM`). When a property is absent, the engine falls back to the geometry alias table (`hasVertexCount ← geometry.vertexCount`, `hasGapCount ← geometry.gapCount`, `hasWidthM ← geometry.widthM`, `hasPlanarityDeviationM ← geometry.planarityDeviationM`).
- `parameters` values are strings or numbers (Revit display values or SI numbers). No secrets, no file paths outside the project.
- GH `nativeId` convention: `gh:<definitionKey>:<source>:<branchPath>:<index>` (e.g. `gh:facade-v1:HU:{0;72}:0`). Revit `nativeId`: the element `UniqueId`.

## 2. Routes

All routes take and return JSON. `project` is always in the request body (POST) or query (GET), because a connector session only passes when its bound project equals the requested project.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| POST | `/mapping/sessions` | `{project, platform, label?, elements: [ElementDescriptor], context?: {populationsFromSessionId?}}` | `MappingSession` |
| GET | `/mapping/sessions/{sessionId}` | `?project=` | `MappingSession` |
| GET | `/mapping/sessions` | `?project=&limit=20` | `{sessions: [MappingSessionSummary]}` newest first |
| POST | `/mapping/sessions/{sessionId}/decisions` | `{project, questionId, optionId, groupIds?: [..], roles?: [classIri], comment?}` | `{decisions: [MappingDecision], profiles: [MappingProfile], session: MappingSession}` |
| POST | `/mapping/sessions/{sessionId}/apply` | `{project}` | `MappingApplyResult` |
| GET | `/mapping/profiles` | `?project=` | `{profiles: [MappingProfile]}` |
| POST | `/mapping/profiles` | `{project, platform, selector, roles, comment?}` (authored profile) | `MappingProfile` |

Error envelope: the existing data-service error shape (`{code, detail}` with HTTP 400/401/403/404/409). New codes: `MAPPING_SESSION_NOT_FOUND` (404), `MAPPING_QUESTION_NOT_FOUND` (404), `MAPPING_OPTION_INVALID` (400), `MAPPING_INPUT_INVALID` (400), `MAPPING_TOO_MANY_ELEMENTS` (400, limit 5000).

## 3. MappingSession

```json
{
  "sessionId": "ms-<12 hex>",
  "project": "v12-hexagonal-facade-01",
  "platform": "grasshopper",
  "label": "act1-cold-start",
  "engineVersion": "dgmap-0.1",
  "createdAt": "2026-10-18T09:00:00Z",
  "createdBy": "owner-username",
  "summary": { "total": 376, "confirmed": 0, "auto": 0, "suggested": 351, "ambiguous": 25, "unmapped": 0, "openQuestions": 2 },
  "questions": [Question],
  "groups": [Group],
  "elements": [ElementResult]
}
```

`MappingSessionSummary` = the session without `questions`, `groups` and `elements`.

### Group

```json
{
  "groupId": "G-<8 hex>",
  "size": 25,
  "signature": { "platform": "grasshopper", "source": "HU", "geometry.kind": "curve", "geometry.vertexCount": 5 },
  "representatives": ["gh:facade-v1:HU:{0;72}:0", "...", "..."],
  "status": "suggested | ambiguous | auto | confirmed | unmapped",
  "candidates": [
    { "classIri": "ex:GroundFloorUnit", "label": "GroundFloorUnit", "score": 3.1, "confidence": 0.957,
      "evidence": [ { "kind": "rule", "weight": 1.5, "detail": "R_GF_HASVERTEXCOUNT_REQ_5_V satisfied (hasVertexCount = 5)" } ],
      "conflicts": [] }
  ],
  "ruleImpact": [ { "classIri": "ex:HexagonalUnit", "rules": [ { "ruleId": "R_HEX_HASVERTEXCOUNT_REQ_6_V", "satisfied": 0, "violated": 25, "notMeasured": 0 } ] } ],
  "priority": 7.42,
  "questionId": "Q-<8 hex> or null"
}
```

### Question

```json
{
  "questionId": "Q-<8 hex>",
  "type": "batch-assign | assign | disambiguate | mapping-or-design",
  "groupIds": ["G-..."],
  "text": "Canonical deterministic text (English); the UI translates the fixed parts",
  "textRu": "Каноническая детерминированная формулировка",
  "options": [
    { "optionId": "accept-all", "label": "Accept all proposed classes", "roles": null },
    { "optionId": "class:ex:GroundFloorUnit", "label": "GroundFloorUnit", "roles": ["ex:GroundFloorUnit"] },
    { "optionId": "design-error:ex:HexagonalUnit", "label": "HexagonalUnit — rule violations are design errors", "roles": ["ex:HexagonalUnit"] },
    { "optionId": "both", "label": "Both roles", "roles": ["ex:HexagonalUnit", "ex:FacadeModule"] },
    { "optionId": "split:geometry.vertexCount", "label": "Split by geometry.vertexCount", "roles": null },
    { "optionId": "none", "label": "None of these", "roles": [] }
  ],
  "consequences": [ { "optionId": "class:ex:GroundFloorUnit", "rules": [ { "ruleId": "R_GF_HASVERTEXCOUNT_REQ_5_V", "effect": "passes", "count": 25 } ] } ]
}
```

- `batch-assign` covers all clear groups; `optionId` `accept-all` accepts every listed group; to exclude groups the client sends `groupIds` with the subset to accept.
- `explanation` (optional, string) may be added by the LLM paraphrase route later; the canonical `text`/`textRu` are always present and are the only text used by tests.

### ElementResult

```json
{ "nativeId": "...", "groupId": "G-...", "state": "confirmed | auto | suggested | ambiguous | unmapped",
  "roles": [ { "classIri": "ex:GroundFloorUnit", "state": "confirmed", "source": "human | profile", "confidence": 1.0, "profileId": "P-..." } ],
  "designSignals": [ { "ruleId": "R_GP_WIDTH_MIN_4.5_V", "classIri": "ex:GlassPanel", "detail": "hasWidthM = 4.4 < 4.5" } ] }
```

## 4. MappingDecision and MappingProfile

```json
{ "decisionId": "D-<12 hex>", "sessionId": "ms-...", "project": "...", "questionId": "Q-...", "groupId": "G-...",
  "optionId": "class:ex:GroundFloorUnit", "roles": ["ex:GroundFloorUnit"], "memberCount": 25,
  "questionText": "...", "evidenceShown": [ ... ], "consequencesShown": [ ... ],
  "decidedBy": "owner-username", "decidedAt": "2026-10-18T09:05:00Z", "profileId": "P-..." }
```

```json
{ "profileId": "P-<12 hex>", "project": "...", "platform": "grasshopper | revit | *",
  "selector": { "source": "HU", "geometry.vertexCount": 5 },
  "roles": ["ex:GroundFloorUnit"], "excludedRoles": [], "acceptsViolations": [],
  "source": "learned | authored", "confirmations": 1, "rejections": 0, "confidence": 0.8333, "support": 25,
  "createdBy": "owner-username", "createdAt": "...", "decisionIds": ["D-..."], "engineVersion": "dgmap-0.1" }
```

- `profileId` is a deterministic hash of `(project, platform, canonical selector, sorted roles)`: the same decision twice increments `confirmations` on the same profile.
- `confidence = (confirmations + 4) / (confirmations + rejections + 5)`; auto-apply when `confidence >= 0.8` and no blocking conflict (see 1303-CONTEXT D-10, D-25).

## 5. MappingApplyResult

```json
{ "project": "...", "sessionId": "ms-...", "applied": 376,
  "byClass": { "ex:HexagonalUnit": ["gh:..."], "ex:GroundFloorUnit": ["gh:..."] },
  "elements": [ { "nativeId": "...", "roles": ["ex:HexagonalUnit"] } ],
  "skipped": [ { "nativeId": "...", "reason": "ambiguous | unmapped" } ] }
```

Apply records `appliedAt` / `appliedBy` / `appliedCount` on the `MappingSession` node and returns the partition consumed by the Grasshopper script (one OBJECT STATE per class). It does **not** write `Representation` or `MAPPED_AS` in the MVP slice (1303-CONTEXT D-32).

## 6. Graph model (MVP slice, experimental, `graph:'Computgraph'`, project-scoped)

```
(:MappingSession {sessionId, project, graph, platform, label, engineVersion, createdAt, createdBy,
                  summaryJson, resultJson, appliedAt?, appliedBy?, appliedCount?})
  -[:HAS_DECISION]->(:MappingDecision {decisionId, project, graph, sessionId, questionId, groupId, optionId,
                                       rolesJson, memberCount, questionText, evidenceJson, consequencesJson,
                                       decidedBy, decidedAt})
  -[:CREATED_PROFILE]->(:MappingProfile {profileId, project, graph, platform, selectorJson, rolesJson,
                                         excludedRolesJson, acceptsViolationsJson, source, confirmations,
                                         rejections, support, createdBy, createdAt, updatedAt, engineVersion})
  -[:ASSIGNS_ROLE]->(:Class)
```

Merge keys: `MappingSession(sessionId, project)`, `MappingDecision(decisionId, project)`, `MappingProfile(profileId, project)`. All three labels are added to `LOCKED_NODE_LABELS`.
