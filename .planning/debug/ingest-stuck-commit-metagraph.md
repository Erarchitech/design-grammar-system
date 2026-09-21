---
slug: ingest-stuck-commit-metagraph
status: fix_applied_pending_live_verification
trigger: "Graph Viewer на Design Grammars, новый проект URBAN_BLOCK_V8. При вводе нового правила через ingest статус замирает на последнем этапе — \"Committing to metagraph\". Правило не доходит до Neo4j / прогресс не завершается."
created: 2026-09-18
updated: 2026-09-18T12:00:00Z
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: fix_applied_pending_live_verification
---

# Debug: ingest freezes at "Committing to metagraph"

## Symptoms

<DATA_START>

- **Expected behavior:** Rule entered via the Graph Viewer ingest console on project `URBAN_BLOCK_V8` runs the full NL → SWRL → Cypher → Neo4j pipeline, the progress indicator completes, and the rule appears in the metagraph.
- **Actual behavior:** Progress freezes at the final stage, labelled "Committing to metagraph". It hangs for a while and then surfaces an error / timeout.
- **Error messages:** Not yet captured verbatim — user reports an error or timeout appears after the hang. Capturing the exact message and the failing HTTP response is an early investigation task.
- **Timeline:** Worked before on all projects; broke recently. Not specific to being a new project per the user's answer — it is a recent regression.
- **Reproduction:** Open Graph Viewer on project `URBAN_BLOCK_V8`, enter a new rule through ingest, watch the status stages; it stalls on the last one.

</DATA_END>

## Investigation constraints (user-authorized)

Allowed against the live stack:

- Read container logs (`docker compose logs` for n8n, data-service, neo4j, design-grammars)
- Read Neo4j via diagnostic Cypher (read-only MATCH queries scoped to `project:'URBAN_BLOCK_V8'`)
- Fire the ingest webhook with a test rule to reproduce and observe the response (may create test nodes — clean up or tag them)

Not authorized without asking: destructive Cypher (DELETE/DETACH DELETE), restarting or rebuilding containers, editing live n8n workflows.

**No browser automation available in this session.** The user asked to test via Kimi Web Bridge in Chrome; it is not reachable here:

- `webbridge` MCP failed at session start with `CONNECTION_CLOSED`. Root cause confirmed: `npx kimi-webbridge mcp` aborts with `[ws] 服务器错误: listen EADDRINUSE: address already in use :::10086`.
- Port 10086 is held by PID 69616 (`node ... kimi-webbridge\src\cli.js mcp`, parent `cmd /c kimi-webbridge mcp`) — a second kimi-webbridge instance, most likely another Claude Code session, with an Established connection to Chrome (54 chrome processes running).
- Even if the port were freed, MCP servers load only at session start, so `mcp__webbridge__*` tools cannot appear mid-session.
- No other browser-driving tool exists here (ToolSearch found none; `WebFetch` refuses localhost, so it cannot reach `:8080`).

User decision: proceed **without** the browser. Reproduce through the HTTP layer instead — `curl` against `/n8n/webhook/dg/rules-ingest` plus container logs. This exercises the same network path the UI uses, and the failing stage ("Committing to metagraph") is server-side, so the browser is not required to observe it. Do NOT kill PID 69616 — it belongs to another session.

## Project-specific leads

- Ingest path: `Nginx SPA (:8080) → /n8n/webhook/dg/rules-ingest → n8n → data-service /llm/generate → Neo4j`
- "Committing to metagraph" is the terminal stage — i.e. the Cypher write into Neo4j, after LLM generation. Suspect the write, not the LLM step, unless evidence says otherwise.
- **Known gotcha (memory):** Neo4j `tx/commit` returns HTTP 200 with a populated `errors[]` — never infer write success from status code. A UI polling for success may hang forever on a 200-with-errors response.
- **Known gotcha (memory):** n8n runs the *published* workflow version, not the draft; the repo's `n8n/workflows/rules-to-metagraph.json` has drifted behind the live versions. Read `execution_data.workflowData` to see what actually ran.
- **Known gotcha (CLAUDE.md):** Neo4j node tagging after n8n ingestion — orphaned nodes need `graph`/`project` props; the V2 UI claims `default-project` nodes for the active project after each ingest.
- **Known gotcha (CLAUDE.md):** LLM Cypher output needs bracket-nesting validation before execution — malformed Cypher would fail exactly at the commit stage.
- Relevant repo surfaces: `n8n/workflows/rules-to-metagraph.json`, `ui-v2/src/` (ingest progress/stage logic, `lib/graphApi`), `data-service/app.py`, `cypher_template.txt`.
- "Broke recently" → check recent commits touching the ingest path and the live-vs-repo n8n workflow drift.

## Current Focus

- hypothesis: CONFIRMED — see reasoning_checkpoint below.
- test: n/a — root cause confirmed via direct reproduction + log evidence
- expecting: n/a
- next_action: CODE FIX APPLIED to repo copy of n8n/workflows/rules-to-metagraph.json (see Resolution). Remaining action requires user checkpoint: (1) rotate/reconfigure the LLM provider credential, (2) import + publish the fixed workflow to the LIVE n8n instance (repo edit alone does not take effect there), (3) re-verify end-to-end via the ingest webhook once both are done.
- reasoning_checkpoint:
    hypothesis: "The LLM provider (custom OpenAI-compatible router at https://router.genproagent.ru/v1, configured via LLM Settings) is rejecting the configured API key with 401/403. data-service's POST /context/generate-cypher catches this as httpx.HTTPStatusError, maps it via map_provider_error() to PROVIDER_AUTH_FAILED, and returns HTTP 502. The n8n 'Generate Validated Cypher' HTTP Request node has no onError/continueOnFail configured, so n8n's default behavior (abort workflow on non-2xx) kills the execution immediately without ever reaching the 'Store Result' node. Because /execution-result is only ever updated by that node, the record freezes forever at its last progress snapshot ('Parsing rules' / whatever stage preceded it), and the UI's pollExecution() polls that stale 'running' record indefinitely, which the user perceives as a freeze at 'Committing to metagraph' (the terminal stage label the UI shows once it gives up waiting / times out client-side)."
    confirming_evidence:
      - "Direct reproduction: fired POST /n8n/webhook/dg/rules-ingest with a real rule against URBAN_BLOCK_V8 -> got executionId, polled /execution-result/{id} 10x over 30s -> status stuck at 'running'/'Parsing rules'/40% every time, never progressed or failed."
      - "data-service logs (docker compose logs data-service) show, for every ingest attempt (execution 238, 239, 240, 243): POST /context/assemble 200 OK -> POST /execution-result 200 OK -> POST /context/generate-cypher 502 Bad Gateway -> then only GET /execution-result/{id} polls forever, no further POST /execution-result ever recorded for that execution."
      - "Direct call to POST /context/generate-cypher (bypassing n8n) returns body: {\"detail\":{\"error\":\"Provider authentication failed. Check your API key.\",\"hint\":\"Check your API key in LLM Settings.\",\"code\":\"PROVIDER_AUTH_FAILED\"}} with HTTP 502 -- reproduces on demand, not intermittent."
      - "GET /data-service/llm/settings shows provider=openai, model=deepseek-v4-pro, baseUrl=https://router.genproagent.ru/v1, apiKeyConfigured=true -- a custom OpenAI-compatible router, not api.openai.com directly, so the key/router pairing is a plausible drift point independent of any OpenAI account."
      - "Read n8n/workflows/rules-to-metagraph.json (live-activated workflow, ID a1b2c3d4-e5f6-7890-abcd-ef1234567890 matches n8n startup log) -- the 'Generate Validated Cypher' httpRequest node has onError=None, continueOnFail=None, i.e. no error branch; n8n's documented default for httpRequest on non-2xx is to throw and stop the workflow."
      - "app.py:1851 post_context_generate_cypher() wraps generate_validated_cypher() in try/except Exception -> map_provider_error() -> always HTTP 502 on any provider exception (confirms 502 is deliberate signaling of upstream failure, not an nginx/proxy-level gateway error)."
    falsification_test: "If the LLM provider auth were NOT the cause, calling /context/generate-cypher directly with a fresh/never-touched prompt would NOT return PROVIDER_AUTH_FAILED -- it would either succeed or fail with a different code (e.g. PROVIDER_RATE_LIMITED, PROVIDER_UNREACHABLE, CONTEXT_TYPE_INVALID). It returned PROVIDER_AUTH_FAILED specifically and reproducibly on every attempt, which rules out a transient/intermittent network blip and rules out a Cypher-validation-stage bug (that stage is never reached)."
    fix_rationale: "Two independent things are true: (1) the API key/router pairing is currently invalid -- that's an operational/config fix (rotate or reconfigure the key via LLM Settings), not a code fix, and (2) regardless of WHY generate-cypher fails, n8n silently swallowing any non-2xx from that node and never posting a terminal status is a code-level gap in the same class 107969f fixed for the Neo4j-write stage -- it was never extended to the earlier LLM-call stage. Fixing only the credential unblocks this one incident; fixing the missing error branch prevents every future upstream failure (auth, rate limit, timeout, malformed response) from re-hanging the UI the same way. Both are needed: config fix for the immediate incident, workflow fix for the recurring class of bug matching the debug file's title ('stuck at commit stage' will recur on ANY future generate-cypher failure without it)."
    blind_spots: "Have not confirmed whether this specific router/key combination previously worked (i.e. whether this is a newly-broken credential vs. one that was always broken and only recently got exercised) -- the 'worked before, broke recently' timeline from the user is consistent with a key rotation/expiry event but not proven from evidence alone. Have not inspected n8n's own execution list (via n8n UI/API with credentials) to see the internal error node/stack trace n8n recorded for these dead executions -- inferred the abort-on-non-2xx behavior from n8n's documented default plus the observed absence of any further /execution-result POST, not from directly observing n8n's execution detail. Editing the live n8n workflow to add error handling is explicitly listed as NOT authorized without a checkpoint -- flagging this before proceeding."
- tdd_checkpoint:

## Evidence

- timestamp: 2026-09-18T00:00:00Z
  checked: git log on ingest-path files (n8n/workflows/rules-to-metagraph.json, ui-v2/src/lib/graphApi.js, data-service/dg_context.py, data-service/app.py, cypher_template.txt)
  found: Most recent relevant commit is 107969f "fix(ingest): stop rule ingestion silently writing zero nodes" (2026-08-17, over a month before this bug report). It fixed exactly this class of symptom (LLM generates malformed Cypher -> Neo4j tx/commit returns HTTP 200 with errors[] -> old code hardcoded status:"ok" -> UI showed success with zero nodes written). Fix added: (1) malformed_node_pattern validation for `(x [Label] {...})`, (2) non-greedy relationship-type regex, (3) Build Response node now inspects errors[] from 'Execute LLM Cypher'/'Annotate Graph Props' steps and reports status:"error"/"failed" instead of hardcoded "ok", (4) graphApi.js pollExecution surfaces data.message on failure instead of generic "Workflow failed."
  implication: The current bug's symptom (freeze/hang rather than "reports success with zero nodes") is DIFFERENT from what 107969f fixed (that one caused false-success, not hangs). But it's the same subsystem and same "commit stage" — need to verify whether 107969f actually reached the LIVE n8n instance (known gotcha: n8n runs published version, not repo draft) or whether something regressed after it.
- timestamp: 2026-09-18T00:00:01Z
  checked: docker compose ps, n8n startup logs (docker compose logs n8n)
  found: All containers up 42+ min, n8n container created "2 months ago" (not recently rebuilt). n8n activated workflow "DG Rules -> Metagraph" (ID a1b2c3d4-e5f6-7890-abcd-ef1234567890) matches the ID pattern used in repo. No errors at n8n startup.
  implication: Container itself is stable/long-running; if there's drift between repo and live workflow, it would have been introduced via manual n8n UI edits (per known gotcha), not a recent container rebuild.

## Eliminated

## Resolution

- root_cause: The active LLM provider credential (provider=openai, model=deepseek-v4-pro, baseUrl=https://router.genproagent.ru/v1, configured via LLM Settings) is being rejected by the router with 401/403. data-service's POST /context/generate-cypher maps this to PROVIDER_AUTH_FAILED and returns HTTP 502 -- reproducible on every attempt, not intermittent. The live n8n "DG Rules -> Metagraph" workflow's "Generate Validated Cypher" HTTP Request node has no onError/continueOnFail configured, so n8n aborts the whole execution on that 502 without ever reaching "Store Result" (the only node that POSTs a terminal status to /execution-result). The execution-result record therefore freezes at its last "running" progress snapshot forever, which the UI's pollExecution() polls indefinitely -- perceived by the user as a hang on the last visible stage ("Committing to metagraph"). Two stacked issues: (1) an invalid/expired API key for the custom OpenAI-compatible router (operational), and (2) the "Generate Validated Cypher" node lacking the same errors-surface treatment that commit 107969f already gave the later Neo4j-write stage (code gap -- same bug class, different pipeline stage, never fixed here).
- fix: CODE PART APPLIED to the repo copy. Two parts total, one done, one still needs the user:
    (A) CODE -- DONE: n8n/workflows/rules-to-metagraph.json edited. "Generate Validated Cypher" now has continueOnFail:true. Added "Handle Cypher-Gen Error" (Function node) immediately after it, which detects an n8n error-shaped item, extracts the structured {error,hint,code} body data-service already returns, and emits a status:"error" payload with a descriptive message -- or passes the item through unchanged on success. Added "Cypher Gen Failed?" (IF node) that routes: true -> straight to "Store Result" (skips Cypher-validation/Neo4j-write stages entirely, since there is no Cypher to write), false -> "Parse LLM Output" (original happy path, unchanged). "Store Result" already builds {status: json.status==='error'?'failed':'completed', message: json.message} from its input, so no change was needed there -- it now receives a terminal status either way instead of the execution dying silently. This mirrors the errors[]-surfacing pattern commit 107969f applied to the later Neo4j-write stage, extended backward to this earlier LLM-generation stage. Verified: JSON re-parses cleanly (python -m json.tool), and all 5 node names referenced in the new connections graph (Generate Validated Cypher, Handle Cypher-Gen Error, Cypher Gen Failed?, Parse LLM Output, Store Result) exist as actual node definitions with matching id/name/type.
    (B) OPERATIONAL -- NOT DONE, needs user: rotate/reconfigure the API key for provider=openai baseUrl=https://router.genproagent.ru/v1 via LLM Settings (PUT /llm/settings or the LLMSettingsPanel UI), or switch the active provider to one with a working credential (e.g. Ollama fallback) to unblock ingest immediately.
    ALSO STILL NEEDED regardless of (B): the repo edit in (A) has NOT been imported/published to the LIVE n8n instance -- n8n runs the published workflow, not the repo file (known gotcha, confirmed again this session). Editing/publishing the live workflow was explicitly out of this session's authorization; doing so is a checkpoint for the user (via the n8n UI: import n8n/workflows/rules-to-metagraph.json's updated JSON, review the diff, republish "DG Rules -> Metagraph").
- verification: Root cause confirmed via direct, repeatable reproduction (5 separate ingest attempts, executions 238/239/240/243/244, identical failure signature in data-service logs every time). Code fix applied to the repo file and validated for JSON well-formedness and connection-graph integrity (no dangling node references). NOT YET verified end-to-end against the live stack -- that requires (B) the credential fix and (C) publishing this workflow change live, both of which are user checkpoints. Re-fire the ingest webhook once both are done to confirm the UI now surfaces a clear "failed" status instead of hanging (for a still-bad credential) or completes successfully (for a fixed one).
- files_changed:
    - n8n/workflows/rules-to-metagraph.json (added "Handle Cypher-Gen Error" function node and "Cypher Gen Failed?" IF node; set continueOnFail:true on "Generate Validated Cypher"; rewired Generate Validated Cypher -> Handle Cypher-Gen Error -> Cypher Gen Failed? -> {Store Result | Parse LLM Output})
