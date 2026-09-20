---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 05
subsystem: api
tags: [n8n, workflow, cypher, context-assembly, spec-docs]

# Dependency graph
requires:
  - phase: 29-03
    provides: "POST /context/assemble + GET /context/debug (dg_context.assemble_context()) -- the endpoint this plan's n8n thin callers target"
  - phase: 29-04
    provides: "POST /context/generate-cypher (dg_context.generate_validated_cypher()) -- the endpoint this plan's n8n thin callers target for validated Cypher generation"
provides:
  - "n8n/workflows/rules-to-metagraph.json -- thin-caller reduction: Build LLM Prompt / Fetch Existing Entities / Parse LLM Output replaced by Assemble Context + Generate Validated Cypher HTTP nodes + thin join/extract nodes"
  - "n8n/workflows/graph-query-mcp.json -- thin-caller reduction: Fetch Graph Context (MCP) removed, Build Cypher Prompt / Parse Cypher replaced by Assemble Context + Generate Validated Cypher HTTP nodes + thin join/extract nodes"
  - "spec/DATABASE.md -- Cypher Expression Catalog section documenting the six-shape llm/cypher_catalog.json"
  - "Live n8n instance reconciled with repo JSON (Task 1 decision: reimport-repo-first) then re-synced with this plan's Task 2 edits -- zero live/repo drift remains"
affects: [31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "n8n prompt-construction nodes reduced to: (1) an HTTP Request node POSTing to /context/assemble with {type, project, rules_text|question}, (2) a thin Function node that string-joins the assembled context dict + minimal task framing into the final LLM prompt, (3) an HTTP Request node POSTing to /context/generate-cypher (never /llm/generate directly for Cypher-producing calls), (4) a thin Function node that extracts response.cypher or throws on {valid:false, violations}"
    - "graph_query's prompt now asks for raw Cypher text only (no JSON wrapper) to match validate_cypher()'s input contract -- the pre-Phase-29 'Return JSON only: {\"cypher\":...}' convention is retired for the LLM-facing prompt (the n8n->data-service transport is still JSON, only the LLM's own output contract changed)"
    - "n8n live-instance sync via PATCH /rest/workflows/{id} (not PUT -- this n8n install's REST API returns 404 on PUT and 200 on PATCH), authenticated via POST /rest/login using docker compose exec n8n printenv to read the live container's actual N8N_BASIC_AUTH_USER/PASSWORD (never grepping .env directly)"

key-files:
  created: []
  modified:
    - n8n/workflows/rules-to-metagraph.json
    - n8n/workflows/graph-query-mcp.json
    - spec/DATABASE.md

key-decisions:
  - "Task 1 checkpoint resolved by the user as reimport-repo-first: the live n8n instance (versionCounter 33, calling Ollama directly via {{ollama_url}}/api/generate, reading $json.response) was overwritten with the repo's pre-Task-2 rules-to-metagraph.json (Phase 28 LLM-gateway caller, project_name body-fallback fix, ignoreSslIssues) via PATCH /rest/workflows/{id} -- versionCounter advanced 33->34, active:true preserved, verified by re-fetch that Ollama Generate now calls http://data-service:8000/llm/generate"
  - "graph-query-mcp.json required zero live-sync action for Task 1 -- re-verified in this session (not just trusted from the prior investigation agent's findings) that all 17 nodes' parameters are byte-identical between live (versionCounter 36) and repo before any edit"
  - "Edit-mode detection in rules-to-metagraph.json's thin join node is now Rule_Id-mention-only (regex over rules_text), dropping the pre-Phase-29 'smart scoring against existing rule text' fallback -- dg_context.fetch_existing_entities() (29-03) only unions Class/DatatypeProperty/ObjectProperty entities, not Rule text, so that scoring path has no data source to read from post-thinning. Documented as a known limitation, not silently dropped."
  - "graph-query-mcp.json's 'Fetch Graph Context (MCP)' node (the live neo4j_schema MCP call) was removed as vestigial rather than left wired-but-unused -- its sole consumer (the old inline Build Cypher Prompt schema-listing logic) no longer exists post-thinning, and /context/assemble's fixed schema description supersedes its purpose. Not explicitly named in the plan's task text but consistent with the thin-caller reduction intent and PATTERNS.md's framing of the whole node body becoming an HTTP caller."
  - "Both workflows' 'Generate...' node (Ollama Generate / Generate Cypher) renamed to 'Generate Validated Cypher' for consistency, since it now calls /context/generate-cypher (which validates internally) rather than the raw /llm/generate passthrough"
  - "A light thin LIMIT-50 safety net was preserved in graph-query-mcp.json's Parse Cypher replacement (append 'LIMIT 50' if absent) -- this is a resource-bound guard, not schema/label Cypher validation, so it does not violate the acceptance criterion that no n8n Function node performs its own bracket-nesting/label-allow-list validation"

patterns-established:
  - "n8n workflow live-sync verification method: fetch both repo JSON and live workflow via authenticated GET, diff every node's `parameters` dict by name, assert zero differences and unchanged `active` state -- reusable for any future n8n workflow drift reconciliation in this project"

requirements-completed: [CTXA-01, CTXA-04]

coverage:
  - id: D1
    description: "Task 1 (blocking decision checkpoint) resolved: live n8n rules-to-metagraph.json instance reconciled with repo (reimport-repo-first), verified via re-fetch that the LLM-call node now targets the Phase 28 gateway instead of Ollama directly"
    requirement: "CTXA-01"
    verification:
      - kind: manual_procedural
        ref: "PATCH /rest/workflows/a1b2c3d4-e5f6-7890-abcd-ef1234567890 then GET re-fetch confirming Ollama Generate url == http://data-service:8000/llm/generate, versionCounter 33->34, active:true preserved"
        status: pass
    human_judgment: false
  - id: D2
    description: "rules-to-metagraph.json: Build LLM Prompt / Fetch Existing Entities / Parse LLM Output reduced to thin callers of /context/assemble + /context/generate-cypher; no inlined 4000-char prompt string remains"
    requirement: "CTXA-01"
    verification:
      - kind: other
        ref: "python -c json.load on both workflow JSONs (parses) + node-name/dangling-connection graph check (all connections resolve to existing node names)"
        status: pass
    human_judgment: false
  - id: D3
    description: "graph-query-mcp.json: Build Cypher Prompt / Smart Overrides (folded into Parse Cypher) reduced to thin callers of /context/assemble + /context/generate-cypher; raw-Cypher prompt contract matches validate_cypher()'s expected input"
    requirement: "CTXA-04"
    verification:
      - kind: other
        ref: "python -c json.load on graph-query-mcp.json (parses) + node-name/dangling-connection graph check"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both edited workflow JSONs pushed to and verified against the live n8n instance -- zero drift between repo and live post-edit"
    verification:
      - kind: manual_procedural
        ref: "PATCH /rest/workflows/{id} for both workflows, then independent GET re-fetch diffing every node's parameters dict by name -- zero diffs, both active:true, versionCounter 35 (rules) / 37 (query)"
        status: pass
    human_judgment: false
  - id: D5
    description: "spec/DATABASE.md documents the six-shape llm/cypher_catalog.json including the existence_count no-new-labels note; historical v3->v4 migration section preserved"
    requirement: "CTXA-01"
    verification:
      - kind: other
        ref: "python -c assert 'cypher_catalog.json' in DATABASE.md and 'existence_count' in DATABASE.md"
        status: pass
    human_judgment: false
  - id: D6
    description: "Manual E2E verification (Success Criterion 4): a natural-language graph query about design states answers correctly using v4 kind values with the context layer active, via the live reconciled n8n workflow"
    verification: []
    human_judgment: true
    rationale: "Requires a live end-to-end run through the actual n8n webhook -> data-service -> Neo4j -> LLM answer-synthesis pipeline with a real LLM provider configured; deferred to /gsd-verify-work per the plan's own <verification> section, which explicitly scopes this to that step."

duration: ~55min
completed: 2026-07-12
status: complete
---

# Phase 29 Plan 05: n8n Thin-Caller Reduction + Live Reconcile + Cypher Catalog Docs Summary

**Both n8n workflows (`rules-to-metagraph.json`, `graph-query-mcp.json`) reduced to thin HTTP callers of `/context/assemble` + `/context/generate-cypher`; the drifted live n8n instance was reconciled (repo-as-canonical) then re-synced with the thinned nodes; `spec/DATABASE.md` now documents the six-shape Cypher catalog**

## Performance

- **Duration:** ~55 min (continuation session: Task 1 checkpoint resolution + live push, Task 2 node edits + live push, Task 3 docs)
- **Completed:** 2026-07-12
- **Tasks:** 3 (1 checkpoint:decision resolved, 2 auto)
- **Files modified:** 3 (n8n/workflows/rules-to-metagraph.json, n8n/workflows/graph-query-mcp.json, spec/DATABASE.md)

## Accomplishments

- **Task 1 (checkpoint, resolved by user as `reimport-repo-first`):** Authenticated against the live n8n REST API (`POST /rest/login` using the container's actual `N8N_BASIC_AUTH_USER`/`PASSWORD`, read via `docker compose exec n8n printenv` rather than grepping `.env`). Confirmed the prior investigation agent's diff: live `rules-to-metagraph.json` (workflow id `a1b2c3d4-e5f6-7890-abcd-ef1234567890`, versionCounter 33) called Ollama directly (`{{ollama_url}}/api/generate`, read `$json.response`); repo already carried the Phase 28 LLM-gateway fix (`http://data-service:8000/llm/generate`, reads `$json.text`) plus the `project_name` body-fallback and `ignoreSslIssues` additions. Pushed the repo's pre-Task-2 content to live via `PATCH /rest/workflows/{id}` (this n8n install's REST API 404s on `PUT`, 200s on `PATCH`) -- versionCounter advanced 33->34, `active:true` preserved, re-fetch confirmed `Ollama Generate` now targets the gateway. Independently re-verified `graph-query-mcp.json` (workflow id `b2c3d4e5-f6a7-8901-bcde-f12345678901`, versionCounter 36) needed no action -- all 17 nodes' parameters byte-identical between live and repo.
- **Task 2:** `n8n/workflows/rules-to-metagraph.json` -- removed `Fetch Existing Entities` and `Compute Neo4j Auth` (live-entity union now happens inside `/context/assemble`); `Build LLM Prompt` reduced to an `Assemble Context` HTTP node (`POST /context/assemble` with `{type: "rule_ingest", project, rules_text}`) followed by a thin join node (edit-mode detection via `Rule_Id` regex mention only + JSON-stringified assembled context + existing-entities list + edit guidance, replacing the ~4000-char inline schema/few-shot string); `Ollama Generate` renamed `Generate Validated Cypher` and now calls `POST /context/generate-cypher`; `Parse LLM Output` reduced to extracting `response.cypher` (throwing on `{valid:false, violations}`) -- no more inline bracket-nesting/dedup JS.
- `n8n/workflows/graph-query-mcp.json` -- removed `Fetch Graph Context (MCP)` (the live `neo4j_schema` MCP call, now vestigial since `/context/assemble` supplies fixed schema context); `Build Cypher Prompt` reduced to an `Assemble Context` HTTP node (`{type: "graph_query", project, question}`) + a thin join node asking for **raw Cypher only** (no JSON wrapper -- matches `validate_cypher()`'s input contract, a necessary prompt-content change from the pre-Phase-29 `{"cypher":"..."}` convention); `Generate Cypher` renamed `Generate Validated Cypher` calling `POST /context/generate-cypher`; `Parse Cypher` reduced to extracting the validated cypher + a preserved `LIMIT 50` safety net (not itself schema validation) -- the old label/rel/prop allow-list regexes and ad hoc `$project` filter string-injection are gone, replaced by `validate_cypher()`'s `missing_project_key` check driving the bounded retry loop.
- Both workflow JSONs verified to parse (`python -c json.load`) and to have zero dangling node references in `connections` (every source/target name resolves to an existing node).
- Task 2 edits pushed to the live n8n instance (same `PATCH` method) and independently re-verified: both workflows' live `nodes[].parameters` are byte-identical to the repo JSON, `active:true` preserved on both, versionCounter 35 (rules) / 37 (query).
- **Task 3:** Added a "Cypher Expression Catalog" section to `spec/DATABASE.md` (inserted before the "v3→v4 Migration Notes" section, which is preserved unchanged) documenting all six `llm/cypher_catalog.json` shapes (`max_limit`, `min_limit`, `range`, `ratio`, `boolean_requirement`, `existence_count`) with their `Rule_Id` formats and semantics, explicitly noting `existence_count` -- the one genuinely new constraint family -- reuses only already-documented labels/relationships (no schema-shape change, no Schema Change Propagation required), and that `validate_cypher()` is the actual runtime enforcement point regardless of which catalog shape guided generation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reconcile live n8n workflow drift (checkpoint:decision, resolved `reimport-repo-first`)** -- no repo git commit (the change was pushed directly to the live n8n instance via its REST API; the repo JSON at that point already held the target content from a prior session, hence the reconcile push, not a git diff)
2. **Task 2: Reduce ingest + query prompt nodes to thin HTTP callers** -- `1c016ab` (feat)
3. **Task 3: Document the six-shape Cypher catalog in spec/DATABASE.md** -- `116847a` (docs)

**Plan metadata:** `commit_docs` is `false` in `.planning/config.json` for this project (same as Plans 29-01 through 29-04) -- the final metadata commit (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) is expected to skip via the SDK's `skipped_commit_docs_false` path.

## Files Created/Modified

- `n8n/workflows/rules-to-metagraph.json` -- `Assemble Context` (new HTTP node), `Build LLM Prompt` (thinned), `Generate Validated Cypher` (renamed + retargeted HTTP node), `Parse LLM Output` (thinned); `Fetch Existing Entities` + `Compute Neo4j Auth` removed
- `n8n/workflows/graph-query-mcp.json` -- `Assemble Context` (new HTTP node), `Build Cypher Prompt` (thinned), `Generate Validated Cypher` (renamed + retargeted HTTP node), `Parse Cypher` (thinned); `Fetch Graph Context (MCP)` removed
- `spec/DATABASE.md` -- new "Cypher Expression Catalog (`llm/cypher_catalog.json`)" section

## Decisions Made

See `key-decisions` in frontmatter above for the full list (Task 1 reconcile direction, edit-detection scope reduction, `Fetch Graph Context (MCP)` removal, node renames, preserved `LIMIT 50` guard).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] graph_query prompt changed from JSON-wrapped to raw-Cypher output**
- **Found during:** Task 2 (graph-query-mcp.json thinning)
- **Issue:** The pre-Phase-29 "Build Cypher Prompt" asked the LLM to `Return JSON only: {"cypher":"..."}`. `POST /context/generate-cypher`'s `generate_validated_cypher()` (Plan 29-04) validates `response.text` directly as raw Cypher via `validate_cypher()` -- it does not unwrap a JSON envelope. Routing the old JSON-wrapped prompt through the new endpoint would cause every attempt to fail `has_valid_nesting()`/label extraction against a JSON string, exhausting all 3 retries every time.
- **Fix:** Rewrote the join-node prompt to explicitly request raw Cypher text only (`"Output Cypher only -- no JSON, no markdown fences, no commentary."`), matching `rule_ingest`'s existing raw-Cypher convention and `validate_cypher()`'s actual input contract.
- **Files modified:** n8n/workflows/graph-query-mcp.json
- **Verification:** Traced `dg_context.generate_validated_cypher()` and `validate_cypher()` source directly -- confirmed no JSON-unwrapping step exists; the fix aligns the prompt contract with the endpoint's actual expectation.
- **Committed in:** 1c016ab (Task 2 commit)

**2. [Rule 3 - Blocking] `Fetch Graph Context (MCP)` removed as vestigial dead code**
- **Found during:** Task 2 (graph-query-mcp.json thinning)
- **Issue:** This node's sole purpose was feeding live-schema data (labels/rels/props/graphs/projects) into the old inline "Build Cypher Prompt" JS. Once that JS is replaced by an `/context/assemble` HTTP call (which supplies its own fixed schema description), the node's output is never consumed by anything -- it would silently execute a redundant live query every request with zero effect on behavior.
- **Fix:** Removed the node and rewired `Mark Running -> Assemble Context` directly.
- **Files modified:** n8n/workflows/graph-query-mcp.json
- **Verification:** Confirmed via the node-name/connection graph check that no dangling references resulted; the plan's read_first/acceptance criteria did not explicitly require this removal, but it is consistent with PATTERNS.md's framing that "the remaining n8n node body becomes an HTTP Request node."
- **Committed in:** 1c016ab (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug-prevention prompt-contract fix, 1 blocking/vestigial-code cleanup)
**Impact on plan:** Both changes were necessary for the thinned workflow to actually function against the new endpoints as designed; neither introduces new scope beyond what Task 2's own acceptance criteria already required (a working thin-caller reduction).

## Known Limitations (not deviations -- inherent to prior-plan scope)

- **Edit-mode "smart scoring" detection is gone.** The pre-Phase-29 `Build LLM Prompt` node scored prompt keywords against **existing Rule text** to infer which rule an ambiguous edit request targeted, when no explicit `Rule_Id` was mentioned. `dg_context.fetch_existing_entities()` (Plan 29-03) -- which now backs `/context/assemble`'s `existing_entities` field -- only unions `Class`/`DatatypeProperty`/`ObjectProperty` entities, not Rule text. Post-thinning, edit-mode detection in both workflows' join nodes is Rule_Id-mention-only (regex over the raw input text). This is a real capability reduction versus pre-Phase-29 behavior, but it is not something this plan's scope (n8n workflow JSON + `spec/DATABASE.md` only, per frontmatter `files_modified`) can fix -- doing so would require modifying `data-service/dg_context.py`'s already-shipped, tested `fetch_existing_entities()` (Plan 29-03), which is out of this plan's file scope. Flagging for a future plan if smart edit-detection needs restoring.

## Issues Encountered

None blocking. The n8n REST API's `PUT /rest/workflows/{id}` returned a bare `404` (not JSON) on this n8n install (v2.4.8); `PATCH` on the same path returned `200` with the full updated workflow body. Discovered by trying both methods directly rather than assuming REST convention -- no retry loop needed once `PATCH` was confirmed to work.

## User Setup Required

None -- no external service configuration required. The live n8n reconcile and re-sync were performed via the already-running `n8n` container's REST API using its existing `N8N_BASIC_AUTH_USER`/`PASSWORD` (read from the running container, not the `.env` file directly, per the sandbox's file-access policy).

## Next Phase Readiness

- Phase 29 (DG-Aware Context Layer) is now complete end-to-end: `/context/assemble` (29-03) + `/context/generate-cypher` (29-04) are live, tested, and now actually called by both n8n workflows in production (not just available as unused endpoints) -- both live and repo are in sync.
- A schema change to the six-shape Cypher catalog is now a `llm/cypher_catalog.json` + `data-service/dg_context.py` edit only -- no n8n Function-node JS string needs touching, fulfilling this plan's stated purpose.
- **Deferred to `/gsd-verify-work`:** Success Criterion 4 (a live natural-language graph query about design states answering correctly using v4 `kind` values with the context layer active) requires an actual LLM provider configured and a live end-to-end webhook run -- not exercised in this session beyond the static JSON/connection-graph checks and the live-sync parameter-diff verification.
- **Known limitation carried forward:** rule-edit "smart scoring" against existing Rule text is gone (see above) -- worth a follow-up plan if edit-mode UX regresses noticeably in practice.
- Phase 31 (RING-02 atom-level diff-preview) can build on the now-frozen `rule_edit` convention (29-03) and the validated-Cypher contract this plan wires n8n to use end-to-end.
- No blockers.

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: n8n/workflows/rules-to-metagraph.json
- FOUND: n8n/workflows/graph-query-mcp.json
- FOUND: spec/DATABASE.md
- FOUND: .planning/milestones/v9.0-phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/29-05-SUMMARY.md
- FOUND: 1c016ab (Task 2 commit)
- FOUND: 116847a (Task 3 commit)
- CONFIRMED: both workflow JSONs parse and have zero dangling connection references
- CONFIRMED: live n8n instance re-fetched independently -- both workflows' node parameters byte-identical to repo JSON, active:true preserved, versionCounter 35 (rules-to-metagraph) / 37 (graph-query-mcp)
