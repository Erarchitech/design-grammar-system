---
phase: 1303-pravilo-gh-obekt
plan: "03"
status: complete
completed: 2026-10-17
requirements: [DGMAP-01, DGMAP-05, DGMAP-06]
executor: controller (inline; the wave-1 subagent stopped on a rate limit before writing anything)
---

# 1303-03 Summary — DG MAPPING script component for Grasshopper

## What was built

- `test/v12-hexagonal-facade-01/gh-mapping-intake.cs` — Rhino 8 C# Script component body (`Script_Instance : GH_ScriptInstance`, as `gh-measure-rules.cs`, whose geometry helpers it reuses). Inputs HU/GU/PB/PA/F/LZ (Tree), OntoClasses, Classes (List), GuAsHu, DefinitionKey, Project, Url, Token, Label, SessionId, Run, Refresh, Apply, DryRun (Item). Outputs SessionIdOut, Summary, Questions, Geometry, Colour, State, Roles, NativeId, ByClass, ClassNames, ClassObjects, Log.
  - Descriptors are class-agnostic: curves → vertexCount, gapCount, closed, z range, hasLevelOffsetM; surfaces/meshes → vertexCount, planarity, width, height, area, hasAspectRatio; the facade box → hasTotalHeightM. The stream name is sent only as `source`; native ids `gh:<key>:<stream>:<path>:0`.
  - HTTP (`HttpClient`, 30 s, `System.Text.Json`) only on rising edges of Run / Refresh / Apply; `Authorization: Bearer <Token>`; the token is never written to an output or the log; DryRun prints descriptors without HTTP.
  - `ByClass` keeps the original stream/branch order inside each class (PROPERTY STATE pairs by position); `ClassObjects` matches METAGRAPH classes by label/IRI via reflection instead of index-based List Items (the failure after the A1 classes).
- `mapping-demo/rhinocode/` — `dgmap_common.py` (refuses any definition not named `*-mapping.gh`, file log + EVIDENCE lines, pulse/slider/input helpers), `dgmap_wire.py` (mirrors the measure script's sources, CONNECTOR.Session → Token, METAGRAPH.Objects → OntoClasses, defaults), `dgmap_run_act.py` (acts v1–v4, refresh, apply; sliders restored in finally).
- `mapping-demo/GH-RUNBOOK.md` — owner runbook (Russian): copy, CONNECTOR re-sign-in, parameters table, wiring, acts, OBJECT STATE hookup, troubleshooting.

## Verification

- **Compile check:** the script body plus a stand-in `GH_ScriptInstance` compiled in a scratch project against the installed `C:\Program Files\Rhino 8\System\RhinoCommon.dll`, `Grasshopper.dll` and `GH_IO.dll` (net7.0-windows): **0 errors, 0 warnings**.
- Static checks: no `Console.Write` / `File.Write`; token only in the request header.
- `python -m py_compile` of the three helpers and a Python 3.9 AST parse: OK.

## Assumptions to confirm live (plan 06)

- Rhino 8 runs the C# script on .NET 7/8 (System.Text.Json and HttpClient present); the RunScript signature must match the created parameters (Tree / List / Item and type hints as in the runbook).
- Slider nicknames `Module Width F1` and `Наклон нечет сот` (from 3b-variants.md / 5-wiring.md); CONNECTOR output `Session`, METAGRAPH output `Objects`; the measure script is the only component with inputs PB, HU, GU, PA, F, LZ.
- PROPERTY STATE alignment in act 4 holds when every class comes from one stream; with `GuAsHu = true` the GroundFloorUnit branch keeps GU order (elements are appended per stream in input order).
