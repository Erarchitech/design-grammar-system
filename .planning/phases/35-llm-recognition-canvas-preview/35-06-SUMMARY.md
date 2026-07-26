---
phase: 35-llm-recognition-canvas-preview
plan: 06
subsystem: api
tags: [pydantic, json-schema, structured-output, constrained-decoding, recognition]

requires:
  - phase: 35-llm-recognition-canvas-preview
    provides: cg_recognition.ALLOWED_PROPOSAL_KINDS and validate_proposed_structure (relational safety)
provides:
  - data-service/cg_schemas.py — StructureProposal / UnrecognizedBlock / ProposedStructure Pydantic v2 models
  - to_strict_json_schema() — emitter for the restricted schema subset OpenAI-strict and Anthropic accept
  - pydantic>=2.7,<3 declared in requirements.txt (was imported but undeclared)
affects: [35-07, 35-10, 35-12, 35-13]

tech-stack:
  added: ["pydantic>=2.7,<3 (declared, already in-image at 2.13.4)"]
  patterns:
    - "Wire schema deliberately weaker than the validation model: strip what providers reject, re-enforce in model_validate()"
    - "Literal kind declarations + a set-equality test instead of a cross-module import, to avoid a circular dependency"

key-files:
  created:
    - data-service/cg_schemas.py
    - data-service/tests/test_cg_schemas.py
  modified:
    - data-service/requirements.txt

key-decisions:
  - "Proposal kinds declared literally in cg_schemas rather than imported from cg_recognition — the import would be circular once 35-12 wires them together. A test asserts set-equality with ALLOWED_PROPOSAL_KINDS so the two cannot drift"
  - "ProposalKind covers both short and long kind spellings, because ProposalDto.ToEntityTagKind accepts both and throws otherwise"
  - "to_strict_json_schema() emits a WEAKER schema than the model: confidence's [0,1] bound is stripped from the wire and still enforced by model_validate()"
  - "No relational validation in the schema — member-id existence, tagged overlap and duplicate claims are not expressible in JSON Schema and stay in validate_proposed_structure()"
  - "Field descriptions carry the grammar-anti-filter framing (UAT F3 root cause) into the one place a strict-mode model definitely reads"
  - "pydantic upper-bounded <3 to pin out a future FastAPI that ships Pydantic v3"

patterns-established:
  - "extra='forbid' on every recognition model so an unexpected field is a schema_violation naming the field, not silent data loss"

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "Typed output contract (StructureProposal / UnrecognizedBlock / ProposedStructure) with extra='forbid' and confidence bounded [0,1]"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_schemas.py — 25 new tests"
        status: pass
    human_judgment: false
  - id: D2
    description: "to_strict_json_schema() inlines $defs/$ref, forces additionalProperties:false and required==properties recursively, strips keywords neither OpenAI strict nor Anthropic accept"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_schemas.py — strict-schema emitter cases"
        status: pass
    human_judgment: false
  - id: D3
    description: "ProposalKind cannot drift from cg_recognition.ALLOWED_PROPOSAL_KINDS"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_schemas.py — set-equality assertion vs ALLOWED_PROPOSAL_KINDS"
        status: pass
    human_judgment: false
  - id: D4
    description: "pydantic declared in requirements.txt; full data-service suite green after the addition"
    verification:
      - kind: unit
        ref: "in-container pytest — 281 passed (was 256); test_cg_recognition + test_llm_gateway still 61"
        status: pass
    human_judgment: false

duration: unrecorded
completed: 2026-07-26
status: complete
---

# Phase 35-06: Recognition Output Contract Summary

**`cg_schemas.py` gives Tier 1 a Pydantic v2 output contract plus a strict-schema emitter, so provider-native constrained decoding can enforce the shape and the retry loop can name the offending field.**

## Performance

- **Tasks:** all tasks executed
- **Files created:** 2
- **Files modified:** 1
- **Commits:** 1

## Accomplishments

- **Typed output contract.** `StructureProposal` / `UnrecognizedBlock` / `ProposedStructure`, all `extra="forbid"`, `confidence` bounded `[0,1]`, and a `ProposalKind` covering both short and long kind spellings (because `ProposalDto.ToEntityTagKind` accepts both and throws otherwise).
- **Strict-schema emitter.** `to_strict_json_schema()` inlines `$defs`/`$ref`, forces `additionalProperties: false` and `required == properties` on every object recursively, and strips the keywords neither OpenAI strict nor Anthropic accept.
- **Carried the F3 fix into the schema itself.** Field descriptions embed the grammar-anti-filter framing — the one place a strict-mode model definitely reads.
- **Fixed an undeclared runtime dependency.** `llm_gateway.py:22` already imported pydantic directly while `requirements.txt` omitted it; this phase makes it load-bearing, so `pydantic>=2.7,<3` is now declared.

## Task Commits

1. **`cg_schemas.py` + strict-schema emitter + tests + requirements** — `5b9ac9d` (feat)

## Files Created/Modified

- `data-service/cg_schemas.py` (+220) — the models and `to_strict_json_schema()`
- `data-service/tests/test_cg_schemas.py` (+161) — 25 tests
- `data-service/requirements.txt` (+1) — `pydantic>=2.7,<3`

## Decisions Made

- **Literal kind declarations, not a cross-module import.** Importing from `cg_recognition` would create the circular import 35-12 introduces. A set-equality test against `ALLOWED_PROPOSAL_KINDS` makes drift a test failure instead of a runtime surprise.
- **The wire schema is deliberately weaker than the model.** `confidence`'s bound is stripped for the providers and re-enforced by `model_validate()`.
- **Relational validation stays out.** Member-id existence, tagged overlap and duplicate claims are not expressible in JSON Schema; they remain in `validate_proposed_structure()`. Pydantic guarantees the *shape*; that function keeps guaranteeing the *safety*.
- **Pydantic upper-bounded `<3`** to pin out a FastAPI that ships Pydantic v3.

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

None.

## User Setup Required

None — pydantic 2.13.4 was already present in-image; the declaration closes a latent gap rather than requiring an install.

## Next Phase Readiness

- 35-07 can accept an already-emitted schema dict without importing `cg_schemas` (dependency arrow stays recognition → gateway).
- 35-10 has the `StructureProposal` shape it emits Tier-0 decided rows in.
- 35-12 can wire strict-mode decoding and a field-naming `schema_violation` retry code.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*
*Summary reconstructed from commit 5b9ac9d during Wave 1 close-out (2026-07-26).*
