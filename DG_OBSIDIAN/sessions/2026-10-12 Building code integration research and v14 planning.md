---
tags: [session, building-codes, gsd, v14]
date: 2026-10-12
---

# Building-code integration research and v14 planning

## Outcome

The owner clarified the goal: connect building-code documents from a file, website or Google Drive folder; propose rules grounded in exact clauses; make an LLM choose approved existing Ontograph classes/properties connected to standard concepts instead of inventing duplicates; propose measured Revit and Grasshopper object/property bindings; review changed editions and accept selected changes without silently changing active project rules. The owner accepted a **separate future milestone** for the full normative pipeline.

- Concept and research: `docs/reviews/building-code-validation-integration-analysis/Design Grammars × Building Codes — концепция интеграции.md`, plus `Design Grammars × Atlas (David Cho) нормоконтроль на графе.md` and the editable five-page `Design Grammars × Building Codes — концептуальная схема.drawio` in the same directory.
- GSD isolation: `.planning/milestones/v14.0-REQUIREMENTS.md` (27 unchecked requirements) and `v14.0-ROADMAP.md` (nine proposed phases, 1400–1408). `.planning/MILESTONES.md` records the future milestone, and active `.planning/ROADMAP.md` points to it without assigning v13 requirements to v14.
- Decision: [[knowledge/decisions/Building code integration is isolated as future v14.0|v14.0 separation and ownership]]. The five existing graphs retain their roles; norm provenance belongs to SpecGraph, not a sixth graph.

## Design conclusions

- A versioned reference catalog cites permitted IFC/bSDD and other standard concepts with exact URIs, definitions, versions, provenance and individual dictionary rights. LLM proposals prefer the pinned company Ontograph release; no external concept becomes an internal class without steward approval. Public IFC classification datasets and general alignment benchmarks are not an expert corpus of norm→class→Revit/GH parameter links.
- Three distinct approvals are needed: norm term → Ontograph concept; Ontograph class → platform object selector; normative property → exact parameter or tested measurement. Existing IFC export mappings are candidate evidence, not regulatory equivalence. Scoped accepted and rejected decisions are reusable where source/context/version/permission remain compatible; they are not model training by themselves.
- Cheap deterministic extraction, filters, retrieval and approved memory precede the LLM. Jev or a similar adapter routes only unresolved cases after an offline same-corpus A/B/C test against always-strong and local rule-based baselines for quality, privacy, tokens, latency and cost per accepted correct mapping. Jev does not approve mappings or writes; the product works without it. No measured savings have been claimed.
- Fetched immutable source snapshots are separate from a clause-level accepted manifest. One Neo4j transaction gives selected compatible library derivatives a common acceptance ID/time; binary storage is outside that transaction. Each affected project gets an impact/proposal and separately approves any new active project rule revision. Missing values and unsupported constructs never yield a compliance pass.
- v13/1302 generic source/vocabulary/revision contract, 1303 native GH identity/binding, 1304 evidence, 1306 Revit read and 1307 DeGram UAT remain owned and gated by v13; 1308/1309 are already Web UI/hosting. Bulk norm ingest requires the existing rule-ID merge/collision defects F6/F13 to be resolved by their owner.

## Evidence and limits

The GSD planning consistency check found 27 distinct IDs mapped to 1400–1408; whitespace checks passed. This is research and future planning only: no code, source connector, paid inference, live model/graph/CDE write or runtime UAT was performed. The draw.io pages predate the latest Jev and GSD paragraphs of the concept and may need an optional visual update when planning the phase; they are not runtime evidence. Source licensing, second pilot jurisdiction, detailed identity/ACL schema and adapter transfer rights remain explicit design gates.

## Resume

Keep v13 active and do not run `/gsd-new-milestone` while its phase/state files are in flight. At a separately approved transition, reconcile unfinished v13 prerequisites and applicable v12 debt, discuss unresolved v14 design gates, and only then activate the isolated future requirements/roadmap and create executable phase plans. For implementation, verify exact source rights, security/evidence/SWRL contracts and native adapter workspaces before relevant changes.
