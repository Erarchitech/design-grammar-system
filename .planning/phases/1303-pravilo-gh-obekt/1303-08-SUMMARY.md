---
phase: 1303-pravilo-gh-obekt
plan: "08"
status: complete
completed: 2026-10-18
requirements: [DGMAP-01, DGMAP-02, DGMAP-03, DGMAP-04]
executor: "controller (Claude, inline); no DSH worker"
commits: [6014cbc, 6c5deeb, efc3e3a, cec26cb]
superseded_in_part_by: "1303-09 (D-37): sliders are DG parameters, not datatype properties"
---

# 1303-08 Summary — CONNECTOR proposes the mapping automatically

## What was built

- **DG.Core** (`DG/src/DG.Core/Mapping/`): `MappingSnapshot` (canvas snapshot and content fingerprint), `MappingSessionClient` (create / poll / apply over HTTP; the `dgk_` session token goes only into the `Authorization` header), `MappingCanvasText` (group names, scribbles, component names as word evidence).
- **DG.Grasshopper** (`DG/src/DG.Grasshopper/Mapping/`): `MappingCanvasReader` (element streams = geometry wired into DG components, else visible terminal geometry, D-34; canvas text, named sliders), `MappingGeometry` (features ported from the `gh-mapping-intake.cs` prototype, plus solids), `MappingAutoRunner` (settles after 1.5 s, sends a session only when the fingerprint changed, polls every 3 s, applies when no question is left), `MappingPreviewConduit` (state colours in Rhino without Custom Preview).
- **CONNECTOR** (`ConnectorComponent.cs`): input `AutoMap` (default true); outputs `Mapping`, `ByClass`, `ClassNames`, `ClassObjects`, `Sliders`.
- **Engine** (`data-service/mapping_engine.py`, `mapping_store.py`, `app.py`): descriptors accept `names` (word evidence, no acronyms); a small Russian → English lexicon (D-35); `POST /mapping/sessions` accepts `parameters`; sliders were scored against the project's datatype properties and asked as `map-parameter` questions (D-36). No new route.
- **Web UI** (`MappingPanel.jsx`, `screens.js`): `map-parameter` questions, "Not a DG property", a Sliders table; while the panel is open it follows the newest session every 5 s.
- Fixes in the same plan: `6c5deeb`: sliders are offered only design properties, not rule-head violation flags; `efc3e3a`: count distinct class words, and a satisfied equality signature breaks weak ties.
- Docs (`cec26cb`): `1303-TEST-GUIDE.md` and `mapping-demo/GH-RUNBOOK.md` for automatic mapping; the RhinoCode acts only set sliders.

## Superseded

The slider half of D-36 (slider → datatype property) was replaced the same day by D-37 in plan 09. A slider is a DG Parameter, and property values come from calculation outputs. The `map-parameter` path was replaced by `batch-parameters` and `batch-measures` / `map-measure`.

## Verification

- Automated (end of 2026-10-18, after plan 09 on top of this one, session note): data-service 5771 passed, with only the known environment failures; DG.Tests 770 passed, with 5 known environment failures; ui-v2 322/322.
- **Live, checked on 2026-10-18:** after the clean facade copy is opened, CONNECTOR signs in from the saved Panels and creates a mapping session by itself. No extra component is needed. Session `ms-98a39fa841bc` (10:54) had 13 questions; CONNECTOR showed «Map: 13?», then «Map: 6?» after the LLM proposal of plan 09 arrived.
- Not covered by this plan's own checkpoint: answers, apply and the green colours are part of the plan 09 live run (`1303-UAT.md`).

## Issues found

- The facade copies sign in on open because Username and Password come from saved Panels and Connect is saved as True. Each reopen is a real sign-in, a new session and a paid LLM call. See `DG_OBSIDIAN/knowledge/debugging/Facade gh copies sign in to CONNECTOR on open from Panels.md`. Open item: remove the password Panel before the demo.
