---
tags: [decisions, building-codes, gsd, v14]
date: 2026-10-12
status: accepted for future planning, not activated
---

# Building-code integration is isolated as future v14.0

**Decision (owner, 2026-10-12):** Plan the full integration of building codes into Design Grammars as a separate future milestone, v14.0, rather than adding a norm phase to the active v13.0 DeGram milestone. The accepted separation does not approve implementation or activate v14.

**Why:** v13/1302 owns generic CDE SourceRevision, company vocabulary releases, steward approval and project rule revisions; 1303/1304/1306 own native bindings, evidence and Revit reads. Full code-source connectors, clause enumeration, standard-linked concept retrieval, rule compilation, measured normative bindings, partial library acceptance and project migration, optional Jev routing and independent normative UAT are additional product capabilities. Phases 1308 and 1309 already belong to Web UI and hosting. Duplicating DGKN/DGBN/DGST/DGHN/DGRL ownership or calling those IDs complete would hide work and misstate evidence.

**Planning record:** `.planning/milestones/v14.0-REQUIREMENTS.md` reserves 27 unchecked IDs and `.planning/milestones/v14.0-ROADMAP.md` assigns phases 1400–1408. The norm source uses SpecGraph, company concepts Ontograph, project rules Metagraph, model bindings Computgraph and evidence ValidGraph; no sixth graph. An approved standard concept URI/version anchors a proposed alignment, never creates an internal class without steward review. Three links require separate semantic and model/measurement approval. Accepted/rejected decisions have scope, and a rule-based/retrieval-first baseline operates without Jev. The adapter requires an offline privacy/quality/cost gate. Source/library acceptance is clause-selective and atomic in Neo4j; each project activates its candidate revision separately. Existing canonical status/evidence contracts remain authoritative.

**Activation:** Leave v13 as Current Milestone and `.planning/phases/` untouched. At an explicitly authorized transition, reconcile unfinished v13 prerequisites and accepted v12 debt before bringing future v14 requirements into the active GSD control plane. No live connectors, paid inference, CAD/graph/CDE writes or deployment follow from this decision.

**References:** [[sessions/2026-10-12 Building code integration research and v14 planning|research and planning session]], `docs/reviews/building-code-validation-integration-analysis/Design Grammars × Building Codes — концепция интеграции.md`, `.planning/milestones/v13.0-OWNERSHIP.md`.
