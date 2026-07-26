---
date: 2026-07-26
tags: [phase-35, uat, bug-fix, f5]
related: [[../debugging/Phase 35 F5 — bare Number component inferring null dataType]]
---

# Phase 35 F5 Fix — dataType Inference on Bare Parameters

## Summary
Fixed UAT F5 (bare Number/Integer/Text/geometry params inferred `null` dataType with no warning → accepted proposals 422'd the entire publish) via `/gsd-audit-fix`. Parser fix already landed in `028ff0e`; verified live on Rhino canvas. Parallel session also closed F4 undo crash and G12 accept-time gate in `ae6d805`. F5 now fully closed.

## Work Done
- Invoked `/gsd-audit-fix @.planning/phases/v9.0-PIPELINE-UAT.md Group 4. F5` to audit and fix
- Parser: two-tier precedence (widgets win; primitives fallback tier for bare Number/Integer/Text/geometry)
- Parser: members present but untypeable now warn instead of returning silently
- Grasshopper: `DG COMPUTGRAPH PUBLISH` pre-flights for null dataTypes, names offending ids in status
- Verified 7 new CanvasAnnotationParserTests cases — full suite **384/384 green**
- `DG.sln Release` builds clean with `GRASSHOPPER_SDK` defined

## Live Verification
Plugin redeployed to `%APPDATA%\Grasshopper\Libraries\DG` (2026-07-26 12:33), Rhino restarted:
- Re-grouped `Num` Const (bare Number component) on UrbanBlock_V7
- Context pull reported **0 warnings** (correct)
- Publish **succeeded**
- Neo4j: `cg:1:const:11_Const_Num` → `Constant` / `Float` / `dg:D11F0CBE622F3039`
- Subgraph: 11→**12 nodes**, 12→**13 rels**
- SC2 idempotency re-confirmed (12→12, 13→13 on rising-edge trigger)

## Evidence
- Commits: `028ff0e` (parser), `85796df` (UAT record), `ae6d805` (parallel G12 gate)
- Tests: 384/384 DG.Tests pass, DesignState flake ordered favourably
- UAT: 35-UAT F5 closed; 36-UAT tests 1–2 re-verified at full size

## Open Items
- F6 (provenance fields unpersistable) — Phase 36 work
- F3 (LLM quality on frontier models) — awaiting Anthropic/OpenAI key
- Frame fixture (JSON-only, no `.gh` file) — re-runs on UrbanBlock_V7 instead

## Parallel Session
`ae6d805` (2026-07-26 14:00) closed **F4** (undo crash on re-preview) and **G12** (accept-time publishability gate) — a complementary backstop to this pre-flight. F5's accept-time half landed there; my publish-side guard catches anything that slips through.
