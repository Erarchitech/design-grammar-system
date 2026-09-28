---
tags: [decision, dsh, gsd, v12.0]
date: 2026-09-28
---

# Live-infrastructure GSD plans run by the orchestrator directly, never DSH

**Context:** Phase 1204's wave 1–2 plans (7 of 9) ran cleanly via DSH deepseek-v4-flash workers per the user's explicit directive. Wave 3 (plans 1204-08/09) required restarting the live Docker Compose stack across process lifetimes and making real, costed calls to an external LLM provider, with the provider API key entered only through the V2 UI settings panel (D-28).

**Decision:** Wave 3 was executed directly by the orchestrator session, never dispatched to a DSH worker.

**Why:**
- **Secrets.** CLAUDE.md's own DSH rule is explicit: never put `.secrets/` contents, API keys, or tokens into a worker brief. Plan 1204-09's D-28 requirement — the key must be decrypted only inside `data-service`'s own process via `resolve_active_provider`, never handled or printed by the executor — is exactly the kind of boundary a DSH worker (a separate process, own transcript, own potential logging) cannot be trusted to hold as reliably as the orchestrator's own `docker exec` script.
- **Real cost.** Each live run made tens of real, paid LLM calls. A DSH worker retrying blindly against TRANSPORT failures (the documented ~50% failure rate) could silently multiply that cost with no easy way for the orchestrator to audit exactly what was spent.
- **Irreversible side effects.** `docker compose restart`/`build --no-cache` and live provider calls are not idempotent, hard-to-undo actions on shared infrastructure — squarely in "confirm first, don't blindly delegate" territory.
- **Human checkpoints already gate this.** Both plans are `autonomous: false` with blocking owner checkpoints (Task 1 provider setup, Task 3/4 report review) — the orchestrator was already the party expected to interact with the owner directly; adding a DSH hop in between would only add a layer the owner can't see into.

**How to apply:** When a GSD phase mixes DSH-suitable subtasks (mechanical code/test generation) with live-infrastructure or secret-touching subtasks in the same phase, split them explicitly — DSH for the former, the orchestrator itself (with the harness's own `Bash`/`docker`/live-provider tooling) for the latter. Don't treat "the user asked for DSH" as blanket authorization once a plan's own frontmatter marks it `autonomous: false` with a human-action/human-verify checkpoint touching credentials or live systems.

**Related:** [[dsh-planning-worker-patterns]], [[knowledge/decisions/1204-09 scoped to rule-ingest only, recognition prompt construction deferred]]
