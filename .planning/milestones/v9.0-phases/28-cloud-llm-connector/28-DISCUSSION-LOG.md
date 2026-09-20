# Phase 28: Cloud LLM Connector and Provider Abstraction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 28-cloud-llm-connector
**Areas discussed:** Provider adapter design, n8n→gateway wiring, UI settings panel, Model discovery

---

## Provider Adapter Design

| Option | Description | Selected |
|--------|-------------|----------|
| Thin normalization (Recommended) | Each adapter keeps provider-native format, standard response envelope | ✓ |
| Heavy normalization | Unified DG prompt format translated per adapter with cost estimates | |

**User's choice:** Thin normalization
**Notes:** The user agreed with the recommendation — adapters map each provider's native format behind a standard `{text, provider, model, usage}` envelope.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit provider tag (Recommended) | Request carries `provider: 'anthropic'` explicitly | ✓ |
| Auto-detect from model name | Gateway parses model prefix to infer provider | |

**User's choice:** Explicit provider tag
**Notes:** Clear and predictable routing — no fragile prefix parsing.

---

| Option | Description | Selected |
|--------|-------------|----------|
| API key only (Recommended) | Single `x-api-key` header | ✓ |
| API key + optional custom base URL | Also support proxy/compatibility layers | |

**User's choice:** API key only
**Notes:** Anthropic adapter keeps it simple — just an API key. Custom base URL can be added later if needed.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: text + provider + model + usage (Recommended) | Standard envelope only | ✓ |
| Extended: add stop_reason + cost_estimate + raw | Extra monitoring fields | |

**User's choice:** Minimal response
**Notes:** Start lean — extra fields can be added when a consumer genuinely needs them.

## n8n→Gateway Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Direct HTTP node (Recommended) | Each workflow POSTs to `http://data-service:8000/llm/generate` | ✓ |
| n8n middleware Function node | Shared function node pre/post processes requests | |

**User's choice:** Direct HTTP node
**Notes:** Keep n8n thin — the gateway owns all LLM logic.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Big-bang: all 5 together (Recommended) | Rewire all workflows in one coordinated change | ✓ |
| Staged: production first, spec workflows second | Two-phase migration | |

**User's choice:** Big-bang
**Notes:** The gateway is a drop-in replacement — one URL swap + body format change per workflow.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Gateway-only: honor active setting (Recommended) | n8n sends null provider/model, gateway resolves from saved settings | ✓ |
| Workflow-carried: n8n sends explicit provider | Each workflow overrides the active provider | |

**User's choice:** Gateway-only active setting
**Notes:** Switching providers in the UI takes effect immediately — no workflow edits needed.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Container-level health only (Recommended) | Docker health check for Ollama as before | ✓ |
| Gateway health endpoint | New `/health` endpoint checking active provider | |

**User's choice:** Container-level health only
**Notes:** Errors surface through the gateway response on the first call — no need for a separate health endpoint.

## UI Settings Panel

| Option | Description | Selected |
|--------|-------------|----------|
| New nav tab (Recommended) | Tab in sidebar alongside Register, Home, Project, Graph Viewer | ✓ |
| Modal from header gear icon | Gear icon in header opens modal | |
| Inline in Project page | Section within Project page | |

**User's choice:** New nav tab
**Notes:** Most discoverable location — LLM Settings becomes a top-level feature.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Full form + status banner (Recommended) | Same panel in both states — shows form with status banner when Ollama fallback is active | ✓ |
| Collapsed no-key, badge active | Single "Configure LLM…" button when no key, header badge when active | |

**User's choice:** Full form + status banner
**Notes:** Transparent about current provider state in both cases.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Test saved config only (Recommended) | Single "Test Connection" after save | ✓ |
| Test before save + test saved config | Test with a temporary key before persisting | |

**User's choice:** Test saved config only
**Notes:** Save first, then test — simpler UX.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Read from data-service every call (Recommended) | No caching — settings read on every `/llm/generate` | ✓ |
| Cache with invalidation on save | In-memory cache invalidated on settings save | |

**User's choice:** Read from data-service every call
**Notes:** Settings changes apply instantly without restart. The local data-service read adds negligible overhead vs an LLM call.

## Model Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| Static + Ollama dynamic | Hardcoded model lists per provider, Ollama from API | |
| Fully dynamic per provider | Query each provider's model listing API | ✓ |

**User's choice:** Fully dynamic per provider
**Notes:** Always up-to-date model lists. See D-14 for the seed-list approach to handle the no-key state.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Seed list + live refresh on test (Recommended) | Hardcoded fallback until first validated connection | ✓ |
| Empty until valid key, manual entry | No seed list — user must know model IDs | |
| Ollama always available, others populate after key | Hybrid approach | |

**User's choice:** Seed list + live refresh on test
**Notes:** Best UX — model dropdown works from the start, refreshes once a key is validated.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Plain model ID list (Recommended) | Just the model ID string in the dropdown | ✓ |
| Model ID + capability indicators | Show context window and tier with each model | |

**User's choice:** Plain model ID list
**Notes:** Clean and simple — model details are in provider documentation.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-discover from Ollama API (Recommended) | Call `http://ollama:11434/api/tags` at startup | ✓ |
| Static: fixed list | Just `llama3.1:latest` hardcoded | |

**User's choice:** Auto-discover from Ollama API
**Notes:** Users see their actual pulled models, not a fixed subset.

## Claude's Discretion

No areas deferred to Claude discretion — the user made explicit choices on every question.

## Deferred Ideas

None — discussion stayed within phase scope. The user's original research framing about generative scalability, parametric model parsing, and lessons-learned mechanisms maps to Phases 2+ and Phases 32-33 respectively, not Phase 28.

---

*Phase: 1-Cloud LLM Connector and Provider Abstraction*
*Discussion logged: 2026-07-03*
