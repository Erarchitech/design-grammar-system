---
status: testing
phase: 01-cloud-llm-connector
source: [01-VERIFICATION.md]
started: 2026-07-06T23:45:00Z
updated: 2026-07-06T23:45:00Z
---

## Current Test

number: 1
name: End-to-end provider switching without restart
expected: |
  With the full Docker stack running (docker compose up -d), verify that switching
  the LLM provider in the UI Settings panel takes effect immediately:
  1. Open the LLM Settings page, configure and save an Anthropic API key
  2. Run a rules-ingest workflow — verify the gateway routes to Anthropic
  3. Switch to Ollama in the UI (change provider, save)
  4. Run the same workflow — verify the gateway now routes to Ollama (no restart)
  5. Verify the gateway's response format is always {text, provider, model, usage}
awaiting: user response

## Tests

### 1. End-to-end provider switching without restart
expected: |
  Provider switching in the UI takes immediate effect on subsequent /llm/generate
  calls from n8n workflows — no Docker restart, no workflow edits required.
  The mechanism is verified at the unit level (D-12 no caching, D-07 provider:null
  sent by n8n, resolve_active_provider() tested), but the live E2E flow
  (n8n -> gateway -> provider API -> response -> Neo4j) needs manual verification.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
