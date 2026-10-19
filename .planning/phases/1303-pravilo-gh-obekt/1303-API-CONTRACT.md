# Phase 1303 MVP slice — Mapping API contract (v0.1)

Shared contract for plans 1303-01 (engine), 1303-02 (routes/persistence), 1303-03 (Grasshopper script), 1303-04 (Revit read adapter) and 1303-05 (Web UI). Any change to these shapes is made here first and announced to every dependent plan. JSON keys are camelCase. All numbers in SI (metres, square metres) unless a field name says otherwise.

Latest rollout evidence: [1303-EXPLICIT-CONFIRMATION-ROLLOUT.md](1303-EXPLICIT-CONFIRMATION-ROLLOUT.md). Implementation checkpoints below are historical; the rollout note distinguishes deployed services/plugins from the pending Desktop build and live CAD acceptance.

## Owner amendment — 2026-10-19: explicit partial commits

The former ten-second auto-apply is superseded. Answering a proposal stores a draft; it must not activate learned profiles or write CAD parameters. One **Confirm and write (N)** action commits exactly the pending accepted answers, even while other questions remain. A session can have several immutable batches; committed answers cannot be undone as drafts. Suggested/automatic results outside the selected answers are not included.

`MappingSession` adds `revision` (opaque result revision), `pendingAnswerIds`, and `batches`. Each batch contains `batchId`, `answerIds`, `committedAt`, `payload` (the exact MappingApplyResult subset), and `delivery` (`queued`, `written`, or `failed`). Server commitment is not proof of a completed CAD transaction. Historical terminal `appliedAt` sessions are not replayed.

`POST .../apply` commits `{project, requestId, revision, answerIds}`. IDs must equal the current pending accepted set; an empty, stale, unknown-class or mismatched set is refused. Retrying the same requestId with the same intent returns the same batch; reusing it with different intent is refused. The existing route also accepts a connector delivery receipt `{project, batchId, delivery: {state, written, skipped}}`; only a matching queued batch is acknowledged, never a new selection. Members and project-bound delegated principals with the live editor role or higher may commit; connector credentials may acknowledge CAD delivery but cannot commit. Earlier route-policy attempts were denied and were not bypassed. The owner's subsequent specific authorization resolved this blocker: only this existing apply route now admits delegated editor intent; no credential fallback or alternate execution path is permitted. The connector executes the immutable payload, not the current whole-session result. Draft rejection (no class) does not assign a class or become a positive learned mapping.

The class catalogue and commit-time validation use exact IRIs in the current project's OntoGraph. Rule references alone do not authorize a foreign or removed class.

**Implementation checkpoint (2026-10-19, not deployed):** backend explicit drafts/batches, browser shared confirmation, Revit queued-batch consumer and GH exact subset/incremental placement are implemented locally, not accepted live. Offline Python regression suite: 511 passed; focused C# client/selection tests: 28 passed. The GH assembly builds against the installed Grasshopper SDK. GH uses persisted branch/item selectors, stable native instance references and a session-owned incremental placer; a receipt waits for calculation/output-count verification, and uncertain delivery is not automatically replayed. Binding context may include earlier non-failed committed payloads, never current uncommitted drafts; a connector further restricts it to locally successful history. These tests do not prove real CAD transactions, rollback or process-restart recovery. The specifically authorized delegated `/apply` policy change is now implemented, with bound-project/editor checks and connector-only receipts retained. DeGram shared-button/RPC source is committed as `38d3e7e7` in the authorized standalone clone `D:\dgb\src`: one `degram.mapping.apply {sessionId, requestId, revision, answerIds}` request, stable retry intent, server-selected accepted draft IDs, RU/EN copy and distinct delivery states. It uses only the existing delegated identity and route; an HTTP 403 stays ACCESS_DENIED with no CAD or credential fallback. Live end-to-end confirmation has not been verified. After renewed owner authorization, the official generator ran with the existing build interpreter and both shared contracts were regenerated; `--check` passed. The new RPC was added to DeGram's explicit RPC surface and long-handler pool (DG authorization remains authoritative); its initial `DEGRAM_LOCKED` failures were corrected. Final focused Python mapping/generated-contract checks: 81 passed, including exact intent, canonical answer ordering, refusal preservation and forbidden scope override. The broader DeGram Python run: 483 passed, 1 skipped (before two final focused validation cases were added). Changed-file lint passes without warnings; renderer and Electron TypeScript pass. Final mapping interaction suite: 22 passed, including four accepted answers with six open proposals, double-click suppression, stable refusal/retry intent, old-server fail-closed behavior, written/failed receipt labels and a successful confirmation surviving refresh failure. Broader renderer run: 324 passed, 1 skipped, 1 failed at `ru-catalog-completeness.test.ts` (`settings.plugins.installModal.repoPlaceholder` equals the English URL placeholder); the whole renderer suite is not green. Framework mapping routes/explicit-commit/security-spec checks: 46 passed with host Python. The build interpreter could not collect those framework tests because it lacks `neo4j.GraphDatabase`; no packages were installed into it. The later narrowly scoped route-policy edit succeeded. Real delegated-token tests cover editor commit, bound-project refusal, viewer refusal, connector-only delivery receipts and revocation without cookie fallback. Targeted auth/mapping/security tests: 128 passed; broader backend/Revit tests: 593 passed. Browser tests: 333 passed and Vite production build completed. DeGram source commit: `38d3e7e7`; no packaged build, runtime deployment or live CAD acceptance is claimed at this checkpoint. Complete schema propagation and live verification remain pending. Do not deploy a mixed backend/consumer release.

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
| POST | `/mapping/sessions/{sessionId}/apply` | Member: `{project, requestId, revision, answerIds}`; connector receipt: `{project, batchId, delivery: {state, written, skipped}}` | `MappingBatch` (immutable `payload: MappingApplyResult` plus delivery state) |
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

## 7. Proposal cards, answers, undo, DeGram (plan 1303-10, owner request 2026-10-18)

Shared by the Web UI Mapping panel and the DeGram «Модели → Mapping» sub-tab. Additive: every earlier field stays.

### 7.1 Session additions

```json
{ "document": "v12-hexagonal-facade-01-auto-mapping",
  "questions": [ { "questionId": "Q-…", "type": "mapping-or-design", "text": "…", "textRu": "…",
                   "title": "Panels A · 120 elements: BottomTriangularPanel or GlassPanel?",
                   "titleRu": "Panels A · 120 элементов: BottomTriangularPanel или GlassPanel?",
                   "items": [ { "itemId": "G-…", "kind": "stream", "name": "Panels A",
                                "componentId": "24549b0264794f1bb333b7768ab72820", "count": 120,
                                "proposal": { "iri": "ex:GlassPanel", "label": "GlassPanel" },
                                "alternatives": [ { "iri": "ex:BottomTriangularPanel", "label": "BottomTriangularPanel" } ],
                                "state": "ambiguous" } ],
                   "options": [ … ], "consequences": [ … ] } ],
  "answers": [ { "answerId": "A-…", "questionId": "Q-…", "type": "batch-assign",
                 "title": "…", "titleRu": "…", "optionId": "accept-all",
                 "items": [ { "itemId": "G-…", "kind": "stream", "name": "Panels B", "componentId": "…", "count": 125,
                              "proposal": { "iri": "ex:GlassPanel", "label": "GlassPanel" }, "alternatives": [], "state": "confirmed" } ],
                 "decidedAt": "…", "decidedBy": "…", "undoable": true } ] }
```

- `document`: the GH document key (label before « · », else the `gh:<key>:` prefix of the first element), `null` for imported Revit sessions. Also on every row of `GET /mapping/sessions`.
- `items`: one row per proposed canvas component, never free text. `kind`: `stream` (an element group: its source parameter), `measure` (a calculation output), `parameter` (a slider). `componentId`: the 32-hex GH `InstanceGuid` (stream = source parameter, measure = output parameter, parameter = slider), `null` when unknown (Revit). `count`: elements of the group, values of the output, `null` for a slider. `proposal`: the class or property the system proposes (for a batch question the accepted one), `null` when none. `alternatives`: other candidates (up to 3). `state`: the row's mapping state.
- `title` / `titleRu`: one short line; `text` / `textRu` stay as the full explanation.
- `answers`: the given answers of this session, newest first, undone ones left out. One answer = one `POST …/decisions` (a batch answer covers all its groups). `items` show what was decided. `undoable` = the session is not applied.

### 7.2 Undo

`POST /mapping/sessions/{session_id}/undo` body `{ "project": "…", "answerId": "A-…" }` → the recomputed session (same shape as `GET`).
- Removes the answer's decisions from the session (`decided`, `decidedMeasures`, `decidedParameters`), marks its `MappingDecision` nodes `undoneAt` / `undoneBy`, and reverses its profile effects: a profile the answer created is retired (`state = retired`, `retiredReason = "undone"`), a confirmation or rejection it added is taken back.
- 409 `MAPPING_SESSION_APPLIED` when the session is applied; 404 `MAPPING_ANSWER_NOT_FOUND` for an unknown or already undone answer.
- Policy: `delegated+member`, body, `editor` (same as decisions).

### 7.3 Principals

`GET /mapping/sessions`, `GET /mapping/sessions/{id}`, `GET /mapping/profiles` add `delegated` (viewer); `POST …/decisions` and `POST …/undo` are `delegated+member` (editor). The connector keeps its scope (create, read, apply).

### 7.4 Grasshopper canvas bridge (LISTENER, 127.0.0.1:8720)

New commands, reachable by DeGram (owner 2026-10-18: DeGram has full access to the GH canvas):
- `focus_component` `{ "componentId": "<32 hex>" }` → `{ "found": true, "name": "…" }`: Grasshopper editor to the front, the component's top-level object selected and centred, zoom to fit it.
- `start_mapping` `{}` → `{ "started": true | false, "message": "…" }`: CONNECTOR reads the canvas and creates a session now (needs CONNECTOR signed in).
- `get_mapping_status` `{}` → `{ "document": "…", "sessionId": "ms-…" | null, "message": "<CONNECTOR message>", "signedIn": true }`.

The DeGram client allowlist becomes every command of `CanvasBridgeCommands.All`.

### 7.5 Canvas tags (DG.gha, no wire change)

While a session has open questions or waits for apply, CONNECTOR draws on the canvas (overlay, not document objects, never saved) a coloured frame around each item's component with a tag: `DG ? GlassPanel | BottomTriangularPanel` (ambiguous, orange), `DG · GlassPanel` (suggested, yellow), `DG ✓ GlassPanel` (confirmed, green), `DG ↺ GlassPanel` (auto by profile, blue). Removed once the session is applied. After the last answer CONNECTOR waits 10 s before apply, so the last answer can still be undone.

## 8. DG Revit connector (plans 1303-11..14, owner decisions 2026-10-18, D-44..D-51)

Additive: every earlier field stays.

### 8.1 Revit descriptor

Section 1 with `platform: "revit"`, `nativeId` = element `UniqueId`, `category`, `family`, `type`, `name` (`<family> : <type>`), `ifc` (from IfcExportAs / IfcExportType parameters, EN or RU), and `parameters`: display values, plus `<name>_m` in metres for length doubles. `geometry` carries only `vertexCount` = the number of adaptive placement points of an adaptive component instance; it is absent for other elements. No `widthM` / `heightM` / `planarityDeviationM` are sent, so the GH range rules are never fed Revit bounding boxes. Cross-platform profiles (`platform: "*"`, selector `geometry.vertexCount`) and the vertex-count equality rules therefore apply to Revit unchanged.

### 8.2 Session from the connector

- Read scope: the Revit selection when it is not empty, else every model element instance visible in the active view (no annotations, views or types), at most 5000.
- `POST /mapping/sessions` body `{project, platform: "revit", label: "<document key> · HH:MM:SS", elements}`. The document key is the `.rvt` file name under the GH `DocumentKey` rule (lower case, every character other than a letter, digit, `-` or `_` becomes `-`). The session's `document` is the label part before « · ».
- Populations: `context.populationsFromSessionId` wins; otherwise the latest applied Grasshopper session of the project is used and recorded in the session context. `populations_of` returns `{classLocal: [sizes]}`, one size per applied group: per GH `stream`, else per `groupId`. A Revit group gets population evidence only when its size matches exactly one class (125 = GlassPanel and BottomTriangularPanel gives none). The old `{class: n}` shape is still read.
- No LLM proposal is asked for Revit sessions.

### 8.3 Connector routes (pyRevit Routes API `dg_revit`, `http://127.0.0.1:48884/dg_revit/…`) and MCP tools

| Route | MCP tool | Body / result |
|---|---|---|
| `GET /mapping_status/` | `dg_mapping_status` | `{signedIn, project, user?, document, sessionId, message}` |
| `POST /start_mapping/` | `dg_start_mapping` | `{}` → `{started, sessionId, message}` (needs sign-in; reads the scope, posts the session, colours the elements) |
| `POST /show_elements/` | `dg_show_elements(unique_ids)` | `{uniqueIds: [..]}` (1..5000) → `{found, shown, missing: [..]}`; selects the elements and zooms the active view to them |
| `POST /clear_colours/` | `dg_clear_mapping_colours` | `{}` → `{cleared}`; removes the connector's overrides in the session view |

Every upstream revit-mcp route and tool is also registered under `dg_revit`, writes included (D-45).

### 8.4 Apply and writes

- The connector polls the open session every 3 s. When `openQuestions == 0` and the session is not applied, it waits 10 s after the newest answer (undo grace, as D-40) and then calls `POST /mapping/sessions/{id}/apply`.
- Colours: solid-fill graphic overrides in the session's view, in the GH palette (confirmed #2E7D32, auto #1565C0, suggested #F9A825, ambiguous #E65100, unmapped #9E9E9E). They are set when the session is created and refreshed when element states change and at apply. Transaction «DG mapping colours».
- Parameters at apply: shared instance text parameters `DG_Class` (class labels joined by `;`) and `DG_MappingState` (element state), bound from the connector's `DG_SharedParameters.txt` to the categories of the mapped elements that allow bound parameters. Transaction «DG mapping parameters».
- Every write is one Revit transaction (undoable). A closed or switched document stops the loop; the connector never writes into another document.

### 8.5 DeGram

- `degram.mapping.start {app: "revit"}` calls `dg_start_mapping`.
- `degram.mapping.focus {app: "revit", sessionId, itemId}` resolves the group `itemId` to the `nativeId`s of its elements from the full session and calls `dg_show_elements`.
- Revit sessions are matched to the open Revit model by `document`.
