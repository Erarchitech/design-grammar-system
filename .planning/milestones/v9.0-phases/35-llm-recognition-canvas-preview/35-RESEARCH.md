# Phase 35: LLM Recognition and On-Canvas Proposal Preview - Research

**Researched:** 2026-07-19
**Domain:** LLM-driven structure recognition over a serialized Grasshopper canvas + live GH canvas mutation (preview groups/scribbles) + GH undo/confirm UX
**Confidence:** HIGH (architecture/contracts — grounded in shipped Phase 29/32/33/34 code); MEDIUM (exact GH_Group visual-style limits, LLM JSON-output reliability); LOW (none — no ungrounded claims in this document)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **`data-service/cg_recognition.py`** + `POST /computgraph/recognize`:
   - Input: `cgContextJson v1` (pulled live via the bridge, or posted directly)
   - Prompt assembly through `dg_context.py`: Computgraph concept catalog (dgc: classes/relations/enums + the annotation-convention grammar), the **Frame few-shot example** (canvas-context excerpt → correct entity classification), the tagged entities as ground-truth anchors, and the untagged nodes/wires/groups
   - LLM call via the Phase-1 gateway (`llm_gateway.py`) — provider-agnostic, works on Ollama fallback
   - Output: **proposed-structure JSON** (contract in `../32-computgraph-serialization-core/32-RESEARCH.md` §6) — per proposal `kind`, `suggestedName` (convention-conformant), `procedureIndex`, `memberIds`, `confidence`, `rationale`; plus `unrecognized[]` with reasons
   - Output is schema-validated in data-service (jsonschema/pydantic); invalid output → bounded retry with the violation list fed back (mirror of CTXA-04); member ids must exist in the submitted context and not overlap tagged entities — hard reject otherwise. **Never invented, never silently dropped.**
2. **Preview rendering (bridge `preview_structure`):** the listener draws each proposal as a temporary `GH_Group` (preview style from `CanvasAnnotationStyles`: desaturated/dashed variant of the target kind color) named `[?] <suggestedName> (<confidence>)`, plus a scribble legend; **all inside one `GH_UndoRecord`** ("DG structure proposal") so Ctrl+Z wipes everything. `clear_preview` does the same programmatically. Preview state is tracked by the listener (proposal id ↔ group instance GUID) and reported via `get_preview_status`.
3. **DG STRUCTURE CONFIRM** (`Components/StructureConfirmComponent.cs`):
   - Shows pending proposals (name, kind, confidence, member count) as output text; inputs `Accept` (list of proposal ids or `*`), `Reject` (ids), `Apply` (button)
   - Accept → the preview group is restyled/renamed into a **permanent convention group** (identical to a Phase 34 manual tag) and marked `source: recognized` in the listener's annotation registry; Reject → group removed cleanly
   - Partial accept supported; leftover proposals stay pending
   - Nothing in this flow writes to Neo4j — publish is Phase 36, and it only ever sees confirmed structure
4. Recognition run scope: per algorithm (whole canvas) by default; optional `procedureIndex` filter for iterating one procedure at a time on large definitions (scalability).

### Constraints

- Tagged entities are immutable ground truth — the LLM may not rename, split, or absorb them.
- Confidence and rationale are mandatory per proposal (auditable AI, feeds provenance in Phase 36).
- All previews must be removable by a single undo — no orphan scribbles/groups after reject.
- Token scalability: `cgContextJson` sent to the LLM is trimmed (node name/nickname/position + wires + group hints; no geometry payloads); definitions beyond a node-count threshold are processed per-procedure.
- Works on Ollama fallback (degraded quality acceptable; contract compliance still enforced by the validator).

### Claude's Discretion (Open for planning)

- Where the `source: recognized` marker persists across file save: listener in-memory registry vs GH document `UserData` (preferred: document UserData keyed by group instance GUID — survives reopen).
- Confirm UX detail: value-list of proposal ids vs "accept all above confidence X" input.
- Few-shot budget: one worked Frame procedure vs the full Frame example — measure prompt size in planning.

### Deferred Ideas (OUT OF SCOPE)

None recorded in 35-CONTEXT.md beyond the milestone-level Out of Scope table (REQUIREMENTS.md): AI *generation*/editing of GH parts, cluster introspection, and vendoring grasshopper-mcp remain out of scope per the v9.0 REQUIREMENTS.md "Out of Scope" table — this phase only recognizes and previews, never writes/generates canvas content beyond the preview scaffold.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RCGN-01 | Recognition pipeline classifies untagged entities into proposals via the LLM gateway, using tags as anchors + concept catalog + Frame few-shot; schema-validated with bounded retry | §"Architecture Patterns" Pattern 1 (recognition pipeline composition reusing `dg_context.assemble_context`/`dg_knowledge.load_computgraph_catalog`/`llm_gateway`), §"Code Examples" (validator mirroring `validate_cypher`), §"Common Pitfalls" 1 (JSON-from-LLM-text extraction has no existing precedent in this repo) |
| RCGN-02 | Proposals render on canvas as temporary preview groups/scribbles, in an undo record, removable via undo or `clear_preview` | §"Architecture Patterns" Pattern 2 (extending `CanvasListenerComponent`'s 3 stub handlers), Pattern 3 (preview registry shared between listener and confirm component), §"Common Pitfalls" 2-4 (GH_Group has no dashed-border API; UI-thread write marshalling differs from read-only precedent; scribble legend has no fill/border) |
| RCGN-03 | DG STRUCTURE CONFIRM lists pending proposals; accept converts to permanent convention groups with `source: recognized`; reject cleans up; partial accept supported | §"Architecture Patterns" Pattern 3 (shared `PreviewRegistry`), Pattern 4 (`source: recognized` persistence via `GH_Document.ValueTable`, existing precedent), §"Runtime State Inventory"-adjacent note: `CanvasAnnotationParser`/`RawGroup`/`CgProcedure` etc. need an additive `Source` propagation path from the ValueTable marker |
| RCGN-04 | Nothing published to Neo4j without confirmation; unrecognized blocks reported with member ids, never invented/dropped | §"Constraints" (locked decision 1: hard reject on overlap with tagged members); confirmed no Neo4j write path exists anywhere in `cg_recognition.py`/bridge preview commands — Phase 36 owns `/computgraph/publish` exclusively (verified: `grep` for `/computgraph/publish` returns nothing pre-Phase-36) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Schema Change Propagation checklist** (CLAUDE.md) does not apply to this phase in the Neo4j sense (no new labels/relationships — Phase 36 owns persistence) but DOES apply to the **DG Canvas Annotation Convention** if the recognition pipeline introduces any new nickname/marker convention (e.g. a `[?]` preview prefix or a UserData key) — document any new convention token in `training/dataset_schema.json`'s sibling annotation-convention doc if one exists, and in this phase's own artifacts at minimum.
- **Conditional compilation `#if GRASSHOPPER_SDK`** guards all GH-dependent code in `DG.Grasshopper` — `StructureConfirmComponent.cs` and any preview-rendering additions to `CanvasListenerComponent.cs` MUST follow this pattern (verified: every existing component in `DG/src/DG.Grasshopper/Components/` uses it).
- **DG.Core vs DG.Grasshopper split**: GH-free logic (schema types, name-factory helpers) belongs in `DG.Core`; GH SDK-dependent code (actual `GH_Group`/`GH_Scribble` mutation, `GH_UndoRecord`) belongs in `DG.Grasshopper`. `DG.Tests` (net9.0) cannot reference `DG.Grasshopper` (net7.0-windows, NU1201 TFM incompatibility) — confirmed unchanged since Phase 33/34; any new xUnit-testable logic for this phase must live in `DG.Core`.
- **What+Where+How-to-fix error pattern** (`ErrorMessageTemplates` on the C# side; `_structured_error_response` on the Python side) — all new error paths in `cg_recognition.py` and the preview command handlers must follow this.
- **No message queue, synchronous HTTP + async polling** — `/computgraph/recognize` should be a synchronous request/response like the existing `/context/generate-cypher`, not a background job (consistent with the project's standing architecture decision).

## Summary

Phase 35 is the "fill the gap" half of the tag→recognize→preview→confirm→publish pipeline. Three of its four deliverables are **extending already-scaffolded seams**, not building from zero:

1. **The wire protocol, dispatcher, and Python client already exist and are stubbed out.** `CanvasCommandDispatcher` in `CanvasListenerComponent.BuildDispatcher()` currently wires `preview_structure`/`clear_preview`/`get_preview_status` to `CanvasCommandDispatcher.StubResult(...)`, which returns `{"supported": false, ..., "message": "Not supported in v9.0 (Phase 35)."}`. The Python side (`gh_bridge.py`'s `preview_structure()`/`clear_preview()`/`get_preview_status()`, and `/mcp`'s `gh_preview_structure`/`gh_clear_preview` tools) already forwards to these stubs and passes the result through untouched — confirmed by `test_gh_bridge.py`'s `test_preview_structure_stub_returns_without_raising`. **Phase 35's job on the C# side is to replace the three stub lambdas with real handlers**, not add new wire-protocol plumbing.
2. **`CanvasAnnotationStyles.Preview(Color baseColor)` already exists** as a Phase-34-added scaffold (alpha=140/255 desaturation) — the "distinct preview style" requirement's color half is already coded; only the "dashed" half needs a design decision (see Pitfall 2 — GH's public SDK does not appear to expose a border/dash-style property on `GH_Group`, based on both the existing codebase's use of `GH_Group` (only `NickName`/`Colour`/`ObjectIDs` are ever touched) and this session's WebSearch).
3. **The undo/group/read-before-write patterns are proven code, reusable near-verbatim** from `EntityTagComponent.cs`: `doc.ScheduleSolution(1, ...)` deferred mutation, `GH_UndoRecord` + `GH_AddObjectAction`/`GH_GenericObjectAction` + `UndoServer.PushUndoRecord`, `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationParser.Parse` read-before-write, and `CanvasAnnotationNameFactory` for convention-conformant names. **New territory**: the preview command runs from the async TCP accept loop (not from a component's own `SolveInstance`), so the mutation-scheduling story needs one architectural decision the planner must make explicitly (see Pattern 2).
4. **The recognition pipeline itself (`cg_recognition.py`) is new code**, but its ingredients are all shipped: `dg_context.assemble_context`-style context composition, `dg_knowledge.load_computgraph_catalog()` for the concept catalog, `llm_gateway.get_adapter()`/`resolve_active_provider()` for the provider-agnostic call, and `dg_context.generate_validated_cypher()`'s bounded-retry-with-corrective-feedback loop as the direct structural template for a new `validate_proposed_structure()` + bounded retry. The one genuinely new problem is that recognition must extract **JSON** from an LLM text response — the existing ingest/edit/query flows explicitly instruct the LLM to output plain Cypher text ("no JSON, no markdown fences"), so there is **no existing precedent in this codebase** for parsing a JSON payload out of LLM output. This is flagged as Pitfall 1.
5. **`source: recognized` persistence has a proven, already-used mechanism**: `GH_Document.ValueTable.SetValue/GetValue` is already used by `ObjectMarkerComponent` to persist `dg.objectClassIri` across file save/reopen. This directly answers CONTEXT.md's open planning question — recommend `ValueTable` (not a listener in-memory dictionary, which dies on Rhino restart) keyed by group `InstanceGuid`, read back by an additive extension to `CanvasContextExtractor`/`CanvasAnnotationParser` (see Pattern 4). This is the same mechanism CONTEXT.md's own preferred option describes ("document UserData keyed by group instance GUID — survives reopen") — `ValueTable` IS that mechanism in this codebase's vocabulary.

**Primary recommendation:** Build `cg_recognition.py` as a sibling module to `dg_context.py` reusing its assembly/validation idioms verbatim (don't invent new patterns); replace the three C# dispatcher stubs with real handlers that reuse `EntityTagComponent`'s proven undo/mutation idiom; introduce one new shared class (`DG.Grasshopper.Canvas.PreviewRegistry` or similar) so `CanvasListenerComponent` and `StructureConfirmComponent` — two independent GH components — can see the same pending-proposal state; and persist `source: recognized` via `GH_Document.ValueTable`, propagated through an additive (non-breaking) extension to the raw-canvas → parsed-context pipeline.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM prompt assembly (concept catalog + anchors + few-shot) | API / Backend (`data-service/cg_recognition.py`) | — | Mirrors `dg_context.py`'s existing assembly pattern; deterministic composition, no embeddings (CTXA-05 precedent extends here) |
| LLM call (provider-agnostic) | API / Backend (`llm_gateway.py`) | — | Single gateway per the standing v9.0 architecture decision; recognition is just a new caller |
| Proposed-structure schema validation + bounded retry | API / Backend (`cg_recognition.py`) | — | Same tier and pattern as `validate_cypher`/`generate_validated_cypher` (CTXA-04 mirror, explicitly required by CONTEXT.md) |
| Canvas preview rendering (temporary `GH_Group`/`GH_Scribble`, undo record) | Browser-equivalent / Local Desktop Client (`DG.Grasshopper` — `CanvasListenerComponent`) | — | Only the live Rhino/GH process can mutate a `GH_Document`; data-service never touches canvas objects directly, only via the bridge's JSON commands |
| Pending-proposal state (proposal id ↔ group GUID, confidence, rationale) | Local Desktop Client (new shared registry class in `DG.Grasshopper`) | — | Must be visible to BOTH `CanvasListenerComponent` (writes it on `preview_structure`) and `StructureConfirmComponent` (reads/mutates it on Accept/Reject) — two independent components in the same process, not a network boundary |
| Confirm/reject UX (accept/reject ids, convert preview→permanent) | Local Desktop Client (`StructureConfirmComponent`) | — | Pure canvas mutation + undo, no network call — everything needed (preview registry, `CanvasAnnotationStyles`, `CanvasAnnotationNameFactory`) already lives in-process |
| `source: recognized` persistence across file save | Local Desktop Client (`GH_Document.ValueTable`) | Data flows into API tier read-side (`cgContextJson.source` field) | `ValueTable` is a GH_Document-scoped, save-file-persisted store — no Neo4j write happens until Phase 36 |
| Neo4j write | *(out of scope for this phase)* | — | Explicitly deferred to Phase 36 `POST /computgraph/publish` — RCGN-04 requires this phase writes nothing to Neo4j |

## Standard Stack

### Core

No new external libraries are required. This phase is 100% composition of already-installed/already-vendored building blocks.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (pinned in `data-service/requirements.txt`, unversioned pin — confirmed installed) | `POST /computgraph/recognize` route | Existing data-service framework, every other endpoint uses it |
| pydantic | (bundled with FastAPI, already used pervasively — e.g. `GenerateRequest`, `ContextAssembleRequest`) | Request/response models for `cg_recognition.py` | Matches the exact modeling style of every sibling module (`dg_context.py`, `llm_gateway.py`) — [VERIFIED: local codebase] |
| Grasshopper SDK (`Grasshopper.Kernel`, `Grasshopper.Kernel.Undo`, `Grasshopper.Kernel.Undo.Actions`) | Rhino 8 SDK, already referenced by `DG.Grasshopper` | `GH_Group`, `GH_Scribble`, `GH_UndoRecord`, `GH_AddObjectAction`, `GH_GenericObjectAction` | Same APIs `EntityTagComponent`/`ObjectMarkerComponent` already use — [VERIFIED: local codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (Python stdlib) | — | Extracting/parsing the LLM's JSON text response | No new dependency — but see Pitfall 1 for the extraction discipline needed (markdown-fence stripping, bounded retry on parse failure) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `validate_proposed_structure()` (pydantic model + custom checks, mirroring `validate_cypher`) | `jsonschema` package (formal JSON Schema validation) | `jsonschema` is **not** in `data-service/requirements.txt` today — [VERIFIED: `data-service/requirements.txt` contains no `jsonschema` entry]. Every existing CTXA-04-style validator in this codebase (`validate_cypher`) is a hand-rolled Python function returning `{"valid": bool, "violations": [{"code","message","path"}]}`, not a JSON-Schema-driven one. Adding `jsonschema` would introduce a new package and a new validation idiom inconsistent with the established pattern — recommend the hand-rolled approach purely for consistency, not because `jsonschema` is wrong. |
| `GH_Document.ValueTable` for `source: recognized` persistence | A custom sidecar file (e.g. `.dgpreview.json` next to the `.gh` file) | `ValueTable` already has a proven precedent in this exact codebase (`ObjectMarkerComponent`'s `dg.objectClassIri`) and survives save/reopen automatically with the `.gh` file — a sidecar file adds a new failure mode (file gets separated from the `.gh`, path resolution, doesn't roundtrip through Rhino's own save mechanism). |

**Installation:** None — no new packages for either data-service or DG.Grasshopper.

**Version verification:** N/A — no new package versions to pin. Existing pins already confirmed installed (`data-service/requirements.txt`: `cryptography, fastapi, httpx, neo4j, pytest, specklepy==3.2.4, uvicorn`; DG.Grasshopper already references the Rhino 8 SDK per Phase 33/34 precedent).

## Package Legitimacy Audit

**No external packages are installed by this phase.** All functionality is composed from libraries already present in `data-service/requirements.txt` and the existing Rhino/Grasshopper SDK reference. The Package Legitimacy Gate protocol is not applicable — there is nothing to run `package-legitimacy check` against.

**Packages removed due to [SLOP] verdict:** none (N/A — no packages proposed)
**Packages flagged as suspicious [SUS]:** none (N/A — no packages proposed)

## Architecture Patterns

### System Architecture Diagram

```
                         ┌────────────────────────────────────────────────┐
                         │         Rhino / Grasshopper process             │
                         │                                                  │
                         │  ┌─────────────────────┐   ┌───────────────────┐│
Architect tags  ────────▶│  │ EntityTagComponent    │   │ CanvasListener    ││
(Phase 34, done)         │  │ (manual tags, done)   │   │ Component         ││
                         │  └──────────┬───────────┘   │ (TCP accept loop) ││
                         │             │ GH_Group/                          │
                         │             │ scribble                          ││
                         │             ▼                                    │
                         │  ┌─────────────────────────────────────────┐    │
                         │  │        GH_Document (live canvas)          │    │
                         │  │  tagged groups + untagged raw nodes/wires │    │
                         │  └──────────┬─────────────────────┬─────────┘    │
                         │             │ (2) get_canvas_context (existing)  │
                         │             │                     │ (5) preview_ │
                         │             │                     │ structure    │
                         │             │                     │ writes       │
                         │             ▼                     │              │
                         │  ┌─────────────────────┐          │              │
                         │  │ PreviewRegistry (NEW,│◀─────────┘              │
                         │  │ shared static class)  │                        │
                         │  │ proposalId ↔ groupGuid│                        │
                         │  │ + kind/confidence/    │──────────┐             │
                         │  │ rationale             │          │ (7) read    │
                         │  └───────────────────────┘          ▼             │
                         │                              ┌───────────────────┐│
                         │                              │ StructureConfirm  ││
                         │                              │ Component (NEW)   ││
                         │                              │ Accept/Reject/     ││
                         │                              │ Apply              ││
                         │                              └──────────┬─────────┘│
                         │                                          │ (8) accept:│
                         │                                          │ restyle +  │
                         │                                          │ ValueTable │
                         │                                          │ marker     │
                         │                                          ▼            │
                         │                              GH_Document.ValueTable   │
                         │                              "dg.recognized.<guid>"   │
                         └────────────────────────────────────────────────┘
                                      ▲                            │
                                      │ (1) TCP: {type, parameters} │ (6) TCP: preview result
                                      │ newline-JSON                │ (proposal ids ↔ guids)
                                      │                              │
                         ┌────────────┴──────────────────────────────┴──────────┐
                         │              data-service (Docker container)          │
                         │                                                        │
                         │  ┌──────────────────┐   ┌──────────────────────────┐  │
   (2) POST /computgraph/│  │ gh_bridge.py      │   │ cg_recognition.py (NEW)  │  │
   context/pull ─────────▶│  (existing client) │   │                          │  │
                         │  └────────┬─────────┘   │  (3) assemble prompt:    │  │
                         │           │ cgContextJson │  concept catalog +       │  │
                         │           ▼               │  Frame few-shot +        │  │
   (4) POST /computgraph/│  ┌──────────────────┐   │  tagged anchors +         │  │
   recognize ────────────▶│  │ POST /computgraph/│   │  untagged nodes/wires   │  │
                         │  │ recognize route   │──▶│                          │  │
                         │  └──────────────────┘   │  (4a) llm_gateway.generate│  │
                         │                          │  (4b) validate_proposed_ │  │
                         │                          │  structure + bounded     │  │
                         │                          │  retry (mirrors CTXA-04) │  │
                         │                          └──────────┬───────────────┘  │
                         │                                     │ proposed-structure│
                         │                                     │ JSON               │
                         │                                     ▼                    │
                         │  (5) POST /computgraph/preview → gh_bridge.preview_       │
                         │      structure(proposal) → TCP command back to Rhino     │
                         └───────────────────────────────────────────────────────┘
```

The critical new architectural piece this diagram makes explicit: **`PreviewRegistry` is a new shared, in-process state holder** — it is the only way `CanvasListenerComponent` (which executes `preview_structure`/`clear_preview`/`get_preview_status` on the async TCP thread) and `StructureConfirmComponent` (a separate `GH_Component` that solves on the UI thread) can agree on what proposals exist and which `GH_Group` instance each one maps to.

### Recommended Project Structure

```
data-service/
├── cg_recognition.py       # NEW — recognition pipeline: assemble prompt, call gateway,
│                           #   validate_proposed_structure(), bounded retry (mirrors
│                           #   dg_context.generate_validated_cypher() structure)
├── tests/
│   └── test_cg_recognition.py   # NEW — unit tests: validator, retry loop, endpoint contract
│                           #   (mirror test_dg_context.py's TestValidator/TestRetryLoop/
│                           #   TestGenerateCypherEndpoint class shapes)
└── app.py                  # MODIFIED — add POST /computgraph/recognize route (thin,
                             #   delegates to cg_recognition like /context/generate-cypher
                             #   delegates to dg_context)

DG/src/DG.Core/
├── Bridge/
│   └── CanvasCommandDispatcher.cs   # MODIFIED (or unchanged) — BuildDispatcher() in
│                                    #   CanvasListenerComponent.cs swaps stub lambdas for
│                                    #   real handlers; CanvasBridgeCommands/Protocol/
│                                    #   Dispatcher classes themselves likely need ZERO changes
└── Models/Computgraph/
    └── RawCanvas.cs / CgProcedure.cs / etc.   # MODIFIED (additive) — RawGroup gains an
                                    #   optional "recognized" flag read from ValueTable;
                                    #   Cg* entities' Source can become "recognized"

DG/src/DG.Grasshopper/
├── Canvas/
│   ├── CanvasAnnotationStyles.cs   # MODIFIED (additive) — Preview() already exists;
│   │                               #   add whatever "distinct preview style" constants
│   │                               #   are still missing (name-prefix constant, e.g. "[?] ")
│   ├── CanvasContextExtractor.cs   # MODIFIED (additive) — read ValueTable per-group marker
│   │                               #   when building RawGroup, so recognized status survives
│   │                               #   into the parsed CgContext
│   └── PreviewRegistry.cs          # NEW — shared, thread-safe (background TCP thread +
│                                   #   UI-thread solve) registry: proposalId → (groupGuid,
│                                   #   kind, suggestedName, confidence, rationale, status)
└── Components/
    ├── CanvasListenerComponent.cs  # MODIFIED — 3 stub handlers become real:
    │                               #   HandlePreviewStructure / HandleClearPreview /
    │                               #   HandleGetPreviewStatus
    └── StructureConfirmComponent.cs   # NEW — DG STRUCTURE CONFIRM: reads PreviewRegistry,
                                       #   Accept/Reject inputs, Apply trigger, restyle/
                                       #   remove groups, write ValueTable marker on accept

DG/tests/DG.Tests/
└── PreviewRegistryTests.cs  # NEW (if PreviewRegistry logic can be split GH-free) — or
                             #   accept that, like EntityTagComponent, most of this is
                             #   manual-only live-Rhino UAT (see Validation Architecture)
```

### Pattern 1: Recognition pipeline composition (mirror `dg_context.py`'s existing assembler + CTXA-04 retry loop)

**What:** `cg_recognition.py` should NOT invent a new prompt-assembly or retry idiom. It should call the exact same building blocks `dg_context.assemble_context()` already composes (`dg_knowledge.load_computgraph_catalog()`, `dg_knowledge.swrl_conventions()` if relevant, and the live `cgContextJson`), format them into one prompt, then run the exact bounded-retry shape `generate_validated_cypher()` already implements — but validating against a `validate_proposed_structure()` function instead of `validate_cypher()`.

**When to use:** Building `cg_recognition.recognize_structure(cg_context: dict, procedure_index: int | None = None) -> dict`.

**Example:**
```python
# Source: data-service/dg_context.py (this repo, lines 880-922) — the exact structural
# template to follow; only the validator function and prompt-assembly change.
def recognize_structure(cg_context: dict, max_retries: int = 2) -> dict:
    prompt = _build_recognition_prompt(cg_context)  # concept catalog + Frame few-shot +
                                                     # tagged anchors + untagged nodes/wires

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))

    current_prompt = prompt
    violations: list[dict] = []
    for attempt in range(max_retries + 1):
        req = GenerateRequest(prompt=current_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key)
        parsed, parse_error = _extract_json(response.text)  # Pitfall 1 — new logic
        if parse_error:
            violations = [{"code": "bad_json", "message": parse_error, "path": None}]
            current_prompt = append_corrective_feedback(prompt, violations)
            continue
        result = validate_proposed_structure(parsed, cg_context)
        if result["valid"]:
            return {"valid": True, "proposal": parsed, "attempts": attempt + 1}
        violations = result["violations"]
        current_prompt = append_corrective_feedback(prompt, violations)

    return {"valid": False, "violations": violations, "attempts": max_retries + 1}
```

### Pattern 2: Extending the 3 stub bridge commands — a NEW mutation-marshalling decision

**What:** `CanvasListenerComponent.BuildDispatcher()` today wires `preview_structure`/`clear_preview`/`get_preview_status` to `StubResult(...)`. Replacing them with real handlers is straightforward for `get_preview_status` (pure read of `PreviewRegistry`, same `InvokeOnCanvas` pattern already used for `get_canvas_context`/`get_selection`). **`preview_structure` and `clear_preview` are different**: they must *write* to the `GH_Document` (add/remove `GH_Group`/`GH_Scribble` objects), and the existing `InvokeOnCanvas` helper only supports read-and-return, never a write.

**When to use:** Designing `HandlePreviewStructure`/`HandleClearPreview`.

**Key architectural difference from `EntityTagComponent`:** `EntityTagComponent.SolveInstance` defers its mutation via `doc.ScheduleSolution(1, ...)` specifically because the SDK forbids mutating the document *while a solution is in progress* — i.e. from inside another component's own `SolveInstance`. The bridge commands, by contrast, arrive asynchronously from the TCP accept loop, **not from inside any component's `SolveInstance`** — there is no active solution to be careful around at the moment the command lands. The safe, consistent choice is still to marshal onto the UI thread (exactly like the existing `InvokeOnCanvas` does for reads) and, once there, either (a) mutate directly if no solution is in progress, or (b) use the same `ScheduleSolution` idiom defensively regardless, since it costs nothing and guarantees correctness even if a solution happens to be active at that instant (e.g. the user is mid-drag when a preview request lands). **Recommendation: reuse `ScheduleSolution` + `GH_UndoRecord` + `GH_AddObjectAction`/`GH_GenericObjectAction` unconditionally**, matching `EntityTagComponent`'s proven pattern, rather than introducing a second, untested "direct mutation" code path. This means `HandlePreviewStructure` needs a *synchronous-looking but internally-deferred* write helper — likely a `TaskCompletionSource`-based wrapper (like `InvokeOnCanvas`) that resolves only after the `ScheduleSolution` callback has actually run and expired the solution, so the TCP response is sent only after the preview groups genuinely exist on canvas.

**Example:**
```csharp
// Source: DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs (this repo) —
// InvokeOnCanvas's TaskCompletionSource pattern, extended with a write variant.
private object? HandlePreviewStructure(CanvasCommandRequest request)
{
    return InvokeOnCanvasWrite(doc =>
    {
        var proposals = ParseProposals(request); // from proposed-structure JSON parameters
        var created = new List<(string proposalId, Guid groupGuid)>();

        var record = new GH_UndoRecord("DG structure proposal");
        foreach (var proposal in proposals)
        {
            var scrib = new GH_Scribble();
            scrib.CreateAttributes();
            scrib.Text = $"[?] {proposal.SuggestedName} ({proposal.Confidence:P0})";
            doc.AddObject(scrib, false);

            var group = new GH_Group();
            group.CreateAttributes();
            group.NickName = $"[?] {proposal.SuggestedName}";
            group.Colour = CanvasAnnotationStyles.Preview(
                CanvasAnnotationStyles.ForKind(proposal.Kind, nested: false));
            foreach (var id in proposal.MemberIds) group.AddObject(Guid.Parse(id));

            record.AddAction(new GH_AddObjectAction(group));
            doc.AddObject(group, false);
            created.Add((proposal.ProposalId, group.InstanceGuid));
        }
        doc.UndoServer.PushUndoRecord(record);

        PreviewRegistry.RegisterAll(created, proposals); // shared state for StructureConfirmComponent
        return (object?)new { previewed = created.Count };
    });
}
```

### Pattern 3: Shared `PreviewRegistry` between two independent components

**What:** `CanvasListenerComponent` (writes previews via the TCP bridge) and `StructureConfirmComponent` (reads/mutates them via canvas UX) are two separate `GH_Component` instances. Neither owns the other, and there is no guarantee both are even on the same canvas tab at once (though typically they are). A `static` (or singleton, keyed by `GH_Document.DocumentID` if multi-document support ever matters) registry class is the simplest correct answer, following the same "internal static class, module-level state" idiom already used by `CanvasAnnotationStyles`, `DgIcons`, and `DgComponentCategory`.

**When to use:** Any time two independently-placed components must observe shared canvas-scoped state that isn't itself a document object.

**Thread-safety note:** `CanvasListenerComponent`'s handlers execute on the accept-loop's background thread (after `InvokeOnCanvasWrite` returns from the UI thread — but the TCP write of the *response* happens back on the background thread per the existing `ServeClientAsync` contract, so the registry write itself should happen while still marshalled on the UI thread inside the `ScheduleSolution` callback). `StructureConfirmComponent.SolveInstance` runs on the UI thread during a normal GH solve. Because both writers ultimately execute on the UI thread (GH's solve loop is single-threaded), a plain `Dictionary` is likely sufficient without a lock — but using `ConcurrentDictionary` costs nothing and removes any doubt, especially since the *read* in `get_preview_status` happens via the same `InvokeOnCanvas`-on-UI-thread pattern as everything else.

### Pattern 4: `source: recognized` persistence via `GH_Document.ValueTable` (proven precedent)

**What:** `ObjectMarkerComponent` already persists a per-document key (`dg.objectClassIri`) via `currentDoc.ValueTable.SetValue(...)` / `doc?.ValueTable.GetValue(...)`. This is a `.gh`-file-persisted, per-document string key/value store — exactly the "GH document UserData... survives reopen" mechanism CONTEXT.md's open question describes as preferred.

**When to use:** On Accept in `StructureConfirmComponent`, after restyling the preview group into a permanent convention group (Phase 34 colors/nickname via `CanvasAnnotationNameFactory`/`CanvasAnnotationStyles.ForKind`), write `doc.ValueTable.SetValue($"dg.recognized.{group.InstanceGuid}", "true")` (optionally also stash provider/model/timestamp as additional keys, e.g. `dg.recognized.{guid}.provider`, satisfying CGPD-03's future provenance need one phase early at zero extra cost). Then, **additively** extend `CanvasContextExtractor.TryAddGroup` to read this marker (needs the `GH_Document` reference it already has) and set a new `RawGroup.Recognized` bool; `CanvasAnnotationParser.Parse` (DG.Core, GH-free) reads `RawGroup.Recognized` and sets the typed entity's `Source = recognized ? "recognized" : "tagged"` instead of always `"tagged"`.

**Example:**
```csharp
// Source: DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs (this repo, lines
// ~120-176) — the exact proven ValueTable read/write precedent to extend.
var storedIri = doc?.ValueTable.GetValue("dg.objectClassIri", string.Empty);
// ...
currentDoc.ValueTable.SetValue("dg.objectClassIri", classIri);

// Phase 35 extension (same idiom, new key):
currentDoc.ValueTable.SetValue($"dg.recognized.{group.InstanceGuid}", "true");
// ... and in CanvasContextExtractor.TryAddGroup:
var isRecognized = doc.ValueTable.GetValue($"dg.recognized.{group.InstanceGuid}", "false") == "true";
```

**Important boundary note:** Phase 34-01's SUMMARY records "Additive-only grammar extraction — `CanvasAnnotationParser.cs` never edited" as a locked pattern for that phase. Phase 35 **will** need to touch `CanvasAnnotationParser.Parse` (and `RawGroup`) — but purely additively (a new optional field read, defaulted to `"tagged"` when absent), not a change to the nickname-regex classification logic itself. Flag this explicitly to the planner as the one place this phase crosses into previously-"locked" Phase 32/34 code, and scope it as a single, narrow, regression-tested change (existing `CanvasAnnotationParserTests.cs`/`CanvasAnnotationNameFactoryTests.cs`/`FrameFixtureTests.cs` must still pass unmodified).

### Anti-Patterns to Avoid

- **Re-POSTing to `/llm/generate` on every retry attempt:** `generate_validated_cypher()`'s own doc comment explicitly calls this out as an anti-pattern it avoids ("NEVER re-POSTs... avoids a redundant network hop + provider re-resolution on every retry attempt"). `cg_recognition.py`'s retry loop must call the adapter in-process the same way, not loop back through the FastAPI route.
- **Trusting the LLM's `memberIds` without cross-checking against the submitted context:** CONTEXT.md's locked decision is explicit — "member ids must exist in the submitted context and not overlap tagged entities — hard reject otherwise." This must be a validator check, not a prompt instruction alone (prompt instructions are advisory; LLMs hallucinate ids).
- **Inventing a new "dashed border" `GH_Group` feature that doesn't exist in the public SDK:** don't spend implementation time hunting for a `LineStyle`/`Dashed` property on `GH_Group` — no such property is used anywhere in this codebase, and this session's WebSearch found no confirmed public property for it either (see Pitfall 2). Achieve visual distinctiveness through the already-scaffolded `Preview()` alpha-desaturation + the `[?]` name prefix + the scribble legend, not a border style.
- **Treating the preview registry as per-request instead of per-document:** if a user has two `.gh` files open, previews must not leak across documents — key the registry (or scope its lifetime) by `GH_Document.DocumentID`, mirroring how `CanvasListenerComponent` itself is a per-canvas-instance component.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM provider selection/encryption/error-mapping | A second provider-dispatch layer inside `cg_recognition.py` | `llm_gateway.resolve_active_provider()` + `get_adapter()` (existing, Phase 28) | One gateway per the standing architecture decision — recognition is just another caller, exactly like `dg_context.generate_validated_cypher()` |
| Cypher/JSON validation-with-retry loop shape | A bespoke recognition-specific retry mechanism | Mirror `dg_context.generate_validated_cypher()`'s exact loop structure (bounded attempts, corrective feedback appended to the *original* prompt each retry, never accumulating retries into an ever-growing prompt) | Already reviewed/battle-tested in this codebase (CTXA-04); CONTEXT.md explicitly calls this out as "mirror of CTXA-04" |
| Undo composition for canvas mutation | A custom undo/redo tracking mechanism | `GH_UndoRecord` + `GH_AddObjectAction`/`GH_GenericObjectAction` + `doc.UndoServer.PushUndoRecord` (proven in `EntityTagComponent`/`ObjectMarkerComponent`) | Grasshopper's own undo stack is the only thing Ctrl+Z actually hooks into — a parallel mechanism would not respond to Ctrl+Z as CONTEXT.md's success criterion 2 requires |
| Per-document persisted key/value state | A sidecar JSON file or a custom document-extension mechanism | `GH_Document.ValueTable` (proven in `ObjectMarkerComponent`) | Already saves/reloads with the `.gh` file automatically; a new mechanism would need its own save/load wiring and could desync from the canvas |

**Key insight:** every piece of infrastructure this phase needs (undo, provider-agnostic LLM call, bounded validation retry, per-document persistence, read-before-write canvas parsing) was already built and proven in Phases 28/29/32/33/34. The engineering risk in Phase 35 is almost entirely in the **two genuinely new problems** — (1) getting structured JSON reliably out of an LLM that may run on Ollama fallback, and (2) marshalling a *write* (not just a read) from the async bridge thread onto the UI thread safely — not in re-deriving infrastructure that already exists.

## Common Pitfalls

### Pitfall 1: No existing precedent for extracting JSON from LLM text output

**What goes wrong:** every existing LLM call site in this repo (`rules-to-metagraph.json`'s prompt, `dg_context.generate_validated_cypher()`) explicitly instructs the LLM to output **plain text, not JSON** ("Output Cypher only, no JSON, no markdown fences" — confirmed via grep of `n8n/workflows/rules-to-metagraph.json`). Recognition needs the opposite: strict, parseable JSON. LLMs (especially smaller Ollama-fallback models) commonly wrap JSON in markdown code fences (` ```json ... ``` `), add leading/trailing prose, or emit near-valid-but-not-quite JSON (trailing commas, single quotes).

**Why it happens:** no code in this repo has ever needed to parse JSON *out of* an LLM's raw text response before — this is a first for the codebase.

**How to avoid:** write a small `_extract_json(text: str) -> tuple[dict | None, str | None]` helper in `cg_recognition.py` that: (1) strips a leading/trailing ` ```json `/` ``` ` fence if present, (2) finds the outermost `{...}` span if there's leading/trailing prose, (3) attempts `json.loads`, returning a structured parse-error message on failure so it feeds into the same bounded-retry corrective-feedback loop as a schema violation (treat "bad_json" as its own violation code). Include an explicit prompt instruction ("Output ONLY a single JSON object, no markdown fences, no commentary") mirroring the existing Cypher-prompt precedent's own explicit-output-discipline style, but do not rely on the instruction alone — the extraction helper is the actual mitigation.

**Warning signs:** on Ollama fallback specifically, expect a higher rate of malformed JSON — CONTEXT.md's constraint "works on Ollama fallback (degraded quality acceptable; contract compliance still enforced by the validator)" already anticipates this; the bounded retry (mirroring CTXA-04's `max_retries=2`) is the safety net, not a guarantee of success — plan for a final "recognition failed after N attempts" structured error path (What+Where+How-to-fix) distinct from "recognition succeeded but found nothing to propose."

### Pitfall 2: `GH_Group` likely has no public dashed-border/line-style API

**What goes wrong:** CONTEXT.md's decision 2 asks for a "dashed/desaturated variant" preview style. `CanvasAnnotationStyles.ForKind`/`Preview` (the only `GH_Group`-styling code in this repo) only ever sets `.Colour` — no code anywhere in this codebase touches a border/line-style property on `GH_Group`. This session's WebSearch for `GH_Group` border/dash properties did not surface a confirmed public property either (results were tangential — `GH_ObjectSettings.GroupColour`, `GH_Colour`, generic SDK links, nothing confirming a dash-style property on `GH_Group` itself).

**Why it happens:** the public Grasshopper SDK's `GH_Group` type appears to expose only `NickName`/`Colour`/`ObjectIDs`/`Border` (fill vs. outline enum, not a dash pattern) in the surface this codebase has ever needed — a genuine dashed border may not be achievable without a custom `IGH_DocumentObject` attributes override, well beyond this phase's proven-pattern budget.

**How to avoid:** treat "dashed" as an ASSUMED/soft requirement and achieve the "clearly distinct, temporary-looking" visual goal through the mechanisms this codebase already has proof for: (a) `CanvasAnnotationStyles.Preview()`'s alpha desaturation (already coded), (b) the `[?] <suggestedName> (<confidence>)` NickName prefix (a *text* signal, always renders regardless of SDK styling limits), and (c) an accompanying `GH_Scribble` legend. Flag this explicitly to the user/planner as a scope note — "dashed" per CONTEXT.md's wording may need to be relaxed to "desaturated + prefixed + legend" unless a live-Rhino spike during planning/execution confirms a real dash-style API exists.

### Pitfall 3: Bridge preview commands write to the canvas from a different execution context than `EntityTagComponent`

**What goes wrong:** copying `EntityTagComponent`'s `ScheduleSolution` pattern verbatim without noticing it assumes the caller is itself a `GH_Component.SolveInstance` (which has a `doc` reference and runs during an active solve pass) — the bridge handler instead runs from `InvokeOnCanvas`'s `RhinoApp.InvokeOnUiThread` callback, invoked from the TCP accept loop, with no `SolveInstance` context of its own.

**Why it happens:** `ScheduleSolution(1, callback)` schedules the callback to run on the **next** solution pass — if there is no pending solve and nothing ever triggers one, the callback may be delayed indefinitely (GH generally solves promptly on any expire, but a preview command shouldn't depend on some *other* component happening to expire soon).

**How to avoid:** as covered in Pattern 2, don't reuse `ScheduleSolution` blindly — either mutate the document directly while already on the UI thread (via `InvokeOnCanvasWrite`, with no active-solve concern since the bridge command isn't itself inside a `SolveInstance`), or explicitly call `doc.NewSolution(false)` / force a redraw (`Grasshopper.Instances.InvalidateCanvas()`, already used by `EntityTagComponent`) immediately after a direct mutation so the preview appears without waiting for an unrelated trigger. This is a decision the planner must make explicitly and verify in the live-Rhino UAT step (see Validation Architecture) — it cannot be fully resolved by static research alone.

### Pitfall 4: `GH_Scribble` has no fill/border styling — the "scribble legend" is text-only

**What goes wrong:** assuming the preview's scribble legend can be colored/boxed distinctly like the preview groups. `ObjectMarkerComponent`'s only `GH_Scribble` usage sets `.Text` and `.Font` — no color/fill/border property is used anywhere in this codebase for scribbles, and 34-RESEARCH.md's own Pitfall 4 ("Assuming `GH_Scribble` uses a simple `Attributes.Pivot` point like other components") already flags scribble API surface as under-documented/uncertain (Tertiary confidence in that phase's Sources).

**How to avoid:** design the preview legend scribble as a plain text annotation (e.g. `"[?] N proposal(s) pending — run DG STRUCTURE CONFIRM"`), not a colored/boxed element — consistent with every existing scribble in the codebase.

## Code Examples

### `validate_proposed_structure()` — mirrors `validate_cypher()`'s violation-list shape

```python
# Source: data-service/dg_context.py's validate_cypher() (this repo) — same return
# shape ({"valid": bool, "violations": [{"code","message","path"}]}) so
# append_corrective_feedback() and the retry loop work unchanged.
def validate_proposed_structure(parsed: dict, cg_context: dict) -> dict:
    violations: list[dict] = []

    proposals = parsed.get("proposals")
    if not isinstance(proposals, list):
        violations.append({"code": "bad_shape", "message": "'proposals' must be a list.", "path": "proposals"})
        return {"valid": False, "violations": violations}

    known_ids = _collect_known_member_ids(cg_context)       # every nodeId across nodes[]
    tagged_ids = _collect_tagged_member_ids(cg_context)      # memberIds already under a
                                                              # tagged procedure/pattern/param/interface

    for i, p in enumerate(proposals):
        path = f"proposals[{i}]"
        for field in ("kind", "suggestedName", "memberIds", "confidence", "rationale"):
            if field not in p:
                violations.append({"code": "missing_field", "message": f"Missing '{field}'.", "path": path})
        member_ids = p.get("memberIds") or []
        unknown = [m for m in member_ids if m not in known_ids]
        if unknown:
            violations.append({"code": "unknown_member_id", "message": f"Ids not in context: {unknown}", "path": path})
        overlap = [m for m in member_ids if m in tagged_ids]
        if overlap:
            violations.append({"code": "tagged_overlap", "message": f"Overlaps ground-truth tags: {overlap}", "path": path})

    return {"valid": len(violations) == 0, "violations": violations}
```

### `PreviewRegistry.cs` — shared static registry (mirrors `CanvasAnnotationStyles`'s internal-static-class idiom)

```csharp
// Source: DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs (this repo) — same
// "internal static class" idiom, extended with mutable state + thread-safety.
internal static class PreviewRegistry
{
    private static readonly ConcurrentDictionary<string, PreviewEntry> _entries = new();

    public static void RegisterAll(IEnumerable<(string proposalId, Guid groupGuid)> created, IEnumerable<ProposalDto> proposals) { /* ... */ }

    public static IReadOnlyCollection<PreviewEntry> Pending => _entries.Values.ToList();

    public static bool TryGet(string proposalId, out PreviewEntry entry) => _entries.TryGetValue(proposalId, out entry!);

    public static void Remove(string proposalId) => _entries.TryRemove(proposalId, out _);

    public static void Clear() => _entries.Clear();
}

internal sealed record PreviewEntry(string ProposalId, Guid GroupGuid, EntityTagKind Kind, string SuggestedName, double Confidence, string Rationale);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Bridge preview commands (`preview_structure`/`clear_preview`/`get_preview_status`) are stubs returning `{"supported": false}` | Phase 35 implements real handlers | This phase | `gh_bridge.py`, `/mcp`'s `gh_preview_structure`/`gh_clear_preview` tools, and `test_gh_bridge.py`'s two stub tests all need their expected result shape updated once real handlers exist — the stub tests (`test_preview_structure_stub_returns_without_raising`, `test_clear_preview_stub_returns_without_raising`) will need replacing, not just extending, since they assert `{"supported": False}` |
| `CgProcedure`/`CgParameter`/etc. `Source` field is always `"tagged"` in practice (parser never emits `"recognized"`) | Parser gains an additive recognized-marker read path | This phase | `CanvasAnnotationParserTests.cs`/`FrameFixtureTests.cs` must still pass unmodified (regression gate, per Phase 34-01's own "consistency test enforces single-source-of-truth" precedent) |

**Deprecated/outdated:** none — this phase does not deprecate anything; it fills in scaffolding (`CanvasAnnotationStyles.Preview()`, the 3 dispatcher stubs, `CanvasBridgeCommands.PreviewStubs`) that Phases 33/34 deliberately left as placeholders for exactly this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GH_Group` has no public dash/line-style property beyond fill `Colour` | Pitfall 2, Anti-Patterns | Low — if a live-Rhino spike during execution finds a real dash-style API, it's a pure enhancement, not a blocker; the fallback (alpha desaturation + `[?]` prefix + legend) is confirmed workable via existing code |
| A2 | Direct UI-thread mutation (bypassing `ScheduleSolution`) is safe for bridge-triggered writes since they don't originate inside another `SolveInstance` | Pattern 2, Pitfall 3 | Medium — if wrong, previews could corrupt the document or throw during a concurrent solve; the plan MUST include a `checkpoint:human-verify` live-Rhino task exercising rapid preview_structure calls while another part of the canvas is actively solving, mirroring Phase 33 Plan 04's precedent |
| A3 | A single shared `PreviewRegistry` (not per-document) is sufficient given this tool's single-architect, typically-single-canvas-tab usage pattern | Pattern 3 | Low — multi-document leakage would only manifest if a user has two `.gh` files open simultaneously and runs recognition in both; scope a `DocumentID`-keyed variant if this proves necessary during UAT |
| A4 | The Frame fixture's parsed/tagged form (comparable in size to the ~8KB raw `frame-cg-context.json` fixture) is small enough to include in full as the few-shot example, resolving CONTEXT.md's "few-shot budget" open question in favor of "full example" over "one worked procedure" | Summary point 5, `<phase_requirements>` | Low — if actual token counts differ significantly from the raw-fixture byte estimate (e.g. because prompt-format JSON is more verbose per-field than the raw fixture), the planner should measure the ACTUAL assembled prompt size in a Wave 0 task rather than trust this estimate blindly |
| A5 | LLM output reliability (valid JSON, valid schema) will be measurably worse on Ollama fallback than on cloud providers, but the bounded retry (mirroring `max_retries=2`) is an acceptable mitigation rather than a guarantee | Pitfall 1 | Medium — if Ollama's fallback model essentially never produces valid JSON, the retry budget alone won't fix it; the plan should include an explicit UAT step recognizing the Frame reference definition on BOTH a cloud provider and Ollama fallback (CONTEXT.md's own constraint: "works on Ollama fallback... contract compliance still enforced by the validator" implies a real recognition may simply fail-with-report on Ollama, which is an acceptable, not a broken, outcome) |

## Open Questions (RESOLVED)

1. **Exact wire shape of the `preview_structure` bridge command's `parameters` payload**
   - What we know: the proposed-structure JSON contract (32-RESEARCH.md §6) defines `proposals[]`/`unrecognized[]`; the bridge wire protocol wraps any JSON object as `parameters`.
   - What's unclear: whether `preview_structure`'s `parameters` is the full `{"proposals": [...], "unrecognized": [...]}` envelope, or just `{"proposals": [...]}` (unrecognized blocks presumably don't get previewed, only reported) — CONTEXT.md doesn't specify this explicitly.
   - Recommendation: the planner should lock this in a task's `<plan_decisions>` — recommend `parameters = {"proposals": [...]}` only (unrecognized blocks are report-only, never rendered on canvas, since there's nothing to preview for something the LLM couldn't classify).

2. **Whether `StructureConfirmComponent`'s Accept path needs to re-derive `procIndex`/pattern-index the same way `EntityTagComponent` does, or can trust the LLM's `procedureIndex` field verbatim**
   - What we know: `CanvasAnnotationNameFactory.ForEntity` requires a valid NN token (`procIndex >= 10`) and, for Patterns, a `patternIndex` — `EntityTagComponent` computes `patternIndex` via `NextFreePatternIndex` at tag-time, never trusting a caller-supplied value.
   - What's unclear: should Accept re-run `NextFreePatternIndex` at accept-time (since other tagging activity may have happened between recognition and confirmation), or trust the `suggestedName` the LLM already produced as the final nickname?
   - Recommendation: **re-validate at accept-time** using the same read-before-write idiom (`CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationNameFactory`) rather than trusting a possibly-stale LLM-suggested name — mirrors the project's own "read-before-write" discipline (34-RESEARCH.md Pattern 2) and avoids a name collision if the architect manually tagged something in the interim.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rhino 8 SDK (RhinoCommon.dll, Grasshopper.dll) | `#if GRASSHOPPER_SDK` code in `CanvasListenerComponent.cs`/new `StructureConfirmComponent.cs` | ✓ (confirmed present per Phase 33/34 RESEARCH.md, unchanged this session) | Rhino 8 | — |
| .NET SDK | Building `DG.Core` (net9.0) / `DG.Grasshopper` (net7.0-windows) | ✓ | 10.0.301 (per 34-RESEARCH.md, unchanged) | — |
| Interactive Rhino/Grasshopper session | Live preview rendering, undo behavior, `StructureConfirmComponent` UX, `ValueTable` save/reopen roundtrip | ✗ (not available in this research/planning environment) | — | All GH-SDK-specific behaviors MUST be gated behind `checkpoint:human-verify` tasks, per Phase 33/34 precedent (both phases deferred live-Rhino UAT to `*-UAT.md`/phase-level `/gsd-verify-work`) |
| LLM provider (cloud key configured, or Ollama running) | `cg_recognition.py`'s actual generate call | Not verifiable from this research session (depends on the executing machine's live Docker/Ollama state at execution time) | — | Ollama fallback is the standing zero-config default (LLMC-05) — the plan should not assume a cloud key is configured |

**Missing dependencies with no fallback:** none — the interactive Rhino session gap has a documented fallback (checkpoint:human-verify gating), consistent with Phase 33/34.

**Missing dependencies with fallback:**
- Interactive Rhino/Grasshopper session — deferred to human-verify checkpoints, same precedent as Phase 33 Plan 04 and Phase 34.
- Cloud LLM key — falls back to Ollama (LLMC-05); recognition quality may degrade but contract compliance is still enforced by `validate_proposed_structure`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (data-service, existing) + xUnit (DG.Core, existing) |
| Config file | none — standard pytest/xUnit, no custom config (matches 33/34 precedent) |
| Quick run command | `python -m pytest data-service/tests/test_cg_recognition.py -x` |
| Full suite command | `python -m pytest data-service/tests/ -x` (Python) + `dotnet test DG/tests/DG.Tests/` (C#) + `dotnet build DG/DG.sln -c Release` |

**Important constraint carried from Phase 33/34:** `DG.Tests` (net9.0) cannot `ProjectReference` `DG.Grasshopper` (net7.0-windows, NU1201 TFM incompatibility — confirmed unchanged). Any new GH-SDK-touching code (`CanvasListenerComponent`'s new handlers, `StructureConfirmComponent`, `PreviewRegistry` if it references GH types) is **not unit-testable from DG.Tests** and requires live-Rhino manual UAT, same as Phase 33/34. Only genuinely GH-free logic (e.g. `validate_proposed_structure`'s Python-side sibling if any C# helper is extracted GH-free, or pure data classes) gets automated xUnit coverage.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RCGN-01 | `validate_proposed_structure` rejects unknown/overlapping member ids, missing fields | unit | `pytest data-service/tests/test_cg_recognition.py::TestValidator -x` | ❌ Wave 0 |
| RCGN-01 | Bounded retry loop mirrors `generate_validated_cypher`'s attempt/violation-feedback shape | unit | `pytest data-service/tests/test_cg_recognition.py::TestRetryLoop -x` | ❌ Wave 0 |
| RCGN-01 | `POST /computgraph/recognize` route contract (thin delegation, error propagation) | integration | `pytest data-service/tests/test_cg_recognition.py::TestRecognizeEndpoint -x` | ❌ Wave 0 |
| RCGN-02 | Preview groups/scribbles created in one undo record; Ctrl+Z and `clear_preview` both wipe everything | manual-only (live Rhino) | — (checkpoint:human-verify) | N/A |
| RCGN-02 | Bridge `preview_structure`/`clear_preview`/`get_preview_status` no longer return the v9.0 stub shape | integration (Python, mocked bridge) | `pytest data-service/tests/test_gh_bridge.py -x` (existing stub tests must be updated, not just re-passed) | ✅ existing file, ❌ new assertions needed |
| RCGN-03 | Accept converts preview group to permanent convention group; Phase 32 extractor reads it back with `source: recognized` | manual-only (live Rhino) + unit (parser propagation, GH-free) | `dotnet test --filter "FullyQualifiedName~CanvasAnnotationParser"` (regression) + live UAT | ❌ Wave 0 (parser extension test), existing regression suite must stay green |
| RCGN-04 | Recognition never calls any Neo4j write path; unrecognized blocks reported with member ids | unit (source-assertion: grep confirms no Neo4j session/driver usage in `cg_recognition.py`) | `grep -c "driver\|session" data-service/cg_recognition.py` (expect 0, or confirm any hits are read-only if the concept-catalog fetch needs a session) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest data-service/tests/test_cg_recognition.py -x` (fast, no live Rhino needed for the recognition half)
- **Per wave merge:** `pytest data-service/tests/ -x` + `dotnet test DG/tests/DG.Tests/` + `dotnet build DG/DG.sln -c Release`
- **Phase gate:** Full suite green (both suites) + Release build clean, before the live-Rhino `checkpoint:human-verify` UAT items are exercised, before `/gsd-verify-work` — same discipline as Phase 33/34.

### Wave 0 Gaps

- [ ] `data-service/tests/test_cg_recognition.py` — covers RCGN-01's validator/retry/endpoint contract (framework already present, zero new install)
- [ ] `DG/tests/DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs` (or extend existing `CanvasAnnotationParserTests.cs`) — covers the additive `Source: "recognized"` propagation path (GH-free, testable)
- [ ] `data-service/tests/test_gh_bridge.py`'s two existing stub tests (`test_preview_structure_stub_returns_without_raising`, `test_clear_preview_stub_returns_without_raising`) must be rewritten once the stubs are replaced — flag as a required edit, not new file
- [ ] No new test-framework install needed — pytest and xUnit already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local desktop plugin + existing data-service trust boundary; no new auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — single local architect, no new project/permission boundary |
| V5 Input Validation | Yes | `validate_proposed_structure()` is the primary control — LLM output is untrusted input reaching canvas mutation and (eventually, Phase 36) Neo4j; every proposal's `memberIds` MUST be checked against the submitted context and against tagged-entity overlap before any preview command reaches the bridge |
| V6 Cryptography | No | N/A — reuses the existing encrypted-at-rest LLM key handling (LLMC-03), no new crypto surface introduced by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM hallucinates `memberIds` that don't exist in the submitted `cgContextJson`, or that reference tagged (ground-truth) entities, corrupting the preview or (later) confirmed structure | Tampering | `validate_proposed_structure()` hard-rejects any proposal referencing unknown or tagged-overlapping member ids — CONTEXT.md's explicit locked constraint; enforced before the proposal ever reaches `preview_structure` |
| LLM output is malformed/non-JSON (especially likely on Ollama fallback), and a naive implementation lets a parse exception propagate as an unhandled 500 | Denial of Service (of the recognize endpoint, locally) | `_extract_json` + bounded retry treats parse failure as a validation violation (mirrors CTXA-04's own failure-handling discipline), never an unhandled exception; final failure surfaces as a structured What+Where+How-to-fix error, matching the project-wide error convention |
| A crafted proposal with an extremely large `memberIds` list or deeply nested proposal structure could be used to exhaust canvas-mutation time or memory when rendering previews | Denial of Service | Bound the proposal count / member count per proposal in `validate_proposed_structure` (reject with a clear violation rather than attempting to render an unbounded preview) — no existing precedent for this specific bound in the codebase, so the planner should pick a concrete number (e.g. reject any single proposal exceeding N members, or a request exceeding M total proposals) as a locked decision during planning |
| A user's `.gh` file is manually edited (or shared/tampered) to inject a `dg.recognized.<guid>` `ValueTable` key without a real recognition ever having occurred, spoofing provenance | Spoofing | Same trust boundary already accepted in 34-RESEARCH.md's Security Domain for tagged-entity spoofing — low severity for a local single-user desktop tool; the `source: recognized` marker is provenance-for-audit, not a security boundary, and CGPD-03 (Phase 36) should treat it as advisory, not authoritative-without-review |

## Sources

### Primary (HIGH confidence)

- `.planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-CONTEXT.md` (this repo) — locked decisions, constraints, open planning questions
- `.planning/REQUIREMENTS.md` (this repo) — RCGN-01..04, milestone Out of Scope table
- `.planning/milestones/v9.0-phases/32-computgraph-serialization-core/32-RESEARCH.md` §5-7 (this repo) — cgContextJson v1 envelope + proposed-structure JSON draft contract + existing-code-to-reuse table
- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (this repo) — `BuildDispatcher()` stub wiring, `InvokeOnCanvas` UI-thread marshalling pattern, TCP accept loop lifecycle
- `DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs`, `CanvasBridgeCommands.cs`, `CanvasBridgeProtocol.cs` (this repo) — wire protocol, allow-list dispatch, `StubResult` shape
- `data-service/gh_bridge.py`, `data-service/tests/test_gh_bridge.py` (this repo) — Python-side bridge client + existing stub test contracts
- `data-service/app.py` (`/computgraph/context/pull`, `/mcp` `gh_*` tools) (this repo) — existing endpoint patterns to extend
- `data-service/dg_context.py` (this repo) — `assemble_context`, `validate_cypher`, `generate_validated_cypher`, `append_corrective_feedback` — the direct structural templates for `cg_recognition.py`
- `data-service/llm_gateway.py` (this repo) — `GenerateRequest`/`GenerateResponse`, `resolve_active_provider`, `get_adapter`
- `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`, `ObjectMarkerComponent.cs` (this repo) — undo/group-mutation pattern, `GH_Document.ValueTable` persistence precedent, `GH_Scribble` creation pattern
- `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs`, `CanvasContextExtractor.cs` (this repo) — existing `Preview()` scaffold, read-before-write traversal, group-nesting detection
- `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs` (this repo) — convention-conformant name construction, reserved-token validation
- `DG/src/DG.Core/Models/Computgraph/CgContext.cs`, `CgProcedure.cs`, `CgParameter.cs` (this repo) — exact field names/shapes for the cgContextJson v1 envelope
- `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` (this repo, measured: 99 lines / 8479 bytes) — Frame few-shot size estimate
- `data-service/requirements.txt` (this repo) — confirms no `jsonschema` package installed, validating the hand-rolled-validator recommendation
- `data-service/tests/test_dg_context.py` (this repo) — `TestValidator`/`TestRetryLoop` test-shape precedent to mirror
- `.planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-RESEARCH.md`, `.planning/milestones/v9.0-phases/34-ontology-tagging-components/34-RESEARCH.md` (this repo) — Security Domain / Validation Architecture section format precedent, Pitfall precedents (UI-thread marshalling, scribble API uncertainty)
- `.planning/milestones/v9.0-phases/34-ontology-tagging-components/34-03-SUMMARY.md` (this repo) — confirms `CanvasAnnotationStyles.Preview()` already exists as a Phase-35 scaffold
- `n8n/workflows/rules-to-metagraph.json` (this repo, grepped) — confirms the existing "no JSON, no markdown fences" LLM-output convention, motivating Pitfall 1
- `CLAUDE.md` (this repo) — project constraints (schema propagation, conditional compilation, DG.Core/DG.Grasshopper split, error-message convention)

### Secondary (MEDIUM confidence)

- [WebSearch, "Grasshopper GH_Group class properties Colour Border NickName API RhinoCommon"] — inconclusive on a dashed-border property; surfaced `GH_ObjectSettings.GroupColour`, `GH_Colour` as tangential confirmations that `Colour`/fill styling is the primary public surface, with no confirmed dash-pattern property found

### Tertiary (LOW confidence)

- None beyond what's already logged in the Assumptions Log — every claim in this document traces to either a direct local-codebase read (Primary) or the one WebSearch above (Secondary, its inconclusiveness is itself the finding).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every building block is a direct, verified read of already-shipped code in this repo
- Architecture: HIGH for the recognition pipeline (direct mirror of `dg_context.py`'s proven CTXA-04 shape) and MEDIUM for the preview-write marshalling (Pattern 2/Pitfall 3 — the exact mutation-context difference from `EntityTagComponent` has no prior code to point to, hence flagged as requiring a live-Rhino UAT decision point, not just a design choice)
- Pitfalls: HIGH for Pitfall 1 (JSON-extraction gap is directly confirmed by grepping the existing prompt text) and MEDIUM for Pitfalls 2/4 (GH_Group/GH_Scribble styling limits — confirmed by absence-of-use in this codebase plus one inconclusive WebSearch, not by an authoritative SDK reference page)

**Research date:** 2026-07-19
**Valid until:** 30 days (stable — this phase depends entirely on already-shipped, stable Phase 28/29/32/33/34 code; the only fast-moving element, LLM JSON-output reliability, is mitigated by the bounded-retry design regardless of provider drift)
