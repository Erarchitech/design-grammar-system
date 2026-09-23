---
tags: [session, audit, research, architecture, gsd]
date: 2026-09-19
---

# Session: 2026-09-19 — Theory–Implementation Alignment Audit and GSD Planning

## Goal

Investigate the alignment between the Design Grammars implementation, R15.7, the ontology and standards artefacts, Obsidian/Graphify knowledge, and GSD planning. Produce a traceable theory–implementation plan without modifying source code, the manuscript, planning files, or live services.

## What Was Done

- Read and extracted `Publications/T1_ITcon_DG_Draft_R15.7.docx` without editing it.
- Captured manuscript metadata: 240 body paragraphs, 6 tables, 49 DOCX parts, 3 insertions, SHA-256 `5768d2f8f316b3bbe6ab459510fb79effb361c519de083077385fae1b2893ad9`.
- Audited repository structure, FastAPI routes, n8n workflows, Docker Compose services, ontology/specification artefacts, C# Grasshopper code, tests, GSD planning, Obsidian notes, and Graphify snapshots.
- Verified runtime/build evidence: data-service 772 passed with 1 skipped; dg-reasoner 39 passed; DG .NET tests 412 passed; Release build passed with 0 warnings/errors; ui-v2 production build passed with a chunk-size warning; Docker Compose configuration passed.
- Audited all 39 manuscript references; 30 were material to the theory/architecture/standards claims. Crossref resolved 26/27 DOI-bearing records. Identified 8 bibliography defects or verification tasks.
- Produced a 50-claim paper register (`PAPER-C-001`–`PAPER-C-050), 13 GSD alignment proposals (`GSD-ALIGN-001`–`GSD-ALIGN-013`), backend/C#/literature/GSD/knowledge-graph audit artefacts, and a 62-artifact integrated evidence index.
- Produced the final report: `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md` (419 lines, 7,476 words).

## Decisions Made

- The appropriate near-term direction is a **conditional GO** for bounded theory–implementation alignment revision, but **NO-GO** for unqualified claims of a full SWRL/OWL reasoner, complete cross-platform BIM integration, lossless Design State replay, production CDE governance, or universal LLM determinism.
- Retain the current hybrid architecture for the next alignment milestone; adopt a canonical evidence envelope and explicit validation-status vocabulary before considering an RDF-canonical or typed-domain-service migration.
- Treat the paper's `ATTRIBUTE_OF` bridge as an explicit decision point: implement it or revise the paper/specification to the runtime's `PARAM_LINK`/`inputBindings` contract.
- Treat Graphify as stale context: latest inspected snapshot is 15,605 nodes/23,659 links at commit `77abe053`, one commit behind `HEAD`; an older 5,412-node snapshot is historical. No Graphify rebuild was performed.
- Classify semantic, architectural, security, governance, and manuscript decisions as manual-only; classify localized code/test repairs as auto-fixable only after contract decisions; keep unavailable live UAT as pending/blocked/unknown.

## Issues Encountered

- The repository had extensive pre-existing staged, modified, and untracked changes. No unrelated files were altered.
- Some official standards and publisher sources were blocked or paywalled; unsupported sentence-level claims were marked explicitly rather than inferred.
- GSD control files disagree on some phase and requirement statuses; Phase 35 SC1 is a measured failure (M1 0.03125 versus 0.60), while several phases retain human UAT gates.
- Security/tenancy is not equivalent to project-property filtering: browser auth is client-side/localStorage, ordinary data-service routes lack server-side tenant enforcement, and direct Neo4j proxy access exists.
- The current implementation is a partitioned system of deterministic validators, OWL/SHACL sidecar checks, LLM proposal paths, ComputGraph structural capture, and Speckle persistence—not one unified reasoning engine.

## Next Steps

- Review the final report and decide which manuscript claims require revision before applying any edits.
- Decide `ATTRIBUTE_OF` versus `PARAM_LINK` as the normative rule–parameter contract.
- Define canonical validation statuses for missing population, unsupported built-ins, indeterminate results, and errors.
- Plan the cross-service golden fixture and DE-01 deterministic equivalence experiment.
- Reconcile GSD control-plane status, especially Phase 35 SC1 and the Phase 36–39 manual/prototype boundaries.
- Keep security/tenancy hardening as a release gate before external multi-user evaluation.

## Related Notes

- [[2026-09-19 T1 ITcon R15.6 title and keywords finalisation]]
- [[dissemination/consistency-map|Dissemination consistency map]]
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md`
- `docs/reviews/theory-implementation-alignment/evidence/paper-claims.json`
- `docs/reviews/theory-implementation-alignment/evidence/gsd-proposed-updates.json`
- `docs/reviews/theory-implementation-alignment/evidence/integrated-index.json`
