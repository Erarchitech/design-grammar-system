---
phase: 1202-design-state-replay-and-per-object-verdict-closure
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - DG/src/DG.Core/Data/IValidGraphRepository.cs
  - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
  - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
  - DG/src/DG.Core/Services/ObjStateGuard.cs
  - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
  - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
  - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs
  - DG/tests/DG.Tests/ObjStateModelTests.cs
  - spec/EVIDENCE-CONTRACT.md
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 1202: Code Review Report (round 2 — gap-closure re-review)

**Reviewed:** 2026-09-22
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found (no Critical; 1 Warning, 2 Info)

## Summary

This is a targeted re-review of plans 1202-10 and 1202-11, which were written to close CR-01 and
CR-02 from the round-1 review (preserved in git history at commit `6b256aa`). Both findings were
verified against the actual code on disk, not assumed resolved from summaries.

**CR-01 (duplicate `(ruleId, objectId)` row collapse in `BuildPerObjectVerdicts`) — genuinely
resolved.** `Neo4jValidGraphRepository.BuildPerObjectVerdicts` (`Neo4jValidGraphRepository.cs:252-317`)
now materializes `envelope.Rows` once and performs two passes over the *same* row list: a
`(RuleId, ObjectId)`-ordinal grouping to detect any pair appearing on more than one row
(`collidingPairs`, `:276-282`), and the pre-existing `ObjectId`-only grouping for the
`StatusRollup.Rollup` cross-rule precedence (`:292-302`), now additionally flagging
`HasDuplicateRuleObjectRows` per object. The distinction between the intended cross-rule rollup case
and the duplicate-identity case is correctly implemented and is well covered by
`Neo4jValidGraphRepositoryTests.cs:485-602` (distinct-object happy path, cross-rule precedence case,
duplicate-pair detection-and-rollup case, and the "must not throw or degrade" case). `spec/EVIDENCE-CONTRACT.md`
§5.1 (`:245-259`) documents the same contract consistently with the code. This closes cleanly.

**CR-02 (ObjectStateComponent silently minting degraded ObjStates on Object/Geometry list-length
mismatch) — genuinely resolved.** The new `ObjStateGuard.IsObjectListLengthMismatch` (`ObjStateGuard.cs:41-44`)
is a pure, SDK-independent predicate correctly encoding the three exempt cases (no Object wired,
single-item broadcast, matched per-instance) and flagging both under-supply and over-supply as
mismatches. `ObjectStateComponent.SolveInstance` (`ObjectStateComponent.cs:111-119`) calls this
shared predicate (not a re-expressed inline condition) before the per-item loop and emits a
dedicated, correctly-worded error template (`ErrorMessageTemplates.ObjStateMismatchedObjectListLength`,
`ErrorMessageTemplates.cs:66-70`) that names "Object" rather than reusing the pre-existing
Label-mismatch template — avoiding the misleading-message trap the plan's own design_decision called
out. Guard logic is exhaustively tested in both `ErrorMessageTemplateTests.cs:405-419` and
`ObjStateModelTests.cs:77-91` against identical `(geometryCount, objectCount)` shapes. This closes
cleanly.

No new Critical or otherwise blocking defects were introduced by either fix. One Warning-level
documentation-drift issue and two Info-level observations are noted below.

## Warnings

### WR-01: `PerObjectVerdictResult.CollidingRuleObjectPairs` doc comment implies row-order alignment with §4 that doesn't hold

**File:** `DG/src/DG.Core/Data/IValidGraphRepository.cs:92-93`
**Issue:** The doc comment states `CollidingRuleObjectPairs` is "Ordered deterministically —
ordinal by `RuleObjectPair.RuleId` then `RuleObjectPair.ObjectId`" and the implementation
(`Neo4jValidGraphRepository.cs:280-282`) matches that claim internally — so the code and its own
doc comment agree. However, `spec/EVIDENCE-CONTRACT.md` §4 (`:183-186`) defines the *envelope's*
normative row order as "lexicographically ascending by `objectId`, ties broken lexicographically by
`ruleId`" — the opposite key precedence from `CollidingRuleObjectPairs`'s `RuleId`-then-`ObjectId`
order. Neither document calls out this inversion explicitly; a future reader skimming both files
side-by-side (as the doc comments elsewhere in this same PR explicitly try to help with, e.g. the
CR-01 write-up in `Neo4jValidGraphRepository.cs:224-251`) could reasonably assume
`CollidingRuleObjectPairs` mirrors the envelope's own `rows` ordering and be surprised when a test
or downstream consumer sorts by the wrong key first. This is not a functional bug (`CollidingRuleObjectPairs`
is a distinct, newly-introduced collection with its own stated order, and every test in
`Neo4jValidGraphRepositoryTests.cs` that touches it only has a single colliding pair, so the ordering
claim is never actually exercised with 2+ pairs), but it's a latent documentation trap for the next
person to extend duplicate-pair reporting to a multi-collision scenario.
**Fix:** Add one sentence to either `IValidGraphRepository.cs:92-93` or `spec/EVIDENCE-CONTRACT.md`
§5.1 noting the deliberate key-order inversion relative to §4's `rows` ordering (RuleId-first here
vs. ObjectId-first there), and add a regression test with 2+ distinct colliding pairs asserting the
actual sort order to lock it in:
```csharp
[Fact]
public void BuildPerObjectVerdicts_WithMultipleCollidingPairs_OrdersByRuleIdThenObjectId()
{
    var envelopeJson = BuildEnvelopeJson(
        ("R_B", "OBJ1", EvidenceStatus.Failed), ("R_B", "OBJ1", EvidenceStatus.Error),
        ("R_A", "OBJ2", EvidenceStatus.Failed), ("R_A", "OBJ2", EvidenceStatus.Error));

    var result = Neo4jValidGraphRepository.BuildPerObjectVerdicts(envelopeJson);

    Assert.Equal(2, result.CollidingRuleObjectPairs.Count);
    Assert.Equal("R_A", result.CollidingRuleObjectPairs[0].RuleId); // R_A sorts before R_B
    Assert.Equal("R_B", result.CollidingRuleObjectPairs[1].RuleId);
}
```

## Info

### IN-01: `GetPerObjectVerdictsAsync` / `BuildPerObjectVerdicts` have no wired caller yet

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:180-216`
**Issue:** A repo-wide search confirms `GetPerObjectVerdictsAsync` and `BuildPerObjectVerdicts` are
referenced only from `IValidGraphRepository.cs`, `Neo4jValidGraphRepository.cs` itself, and the two
test files reviewed here — no Grasshopper component (e.g. a VALIDATION GRAPH or OBJECT DECONSTRUCT
consumer) calls the new per-object verdict path yet. This is very likely intentional and out of
this gap-closure round's scope (1202-10/1202-11 closed the repository-layer detection gap, not UI
wiring), but flagging it for completeness since an unconsumed public API is otherwise a code-quality
smell in isolation.
**Fix:** No action needed if UI wiring is tracked in a later phase/plan; otherwise cross-reference
the tracking plan in the doc comment at `IValidGraphRepository.cs:113-129` so a future reader knows
this is deliberately staged rather than forgotten.

### IN-02: Empty/default `ruleId`/`objectId` on a malformed evidence row is silently treated as a valid identity component

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:276-302`
**Issue:** `EvidenceRow.RuleId`/`EvidenceRow.ObjectId` default to `string.Empty` (never null) per
`EvidenceEnvelope.cs:18,21`. If a producer emits a row missing the `ruleId` or `objectId` JSON key
(a contract violation independent of the duplicate-pair one this plan addresses), `System.Text.Json`
silently leaves the property at `""`, and `BuildPerObjectVerdicts` will happily group it as a
legitimate `("", "")`-or-partial identity, potentially reporting a spurious collision between two
otherwise-unrelated malformed rows, or rolling an empty-ObjectId "object" into `Verdicts` with an
empty `ObjectId` — a verdict a caller has no sensible way to display. This is pre-existing behavior
of the JSON deserialization convention used throughout this file (not introduced by 1202-10) and is
a low-likelihood scenario given `EvidenceEnvelopeFactory` (the only current producer) always
populates both fields, so it is Info rather than Warning.
**Fix:** Optional hardening — filter or flag rows where `RuleId`/`ObjectId` is empty before the
grouping passes, e.g.:
```csharp
var rows = envelope.Rows
    .Where(r => !string.IsNullOrEmpty(r.RuleId) && !string.IsNullOrEmpty(r.ObjectId))
    .ToList();
```
Not required for this gap-closure round; worth a follow-up ticket if a second envelope producer is
ever added.

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
