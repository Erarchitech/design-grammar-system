---
tags: [session, ontology, dcm, v5]
date: 2026-05-30
---

# 2026-05-30 — Ontology v5.0: DCM ComputationGraph Extension

## Summary

Extended the DG ontology from v4.1 to v5.0 with a new **ComputationGraph** layer (5th graph layer) implementing the Design Computation Model (DCM) for future Grasshopper parametric design translation. Also created per-vocabulary extension files for BOT and Topologic, replacing the monolithic aligned facade approach.

## What was done

1. **Analyzed ERD diagram** (`ontology/900_04_Ontologies_Rev05.drawio`, sheet `04_MAPPING`) — extracted all entities and relationships via PowerShell XML parsing.
2. **Analyzed conceptual mapping PDF** — screenshot shows GH definition of a Frame object (1_Algorithm → 11_Proc Truss → 12_Proc Footer) with Pattern/Parameter/Interface/Emergent mapping.
3. **Performed semantic overlap validation** — evaluated all ERD entities against existing DG ontology through DCM/Grasshopper lens (not just current runtime). Key conclusion: BODY/HEAD overlap with hasBody/hasHead, all other entities add genuine value for future GH translation.
4. **Updated `DesignGrammar.owl` to v5.0**:
   - Added `dgc:` namespace (`http://example.org/design-grammar/computation#`)
   - Added 5th GraphLayer member: `dgc:ComputationGraph`
   - Added `dgm:RuleSet` + `dgm:Reasoner` to Metagraph
   - Added full ComputationGraph layer: Object, Function, Behavior, Structure, ParametricState, Algorithm, Procedure, Pattern, Parameter (Var/Const/Emergent), Interface (Input/Output), Geometry, Topology
   - Added enums: ParamDataTypeValue, ListStructureValue
   - Added cross-layer bridge: `dgc:attributeOf` (Atom → Parameter)
   - Added disjointness axioms for all new classes
5. **Created `DesignGrammar-BOT-extension.owl`** — BOT alignment (6 bot: classes → subClassOf dgc:Topology)
6. **Created `DesignGrammar-Topologic-extension.owl`** — Topologic spatial decomposition (8 topo: classes, containment/adjacency properties)
7. **Renamed `DesignGrammar-aligned.owl`** → `DesignGrammar-standards-extension.owl`
8. **Updated `catalog-v001.xml`** with all new entries

## Key decisions

- **FBS framework (Gero 1990)** chosen as theoretical basis for DCM: Object → Function / Behavior / Structure
- **ComputationGraph is conceptual/future** — no current runtime depends on it; purely additive
- **BODY/HEAD NOT added as classes** — existing `dgm:hasBody`/`dgm:hasHead` properties already model this correctly
- **Per-vocabulary extension files** instead of monolithic aligned facade: `*-extension.owl` naming pattern
- **Cross-layer bridge pattern**: `dgc:attributeOf` connects SWRL Atoms to GH Parameters (same pattern as `dgm:refersTo`)

## Grasshopper mapping (validated by screenshot)

| ERD Entity | GH Equivalent | Example |
|---|---|---|
| Algorithm | GH Definition (canvas) | 1_Algorithm |
| Procedure | GH Cluster/Group | 11_Proc - 2D Truss Configuration |
| Pattern | GH Component (node) | 11_Pat_DivideLine |
| Parameter:Var | GH Slider/Input | 11_Var_SpansCount |
| Parameter:Const | GH Constant | 11_Const_ptZero |
| Parameter:Emergent | GH Computed Output | 11_Emg_LineSDL |
| Interface | Inter-procedure connector | 11_IntF_MergeRes |

## Files modified/created

- `ontology/DesignGrammar.owl` — v5.0 (2219 → 2787 lines)
- `ontology/DesignGrammar-BOT-extension.owl` — NEW
- `ontology/DesignGrammar-Topologic-extension.owl` — NEW
- `ontology/DesignGrammar-standards-extension.owl` — RENAMED from DesignGrammar-aligned.owl
- `ontology/catalog-v001.xml` — updated

## Next steps

- Update `DesignGrammar.md` (markdown reference) to reflect v5.0
- Update `ONTOLOGY-ALIGNMENT.md` with BOT/Topologic extension notes
- Future: Implement ComputationGraph in Neo4j when GH integration proceeds
- Future: Populate with instance data from real GH definitions

## Session continuation (same day)

**Added ComputationGraph example individuals** based on the Grasshopper screenshot:
- 1 Object (Frame), 1 Behavior, 1 Structure
- 1 Algorithm (1_Algorithm)
- 2 Procedures: 11_Proc (2D Truss), 12_Proc (2D Footer)
- 3 Patterns: DivideLine, TopChord, FooterBottomLines
- 4 VariableParam: SpansCount, HTotal, HFooter, FooterCount
- 4 ConstantParam: ptZero, TrussConfig×2, IndList_1
- 4 EmergentParam: LineSDL, UpperChord, BottomLn, FooterFrame
- 4 Interfaces (Output): ParSplitAt, TrussConfig, MergeRes, FooterFrame
- 1 ParametricState (default)

Total: +249 lines, 26 NamedIndividuals added. XML validation passed.
