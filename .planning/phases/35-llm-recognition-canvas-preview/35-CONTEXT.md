# Phase 35 Context: LLM Recognition and On-Canvas Proposal Preview

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** RCGN-01..04
**Depends on:** Phase 29 (Computgraph concept catalog in `dg_context.py`), Phase 33 (bridge preview commands), Phase 34 (tags as anchors).

## What this phase is

The AI half of the pipeline: given a canvas where the architect tagged what they know, the LLM classifies the untagged remainder into Computgraph entities, and the proposal is rendered **on the Grasshopper canvas** as clearly-styled temporary groups/scribbles. The architect confirms, partially accepts, or rejects — on the canvas, before anything is persisted. This is the "temporary proposed structure presented for confirmation right on the canvas" requirement.

## Decided

1. **`data-service/cg_recognition.py`** + `POST /computgraph/recognize`:
   - Input: `cgContextJson v1` (pulled live via the bridge, or posted directly)
   - Prompt assembly through `dg_context.py`: Computgraph concept catalog (dgc: classes/relations/enums + the annotation-convention grammar), the **Frame few-shot example** (canvas-context excerpt → correct entity classification), the tagged entities as ground-truth anchors, and the untagged nodes/wires/groups
   - LLM call via the Phase-1 gateway (`llm_gateway.py`) — provider-agnostic, works on Ollama fallback
   - Output: **proposed-structure JSON** (contract in `../32-computgraph-serialization-core/32-RESEARCH.md` §6): per proposal `kind`, `suggestedName` (convention-conformant), `procedureIndex`, `memberIds`, `confidence`, `rationale`; plus `unrecognized[]` with reasons
   - Output is schema-validated in data-service (jsonschema/pydantic); invalid output → bounded retry with the violation list fed back (mirror of CTXA-04); member ids must exist in the submitted context and not overlap tagged entities — hard reject otherwise. **Never invented, never silently dropped.**
2. **Preview rendering (bridge `preview_structure`):** the listener draws each proposal as a temporary `GH_Group` (preview style from `CanvasAnnotationStyles`: desaturated/dashed variant of the target kind color) named `[?] <suggestedName> (<confidence>)`, plus a scribble legend; **all inside one `GH_UndoRecord`** ("DG structure proposal") so Ctrl+Z wipes everything. `clear_preview` does the same programmatically. Preview state is tracked by the listener (proposal id ↔ group instance GUID) and reported via `get_preview_status`.
3. **DG STRUCTURE CONFIRM** (`Components/StructureConfirmComponent.cs`):
   - Shows pending proposals (name, kind, confidence, member count) as output text; inputs `Accept` (list of proposal ids or `*`), `Reject` (ids), `Apply` (button)
   - Accept → the preview group is restyled/renamed into a **permanent convention group** (identical to a Phase 34 manual tag) and marked `source: recognized` in the listener's annotation registry; Reject → group removed cleanly
   - Partial accept supported; leftover proposals stay pending
   - Nothing in this flow writes to Neo4j — publish is Phase 36, and it only ever sees confirmed structure
4. Recognition run scope: per algorithm (whole canvas) by default; optional `procedureIndex` filter for iterating one procedure at a time on large definitions (scalability).

## Constraints

- Tagged entities are immutable ground truth — the LLM may not rename, split, or absorb them.
- Confidence and rationale are mandatory per proposal (auditable AI, feeds provenance in Phase 36).
- All previews must be removable by a single undo — no orphan scribbles/groups after reject.
- Token scalability: `cgContextJson` sent to the LLM is trimmed (node name/nickname/position + wires + group hints; no geometry payloads); definitions beyond a node-count threshold are processed per-procedure.
- Works on Ollama fallback (degraded quality acceptable; contract compliance still enforced by the validator).

## Open for planning

- Where the `source: recognized` marker persists across file save: listener in-memory registry vs GH document `UserData` (preferred: document UserData keyed by group instance GUID — survives reopen).
- Confirm UX detail: value-list of proposal ids vs "accept all above confidence X" input.
- Few-shot budget: one worked Frame procedure vs the full Frame example — measure prompt size in planning.

## Verification sketch

On the Frame definition with only Object marker + two Proc tags: `POST /computgraph/recognize` → proposals cover the known patterns/params/interfaces with member sets matching the reference for the majority of blocks; `preview_structure` shows dashed groups; Ctrl+Z clears all; re-run, accept subset via DG STRUCTURE CONFIRM → permanent groups parse identically to manual tags with `source: recognized`.
