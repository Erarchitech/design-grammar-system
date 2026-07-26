---
phase: 35-llm-recognition-canvas-preview
plan: 12
subsystem: recognition-orchestrator
tags: [llm-gateway, pydantic, structured-output, guardrails, cg_topology, two-tier]

requires:
  - phase: 35-llm-recognition-canvas-preview
    plan: 06
    provides: cg_schemas.ProposedStructure + to_strict_json_schema
  - phase: 35-llm-recognition-canvas-preview
    plan: 07
    provides: llm_gateway.GenerationOptions + negotiate_structured_output + GenerateResponse.truncated/finish_reason
  - phase: 35-llm-recognition-canvas-preview
    plan: 08
    provides: prompts/recognition_system.md system prompt + counterexample few-shot fixture ({description, promptVersion, examples[]})
  - phase: 35-llm-recognition-canvas-preview
    plan: 10
    provides: cg_topology (scope_untagged/extract_features/classify/merge/output_token_budget) -- the Tier-0 deterministic layer
provides:
  - recognize_structure() rewired into a two-tier orchestrator -- Tier 0 (cg_topology) decides what it can with certainty, Tier 1 (LLM) sees only the residual over a real system+user prompt split
  - Four in-band guardrails (G6 unaddressed_candidate, G7 grammar_as_filter, G10 confidence floor, G11 flat-confidence flag) enforced inside the retry loop, closing the live UAT F1-F3 findings as invariants rather than known bugs
  - GRAMMAR_CITATION_PATTERNS as the single source of truth for the naming-grammar-citation detector, shared between the online G7 guard and the offline recognition_eval.scoring.grammar_citation_rate metric
  - POST /computgraph/recognize surfaces empty_procedure_scope as 422 and the new model-run outcomes (output_truncated, grammar_as_filter, provider_refusal) as 200/valid:false
affects: [35-13, 35-14, 35-15]

tech-stack:
  added: []
  patterns:
    - "System/user prompt split: role/task/grammar-anti-filter framing lives once in prompts/recognition_system.md (loaded via GenerateRequest.system); the user prompt carries only data (catalog, few-shot, tagged anchors, Tier-0 decisions, residual candidate features) -- stating the output contract in both halves was flagged as the real regression risk to avoid"
    - "Derived-feature candidate lines, never raw fields: widget=/in=/out=/group=/adj_proc=/name=/nick= replaces the old position-only line; position is the most seductive and least reliable classification signal (FM-1) and is never rendered"
    - "Tier-0 decisions rendered as an in-context worked example generated from the architect's own canvas -- free, and the strongest few-shot available since it is real evidence from this exact context"
    - "Guardrail asymmetry by design: G8/G9 block immediately with no retry (deterministic in the scope, retrying is pure waste); G6/G7 retry once/bounded then convert to an enforced action (auto-fill / block with diagnostic); G10/G11 never block, only demote/flag -- confidence signals are provisional, not gates"
    - "One shared pattern set for a detector that must never disagree with itself: GRAMMAR_CITATION_PATTERNS lives in production code (cg_recognition) and the offline eval metric (tests/recognition_eval/scoring.py) imports it, rather than each side maintaining its own regex/keyword copy"

key-files:
  created: []
  modified:
    - data-service/cg_recognition.py
    - data-service/tests/test_cg_recognition.py
    - data-service/tests/recognition_eval/scoring.py
    - data-service/app.py

key-decisions:
  - "validate_proposed_structure() left byte-for-byte unchanged and still runs POST-MERGE -- verified via git diff showing zero hunks inside its line range across all four tasks. Pydantic (cg_schemas.ProposedStructure) sits strictly BETWEEN _extract_json and it, never replacing its relational checks (tagged_overlap/duplicate_member/unknown_member_id), which are relations to the submitted context no JSON Schema can express."
  - "_filtered_untagged_node_ids/_filtered_untagged_groups (the F2 fail-open that turned a 14-node scoped call into a 214-node whole-canvas call) deleted entirely -- cg_topology.scope_untagged is now the only scope-resolution code path."
  - "G7's structural-signature check (0 proposals, >= 5 candidates) is checked BEFORE G6's unaddressed-candidate check in the loop: a systemic filter-reading failure is usually also why nothing was addressed, and G7's targeted prompt-version/provider diagnostic is more actionable than a generic unaddressed_candidate retry for the same root cause."
  - "G7's retry-once state (g7_already_retried) is a dedicated flag independent of the overall max_retries budget -- it must fire exactly once as a retry then block on the SECOND trigger, even if max_retries attempts remain, per the plan's 'the adapter is called exactly twice' acceptance bar."
  - "Per-attempt log records are JSON strings passed as the log message itself (not extra=), so every field (negotiated_mode, prompt_version, usage, etc.) is visible in captured log text -- an extra= dict would be invisible to a plain %(message)s formatter/caplog.text check."
  - "scoring.py's module docstring updated to distinguish the two directions: production importing eval code stays forbidden (corpus.py's freeze-protocol guard, unaffected); this module importing a production constant (test importing production) is the normal, sanctioned direction and is not what that guard was written to prevent."

requirements-completed: [RCGN-01, RCGN-04]

coverage:
  - id: D1
    description: "System prompt loaded from prompts/recognition_system.md and sent via GenerateRequest.system on every Tier-1 call; user prompt rewritten to derived candidate features + Tier-0 decisions block, never raw position"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestSystemPrompt and TestPrompt"
        status: pass
    human_judgment: false
  - id: D2
    description: "recognize_structure() is a two-tier orchestrator: Tier 0 decides with certainty and skips the LLM entirely when residual is empty (tier:'0'); empty_procedure_scope blocks with no LLM call; Tier-1 output is Pydantic-validated then merged with Tier-0 decisions before the unchanged validate_proposed_structure runs post-merge"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestTierZero and TestRetryLoop"
        status: pass
    human_judgment: false
  - id: D3
    description: "G6 unaddressed_candidate (retry then auto-fill+flag on the final attempt), G7 grammar_as_filter (retry once then block with a prompt-version/provider diagnostic), G10 confidence floor (demote, never block), G11 flat-confidence flag (never block) all enforced inside the Tier-1 loop; GRAMMAR_CITATION_PATTERNS shared with the offline eval metric"
    requirement: RCGN-04
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestGuardrails"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_recognition_scoring.py (unaffected; grammar_citation_rate now delegates to the shared pattern set)"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /computgraph/recognize maps empty_procedure_scope to 422 with an actionable message; output_truncated and grammar_as_filter stay HTTP 200 with valid:false so the caller can read attempts/violations alongside them; a Tier-0-only recognition returns 200 tier:'0' without invoking the adapter"
    requirement: RCGN-04
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRecognizeRoute"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-26
status: complete
---

# Phase 35 Plan 12: Two-Tier Recognition Orchestrator + Guardrails Summary

**Rewired `recognize_structure()` into a Tier-0 (deterministic topology)/Tier-1 (LLM) pipeline with a real system prompt, Pydantic-validated structured output, and four enforced in-band guardrails (G6/G7/G10/G11) closing UAT F1-F3.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 4
- **Files modified:** 4 (`data-service/cg_recognition.py`, `data-service/tests/test_cg_recognition.py`, `data-service/tests/recognition_eval/scoring.py`, `data-service/app.py`)

## Accomplishments

- `build_recognition_system_prompt()` loads `prompts/recognition_system.md` (front matter stripped, `PROMPT_VERSION` sourced from it), passed as `GenerateRequest.system` on every Tier-1 call for the first time -- the model was previously reverse-engineering role/task/grammar-anti-filter framing from a data dump.
- `_build_recognition_prompt()` rewired to the USER half only: derived candidate feature lines (`widget=`/`in=`/`out=`/`group=`/`adj_proc=`/`name=`/`nick=`, never `position=`), a Tier-0 decisions block as a free in-context worked example, and tagged-anchor summarization (full member list for the target procedure, one-line count for every other procedure).
- `recognize_structure()` runs Tier 0 first (`cg_topology.scope_untagged`/`extract_features`/`classify`): an empty procedure scope blocks immediately with no LLM call (G9); an empty residual returns `tier: "0"` and skips the LLM entirely.
- Tier 1 resolves provider/adapter/negotiated structured-output mode once, builds `GenerationOptions` pinned to `temperature=0.0` and `max_tokens` sized by `cg_topology.output_token_budget(residual)` (never the old hardcoded 4096), and calls `adapter.generate()` in-process every attempt -- never a re-POST to `/llm/generate`.
- `output_truncated` (G8) and `provider_refusal` block with no retry; `bad_json` and the new `cg_schemas.ProposedStructure`-backed `schema_violation` (dotted path) retry with corrective feedback.
- `cg_topology.merge()` composes Tier-0 decisions with Tier-1's proposals BEFORE the unchanged `validate_proposed_structure()` runs post-merge, so a Tier-1 proposal claiming a Tier-0-decided id survives into a `duplicate_member` violation instead of being silently dropped.
- G6 `unaddressed_candidate`: retries naming missing ids, then on the final attempt auto-fills them into `unrecognized[]` with reason `"not addressed by the model"` and flags `unaddressed_candidates_autofilled`.
- G7 `grammar_as_filter`: retries once with a targeted corrective message, then blocks with a diagnostic naming the prompt version and provider; triggers on a grammar-citing rationale OR the structural signature (0 proposals, >= 5 candidates). The keyword/regex pattern set (`GRAMMAR_CITATION_PATTERNS`) now lives in `cg_recognition` and `tests/recognition_eval/scoring.py` imports it, so the online guard and the offline SC1 metric can never disagree.
- G10 (`CONFIDENCE_FLOOR = 0.5`, labelled a provisional guess in code) demotes low-confidence proposals into `unrecognized[]`; G11 flags (never blocks) an uninformative flat confidence spread across >= 5 proposals.
- One structured, redacted per-attempt log record per Tier-1 call (`attempt`/`provider`/`model`/`negotiated_mode`/`prompt_version`/`temperature`/`max_tokens`/`usage`/`finish_reason`/`tier0_decided_count`/`tier1_residual_count`/`violation_codes`/`latency_ms`); never the prompt body or the API key.
- `POST /computgraph/recognize` stays a thin delegation; only `empty_procedure_scope` (a caller error) maps to 422, while `output_truncated`/`grammar_as_filter`/`provider_refusal` stay HTTP 200 with `valid: false` so `attempts`/`violations` reach the caller intact.

## Task Commits

Each task was committed atomically:

1. **Task 1: System prompt loader + prompt split with Tier-0 decisions and feature lines** - `e189fac` (feat)
2. **Task 2: Two-tier recognize_structure() with the Pydantic layer and post-merge validation** - `2de50f0` (feat)
3. **Task 3: Guardrails G6, G7, G10, G11 + redacted per-attempt logging** - `5e5ccf7` (feat)
4. **Task 4: Endpoint error surface for the new blocking violations** - `c5dac11` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `data-service/cg_recognition.py` - Two-tier orchestrator, system prompt loader, Tier-0/Tier-1 prompt assembly, Pydantic validation layer, four guardrails, per-attempt structured logging
- `data-service/tests/test_cg_recognition.py` - Extended (never rewritten): `TestSystemPrompt`, `TestTierZero`, `TestGuardrails`, `TestRecognizeRoute` classes added; `TestRetryLoop`/`TestPrompt`/`TestRecognitionProvenance` adapted to the new two-tier signatures
- `data-service/tests/recognition_eval/scoring.py` - `_cites_grammar` now delegates to `cg_recognition.GRAMMAR_CITATION_PATTERNS` instead of maintaining a second copy of the same regex/keyword set
- `data-service/app.py` - `post_computgraph_recognize` maps `empty_procedure_scope` to 422; docstring names the two-tier behaviour

## Decisions Made

See `key-decisions` in frontmatter above. Highlights: `validate_proposed_structure()` left byte-for-byte unchanged (verified via `git diff` showing zero hunks inside it across all four commits); `_filtered_untagged_node_ids`/`_filtered_untagged_groups` (the F2 fail-open) deleted entirely; G7 checked before G6 in the loop since a systemic filter-reading failure is usually also why nothing got addressed; G7's retry-once state is a dedicated flag independent of `max_retries`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Container image rebuild required before any verification**
- **Found during:** Task 1 verification
- **Issue:** `data-service`'s Docker image bakes in a `COPY . .` snapshot at build time (no bind mount for source), so the running container's `/app/cg_recognition.py` did not reflect any of this plan's edits until rebuilt.
- **Fix:** `docker compose build data-service && docker compose up -d data-service` run once per task before executing that task's `<verify>` pytest command (matches the existing STATE.md precedent from Phase 821 Plan 04, which hit the same issue).
- **Files modified:** none (infra-only, no source change)
- **Verification:** `docker compose exec -T data-service python -m pytest tests/ -q` passed after each rebuild
- **Committed in:** n/a (not a source change)

---

**Total deviations:** 1 auto-fixed (1 blocking/infra)
**Impact on plan:** No scope creep -- the rebuild is a verification-environment prerequisite, not a code change.

## Issues Encountered

- Existing `_cg_context()` test fixture's `n4` node (a `Line SDL` component) turns out to be Tier-0-decidable under R3 (clean sink, `group_member_count <= 1`, adjacent to exactly one tagged procedure) once the two-tier split landed -- several pre-existing tests assumed `n4` reached the LLM. Retargeted the fake-LLM fixtures at `n3` (the one node that genuinely abstains at Tier 0 in that fixture) and added an explicit comment in the test file documenting which fixture node lands where, so this doesn't surprise the next editor.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The two-tier orchestrator, guardrails, and system-prompt split are the exact configuration Plan 35-13 grades as arms A2 (system prompt) and A3 (+ Tier 0) against the recognition eval harness from Plan 35-11.
- `GRAMMAR_CITATION_PATTERNS` is now importable by the eval harness for the grammar-citation-rate metric, closing the "online guard vs. offline metric could disagree" gap flagged in this plan's decisions.
- No blockers for 35-13 (recognition eval harness run) or 35-14/35-15.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*

## Self-Check: PASSED

All key files (`data-service/cg_recognition.py`, `data-service/app.py`, `data-service/tests/test_cg_recognition.py`, `data-service/tests/recognition_eval/scoring.py`, this SUMMARY.md) confirmed present on disk. All four task commits (`e189fac`, `2de50f0`, `5e5ccf7`, `c5dac11`) confirmed present in `git log`.
