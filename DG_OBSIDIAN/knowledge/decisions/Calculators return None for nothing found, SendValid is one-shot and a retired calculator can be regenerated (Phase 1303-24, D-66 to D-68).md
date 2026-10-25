---
tags: [decision, phase-1303, property-calculator, run-property-check, d66, d67, d68]
date: 2026-10-25
---

# Calculators return None for nothing found; SendValid is one-shot; a retired calculator can be regenerated

Fixes for the findings of the live acceptance of plans 1303-18/23 (2026-10-25). Implemented by plan 1303-24; see [[sessions/2026-10-25 Phase 1303 plan 24 executed — no-data calculators, run check, regenerate retired, derived edges, rollout 23ed720]].

## D-66 — no data is `None`, never 0

A measured distance, clearance or size returns `None` when the elements to measure against do not exist; PROPERTY STATE skips the PropState, VALIDATOR resolves no value and reports `unknown` (spec/EVIDENCE-CONTRACT.md D-05). Counts keep returning 0. Enforced narrowly: `validate_function` refuses a constant zero returned inside `if <name> is None`; the rest rests on the prompt (CONTEXT_API). **Why:** `return 0.0` for "not found" read as the worst clearance and violated all 313 boxes. **How to apply:** a stored source with the old pattern now fails `verify_stored_source`, so it can neither be promoted nor reused; regenerate it (paid, confirmed flow).

## D-67 — one run, no blind retry, SendValid one-shot

`run_property_check` is sent once by data-service (503 `CANVAS_BUSY` on BUSY, 409 `SEND_VALID_ARMED` when the canvas already has SendValid on, then a poll on the listener's `solutionsEnded` counter). The listener waits 60 s for its UI hand-off, cancels a hand-off whose wait expired and does not read the canvas behind a long solution. `SendValidGuard` (DG.Core) switches SendValid off at the end of any solution that finds it on, also when set by hand. **Why:** BUSY retries queued further solutions and a SendValid left True published 50 runs in 54 minutes. **How to apply:** a hand publish is `SendValid` True, one F5, nothing else; a publish that needs SendValid across several solutions is not supported.

## D-68 — regenerate a retired calculator from the UI

`POST /scripts/property-calculators/regenerate` (member, editor): sets `regenerateRequested` on the retired project copy with the shown sha256; no LLM call, nothing deleted, the retired hash is not rejected. The Mapping panel shows "Regenerate with DG" on a retired card. D-60 is unchanged otherwise (no Reject on a retired copy).

## D-69

Derived Class -> Class edges in the Graph Viewer: see [[Graph Viewer draws class-to-class edges derived from ObjectProperty domain and range (Phase 1303)]].
