---
tags: [session, phase-36, f6, provenance]
date: 2026-07-26
---

# Session: 2026-07-26 — Phase 36 F6 fix — provenance transport chain

## Goal
Fix Phase 36 UAT finding F6: `provider`/`model`/`confidence` were structurally unpersistable for recognized entities — `computgraph_publish.py` read and wrote them, but nothing upstream supplied them because the LLM provider/model were resolved and dropped at recognize time, and the accept path discarded them into a bare `"true"` marker.

## What Was Done

Built the missing transport across seven links:
1. **RecognitionMarker** (new `DG.Core.Parsing`) — owns the canvas ValueTable marker format. Compact JSON replaces bare `"true"`, preserves backward compatibility
2. **cg_recognition.recognize_structure** — return run's provider/model at top level AND inject into proposal
3. **CanvasListenerComponent.ParseProposals** — read provider/model off preview_structure command top level into ProposalDto
4. **PreviewRegistry / PreviewEntry** — carry Provider/Model through the preview lifecycle
5. **StructureConfirmComponent** — stamp provider/model/confidence into the marker at accept time
6. **CanvasContextExtractor** — parse marker back into RawGroup
7. **CanvasAnnotationParser + ComputgraphContextSerializer** — propagate through all entity kinds to the wire

Added 16 xUnit tests pinning marker round-trip, legacy `"true"` parsing, unreadable-value handling, and the full parser→wire path. Added 4 pytest cases for recognition response. Live seam check: real `ComputgraphContextSerializer` output through `_build_publish_params` produced the three fields with correct values on Procedure and Parameter rows.

Also resolved F6b (secondary) by moving the criterion in spec/DATABASE.md: scoped provenance to the five *entity* labels (Object, Procedure, Pattern, Parameter, Interface) exactly as `dgId` is scoped per spec/DG-ID.md. Behavior/Algorithm are synthesized server-side and carry no `source`.

## Decisions Made

- Marker format is compact JSON not just `"true"` — allows escaping when provider/model are null
- Legacy `"true"` parses as recognized-with-null provenance, not as "not recognized" — preserves `source: recognized` on old canvases
- F6b resolved by moving SC3 criterion, not code — inventing a third `source` enum value would violate the documented `tagged | recognized` constraint

## Issues Encountered

- Concurrent git activity mid-session: while I had F6 parser edits uncommitted, another agent committed a redo of plan 35-16 (`fix(35-16)`) that swept my 12 parser lines into its commit. Re-checking after, the redo (`c6eabee`) was clean and my lines came back to the working tree. Backed up all work to scratchpad before committing to avoid the reset loop.
- Initial baseline test count was wrong: 384 passing, 3 failing, but the DLL was stale — the 3 reds were 35-16's pre-written red tests. Final count after the other agent landed 35-16: 405/405 green

## Next Steps

- Live verification **still outstanding**: 36-UAT test 3 (SC3 / provenance query) stays PARTIAL. The two Grasshopper-only links (marker write in StructureConfirmComponent, marker read in CanvasContextExtractor) and marker survival across `.gh` save/reopen are unreachable from `DG.Tests`. Requires a real Rhino session: recognize → confirm → publish, then query provenance and verify non-null provider/model/confidence
- Rebuild data-service before that run (recognize response changed — cf. F7)
- Update 36-UAT and v9.0-PIPELINE-UAT.md with the live-verification note (done but awaiting the actual run)
- Outstanding audit items: **3** (F3 model quality, F6 live verification, F7 standing checklist)

## Related Notes

- [[decisions/Phase 36 F6 provenance transport — marker format and backward compat]]
