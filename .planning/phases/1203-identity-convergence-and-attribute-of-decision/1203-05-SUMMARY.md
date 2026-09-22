---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 05
subsystem: database
tags: [schema-propagation, attribute-of, shacl, identity, dg-id, api-docs, rule-partition]

# Dependency graph
requires:
  - phase: 1203-02
    provides: Length-prefix hash-input encoding (EncodeHashInput/_encode_hash_input) and project-in-hash for DesignState ids, both re-derived and documented here
  - phase: 1203-03
    provides: Label-aware, graph-tagging mint_identity with the entity_kind-validated /identity/mint route, documented here in spec/API.md
  - phase: 1203-04
    provides: ATTRIBUTE_OF as a real, project-scoped Neo4j relationship (_publish_attribute_of), propagated here across every schema surface
provides:
  - ATTRIBUTE_OF documented consistently across CLAUDE.md, README.md, copilot-instructions.md, cypher_template.txt (with an explicit rule-ingest exclusion), dataset_schema.json, spec/DATABASE.md, spec/LPG-OWL-MAPPING.md, and a new SHACL shape in ontology/dg-shapes.ttl
  - A new spec/RULE-PARTITION-POLICY.md decision-table row assigning the cross-layer rule-parameter bridge category to the ATTRIBUTE_OF edge
  - spec/DG-ID.md extended into the single identity authority: DesignState id minting, the ObjState dual-form authority contract, the length-prefix encoding contract precise enough to reimplement, the project-in-hash rollout across DesignState functions, the no-rewrite migration policy for pre-1203 ids, and the resolved definitionId (DocumentId, not FileName) ambiguity
  - spec/API.md's first-write Identity section documenting all seven /identity/* routes, with /identity/mint's entity_kind field detailed
  - WR-02 fixed in spec/DATABASE.md (POST not PATCH for /identity/bind; GET/DELETE split correctly for /identity/{dgId}/representations)
affects: ["1203-06"]

tech-stack:
  added: []
  patterns: ["Schema-propagation sweep: walk CLAUDE.md's checklist file by file for every new relationship type, verifying documentation against the actual writer implementation rather than paraphrasing the plan"]

key-files:
  created: []
  modified:
    - CLAUDE.md
    - README.md
    - .github/copilot-instructions.md
    - cypher_template.txt
    - training/dataset_schema.json
    - ontology/dg-shapes.ttl
    - spec/DATABASE.md
    - spec/API.md
    - spec/DG-ID.md
    - spec/RULE-PARTITION-POLICY.md
    - spec/LPG-OWL-MAPPING.md

key-decisions:
  - "Added spec/LPG-OWL-MAPPING.md to CLAUDE.md's Schema Change Propagation checklist -- it was a real schema-coupled surface missing from that list (Rule 2: the checklist omitting a relevant surface is exactly the drift class this milestone exists to close)"
  - "AtomAttributeOfShape targets swrl:DatavaluedPropertyAtom (the RDF/SHACL-visible class corresponding to a Metagraph Atom{type:'DataPropertyAtom'}), constrains dgc:attributeOf's range to dgc:Parameter, at sh:Warning severity -- a rule with no bound parameters is legitimate (geometry-required default); only a misdirected edge is a genuine defect"
  - "RULE-PARTITION-POLICY.md's new decision-table row assigns ATTRIBUTE_OF ownership to itself (the persisted edge), not to SWRL or SHACL -- it is a derived structural fact recorded from an already-computed inputBindings resolution, not a new validation verdict"
  - "Resolved WR-04 (definitionId ambiguity) by reading CgContextDgIdAssigner.AssignDgIds directly rather than trusting the golden-vector test constants: definitionId = CgDefinition.DocumentId (doc.DocumentID.ToString()), never FileName (doc.DisplayName) -- test literals like 'wall.gh'/'frame.gh' are opaque readability choices, not evidence of what the production caller passes"
  - "Documented the canonical_json.hash_scalar_tuple/CanonicalJsonWriter.HashScalarTuple divergence (surfaced by 1203-02) as a known, deliberately out-of-scope gap in spec/DG-ID.md rather than silently describing the byte-for-byte parity claim as still true"
  - "spec/API.md's /identity/mint entry documents only the FastAPI pydantic-validation 422 shape for an unrecognized entity_kind (not the {error,hint,code} shape), since that rejection happens before the route body runs -- verified against MintRequest's field_validator"

patterns-established:
  - "For a schema-propagation sweep touching an ontology file, re-derive the SHACL shape's target/path/range from the actual writer Cypher (or the TBox declaration it implements) rather than the plan prose, and grep-verify the file still parses as Turtle before committing"

requirements-completed: [ALGN12-12, ALGN12-13, ALGN12-14]

coverage:
  - id: D1
    description: "ATTRIBUTE_OF documented consistently (endpoints, direction, project scoping, publish-time derivation, rule-ingest exclusion) across every file on CLAUDE.md's Schema Change Propagation checklist, matching computgraph_publish.py's _publish_attribute_of exactly"
    requirement: "ALGN12-14"
    verification:
      - kind: other
        ref: "for f in CLAUDE.md README.md .github/copilot-instructions.md cypher_template.txt training/dataset_schema.json spec/DATABASE.md spec/RULE-PARTITION-POLICY.md spec/LPG-OWL-MAPPING.md ontology/dg-shapes.ttl; do grep -qE 'ATTRIBUTE_OF|attributeOf' \"$f\"; done"
        status: pass
      - kind: other
        ref: "python -c \"import json;json.load(open('training/dataset_schema.json'))\""
        status: pass
      - kind: other
        ref: "python -c \"import rdflib;rdflib.Graph().parse('ontology/dg-shapes.ttl',format='turtle')\""
        status: pass
    human_judgment: false
  - id: D2
    description: "New dgsh:AtomAttributeOfShape SHACL shape constrains ATTRIBUTE_OF's range to Parameter at Warning severity, following the file's existing sh:NodeShape/named-property-shape/howToFix conventions; new spec/RULE-PARTITION-POLICY.md decision-table row assigns the cross-layer rule-parameter bridge category to the ATTRIBUTE_OF edge itself"
    requirement: "ALGN12-14"
    verification:
      - kind: other
        ref: "grep -c 'howToFix' ontology/dg-shapes.ttl (increased vs. pre-task baseline of 17 NodeShapes/46 total mentions); git diff shows exactly one new decision-table row in spec/RULE-PARTITION-POLICY.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "spec/DG-ID.md extended to cover DesignState id minting: four id families + two aggregate functions, the ObjState dual-authoritative-form contract (neither form deleted/deprecated), the length-prefix encoding contract precise enough to reimplement (including null-vs-empty), project-in-hash rollout across DesignState functions, and the no-rewrite migration policy for pre-1203 ids"
    requirement: "ALGN12-12"
    verification:
      - kind: other
        ref: "grep -qi 'DesignState' spec/DG-ID.md && grep -q 'ComputeObjectStateIdFromRef' spec/DG-ID.md && grep -q 'ComputeObjectStateId' spec/DG-ID.md"
        status: pass
      - kind: other
        ref: "grep -n 'deleted, deprecated, or scheduled for removal' spec/DG-ID.md -- both matches are explicit negations (retained, not scheduled for removal), not violating claims"
        status: pass
    human_judgment: false
  - id: D4
    description: "WR-04 resolved: definitionId is CgDefinition.DocumentId (GH document id), not FileName -- confirmed against the actual production caller CgContextDgIdAssigner.AssignDgIds, not inferred from filename-shaped test literals"
    verification:
      - kind: other
        ref: "grep -n 'DG.Core.Services.CgContextDgIdAssigner.AssignDgIds' spec/DG-ID.md; manual read of DG/src/DG.Core/Services/CgContextDgIdAssigner.cs confirms context.Definition.DocumentId is read into the local definitionId variable, never FileName"
        status: pass
    human_judgment: false
  - id: D5
    description: "spec/API.md documents /identity/mint (entity_kind field + allowed values) as a first-write, alongside all seven live /identity/* routes; WR-02 fixed in spec/DATABASE.md (POST not PATCH for /identity/bind; GET/DELETE correctly split for /identity/{dgId}/representations); route-consistency script confirms every documented identity route matches a live app.py decorator by verb and path"
    requirement: "ALGN12-13"
    verification:
      - kind: other
        ref: "grep -q '/identity/mint' spec/API.md; route-diff script (re.finditer over @app.* decorators vs. backtick-quoted VERB path claims in spec/DATABASE.md) exits 0 with 'all documented identity routes match live decorators'"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-09-22
status: complete
---

# Phase 1203 Plan 05: ATTRIBUTE_OF Schema Propagation + DG-ID.md Consolidation Summary

**Propagated the new `ATTRIBUTE_OF` Metagraph→Computgraph relationship across every schema surface (including a new SHACL shape and rule-partition decision-table row), and extended `spec/DG-ID.md` into the single identity authority covering both `dgId` and DesignState id minting, resolving the `definitionId` DocumentId/FileName ambiguity and the WR-02 route-doc defect along the way.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-22
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Added `ATTRIBUTE_OF` to `CLAUDE.md`'s Relationships paragraph (with endpoints, derivation, project scoping) and its Schema Change Propagation checklist (also adding the previously-missing `spec/LPG-OWL-MAPPING.md` to that checklist itself)
- Added the relation to `README.md`, `.github/copilot-instructions.md`, and `cypher_template.txt` — the last with an explicit instruction that an LLM must NOT emit `ATTRIBUTE_OF` MERGE statements during rule ingestion, since the edge is derived exclusively at publish time
- Added `ATTRIBUTE_OF` to `training/dataset_schema.json`'s relationship structures, preserving valid JSON
- Documented the relation's full shape (endpoints, provenance properties `derivedFromRuleId`/`source`/`determinability`, project scoping, publish-only write path) in `spec/DATABASE.md`'s Parameter description and Relationships table
- Added a new TBox-to-LPG correspondence entry in `spec/LPG-OWL-MAPPING.md` recording that `dgc:attributeOf` is now realized by the live `ATTRIBUTE_OF` relationship type, with the CQ3 narrowing preserved (records structure, does not prove solver equivalence)
- Added a new SHACL shape `dgsh:AtomAttributeOfShape` (targeting `swrl:DatavaluedPropertyAtom`, constraining `dgc:attributeOf`'s range to `dgc:Parameter`, `sh:Warning` severity) to `ontology/dg-shapes.ttl`, following the file's existing named-property-shape/`howToFix` conventions
- Added a new decision-table row to `spec/RULE-PARTITION-POLICY.md` assigning the cross-layer rule-parameter bridge category to the `ATTRIBUTE_OF` edge itself (neither SWRL nor SHACL — a persisted derived fact, not a new judgment)
- Extended `spec/DG-ID.md` with: the length-prefix hash-input encoding contract (precise enough to reimplement, including the `-1:`/`0:` null-vs-empty distinction and the twinned C#/Python implementation table); a new DesignState Identity section covering the four id families, the two aggregate functions, and the ObjState dual-form authority contract (`ComputeObjectStateIdFromRef` authoritative for canvas capture, the 3-arg CMPST-07 form retained with no current production caller — neither deprecated); a project-in-hash table showing which DesignState functions take `project` and why the three capture components currently do not; the no-rewrite migration policy for pre-1203 ids; and the resolved `definitionId` ambiguity (DocumentId, not FileName)
- Added a first-write Identity section to `spec/API.md` documenting all seven `/identity/*` routes, with `/identity/mint`'s request/response shape and `entity_kind` allowlist detailed
- Fixed WR-02 in `spec/DATABASE.md`: `/identity/bind` corrected from `PATCH` to `POST`, and `/identity/{dgId}/representations` correctly split into its `GET` (list) and `DELETE` (detach) forms — both errors on the same line the 1203-01 preflight identified

## Task Commits

1. **Task 1: Propagate ATTRIBUTE_OF across every schema surface and add its SHACL shape** - `da03d2a` (docs)
2. **Task 2: Extend spec/DG-ID.md into the single identity authority and fix the carried doc findings** - `555912f` (docs)

## Files Created/Modified

- `CLAUDE.md` - Added `ATTRIBUTE_OF` to the Relationships paragraph; added `spec/LPG-OWL-MAPPING.md` to the Schema Change Propagation checklist
- `README.md` - Added `ATTRIBUTE_OF` alongside the Computgraph relationship list
- `.github/copilot-instructions.md` - Added `ATTRIBUTE_OF` with an explicit rule-ingest exclusion note
- `cypher_template.txt` - Added `ATTRIBUTE_OF` to the relationship legend with a "never emit during rule ingestion" warning (this is the LLM prompt surface)
- `training/dataset_schema.json` - Added an `ATTRIBUTE_OF` relationship-type entry mirroring `PARAM_LINK`'s structure
- `ontology/dg-shapes.ttl` - Added `dgsh:AtomAttributeOfShape` (new numbered section 18)
- `spec/DATABASE.md` - Documented `ATTRIBUTE_OF`'s full shape in the Parameter section and Relationships table; fixed WR-02 (`/identity/bind` verb, `/identity/{dgId}/representations` GET/DELETE split)
- `spec/RULE-PARTITION-POLICY.md` - Added the cross-layer rule-parameter bridge decision-table row
- `spec/LPG-OWL-MAPPING.md` - Added the `dgc:attributeOf` TBox-to-LPG correspondence section
- `spec/DG-ID.md` - Added the length-prefix encoding contract, the DesignState Identity section (four id families, ObjState authority contract, project-in-hash table, migration policy, definitionId resolution), and updated the Valid Until/Propagation footer to declare single-authority status
- `spec/API.md` - Added the first-write Identity section documenting all seven `/identity/*` routes

## Decisions Made

- Added `spec/LPG-OWL-MAPPING.md` to `CLAUDE.md`'s propagation checklist — it was a genuine gap (a schema-coupled surface this plan's own Task 1 needed to edit, absent from the checklist that should have named it)
- `AtomAttributeOfShape` uses `sh:Warning` (not `sh:Violation`) severity per the plan's own reasoning: a rule with zero bound parameters is the legitimate geometry-required default, so only a misdirected edge (wrong range) is a genuine defect, not the mere absence of the edge
- Resolved the `definitionId` DocumentId/FileName ambiguity by tracing the actual production caller (`CgContextDgIdAssigner.AssignDgIds`) rather than trusting the golden-vector test literals, which use filename-shaped strings (`"wall.gh"`, `"frame.gh"`) purely for readability — the code path definitively reads `context.Definition.DocumentId`, never `FileName`
- Documented the `canonical_json.hash_scalar_tuple`/`CanonicalJsonWriter.HashScalarTuple` divergence (from 1203-02's SUMMARY) as a known, deliberately out-of-scope gap rather than silently perpetuating the stale "byte-for-byte parity" claim anywhere this plan's DG-ID.md edits touch identity-hashing documentation

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria were verified via the exact grep/JSON/Turtle/route-diff commands specified in the plan's `<verify>` blocks before each commit.

## Issues Encountered

None requiring escalation. A quick grep for "delet|deprecat|remov" language against the `ComputeObjectStateId` 3-arg form's documentation initially looked like a self-check failure, but both matches on inspection are explicit negations ("neither is deleted... nor scheduled for removal", "not a legacy artifact awaiting removal") — satisfying the plan's prohibition rather than violating it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ATTRIBUTE_OF` is now documented consistently everywhere the schema-propagation checklist requires, matching the Plan 04 implementation exactly (verified endpoint-by-endpoint against `_publish_attribute_of`'s Cypher, not paraphrased from prose).
- `spec/DG-ID.md` is now the single identity authority per ALGN12-12 — Plan 06 (or any future identity work) should extend this file rather than create a second identity spec.
- `spec/API.md`'s `/identity/*` documentation and `spec/DATABASE.md`'s route-verb corrections are verified against the live `app.py` decorators via an automated diff script — future route changes should re-run that script (embedded in this plan's Task 2 `<verify>` block) before merging.
- No blockers identified for Plan 06.

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/1203-identity-convergence-and-attribute-of-decision/1203-05-SUMMARY.md`
- FOUND: `CLAUDE.md`, `README.md`, `.github/copilot-instructions.md`, `cypher_template.txt`, `training/dataset_schema.json`, `ontology/dg-shapes.ttl`, `spec/DATABASE.md`, `spec/API.md`, `spec/DG-ID.md`, `spec/RULE-PARTITION-POLICY.md`, `spec/LPG-OWL-MAPPING.md` — all present and modified on disk
- FOUND commit: `da03d2a` (Task 1) in `git log --oneline --all`
- FOUND commit: `555912f` (Task 2) in `git log --oneline --all`
- `grep -qE 'ATTRIBUTE_OF|attributeOf'` over all 9 propagation-list files: all pass
- `python -c "import json;json.load(open('training/dataset_schema.json'))"`: exits 0
- `python -c "import rdflib;rdflib.Graph().parse('ontology/dg-shapes.ttl',format='turtle')"`: exits 0
- Route-consistency script (documented `/identity/*` routes in `spec/DATABASE.md` vs. live `@app.*` decorators): "all documented identity routes match live decorators"
- `git status --porcelain migrations/`: empty (unchanged)
- `git status --porcelain Publications/`: no modifications (all pre-existing untracked content, none touched)
