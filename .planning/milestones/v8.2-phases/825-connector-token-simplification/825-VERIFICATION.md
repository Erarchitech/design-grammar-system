---
phase: 825-connector-token-simplification
verified: 2026-07-13T00:00:00Z
status: human_needed
score: all code-level must-haves verified (data-service 23/23 + build 0/0 + DG.Tests 236/236); 3 phase success-criteria need in-Rhino UAT
behavior_unverified: 3
overrides_applied: 0
gaps: []
automated_verified:
  - "data-service: python -m pytest tests/test_connectors.py -q → 23/23 (4 new: project echo, default-project fallback, host-facing bundle, NEO4J_PUBLIC_URI env override). Full suite 168 pass; the 4 test_dg_context failures are pre-existing (need the Docker DG_KNOWLEDGE_REPO_ROOT mount) — confirmed identical on a clean tree via git stash."
  - "dotnet build DG/DG.sln -c Release → 0 warnings / 0 errors; DG.Grasshopper compiled against the real Rhino 8 SDK (GRASSHOPPER_SDK) incl. NonPersistentStringParam + new CONNECTOR GUID."
  - "dotnet test DG/tests/DG.Tests → 236/236 (2 new heartbeat-bundle tests). One re-run needed: the order-dependent E2E flake HappyPath_StatePublishAndRetrieve failed once then passed (documented in STATE.md)."
  - "Source assertions: SC-1 two-input registration (Token + Connect only); new GUID 3F9B1C7E-… literal; NonPersistentStringParam on Token (Write clears PersistentData); ADR-825-6 auth-gated connection (bolt attempted only when Outcome==Authenticated && Bundle present)."
behavior_unverified_items:
  - truth: "SC-4 — a valid project-scoped token authenticates and the CONNECTOR connects using the token-resolved bundle, emitting the bound Project"
    test: "Live Rhino: paste a dgc_ token bound to a project, Go=true (825-UAT Test 1)"
    expected: "Message 'Connected · Auth OK'; Project output = the bound project; Database = live connection"
    why_human: "The client bundle-parse + auth-gate are unit-proven, but the in-canvas bolt connect + output render need a live Rhino runtime (DG.Grasshopper is not in DG.Tests)."
  - truth: "SC-5 — invalid/revoked → Error, unreachable → Warning, missing token → Awaiting-token Warning; connection never attempted without a bundle"
    test: "825-UAT Test 2 (bogus token; data-service down; empty token)"
    expected: "red Error 'token rejected' / orange Warning 'could not reach' / orange Warning 'no platform token'; Database output not-connected"
    why_human: "Runtime message-bubble render requires a live Rhino session; message strings + gating are code-verified."
  - truth: "SC-6 — token typeable live, saved .gh has no dgc_, old 8-input canvas shows a placeholder"
    test: "825-UAT Test 3 (type token, save, grep .gh; open pre-825 canvas)"
    expected: "no dgc_ in saved .gh; field usable without per-solve scrub; old GUID → missing-component placeholder"
    why_human: "On-disk .gh inspection + GH serialization (NonPersistentStringParam.Write) require Rhino/Grasshopper."
human_verification:
  - test: "Two inputs only + valid token → Connected · Auth OK + bound Project (825-UAT Test 1)"
    expected: "exactly Token+Go inputs; Auth OK; Project from token"
    why_human: "No Rhino runtime + no DG.Grasshopper unit coverage"
  - test: "Failure feedback + auth-gated output (825-UAT Test 2)"
    expected: "Error/Warning bubbles; not-connected Database when auth fails"
    why_human: "Runtime bubble render needs live Rhino"
  - test: "Typeable, non-persistent token + old-canvas placeholder (825-UAT Test 3)"
    expected: "no dgc_ in saved .gh; old GUID canvas placeholders"
    why_human: "On-disk .gh + GH serialization need Rhino"
---

# Phase 825: CONNECTOR Token-Driven Simplification — Verification

## Status: human_needed

Code-complete and green on every automatable check. The CONNECTOR component now registers
**exactly two inputs (Token + Connect)**; a valid platform token is authenticated by
data-service, which returns the project scope + a host-facing Neo4j connection bundle
(`NEO4J_PUBLIC_URI`, default `bolt://localhost:7687`), and the component derives its whole
connection from that. The token is typeable live and scrubbed only at save
(`NonPersistentStringParam`). Backward compatibility was intentionally broken (new GUID,
user-approved 2026-07-13).

What remains is **in-Rhino acceptance** for SC-4/SC-5/SC-6 — the in-canvas connect, runtime
message bubbles, and on-disk `.gh` non-persistence can only be observed with a live
Rhino/Grasshopper session + running data-service. See `825-UAT.md`.
