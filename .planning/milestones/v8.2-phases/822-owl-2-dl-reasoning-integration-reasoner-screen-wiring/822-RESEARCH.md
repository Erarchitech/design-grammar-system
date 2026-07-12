# Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring - Research

**Researched:** 2026-07-12
**Domain:** React state-machine wiring to an already-shipped FastAPI proxy + OWL reasoner sidecar
**Confidence:** HIGH (all core claims verified directly against committed source and a live, running docker stack — not from training-data assumptions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Result Presentation**
- **D-01:** The result renders by expanding the HermiT card itself — replacing the "Selected — will be used when integration is complete" / "Integration pending" area with the live verdict. Result stays visually bound to the engine that produced it. Reuse the existing screen card / `dg-frost` styling; no modal, no separate route.
- **D-02:** On an inconsistent verdict, show the unsatisfiable-class count (criterion 2's hard requirement) plus a list of the classes by their human-readable label — the OntoGraph `Class.label` property, falling back to the local IRI name only when no label exists. Never surface raw full IRIs to the architect (keeps the Phase 823 "no raw RDF vocabulary" principle).
- **D-03:** The verdict is explicitly labeled "schema consistency" (not "validation"/"compliance") so it is never confused with a design-compliance result (criterion 2).

**Run Trigger & Card State**
- **D-04:** Per-card Run button on HermiT only. The HermiT card gains a Run check button and drops its "Integration pending" badge — it becomes the one live/integrated engine (criterion 1). Pellet keeps its placeholder badge and has no run button.
- **D-05:** The run always forces `engine: "hermit"` and targets the active project (the `project` prop already passed into `ReasonerScreen`). The request payload is `{"project": <active>, "engine": "hermit"}` per the Phase 821 contract (D-10).
- **D-06:** The existing reasoner-selection behavior (persisting selection via `PUT /reasoner/settings`) stays; selecting Pellet must not offer a way to run it.

**In-Progress, Timeout & Verdict States**
- **D-07:** While a check runs, the HermiT card shows a spinner + a live elapsed-seconds counter; the Run button is disabled, and a Cancel button aborts the fetch client-side via `AbortController`. (Aborting the client wait does not necessarily stop the server run — that's acceptable.)
- **D-08:** Four distinct verdict states, each with its own visual treatment: Consistent (positive/"ok"), Inconsistent (signal/red + D-02 unsat count & labeled list), Unknown (neutral/amber "timed out — result inconclusive", distinct from a real fail, triggered by the sidecar's server-side timeout response per Phase 821 D-09, ~60–120s), Cancelled (quiet/gray "you stopped this run — no result", kept separate from Unknown so a user-initiated stop is never read as a reasoner verdict).
- **D-09:** Transport/hard errors (sidecar unreachable, 5xx, malformed body) surface as a distinct error line — reuse the screen's existing error-message pattern (the `loadError`/`saveError` `--color-signal` line) — and are not folded into the semantic "Unknown" verdict.

**Result Freshness & Re-run**
- **D-10:** Each run is a fresh `POST` (browsers don't cache POST), so the sidecar re-reads live Neo4j every time — satisfying criterion 4 by construction, no cache-busting needed.
- **D-11:** Show a "Last checked: <relative time>" timestamp with each result. The result persists in-memory across screen revisits within the session (component/app state), so returning to the screen shows the last verdict rather than a blank card.
- **D-12:** No active staleness detection. We do not compare axiom counts / export hashes to warn "ontology changed." The timestamp lets the architect judge freshness and re-run at will.

**Reachability (settled default — not discussed)**
- **D-13:** The UI reaches the sidecar through the existing data-service proxy at `/reasoner/consistency` (built by Phase 821 D-06). nginx already routes `/reasoner/` → data-service and the vite dev proxy forwards `/reasoner`, so no new nginx route or vite-proxy entry is needed. `reasonerApi.js` gains a `runConsistencyCheck(project, { signal })` function posting to `/reasoner/consistency`.

### Claude's Discretion
- Exact copy/wording of each verdict, the "schema consistency" label, the placeholder disclaimer note, and the Cancel/error messages.
- Spinner/elapsed-counter styling and the amber/red/green/gray color mapping (pull from existing tokens: `--color-signal`, `--color-accent`, `--text-muted`, etc. — NOTE: this research + UI-SPEC.md found `--color-accent` is a phantom/undefined token; use `--accent-selection`/`--accent-selection-bg` instead, see Code Examples).
- Elapsed-timer tick interval and relative-time formatting for "Last checked".
- **IRI→label resolution location (flagged for research — resolved below):** the Phase 821 `/reason/consistency` response returns `unsatisfiable_classes` (shape was unspecified in the 821 contract at CONTEXT-gathering time, confirmed by this research to currently be a flat IRI-string list). D-02 needs human labels. This research's recommendation (sidecar-side enrichment) is in the Summary and Architecture Patterns below.

### Deferred Ideas (OUT OF SCOPE)
- **Pellet integration** — stays a placeholder this phase; a second real engine is future work.
- **Active staleness detection / "ontology changed" banner** — needs a change signal (export hash / axiom-count delta) the 821 contract doesn't provide; deferred (D-12).
- **Persisting run history / results across sessions** — D-11 persistence is in-memory for the session only; a durable run log is future work.
- **Async submit/poll job pattern** for very long reasoning runs — inherited deferral from Phase 821; revisit only if real ontologies exceed the sync timeout in practice.
- **Detailed explanation of *why* a class is unsatisfiable** (justifications/axiom pinpointing) — out of scope; 822 shows which classes, not the proof.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REAS-06 | User runs an OWL 2 DL consistency check from the Reasoner screen (HermiT default engine) and sees a pass/fail summary with unsatisfiable-class count, replacing the v8.1 "integration pending" placeholder label | Confirmed the full request/response contract is already implemented and live (verified via running docker stack + direct curl); identified the exact D-13 label-resolution fix (sidecar-side, `{iri,label}` shape) and the exact D-08/D-09 timeout-vs-error body-shape distinction the UI must implement to satisfy criteria 2 and 3 correctly. See Summary, Architecture Patterns, and Common Pitfalls #1/#2. |
</phase_requirements>

## Summary

Phase 822 is smaller than the CONTEXT.md framing implies. Direct inspection of the working tree (not just STATE.md, which is stale) shows **Phase 821 is functionally complete already**: `dg-reasoner/app.py`, `reasoning.py`, `ontology_export.py` and the `data-service` `/reasoner/consistency` proxy are all committed (`2c6cb8a feat(821-04): add thin data-service proxy to dg-reasoner sidecar (D-06)`), and the full docker stack (`neo4j`, `dg-reasoner`, `data-service`, `design-grammars`) is currently **up and running**. A live `curl` against the real proxy against project `v8-ui-smoke` returned a genuine HermiT result in 1.6s: `{"consistent":true,"unsatisfiable_classes":[],"axiom_counts":{...},"duration_ms":1613,"stripped_builtin_rules":5}`. This means 822 can be validated end-to-end against the real reasoner today, not just at the contract level — the CONTEXT.md's "822 cannot be verified end-to-end until 821 is executed" caveat is now out of date and should be re-confirmed by the planner rather than treated as a hard blocker.

Two concrete, code-verified findings should drive planning:

1. **D-13 (IRI→label resolution): resolve in the sidecar (option a), not the proxy or the UI.** `dg-reasoner/ontology_export.py`'s `build_graph()` already writes an `rdfs:label` triple for every `Class` node that has a Neo4j `label` property, *before* the graph is handed to HermiT. That means the exact label data D-02 needs is already loaded into the in-memory Owlready2 ontology object at the moment `_reason_worker` collects `inconsistent_classes()` — enriching the response costs one extra attribute read per class, zero new Neo4j round-trips, and zero IRI-parsing duplication in a second service. The other two options both require re-implementing `ontology_export.py`'s IRI-minting/expansion logic in a second place (data-service or the browser), which is a documented anti-pattern this codebase actively avoids (see `CLAUDE.md`'s "Schema Change Propagation" list).

2. **A real timeout-semantics gap exists between the sidecar (90s) and the proxy (5s read timeout) that the UI must parse correctly, not paper over.** `data-service/app.py`'s `/reasoner/consistency` route uses `httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0)` while the sidecar's own hard timeout (`DG_REASONER_TIMEOUT_SECONDS`) defaults to 90s. Today's `v8-ui-smoke` fixture reasons in ~1.6s so this isn't visibly broken yet, but the mismatch means: (a) as the rule corpus grows, real HermiT runs will very plausibly exceed 5s and get masked as a data-service **transport** timeout long before the sidecar's own **semantic** timeout could ever fire, and (b) — more importantly for 822's plan — **both failure modes return HTTP 504 today, but with different JSON body shapes**, and the frontend must branch on body shape, not status code, to correctly tell D-08 (Unknown) apart from D-09 (hard error). See Common Pitfalls #1 for the exact shapes.

**Primary recommendation:** Plan 822 to (a) extend `dg-reasoner/reasoning.py`'s `_reason_worker`/`run_consistency` to emit `unsatisfiable_classes` as `[{iri, label}]` instead of a flat IRI list (small, contained change to already-committed-but-not-yet-phase-closed 821 code, with a matching test update in `dg-reasoner/tests/test_routes.py`), (b) bump `data-service/app.py`'s proxy read timeout to track the sidecar's own timeout with margin (e.g. `DG_REASONER_TIMEOUT_SECONDS + 10`), and (c) write `reasonerApi.runConsistencyCheck` to branch on JSON body shape (`"error" in body && "consistent" in body` → Unknown; `body.detail?.code` → hard error) rather than HTTP status alone.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Run trigger, state machine (idle/running/verdict/cancelled), elapsed timer, Cancel/AbortController | Browser/Client (`ReasonerScreen.jsx`) | — | Screen-local React state per existing repo pattern; no backend involvement needed for UI state |
| Result rendering (verdict copy, badge, unsat-class list) | Browser/Client | — | Pure presentation of a server-provided, already-resolved payload |
| IRI→human-label resolution for unsatisfiable classes | **API/Backend — dg-reasoner sidecar** (`reasoning.py`) | — | Label data is already loaded in-memory in the same reasoning call (via `ontology_export.build_graph`'s `rdfs:label` triples); resolving anywhere else duplicates IRI-minting logic in a second service |
| Timeout/error normalization (sidecar-timeout vs. transport-timeout vs. connect-error) | API/Backend — `data-service` proxy (existing, committed) | Browser/Client (must correctly parse the two distinct 504 body shapes) | data-service already owns the httpx call and structured-error convention; the UI's job is correct branching on the response it receives, not re-deriving verdict semantics |
| OWL 2 DL consistency reasoning (HermiT) | Reasoning Service — `dg-reasoner` sidecar (isolated per ADR-820-2) | — | Already implemented; out of 822's scope to modify the reasoning core beyond the label-enrichment change |
| Freshness / no-cache | Browser/Client (by construction: POST is never cached) | — | D-10; no server-side cache-busting logic needed |
| Reachability (routing) | Already solved — nginx `/reasoner/` (`ui-v2/nginx.conf` L31) + vite dev proxy (`ui-v2/vite.config.js` L15) | — | Confirmed present; zero new routing work in 822 |

## Standard Stack

No new libraries. This phase is 100% wiring against already-installed dependencies.

### Core (already present, reused as-is)
| Library | Version (verified) | Purpose | Where |
|---------|---------|---------|-------|
| FastAPI + httpx | already in `data-service/requirements.txt` (Phase 821) | proxy route, timeout handling | `data-service/app.py` |
| Owlready2 / rdflib / pySHACL | 0.51 / 7.6.0 / 0.40.0 per `.planning/research/` (Phase 821 pinned) | reasoning core | `dg-reasoner/` |
| React 18 (native `fetch`, `AbortController`) | `react@^18.3.1` per `ui-v2/package.json` | run state machine, cancel | `ui-v2/src/screens/ReasonerScreen.jsx` |

**No `npm install` / `pip install` needed for this phase.** `AbortController` is a browser-native Web API, not a package.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `AbortController` + `fetch` | axios / a fetch-wrapper lib | Repo has zero HTTP client dependency today (`reasonerApi.js` uses raw `fetch`) — adding one for a single cancel button contradicts the existing "no new shared primitives expected" UI-SPEC constraint |
| Sidecar-side label enrichment (recommended) | data-service Neo4j lookup / client-side resolution | Both alternatives require re-implementing `ontology_export.py`'s IRI expand/mint logic in a second place — see Summary finding #1 |

## Package Legitimacy Audit

**Not applicable — this phase introduces zero new external packages** (npm or pip). All work extends already-installed, already-audited dependencies from Phases 814/821. No `package-legitimacy check` run was needed.

## Architecture Patterns

### System Architecture Diagram

```
Architect (browser)
   │ clicks "Run check" on HermiT card
   ▼
ReasonerScreen.jsx (React state: idle → running → verdict|cancelled)
   │ fetch POST /reasoner/consistency {project, engine:"hermit"} + AbortController signal
   ▼
nginx (:8080, /reasoner/ → data-service)  [existing route, unchanged]
   ▼
data-service /reasoner/consistency (app.py L1173-1208)
   │ httpx.post(DG_REASONER_URL/reason/consistency, timeout=short)
   │   ├─ httpx.TimeoutException  → 504 {"detail":{"error":...,"code":"REASONER_TIMEOUT"}}   [TRANSPORT — D-09 hard error]
   │   └─ httpx.ConnectError      → 502 {"detail":{"error":...,"code":"REASONER_UNAVAILABLE"}} [TRANSPORT — D-09 hard error]
   │ else: pass sidecar's JSON body + status code straight through
   ▼
dg-reasoner /reason/consistency (app.py L57-78 → reasoning.run_consistency)
   │ 1. _hybrid_union(project, session): static TBox + curated disjointness + live Neo4j export
   │      (Class nodes get an rdfs:label triple here if Neo4j has one — ontology_export.py L236-237)
   │ 2. strip_hermit_unsupported(union)  → stripped_builtin_rules count
   │ 3. serialize to NTriples, run HermiT in a multiprocessing.Process
   │      joined with DG_REASONER_TIMEOUT_SECONDS (default 90s)
   │      ├─ completes in time → {consistent, unsatisfiable_classes:[iri,...], axiom_counts, duration_ms, stripped_builtin_rules}  [HTTP 200]
   │      └─ hard timeout, process killed → {consistent:null, error:"timeout", duration_ms, stripped_builtin_rules, timeout_seconds}  [HTTP 504 — SEMANTIC "Unknown", D-08]
   ▼
Neo4j (bolt, direct — sidecar owns its own connection, independent of data-service's)
```

### Recommended Project Structure (files touched, no new dirs)
```
ui-v2/src/
├── lib/reasonerApi.js       # + runConsistencyCheck(project, {signal})
└── screens/ReasonerScreen.jsx  # + Run/Cancel buttons, run-state machine, result region on HermiT card

data-service/
└── app.py                   # timeout value adjustment only (existing route, already committed)

dg-reasoner/
├── reasoning.py              # unsatisfiable_classes enrichment: iri → {iri, label}
└── tests/test_routes.py      # updated/added assertions for the new shape
```

### Pattern 1: Screen-local run-state machine (no global store)
**What:** `idle → running → {consistent|inconsistent|unknown|cancelled}` plus a separate `error` line, held entirely in `React.useState` inside `ReasonerScreen.jsx` — matches the existing `loading`/`loadError`/`saving`/`saveError` pattern already in the file (lines 10-17).
**When to use:** Always in this codebase — "Screen-local React state only (no global store)" is an established v8.x pattern (STATE.md, Phase 815 decision, repeated across every screen).
**Example (existing precedent to mirror), elapsed-timer + settle pattern from `GraphScreen.jsx`:**
```javascript
// Source: ui-v2/src/screens/GraphScreen.jsx L500-519 (existing, verified)
let step = 0;
const t0 = Date.now();
const timer = setInterval(() => {
  // ...tick UI...
}, 1400);
try {
  const payload = await someAsyncCall(...);
  clearInterval(timer);
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  // ...render secs...
} finally {
  clearInterval(timer); // always clear on any exit path
}
```
822's elapsed-seconds counter (D-07) should follow this exact shape (`t0 = Date.now()`, `setInterval` tick, `clearInterval` in both success and catch/finally paths) — it is the only existing precedent for a live running-duration counter in this codebase and keeps the new code idiomatically consistent.

### Pattern 2: Relative-time formatting for "Last checked"
**What:** `formatRelativeDate(isoString)` in `ui-v2/src/components/display/SessionHistory.jsx` L27-40 is the only existing relative-time formatter in the codebase (`"just now"` / `"{n}m ago"` / `"{n}h ago"` / `"{n}d ago"` / falls back to a date slice past 7 days).
**When to use:** D-11's "Last checked: <relative time>" — reuse this exact function (import it, or lift its logic) rather than writing a second relative-time formatter. `ConnectorsScreen.jsx`'s `lastConnectionText`/`formatDate` (L31-33) is the only other precedent and is absolute-date-only — less suited to D-11's "2m ago" framing.
```javascript
// Source: ui-v2/src/components/display/SessionHistory.jsx L27-40 (existing, verified)
function formatRelativeDate(isoString) {
  if (!isoString) return "";
  const then = new Date(isoString).getTime();
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return diffMin + "m ago";
  if (diffHr < 24) return diffHr + "h ago";
  if (diffDay < 7) return diffDay + "d ago";
  return String(isoString).slice(0, 10);
}
```

### Pattern 3: AbortController fetch cancellation — NO existing precedent
**Finding:** `grep -rn "AbortController"` across `ui-v2/src` returns **zero hits** (only false positives: `Badge.jsx`'s `signal` color variant, `graphEngine.js`'s `signal` color constant). D-07's Cancel button is a genuinely new pattern for this codebase — there is nothing to reuse, only the standard Web API to apply directly:
```javascript
// New pattern (no repo precedent) — reasonerApi.js
export async function runConsistencyCheck(project, { signal } = {}) {
  const res = await fetch("/reasoner/consistency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project, engine: "hermit" }),
    signal,
  });
  // IMPORTANT: do not reuse getJson() unmodified here — see Pitfall #1.
  // A non-2xx response must still be parsed (504 can mean Unknown OR hard-error;
  // see the body-shape branch documented below).
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}
```
`AbortController`'s `abort()` only cancels the client-side `fetch` wait; per D-07 this is explicitly acceptable — the FastAPI route is a sync `def` (not `async def`, confirmed at `app.py` L1174), so it runs in Starlette's threadpool and has no `await request.is_disconnected()` check; an aborted client fetch does not stop the server-side `httpx.post()` already in flight. This matches D-07's documented expectation exactly — no code change needed to make this true, just don't assume cancel stops the actual reasoning run.

### Anti-Patterns to Avoid
- **Re-deriving `unsatisfiable_classes` labels client-side by loading OntoGraph separately:** would require a second network round-trip (`GraphScreen`-style OntoGraph fetch) plus reimplementing IRI matching against `ontology_export.py`'s `mint()`/`expand_iri()` scheme in JavaScript. Fragile and duplicative — see D-13 recommendation.
- **Branching Unknown vs. hard-error on HTTP status code alone:** both are 504 today (see Pitfall #1). Must branch on body shape.
- **Reusing `reasonerApi.js`'s existing `getJson()` unmodified for the consistency call:** `getJson` throws on any non-2xx and extracts `j?.detail?.error || j?.detail` — this loses the distinction between the sidecar's native timeout body (`error` top-level, no `detail` wrapper) and data-service's structured error body (`detail.error`/`detail.code`). Write a dedicated response handler for this one call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative-time display | A new "time ago" formatter | `formatRelativeDate` from `SessionHistory.jsx` (import or lift) | Only one relative-time convention should exist in the UI; already battle-tested for the same "Last checked"-shaped UX in Session History |
| IRI-local-name fallback parsing | A JS IRI-fragment parser in the browser | A tiny Python helper alongside `ontology_export.py`'s existing `expand_iri`/`mint` (same module already owns IRI shape knowledge) | Single source of truth for IRI shape; the sidecar already has the full IRI string and the owlready2 class object in memory at enrichment time |
| Elapsed-seconds ticking | A new timer abstraction / library | `Date.now()` + `setInterval` + `clearInterval`, exactly as `GraphScreen.jsx` L502-519 does it | Matches existing idiom; no new dependency; proven pattern already handles clear-on-both-exit-paths correctly |

**Key insight:** every UI-side need in this phase (relative time, elapsed counter, error-line styling) already has a direct, working precedent somewhere in `ui-v2/src`. The only genuinely new client-side primitive is `AbortController`, which is a browser standard, not something to build.

## Common Pitfalls

### Pitfall 1: HTTP 504 is ambiguous between D-08 (Unknown) and D-09 (hard error) — must branch on JSON body shape
**What goes wrong:** Both "the sidecar's own HermiT timeout genuinely fired" and "data-service's proxy gave up waiting on the sidecar" surface as HTTP 504 to the browser. Rendering both as "Unknown" would violate D-09 (transport errors must be a distinct error line, never folded into Unknown); rendering both as a hard error would violate D-08 (a genuine reasoner timeout is a first-class, non-error "Inconclusive" verdict).
**Why it happens:** `dg-reasoner/app.py`'s own timeout response is forwarded by `data-service/app.py`'s proxy verbatim (`return JSONResponse(status_code=response.status_code, content=body)`, `app.py` L1208) — so a genuine sidecar timeout produces body `{"consistent": null, "error": "timeout", "duration_ms": N, "stripped_builtin_rules": N, "timeout_seconds": 90}` (no `detail` key, `consistent` key present). But when data-service's OWN `httpx.post()` call times out first (its 5s read timeout, `app.py` L1186), it raises its own `_structured_error_response("...", "...", "REASONER_TIMEOUT", 504)`, which FastAPI serializes as `{"detail": {"error": "...", "hint": "...", "code": "REASONER_TIMEOUT"}}` (no `consistent` key, wrapped in `detail`) — same 504 status, different shape.
**How to avoid:** In `reasonerApi.runConsistencyCheck`'s caller, branch like: `if (body?.error === "timeout" && "consistent" in body) → Unknown (D-08)`; `else if (!res.ok) → hard error (D-09), read body.detail?.error/code`. Verified directly from `dg-reasoner/app.py` L76-78, `data-service/app.py` L1173-1208, and `data-service/app.py` L569-574 (`_structured_error_response`'s exact shape).
**Warning signs:** If the plan's task list has the UI check `response.status === 504` alone to decide Unknown vs. error, this pitfall has not been addressed.

### Pitfall 2: data-service's proxy timeout (5s) is much shorter than the sidecar's own hard timeout (90s)
**What goes wrong:** Not currently visible with the small `v8-ui-smoke` fixture (live-tested at 1.6s duration_ms), but as a project's rule corpus grows, real HermiT runs will plausibly exceed 5s and get masked as a data-service transport timeout (Pitfall 1's second branch) well before the sidecar's own 90s semantic timeout could ever legitimately fire and produce the honest `error:"timeout"` D-08 payload.
**Why it happens:** `data-service/app.py` L1186: `httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0)` was set short specifically so a hung sidecar can't block the calling thread indefinitely — but 5s is far shorter than the sidecar's own configured ceiling (`DG_REASONER_TIMEOUT_SECONDS=90` in `dg-reasoner/reasoning.py`/`app.py`), so the two timeouts don't compose the way D-08/D-09 intends.
**How to avoid:** Bump the proxy's `read` timeout to track the sidecar's ceiling with margin (e.g. `os.getenv("DG_REASONER_TIMEOUT_SECONDS", 90) + 10`), while keeping `connect` short (2s is fine — a genuinely unreachable sidecar should fail fast). Since the route is a sync `def` on Starlette's threadpool (not the event loop), a longer read timeout on this one route does not block other data-service requests — the original "never blocks the hot path" rationale (821 D-06) is about isolating *this* endpoint's own worst case, not about needing an artificially short number.
**Warning signs:** Any project with >~20-30 rules or a denser class hierarchy may start seeing spurious "Reasoner unavailable" errors instead of real verdicts. Not observed in today's fixture, but worth a plan task to fix proactively rather than discover it live in front of an architect.

### Pitfall 3: STATE.md and 822-CONTEXT.md's phase-ordering assumption is stale
**What goes wrong:** Planning 822 as strictly blocked on "821 has to execute first" when 821's code (all 4 plans: sidecar scaffold, translator, hybrid reasoning core, and the data-service proxy) is already committed and the docker stack is live-running right now.
**Why it happens:** `.planning/STATE.md`'s frontmatter (`stopped_at: Completed 821-02-PLAN.md`) and `821-04-SUMMARY.md`'s absence (only `821-01/02/03-SUMMARY.md` exist) suggest 821 is mid-flight, but `git log -- data-service/app.py` shows `2c6cb8a feat(821-04): add thin data-service proxy to dg-reasoner sidecar (D-06)` already committed, and a live `curl` against the running stack returned a real HermiT verdict.
**How to avoid:** The planner should not treat "wait for 821" as a hard sequencing gate for 822's own plan; it can be developed and manually verified against the live stack today. Still worth flagging to the user that 821's `SUMMARY.md`/`STATE.md` bookkeeping appears incomplete (separate from 822's own work).
**Warning signs:** A plan that adds an explicit "blocked-until-821-ships" checkpoint task without first checking `git log`/the running containers.

### Pitfall 4: `unsatisfiable_classes` label enrichment must not break the existing D-10 contract test
**What goes wrong:** `dg-reasoner/tests/test_routes.py`'s `test_reason_consistency_returns_d10_contract` currently asserts `D10_KEYS <= set(body.keys())` where `D10_KEYS` includes `unsatisfiable_classes` as a set-membership check only (doesn't assert element shape) — so changing element shape from `str` to `{iri, label}` won't break that specific assertion, but it's still worth adding an explicit shape assertion for the new `{iri, label}` entries so the contract change is locked in as a regression guard, not left implicit.
**How to avoid:** Add a dedicated test asserting `label` is present, non-empty, and falls back to a local-name string (never a raw `http://...` value) when the fixture Class node has no `label` property.

## Code Examples

### Existing D-09-style error line (reuse, do not reinvent) — `ReasonerScreen.jsx` L114-134 (verified)
```jsx
// Source: ui-v2/src/screens/ReasonerScreen.jsx L124-132
<div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
  Settings unavailable · {loadError}{" "}
  <span onClick={handleRetry} style={{ cursor: "pointer", textDecoration: "underline" }}>
    Retry
  </span>
</div>
```
This is the exact template D-09's transport/hard-error line should mirror for the HermiT card.

### Phantom-token correction (confirmed by direct token-file grep, matches UI-SPEC's flag)
`ReasonerScreen.jsx` currently references `--color-accent` (L176, L227) and `--surface-focus` (L179) — **neither is defined anywhere under `ui-v2/src/styles/tokens/`** (grep across `colors.css`/`effects.css`/`base.css` confirms zero matches). Real equivalents: `--accent-selection` / `--accent-selection-bg` (both alias Signal Red, `colors.css` L47-48). Any code this phase touches on those lines should fix the phantom refs (in-scope cleanup per UI-SPEC, now independently confirmed).

### Real, currently-live response shapes (verified via running stack + source)
```jsonc
// Success (verified live, v8-ui-smoke, 2026-07-12):
{"consistent": true, "unsatisfiable_classes": [], "axiom_counts": {"subClassOf": 65, "domain": 101, "range": 138, "disjointWith": 2, "classDeclarations": 89}, "duration_ms": 1613, "stripped_builtin_rules": 5}

// Sidecar's own semantic timeout (verified via dg-reasoner/reasoning.py L203-210, forwarded verbatim by app.py L1208):
{"consistent": null, "error": "timeout", "duration_ms": 90000, "stripped_builtin_rules": 3, "timeout_seconds": 90}
// HTTP 504

// data-service's own transport timeout (verified via app.py L1188-1194 + L569-574):
{"detail": {"error": "Reasoner sidecar request timed out.", "hint": "The dg-reasoner sidecar is slow or unreachable. Try again later.", "code": "REASONER_TIMEOUT"}}
// HTTP 504

// data-service's own connect error (verified via app.py L1195-1201):
{"detail": {"error": "Could not connect to the reasoner sidecar.", "hint": "Verify the dg-reasoner service is running.", "code": "REASONER_UNAVAILABLE"}}
// HTTP 502
```

### Recommended D-13 sidecar enrichment shape (this phase's one backend change)
```jsonc
// unsatisfiable_classes changes from ["http://.../ex#SlidingDoor"]
// to:
"unsatisfiable_classes": [
  {"iri": "http://example.org/design-grammar/ex#SlidingDoor", "label": "Sliding Door"}
]
// label = Class.label from Neo4j if present (already an rdfs:label triple in the
// reasoned ontology, ontology_export.py L236-237); else the local IRI name
// (fragment after '#', or last path segment) — never null, never the raw full IRI.
// The UI renders ONLY `label`; `iri` is kept solely as a stable React key / future
// debugging hook, never rendered to the architect (D-02).
```

## State of the Art

Not applicable — no external library/version drift to report. All findings above concern this specific codebase's internal contract shapes, verified directly against source and a live instance, not general OWL/React ecosystem trends.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Owlready2's `.label` attribute on a `Thing`/`Class` instance reliably exposes the `rdfs:label` literal loaded from the NTriples file (list-like; take first element) | D-13 recommendation, Code Examples | If owlready2's label API differs from expectation, the enrichment helper needs a small adjustment (e.g. `list(c.label)` vs `c.label.first()`) — low risk, easily caught by the recommended new unit test (Pitfall 4) before it ships |
| A2 | The static TBox (`DesignGrammar-V7.owl`) classes also carry `rdfs:label` (not just live per-project `ex:` classes) | D-13 recommendation | If a TBox-only class goes unsatisfiable and has no label, the local-IRI-name fallback (mandatory per D-02) covers it — no functional risk, just a less pretty label for meta-schema classes, which is an edge case (design rule violations are expected to surface project-scoped `ex:` classes, not TBox classes) |
| A3 | 821's `SUMMARY.md`/`STATE.md` gap (Pitfall 3) is bookkeeping lag, not a sign that 821-04's Task 2 (live integration test) is incomplete or failing | Pitfall 3 | If 821-04's own integration test is actually broken, that's a Phase 821 concern, not blocking for 822 (which was empirically verified live above, independent of that test's status) |

## Open Questions (RESOLVED)

1. **Does 822's plan get to touch `dg-reasoner/reasoning.py` directly, or must the D-13 change go back through a formal Phase 821 addendum?**
   - RESOLVED (2026-07-12, plan-phase): Yes, 822's plan edits `dg-reasoner/reasoning.py` directly (Plan 01, Task 2). D-13 is RESOLVED = option (a), sidecar enriches labels. The change is small and contained — `_local_name` helper + `{iri,label}` construction inside `_reason_worker`. Label data is already in-memory. Flagged as an explicit upstream-821-touch in Plan 01's objective.

2. **Should the data-service proxy timeout bump (Pitfall 2) be in scope for 822?**
   - RESOLVED (2026-07-12, plan-phase): Yes, fixed now in Plan 02 Tasks 1-2. The proxy read timeout is reconciled to `float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90")) + 10` with connect staying at 2.0s. It directly protects criterion 3 and is a one-line change to an already-listed file.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker + compose stack (`neo4j`, `dg-reasoner`, `data-service`, `design-grammars`) | End-to-end manual verification of criteria 1-4 | ✓ (confirmed running at research time) | Docker 29.1.3, compose 2.40.3 | — |
| Live `dg-reasoner` sidecar reachable via `data-service` proxy | Criterion 1 (real HermiT check) | ✓ (verified via live curl, 200 OK, duration_ms 1613) | — | — |
| Node.js (for `ui-v2` dev server) | Frontend dev loop | ✓ | v20.20.0 | — |
| Python | Backend test runs | ✓ | 3.14.2 (host); containers use their own pinned versions | — |
| JS test framework (vitest/jest) in `ui-v2` | Automated frontend state-machine tests | ✗ (none configured — `package.json` has no test script, no vitest/jest config anywhere in `ui-v2/`) | — | Manual/conversational UAT via `/gsd-verify-work`, consistent with every other `ui-v2` screen (none has automated tests today) |

**Missing dependencies with no fallback:** none — the one gap (no JS test framework) has a clear, project-consistent fallback (manual UAT).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (already configured: `data-service/tests/`, `dg-reasoner/tests/`) |
| Frontend framework | **none** — `ui-v2/package.json` has no test script, no vitest/jest/testing-library dependency anywhere in the repo. This is consistent with every existing `ui-v2` screen (zero prior JS test files found). |
| Config file | `dg-reasoner/tests/conftest.py` (integration-marker + Neo4j-availability skip helper, from Phase 821) |
| Quick run (backend) | `pytest dg-reasoner/tests -m "not integration"` / `pytest data-service/tests/test_reasoner.py` |
| Full suite (backend) | `pytest dg-reasoner/tests` (stack up) |
| Frontend verification | Manual conversational UAT (`/gsd-verify-work`) against the running dev server / docker stack — no automated frontend test infra exists to extend |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REAS-06 (criterion 1: real check executes) | Route wiring (mocked reasoning) | unit | `pytest dg-reasoner/tests/test_routes.py::test_reason_consistency_returns_d10_contract -x` | ✅ (existing, Phase 821) |
| REAS-06 (criterion 1: real check executes, true E2E) | Live HermiT round-trip | integration | `pytest dg-reasoner/tests/test_roundtrip_integration.py -m integration` (stack up) | ✅ (existing, Phase 821) — **or** manual `curl localhost:8000/reasoner/consistency` (verified working live during this research) |
| REAS-06 (criterion 2: label resolution, D-02/D-13) | `{iri,label}` shape + fallback | unit | new test in `dg-reasoner/tests/test_routes.py` (or a new file) — mock `run_consistency` to return non-empty `unsatisfiable_classes` with/without a `label` and assert fallback | ❌ Wave 0 |
| REAS-06 (criterion 3: timeout → distinct Unknown, non-blocking) | proxy timeout branching | unit | new test in `data-service/tests/test_reasoner.py` — monkeypatch `httpx.post` to raise `httpx.TimeoutException`/`ConnectError`, assert 504/502 with the exact `detail.code` shapes documented in Pitfall 1 | ❌ Wave 0 |
| REAS-06 (criterion 3, UI state machine) | idle→running→unknown/cancelled, never hangs | manual UAT | conversational verification: point the dev UI at a stubbed slow/504 response and confirm state transitions | manual (no frontend test infra) |
| REAS-06 (criterion 4: fresh POST, no cache) | inspectable in code (no `Cache-Control`, no memoization) | manual/code-review | `grep -n "Cache-Control\|memo" ui-v2/src/lib/reasonerApi.js` (expect no matches) | manual |

### Sampling Rate
- **Per task commit (backend):** `pytest dg-reasoner/tests -m "not integration"` and `pytest data-service/tests/test_reasoner.py`
- **Per wave merge:** full `pytest dg-reasoner/tests` with stack up (integration tier included) + manual click-through of all four verdict states in the running dev UI
- **Phase gate:** all four verdict states (Consistent/Inconsistent/Unknown/Cancelled) manually exercised against the live stack before `/gsd-verify-work`, since Unknown/timeout genuinely cannot be forced without either a slow real project or a temporarily-lowered `DG_REASONER_TIMEOUT_SECONDS`/stubbed proxy — plan should include an explicit task for simulating this (e.g. a short-lived `docker compose run -e DG_REASONER_TIMEOUT_SECONDS=1` or a stubbed `/reasoner/consistency` response during manual QA)

### Wave 0 Gaps
- [ ] `dg-reasoner/tests/test_routes.py` (or new file) — label-enrichment shape + fallback test, covers REQ REAS-06 criterion 2
- [ ] `data-service/tests/test_reasoner.py` — proxy timeout/connect-error response-shape test, covers REQ REAS-06 criterion 3
- [ ] No frontend test framework install planned — confirm with user/planner that manual UAT is acceptable for the React state machine (consistent with existing project convention; introducing vitest for one screen would be new scope)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | This route inherits whatever session/auth the rest of `ui-v2`→`data-service` traffic already uses (unchanged by this phase); no new auth surface introduced |
| V3 Session Management | no | No new session state; result persistence is in-memory screen state (D-11), not a server session |
| V4 Access Control | no | `project` is client-supplied (matches every other `ui-v2`→`data-service` call, e.g. `reasonerApi.getReasonerSettings`); no new authorization boundary crossed by this phase |
| V5 Input Validation | yes | `project` is passed through as a Cypher parameter (`$project`) in `ontology_export.py`'s queries — already parameterized, not string-interpolated; no new injection surface introduced by 822 |
| V6 Cryptography | no | No secrets/credentials touched by this phase (reasoner settings are explicitly documented as needing no encryption, per `data-service/reasoner.py`'s module docstring) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Resource-exhaustion via repeated expensive HermiT runs (no rate limit on `/reasoner/consistency`) | Denial of Service | Out of scope for 822 per its boundary (no async submit/poll, no rate limiting mentioned in CONTEXT.md); worth a note but not a blocking finding since the sidecar's own hard timeout (90s) already bounds worst-case resource hold per request, and the endpoint is `POST`, on-demand only, not polled |
| Error-message information leakage (sidecar/Neo4j internals in error bodies) | Information Disclosure | Already handled — `_structured_error_response`'s bodies are pre-written human messages (`"Verify the dg-reasoner service is running."`), not raw exception text or stack traces |

## Sources

### Primary (HIGH confidence — verified directly against source/running system)
- `dg-reasoner/app.py`, `dg-reasoner/reasoning.py`, `dg-reasoner/ontology_export.py` — full read, response shapes and label-embedding behavior confirmed by code
- `data-service/app.py` L1-73, L1132-1218 — proxy route, timeout values, `_structured_error_response` shape, all confirmed by code
- `dg-reasoner/tests/test_routes.py` — confirms the currently-tested D-10 contract shape
- Live `curl` against `http://localhost:8000/reasoner/consistency` (project `v8-ui-smoke`) — real response captured, 2026-07-12
- `git log --oneline -- data-service/app.py` — confirms 821-04's proxy commit (`2c6cb8a`) is already in the tree
- `ui-v2/src/screens/ReasonerScreen.jsx`, `ui-v2/src/lib/reasonerApi.js`, `ui-v2/src/screens/GraphScreen.jsx` L460-534, `ui-v2/src/components/display/SessionHistory.jsx` L1-40, `ui-v2/src/components/forms/Button.jsx`, `ui-v2/src/components/display/Badge.jsx` — all read directly
- `ui-v2/src/styles/tokens/colors.css`, `effects.css` — token existence/absence confirmed via grep (phantom-token claim independently verified)
- `ui-v2/nginx.conf`, `ui-v2/vite.config.js` — routing confirmed present
- `.planning/phases/821-.../821-04-PLAN.md`, `821-CONTEXT.md`, `820-DECISION.md` — canonical upstream contract docs

### Secondary (MEDIUM confidence)
- Owlready2's `.label` attribute behavior (A1 in Assumptions Log) — based on general Owlready2 API knowledge, not verified against this exact loaded ontology in this session (no live enrichment code exists yet to test)

### Tertiary (LOW confidence)
- None — every claim in this document traces to either a direct code read or a live system probe performed during this research session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, pure wiring
- Architecture / contract shapes: HIGH — verified via direct source read + live curl against the running stack, not assumption
- D-13 recommendation: HIGH — the label data's presence in the reasoned ontology is directly visible in `ontology_export.py`'s source, not inferred
- Pitfalls: HIGH for #1/#2/#4 (code-verified), MEDIUM for #3 (STATE.md staleness inference, though directly supported by git log)

**Research date:** 2026-07-12
**Valid until:** Short shelf life recommended (~7 days) — this research is unusually tied to the exact current state of a fast-moving, actively-committed sibling phase (821); re-verify `git log -- data-service/app.py dg-reasoner/` before planning if more than a few days have passed.
