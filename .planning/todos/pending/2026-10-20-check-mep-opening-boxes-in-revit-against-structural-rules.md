---
created: 2026-10-20T07:51:30.075Z
title: Check MEP opening boxes in Revit against structural rules
area: planning
severity: major
files:
  - apps/dg-revit-connector/dg_revit_mcp/clash.py:1-60
  - apps/dg-revit-connector/dg_revit_mcp/colors.py
  - apps/dg-revit-connector/lib/dg_connector/revit_io.py
  - apps/dg-revit-connector/lib/dg_connector/palette.py
  - data-service/mapping_engine.py
  - DG/src/DG.Core/Validation/SupportedBuiltins.cs
  - .planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md:173-213
---

## Problem

**Owner priority, 2026-10-20: next demo in about 6 hours.** The 19.10 mapping demo passed. The next demo shows Design Grammars on a coordination case between disciplines: the hand-off of opening requests from MEP engineers to structural engineers.

The current workflow:
1. MEP engineers model **opening boxes** in their Revit model: families of the **Generic Model** category placed where ducts, pipes and trays cross structural elements (walls, columns, beams, floors).
2. Structural engineers **copy the boxes** from the MEP model into their own Revit model. The boxes then become native elements, not a link.
3. Structural engineers check every box by eye and place an opening only where the rules allow it.

**Rules (owner, 2026-10-20):**
- R1: no openings in **beams**.
- R2: no openings in **columns**.
- R3: no openings **above door/window openings**.
- R4: an opening must be at least **300 mm** from the boundary of a door/window opening.

**Goal:** DG checks the boxes against these rules automatically and **highlights the boxes that violate them**. The structural engineer no longer checks each box by eye.

**Where the work happens:** worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp`, as planned for Phase 1303. Nothing goes into the main folder or `feature/hosting-dg-pilot`.

**What already exists (read on 2026-10-20):**
- Revit writes are allowed in the DG fork of the connector (D-45, 2026-10-18): parameters, colour/graphic overrides and selection. Writes still go to a local model copy only (D-52 protocol), never to a shared original.
- `apps/dg-revit-connector/dg_revit_mcp/clash.py` already finds hard clashes with Revit's `ElementIntersectsElementFilter`, paired with a category filter. It has aliases for `generic models`, `beams` (`OST_StructuralFraming`), `structural columns`, `walls`, `floors`, `doors` and `windows`. Limits: auto-joined elements and elements without solids are not reported.
- `colors.py` / `palette.py` write colour overrides in the active view. «Очистить цвета» removes them (D-50).
- The connector reads descriptors (UniqueId, category, family, type, parameters, geometry) and writes the shared parameters `DG_Class` and `DG_MappingState` (D-48, D-50). The mapping engine can classify Revit elements into DG classes (OpeningBox, Beam, Column, Wall, Floor, Door/Window).
- Rhino.Inside.Revit, pyRevit and the Speckle Revit connector are installed for Revit 2024.
- The only SWRL evaluator is the C# one (`DG.Core`, used by VALIDATOR in GH and by the DE-01 harness). The data-service has no Revit validation route.

**Open questions:**
- Which test model to use. It must have opening boxes, structural elements and doors/windows. Only the facade model `AdaptComponent_V18` is on disk, and it has no MEP boxes.
- Where the rules are evaluated:
  - (a) Rhino.Inside.Revit → GH → the existing VALIDATOR, then colours back to Revit;
  - (b) the pyRevit connector computes geometric facts and the rules are checked on the server.
- What R3 and R4 mean geometrically:
  - R3: "above an opening" in the wall plane only, or also through a floor slab above a door?
  - R4: the 300 mm is the clear gap between the box edge and the opening edge in the host wall plane.

## Solution

Plan **1303-15** in Phase 1303 (owner's choice, 2026-10-20). The approach:
1. **Facts from Revit.** For each OpeningBox (Generic Model, filtered by family name), compute:
   - the host it intersects, by category (beam, column, wall or floor), with `ElementIntersectsElementFilter` plus a bounding-box fallback;
   - for each door/window in the same host wall: whether the box is above it (the horizontal projections overlap and the box bottom is at or above the opening head), and the minimal clear distance between the box and the opening boundary in the wall plane, in mm.
2. **Rules as DG rules.** Ingest R1–R4 through the normal NL → SWRL pipeline into the project, so the demo shows the DG grammar and not hard-coded checks. Evaluate them deterministically, with no LLM at check time.
3. **Highlighting.** Colour violating boxes red and passing boxes green in the active view, in one undoable transaction. Write `DG_Violation` (a rule-id list) and `DG_ValidStatus` to the boxes. Optionally publish a validation run to ValidGraph and Speckle.
4. **Demo script.** A short protocol, «Акт 4 — отверстия»: boxes copied in → «Проверить отверстия» → the red boxes, each with the rule it breaks.
</content>
</invoke>
<invoke name="Bash">
<parameter name="command">cd /c/Users/Admin/source/repos/dg-mapping && mkdir -p .planning/todos/completed && git mv .planning/todos/pending/2026-10-17-deliver-automated-gh-and-revit-to-dg-mapping-mvp-by-19-10.md .planning/todos/completed/ && node ~/.claude/gsd-core/bin/gsd-tools.cjs query init.todos | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('pending_read_ok'));print(d.get('pending_todos_markdown'))"