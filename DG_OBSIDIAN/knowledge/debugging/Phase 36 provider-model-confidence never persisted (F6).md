---
tags: [debugging, computgraph, provenance, phase-35, phase-36]
date: 2026-07-25
status: open
---

# F6 — provider/model/confidence can never be persisted for recognized nodes

**Context:** v9.0-PIPELINE-UAT Group 4.5, 36 test 3 (provenance query, SC3). `source` (tagged/recognized), `definitionId`, `publishedAt` and `dgId` all came back correctly for every entity node — but `provider`, `model`, `confidence` were null on every `recognized` node, including ones accepted from live proposals in this same session.

## Root cause

`computgraph_publish.py` reads `procedure.get("provider")` / `.get("model")` / `.get("confidence")` and writes them whenever `source == "recognized"` (lines 183-186, 201-204, 241-244, 267-270, 313-315) — but **nothing upstream ever supplies these fields**:

- The `Cg*` models (DG.Core) carry no Provider/Model/Confidence properties.
- `ComputgraphContextSerializer` emits none.
- `StructureConfirmComponent.ApplyToDocument` (the Phase 35 accept path) stores only a boolean `dg.recognized.<guid>` ValueTable marker (`StructureConfirmComponent.cs:210`) — the model identity and confidence score that arrived with the original proposal are discarded at confirm time, never carried forward.

So this isn't a data-availability gap in one test run — **it's structurally unimplemented**. SC3's "provider/model when source=recognized" clause has no code path that could ever satisfy it as written.

## Secondary observation

`Behavior` and `Algorithm` nodes carry no `source` property at all, while SC3 says "every node". They're synthesized container nodes rather than tagged/recognized entities — arguably correct by design, but the criterion and the implementation disagree, and one of them should move.

## Suggested fix

Extend `PreviewRegistry` entries (and the ValueTable persistence — either widen the `dg.recognized.<guid>` marker to a JSON blob, or add sidecar ValueTable keys per group) to carry `provider`/`model`/`confidence` through accept. Add the corresponding fields to the `Cg*` models and `ComputgraphContextSerializer`.

**Severity:** medium — provenance is a stated Phase 36 success criterion and an auditability requirement for LLM-authored structure, but doesn't block publish/idempotency/display (36 tests 1/2/4 all pass independently).

**Cross-phase:** 35 (accept path drops the data) → 36 (publish reads fields that never existed).

## Related

- [[debugging/Phase 35-36 dataType inference gap breaks publish (F5)]]
- `.planning/phases/36-computgraph-persistence-display/36-UAT.md` test 3
