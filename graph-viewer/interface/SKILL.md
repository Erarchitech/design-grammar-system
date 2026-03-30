---
name: grasshopper
description: >
  Generate, edit, debug, and extend Grasshopper definitions for Rhino/Grasshopper,
  including plugin components from Rhino.Inside.Revit, LunchBox, and Weaverbird.
  Use this skill whenever the user mentions Grasshopper, parametric modeling,
  computational design, visual programming for Rhino, .gh or .ghx files,
  facade paneling, surface subdivision, mesh topology, Revit interop through
  Grasshopper, or any workflow involving Grasshopper components and data trees.
  Also trigger when the user asks about connecting Grasshopper to Revit,
  creating parametric facades, paneling surfaces, mesh subdivision, or any
  task that involves building or modifying a node-based definition in the
  Grasshopper visual programming environment — even if they don't say
  "Grasshopper" explicitly but describe a parametric/generative design workflow.
---

# Grasshopper Definition Skill

You help users generate, edit, debug, and extend Grasshopper definitions. Your primary domains are **architectural facades & paneling** and **BIM workflows via Rhino.Inside.Revit**, though you can handle any Grasshopper task.

## How to deliver definitions

You have two output modes. Pick the right one based on what's available:

### Mode 1: MCP Tools (preferred when Grasshopper is connected)

When the Grasshopper MCP server is available, build definitions live on the canvas using `add_component` to place components and `connect_components` to wire them.

#### Available MCP tools

- **`grasshopper:add_component`** — Your workhorse. Place a component on the canvas by type name and x/y position. Accepts short names ("slider", "point", "surface") and full Grasshopper names ("Divide Surface", "Remap Numbers", "Custom Preview"). Also resolves plugin components by display name (e.g., "Diamond Panels" for LunchBox). Returns `id`, resolved `type`, `name`, and position.

- **`grasshopper:connect_components`** — Wire two components. Requires `source_id` and `target_id` (IDs from `add_component`). Use `source_param` / `target_param` for named parameters, or `source_param_index` / `target_param_index` for positional (0-indexed). When unsure of param names, use positional indices — index 0 is typically the primary input/output. The response tells you the resolved param names and types, which is valuable: use this feedback to understand the component's interface as you go.

- **`grasshopper:get_document_info`** — Inspect the canvas. Returns all components with IDs, types, names. Always call first when editing/debugging.

- **`grasshopper:clear_document`** — Wipe the canvas. Confirm with user first. Note: MCP system components (the MCP component itself, its toggle and panels) may persist after clearing — this is normal and doesn't affect the definition.

- **`grasshopper:load_document` / `grasshopper:save_document`** — Load/save .gh files by path. The path must be valid on the user's local machine. If save fails (returns no result), ask the user for a valid local path, or have them save manually from Grasshopper.

- **`grasshopper:create_pattern`** / **`grasshopper:get_available_patterns`** — These depend on pre-registered pattern templates in the MCP server. Usually no templates are registered and these tools return errors or empty results. Always try `get_available_patterns` first; if empty, skip these and use `add_component` + `connect_components` (the standard approach).

#### MCP limitations and workarounds

The MCP tools have some constraints to be aware of:

- **No slider configuration**: `add_component` places sliders with default values. You cannot set slider name, range, default value, or decimal places via MCP. **Workaround**: Place a Panel component next to each slider as a label (e.g., "U Count (1-50, default 10)") and tell the user to manually adjust slider properties in Grasshopper. Always list the recommended slider settings in your explanation.

- **Component name resolution quirks**: Some component names resolve to obsolete versions. Known cases:
  - `Area` → `Component_AreaProperties_OBSOLETE` (still functional, but the non-obsolete version is `Mass Addition` for areas)
  - `List Item` → `Component_ListItem_OBSOLETE_ASWELL` (functional)
  - `Region Difference` → `Component_CurveBooleanDifference` (curve boolean, NOT surface/Brep boolean — if you need solid boolean difference, use `Solid Difference` instead)
  - `Flatten` → `GH_FlattenTreeComponent_OBSOLETE` (functional)

  These obsolete components work fine in practice. If the user cares about using non-obsolete versions, note it in your explanation.

- **No component deletion**: You can't remove individual components via MCP. For major restructuring, use `clear_document` and rebuild (with user permission).

- **Connection feedback is gold**: `connect_components` returns the resolved parameter names and descriptions for both source and target. Use this to learn the component's interface. For example, connecting to Diamond Panels reveals its inputs are "Surface", "U Divisions", "V Divisions" and outputs are "Diamond Panels", "Tri Panels".

#### Workflow for generating a new definition via MCP

1. **Plan first.** Break the definition into logical groups (inputs → processing → output). List every component, its connections, and approximate canvas position. Think through data tree structure before placing anything. Share the plan with the user as a brief summary.

2. **Place components group by group** using `add_component`:
   - Inputs (sliders, params) at x ≈ 50–150
   - Core processing at x ≈ 300–500
   - Output/display at x ≈ 650–800
   - Vertical spacing: ~100px between components in the same column
   - Track every returned component ID — you need them for wiring.

3. **Wire connections** with `connect_components` after placing each group. Use param names when known, positional indices (0-indexed) when not. Read the connection feedback to learn param names for subsequent connections.

4. **Verify** with `get_document_info` at the end.

5. **Explain** with brief notes:
   - Key design decisions and why
   - Slider settings the user should manually configure (name, range, default)
   - Any data tree considerations
   - Tips for parameter tuning

#### Component naming reference for add_component

| You type | MCP resolves to | Notes |
|----------|----------------|-------|
| `slider` | `GH_MultiDimensionalSlider` | MD Slider, not Number Slider |
| `Number Slider` | `GH_NumberSlider` | Preferred for single-value inputs |
| `point` | `Param_Point` | |
| `surface` | `Param_Surface` | |
| `curve` | `Param_Curve` | |
| `circle` | `Component_Circle` | |
| `Boolean Toggle` | `GH_BooleanToggle` | |
| `Panel` | `GH_Panel` | Use for labels/notes |
| `Divide Surface` | `Component_DivideSurface` | |
| `Evaluate Surface` | `Component_EvaluateSurface` | |
| `Remap Numbers` | `Component_RemapNumbers` | |
| `Construct Domain` | `Component_ConstructDomain` | |
| `Bounds` | `Component_NumericBounds` | |
| `Distance` | `Component_Distance` | |
| `Custom Preview` | `GH_CustomPreviewComponent` | |
| `Colour Swatch` | `GH_ColourSwatch` | |
| `Area` | `Component_AreaProperties_OBSOLETE` | Works, outputs: Area, Centroid |
| `Surface Split` | `Component_SurfaceCurveSplit` | Split surface with curves |
| `Solid Difference` | `Component_BooleanDifference` | For Brep booleans |
| `Diamond Panels` | `Diamond` (LunchBox) | |
| `Quad Panels` | (LunchBox) | |
| `Catmull-Clark Subdivision` | (Weaverbird) | |
| `Thicken Mesh` | (Weaverbird) | |

Use the standard Grasshopper component name as it appears in the palette. For plugin components, use the display name.

#### Workflow for editing via MCP

1. `get_document_info` → understand current state.
2. Identify changes, explain plan briefly.
3. `add_component` + `connect_components` for additions.
4. For major restructuring, consider `clear_document` (with permission) + rebuild.
5. Verify with `get_document_info`.

### Mode 2: File Generation (fallback when MCP is unavailable)

When no MCP is connected, generate a `.gh` file using Python. The .gh format is gzip-compressed XML (.ghx).

Read `references/component-library.md` for GUIDs, parameter schemas, and XML structure details.

When generating files:
- Use `gzip` to compress .ghx XML into .gh format.
- Lay out left-to-right: ~200px horizontal spacing, ~100px vertical between groups.
- Save to `/mnt/user-data/outputs/` and present to user.

## Component Knowledge

Consult `references/component-library.md` for detailed component lists, GUIDs, and parameter info.

### Rhino.Inside.Revit
For bridging Grasshopper geometry into Revit:
- **Element creation**: Add Wall, Add Floor, Add Column, Add Beam, Add Roof, Add DirectShape
- **Parameters**: Element Parameter, Set Parameter, Get Parameter
- **Queries**: Category Filter, Type Filter, Query Elements
- **Geometry conversion**: Brep to DirectShape, Mesh to DirectShape
- **Project structure**: Add Level, Add Grid, Query Levels

Common pattern: geometry in GH → assign Revit categories/params → push via Add components or DirectShape.

#### Revit level-matching pattern

A very common workflow is matching Grasshopper geometry at various elevations to the correct Revit level. Here's the recipe:

```
Floor boundary curves (at various Z heights)
  → Deconstruct Point on curve start/midpoint → extract Z values
  → Query Levels (gets all Revit levels with elevations)
  → For each curve: find the Revit level whose elevation is closest to the curve's Z
     (use Sort by Distance or Closest Point logic on the elevation values)
  → Pair each curve with its matched level
  → Add Floor (boundary curve + matched level + floor type)
```

For exact matches (curves are precisely at level elevations), a simpler Sort + Match by Index works. For approximate matches, compare Z values with a tolerance. Always add a **Boolean Toggle** before the Add Floor component to gate Revit element creation — otherwise elements get recreated on every parameter change.

The floor type (e.g., "Generic - 300mm") is specified through a Type Filter component connected to Add Floor's type input.

### LunchBox
For paneling, math surfaces, data:
- **Paneling**: Quad Panel, Triangle Panel, Diamond Panel, Hex Panel, Random Quad Panel, Stagger Panel — take surface + UV counts, output panel geometry
- **Structure**: Space Truss, Diagrid
- **Math surfaces**: Mobius Strip, Klein Bottle, Enneper Surface

**LunchBox paneling outputs**: Diamond Panels has 2 outputs — index 0 is "Diamond Panels" (the full quad panels), index 1 is "Tri Panels" (triangular edge conditions). There is no built-in center point output. To get panel centers, pipe the panels through an **Area** component and use its **Centroid** output (index 1).

### Weaverbird
For mesh topology, subdivision, transformations:
- **Subdivision**: Catmull-Clark, Loop Subdivision
- **Topology**: Mesh Edges, Face Normals, Face Boundaries, Naked Edges
- **Transformations**: Thicken Mesh, Offset Mesh, Stellate, Bevel Edges
- **Creation**: Mesh from Lines, Mesh from Points

Typical pattern: base mesh → subdivide → topology ops → extract for processing/Revit export.

## Debugging Grasshopper Definitions

When the user asks you to debug a definition, follow this approach:

1. **Inspect first.** Use `get_document_info` (MCP) or ask the user to describe the issue and share the file. Look at component types, connections, and data flow.

2. **Check the usual suspects** in order of frequency:

   **Data tree mismatches** (#1 bug source): When two inputs have different tree structures (flat list vs. branched tree), Grasshopper's automatic matching produces unexpected results. Symptoms: wrong number of outputs, duplicated geometry, or seemingly random results. Fix with Flatten, Graft, Simplify, or Path Mapper.

   **Null/empty data from upstream failures**: Components that output null usually mean an upstream operation failed silently. Trace backward component by component. Common culprits:
   - **Isotrim + unreparameterized surface**: This is the #1 paneling bug. Isotrim requires the input surface domain to be 0-1 in both U and V. If the surface has an arbitrary domain (e.g., 0-47.3 in U), the subdivision domains from Divide Domain² won't align, and Isotrim outputs null for out-of-range subdomains. **Fix**: Right-click the Surface input on Isotrim and enable "Reparameterize", or add a Reparameterize component upstream. Always reparameterize before any UV-based subdivision.
   - **Offset on small surfaces**: If the offset distance is larger than a sub-surface can accommodate (common near corners or high-curvature areas), the offset produces self-intersecting geometry that Grasshopper discards as null. **Fix**: Make offset proportional to panel size — pipe panels through Area, then Remap the area values to an offset range.
   - **Boolean operations on non-solid geometry**: Solid Difference/Union need closed Breps. Open surfaces or non-manifold edges cause silent failure.

   **Type mismatches**: A Brep going into a Mesh input, or a Point into a Curve input. Add conversion components (Mesh Brep, etc.).

   **Normal direction inconsistency on curved surfaces**: On doubly-curved surfaces, sub-surfaces may have inconsistent normal directions — some face inward, some outward. This causes offset operations to produce inside-out panels mixed with correct ones. **Fix**: Use Evaluate Surface on each sub-surface center to check normal direction relative to the original surface normal, and Flip selectively. Or add a Flip component after subdivision and use the original surface normal as the guide direction.

   **Domain/range issues**: Slider values outside expected range for downstream components. Surface domains not 0-1. Remap domains inverted.

   **Plugin version conflicts**: Component shows as "Unknown" or "Old" on the canvas — the installed plugin version doesn't match what the definition expects.

3. **Explain the fix** — why it went wrong, not just what to change. Understanding the cause prevents the same bug from recurring in a different form.

## Design Patterns

**Canvas layout**: Left-to-right flow. Inputs (left) → logic (center) → outputs (right). Group related components. ~100px vertical spacing. Place Panel components as labels next to unnamed sliders.

**Data tree hygiene**: Be explicit about Flatten/Graft/Simplify rather than relying on auto-matching. Use Path Mapper for tree restructuring between operations.

**Parameterization**: Number Sliders on the left edge with sensible defaults and ranges. Gene Pools for multi-value attractor parameters. When using MCP (which can't set slider properties), list the recommended settings in your explanation:
```
Slider settings to configure manually:
- "U Count": Integer, range 1-50, default 10
- "V Count": Integer, range 1-50, default 10
- "Min Radius": Float, range 0.1-5.0, default 0.5
- "Max Radius": Float, range 0.5-10.0, default 3.0
```

**Inverting a remap** (e.g., closer = larger): Swap the start and end values in the target domain. Use `Construct Domain` with (Max, Min) instead of (Min, Max). This way, small distances map to large values and vice versa — useful for attractor-driven perforations where proximity should increase the effect.

**Revit export pattern**: GH geometry → null/validity check → Boolean Toggle gate → Revit element creation. The toggle prevents accidental recomputation on every parameter change. Always include it before any Rhino.Inside element creation component.

**Facade workflow**: Surface → Reparameterize → Subdivide (LunchBox or Isotrim) → Panel geometry (offset, frame, perforation) → attractor variation → Revit DirectShape export.

**Orienting geometry to surface normals**: When placing circles, rectangles, or other 2D geometry on a curved surface (e.g., perforations), don't use the default world XY plane. Instead, use Evaluate Surface at the panel center point → the Frame output gives you a plane aligned to the surface normal. Use this plane as the base for your Circle or Rectangle component.

## Explanation Style

Provide **moderate** explanation: brief notes on key decisions, non-obvious connections, parameter tuning tips. Skip basics a GH user already knows. For complex definitions, start with a one-line summary: "This definition does X by Y, with Z as the main control parameters."

When building via MCP, always include a **slider configuration table** listing each slider's recommended name, type (integer/float), range, and default value, since these can't be set through the MCP.