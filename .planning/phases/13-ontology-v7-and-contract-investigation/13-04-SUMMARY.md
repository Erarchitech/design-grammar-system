---
phase: 13-ontology-v7-and-contract-investigation
plan: 04
subsystem: ontology
tags: [owl, rdf, catalog, markdown-export, python, ontology-transform]

# Dependency graph
requires:
  - phase: 13-ontology-v7-and-contract-investigation (plan 02)
    provides: "ontology/DesignGrammar-V7.owl — generated V7 ontology, the core file the companion artifacts reference"
provides:
  - "ontology/apply_v7_extensions.py — idempotent, self-checking V6->V7 facade/extension transform script"
  - "ontology/DesignGrammar-{BOT,Topologic,standards}-extension-V7.owl — the three regenerated V7 facade files"
  - "ontology/catalog-v001-V7.xml — OASIS XML catalog mapping DG ontology IRIs to the -V7 bundle"
  - "ontology/make_export_v7.py + ontology/export_to_markdown_v7.py — ported markdown-exporter generator chain"
  - "ontology/make_docs_v7.py + ontology/DesignGrammar-V7.md — regenerated human-readable V7 ontology docs"
affects: ["14-graph-schema-v4-propagation", "17-graph-access-components", "18-rules-and-validator-rework"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Generator-of-a-generator chain for markdown docs (make_export_v7.py writes export_to_markdown_v7.py, which is itself directly runnable; make_docs_v7.py is the named driver that invokes it) — mirrors the V6 apply_v6_extensions.py / make_export_v6.py generator-script pattern so no generated artifact is ever hand-edited"]

key-files:
  created:
    - "ontology/apply_v7_extensions.py"
    - "ontology/DesignGrammar-BOT-extension-V7.owl"
    - "ontology/DesignGrammar-Topologic-extension-V7.owl"
    - "ontology/DesignGrammar-standards-extension-V7.owl"
    - "ontology/catalog-v001-V7.xml"
    - "ontology/make_export_v7.py"
    - "ontology/export_to_markdown_v7.py"
    - "ontology/make_docs_v7.py"
    - "ontology/DesignGrammar-V7.md"
  modified: []

key-decisions:
  - "BOT/Topologic extensions only needed a version bump + a prose-only ComputationGraph->Computgraph rename — both anchor on dg:Topology, which V7-INVESTIGATION.md does NOT rename, and neither file references the dg:ObjectProperty/dg:DatatypeProperty reification classes (only the unrelated, already-short-named dgm:ObjectPropertyAtom/dgm:DataPropertyAtom compound classes appear, out of scope for the rename table)"
  - "Standards facade needed a single blanket ValidationRun->Run rename (class ref + 2 prose mentions) plus the version bump — confirmed via grep that ValidationGraph and the bare dg:ObjectProperty/dg:DatatypeProperty reification-class tokens are not referenced in this file, so those transforms from the task's conditional list were correctly skipped"
  - "make_docs_v7.py implemented as a thin importlib driver that loads export_to_markdown_v7.py as a module and calls its main() — export_to_markdown_v6.py (the V6 file this ports from) is itself directly runnable via its own __main__ block, so make_docs_v6.py in this repo does NOT actually drive DesignGrammar-V6.md generation (it generates a different pair of docs, ONTOLOGY-ALIGNMENT-V6.md/HIERARCHY-OPTIMIZATION-V6.md); make_docs_v7.py fills the role the plan's task 3 describes (a named, separate driver script for the DesignGrammar-V7.md docs) without hand-editing the generated markdown"
  - "Reification-class rename ObjectProperty->ObjProperty / DatatypeProperty->DataProperty was applied only inside the graph-layers table row's prose in export_to_markdown_v7.py (the row that describes the dg:Class/DataProperty/ObjProperty reification meta-schema) — the actual owl:ObjectProperty/owl:DatatypeProperty tag-matching code (lines checking `NS['owl']}ObjectProperty` / `DatatypeProperty`) is untouched since it matches the OWL 2 language construct, not DG domain content, and is generic (works against V7's already-renamed data automatically)"

requirements-completed: [ONTO-05]

coverage:
  - id: D1
    description: "apply_v7_extensions.py runs cleanly from ontology/, writes 3 -V7 extension owls, exits 0 with '[OK] extension/facade files clean'"
    requirement: "ONTO-05"
    verification:
      - kind: other
        ref: "cd ontology && python apply_v7_extensions.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "All three DesignGrammar-{BOT,Topologic,standards}-extension-V7.owl carry versionInfo 7.0, parse as well-formed XML, and owl:ObjectProperty/owl:DatatypeProperty construct counts are unchanged (8->8 in Topologic)"
    requirement: "ONTO-05"
    verification:
      - kind: other
        ref: "grep -L versionInfo>6.0 DesignGrammar-*-extension-V7.owl (no output = pass); python -c xml.dom.minidom.parse per file"
        status: pass
    human_judgment: false
  - id: D3
    description: "catalog-v001-V7.xml is well-formed XML; its 4 DG <uri> entries point at DesignGrammar-V7.owl + the three -extension-V7.owl files; the 7 external vocabulary imports are byte-identical to catalog-v001-V6.xml; catalog-v001-V6.xml is unmodified"
    requirement: "ONTO-05"
    verification:
      - kind: other
        ref: "python -c xml.dom.minidom.parse; grep -n uri= catalog-v001-V7.xml; git diff --stat catalog-v001-V6.xml (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "DesignGrammar-V7.md is regenerated from DesignGrammar-V7.owl via make_export_v7.py -> export_to_markdown_v7.py -> make_docs_v7.py, contains 0 occurrences of -V6 paths or versionInfo 6, and reflects the ObjState/ParamState/PropState trio plus rule-level SWRL/RuleName/RuleDescription"
    requirement: "ONTO-05"
    verification:
      - kind: other
        ref: "grep -c 'DesignGrammar-V6\\|<owl:versionInfo>6' DesignGrammar-V7.md (==0); grep -n ObjState/ParamState/PropState/RuleDescription DesignGrammar-V7.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "The full V7 bundle (DesignGrammar-V7.owl + 3 -extension-V7.owl + catalog-v001-V7.xml) parses as well-formed XML via stdlib xml.dom.minidom (the project's bespoke-parsing stance, no vendor OWL library) — the concrete stand-in for ROADMAP SC4"
    requirement: "ONTO-05"
    verification:
      - kind: other
        ref: "for f in DesignGrammar-V7.owl DesignGrammar-*-extension-V7.owl catalog-v001-V7.xml; do python -c xml.dom.minidom.parse; done — all printed OK"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-03
status: complete
---

# Phase 13 Plan 04: Ontology V7 Companion Artifacts Summary

**Ported the four `*_v6` generator scripts (`apply_v6_extensions.py`, `make_export_v6.py`, plus a new `make_docs_v7.py` driver) to `*_v7` equivalents, regenerating the three V7 extension/facade owls, `catalog-v001-V7.xml`, and `DesignGrammar-V7.md` — the complete V7 companion bundle now parses cleanly as well-formed XML, closing Phase 13's SC4 "load/parse without errors" criterion.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-03T02:00:00Z (approx)
- **Completed:** 2026-07-03T02:25:00Z
- **Tasks:** 4 (Task 4 was verification-only, no file changes / no commit)
- **Files modified:** 9 (all new)

## Accomplishments
- Wrote `ontology/apply_v7_extensions.py` mirroring `apply_v6_extensions.py`'s `check()`/banned-token-self-check pattern: BOT/Topologic extensions get only a version bump + prose `ComputationGraph`->`Computgraph` casing rename (both anchor on the unrenamed `dg:Topology`); the standards facade gets a blanket `ValidationRun`->`Run` rename plus the version bump. Ran the script — clean pass first try (`[OK] extension/facade files clean`), producing all 3 `-V7` extension owls with `versionInfo` 7.0 and `owl:ObjectProperty`/`owl:DatatypeProperty` OWL-construct counts exactly unchanged (8->8 verified in Topologic)
- Wrote `ontology/catalog-v001-V7.xml` by copying `catalog-v001-V6.xml`'s structure, retargeting the 4 DG `<uri>` entries (DG-core, DG-standards, DG-BOT, DG-Topologic) to the `-V7` physical files, keeping the 7 external vocabulary imports (BOT, SWRL, PROV-O, SOSA, SHACL, SKOS, DCTERMS, GEOSPARQL) byte-identical. Verified well-formed XML and confirmed `catalog-v001-V6.xml` untouched
- Wrote `ontology/make_export_v7.py` porting `make_export_v6.py`'s string-transform pattern against `export_to_markdown_v6.py`: `-V6` file paths -> `-V7`, `LAYER_NAMES` casing rename (Ontograph/Validgraph/Computgraph), the graph-layers table row's `DesignState{ObjectState,DefState}` -> `DesignState{ObjState,ParamState,PropState}` and `DatatypeProperty/ObjectProperty` -> `DataProperty/ObjProperty` reification rename, and the namespace-reference block's `OntoGraph` -> `Ontograph`. Ran it to produce `export_to_markdown_v7.py`
- Wrote `ontology/make_docs_v7.py` as a thin `importlib` driver invoking `export_to_markdown_v7.py`'s `main()` — a named, separate entry point per the plan's task 3, since (discovered during this task) the real `make_docs_v6.py` in this repo does not actually drive `DesignGrammar-V6.md` generation (it generates the unrelated `ONTOLOGY-ALIGNMENT-V6.md`/`HIERARCHY-OPTIMIZATION-V6.md` pair; `export_to_markdown_v6.py` is directly self-running via its own `__main__` block). Ran `make_docs_v7.py`, producing `DesignGrammar-V7.md` (1742 lines, 93,332 bytes) with zero `-V6` path or `versionInfo 6` residue, and confirmed the state trio (`ObjState`/`ParamState`/`PropState`) and rule-level `SWRL`/`RuleName`/`RuleDescription` properties render correctly (parsed generically from the already-renamed V7 owl content — no exporter code changes needed for those)
- Parse-checked the full V7 bundle (`DesignGrammar-V7.owl` + 3 `-extension-V7.owl` + `catalog-v001-V7.xml`) via stdlib `xml.dom.minidom` — all 5 files parse cleanly, matching the project's bespoke-parsing (no vendor OWL library) stance
- Confirmed all V6 sources (`DesignGrammar-V6.owl`, the 3 `-extension-V6.owl` files, `catalog-v001-V6.xml`) are byte-for-byte unmodified throughout (`git diff --stat` empty for all)

## Task Commits

Each task was committed atomically:

1. **Task 1: Port apply_v6_extensions.py to apply_v7_extensions.py and regenerate the 3 facades** - `efc8a33` (feat)
2. **Task 2: Write catalog-v001-V7.xml** - `120da9f` (feat)
3. **Task 3: Regenerate DesignGrammar-V7.md via make_export_v7.py / make_docs_v7.py** - `db14c21` (docs)
4. **Task 4: Parse-check the full V7 bundle** - verification-only, no file changes, no commit (results recorded above and in Coverage D5)

## Files Created/Modified
- `ontology/apply_v7_extensions.py` - V6->V7 extension/facade transform script (version bump + targeted renames + banned-token self-check)
- `ontology/DesignGrammar-BOT-extension-V7.owl` - BOT alignment facade, versionInfo 7.0
- `ontology/DesignGrammar-Topologic-extension-V7.owl` - Topologic alignment facade, versionInfo 7.0
- `ontology/DesignGrammar-standards-extension-V7.owl` - cross-vocab alignment facade, versionInfo 7.0, ValidationRun->Run
- `ontology/catalog-v001-V7.xml` - OASIS catalog mapping the V7 bundle's 4 DG IRIs + 7 external imports
- `ontology/make_export_v7.py` - generates export_to_markdown_v7.py from export_to_markdown_v6.py
- `ontology/export_to_markdown_v7.py` - generated V7 markdown exporter (generic OWL->markdown, self-runnable)
- `ontology/make_docs_v7.py` - named driver invoking export_to_markdown_v7.main()
- `ontology/DesignGrammar-V7.md` - regenerated human-readable V7 ontology docs (1742 lines)

## Decisions Made
- BOT/Topologic extensions required only a version bump + prose casing rename (no reification-class or ValidationGraph transform applies — confirmed absent via grep before writing the transform, per the task's own instruction)
- Standards facade's `ValidationRun`->`Run` rename implemented as a safe blanket `str.replace` (not entity-anchored) since "ValidationRun" is not a substring of any other token in that file (verified: `ValidationEntity` is a distinct, non-renamed token)
- `make_docs_v7.py` built as an `importlib`-based driver rather than a literal string-port of `make_docs_v6.py`, because the latter serves an unrelated purpose in this repo (see key-decisions in frontmatter) — this fulfills the plan's task 3 intent (a separate, named generator for `DesignGrammar-V7.md`) without hand-editing the generated markdown or inventing an inconsistent script

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] make_docs_v6.py does not generate DesignGrammar-V6.md**
- **Found during:** Task 3, before writing make_docs_v7.py
- **Issue:** The plan's task 3 action assumed `make_docs_v6.py` is the script that "invokes export_to_markdown_v6.py and writes DesignGrammar-V6.md" and instructed porting it 1:1. Reading `make_docs_v6.py` showed it actually generates a different, unrelated pair of docs (`ONTOLOGY-ALIGNMENT-V6.md`/`HIERARCHY-OPTIMIZATION-V6.md` via `common_renames()`/`insert_banner()` helpers specific to those two source files) — it has no knowledge of `export_to_markdown_v6.py` or `DesignGrammar-V6.md` at all. `export_to_markdown_v6.py` is itself directly runnable via its own `__main__` block and is what actually produces `DesignGrammar-V6.md` when invoked.
- **Fix:** Implemented `make_docs_v7.py` as a purpose-built `importlib` driver that loads `export_to_markdown_v7.py` as a module and calls its `main()`, fulfilling the plan's stated goal (a named, separate generator script for `DesignGrammar-V7.md`, never hand-editing the generated markdown) without literally porting the mismatched `make_docs_v6.py` content.
- **Files modified:** ontology/make_docs_v7.py (new file, written to match actual intent rather than the plan's literal-port instruction)
- **Verification:** `python make_docs_v7.py` successfully writes `DesignGrammar-V7.md`; content verified free of `-V6`/`versionInfo 6` residue and containing the state trio + rule-level properties
- **Committed in:** db14c21 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — plan's task description didn't match the actual repo file it referenced; fixed by implementing the described *behavior* rather than a literal port of the mismatched source)
**Impact on plan:** No scope creep — same deliverable (`DesignGrammar-V7.md` regenerated by a named driver script, `make_docs_v7.py`, per the `files_modified` frontmatter list) achieved via a script that matches the actual generator-of-a-generator pattern already established by `make_export_v6.py`/`export_to_markdown_v6.py`.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The full V7 ontology bundle (`DesignGrammar-V7.owl` + 3 extension facades + catalog + markdown docs) is generated, self-consistent, and parses cleanly — ready for Phase 14+ (graph schema v4 propagation) to consume as the locked reference
- `ontology/DesignGrammar-V7.md` gives Phase 14+ planning a human-readable, searchable rendering of every V7 class/property without needing to read raw OWL/XML
- No blockers identified for downstream plans

---
*Phase: 13-ontology-v7-and-contract-investigation*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: ontology/apply_v7_extensions.py
- FOUND: ontology/DesignGrammar-BOT-extension-V7.owl
- FOUND: ontology/DesignGrammar-Topologic-extension-V7.owl
- FOUND: ontology/DesignGrammar-standards-extension-V7.owl
- FOUND: ontology/catalog-v001-V7.xml
- FOUND: ontology/make_export_v7.py
- FOUND: ontology/export_to_markdown_v7.py
- FOUND: ontology/make_docs_v7.py
- FOUND: ontology/DesignGrammar-V7.md
- FOUND: .planning/phases/13-ontology-v7-and-contract-investigation/13-04-SUMMARY.md
- FOUND: commit efc8a33
- FOUND: commit 120da9f
- FOUND: commit db14c21
- FOUND: commit 12da6b0
