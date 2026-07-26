---
status: testing
phase: 36-computgraph-persistence-display
source: [ROADMAP.md Phase 36 Success Criteria, 36-VERIFICATION.md]
started: 2026-07-20T00:00:00Z
updated: 2026-07-25T00:00:00Z
---

## Current Test

number: 3
name: Provenance is queryable per node (SC3)
expected: Every Computgraph node answers a provenance query with source, provider/model when recognized, definitionId and publishedAt.
awaiting: code fix for F6 — provider/model/confidence are structurally unpersistable today

## Test conditions (2026-07-25 session)

Run as Group 4.5-4.6 of `.planning/phases/v9.0-PIPELINE-UAT.md` on the **UrbanBlock_V7** canvas, NOT
the Frame fixture (no Frame `.gh` exists — JSON fixtures only). Project `urbanblock-uat`, Neo4j
Computgraph a clean slate beforehand. Published structure = 2 tagged Procedures (11 unnamed, 12
"BUILDING MASS EXTRUDING") + 1 tagged Pattern + 1 tagged Const, plus 4 entities accepted from Phase 35
synthetic proposals (nested Pattern `SUBPLOT`, `TargetScr` Var, `Result` Emg, `ScrRatio` IntF). The
`Num` Const proposal was ungrouped mid-test to work around F5. `Building` has no Class IRI, so
`REFERS_TO Object→Class` is untested (optional in SC1).

**Deployment gap found first:** the running `data-service` container predated Phase 36 entirely — it
served `/computgraph/context/pull` and `/computgraph/recognize` but had no `/computgraph/publish`, so
the first publish attempt returned 404. `docker compose build data-service && up -d` fixed it. Phase 36
shipped code-complete but had never been deployed, i.e. this endpoint had never once run before this
session.

## Tests

### 1. Publish confirmed Frame → expected subgraph, project-scoped (SC1)
expected: Publishing the confirmed Frame structure (DG COMPUTGRAPH PUBLISH, or the confirm-then-publish output on DG STRUCTURE CONFIRM) yields the expected Neo4j subgraph — one Object–Behavior–Algorithm chain, 2 Procedures (11_Proc 2D Truss Configuration, 12_Proc 2D Footer Configuration), correct patterns/parameters (paramKind Variable/Constant/Emergent + dataType)/interfaces (ifaceType Input/Output), all with graph:'Computgraph' + project; relationships HAS_BEHAVIOR/HAS_ALGORITHM/HAS_PROCEDURE/HAS_PATTERN/PATTERN_HOST_TO/HAS_PARAMETER/HAS_INTERFACE/PARAM_LINK present; optional REFERS_TO Object→Class when a Class IRI was tagged. DEDUP: this single subgraph-shape check is the terminal integration gate — a correct subgraph transitively re-proves Phase 32 parse + Phase 34 tags + Phase 35 recognition.
result: pass (adapted to UrbanBlock) — 2026-07-25. DG COMPUTGRAPH PUBLISH returned `published` with empty StaleEntityIds. Neo4j: 11 nodes = Object 1 / Behavior 1 / Algorithm 1 / Procedure 2 / Pattern 2 / Parameter 3 / Interface 1, all graph:'Computgraph' + project:'urbanblock-uat'; 12 relationships = HAS_BEHAVIOR 1, HAS_ALGORITHM 1, HAS_PROCEDURE 2, HAS_PATTERN 2, PATTERN_HOST_TO 1, HAS_PARAMETER 3, HAS_INTERFACE 1, PARAM_LINK 1. Every expected relationship type present, exactly matching the pre-computed prediction from the context pull. paramKind coverage complete (Constant `Gr`, Variable `TargetScr`, Emergent `Result`) with dataType on each; ifaceType Input on `ScrRatio`. REFERS_TO Object→Class = 0 (no Class IRI on `Building`) — declared gap, optional per the criterion. Terminal integration gate: transitively re-proves Phase 32 parse + Phase 34 tags + Phase 35 accept. NOT the Frame's literal "2 Procedures 11_Proc 2D Truss / 12_Proc 2D Footer" — same shape, different fixture.

### 2. Re-publish is MERGE-idempotent — zero node-count change (SC2)
expected: Re-publishing the same definition changes ZERO node counts (verified by a before/after count query). MERGE keys are stable entity ids from definition id + convention name, so re-publish updates in place and never duplicates; every published node retains its Phase 32.1 dgId across the re-publish.
result: pass — 2026-07-25. Re-published the unchanged canvas (pull → POST /computgraph/publish; the route recomputes dgId server-side regardless of client stamping, so this is equivalent to a second component trigger). Response `published` with identical publishedCounts {object 1, behavior 1, algorithms 1, procedures 2, patterns 2, parameters 3, interfaces 1, paramLinks 1} and empty staleEntityIds. Before/after diff: 11 nodes → 11 nodes, 12 relationships → 12 relationships, per-label counts byte-identical, and all 9 dgIds unchanged. MERGE idempotency holds.

### 3. Provenance is queryable per node (SC3)
expected: Every Computgraph node answers a provenance query — source (tagged | recognized), provider/model (when source=recognized), definitionId, and publishedAt timestamp. A MATCH over the published Frame subgraph returns these properties for each node.
result: PARTIAL — 2026-07-25. PASSES: `source` correct on all 9 entity nodes (5 tagged / 4 recognized, matching the canvas exactly), `definitionId` and `publishedAt` on all 11, `dgId` on all 9 entity nodes. The 2 nodes without dgId are Behavior and Algorithm, which is BY DESIGN — CLAUDE.md/spec/DG-ID.md scope dgId to Object/Procedure/Pattern/Parameter/Interface only. FAILS: `provider` / `model` / `confidence` are null on every recognized node, and this is structural, not an artefact of using synthetic proposals — see F6.

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
- Test 2 was driven through the HTTP route rather than a second component trigger (the component path
  was already proven by the first publish; the route recomputes dgId server-side either way).
- Prior code-review fixes (WR-08 Behavior caption, WR-09 ComputgraphPublishClient 15s timeout) closed;
  WR-08 visually confirmed in test 4.
