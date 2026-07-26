---
date: 2026-07-26
tags: [phase-35, execution, wave-3, corpus-b, live-canvas, r4-defect, frame-recovery]
links: [phases/35-llm-recognition-canvas-preview, decisions/Phase-35-Corpus-A-frozen-as-is-binaries-not-committed, debugging/Phase-35-R4-interface-rule-unreachable-on-live-data]
---

# 2026-07-26 Phase 35 Wave 3 Execution — Two-Tier Orchestrator, Corpus B Frozen, R4 Defect Found

## Session Summary

Executed `/gsd-execute-phase 35 --wave 3` (35-12, 35-14). 35-12 shipped autonomously. 35-14 required live Grasshopper interaction — the architect hand-annotated a UrbanBlock_V7 slice across several rounds of live `/computgraph/context/pull` verification before freezing Corpus B. Along the way: recovered the long-lost Frame/Truss `.gh` source (UAT correction), decided against re-grounding Corpus A, and found a real Tier-0 rule defect (R4 unreachable on live data) via the corpus-building process itself.

**Outcome:** 14/16 Phase 35 plans complete. Waves 1–3 done. Waves 4–5 (35-13, 35-15) remain.

## Work Done

### 35-12: Two-tier recognition orchestrator (autonomous, e189fac → 60090c2)

Rewired `cg_recognition.py`: Tier 0 (`cg_topology.py`) decides what it can from topology alone; Tier 1 (LLM) sees only the semantic residue, with a real `system=` prompt (previously never set — the model was reverse-engineering the task from a raw data dump) and feature-enriched candidate lines. Added guardrails G6/G7/G10/G11 plus redacted per-attempt logging. `validate_proposed_structure()` confirmed byte-identical pre/post (diffed against `f018a1f`) — still runs post-merge as the RCGN-04 safety contract. Deleted the F2 fail-open fallback (`_filtered_untagged_node_ids`); `cg_topology.scope_untagged` is now the sole scope-resolution path. 433 tests passing (rebuilt the data-service image per task — no source bind mount).

### Frame/Truss source recovered, UAT corrected (f66a21b)

Architect located `docs/Bridge_Truss_V4_OntologyMapping.gh` (126 KB) and `docs/Truss_Joint_V4_RH7.3dm` (20.4 MB) outside the scanned tree, overturning 35-UAT.md's "no Frame .gh file on disk (whole-profile scan negative)" finding. Identity vs. the `frame.gh` named in `frame-cg-context.json` recorded as plausible-not-confirmed (the fixture's `definition` block is synthetic — canonical Swagger placeholder UUID, round-midnight timestamp — so the filename itself carries little evidential weight).

### Decisions recorded (c15c328)

1. **Corpus A stays as-is** — not re-grounded on a live pull from the recovered file. 35-05's hand-repaired fixture remains frozen; 35-11 stays closed.
2. **Binaries not committed** — `.gitignore` gained `*.gh`/`*.3dm` (verified zero such files were previously tracked, so the rule shadows nothing) to stop a broad `git add` from sweeping the 20 MB `.3dm` into permanent history.

### 35-14: Corpus B frozen (human-action checkpoint → 22cecc6, 4253be0)

**This was the substantive part of the session.** The plan's Task 1 cannot be automated — it requires the architect to annotate a live UrbanBlock_V7 canvas through the normal DG ENTITY TAG UI, independently of the Tier-0 rule table, so the corpus escapes the circularity that disqualifies Corpus A (`tier0Evidence: false`).

Four `/computgraph/context/pull` round-trips over the session, each checked against the plan's composition checklist (FM-1..FM-6, E3) before the architect continued:

1. **First pull** (30 blocks, 4 procedures) — solid coverage on FM-3/4/5/6/E3, but zero nested Patterns and zero bare pass-through `Param`s (FM-2 uncovered).
2. **Second pull** — architect added a nested Pattern (`HeightAssign` → `Extruder`) closing FM-4, but PROC 17 (OPENSPACE) lost its name during editing and fell out of the tagged structure, degrading E3 from 4→3 crossing interfaces. Attempted FM-2 fix (adding `Geometry`/`Integer` components) didn't help — those components sit **inside** a `Proc` group, and `Proc` claims all its members in the first parser pass (`CanvasAnnotationParser.cs:184`), so anything inside is invisible to `scope_untagged`'s ablation.
3. **Third pull** — architect deliberately deleted PROC 17 to make room, but the two added components were still named `Geometry`/`Integer` (real GH component display names), not `Param*` — so R4 still couldn't be probed, and OPENSPACE was now missing outright.
4. **Fourth pull** — PROC 17 restored (32 blocks, 5/6 crossing interfaces, 73 nodes across 4 procedures), two genuine bare relays left outside all `Proc` groups. This is what got frozen.

**Ablation verified independently before handoff to the executor:** 0 entities remaining inside procedures, 0 nickname leaks matching the tagging convention, 32 `untagged.groups` (matches block count), all four `_Proc.memberIds` byte-identical pre/post ablation, node/wire counts unchanged (102/105).

**Executor (Tasks 2–3) derived and froze the reference** from the tagged pull, mirroring `frame_ablated.expected.json`'s shape: 32 blocks (12 Pattern/10 Variable/6 Interface/2 Constant/2 Emergent), `tier0Evidence: true`, 8 `abstainExpected` entries, one nested-Pattern pair, zero member-id collisions. One mechanical fix during derivation: the `Extruder` pattern's raw `memberIds` contained a phantom id that was actually the nested `HeightAssign` child group's own instanceId leaking into the parent — excluded from the reference, verified all 64 member ids resolve to real nodes.

**Freeze protocol respected:** commit `22cecc6` touches exactly two files (context + expected); confirmed no touch to `recognition_system.md`, `frame_recognition_fewshot.json`, or `cg_topology.py`.

### Finding: R4 (Interface classification) is unreachable on live data

While probing FM-2, discovered that Tier-0 rule R4 (`cg_topology.py` ~L383-393, `f.name.startswith("Param")`) can never fire on a real canvas. The C# extractor sets `Name = obj.Name` — the Grasshopper **display** name (`Geometry`, `Integer`, `Number`, `Curve`, ...). No real GH component displays as `Param...`. Scanned all 102 canvas nodes: zero matches. The rule's only test (`test_r4_pass_bare_param_relay_decides_intf`) feeds a synthetic node with `name="Param"` — a name that cannot occur in production, so the test cannot catch this. See [[debugging/Phase 35 R4 interface rule unreachable on live Grasshopper data|full write-up]].

Not fixed in this session — the freeze protocol forbids touching `cg_topology.py` in the same commit as the reference. Left as a follow-up, to be fixed **after** 35-15's ablation sweep (fixing it first would invalidate the SC1 measurement it's meant to inform).

## Invariants Verified

- ✅ `validate_proposed_structure()` byte-identical pre/post 35-12
- ✅ Freeze commit (22cecc6) touches only context+expected, confirmed via `git show --name-only`
- ✅ `contextSha256` in expected.json matches actual file hash independently
- ✅ Zero member-id collisions across 32 blocks
- ✅ All 64 member ids resolve to real nodes in the committed context
- ✅ `tier0Evidence: true` on Corpus B (vs. `false` on Corpus A)
- ✅ 433 data-service tests green post-35-12

## Decisions

1. **Wave-scope interpretation.** User invoked `/gsd-execute-phase 35 Wave 3` (not the literal `--wave 3` flag syntax the skill's own anti-hallucination guard requires). Resolved as `--wave 3` based on corroborating evidence — this user's commit history phrases progress the same way ("Phase 35 Wave 2 complete") — rather than asking, since the skill's flag-filtering rule and the plain-English reading conflicted and asking would have cost nothing but the literal-vs-natural-language tension wasn't genuinely unresolvable from context.

2. **Corpus A frozen as-is; binaries not committed.** See dedicated decision note.

3. **R4 fix deferred past 35-15.** A code fix to `cg_topology.py` before the ablation sweep would contaminate the very measurement Corpus B exists to produce.

## Open Items

- **R4 fix** — `cg_topology.py` rule needs a real detection signal (likely `componentGuid` matching or a name-set check against actual GH parameter component display names, not a string prefix). Separate plan, after 35-15.
- **Wave 4 (35-13)** — eval harness driver (cassette record/replay, arms A0–A5, pytest SC1 gate). Ready to run: dependencies (35-11, 35-12) closed, autonomous.
- **Wave 5 (35-15)** — ablation sweep, SC1 measurement, UAT closeout. Depends on 35-13 + 35-14 (both now satisfied once 35-13 ships). Non-autonomous.
- Corpus A re-grounding on the recovered Frame/Truss source — explicitly declined this session; would need its own plan if revisited.

## Files Modified

Commits: e189fac, 2de50f0, 5e5ccf7, c5dac11, 60090c2 (35-12); f66a21b, c15c328 (UAT + decisions); 22cecc6, 4253be0 (35-14).

SUMMARY.md files: 35-12, 35-14 (both created).

Artifacts frozen:
- `data-service/fixtures/recognition_eval/urbanblock_slice.context.json`
- `data-service/fixtures/recognition_eval/urbanblock_slice.expected.json`

`.gitignore`: added `*.gh` / `*.3dm`.

## Related Sessions / Decisions

- [[sessions/2026-07-26 Phase 35 Wave 2 execution — Tier 0 topology, Corpus A, parser fix|2026-07-26: Wave 2 execution]]
- [[decisions/Phase 35 Corpus A frozen as-is, Frame Truss binaries not committed|Decision: Corpus A as-is, binaries untracked]]
- [[debugging/Phase 35 R4 interface rule unreachable on live Grasshopper data|Debugging: R4 unreachable on live data]]
