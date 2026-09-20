---
status: testing
phase: 36-computgraph-persistence-display
source: [ROADMAP.md Phase 36 Success Criteria, 36-VERIFICATION.md]
started: 2026-07-20T00:00:00Z
updated: 2026-07-26T00:00:00Z
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  gap_snapshot: "testing::scenarios=0"
---

## Current Test

number: 3
name: Provenance is queryable per node (SC3)
expected: Every Computgraph node answers a provenance query with source, provider/model when recognized, definitionId and publishedAt.
awaiting: LIVE re-run of test 3 in Rhino — F6's transport chain is code-fixed and seam-verified but has never executed on a real canvas

## Test conditions (2026-07-25 session)

Run as Group 4.5-4.6 of `.planning/milestones/v9.0-phases/v9.0-PIPELINE-UAT.md` on the **UrbanBlock_V7** canvas, NOT
the Frame fixture (no Frame `.gh` exists — JSON fixtures only). Project `urbanblock-uat`, Neo4j
Computgraph a clean slate beforehand. Published structure = 2 tagged Procedures (11 unnamed, 12
"BUILDING MASS EXTRUDING") + 1 tagged Pattern + 1 tagged Const, plus 4 entities accepted from Phase 35
synthetic proposals (nested Pattern `SUBPLOT`, `TargetScr` Var, `Result` Emg, `ScrRatio` IntF). The
`Num` Const proposal was ungrouped mid-test to work around F5. `Building` has no Class IRI, so
`REFERS_TO Object→Class` is untested (optional in SC1).

**Update 2026-07-26 — F5 fixed, subgraph re-verified at full size.** With the F5 parser fix deployed,
the `Num` Const that had to be ungrouped as a workaround was re-grouped and published. Tests 1 and 2
were re-run on the resulting **12-node / 13-relationship** subgraph (was 11/12); see the appended
results below. No data-service rebuild was needed — the image (built 2026-07-25T09:59Z) is newer than
the last `data-service/` commit (`3e76bb2`, 2026-07-19), and its OpenAPI still serves all three
`/computgraph/*` routes.

**Deployment gap found first:** the running `data-service` container predated Phase 36 entirely — it
served `/computgraph/context/pull` and `/computgraph/recognize` but had no `/computgraph/publish`, so
the first publish attempt returned 404. `docker compose build data-service && up -d` fixed it. Phase 36
shipped code-complete but had never been deployed, i.e. this endpoint had never once run before this
session.

## Tests

### 1. Publish confirmed Frame → expected subgraph, project-scoped (SC1)

expected: Publishing the confirmed Frame structure (DG COMPUTGRAPH PUBLISH, or the confirm-then-publish output on DG STRUCTURE CONFIRM) yields the expected Neo4j subgraph — one Object–Behavior–Algorithm chain, 2 Procedures (11_Proc 2D Truss Configuration, 12_Proc 2D Footer Configuration), correct patterns/parameters (paramKind Variable/Constant/Emergent + dataType)/interfaces (ifaceType Input/Output), all with graph:'Computgraph' + project; relationships HAS_BEHAVIOR/HAS_ALGORITHM/HAS_PROCEDURE/HAS_PATTERN/PATTERN_HOST_TO/HAS_PARAMETER/HAS_INTERFACE/PARAM_LINK present; optional REFERS_TO Object→Class when a Class IRI was tagged. DEDUP: this single subgraph-shape check is the terminal integration gate — a correct subgraph transitively re-proves Phase 32 parse + Phase 34 tags + Phase 35 recognition.
result: pass (adapted to UrbanBlock) — 2026-07-25. DG COMPUTGRAPH PUBLISH returned `published` with empty StaleEntityIds. Neo4j: 11 nodes = Object 1 / Behavior 1 / Algorithm 1 / Procedure 2 / Pattern 2 / Parameter 3 / Interface 1, all graph:'Computgraph' + project:'urbanblock-uat'; 12 relationships = HAS_BEHAVIOR 1, HAS_ALGORITHM 1, HAS_PROCEDURE 2, HAS_PATTERN 2, PATTERN_HOST_TO 1, HAS_PARAMETER 3, HAS_INTERFACE 1, PARAM_LINK 1. Every expected relationship type present, exactly matching the pre-computed prediction from the context pull. paramKind coverage complete (Constant `Gr`, Variable `TargetScr`, Emergent `Result`) with dataType on each; ifaceType Input on `ScrRatio`. REFERS_TO Object→Class = 0 (no Class IRI on `Building`) — declared gap, optional per the criterion. Terminal integration gate: transitively re-proves Phase 32 parse + Phase 34 tags + Phase 35 accept. NOT the Frame's literal "2 Procedures 11_Proc 2D Truss / 12_Proc 2D Footer" — same shape, different fixture. **Re-verified 2026-07-26 at full size after the F5 fix: 12 nodes = Object 1 / Behavior 1 / Algorithm 1 / Procedure 2 / Pattern 2 / Parameter 4 / Interface 1; 13 relationships = the same 8 types with HAS_PARAMETER now 4. The +1 node / +1 rel is `cg:1:const:11_Const_Num` (Constant / Float / dg:D11F0CBE622F3039), the parameter that previously could not be published at all — so the gate now passes on the complete canvas with no workaround in place.** All 4 parameters carry a non-null dataType (`Gr` Integer, `Num` Float, `TargetScr` Integer, `Result` Text).

### 2. Re-publish is MERGE-idempotent — zero node-count change (SC2)

expected: Re-publishing the same definition changes ZERO node counts (verified by a before/after count query). MERGE keys are stable entity ids from definition id + convention name, so re-publish updates in place and never duplicates; every published node retains its Phase 32.1 dgId across the re-publish.
result: pass — 2026-07-25. Re-published the unchanged canvas (pull → POST /computgraph/publish; the route recomputes dgId server-side regardless of client stamping, so this is equivalent to a second component trigger). Response `published` with identical publishedCounts {object 1, behavior 1, algorithms 1, procedures 2, patterns 2, parameters 3, interfaces 1, paramLinks 1} and empty staleEntityIds. Before/after diff: 11 nodes → 11 nodes, 12 relationships → 12 relationships, per-label counts byte-identical, and all 9 dgIds unchanged. MERGE idempotency holds. **Re-confirmed 2026-07-26 on the full 12-node subgraph and via a real second component trigger this time (Publish toggled False→True in Grasshopper, closing the test-2 gap noted below): 12 nodes → 12 nodes, 13 relationships → 13 relationships. Zero parameters with a null dataType; the only 2 nodes without a dgId are Behavior + Algorithm, by design.**

### 3. Provenance is queryable per node (SC3)

expected: Every Computgraph node answers a provenance query — source (tagged | recognized), provider/model (when source=recognized), definitionId, and publishedAt timestamp. A MATCH over the published Frame subgraph returns these properties for each node.
result: PARTIAL — 2026-07-25. PASSES: `source` correct on all 9 entity nodes (5 tagged / 4 recognized, matching the canvas exactly), `definitionId` and `publishedAt` on all 11, `dgId` on all 9 entity nodes. The 2 nodes without dgId are Behavior and Algorithm, which is BY DESIGN — CLAUDE.md/spec/DG-ID.md scope dgId to Object/Procedure/Pattern/Parameter/Interface only. FAILS: `provider` / `model` / `confidence` are null on every recognized node, and this is structural, not an artefact of using synthetic proposals — see F6. **Status 2026-07-26: F6's transport chain is CODE-FIXED and seam-verified (see the F6 finding below), but this test has NOT been re-run live — it stays PARTIAL until a Rhino recognize→confirm→publish round on a real canvas returns a non-null provider/model/confidence from the provenance query.**

### 4. ui-v2 shows Computgraph layer distinctly + per-project filter (SC4)

expected: The ui-v2 graph datascape (ui-v2/src/graph + ui-v2/src/screens) shows the Computgraph layer with distinct styling for the new labels (Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface, correct casing via buildRings.js), correct orbit/caption placement (Behavior caption shows definitionId per WR-08), and a per-project filter toggle isolating the Computgraph layer for the active project. Hard-refresh (Ctrl+Shift+R) after any design-grammars container rebuild.
result: pass — 2026-07-25. The served bundle was verified current before testing (contains the Computgraph ring code — no rebuild needed, unlike data-service). All 11 published nodes render on the Graph screen for project `urbanblock-uat` with the expected ring placement (ring 0 Object/Behavior/Algorithm, ring 1 Procedure/Pattern, ring 2 Parameter/Interface per buildRings.js:17), distinct per-label styling, Behavior captioned with the definitionId (WR-08), and the per-project filter isolating the layer. Expected non-defect: the unnamed Procedure 11 and the Algorithm render with empty captions — a canvas-tagging artefact, not a UI fault.

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Findings

### F6 — provider/model/confidence can never be persisted for recognized nodes

`computgraph_publish.py` reads `procedure.get("provider")` / `.get("model")` / `.get("confidence")` and
writes them whenever `source == "recognized"` (lines 183-186, 201-204, 241-244, 267-270, 313-315) — but
nothing upstream ever supplies them. The Computgraph models carry no Provider/Model/Confidence fields,
`ComputgraphContextSerializer` emits none, and the accept path in StructureConfirmComponent stores only
a boolean `dg.recognized.<guid>` ValueTable marker (line 210), discarding the model identity and the
confidence score at confirm time. So every recognized node publishes with those three properties null,
and SC3's "provider/model when source=recognized" is unimplemented rather than untested. Confirmed by
code inspection, not just by the synthetic-proposal run. Suggested fix: extend PreviewRegistry entries

+ the ValueTable marker (or a sidecar ValueTable key per group) to carry provider/model/confidence

through accept, add the fields to the Cg* models and the serializer. Severity: medium (provenance is a
stated Phase 36 success criterion and an auditability requirement for LLM-authored structure).

Secondary, folded in here: Behavior and Algorithm nodes carry no `source` property at all, while SC3
says "every node". They are synthesized container nodes rather than tagged/recognized entities, so this
is arguably correct-by-design — but the criterion and the implementation disagree and one of them
should move.

**F6 CODE-FIXED 2026-07-26 via `/gsd-audit-fix` — NOT yet live-verified.** The transport chain that was
missing now exists end to end:

1. `cg_recognition.recognize_structure()` returns the run's resolved `provider`/`model` (top level AND
   injected into the returned `proposal`) — it resolved them all along and dropped them on the floor.
2. `CanvasListenerComponent.ParseProposals` reads `provider`/`model` off the `preview_structure`
   command's top level (per-proposal override wins) into `ProposalDto` → `PreviewEntry`.
3. `StructureConfirmComponent`'s accept path writes them, plus the proposal's confidence, into the
   `dg.recognized.<guid>` ValueTable marker via the new `DG.Core.Parsing.RecognitionMarker` — a compact
   JSON value replacing the bare `"true"` literal that was discarding all three.
4. `CanvasContextExtractor` parses the marker back into `RawGroup.Provider/Model/Confidence`;
   `CanvasAnnotationParser` propagates onto all four entity kinds; `ComputgraphContextSerializer`'s
   `Cg*Dto` types carry them to the wire.
5. `computgraph_publish.py` needed NO change — it has always read these three keys.

Backward compatibility: a pre-fix canvas holds the legacy `"true"` marker, still parses as
`source: recognized`, and still publishes null provenance — re-confirming those groups is the only way
to attribute them. An Ollama-fallback run records `provider: "ollama"` with a null `model`.

Verification done: 16 new xUnit tests (`RecognitionProvenanceFlowTests`) pin the marker format
(round-trip, legacy `"true"`, unreadable-value handling, the ValueTable key), parser propagation, and
the wire round-trip; 4 new pytest cases pin the recognize response. The C#↔Python seam was checked for
real — live `ComputgraphContextSerializer` output was fed through `computgraph_publish._build_publish_params`
and produced `provider='anthropic' model='claude-opus-4-6' confidence=0.87` on the Procedure and
Parameter rows. **Not verified: the two Grasshopper-only links (the marker write in
StructureConfirmComponent, the marker read in CanvasContextExtractor) and marker survival across
`.gh` save/reopen — `DG.Tests` cannot reference `DG.Grasshopper`, so these need the live Rhino run
that test 3 is now awaiting. The data-service container also needs a rebuild for the recognize change
(cf. F7).**

Secondary resolved by moving the criterion, not the code: `spec/DATABASE.md`'s Behavior section now
states that `source`/`provider`/`model`/`confidence` are scoped to the five *entity* labels, exactly as
`dgId` already is per `spec/DG-ID.md`, and that SC3's "every node" reads as "every entity node".
Inventing a third `source` enum value for synthesized containers would have contradicted the documented
`tagged | recognized` enum and the `ObjectShape_source` SHACL `sh:in` constraint.

### F7 — Phase 36 was never deployed (see Test conditions)

The running data-service image predated the phase; `/computgraph/publish` returned 404 on first
attempt. Not a code defect, but it means no Phase 36 code had ever executed outside unit tests before
2026-07-25, and 36-VERIFICATION.md's "code-complete" was never a deployment claim. Worth a standing
check: after any phase that adds a data-service route, rebuild the container before UAT.

## Gaps

- Not run on the Frame fixture (no Frame `.gh` exists — JSON fixtures only). Test 1's literal Frame
  expectation ("2 Procedures: 11_Proc 2D Truss Configuration, 12_Proc 2D Footer Configuration") is
  therefore unverified; the equivalent shape check passed on UrbanBlock_V7 instead.
- `REFERS_TO Object→Class` untested — `Building` carries no Class IRI. Optional per SC1; to close,
  re-run DG OBJECT MARKER with a Class IRI and re-publish.
- ~~Test 2 was driven through the HTTP route rather than a second component trigger~~ — **closed
  2026-07-26**: re-run as a real rising-edge trigger on DG COMPUTGRAPH PUBLISH, counts unchanged.
- Prior code-review fixes (WR-08 Behavior caption, WR-09 ComputgraphPublishClient 15s timeout) closed;
  WR-08 visually confirmed in test 4.
