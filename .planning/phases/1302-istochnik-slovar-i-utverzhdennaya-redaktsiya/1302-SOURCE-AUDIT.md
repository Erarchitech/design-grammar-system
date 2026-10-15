# 1302 — Multi-source coverage audit (planning only)

No implementation, product approval or CDE authorization is evidenced by these plans. `1302-CONTEXT.md` does not assign D-NN IDs: citations below use its actual titled decision groups and bullets, not invented decision numbers. Spec-less edge probe returned **10/10 `unclassified` / `unresolved`**, zero explicit/backstop; each remains an assumption in the plans and must be independently verified. No plain phase SPEC or AI-SPEC exists.

| Source | Item | Coverage | Plan / limit |
|---|---|---|---|
| GOAL | Source-linked project rule, steward release, independent lessons copy with history | COVERED | 08 entry → 01 tracer → 02/03 → 09 propagation → 10 publish backend → 04 evaluator/history → 05/06 → 07 exit; actual owner gate 08 and 07 |
| REQ | DGKN-01 source revision + non-executable intent | COVERED | 01/06/07; real source ACL gated |
| REQ | DGKN-02 immutable company release + draft privacy | COVERED | 02/06/07 |
| REQ | DGKN-03 steward issue + retirement history | COVERED | 02/06/07; appointment gated |
| REQ | DGKN-04 typed diff/formalization/confirm | COVERED | 01/03/06/07 |
| REQ | DGKN-05 atomic CAS/audit | COVERED | 01/03/06/07; real Neo4j race gated |
| REQ | DGKN-06 executable run corpus/history/recheck | COVERED | 10 backend publish/run manifest; 04 actual C# evaluator→Publish→BuildRequest→backend→saved run equality; 06/07; actual isolated run gated |
| REQ | DGKN-07 one-project class/object/condition scope | COVERED | 01/06/07 |
| REQ | DGKN-08 two-right transfer/new ID/lineage | COVERED | 05/06/07; approved provider gated |
| REQ | DGKN-09 fresh destination check + separate approval | COVERED | 05/06/07; human gate |
| REQ | DGKN-10 typed deterministic `/dg-` registry | COVERED | 06/07; web/server adapter only, component not claimed |
| CONTEXT | Source and applicability: pin URI/ID/revision/hash/fragment/provenance; CDE ACL separate; intent non-executable; one project; no source until allowed list | COVERED | 01, 07 |
| CONTEXT | Vocabulary: immutable company release, provenance, project pin, editor proposal, appointed steward issuance, private draft, retirement history | COVERED | 02, 06, 07 |
| CONTEXT | Rule edit/retirement: typed diff/formalization/confirm, expectedRevision, server audit, old run corpus and recheck | COVERED | 01, 03, 04, 06, 07 |
| CONTEXT | Lessons/commands: independent same-company transfer/destination checks, fresh evidence/approval, registry/help/risk, early reject, per-action recheck | COVERED | 05, 06, 07 |
| RESEARCH | Patterns 1–6: source/scope, vocabulary, transactional CAS, actual corpus pin, independent copy, typed dispatch | COVERED | 08 entry/01 source; 02/03 vocab/CAS; 09 mandatory graph propagation; 10/04 publish/corpus; 05/06 copy/dispatch; 07 exit |
| RESEARCH | Validation Architecture: Wave 0 focused files, deny matrix, real DB/evaluator, route/security tests, human acceptance | COVERED | 01–10; `1302-VALIDATION.md` maps 25 final task IDs, flags false and latency unknown pending execution/independent sign-off |
| RESEARCH | Legacy bypass, leakage, read skew, no machine verdict from human-only check, deterministic measurement limits | COVERED | 01/03/04/05/06/07 |
| UI-SPEC | Empty/loading/partial/conflict, zero-one-many, overflow + access-clearing, bilingual/accessibility | COVERED WITH OPEN SIGN-OFF | 06/07; six `## UI Considerations` rows pending independent probe |

Excluded, not gaps: native GH/Revit binding (1303), Viewer state/review parity (1304), CAD write (1305), CDE publication (1306), removed DeGram-current-DG comparison (`1300-SCOPE-REVISION.md`), and child `apps/degram` edits without separate repository approval. No provider endpoints or steward identities are invented. If execution discovers an affected tracked graph consumer, 09 must record tested compatibility or execute an exact amended in-phase task before 02/04; no unspecified future plan may substitute. If actual provider is selected, 08/07 require owner gate and an approved capability matrix before integration; do not silently narrow scope.

## Phase gate state at planning

- Phase 1300/1301 acceptance, steward/approver appointments, allowed CDE source list and transfer/destination authority: **OPEN**.
- `python tools/degram/workspace.py verify` is structural (`productAccepted: false` in prior observed probe), not product evidence.
- Existing `python -m pytest data-service/tests/test_company_scope.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` currently fails collection on Python 3.14 because `cryptography` is absent. No package install authorized.
- No live Neo4j/CDE/evaluator/CAD/LLM/Desktop, schema migration, activation, commit or push performed.
