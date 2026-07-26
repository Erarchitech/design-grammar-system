---
tags: [debugging, f6, phase-36, provenance]
date: 2026-07-26
issue: F6 — provider/model/confidence structurally unpersistable
---

# F6: provider/model/confidence were never reached the published nodes

## Root Cause

`computgraph_publish.py` has always had code to read and write `provider`/`model`/`confidence` on recognized entities. The properties existed in the database schema, but **two independent drops** prevented them from ever being populated:

1. **Drop in recognize**: `cg_recognition.recognize_structure()` calls `resolve_active_provider()` to determine which LLM is active and returns it in the response, but the resolve result was used only for the adapter call — it was never surfaced to the caller. Every recognized proposal had no way to know who authored it.

2. **Drop in accept**: `StructureConfirmComponent` wrote a ValueTable marker `dg.recognized.<groupGuid>` = `"true"` (a bare string). The marker recorded THAT the group was recognized but discarded the LLM identity and confidence score, which came from the preview lifecycle (`PreviewRegistry` entry). By the time the context was extracted and parsed, those three values were gone.

Result: every recognized node published with `provider = null`, `model = null`, `confidence = null`, making Phase 36 SC3 unimplemented rather than untested.

## Fix

Built a complete transport chain using a proper marker format. RecognitionMarker (new, in DG.Core) owns the format — a compact JSON object that survives `.gh` save/reopen. The marker is written at accept time with all three values and read back by the extractor, propagated by the parser, and serialized to the wire.

Backward compatibility: pre-fix canvases hold the legacy `"true"` literal. `TryParse` accepts it and returns null provenance, so `source: recognized` is preserved and the canvases keep working — they just stay unattributed until re-confirmed.

## Prevention

- The seam between GH-side (untyped JSON proposal) and publishing (typed Cg* models) was the leak. Now ProvenanceRegistry and PreviewEntry carry Provider/Model through the GH lifecycle, and all Cg* models have the three fields.
- The marker format now has a schema (RecognitionMarker) instead of a magic string. Any future changes go through one place.
- xUnit tests pin the round-trip and edge cases (legacy parse, null handling, the ValueTable key). Marker is in DG.Core so it's testable without the Grasshopper SDK.

## Still Unverified

The two Grasshopper-only links are unreachable from DG.Tests:
- StructureConfirmComponent actually writes the marker via `RecognitionMarker.Serialize()` ✓ (code inspection)
- CanvasContextExtractor actually reads it back via `RecognitionMarker.TryParse()` ✓ (code inspection)
- The marker survives a `.gh` save/reopen cycle — **NOT TESTED**, requires Rhino

Live verification awaits a real recognize → confirm → publish round on a canvas, with a provenance query afterward.
