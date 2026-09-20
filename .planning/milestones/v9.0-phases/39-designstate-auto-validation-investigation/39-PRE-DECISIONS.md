# Phase 39 — Pre-Planning Decisions

**Captured:** 2026-07-27
**Source:** `/gsd-plan-phase 39` context gate (operator answers before exiting to discuss-phase)
**Status:** Input to `/gsd-discuss-phase 39` — NOT a GSD artifact, not CONTEXT.md

These two answers were given by the operator when `/gsd-plan-phase 39` hit the
missing-CONTEXT.md gate. The operator chose to run discuss-phase first; these are
recorded so discuss-phase does not re-litigate them.

## D-A: Prototype trigger path — **data-service watcher** (path b)

DSAV-02 requires a working prototype of at least one trigger path. The prototype
targets **path (b): a data-service watcher on DesignState writes** — data-service
observes DesignState/ValidationRun writes in Neo4j and fires the validation Run.

Rationale recorded at decision time:
- No live Rhino needed to verify the loop closes — avoids repeating the deferred
  in-Rhino UAT problem seen in Phase 33 plan 04 and Phase 824
- Testable inside the existing Docker compose network
- Lands on the existing FastAPI surface (`data-service/app.py`) rather than a new
  runtime dependency

Paths (a) GH capture-time hook and (c) Neo4j write-event trigger (APOC / CDC) are
still compared **on paper** for DSAV-01 — latency, publish-flood, Speckle-noise
analysis — but are not prototyped in this phase.

## D-B: Prototype depth — **spike quality, ADR-scoped**

The prototype proves the loop closes and that the guardrails work; it is not
production hardening.

- Guardrails must be **demonstrated in the prototype**, not merely described:
  debounce window, per-project rate limit, per-project opt-in flag
- Code lands behind an **off-by-default** per-project flag
- The ADR (DSAV-03) scopes hardening to a follow-up milestone
- Matches the ROADMAP "investigation" framing and the REQUIREMENTS out-of-scope
  note (`DesignState auto-validation full implementation | Investigation +
  prototype + ADR only`)

## Notes for the re-run of /gsd-plan-phase 39

- **Perplexity MCP is orchestrator-only.** The server is registered as `Perplexity`
  (capital P); `gsd-phase-researcher` is granted `mcp__perplexity__*` (lowercase)
  and cannot see it. If Perplexity-sourced research is wanted, the orchestrator
  must run the searches and seed them into RESEARCH.md — the researcher subagent
  cannot do it itself. Perplexity calls must also run **sequentially** (parallel
  calls crash the shared Chrome profile lock).
- UI gate returned `frontend: false` for this phase — no UI-SPEC needed, no
  `--skip-ui` required.
- Security contribution is active at ASVS L1, block on `high` — plans need a
  `<threat_model>` block. Relevant here: an auto-trigger is an unauthenticated
  write amplifier (DesignState write → validation Run → Speckle publish), so
  rate-limit bypass and publish-flood belong in the threat model.
