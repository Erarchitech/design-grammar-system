---
phase: 1202-design-state-replay-and-per-object-verdict-closure
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - DG/src/DG.Core/Data/IValidGraphRepository.cs
  - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
  - DG/src/DG.Core/Serialization/DesignStateCanonicalProjection.cs
  - DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs
  - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
  - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
  - DG/tests/DG.Tests/DesignStateCanonicalProjectionTests.cs
  - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs
  - DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs
  - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs
  - DG/tools/DG.De01Harness/Program.cs
  - data-service/app.py
  - data-service/design_state_projection.py
  - data-service/evidence_contract.py
  - data-service/tests/test_design_state_projection.py
  - data-service/tests/test_designstate_capture.py
  - data-service/tests/test_validation_entity_rollup.py
  - data-service/tests/test_validation_run_immutability.py
  - fixtures/golden/replay/README.md
  - fixtures/golden/replay/mixed-verdicts.json
  - fixtures/golden/replay/seed-replay.cypher
  - spec/DATABASE.md
  - spec/EVIDENCE-CONTRACT.md
  - tools/de01/legs.py
  - tools/de01/report.py
  - tools/de01/report_schema.json
  - tools/de01/run_de01.py
  - tools/de01/tests/test_de01_runner.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 1202: Code Review Report

**Reviewed:** 2026-09-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

This phase closes the D-01/D-08/D-10/D-12/D-13 loop for canonical per-object verdicts and the
canonical DesignState state hash, across a C# repository/harness leg, a Python data-service leg,
and the DE-01 cross-service comparison tool. The code is heavily and honestly self-documented
about known parity gaps (the two `parameters[]` wire shapes, the `classIri` divergence, the
float→decimal scale collapse), and most of those gaps are pinned by regression tests rather than
silently accepted. That discipline is real and worth crediting.

However, two areas fall short of what the code's own stated contract promises:

1. `GetPerObjectVerdictsAsync`/`BuildPerObjectVerdicts` silently **drops duplicate-(ruleId,
   objectId) evidence rows** during rollup grouping, which contradicts `spec/EVIDENCE-CONTRACT.md`
   §4's explicit identity rule ("never merged, collided, or deduplicated on value equality alone")
   as applied within a single object's row set — see CR-01 below.
2. `ObjectStateComponent.SolveInstance` has an **unvalidated list-length mismatch** between
   `Object` and `Geometry` inputs that silently degrades identity resolution for the unmatched
   tail, in a component whose entire job is producing a stable per-object identity.

Both are BLOCKER-class because they produce a *wrong, silently-accepted* verdict/identity rather
than a typed absence or a loud failure — the exact failure mode this phase's own design
philosophy (`D-11`, "typed absence never fabrication") exists to prevent elsewhere.

## Critical Issues

### CR-01: `BuildPerObjectVerdicts` silently drops the identity distinction between rows with the same `(ruleId, objectId)` pair when rolling up per-object status, contradicting the envelope's own row-identity rule

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:226-260`

**Issue:** `BuildPerObjectVerdicts` groups `envelope.Rows` by `ObjectId` alone (`GroupBy(row =>
row.ObjectId, ...)`) and rolls every row in the group up through `StatusRollup.Rollup`. This is
correct and intended for the *cross-rule* rollup case (D-12: one object, several rules, worst
status wins) — the DE-01 fixture and tests exercise exactly that shape.

But `spec/EVIDENCE-CONTRACT.md` §4 states rows are identity-addressed by the **`(ruleId,
objectId)` pair**, and are "never merged, collided, or deduplicated on value equality alone." A
malformed or buggy upstream producer that emits **two rows for the same `(ruleId, objectId)`
pair** (e.g. a retried evaluation, or the C# harness's own "multiple rows per pair" case
documented in `tools/de01/report.py:119-121` for the ObjectPropertyAtom synthesized row) is
silently folded into a single rolled-up verdict here with no way for a caller to detect that two
rows collided on identity. `tools/de01/report.py`'s `compare_legs` explicitly keeps *all* rows per
pair (`_rows_by_pair`, never deduplicates) specifically to avoid this — the C# repository path
does not have the equivalent safeguard, so the same envelope produces a loud "every row visible"
comparison on the Python side and a silent collapse on the C# `GetPerObjectVerdictsAsync` side for
the same underlying data.

Concretely: if `evidenceEnvelopeJson` ever contains two rows `(R1, OBJ1, failed)` and `(R1, OBJ1,
error)` (same rule, same object, genuinely duplicate identity — a producer bug per the contract),
`BuildPerObjectVerdicts` reports `OBJ1 -> error` with no warning and no way to tell a caller "this
object's evidence contained a duplicate/conflicting row for the same rule," which is exactly the
kind of producer bug D-12's own test suite (`test_validation_entity_rollup.py`) was built to
surface on the Python leg, but there is no equivalent visibility on the canonical C# read path
consumed by the Grasshopper canvas.

**Fix:** Either (a) treat the `(ruleId, objectId)` identity as load-bearing before grouping by
`ObjectId` for rollup — group by `(RuleId, ObjectId)` first, detect any group with count > 1, and
surface that as a distinguishable condition (a warning or a new `VerdictSource` value) rather than
silently letting `StatusRollup.Rollup` swallow it — or (b) explicitly document, next to
`BuildPerObjectVerdicts`, that the per-object rollup deliberately treats within-object row
identity as immaterial (the current doc-comment only explains the cross-rule case, not the
duplicate-identity case), so a future reader does not mistake this for the §4 guarantee holding at
this boundary too.

```csharp
// Illustrative: detect (not silently swallow) same-(rule,object) duplicates before rollup
var duplicateKeys = envelope.Rows
    .GroupBy(row => (row.RuleId, row.ObjectId))
    .Where(g => g.Count() > 1)
    .Select(g => g.Key)
    .ToList();
// surface duplicateKeys via a warning/log or a new PerObjectVerdict flag rather than
// discarding the information inside StatusRollup.Rollup's HashSet<EvidenceStatus>.
```

### CR-02: `ObjectStateComponent.SolveInstance` never validates `Object` list length against `Geometry` list length, silently degrading ObjectRef/ClassIri resolution for the unmatched tail

**File:** `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:87-131`

**Issue:** The component validates `Label` count against `Geometry` count (lines 90-98) and errors
out on mismatch, but performs **no equivalent check for `Object` vs `Geometry`** when more than
one `Object` is wired (the non-broadcast, per-instance identity path). Per-instance resolution is:

```csharp
var perItemObject = i < objects.Count ? objects[i] : null;
```

If a user wires, say, 5 geometry items but only 3 per-instance `Object` references (a plausible
Grasshopper mistake — grafting/flattening mismatches are common), items 4 and 5 silently get
`perItemObject = null`, which means:
- `ResolveInstanceRef(null)` returns `null`
- `classIri` falls through to `null` (no `ResolveClassIri` call for those items, since
  `broadcastClassIri` is also null when `objects.Count != 1`)
- `ObjectRef` falls back to `GeometryReferenceId` or `$"obj_{i}"`

The net effect: the last two ObjStates in the output silently get a **different identity
resolution path** than the first three, with `ClassIri = null` regardless of what the user
intended, and no `AddRuntimeMessage` warning at all. This is the exact component whose class
doc-comment states "Each ObjState gets a UNIQUE ObjectRef" and "the ontology class IRI is
extracted" — a length mismatch here produces IDs (via
`DesignStateIdGenerator.ComputeObjectStateIdFromRef`) that will look plausible (16 hex chars,
`OS_`-prefixed) but are missing information the user actually supplied and expected, with zero
diagnostic signal on the canvas. This is worse than the `Label` mismatch case, which is treated as
an outright error (lines 90-98) — the identical shape of bug (list-length mismatch on a
per-instance broadcast component) is fatal for `Label` and silent for `Object`.

**Fix:** Apply the same guard already used for `Label`:

```csharp
var objCount = objects.Count;
if (objCount != 0 && objCount != 1 && objCount != geoCount)
{
    AddRuntimeMessage(
        GH_RuntimeMessageLevel.Error,
        ErrorMessageTemplates.ObjStateMismatchedListLengths(geoCount, objCount)); // or a dedicated template
    da.SetData(0, null);
    return;
}
```
(`objCount == 1` is the deliberate broadcast case and must remain exempt; `objCount == 0` is the
documented "no Object wired" case.)

## Warnings

### WR-01: `Neo4jValidGraphRepository.TryParseDesignState`'s v2-sniff branch silently mis-parses the serializer's own `parameters[]` shape as a documented but consequential divergence with no runtime signal

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:279-361`

**Issue:** This is a *documented* divergence (D-09/ALGN12-09, with two named pinning regression
tests), so it is not a hidden defect — but it remains a real, live production code path: the
inline reader silently returns `NumberValue == null` etc. for a real, currently-shipping wire
shape (the serializer's own `{type, value}` form, e.g. every payload the DE-01 replay fixture
carries). A caller of `GetRunsAsync` who receives a `DesignState` back has **no signal** that a
`ParamState`'s parameters silently came back empty-valued rather than absent — `TryParseDesignState`
returns a non-null `DesignState` either way, and the caller cannot distinguish "this ParamState
genuinely has null-valued parameters" from "this reader doesn't understand this parameter's wire
shape." Given that `mixed-verdicts.json`'s own `statePayloadJson` (the DE-01 replay fixture, which
this very phase ships) is in the shape that mis-parses, any consumer of `GetRunsAsync`/canvas
rendering of that state's ParamState will silently show blank/null parameter values today.

**Fix:** At minimum, surface a `RuntimeMessageLevel.Warning`-equivalent signal (a log line, or a
flag on `DesignState`) when the inline reader detects a `parameters[]` entry with a `type` set but
every typed value (`numberValue`/`integerValue`/`booleanValue`) absent and a raw `value` key
present in the source JSON that it did not consume — that combination is the fingerprint of this
exact divergence and is mechanically detectable without waiting for the two readers to converge
(tracked as a future plan per the code comments).

### WR-02: `get_validation_entity_sets` re-derives `ROLLUP_PRECEDENCE`-based status entirely from a legacy `{"failed":[...], "passed":[...]}` two-bucket shape, discarding the richer canonical status before it ever reaches callers

**File:** `data-service/app.py:871-937`

**Issue:** The function computes the correct canonical rollup (`evidence_contract.CanonicalStatus`,
walking `ROLLUP_PRECEDENCE`) but then immediately collapses it to a boolean bucket via
`to_legacy_boolean` before returning. Every caller of `get_validation_entity_sets` (and therefore
every consumer of `build_view_payload`'s `objectSets`) only ever sees "passed" or "failed" — the
distinction between `error`, `no_population`, `unsupported`, and `not_evaluated` (all of which
D-05's situation table treats as meaningfully different, and which the C# leg's
`GetPerObjectVerdictsAsync` correctly preserves via `PerObjectVerdict.Status`) is computed here and
then thrown away. The function's own docstring (lines 883-887) correctly states this function is
"legacy/non-authoritative" and that `GetPerObjectVerdictsAsync` is canonical — but nothing prevents
a future UI consumer from reaching for the Python-side `objectSets` (which is exposed on
`/validation/view/...`) as a per-object status source, since it's the only per-object endpoint the
Python side exposes at all. This is a design smell rather than a functional bug in this phase, but
it means the phase's "canonical per-object verdict" work is asymmetric across the two languages:
C# consumers get the full 8-status vocabulary; Python/UI consumers reachable via this endpoint get
a lossy 2-bucket view with no equivalent of `GetPerObjectVerdictsAsync` on the Python side.

**Fix:** Consider exposing the pre-collapse `rolled_up` `CanonicalStatus` (not just the
`passed`/`failed` bucket) as an additional field per entity in the returned dict, so a UI consumer
that wants the real vocabulary does not have to reimplement the rollup a third time.

### WR-03: `capture_design_state`'s DSAV size cap is enforced only after JSON body parsing/Pydantic validation, so an oversized payload is fully deserialized before the 413 is raised

**File:** `data-service/app.py:2509-2565`

**Issue:** `DesignStateCaptureRequest` (a Pydantic model) parses `statePayloadJson` as a plain
`str` with no `max_length` constraint at the model level; FastAPI/Pydantic will happily
deserialize and hold an arbitrarily large string in memory (bounded only by the wider FastAPI
request body limit, if any) before `capture_design_state`'s own `len(...encode("utf-8")) >
DSAV_MAX_STATE_PAYLOAD_BYTES` check runs. The comment at line 147-153 frames `DSAV_MAX_STATE_PAYLOAD_BYTES`
as "the only thing standing between an authenticated connector and an arbitrarily large Neo4j
property," but as written it only protects Neo4j — an authenticated (but possibly compromised or
misbehaving) connector can still force the service to buffer and JSON-parse an unbounded string
per request before the rejection fires. This isn't request-smuggling/DoS-from-anonymous-traffic
(auth is required first), but it is a gap between the stated intent ("the only thing standing
between...") and what the code order actually guards.

**Fix:** Add `Field(min_length=1, max_length=DSAV_MAX_STATE_PAYLOAD_BYTES)` (or an equivalent
Pydantic validator) directly on `DesignStateCaptureRequest.statePayloadJson` so oversized bodies
are rejected during model validation rather than after a full parse, or explicitly document why
buffering isn't considered a risk here (e.g. a reverse-proxy body-size cap already exists).

### WR-04: `_auto_publish_run`'s `valid_status` parameter is silently unused and its docstring papers over the coupling to `dsav_watcher.poll_once`'s exact call signature with no compile-time or defensive runtime check

**File:** `data-service/app.py:2403-2506`

**Issue:** The function accepts `valid_status: list[bool] | None = None` purely so it satisfies
`dsav_watcher.poll_once`'s hardcoded two-positional-argument call
(`publish_fn(project, run_id)` — per the docstring, this is apparently *not even threading
`valid_status` through*, since the call site only ever passes two args). The only test
(`test_auto_publish_run_is_callable_with_the_watcher_publish_fn_contract`) checks the signature is
*bindable* with two args via `inspect.signature(...).bind(...)`, but nothing asserts the watcher's
actual call site still only passes two arguments — if `dsav_watcher.poll_once` is ever changed to
pass a third positional argument (or the `valid_status` kwarg) that doesn't match this function's
now-unused parameter, this reads as silently accepted (Python permits it) rather than caught. This
is a maintainability/coupling smell: two independent modules must stay in lock-step on an
unenforced calling convention, with the coupling documented only in prose.

**Fix:** Either have `dsav_watcher.poll_once` import and inspect
`app._auto_publish_run`'s signature directly (fail fast on drift), or remove the unused parameter
entirely if it truly carries no information the callee needs, replacing the current "accepted but
ignored" shape with `*args` plus an explicit assertion, so a signature drift fails loudly instead
of silently.

### WR-05: `store_validation_run`'s `entity_rows` `MERGE` block silently permits stale `ValidationEntity` rows to survive a re-publish that removes an entity's rule association entirely

**File:** `data-service/app.py:551-680`

**Issue:** `entity_rows` is built fresh from the current `entities` list and `MERGE`d in, but there
is no corresponding delete/reconciliation of `ValidationEntity` rows from a *previous* publish of
the same `runId` that are no longer present in the current `entities` list (e.g. an entity that
was `failed` on rule R1 in publish #1 but is not included in `ruleIds`/`failedRuleIds` at all on a
re-publish #2, perhaps because it was removed from the design). Because the D-15 immutability split
(this same phase) now explicitly allows re-publishing the *same* `runId` for mutable/publish-output
fields, this makes a stale `ValidationEntity` from an earlier publish of that same run silently
outlive its relevance — `get_validation_entity_sets` will keep reporting it as `failed`/`passed`
even though the current design state no longer has an opinion on it. This predates this phase but
this phase's own D-15 change (making re-publish of the same `runId` a supported, no-longer-clobbering
operation) makes the staleness window newly reachable in a way it wasn't when a re-publish
implicitly overwrote everything.

**Fix:** Either `DETACH DELETE` existing `ValidationEntity` rows for `(graph, project, runId)`
before writing the new `entity_rows` batch, or document explicitly (next to D-15's three-way
classification comment) that `ValidationEntity` rows are additive-only across re-publishes and
callers must not assume they reflect only the latest publish's entity set.

### WR-06: `TryParseDesignState`'s version-sniff logic silently treats a payload with an empty-but-present `objStates: []`/`paramStates: []`/`propStates: []` and no `version` key as v1, even though the structural shape (an empty 3-part composition) is far closer to v2

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:279-292`

**Issue:** The v2-sniff condition is:
```csharp
root.TryGetProperty("stateKind", out _) ||
root.TryGetProperty("objStates", out _) ||
root.ValueKind == JsonValueKind.Object &&
    root.EnumerateObject().Any(p => p.Name is "objStates" or "paramStates" or "propStates")
```
This correctly identifies a v2 shape when *any* of the three arrays is present as a key — but a
payload with **no** `version` key and **no** `objStates`/`paramStates`/`propStates` keys at all
(e.g. a hand-authored or partially-written v1-style payload missing its `parameters` array) falls
through to the v1 fallback (`DesignStateJsonSerializer.Deserialize`), which — per
`DesignStatePayloadV2SerializerTests`' own `Deserialize_WhenVersionIsMissing_ShouldThrow` test for
the *v2* reader — is a substantively different failure/success contract than the v2 path. This
isn't wrong per the current test suite (which only exercises the documented v1/v2/v3 cases), but
the boundary condition — an object with none of `version`, `stateKind`, `objStates`, `paramStates`,
`propStates` at all — has no explicit test and no explicit doc-comment statement of what should
happen (it currently falls to `DesignStateJsonSerializer.Deserialize`, which will likely throw or
return a mostly-empty `ParamState`, silently, inside the outer `catch (Exception)` that returns
`null`). Worth an explicit regression test given how much of this file's other logic is
test-pinned.

**Fix:** Add a regression test asserting the behavior of a payload with none of the sniffed keys
(e.g. `{"stateId":"X"}` alone), and a doc-comment sentence stating the intended fallback outcome.

## Info

### IN-01: `_format_prop_value`'s `int(num)` truncation for whole-number floats silently loses precision for values outside the float53-safe integer range

**File:** `data-service/app.py:718-744`

**Issue:** `num.is_integer()` followed by `str(int(num))` is used for display formatting of a
`number`-typed PropState value. For a float whose magnitude exceeds `2**53`, `is_integer()` can
still return `True` while the float itself has already lost precision relative to the original
value — this is a display-only path (not used for hashing/identity), so the impact is cosmetic,
but worth a comment given how carefully-argued the rest of this file's numeric-precision reasoning
is (`_compute_canonical_state_hash`'s long docstring on double/decimal scale collapse).

**Fix:** No functional change needed; consider a one-line comment noting this is display-only and
intentionally not held to the same precision discipline as the hashing path, to pre-empt a future
"why does this differ from `design_state_projection.py`'s handling" question.

### IN-02: `_auto_publish_run`'s Speckle-publish call passes `rules=[]` and `entities=[]` unconditionally, which is correct per the docstring but makes the function's name ("publish_run") misleading relative to what it actually publishes

**File:** `data-service/app.py:2427-2465`

**Issue:** Purely a naming/documentation observation: `_auto_publish_run` publishes a
"state-level marker" version with no rule/entity content by design (D-11), which is well explained
in the docstring, but a reader skimming call sites (`dsav_watcher.py`) without reading this
function's docstring could reasonably assume it publishes the same rich content the manual
`publish_validation` route does. No behavior change needed; consider renaming to something like
`_auto_publish_state_marker` in a future pass, or adding a one-line comment at the two call sites
in `dsav_watcher.py` cross-referencing the D-11 rationale.

### IN-03: `seed-replay.cypher` embeds a large inline JSON string literal (the full `statePayloadJson`) duplicated verbatim from `mixed-verdicts.json`, creating a manual-sync liability between the two files

**File:** `fixtures/golden/replay/seed-replay.cypher:201`

**Issue:** The Cypher seed script hardcodes the exact same `statePayloadJson` string that lives in
`mixed-verdicts.json`, with no automated check that the two stay byte-identical over time (the
README documents this is intentional/manual, and there's no CI enforcement mentioned). A future
edit to `mixed-verdicts.json`'s `statePayloadJson` (e.g. to fix the known `classIri` C#-parity gap
referenced in the README) will silently desynchronize from `seed-replay.cypher` unless a human
remembers to update both. Low severity since this is dev-only tooling, explicitly documented as
such, and not part of the production write path.

**Fix:** Consider a small script/test that reads both files and asserts the JSON strings match
byte-for-byte, catching drift mechanically rather than relying on review discipline alone (the
project's own stated preference elsewhere in this phase, e.g. `test_report_schema_canonical_status_matches_contract_schema`).

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
