---
name: Phase-35-R4-interface-rule-unreachable-on-live-data
tags: [phase-35, debugging, tier-0, cg_topology, r4, interface, corpus-b, live-canvas]
date: 2026-07-26
links: [sessions/2026-07-26 Phase 35 Wave 3 execution — two-tier orchestrator, Corpus B frozen, R4 defect found]
---

# Phase 35: R4 (Interface Classification) Is Unreachable on Live Grasshopper Data

## Symptom

While hand-annotating the UrbanBlock_V7 slice for Corpus B (plan 35-14), the composition checklist required at least one genuine bare pass-through `Param` component left untagged — a false-positive probe for Tier-0 rule R4, which classifies bare single-in/single-out relays as `Interface`. The architect added two real components to the canvas for this purpose (`Geometry`/nickname `Geo`, `Integer`/nickname `Int`, both in_degree=1/out_degree=1, placed outside all `Proc` groups). A scan of the full 102-node canvas found **zero** components whose Grasshopper display name starts with `Param`.

## Root Cause

Tier-0 rule R4, `data-service/cg_topology.py` (~L383-393):

```python
elif (f.in_degree == 1 and f.out_degree == 1
      and f.widget_kind == "None"
      and f.name.startswith("Param")):
    row = _decide_row("IntF", f)
```

`f.name` is populated from the C# extractor's `Name` field, `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs:109`:

```csharp
Name = obj.Name ?? string.Empty,
```

This is the Grasshopper component's **display name** — what appears on the canvas node. Real Grasshopper parameter/relay components display as `Geometry`, `Integer`, `Number`, `Curve`, `Boolean`, etc. **None of them display as `Param...`.** The rule's condition can never be satisfied by a real canvas node.

The only test exercising R4, `test_r4_pass_bare_param_relay_decides_intf()` (`data-service/tests/test_cg_topology.py:422`), feeds a synthetic node with `name="Param"` — a name that cannot occur in production. The test is green, and always will be, regardless of whether R4 works on real data.

## Why This Wasn't Caught Earlier

Corpus A (`frame_ablated`) never exercises R4 either — it has zero bare pass-through relays in its composition, because it was mechanically emitted from a fixture, not hand-composed against a checklist. FM-2 in Corpus B's composition requirements exists precisely to force this case into being — and it did: building the corpus surfaced the defect before any eval run needed to.

## Fix (Not Applied This Session)

**Deliberately deferred.** The freeze protocol for Corpus B forbids the reference/context commit from touching `cg_topology.py` in the same commit — doing so would invalidate the SC1 measurement 35-15 is about to produce (the whole point of freezing is that the rules under test predate the eval). The fix belongs in a follow-up plan, to run **after** 35-15's ablation sweep completes.

Likely fix shape: R4 needs a real detection signal instead of a name-prefix string match. Candidates:
- Match against `componentGuid` for the actual GH parameter/relay component GUIDs (mirroring how `widget_kind()` already does exact `componentGuid`/name matching for other classifications, per its own docstring claiming C#-`ClassifyNodeKind` parity).
- Match against the real set of Grasshopper parameter component display names (`Geometry`, `Number`, `Integer`, `Text`, `Curve`, `Brep`, `Point`, `Vector`, `Plane`, etc. — see `_GEOMETRY_PARAM_NAMES` in the same file, which already enumerates a similar set for a different purpose and could plausibly be reused or extended).

Whichever approach is chosen, update `test_r4_pass_bare_param_relay_decides_intf()` to feed a name that can actually occur on a live canvas, so a regression can't hide behind the same fictitious fixture again.

## Related

- [[sessions/2026-07-26 Phase 35 Wave 3 execution — two-tier orchestrator, Corpus B frozen, R4 defect found|Session: Wave 3 execution — full corpus-building narrative]]
- [[decisions/Phase 35 Corpus A frozen as-is, Frame Truss binaries not committed|Decision: Corpus A not re-grounded]]
