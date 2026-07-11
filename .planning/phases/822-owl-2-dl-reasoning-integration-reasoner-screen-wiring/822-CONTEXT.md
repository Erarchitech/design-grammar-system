# Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 822 turns the Reasoner screen's HermiT card from a persisted placeholder into a real "run a consistency check and read the result" flow. Clicking a per-card **Run check** on HermiT calls the `dg-reasoner` sidecar's `/reason/consistency` endpoint (built in Phase 821, reached via the data-service `/reasoner/consistency` proxy) against the active project, then renders a trustworthy, four-state result **inside the HermiT card**: Consistent / Inconsistent (with unsatisfiable-class count + labeled list) / Unknown (server timeout) / Cancelled (user stopped). The result is framed as "schema consistency" so it is never mistaken for a design-compliance verdict.

**Not in this phase:** the sidecar itself, the RDF translation, or the `/reason/consistency` contract (all Phase 821); real SHACL shapes / severity mapping / ErrorMessageTemplates surfacing (Phase 823); Pellet integration (stays a placeholder); any active ontology-change detection or staleness banner; async submit/poll job pattern; LLM-ingestion axiom emission (deferred out of v8.2 per ADR-820-1).

</domain>

<decisions>
## Implementation Decisions

### Result Presentation
- **D-01:** The result renders by **expanding the HermiT card itself** — replacing the "Selected — will be used when integration is complete" / "Integration pending" area with the live verdict. Result stays visually bound to the engine that produced it. Reuse the existing screen card / `dg-frost` styling; no modal, no separate route.
- **D-02:** On an **inconsistent** verdict, show the unsatisfiable-class **count** (criterion 2's hard requirement) **plus a list of the classes by their human-readable label** — the OntoGraph `Class.label` property, falling back to the local IRI name only when no label exists. **Never surface raw full IRIs** to the architect (keeps the Phase 823 "no raw RDF vocabulary" principle).
- **D-03:** The verdict is explicitly labeled **"schema consistency"** (not "validation"/"compliance") so it is never confused with a design-compliance result (criterion 2).

### Run Trigger & Card State
- **D-04:** **Per-card Run button on HermiT only.** The HermiT card gains a **Run check** button and **drops its "Integration pending" badge** — it becomes the one live/integrated engine (criterion 1). Pellet keeps its placeholder badge and has **no** run button.
- **D-05:** The run **always forces `engine: "hermit"`** and targets the **active project** (the `project` prop already passed into `ReasonerScreen`). The request payload is `{"project": <active>, "engine": "hermit"}` per the Phase 821 contract (D-10).
- **D-06:** The existing reasoner-selection behavior (persisting selection via `PUT /reasoner/settings`) stays; selecting Pellet must not offer a way to run it.

### In-Progress, Timeout & Verdict States
- **D-07:** While a check runs, the HermiT card shows a **spinner + a live elapsed-seconds counter**; the Run button is disabled, and a **Cancel button** aborts the fetch client-side via `AbortController`. (Aborting the client wait does not necessarily stop the server run — that's acceptable.)
- **D-08:** **Four distinct verdict states**, each with its own visual treatment:
  - **Consistent** — positive/"ok" treatment.
  - **Inconsistent** — signal/red treatment + the D-02 unsat count & labeled list.
  - **Unknown** — neutral/amber "timed out — result inconclusive" treatment; distinct from a real fail (criterion 3). Triggered by the sidecar's server-side timeout response (Phase 821 D-09, ~60–120s, 504-style).
  - **Cancelled** — quiet/gray "you stopped this run — no result"; kept separate from Unknown so a user-initiated stop is never read as a reasoner verdict.
- **D-09:** **Transport/hard errors** (sidecar unreachable, 5xx, malformed body) surface as a **distinct error line** — reuse the screen's existing error-message pattern (the `loadError` / `saveError` `--color-signal` line) — and are **not** folded into the semantic "Unknown" verdict.

### Result Freshness & Re-run
- **D-10:** Each run is a **fresh `POST`** (browsers don't cache POST), so the sidecar re-reads live Neo4j every time — satisfying criterion 4 by construction, no cache-busting needed.
- **D-11:** Show a **"Last checked: <relative time>"** timestamp with each result. The result **persists in-memory across screen revisits within the session** (component/app state), so returning to the screen shows the last verdict rather than a blank card.
- **D-12:** **No active staleness detection.** We do not compare axiom counts / export hashes to warn "ontology changed." The timestamp lets the architect judge freshness and re-run at will. (Change-detection banner explicitly deferred — the 821 contract provides no change signal.)

### Reachability (settled default — not discussed)
- **D-13:** The UI reaches the sidecar through the **existing data-service proxy at `/reasoner/consistency`** (built by Phase 821 D-06). nginx already routes `/reasoner/` → data-service and the vite dev proxy forwards `/reasoner`, so **no new nginx route or vite-proxy entry is needed**. `reasonerApi.js` gains a `runConsistencyCheck(project, { signal })` function posting to `/reasoner/consistency`.

### Claude's Discretion
- Exact copy/wording of each verdict, the "schema consistency" label, the placeholder disclaimer note, and the Cancel/error messages.
- Spinner/elapsed-counter styling and the amber/red/green/gray color mapping (pull from existing tokens: `--color-signal`, `--color-accent`, `--text-muted`, etc.).
- Elapsed-timer tick interval and relative-time formatting for "Last checked".
- **IRI→label resolution location (flagged for research):** the Phase 821 `/reason/consistency` response returns `unsatisfiable_classes` (shape unspecified in the 821 contract, likely IRIs). D-02 needs human labels. Researcher/planner must decide where resolution happens — options: (a) the sidecar enriches each entry with its `Class.label` at export time, (b) the data-service proxy resolves IRI→label via a Neo4j lookup, or (c) the UI resolves against already-loaded OntoGraph data. Since Phase 821 is not yet executed, option (a) may be worth coordinating into the 821 response shape before it locks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Upstream contract (normative — this phase consumes it)
- `.planning/phases/821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation/821-CONTEXT.md` — the `dg-reasoner` sidecar contract 822 wires to: **D-10** (`POST /reason/consistency` request/response shape: `{consistent, unsatisfiable_classes[], axiom_counts{}, duration_ms, stripped_builtin_rules}`), **D-09** (synchronous + hard server-side timeout, 504-style), **D-06** (data-service `/reasoner/consistency` proxy with short timeout), **D-12** (sidecar internal-only — 822 owns UI reachability, resolved here in D-13)
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/820-DECISION.md` — ADR-820-1 (hybrid axiom scoping — why the check is meaningful and not trivially "consistent") + ADR-820-2 (sidecar architecture); context for what "consistent"/"inconsistent" actually means here

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — **REAS-06** (HermiT default engine, pass/fail summary + unsatisfiable-class count, replaces v8.1 "integration pending" placeholder)
- `.planning/ROADMAP.md` §"Phase 822" — the four success criteria this CONTEXT implements

### Existing code to modify (see code_context)
- `ui-v2/src/screens/ReasonerScreen.jsx` — the screen being wired
- `ui-v2/src/lib/reasonerApi.js` — gains `runConsistencyCheck`
- `data-service/reasoner.py` + `data-service/app.py` (`/reasoner/settings` routes ~L1132–1158) — existing reasoner registry/settings; the `/reasoner/consistency` proxy (Phase 821 D-06) lands beside these

### Schema (label resolution)
- `training/dataset_schema.json` + `cypher_template.txt` — graph schema v4; `Class` node key = `iri`, display = `label` (the label used in D-02's unsat list)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ui-v2/src/screens/ReasonerScreen.jsx` — the HermiT/Pellet card layout, `dg-frost` panels, loading/error states, and `Badge` usage all already exist; 822 adds the Run button + expanded-result region to the HermiT card and a new run-state machine (idle → running → consistent/inconsistent/unknown/cancelled/error).
- `ui-v2/src/lib/reasonerApi.js` — `getReasonerSettings`/`selectReasoner` + a shared `getJson` error-unwrap helper (`j?.detail?.error || j?.detail`) to mirror for the new POST.
- `ui-v2/src/components/index.js` — `Button` (variants: outline/solid, sizes) and `Badge` (solid/outline) primitives; reuse for Run/Cancel and verdict chips. No new shared primitives expected.
- Design tokens in `ui-v2/src/styles/tokens/` — `--color-signal` (error/fail red), `--color-accent`, `--text-muted`, `--surface-*` — for the four verdict treatments.

### Established Patterns
- Screen-local React state only (no global store) — matches the existing `ReasonerScreen` pattern; the persisted-result-in-memory (D-11) lives in screen/app state, not a backend cache.
- The screen's existing error line (`--color-signal` text + inline Retry) is the template for D-09 transport errors.
- Synchronous HTTP + client-side timeout/abort — repo-wide "no message queue" Key Decision; D-07's `AbortController` and D-08's Unknown-on-server-timeout honor it.
- nginx `/reasoner/` → data-service proxy already exists (`ui-v2/nginx.conf` L31); vite dev proxy forwards `/reasoner` (`ui-v2/vite.config.js` L15). No proxy changes needed (D-13).

### Integration Points
- `ReasonerScreen.jsx` → `reasonerApi.runConsistencyCheck(project, {signal})` → `POST /reasoner/consistency` → (nginx) → data-service proxy → `dg-reasoner` sidecar.
- Depends on Phase 821 having shipped the sidecar + the data-service `/reasoner/consistency` proxy. **822 cannot be verified end-to-end until 821 is executed** — plan should account for this ordering (contract is known now; live wiring needs 821 running).
- Label resolution (D-02) is the one cross-service open question — see D-13 discretion note.

</code_context>

<specifics>
## Specific Ideas

- "Schema consistency" is the exact framing to lean on — the whole point of criterion 2 is that an architect must never read this result as "my design passed the rules." Copy should reinforce that (e.g., "Schema consistency check — validates the ontology's logical structure, not design compliance").
- The Unknown state is a first-class, trustworthy outcome, not an error: a hung/timed-out reasoner returning "inconclusive" is the honest answer criterion 3 demands — visually neutral (amber), never green or red.
- Keep Cancelled visually quiet — it's a non-event, just an acknowledgment that the user stopped waiting.

</specifics>

<deferred>
## Deferred Ideas

- **Pellet integration** — stays a placeholder this phase; a second real engine is future work.
- **Active staleness detection / "ontology changed" banner** — needs a change signal (export hash / axiom-count delta) the 821 contract doesn't provide; deferred (D-12).
- **Persisting run history / results across sessions** — D-11 persistence is in-memory for the session only; a durable run log is future work.
- **Async submit/poll job pattern** for very long reasoning runs — inherited deferral from Phase 821; revisit only if real ontologies exceed the sync timeout in practice.
- **Detailed explanation of *why* a class is unsatisfiable** (justifications/axiom pinpointing) — out of scope; 822 shows which classes, not the proof.

None of these were scope-creep redirects — discussion stayed within the wiring domain.

</deferred>

---

*Phase: 822-OWL 2 DL Reasoning Integration + Reasoner Screen Wiring*
*Context gathered: 2026-07-12*
