---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 01
type: preflight-record
created: 2026-09-22
---

# Phase 1203 — Preflight Baseline

> Read-and-record only. Every number below was produced by a command run in this
> session on 2026-09-22, never copied from CONTEXT.md, RESEARCH.md, or 1202 artifacts.
> This closes the four "Wave 0 Requirements" open verification items in
> `1203-VALIDATION.md`.

---

## 1. Test suite baselines

### Python suite

Command: `python -m pytest data-service/tests -q`

Observed tail (verbatim):

```
4 failed, 819 passed, 1 skipped, 8 deselected, 25 errors in 33.47s
```

**Correction vs. VALIDATION.md:** `1202-CONTEXT.md` / `1203-VALIDATION.md` cite "823
passed / 1 skipped / 1 pre-existing-failed" as the prior baseline. The observed count
today is **819 passed, 4 failed, 25 errors** — materially different from the cited
"1 pre-existing-failed." This is recorded as an explicit correction, not silently
reconciled: the true current baseline plans 02/03 must diff against is **819 passed /
4 failed / 1 skipped / 8 deselected / 25 errors**, not the 1202-era number.

Failing tests (all 4, `FAILED`, not `ERROR`):

- `data-service/tests/test_dg_context.py::TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`
- `data-service/tests/test_dg_context.py::TestContextEndpoints::test_get_debug_matches_post_assemble_body`
- `data-service/tests/test_dg_context.py::TestDeterminism::test_repeated_assemble_calls_are_byte_identical`
- `data-service/tests/test_dg_context.py::TestDeterminism::test_get_debug_and_post_assemble_are_equal_for_graph_query`

Root cause confirmed: each asserts `response.status_code == 200` and observes `500`.
The `TestClient` does not surface the inner traceback, but this file
(`test_dg_context.py`) is explicitly named in `1203-VALIDATION.md`'s documented
environment-dependent list ("4 `test_dg_context.py` tests fail from the host because
the `neo4j` hostname resolves only inside compose"). **Classification: documented
environment-dependent (Neo4j/host-only DNS), not a regression.**

25 `ERROR` entries, broken down by file:

```
     20 ERROR data-service/tests/test_cg_structure_checks.py
      5 ERROR data-service/tests/test_computgraph_consult.py
```

Sampled traceback (`test_structural_full_frame_has_zero_violation_findings` setup):

```
address = IPv4Address(('neo4j', 7687)), family = 0
    @staticmethod
    def _dns_resolver(address, family=0):
        ...
>           info = NetworkUtil.get_address_info(address.host, address.port, ...)
```

All 25 errors are Neo4j-driver DNS resolution failures against hostname `neo4j`
(only resolvable inside the docker-compose network), at test setup, in
`TestStructuralChecksIntegration`, `TestRuleMappedChecksIntegration`,
`TestValidateRouteIntegration` (`test_cg_structure_checks.py`), and
`TestConsultIntegration` (`test_computgraph_consult.py`) — exactly the integration
classes the plan names as environment-dependent. **Classification: documented
environment-dependent (Neo4j not reachable from host), not a regression.**

**Unexplained failures: none.** Every failing/erroring test in the Python suite
classifies as documented environment-dependent.

### C# suite

Command: `dotnet test DG/tests/DG.Tests/ -v minimal`

Observed tail (verbatim, localized Russian runner output):

```
Не пройден!: не пройдено     4, пройдено   552, пропущено     0, всего   556, длительность 8 s. - DG.Tests.dll (net9.0)
```

Parsed (English): **failed: 4, passed: 552, skipped: 0, total: 556, duration: 8s.**

Failing tests (all 4, confirmed via targeted filter run):

- `DG.Tests.E2E.DesignStateValidationFlowTests.LegacyNoState_FlowStillWorks`
- `DG.Tests.E2E.DesignStateValidationFlowTests.ReinstateFailureModes_ProduceActionableMessages`
- `DG.Tests.E2E.DesignStateValidationFlowTests.Filtering_StateAndRule`
- `DG.Tests.E2E.DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve`

Root cause (sampled stack trace):

```
Neo4j.Driver.ServiceUnavailableException : Connection with the server breaks due to
IOException: Failed to connect to server 'bolt://localhost:7687/' ...
```

All 4 are `DesignStateValidationFlowTests` — exactly the documented
environment-dependent group ("4 `DesignStateValidationFlowTests` (C#) fail fast when
Neo4j is down"). **Classification: documented environment-dependent (Neo4j down),
not a regression.**

**Unexplained failures: none.**

### Baseline summary (the number plans 02/03 diff against)

| Suite | Passed | Failed | Skipped/Deselected | Errors | Unexplained |
|---|---|---|---|---|---|
| Python (`data-service/tests`) | 819 | 4 | 1 skipped, 8 deselected | 25 | 0 |
| C# (`DG/tests/DG.Tests`) | 552 | 4 | 0 | — | 0 |

---

## 2. Identity-literal blast radius (D-08/D-09)

Command:

```
grep -rn -E '(dg:[0-9A-F]{16}|OS_[0-9A-F]{16}|DS_[0-9A-F]{16}|PS_[0-9A-F]{16})' \
  --include=*.cs --include=*.py --include=*.json --include=*.md --include=*.cypher --include=*.txt . \
  | grep -v '\.kilo/\|/obj/\|/bin/\|node_modules'
```

**90 total hits.** Full inventory below, grouped by role.

### 2a. Known/expected pins (test assertions that WILL need updating in plan 02)

| File:Line | Literal | Note |
|---|---|---|
| `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs:64` | `dg:BC8E62EE137E2B56` | golden dgId vector — expected, already named in VALIDATION.md |
| `data-service/tests/test_dg_identity.py:39` | `GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"` | Python counterpart — expected |
| `data-service/tests/test_computgraph_publish.py:11,45` | `dg:BC8E62EE137E2B56` (doc comment + `GOLDEN_DG_ID`) | reuses the same golden vector — expected |
| `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs:169` | `OS_493B9A7153D92072` | DesignState regression pin (3-arg `ComputeObjectStateId`) — expected, named in VALIDATION.md/1203-02-PLAN.md |
| `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs:319` | `DS_3C3C50530BE1DED0` | DesignState regression pin (aggregate) — expected, named in 1203-02-PLAN.md |

These five are the ones VALIDATION.md and 1203-02-PLAN.md already call out as the
pins plan 02 must update.

### 2b. Additional literals plan 02 must update

**None discovered in test-assertion form beyond the five listed in 2a.** However,
the following additional occurrences of the SAME golden vector literal
(`dg:BC8E62EE137E2B56`) exist as *fixture data / test scaffolding referencing it
indirectly* and must be checked when plan 02 re-derives the vector:

| File:Line | Literal | Note |
|---|---|---|
| `data-service/tests/cg_fixtures.py` — no direct hit for `BC8E62...`, but references it in a docstring at line 16 | `dg:BC8E62EE137E2B56` (docstring only) | prose reference, not an assertion — no code change needed, but reads stale if plan 02 changes the golden vector without updating this comment |
| `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs:284,431,437` | `DS_A1B2C3D4E5F6A7B8` | **This is a hand-authored fixture literal, NOT a derived-hash regression pin** — it is embedded directly in a JSON test payload string (`statePayloadJson`) and re-asserted as a literal expected value in the same test, not computed via any ID-generation function under test. It does not encode `(project, ...)` inputs the same way `DesignStateIdGeneratorTests.cs` pins do, so **D-08/D-09 do not invalidate it** — confirmed by inspection: the test never calls `DesignStateIdGenerator`, it round-trips a hardcoded stateId string through deserialization. Flagged here for visibility, not required to change. |

No other test file outside `DG.Tests` / `data-service/tests` contains a literal in
assertion position. The remaining 82 hits (of 90 total) are either:

- **Planning-doc prose** (`.planning/milestones/...`, `.planning/phases/1200-*`,
  `.planning/phases/1202-*`, `.planning/phases/1203-*`, `DG_OBSIDIAN/...`,
  `.planning/STATE.md`) — narrative references to the golden vector or historical
  literals, not executable code. Not in scope for plan 02's edits (they are history/
  session notes and prior-phase artifacts, not live assertions), but note that
  `1203-RESEARCH.md`, `1203-PATTERNS.md`, and `1203-02-PLAN.md` themselves quote
  `dg:BC8E62EE137E2B56` as the "before" value — plan 02 should treat those quotes as
  its own before/after worked example, not as something to edit for correctness.
- **`fixtures/golden/` frozen-fixture literals** (`fixture.json`, `seed.cypher`,
  `replay/mixed-verdicts.json`, `replay/seed-replay.cypher`,
  `canonical-vectors.json`) — see § 3 below. These are Phase 1200's frozen fixture
  and are explicitly NOT to be edited by this phase per `fixtures/golden/MANIFEST.md`'s
  freeze policy. They pin `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`/`OBJ_GOLD_EMPTY` object
  dgIds (`dg:57C65BE15E8E368B`, `dg:729E143958721742`, `dg:0B23FFBDA52B73A6`),
  computed from `(project, definitionId, cgId)` — the *Object* dgId hash inputs,
  not the DesignState `(D-08 project-folding)` hash inputs. **D-08 changes
  DesignState ID inputs (`OS_`/`DS_`/`PS_` StateId hashing), not Object dgId
  minting inputs — these frozen fixture dgIds are unaffected by D-08.** D-09
  (length-prefix / pipe-collision fix) DOES touch the shared hash-input encoding
  used by both Object dgId minting and DesignState ID minting, so if D-09 changes
  the canonical join format, these frozen fixture values would need re-derivation —
  **this is a direct conflict with the fixture freeze policy and must be flagged to
  plan 02/03 as a blocking question, not silently resolved here.**
- **Illustrative documentation examples** (`spec/DATABASE.md:386,411,441,473,527`,
  `spec/API.md:189`, `spec/DG-ID.md:39,155`) — placeholder-shaped `dgId` values in
  Cypher/JSON code-block examples (e.g. `dg:9F2A4C1E7B03D5A8`), not derived from any
  real input tuple and not asserted anywhere. These are not testable pins; they are
  prose illustrations of the ID *shape*. No action required for D-08/D-09 unless the
  shape itself changes (it does not — D-08/D-09 change hash *inputs*, not output
  format).
- **Deliberately-fake test literals** (`data-service/tests/cg_fixtures.py`,
  `test_cg_paramstate_store.py`, `test_design_state_projection.py`,
  `DesignStateCanonicalProjectionTests.cs`, `ObjStateDgIdTests.cs`,
  `test_dg_identity.py:368,553`) — literals like `dg:AAAAAAAAAAAAAAAA`,
  `dg:DEADBEEFDEADBEEF`, `dg:0000000000000000` are intentionally-fake sentinel
  values used as opaque test doubles, never computed by a real hash function under
  test. Not affected by D-08/D-09.

### Blocking question surfaced for plan 02/03

**Does D-09's length-prefix fix change the canonical join string used to mint
`fixtures/golden/fixture.json`'s frozen Object dgIds?** If yes, this is a direct
conflict with `fixtures/golden/MANIFEST.md`'s freeze policy (which forbids editing
`fixture.json`/`seed.cypher`/`canonical-vectors.json` without a version bump and
Change-Reason Log entry). This preflight surfaces the conflict; it does not resolve
it — resolution belongs to whichever plan actually implements D-09.

---

## 3. `fixtures/golden/canonical-vectors.json` — does it carry a DesignState/dgId literal?

Command: `grep -nE '(dg:[0-9A-F]{16}|OS_[0-9A-F]{16}|DS_[0-9A-F]{16}|PS_[0-9A-F]{16})' fixtures/golden/canonical-vectors.json`

Output:

```
18:      "description": "dgId minting input for fixtures/golden/fixture.json's OBJ_GOLD_PASS object (project|definitionId|cgId), truncated-to-16-hex form is fixture.json's OBJ_GOLD_PASS.dgId = dg:57C65BE15E8E368B.",
29:      "description": "dgId minting input for fixtures/golden/fixture.json's OBJ_GOLD_FAIL object; truncated-to-16-hex form is fixture.json's OBJ_GOLD_FAIL.dgId = dg:729E143958721742.",
```

**Answer: YES — not empty.** `canonical-vectors.json` contains two `dg:`-shaped
literals in `description` fields (`dg:57C65BE15E8E368B`, `dg:729E143958721742`), plus
the top-level golden vector's `sha256Upper` full digest (`BC8E62EE137E2B56...`) whose
first-16 truncation is `dg:BC8E62EE137E2B56` (not matched by the regex directly
because it's stored as a bare 64-hex `sha256Upper` value, not prefixed `dg:`, but it
is the same identity string in expanded form — see `vectors[0]`, line 14 of the file).

**This closes RESEARCH.md Open Question 1 with a correction:** the file is not
literal-free. However, all three literals it carries are **Object dgId** values
(`OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`, hashed from `project|definitionId|cgId`) — the same
frozen-fixture values discussed in § 2 above, describing (not asserting-as-test-input)
the already-frozen `fixture.json` dgIds. **No `OS_`/`DS_`/`PS_` DesignState-ID
literal exists anywhere in `canonical-vectors.json`.** D-08 (DesignState hash change)
does not touch this file. D-09 (length-prefix / pipe-collision fix) **does** touch
this file's `sha256Upper` digests IF the join-string encoding it hashes changes —
same blocking question as § 2's fixture-freeze conflict, and it applies here too:
`canonical-vectors.json` is under the same `fixtures/golden/MANIFEST.md` freeze
policy as `fixture.json`.

---

## 4. SHACL shape count

Command: `grep -c 'a sh:NodeShape' ontology/dg-shapes.ttl`

Output: **17**

**Correction vs. both prior claims:** CONTEXT.md D-05 claims 20; RESEARCH.md claims
18. The observed disk count is **17** — neither prior claim is correct. This is
recorded as an explicit correction per this plan's prohibition against silently
reconciling to either cited number. Per the plan's own instruction, the propagation
checklist for `dgsh:AtomAttributeOfShape` (the new shape ALGN12-14 adds) must assert
the presence of that specific named shape after the change, not assert any total
count — the baseline "before" count for that comparison is **17**, not 18 or 20.

---

## 5. WR-02 relocation

`1203-VALIDATION.md` / prior phase artifacts cite `spec/DATABASE.md:336` for a
wrong-route/verb defect (WR-02). That line is confirmed stale — it currently holds
unrelated Phase 36 provenance prose.

Commands run:

```
grep -n -E '/identity/|/computgraph/' spec/DATABASE.md
grep -n -E '@app\.(get|post|patch|put|delete)\("/identity' data-service/app.py
```

Live decorators in `data-service/app.py`:

```
2054:@app.post("/identity/mint")
2069:@app.get("/identity/resolve")
2084:@app.post("/identity/bind")
2109:@app.get("/identity/{dg_id}/representations")
2116:@app.delete("/identity/{dg_id}/representations")
2131:@app.post("/identity/{dg_id}/properties")
2155:@app.get("/identity/{dg_id}/properties")
```

`spec/DATABASE.md`'s only route-verb claims for `/identity/*` are on two lines
(518, 551); the other `/identity/` hits in the grep are prose (line 558) or
non-route context. Comparison table:

| Doc line | Doc-claimed verb + path | Actual decorator verb + path | Match / MISMATCH |
|---|---|---|---|
| `spec/DATABASE.md:518` | `PATCH /identity/bind` | `POST /identity/bind` (`app.py:2084`) | **MISMATCH** — verb: doc says PATCH, code is POST |
| `spec/DATABASE.md:518` | `POST /identity/{dgId}/representations` | `GET /identity/{dg_id}/representations` (`app.py:2109`) | **MISMATCH** — verb: doc says POST, code is GET |
| `spec/DATABASE.md:551` | `POST /identity/{dgId}/properties` | `POST /identity/{dg_id}/properties` (`app.py:2131`) | match |

**Conclusion: WR-02 located at `spec/DATABASE.md:518`** — doc says `PATCH
/identity/bind`, code is `POST /identity/bind` (a second, co-located mismatch on the
same line also claims `POST /identity/{dgId}/representations` where the code is
`GET /identity/{dg_id}/representations`). This single doc line carries two
independent verb/route mismatches against live code. `spec/DATABASE.md:336`, the
Phase 32.1-era citation, no longer contains this text — it was correctly identified
as stale by RESEARCH.md Discrepancy 2; the real location has moved to line 518 in
the current file. Plan 05 should fix both mismatches on that line, and additionally
note that the doc does not mention `/identity/mint`, `/identity/resolve`,
`/identity/{dg_id}/representations` DELETE, or `/identity/{dg_id}/properties` GET
by verb+path at all in a per-route documentation block — those four live routes
have no explicit doc-claim to cross-check (not a MISMATCH, just undocumented at the
per-route level; the identity-registry paragraph at line 558 describes the
route family generically).

### `spec/API.md` identity-route count

Command: `grep -n '/identity/' spec/API.md`

Output: **0 matches.**

**`spec/API.md` documents zero `/identity/*` routes.** This is a first-write for
plan 05's API documentation work, not a revision of existing content.

---

## 6. D-04 attachment inputs — observed atom-naming convention

Source: `cypher_template.txt` lines 236-269 (the `A1`/`A2`/`A3`/`H1` atom MERGE
block).

Observed `Atom_Id` pattern: `'<RULE_ID>_A1'`, `'<RULE_ID>_A2'`, `'<RULE_ID>_A3'`,
`'<RULE_ID>_H1'` — i.e. `Atom_Id` is `{RULE_ID}_{suffix}` where suffix is one of
`A1`, `A2`, `A3` (body atoms, via `HAS_BODY` with `order` 1/2/3) or `H1` (head atom,
via `HAS_HEAD` with `order` 1).

Observed `type` per suffix:

| `Atom_Id` suffix | `type` value | Role |
|---|---|---|
| `_A1` | `ClassAtom` | body atom 1 — class membership |
| `_A2` | `DataPropertyAtom` | body atom 2 — data property |
| `_A3` | `BuiltinAtom` | body atom 3 — builtin comparison |
| `_H1` | `DataPropertyAtom` | head atom 1 — violation-flag property (inverted-logic pattern per CLAUDE.md) |

**The suffix that maps to `type = 'DataPropertyAtom'` is `_A2` (body) and `_H1`
(head)** — both share the same `type` value despite different `Atom_Id` suffixes
and different `HAS_BODY`/`HAS_HEAD` relationship roles. This is the factual basis
plan 04 must cite when stating the D-04 attachment rule: `ATTRIBUTE_OF` must key off
`type = 'DataPropertyAtom'` (not off suffix alone, since both `_A2` and `_H1` share
that type but play different structural roles), and must disambiguate the two
`DataPropertyAtom` occurrences by their `HAS_BODY`/`HAS_HEAD` relationship, not by
`Atom_Id` suffix pattern-matching alone.

---

## Self-verification: no source/spec/ontology/fixture file was touched

```
git status --porcelain -- . ':!.planning/phases/1203-identity-convergence-and-attribute-of-decision/'
```

Expected: no output from this command scoped outside the phase directory (pre-existing
unrelated modifications from before this plan started — `.planning/STATE.md` and
`DG/src/DG.Core/bin|obj/*` build artifacts — are excluded from this plan's own
diff scope; they predate this session and are not caused by Task 1 or Task 2).

