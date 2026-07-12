---
phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring
plan: 01
subsystem: api
tags: [owlready2, fastapi, python, rdflib, hermit, dg-reasoner]

# Dependency graph
requires:
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    provides: reasoning.py's _reason_worker/run_consistency D-10 envelope and ontology_export.py's rdfs:label triple emission (L234-237)
provides:
  - "POST /reason/consistency unsatisfiable_classes elements are now {iri, label} dicts instead of bare IRI strings"
  - "_local_name(iri) pure helper for IRI-local-name fallback labels"
affects: [822-02, 822-03, 822-04, "phase 822 reasoner screen wiring (frontend consumes label field)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Label enrichment reads owlready2's in-memory Class.label (already populated by ontology_export.py's rdfs:label triples) inside the same reasoning subprocess — zero extra Neo4j round-trip"

key-files:
  created: []
  modified:
    - dg-reasoner/reasoning.py
    - dg-reasoner/tests/test_routes.py

key-decisions:
  - "_local_name splits on last '#' first, then last '/', else returns the IRI unchanged — guarantees a non-empty, non-http-prefixed fallback for every well-formed IRI"
  - "Label resolution order: first non-empty element of owlready2's Class.label list, else _local_name(iri) fallback — matches D-02's 'human label or local IRI name, never raw IRI' requirement"
  - "Entries are keyed and sorted by iri (dict-of-iri, then sorted list) to keep the same deterministic ordering guarantee the prior sorted-set-of-strings implementation had"

patterns-established:
  - "IRI-local-name pure helper pattern (_local_name) is available for reuse anywhere else in the sidecar that needs a display fallback for an unlabeled RDF resource"

requirements-completed: [REAS-06]

coverage:
  - id: D1
    description: "POST /reason/consistency returns unsatisfiable_classes as a list of {iri,label} dicts (empty list when consistent)"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_routes.py#test_unsatisfiable_classes_have_iri_and_label"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_routes.py#test_reason_consistency_returns_d10_contract"
        status: pass
    human_judgment: false
  - id: D2
    description: "_local_name resolves fragment-after-# or last-path-segment fallback and never returns a raw http IRI"
    requirement: "REAS-06"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_routes.py#test_local_name_fallback"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-12
status: complete
---

# Phase 822 Plan 01: OWL 2 DL Reasoning Integration — Unsatisfiable Class Label Enrichment Summary

**Enriched `POST /reason/consistency`'s `unsatisfiable_classes` from a bare IRI string list to `{iri, label}` dicts, with an in-process owlready2 `.label` read and a pure `_local_name` IRI-fragment fallback — zero new Neo4j round-trips.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-12 (session start)
- **Completed:** 2026-07-12
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `dg-reasoner/reasoning.py` now defines `_local_name(iri: str) -> str`, a pure helper returning the fragment after `#` (or last path segment, or the IRI unchanged) — never empty for a non-empty input.
- `_reason_worker`'s unsatisfiable-class collection now builds `{"iri": iri, "label": label}` dicts: `label` is the first non-empty element of the owlready2 `Class.label` list when present, else `_local_name(iri)`. `owl#Nothing` is still excluded; entries are deduplicated and sorted by `iri` for deterministic output.
- `run_consistency`'s pass-through required no change — it already forwards `result["unsatisfiable_classes"]` verbatim, which now carries the new dict shape; D-10 envelope keys (`consistent`, `axiom_counts`, `duration_ms`, `stripped_builtin_rules`) are untouched.
- TDD gate honored: Task 1 committed RED tests first (`_local_name` import error confirmed before implementation), Task 2 made them GREEN.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — failing tests for {iri,label} enrichment + local-name fallback** - `411e402` (test)
2. **Task 2: Enrich unsatisfiable_classes to {iri,label} with local-name fallback** - `22d2518` (feat)

**Plan metadata:** pending (this commit)

_Note: TDD task — test → feat, no refactor needed._

## Files Created/Modified
- `dg-reasoner/reasoning.py` - Added `_local_name` helper; `_reason_worker`'s unsatisfiable-class build now emits `{iri,label}` dicts instead of bare IRI strings
- `dg-reasoner/tests/test_routes.py` - Added `test_local_name_fallback` and `test_unsatisfiable_classes_have_iri_and_label`; updated `test_reason_consistency_returns_d10_contract`'s fake payload to the new element shape

## Decisions Made
- `_local_name` splits on `#` before `/` and falls back to the raw IRI only when neither delimiter exists (guarantees non-empty, non-`http`-prefixed output for well-formed IRIs) — per plan's `<behavior>` spec.
- Label resolution reads owlready2's `Class.label` defensively (coerce list-like to `list`, guard against empty/whitespace-only first element) before falling back to `_local_name` — matches RESEARCH.md Assumption A1 (owlready2 `.label` is list-like).
- Deduplication via `dict` keyed by `iri` before sorting preserves the previous implementation's dedup-by-iri behavior (owlready2 `inconsistent_classes()` can theoretically yield duplicates) while adding the label.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>` and `<acceptance_criteria>` blocks with no scope changes.

## Issues Encountered

None. RED test failure was the expected `ImportError: cannot import name '_local_name'` per the plan's `<verify>` expectation; GREEN run on the full `test_routes.py` file and the full `not integration` suite passed cleanly on the first attempt.

Note: this SUMMARY.md was reconstructed after the original was lost to a concurrent `git rebase` running on `master` from a separate session during this phase's execution; content is verbatim-identical to the original (verified against conversation history before the file was lost). Execution continued on an isolated branch (`gsd/phase-822-owl-2-dl-reasoning-integration-reasoner-screen-wiring`) to avoid a repeat collision. Commit hashes above reflect the rebase-rewritten SHAs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 (reasoner screen wiring) can now render `unsatisfiable_classes[].label` directly without any client-side IRI parsing — the sidecar guarantees a non-null, non-raw-IRI human label per D-02.
- No blockers for Plans 02–04; `dg-reasoner`'s unit tier (`pytest dg-reasoner/tests -m "not integration"`) remains green at 15/15.
- Manual/live sanity check (`curl .../reasoner/consistency`) was not run in this plan (docker stack not required for this unit-only plan per the plan's own scope) — deferred to whichever plan next exercises the live stack.

---
*Phase: 822-owl-2-dl-reasoning-integration-reasoner-screen-wiring*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: dg-reasoner/reasoning.py
- FOUND: dg-reasoner/tests/test_routes.py
- FOUND: 411e402 (test commit)
- FOUND: 22d2518 (feat commit)
