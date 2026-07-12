---
phase: 823-shacl-validation-layer
reviewed: 2026-07-12T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - .github/copilot-instructions.md
  - CLAUDE.md
  - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
  - DG/src/DG.Core/Validation/ShaclReportPayload.cs
  - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
  - DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs
  - DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs
  - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
  - DG/tests/DG.Tests/ValidationPublishResponseShaclTests.cs
  - README.md
  - data-service/app.py
  - data-service/tests/test_shacl_proxy.py
  - dg-reasoner/app.py
  - dg-reasoner/reasoning.py
  - dg-reasoner/tests/fixtures/valid_graph_fixture.json
  - dg-reasoner/tests/test_routes.py
  - dg-reasoner/tests/test_shacl_report.py
  - dg-reasoner/tests/test_validgraph_export.py
  - dg-reasoner/valid_graph_export.py
  - ontology/dg-shapes.ttl
  - spec/DATABASE.md
  - spec/LPG-OWL-MAPPING.md
  - spec/RULE-PARTITION-POLICY.md
  - ui-v2/src/components/display/Badge.jsx
  - ui-v2/src/components/surfaces/Collapsible.jsx
  - ui-v2/src/screens/ModelScreen.jsx
  - ui-v2/src/styles/tokens/colors.css
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 823: Code Review Report

**Reviewed:** 2026-07-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Reviewed the full SHACL validation layer added across phase 823's six plans: the
ValidGraph→RDF ABox exporter and `owl:AllDifferent` derivation
(`dg-reasoner/valid_graph_export.py`), the version-controlled SHACL shapes
(`ontology/dg-shapes.ttl`) and pySHACL result-mapping pipeline
(`dg-reasoner/reasoning.py`), the non-fatal sidecar proxy and persistence wiring
in `data-service/app.py`, the rule-partition policy doc, the Grasshopper-side
`ShaclReportPayload`/`ErrorMessageTemplates`/`ValidatorComponent` surfacing, and
the ModelScreen "SHACL Data Integrity" panel + supporting design-system tokens.

The overall shape of the feature is sound and its "never fail the publish hot
path" contract is genuinely well-tested (data-service's proxy tests cover
connect-error/timeout/504/body-error-timeout/persist-failure paths). However,
one confirmed logic bug in the ValidGraph exporter will cause the new feature
to raise **false SHACL violations on valid, already-supported data** (a Run
whose DesignState has zero ObjStates), and a shipped SHACL shape can never
actually fire given what the exporter emits. There is also an unaddressed
timeout-budget mismatch between the data-service proxy and the sidecar's own
internal SHACL timeout, and a minor code-organization regression in
`ErrorMessageTemplates.cs`.

## Critical Issues

### CR-01: `valid_graph_export._mint_run_individual` uses a truthy check, not `is not None`, so an empty (but valid) `ValidStatus` list is misreported as a SHACL violation

**File:** `dg-reasoner/valid_graph_export.py:120-135`

**Issue:** `_mint_run_individual` handles `sendStatus` and `validStatus` inconsistently:

```python
send_status = row.get("sendStatus")
if send_status is not None:
    graph.add((run_iri, DGV.sendStatus, RDFLiteral(bool(send_status), datatype=XSD.boolean)))

valid_status = row.get("validStatus")
if valid_status:                      # <-- truthy check
    bool_literals = [RDFLiteral(bool(v), datatype=XSD.boolean) for v in valid_status]
    graph.add((run_iri, DGV.validStatus, make_argument_list(graph, bool_literals)))
```

`sendStatus` correctly uses `is not None` (so a legitimate `False` value still
gets a triple). `validStatus` uses a bare truthy check, so `[]` (empty list)
and `None`/absent are treated identically — **no `dgv:validStatus` triple is
emitted for either case.**

An empty `ValidStatus` list is not a data-integrity defect: `ValidatorComponent.cs`
(`DG/src/DG.Grasshopper/Components/ValidatorComponent.cs:87-98`) builds
`validStatus` by iterating `designState.ObjStates.Count`, and explicitly
supports zero ObjStates (e.g. a project-level or parameter-only rule with no
bound building instances) — this produces exactly `validStatus == []`, a
perfectly valid, already-shipped scenario, not an error.

Because `_mint_run_individual` treats `[]` the same as "missing", every such
Run trips `ontology/dg-shapes.ttl`'s `dgsh:RunStatusShape_valid`
(`sh:minCount 1` on `dgv:validStatus`, `sh:severity sh:Violation`, message "A
validation Run is missing its ValidStatus list") — a **false-positive
Violation** surfaced through the whole pipeline into the new "SHACL Data
Integrity" panel on the Model screen, for runs that did nothing wrong.

No test in `dg-reasoner/tests/test_validgraph_export.py` exercises
`validStatus: []` (the fixture only covers `[true, false]` and the
all-`None` "missing row" case), so this regression shipped without coverage.

**Fix:**
```python
valid_status = row.get("validStatus")
if valid_status is not None:
    bool_literals = [RDFLiteral(bool(v), datatype=XSD.boolean) for v in valid_status]
    graph.add((run_iri, DGV.validStatus, make_argument_list(graph, bool_literals)))
```
Add a regression test with `"validStatus": []` in the fixture/session asserting
the `dgv:validStatus` triple IS still emitted (as an empty `rdf:List`, i.e.
`RDF.nil`) and that `run_shacl` does not flag such a run under
`RunStatusShape_valid`.

## Warnings

### WR-01: SHACL sidecar HTTP timeout (15s) is much shorter than the sidecar's own internal SHACL timeout bound (90s), so slow-but-successful validations report as false "timeout"

**File:** `data-service/app.py:73-76, 1271-1316`; `dg-reasoner/reasoning.py:89, 510`; `dg-reasoner/app.py:86-96`

**Issue:** `data-service` waits at most `DG_SHACL_HTTP_TIMEOUT_SECONDS` (default
`15`) for the `dg-reasoner` sidecar's `POST /shacl/validate` to respond:

```python
DG_SHACL_HTTP_TIMEOUT_SECONDS = float(os.getenv("DG_SHACL_HTTP_TIMEOUT_SECONDS", "15"))
...
timeout=httpx.Timeout(connect=2.0, read=DG_SHACL_HTTP_TIMEOUT_SECONDS, write=2.0, pool=2.0)
```

But `reasoning.run_shacl()` bounds its own pySHACL subprocess with
`DG_REASONER_TIMEOUT_SECONDS` (default `90`, shared with the unrelated HermiT
consistency check) — six times longer:

```python
result = _run_shacl_with_timeout(data_graph, shapes_graph, DG_REASONER_TIMEOUT_SECONDS)
```

The `POST /reason/consistency` proxy explicitly accounts for this kind of
mismatch with a documented, deliberately larger read timeout ("read must
exceed the sidecar's own DG_REASONER_TIMEOUT_SECONDS ceiling ... with margin,
or the proxy returns false 504s" — `data-service/app.py:1209-1212`), but the
same reasoning was not applied to the new SHACL proxy. Any SHACL validation
that legitimately takes longer than 15s (subprocess spawn overhead for
`spawn`-context multiprocessing plus pyshacl/rdflib import + validate, which
grows with data/shape graph size) will make `httpx.post` raise
`TimeoutException` and report `{"status": "timeout"}` even though the sidecar
would have produced a valid, non-error result shortly after.

Compounding this: `dg-reasoner/app.py`'s `shacl_validate` route (unlike
`reason_consistency`) never converts an internal timeout into an HTTP 504 — it
returns the `run_shacl()` dict verbatim with a `200` status. This means when
data-service's 15s read timeout fires first, the sidecar's request handler is
still running server-side (blocked inside `process.join(90)`) for up to 90
more seconds after the caller has already given up and moved on — an orphaned,
uncancellable unit of work per abandoned request.

No test (`data-service/tests/test_shacl_proxy.py`,
`dg-reasoner/tests/test_shacl_report.py`) covers a "slow but eventually
successful" SHACL run to catch this budget mismatch.

**Fix:** Either raise `DG_SHACL_HTTP_TIMEOUT_SECONDS`'s default to exceed
`DG_REASONER_TIMEOUT_SECONDS` with margin (mirroring the `/reason/consistency`
proxy's pattern), or introduce a dedicated, smaller internal SHACL subprocess
timeout in `run_shacl()` (SHACL/pySHACL has no JVM startup cost, so it
plausibly deserves its own, shorter ceiling than HermiT) and keep the two
budgets in a documented, enforced relationship.

### WR-02: `ontology/dg-shapes.ttl`'s `ObjStateObjectRefShape` can never fire — it duplicates shape #1's predicate instead of validating a distinct `objectRef` field

**File:** `ontology/dg-shapes.ttl:109-122`; `dg-reasoner/valid_graph_export.py:81-92`

**Issue:** Section 4 is commented "ObjState objectRef non-empty," but the shape
constrains `rdfs:label`, the exact same predicate already covered by shape #1
(`dgsh:DsKindLabelShape`, `sh:minCount 1` on `rdfs:label` for `ObjState` among
other kinds):

```turtle
dgsh:ObjStateObjectRefShape_label
    sh:path rdfs:label ;
    sh:minLength 1 ;
    sh:severity sh:Violation ;
    sh:message "An object state has an empty object reference." ;
```

`valid_graph_export.py` never emits a distinct `dgv:objectRef` RDF predicate —
`_state_label()` folds `label`/`objectRef`/`stateId` into a single display
string, and `_mint_state_individuals` only adds the `rdfs:label` triple `if
label:` (skips it entirely when the resolved string is empty). Given that:

- If the label is genuinely absent, `sh:minCount 1` (shape #1) already flags
  it; `sh:minLength` has zero value-nodes to evaluate for an absent property
  and does not fire independently.
- If the label is present, it is by construction always a non-empty string
  (the exporter never emits an empty-string `rdfs:label` literal), so
  `sh:minLength 1` can never be violated either.

The shape is therefore dead code that can never produce a finding in the real
pipeline, under a name/comment that promises a check ("objectRef non-empty")
that isn't actually implemented anywhere.

**Fix:** Either emit a real `dgv:objectRef` predicate from
`_mint_state_individuals` for `ObjState` (`state.get("objectRef")`) and point
this shape's `sh:path` at it, or remove the shape and rely on shape #1 alone,
updating the section comment to stop promising a check that doesn't exist.

### WR-03: `ErrorMessageTemplates.cs` — SHACL method insertion splits and mislabels two pre-existing, related formatter methods

**File:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs:164-188`

**Issue:** Commit `a1c86ba` (823-05) inserted the new `--- SHACL templates
(Phase 823, D-15) ---` section header and `ShaclViolation` directly between
the pre-existing `FormatStatus` and `FormatMessage` methods (both formatters
over `ReinstatementResult`, previously adjacent since phase 19). The result:

```csharp
    // --- SHACL templates (Phase 823, D-15) ---

    public static string ShaclViolation(string severity, string what, string where, string howToFix) { ... }

    public static string FormatMessage(ReinstatementResult result) { ... }   // unrelated to SHACL, now sits under the SHACL header
}
```

`FormatMessage` has nothing to do with SHACL but now visually reads as part of
the SHACL section, and the two near-duplicate `ReinstatementResult` formatters
(`FormatStatus`/`FormatMessage`) that used to sit together are now separated
by an unrelated method. This is a maintainability regression introduced by
this phase's diff, not a functional bug.

**Fix:** Move `ShaclViolation` (and its section header) to the end of the
file, after `FormatMessage`, so the pre-existing `FormatStatus`/`FormatMessage`
pair stays adjacent and the SHACL section header only precedes SHACL-related
methods.

### WR-04: `data-service/app.py`'s `/create_node/` endpoint builds Cypher via unsanitized label interpolation (pre-existing, out of phase-823 scope, but present in the reviewed file)

**File:** `data-service/app.py:901-905`

**Issue:** Not part of phase 823's diff (confirmed via `git log`/`git blame` —
this endpoint predates the SHACL work), but it lives in a file this review's
scope includes in full, and is a live Cypher/label-injection vector worth
tracking separately:

```python
@app.post("/create_node/")
def create_node(label: str, name: str):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{label: $name}})", name=name)
    return {"status": f"Node {name} with label {label} created"}
```

`label` is interpolated directly into the Cypher string with no allow-list or
escaping; Cypher does not support parameterizing labels, but an allow-list
check (or removing this apparently-unused debug endpoint) is standard
practice here. Flagging for awareness/backlog — do not conflate with phase 823
scope when triaging.

**Fix:** Validate `label` against an allow-list of known node labels before
interpolating, or delete the endpoint if it is unused debug scaffolding.

## Info

### IN-01: `ErrorMessageTemplates.ShaclViolation` produces a stray leading space when `severity` is empty

**File:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs:166-170`; `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs:139-140`

**Issue:** `ValidatorComponent` calls `ShaclViolation(finding.Severity ?? string.Empty, ...)`. If a malformed sidecar response yields an empty `Severity`, the formatted line reads `"SHACL : {what} at {where}. ..."` — an orphan space before the colon. Low-impact (requires a malformed upstream payload dg-reasoner's own enrichment always defaults to `"violation"`), but worth a `string.IsNullOrWhiteSpace` fallback to `"finding"` or similar for defense in depth.

**Fix:** `var sev = string.IsNullOrWhiteSpace(severity) ? "finding" : severity;` before building the message.

### IN-02: SHACL severity mapping in `ValidatorComponent` silently downgrades any future/unrecognized severity to `Remark`

**File:** `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs:143-149`

**Issue:** The switch's `_ => GH_RuntimeMessageLevel.Remark` default is intentional today (matches the three known severities), but if `dg-reasoner` ever introduces a new severity string, it will silently blend into `Remark` with no signal that an unrecognized value was seen. Not a bug given the current closed severity set (`violation`/`warning`/`info`), but worth a code comment or debug-only assert if the severity vocabulary is expected to grow.

**Fix:** Optional — no action required unless the SHACL severity vocabulary is extended.

### IN-03: `FormatStatus`/`FormatMessage` remain near-duplicate helpers (pre-existing, adjacent to the new SHACL section)

**File:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs:145-188`

**Issue:** `FormatStatus` and `FormatMessage` implement almost identical branch logic over `ReinstatementResult` (Applied/Aborted/Unchanged/Idle) with only cosmetic differences in the returned strings. Pre-existing (phase 19), not introduced by 823, but since the file was touched in this phase it's a low-cost opportunity to consolidate.

**Fix:** Optional consolidation — out of scope for this phase's review but worth a backlog note.

---

_Reviewed: 2026-07-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
