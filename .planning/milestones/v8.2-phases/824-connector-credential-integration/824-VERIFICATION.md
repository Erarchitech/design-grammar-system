---
phase: 824-connector-credential-integration
verified: 2026-07-12T00:00:00Z
status: human_needed
score: code-level must-haves all verified (build + 234 tests + source assertions); 3 phase success-criteria need in-Rhino UAT
behavior_unverified: 3
overrides_applied: 0
gaps: []
behavior_unverified_items:
  - truth: "Criterion 2 — a valid token minted from the v8.1 Connectors screen (Grasshopper connector) authenticates a heartbeat to data-service, observed end-to-end in the Grasshopper canvas"
    test: "In a live Rhino/Grasshopper session with data-service running, wire a Panel holding a real dgc_ token into CONNECTOR's Token input, set Connect=true, and observe the component"
    expected: "Component Message reads 'Connected · Auth OK'; no runtime Error/Warning bubble; data-service records the heartbeat (last_connection updates)"
    why_human: "The client outcome-matrix is unit-proven (Plan 01: 200→Authenticated with Bearer header + /connectors/heartbeat endpoint), but the DG.Grasshopper component is not compiled into DG.Tests and no Rhino runtime is available here — the actual in-canvas run → verdict has never been observed."
  - truth: "Criterion 3 — an invalid/revoked/expired token produces a clear in-canvas runtime Error (data-service unreachable → Warning), never a silent failure or crash, and never blocks the bolt output"
    test: "Wire a bogus token (e.g. 'dgc_revoked') and set Connect=true against a running data-service; then stop data-service and retry"
    expected: "Bogus token → red Error bubble 'CONNECTOR: platform token rejected…' + Message 'Connected · Auth failed', while the Database/Project outputs still populate; data-service down → orange Warning 'CONNECTOR: could not reach data-service at …'"
    why_human: "The outcome→AddRuntimeMessage mapping and the ungated outputs are code-proven (source assertions HEARTBEAT_WIRED_OK + OUTPUT_UNGATED_OK; message strings unit-tested), but the runtime message bubble rendering on the component requires a live Rhino session to observe."
  - truth: "Criterion 4 — the raw token is never persisted inside the .gh file (nor written to outputs/logs/status in plaintext)"
    test: "Type a token directly into the Token input (internalise), save the .gh, then open the saved .gh in a text/xml viewer and search for the dgc_ string; also confirm the internalise Remark fired"
    expected: "The saved .gh contains no dgc_ substring (ScrubTokenPersistentData cleared it); a Remark instructed wiring from a Panel; the Database output object carries no token"
    why_human: "All code paths that could persist the token are closed and asserted (token-free ConnectionInfo/HeartbeatResult, SHA-256-hashed dedup key, PersistentData.Clear()), but confirming an actual on-disk .gh has no dgc_ string is a manual save-and-inspect."
human_verification:
  - test: "Valid token → in-canvas Auth OK + data-service heartbeat recorded (824-UAT.md Test 1)"
    expected: "Message 'Connected · Auth OK', no error bubble, data-service last_connection updates"
    why_human: "No Rhino runtime + no DG.Grasshopper unit coverage; live E2E never observed"
  - test: "Invalid token → red Error bubble, outputs still populate; data-service down → orange Warning (824-UAT.md Test 2)"
    expected: "'platform token rejected' Error + 'Auth failed' with Database output still set; unreachable → Warning, never a crash/hang"
    why_human: "Runtime message-bubble render requires a live Rhino session; only the message strings + wiring are code-verified"
  - test: "Internalised token is scrubbed — saved .gh contains no dgc_ (824-UAT.md Test 3)"
    expected: "No dgc_ substring in the saved .gh; internalise Remark fired; old 6-input canvas opens without rewiring"
    why_human: "On-disk .gh inspection + old-canvas backward-compat opening require Rhino/Grasshopper"
automated_verified:
  - "dotnet test DG/tests/DG.Tests — 234/234 pass (incl. 6 heartbeat-client + 2 template facts)"
  - "dotnet build DG/DG.sln -c Release — 0 warnings / 0 errors, DG.Grasshopper compiled against the real Rhino 8 SDK (GRASSHOPPER_SDK defined)"
  - "Source assertions: INPUTS_OK (GUID 24E78A17… + additive DataServiceUrl/Token inputs, existing 0-5 preserved), HEARTBEAT_WIRED_OK (client + AddRuntimeMessage Error/Warning), SECRECY_OK (token-free ConnectionInfo, SHA-256 hashed key, PersistentData scrub), OUTPUT_UNGATED_OK (da.SetData outside the auth branch)"
---

# Phase 824: CONNECTOR Credential Integration — Verification

## Status: human_needed

The feature is **code-complete and fully green on every automatable check** — the full DG solution builds against the real Rhino/Grasshopper SDK, all 234 unit tests pass (including the heartbeat outcome matrix and the two new error templates), and every planned source assertion holds (additive inputs + unchanged GUID, heartbeat + Error/Warning wiring, token secrecy, and outputs that are never gated by auth).

What remains is **in-Rhino acceptance** for the three success criteria whose truth can only be observed with a live Rhino/Grasshopper session and a running `data-service` — the DG.Grasshopper component is deliberately excluded from the headless test project, so its runtime behavior (in-canvas heartbeat, runtime-message bubbles, and actual `.gh` on-disk non-persistence) has not been exercised here. See `824-UAT.md` for the three manual checks.

**Criterion 1 (additive input + GUID preserved)** is considered verified automatically: the GUID literal is unchanged, the two inputs are appended at indices 6–7 leaving 0–5 untouched, and the whole thing compiles against the GH SDK — the standard GH additive-param reconciliation guarantees saved canvases keep their wiring. A quick old-canvas open is folded into UAT Test 3 as a courtesy confirmation.
