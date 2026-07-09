---
tags: [session, grasshopper, plugin]
date: 2026-07-09
---

# 2026-07-09 GH Component Subcategory Grouping

## Summary

Reorganized the Grasshopper plugin's 14 components into 3 logical subcategories on the tool panel to improve discoverability and workflow.

## Work Done

### Changes to DgComponentCategory.cs
Added 3 new subcategory constants to replace the single flat "Design Grammars" grouping:

```csharp
public const string GraphSubcategory = "Graph";
public const string StatesSubcategory = "States";
public const string ActionsSubcategory = "Actions";
```

### Regrouped 15 component classes

**Graph panel (6 components):**
- Connector
- Graph Deconstruct  
- Validation Graph
- MetaGraph
- OntoGraph
- Rule Deconstruct

**States panel (7 components):**
- Design State
- Design State Deconstruct
- Property State
- Object State
- Object Deconstruct
- Parameter State
- Label

**Actions panel (2 components):**
- Validator
- Parameter Reinstate

## Icon Discrepancies Found

### Missing: `Label24.png`
- File: `DG/src/DG.Grasshopper/Properties/Label24.png` — **does not exist**
- Component: `LabelComponent` references `DgIcons.Label24` which loads this PNG
- Runtime behavior: Pink fallback icon with red X (visible indicator of missing resource)
- Action needed: Provide the missing icon file

### Orphaned resources
- `DesignState24.png` — embedded but not referenced in `DgIcons.cs`
- `Reinstate24.png` — `DgIcons.Reinstate24` exists but not used by any component (ParameterReinstate uses `ParameterReinstate24.png` instead)

## Build Verification

```
dotnet build ./DG/DG.sln -c Release
```

Result: ✅ Build succeeded, 0 warnings, 0 errors

All 14 components compile correctly with new subcategory assignments. The Grasshopper plugin will now display components grouped under three distinct tool panel tabs instead of a single flat list.

## Files Modified

- `DG/src/DG.Grasshopper/DgComponentCategory.cs` (+ 3 constants)
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`
- `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs`
- `DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs`
- `DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs`
- `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs`
- `DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs`
- `DG/src/DG.Grasshopper/Components/DesignStateCompositionComponent.cs`
- `DG/src/DG.Grasshopper/Components/DesignStateDeconstructComponent.cs`
- `DG/src/DG.Grasshopper/Components/PropertyStateComponent.cs`
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs`
- `DG/src/DG.Grasshopper/Components/ObjectDeconstructComponent.cs`
- `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs`
- `DG/src/DG.Grasshopper/Components/LabelComponent.cs`
- `DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs`
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`
