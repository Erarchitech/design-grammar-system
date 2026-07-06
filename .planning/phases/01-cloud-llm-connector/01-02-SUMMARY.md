---
phase: 01-cloud-llm-connector
plan: 02
subsystem: n8n
tags:
  - n8n
  - gateway
  - rewiring
  - ollama
  - anthropic
  - openai
  - data-service

requires:
  - 01-01 (LLM Gateway endpoints + encryption)
provides:
  - All 5 n8n workflows rewired to POST /llm/generate instead of direct Ollama calls
  - Provider switching works via UI settings, no n8n workflow edits needed (D-07)
affects: []

tech-stack:
  added: []
  patterns:
    - Direct HTTP nodes call data-service gateway URL with provider:null, model:null contract
    - Response parsing reads $json.text from gateway envelope instead of $json.response
    - Dead ollama_url variables left as-is (no downstream consumers)

key-files:
  created: []
  modified:
    - n8n/workflows/rules-to-metagraph.json (URL, body, parse logic)
    - n8n/workflows/graph-query-mcp.json (2x URL, 2x body, 2x parse logic)
    - n8n/workflows/spec-ingest.json (URL, body, parse logic)
    - n8n/workflows/spec-query.json (URL, body, parse logic)
    - n8n/workflows/spec-update.json (URL, body, parse logic)

key-decisions:
  - "spec-query and graph-query-mcp generate-answer bodies reference upstream fields: .answerPrompt and .cypher_prompt respectively (not generic .prompt) — plan template referenced .prompt, corrected per actual workflow structure"
  - "ollama_url defaults in Set Input Defaults nodes changed to empty string to pass zero-ollama:11434 grep check"

requirements-completed:
  - LLMC-04
  - LLMC-05

duration: 8min
completed: 2026-07-06
status: complete
---

# Phase 01 Plan 02: n8n Workflow Rewiring — All 5 Workflows Rewired to LLM Gateway

**6 Ollama HTTP nodes across 5 n8n workflows rewired to `http://data-service:8000/llm/generate`. Zero remaining `ollama:11434` references. Response parsing reads from gateway envelope field `.text` instead of Ollama-specific `.response`.**

## Performance

- **Duration:** 8 min
- **Tasks:** 2
- **Files modified:** 5 (all modified, 0 created)
- **Nodes rewired:** 6 (2 in graph-query-mcp, 1 each in the other 4)
- **ollama:11434 refs eliminated:** 7 (5 HTTP URLs + 2 Set Input Defaults)

## Accomplishments

### Task 1: rules-to-metagraph.json and graph-query-mcp.json (4 nodes)

**rules-to-metagraph.json** (3 changes):
- "Ollama Generate" HTTP node: URL changed from `ollama_url/api/generate` to `http://data-service:8000/llm/generate`; body replaced with `{provider: null, model: null, prompt, system: null}` gateway contract
- "Parse LLM Output" Function node: `$json.response` to `$json.text` for both the primary extraction (`$json.text`) and the fallback object parsing (`raw.text`)

**graph-query-mcp.json** (6 changes):
- "Generate Cypher" HTTP node: URL + body swapped to gateway; body references `cypher_prompt` (upstream field name)
- "Generate Answer" HTTP node: URL + body swapped to gateway; body references `answer_prompt`
- "Parse Cypher" and "Parse Answer" Function nodes: `$json.response` to `$json.text` in both

### Task 2: spec-ingest.json, spec-query.json, spec-update.json (3 nodes)

**spec-ingest.json** (3 changes):
- "Ollama Generate" HTTP node: URL `http://ollama:11434/api/generate` to `http://data-service:8000/llm/generate`; body replaced with gateway contract
- "Parse LLM JSON" Function node: `$json.response` to `$json.text`

**spec-query.json** (3 changes):
- "Ollama Generate Answer" HTTP node: URL + body swapped; body references `answerPrompt`
- "Parse Answer" Function node: `$json.response` to `$json.text`

**spec-update.json** (3 changes):
- "Ollama Generate" HTTP node: URL + body swapped; body references `update_prompt`
- "Parse LLM Text" Set node: `$json.response` to `$json.text` in value expression

### Dead Variable Cleanup

The `ollama_url` default values in "Set Input Defaults" nodes (rules-to-metagraph.json and graph-query-mcp.json) contained `'http://ollama:11434'` as fallback strings. These were changed to empty string to achieve zero-ollama:11434 coverage across all 5 workflows. These variables have no downstream consumers since the HTTP nodes now use hardcoded gateway URLs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire rules-to-metagraph.json and graph-query-mcp.json (4 Ollama nodes)** — `da4a178` (feat)
2. **Task 2: Rewire spec-ingest.json, spec-query.json, and spec-update.json (2 Ollama nodes)** — `d2d1489` (feat)

## Files Modified

- `n8n/workflows/rules-to-metagraph.json` — URL + body + 2 response field refs in Parse LLM Output
- `n8n/workflows/graph-query-mcp.json` — 2x URL + 2x body + 2x response field refs in Parse Cypher and Parse Answer
- `n8n/workflows/spec-ingest.json` — URL + body + response field ref in Parse LLM JSON
- `n8n/workflows/spec-query.json` — URL + body + response field ref in Parse Answer
- `n8n/workflows/spec-update.json` — URL + body + response field ref in Parse LLM Text (Set node)

## Decisions Made

- **spec-query body field name:** The plan template references `$items("Build Answer Prompt")[0].json.prompt` for the gateway body's `prompt` field, but the upstream function node actually produces `answerPrompt`. Used `.answerPrompt` to match the actual field name.
- **graph-query-mcp generate-cypher body field name:** Same correction — upstream function produces `cypher_prompt`, not `prompt`. Used `.cypher_prompt`.
- **graph-query-mcp generate-answer body field name:** Same — `.answer_prompt` preserved as-is.
- **Set Input Defaults cleanup:** The plan action says "leave as dead variables" for `ollama_url` defaults, but the verify/acceptance criteria require zero `ollama:11434` matches. Cleaned up the default values to empty string (Rule 3 deviation — conflicting plan instructions, verify takes precedence).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] spec-query/graph-query body bodyParametersJson references wrong field name**
- **Found during:** Task 1
- **Issue:** Plan template specifies `$items("Build Cypher Prompt")[0].json.prompt` but the actual upstream field is `cypher_prompt` (graph-query-mcp Generate Cypher) and `answer_prompt` (Generate Answer). Similarly, spec-query references `.answerPrompt` not `.prompt`.
- **Fix:** Used `.cypher_prompt`, `.answer_prompt`, and `.answerPrompt` respectively to match actual workflow node outputs.
- **Files modified:** graph-query-mcp.json, spec-query.json
- **Commit:** `da4a178`

**2. [Rule 1 - Bug] rules-to-metagraph Parse LLM Output fallback path still reads `raw.response` instead of `raw.text`**
- **Found during:** Task 1 verification
- **Issue:** The `typeof raw.text === 'string'` check was correctly updated but the extraction inside the block still read `raw.response` instead of `raw.text`.
- **Fix:** Changed `cypherText = raw.response;` to `cypherText = raw.text;`
- **Files modified:** rules-to-metagraph.json
- **Commit:** `da4a178`

**3. [Rule 3 - Blocking] Set Input Defaults ollama_url defaults prevent zero-match verification**
- **Found during:** Task 1 verification
- **Issue:** Plan action says "leave as dead variables" but verify/acceptance criteria require zero `ollama:11434` matches. Dead variable defaults contain `'http://ollama:11434'`.
- **Fix:** Changed default values to empty string (no downstream consumers).
- **Files modified:** rules-to-metagraph.json, graph-query-mcp.json
- **Commit:** `da4a178`

## Threat Surface Scan

No new threat surface found. All changes are internal URL/body/response-field modifications to n8n workflow JSON files. The gateway contract follows T-02-01 (n8n may log request/response bodies, but gateway responses contain no credentials). No new network endpoints or auth paths introduced.

## Known Stubs

None identified. All workflows have functional HTTP nodes pointing to the live gateway endpoint.

## Verification Summary

| Check | Result |
|-------|--------|
| `grep -r "ollama:11434" n8n/workflows/ \| wc -l` | 0 |
| `grep -r "data-service:8000/llm/generate" n8n/workflows/ \| wc -l` | 6 |
| All 5 workflow files parseable JSON | PASS |
| `$json.response` references in n8n/workflows/ | 0 (all changed to `$json.text`) |
| Provider null, model null in each HTTP node body | PASS (6 of 6) |

## Self-Check: PASSED

All 5 modified files verified on disk. Both commits confirmed in git log. Zero `ollama:11434` references remain across all workflow files. Six `data-service:8000/llm/generate` references confirmed (correct count). All files are valid JSON. No `$json.response` references remain.
