---
tags: [debugging, v9.0, phase-35, phase-32, parser, latent]
date: 2026-07-26
severity: medium
status: found — fix planned as 35-16, not yet applied
---

# Phase 35 latent parser bug — pattern host resolved by document order

**Found:** 2026-07-26, while executing plan 35-05 (filling the Frame fixture's `_Proc` groups).
**Not** a UAT finding — never observed in production, because no real canvas has been
published through this path yet. Caught by reasoning about the fixture edit before making it.

## Symptom (what would happen)

A nested Pattern silently loses its host: `hostPatternId` comes back `null`, so
`PATTERN_HOST_TO` never reaches Neo4j and the published Computgraph is **flatter than the
canvas the architect drew**. No warning, no error — the publish succeeds and the graph is
simply wrong.

## Root cause

`CanvasAnnotationParser.ComputeHostPatternIds` (`DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs:429`):

    var hostGroup = allGroups.FirstOrDefault(g => g.NestedGroupIds.Contains(pending.Group.Nickname));
    if (hostGroup is not null && idByGroup.TryGetValue(hostGroup, out var primaryHostId))
    { hostId = primaryHostId; }
    else if (pending.Group.MemberIds.Count > 0) { /* strict-superset fallback */ }

Three facts combine:

1. `FirstOrDefault` searches **all** groups in `RawCanvas.Groups` order, with no filter on
   whether the candidate is itself a pattern.
2. `idByGroup` only contains **pending patterns**, so a non-pattern hit fails the lookup.
3. Grasshopper group containment is **transitive** — `CanvasContextExtractor` computes
   `NestedGroupIds` from real containment, so a Procedure group legitimately lists every
   pattern inside it, including ones nested a level deeper inside another pattern.

So when a Procedure group appears earlier in `groups[]` than the true parent pattern:
`FirstOrDefault` returns the Procedure → `idByGroup.TryGetValue` misses → the `if` is false →
control falls to the `else if` strict-superset fallback → the parent pattern's `MemberIds`
are not a superset of the child's (they own different components) → no candidate →
`hostId` stays `null`. **The nesting is dropped with no diagnostic.**

The outcome therefore depends on the order groups happen to appear in the document — which
is not a property anyone reasoning about the parser would expect to matter.

## How it surfaced

Plan 35-05 required filling the two `_Proc` groups' `memberIds`/`nestedGroupIds`, which had
been empty (the UAT F2 trigger). The obvious edit — list every `11_*` entity group under
`11_Proc`, including `11_Pat_TopChord` — would have put the Proc group (array position 0)
ahead of `11_Pat_DivideLine` (position 2) for the `FirstOrDefault`, breaking the nesting the
Phase 32 acceptance test asserts.

## Workaround applied (35-05)

The fixture lists **direct children only**: `11_Pat_TopChord` is nested inside
`11_Pat_DivideLine`, so it is not named under `11_Proc`. This is consistent with the method's
own XML doc, which says *"each pattern group's **immediate** host id"* — so the fixture is
correct as written and the Phase 32 nesting assertion
(`Assert.Equal(divideLine.Id, topChord.HostPatternId)`) still passes.

The workaround holds for the fixture. It does **not** hold for a real canvas, where the
extractor emits transitive containment and the author has no control over group ordering.

## Planned fix — [[.planning/phases/35-llm-recognition-canvas-preview/35-16-PLAN.md|plan 35-16]]

Search only groups that are themselves pending patterns, and among those pick the
**innermost** by ascending `MemberIds.Count` (the smallest enclosing pattern is the immediate
one). This makes resolution depend on nesting structure rather than array position, and
removes the now-redundant `idByGroup` guard on the primary path. The strict-superset
`MemberIds` fallback stays for the case where no group names the child at all.

Order-independence is asserted directly: the plan requires a test that parses ≥ 4
permutations of the same `Groups` list and asserts identical host assignments — a fix
validated only against a reordered fixture would pass a weaker test for the wrong reason.

## Why it is medium and not high

- Not reachable today: the only canvas published so far is the Frame fixture, which lists
  direct children only.
- Fails toward flatness, not corruption — no wrong parent is assigned, the parent is simply
  missing.
- But it is **silent**, it persists into Neo4j, and it would be discovered (if ever) as
  "the published graph doesn't match my canvas" long after the fact — the same
  three-phases-away signature as [[Phase 35-36 dataType inference gap breaks publish (F5)|F5]].

## Related

- [[Phase 35 F4 — Re-preview undo crash]] — the other Phase 35 canvas-layer defect, fixed 2026-07-26
- [[Phase 35-36 dataType inference gap breaks publish (F5)]] — same "detonates phases later" shape
- Consumers of `hostPatternId`: `ComputgraphContextSerializer` → `computgraph_publish.py` → `PATTERN_HOST_TO`
