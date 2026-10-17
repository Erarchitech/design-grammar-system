---
created: 2026-10-17T12:07:21.943Z
title: Deliver automated GH and Revit to DG mapping MVP by 19.10
area: planning
files:
  - docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md
  - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:49-68
  - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:137-145
  - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:201-211
  - DG/src/DG.Core/Services/DesignStateBindingService.cs:43-92
  - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs:130-134
  - data-service/computgraph_publish.py:565-603
  - data-service/dg_identity.py:107-108
  - data-service/dg_identity.py:335-354
  - apps/revit-mcp/revit_mcp/documents.py:173-199
  - apps/revit-mcp/revit_mcp/degram_readonly.py:24-46
  - ontology/dg-disjointness.ttl:47
  - ontology/dg-disjointness.ttl:53
  - test/v12-hexagonal-facade-01/README.md:66
  - test/v12-hexagonal-facade-01/README.md:112
  - test/v12-hexagonal-facade-01/README.md:119
  - .planning/REQUIREMENTS.md:56-61
  - .planning/milestones/v14.0-REQUIREMENTS.md:45-47
---

## Problem

**Owner priority, 2026-10-17:** revise the current plans around automated mapping of Grasshopper outputs and Revit elements to DG objects, and show a working MVP on **2026-10-19**. Plans not directly related to this are deferred. Phase 1309 (hosting package) is **not** deferred: it continues in a parallel Hermes session on `feature/hosting-dg-pilot` in the main folder and must not be interrupted. The owner's question: a plain LLM confirmation ("is this element a window?") is not enough when IFC references overlap (a facade element can be both a window and a wall). What state-of-the-art interactive learning should improve DG mapping quality?

Research input: `docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md` (ontology-alignment user validation, SystemER, colour-coded Revit views, GH groups, LLM as explainer/refiner/disambiguator, active-learning queues).

**What exists in code (read-only investigation, 2026-10-17)** — the owner's three described mapping means are mostly not built:

- **GH manual mapping — partial.** The user wires an OntologyClass into OBJECT STATE (`ObjectStateComponent.cs:49-68`, `:201-211`); ObjectRef is the explicit ref, the geometry GUID or `obj_{i}` (`:137-145`). VALIDATOR binds ObjStates to rule variables by exact ClassIri equality only (`DesignStateBindingService.cs:43-92`). On the Computgraph track `classIri` is never filled (parser keeps only Name/Source, `CanvasAnnotationParser.cs:130-134`), so no `Object-[:REFERS_TO]->Class` is written by GH. No mapping state, confidence or provenance exists anywhere.
- **Revit "category + properties in a DG add-in" — does not exist.** There is no DG Revit add-in. The only Revit code is the read-only `apps/revit-mcp` fork (8-tool allowlist, `degram_readonly.py:24-46`); `get_selection_snapshot` returns uniqueId, elementId, category, typeName and parameters with units (`documents.py:173-199`, 200 elements / 50 parameters by default). Colour overrides (`colors.py`) are writes and stay blocked by D-10 until Phase 1306. `/identity/bind` can store `Representation{platform:'Revit', nativeIdKind:'UniqueId'}` (`dg_identity.py:107-108`, `:335-354`) but has no caller.
- **IFC-class suggestion and auto-mapping by shared IFC class — does not exist.** `:Class` has only `{iri, label, graph, project}`; IFC/bSDD lives only in the decision note "Alignment modules over extension modules in the DG ontology" and the building-codes concept doc. Disjointness exists only in the OWL overlay (Door ⊥ Window, Wall ⊥ Slab, `dg-disjointness.ttl:47`, `:53`); `classIri` is single-valued.
- **No learning loop.** Phase 38 candidate accept has no reject and no feedback.
- Requirements already point here: DGBN-01..06 (Phase 1303, not started, `.planning/REQUIREMENTS.md:56-61`) and v14 NMOD-01..03 (`v14.0-REQUIREMENTS.md:45-47`: "Revit category→IFC export data and GH recognition are candidate signals, never proof"; BindingProfile with approver and selected/excluded/unclassified/missing/stale probe).
- The 22.10 pilot plan (`.planning/PILOT-2026-10-22.md`, untracked in the main folder) required manual confirmation of every binding and excluded recognition — superseded for this work by owner decision D-03 below.

**Documented mapping failures in hexagonal-facade (demo material):** F5 — 25 of 125 modules in the HU tree (`HU{72}…{96}`) were pentagonal ground-floor units (`README.md:66`, `:112`); F12 — rule ingest matched "ground floor module" to `HexagonalUnit` on the shared word "module" (`:119`); after the A1 classes were added, index-based class pickers shifted and 100 elements were bound to the wrong class (`C:\Users\Admin\source\repos\design-grammar-system\test\v12-hexagonal-facade-01\9-A1-loaded-after-repair.json:79-87`, untracked, main folder only); HexagonalUnit and FacadeModule legitimately share the same 100 geometries (multi-role).

**Owner decisions (2026-10-17):**
- D-01 Isolation: git worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp` from committed `535eb30`; no changes or commits in the main folder / `feature/hosting-dg-pilot`; merge after the demo and after a 1309 commit point. GSD in flat mode inside the branch (no workstreams: `workstream.create` migrates ROADMAP/STATE/REQUIREMENTS/phases; no `/gsd-new-milestone`).
- D-02 Scenario: GH + Revit **live**. A Revit model of the facade already exists, generated through Rhino.Inside: facade modules are Generic Model adaptive-point families, the frame is built in Grasshopper. Path of the `.rvt` still to be given by the owner.
- D-03 Confirmation: group-level answers with rule consequences create profiles (author, date, support); profiles auto-apply only above a threshold, everything else is queued; this counts as explicit confirmation.
- D-04 Authorized for 17–19.10: Docker on this PC (rebuild data-service and design-grammars from a clean export of the branch), live Rhino/GH via RhinoCode on a copy of the facade `.gh`, live **read-only** Revit, paid LLM calls through the gateway.

## Solution

**Approach (state of the art):** evidence → groups → consequence questions → learned profiles.
1. Mapping is multi-role with explicit incompatibility: element→class edge with role, state (suggested/confirmed/rejected/ambiguous/manual), confidence, sources, decidedBy/At.
2. Several weak evidence sources instead of IFC alone (weak supervision, Snorkel): authored profiles (GH wiring, Revit category+parameters), IFC entity+PredefinedType(+bSDD), name/type, geometry (vertex/adaptive-point count, closure, planarity), consistency with DG rules (R5/R11/R12 act as class signatures), learned profiles, LLM as one vote.
3. Questions about groups, ordered by uncertainty × impact (elements × rules affected); answers propagate to the group; outliers shown separately (SystemER, active learning for EM).
4. Questions framed by consequences: "as HexagonalUnit these 25 outlines violate R12 ×25, as GroundFloorUnit R11 passes — mapping error or design error?"
5. Each answer becomes an inspectable MappingProfile (≈ NMOD-02 BindingProfile), applied deterministically on the next import; auto-apply above threshold (later calibrated, e.g. conformal prediction).
6. The LLM explains and proposes, never decides high-impact cases.

**MVP architecture:** data-service `mapping_engine.py` (pure functions + pytest) and `/mapping/*` routes (route policy + `spec/SECURITY-BOUNDARY.md`; new nodes MappingProfile/MappingDecision documented as experimental in `spec/DATABASE.md` and `spec/LPG-OWL-MAPPING.md`); GH script component (like `gh-measure-rules.cs`, no DG.gha rebuild) + Custom Preview colours; Revit read-only adapter (`get_selection_snapshot`/Rhino.Inside read → descriptors); Web UI "Mapping" panel (queue, question card, progress, profiles, RU/EN).

**Demo scenario (V1 = 376 elements: 100 HexagonalUnit, 25 GroundFloorUnit, 125 GlassPanel, 125 BottomTriangularPanel, 1 Facade; gold labels known):** (1) GH cold start with all 125 module outlines as one stream → ~5 groups, questions on the 25 pentagons and on HexagonalUnit+FacadeModule; (2) V2/V3 → profiles map new geometry with 0–1 questions; (3) live Revit read of the RiR-generated model: all modules are Generic Model adaptive components, so category/IFC cannot separate classes — geometry and transferred GH profiles do; one question → Revit profile; (4) roles → OBJECT STATE → VALIDATOR, V1 11/11 PASS, contrasted with the documented mis-mapping. Metrics: questions per 376 elements, precision/recall vs gold, auto-apply share.

**Plan revision:** re-scope Phase 1303 as the priority "Automated GH/Revit → DG mapping MVP (demo 19.10)", pulling DGBN-03/05 and NMOD-01/02 concepts in; 1300/1302 entry gates stay open for formal 1303 acceptance (the demo slice is demo-grade); defer 1302 (gate 1302-08), remaining 1300/1301 work, 1304–1307, v14 activation and Phase 35; 1309 continues in parallel.

**Next:** plan revision in this branch → `1303-CONTEXT.md` → plans → execution (DSH workers for implementation) → live rehearsal 19.10 morning. Cut lines if late: no Web UI (answers in GH), no LLM (template questions).
