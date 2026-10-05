---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 08
subsystem: data-service-relay
tags: [llm-relay, sse-streaming, provider-export-policy, consent, provenance, cancellation, operational-outcomes, nginx, reproducibility, tdd]
requires: [1301-05]
provides:
  - "degram_relay.py: POST /degram/v1/chat/completions, delegated principal only, streams the operator-configured genpro endpoint (model mimo-v2.5-pro), server overrides model/stream, drops client provider, no fallback, no retry"
  - "Operator config store degram-llm.json (Fernet-encrypted key via llm_gateway helpers, atomic write, masked read); admin GET/PUT /degram/admin/llm-config"
  - "Provenance JSONL degram-llm-provenance.jsonl (requested/served model, response id, fingerprint, usage, outcome, user, company, project, contextScope, payloadBytes; no prompt text, no key)"
  - "degram_policy.py: deny-by-default per-project providerExportAllowed / wholeDefinitionAllowed store (degram-policy.json); admin GET/PUT /projects/{project}/degram-policy"
  - "Relay check order before any upstream contact: delegated principal + live scope, export policy, X-DeGram-Context-Scope, whole-definition policy then X-DeGram-Whole-Definition-Consent, 1 MiB body cap"
  - "Named operational outcomes (COMPLETED, CANCELLED, PROVIDER_TIMEOUT, PROVIDER_RATE_LIMITED, PROVIDER_UNAVAILABLE, PROVIDER_ERROR, RELAY_NOT_CONFIGURED, POLICY_DENY, CONSENT_REQUIRED + bridge and agent codes) as degram_relay.OPERATIONAL_OUTCOMES, disjoint from the eight evaluator statuses"
  - "spec/degram/OPERATIONAL-OUTCOMES.md with a machine-checked code block; nginx streaming location /data-service/degram/v1/; REPRODUCIBILITY call-site row degram_relay.py|relay_chat_completions"
affects: [1301-09, 1301-10, 1301-12, 1301-13, 1301-14]
tech-stack:
  added: []
  patterns:
    - "Module-level _transport_factory seam: tests inject httpx.MockTransport, production passes None (real network)"
    - "Prime the async generator before returning StreamingResponse so pre-stream failures are HTTP errors and post-stream failures are a final `event: degram-error` SSE event"
    - "Shielded anyio CancelScope around upstream close so a cancelled request still closes the provider stream and writes provenance"
key-files:
  created:
    - data-service/degram_relay.py
    - data-service/degram_policy.py
    - data-service/tests/test_degram_relay.py
    - data-service/tests/test_degram_policy.py
    - spec/degram/OPERATIONAL-OUTCOMES.md
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-08-SUMMARY.md
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_static_proxy_boundary.py
    - ui-v2/nginx.conf
    - spec/SECURITY-BOUNDARY.md
    - spec/REPRODUCIBILITY.md
    - spec/API.md
    - tools/de01/tests/test_reproducibility_scope_drift.py
key-decisions:
  - "The relay route policy is delegated-only with no project source: project, user and company come from the delegated principal, and the plan 05 live scope check (DELEGATED_SCOPE_CHANGED) runs inside require_principal before the handler"
  - "The two admin policy routes and the two admin config routes carry no project source (same reasoning as PUT /projects/{project}/company in plan 05: admin is owner everywhere and the cross-project matrix needs every scoped row to be member-authorizable)"
  - "A POLICY_DENY is terminal and checked before the consent header is read; the consent header accepts only `true` or `1`"
  - "The first-byte window covers connect + response headers + first SSE line, so a provider that accepts the connection but never speaks is a PROVIDER_TIMEOUT"
  - "Redirects are never followed (a redirect would carry the system key to another host); an upstream 3xx is PROVIDER_ERROR"
  - "stream_options.include_usage is NOT forced: usage in provenance is whatever the upstream volunteers (null otherwise)"
  - "Relay provenance is operational audit, not the D-19 reproducibility block; REPRODUCIBILITY.md says so explicitly and classes the call site not-reproducible-provider-managed"
metrics:
  duration: ~90 min
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-02, DGCL-05, DGCL-06, DGCL-07]  # server side of the relay only; client, agent wiring and live provider are later plans
status: complete
---

# Phase 1301 Plan 08: User-scoped streaming model relay Summary

DeGram now has exactly one model path: an OpenAI-compatible SSE relay that only a delegated user token can call, that sends the operator-configured model to the operator-configured endpoint, that is gated per project by a deny-by-default provider-export policy plus a whole-definition consent, that records provenance without prompt text or key, and that cancels and fails with named outcomes and never retries or falls back.

## What was built

**Task 1 (commit `66aab07`) tracer.** `degram_relay.py` holds the config store (`degram-llm.json`, key Fernet-encrypted with `LLM_MASTER_SECRET` through the `llm_gateway` helpers, atomic temp plus `os.replace`, chmod 600; `baseUrl` https or plain http only for localhost, no credentials/query/fragment; `model` defaults to `mimo-v2.5-pro`, `providerLabel` to `genpro`; an omitted field keeps its stored value; read returns a masked preview), `DegramRelayAdapter.stream_chat` (httpx `AsyncClient.stream` equivalent with `send(..., stream=True)`, Bearer key, server-set `model` and `stream: true`, client `tools`/`tool_choice` plus an allowlist of sampling fields, never `provider`), the `StreamCapture` that reads model/id/fingerprint/usage out of `data:` lines, and `relay_chat_completions` returning a `StreamingResponse` with the upstream lines forwarded verbatim. Routes `POST /degram/v1/chat/completions` (delegated), `GET`/`PUT /degram/admin/llm-config` (admin). Cookie sessions (admin included), connector and service principals get 403 `PRINCIPAL_NOT_PERMITTED`; unconfigured gives 503 `RELAY_NOT_CONFIGURED` before streaming.

**Task 2 (commit `e597784`) policy.** `degram_policy.py` stores `{providerExportAllowed, wholeDefinitionAllowed}` per project (`degram-policy.json`), false unless a stored value is literally boolean true (missing row, corrupt file, non-boolean value all deny). Admin `GET`/`PUT /projects/{project}/degram-policy` (strict booleans, at least one flag, project name validated). The relay checks in order and always before opening the upstream connection: export policy (403 `POLICY_DENY` reason `provider-export-not-allowed`), context scope header (`none|selection|whole-definition`, default `selection`, else 422 `CONTEXT_SCOPE_INVALID`), whole-definition policy (403 `POLICY_DENY` reason `whole-definition-not-allowed`), consent header (428 `CONSENT_REQUIRED`), body cap (`DEGRAM_RELAY_MAX_BODY_BYTES = 1048576`, 413 `RELAY_BODY_TOO_LARGE`, also from `Content-Length`). Consent can never override a deny. `contextScope` is in every provenance line.

**Task 3 (commit `55f026b`) cancellation and failures.** Between chunks the handler polls `request.is_disconnected()` and closes the upstream response (outcome `CANCELLED`, usage known so far kept); timeouts connect 10 s, first byte 60 s, total 300 s (module constants, call-time lookup); upstream 429 maps to `PROVIDER_RATE_LIMITED` (`retryAfter` seconds or null, `Retry-After` echoed), unreachable/5xx to `PROVIDER_UNAVAILABLE`, other non-2xx to `PROVIDER_ERROR` (`upstreamStatus`, key-scrubbed excerpt of at most 2 KiB), timeouts to `PROVIDER_TIMEOUT`; errors after streaming began are one final `event: degram-error`; exactly one upstream call per request. `OPERATIONAL_OUTCOMES` (relay + bridge + agent codes) is checked against `spec/evidence-contract.schema.json` `CanonicalStatus` for disjointness and against the machine-checked block in `spec/degram/OPERATIONAL-OUTCOMES.md` in both directions. `ui-v2/nginx.conf` gets `location /data-service/degram/v1/` (HTTP/1.1, `proxy_buffering off`, `proxy_read_timeout 330s` above the 300 s total, `client_max_body_size 1m`, no `add_header` so the server-level security headers are inherited); `/llm/` still proxies unchanged and never reaches the relay. The REPRODUCIBILITY scan rule and drift test now match `stream_chat` on adapter-named receivers; the block grew from seven to eight lines with `degram_relay.py|relay_chat_completions|model-dependent-unmeasured`.

## TDD

RED observed before implementation for every task: `test_degram_relay.py` stopped at collection with `ModuleNotFoundError: No module named 'degram_relay'` (task 1); `test_degram_policy.py` with `No module named 'degram_policy'` (task 2); task 3 showed 24 failing relay tests (no outcome mapping, no outcomes spec), 7 failing nginx boundary tests and 3 failing drift tests before the code and spec changes. GREEN afterwards. Each task is one commit (tests plus implementation), so there are no separate `test(...)` commits.

## Verification (host, Python 3.14.2; no Docker, no network, no real provider)

- Task 1: `test_degram_relay.py` + `test_route_inventory.py` + `test_security_boundary_spec.py` -> 797 passed.
- Task 2: policy, relay, inventory, boundary spec, cross-project matrix, delegated token -> 1837 passed.
- Task 3: relay, policy, static proxy boundary, reproducibility drift, boundary spec, route inventory, config.js, compose boundary -> 926 passed.
- Relay file: 58 tests (config, principals, happy path, provenance, policy/consent/scope denies with zero upstream requests, body cap, disconnect via raw ASGI, each timeout kind, 429, 5xx, 4xx, redirect, mid-stream error event, single call, no fallback, vocabulary).
- Full suite `python -m pytest data-service/tests -q -p no:cacheprovider`: **4639 passed, 35 skipped, 8 deselected, 6 failed, 25 errors** (277 s). All 31 are the documented environmental set: 25 errors in `test_cg_structure_checks.py` / `test_computgraph_consult.py` (the `neo4j` hostname does not resolve from the host), 4 failures in `test_dg_context.py` (same cause), 2 failures in `recognition_eval/test_repeat_sweep.py` (missing 1204 report, planning tree archived). Plan 05's 7th failure (a `git log` timeout in `test_recognition_eval.py`) did not recur. Nothing else failed: no regression.

## Deviations from Plan

### Auto-fixed Issues

None required fixing. Interpretations worth recording:

**1. [Plan interpretation] Provenance is written for every request that reaches the adapter, not for denies.** Policy, scope, consent, size and not-configured refusals never contact the provider and write no provenance line (they are visible as the 4xx/5xx the caller got). The plan says "every relayed request", and a request refused before the upstream is not relayed.

**2. [Plan interpretation] `degram_policy.py` carries its own small atomic-write helper** rather than importing the relay's, so the relay can import the policy module without a cycle. The duplicate is about fifteen lines.

**3. [Plan interpretation] Admin routes carry no project source.** `PUT`/`GET /projects/{project}/degram-policy` follow the plan 05 company-route precedent for the same cross-project-matrix reason; the handler validates the path value itself (`PROJECT_NAME_INVALID`).

**4. [Rule 2 - fail-closed additions]** Strict boolean parsing (`StrictBool`, so `"yes"` or `1` cannot enable export), key scrubbing in the upstream excerpt, `follow_redirects=False`, `Content-Length` early refusal, a `CONTEXT_SCOPE_INVALID` code, and a policy value check that treats anything but literal `true` as deny.

## Overlap with pre-existing uncommitted work

`data-service/auth.py` (the `os.replace` retry-loop hunk), `recognition_eval/*`, `test_auth_store.py`, `test_validation_run_immutability.py`, `spec/SWRL-SUBSET.md`, `tools/de01/tests/test_de01_runner.py` and the `ui-v2/src` and `ui-v2/tests` working-tree changes were present before this plan and were not touched or staged. Every file this plan edited was clean before the edit (checked with `git status`/`git diff --stat`), so each commit contains only this plan's hunks and no index blob surgery was needed. `apps/degram` and `apps/revit-mcp` gitlinks were not touched.

## Known Stubs

None. The relay is fully functional against any OpenAI-compatible endpoint; the only thing missing is the real operator configuration (endpoint and key), which is deliberately not part of the repository and is entered through `PUT /degram/admin/llm-config`.

## Unverified

- No live provider call, no real genpro endpoint, no real key (all forbidden here). The wire shape is OpenAI chat-completions streaming; whether genpro's `mimo-v2.5-pro` accepts every forwarded field (`tools`, `tool_choice`, the sampling allowlist) is unverified.
- Disconnect is tested on ASGI spec 2.4 (the relay's own `is_disconnected` poll). Under uvicorn's older spec Starlette instead cancels the response task on disconnect; the relay handles `CancelledError` and `GeneratorExit` (shielded upstream close plus provenance), but that path was not exercised live.
- nginx was not run (no nginx binary or Docker here); the new location is checked by the static brace-aware parser only. A live streaming check through `/data-service/degram/v1/` belongs to the owner's rebuild/deploy step. Compose/Docker was not rebuilt.
- The Windows `os.replace` retry loop in the config/policy writers is not exercised by a test.

## Threat Flags

None beyond the plan's register. T-1301-08-01 (deny-by-default policy before upstream, consent cannot override) and -06 (delegated-only, inventory sweeps) are covered by tests asserting zero upstream requests; -02 (key encrypted at rest, masked, absent from responses/provenance/excerpts) by the config, provenance and 4xx-excerpt tests; -03 (server overwrites model, single endpoint, no fallback) by the override and no-fallback tests; -04 (1 MiB cap, 300 s total, disconnect cancel) by the size, timeout and disconnect tests; -05 (provenance with user/project/company/outcome/sizes) by the provenance tests. New surface not in the register: the `degram-llm-provenance.jsonl` file grows without rotation (append-only by design); retention is an operator concern.

## Self-Check: PASSED

- FOUND: data-service/degram_relay.py, data-service/degram_policy.py, data-service/tests/test_degram_relay.py, data-service/tests/test_degram_policy.py, spec/degram/OPERATIONAL-OUTCOMES.md
- FOUND commits: 66aab07 (task 1), e597784 (task 2), 55f026b (task 3)
