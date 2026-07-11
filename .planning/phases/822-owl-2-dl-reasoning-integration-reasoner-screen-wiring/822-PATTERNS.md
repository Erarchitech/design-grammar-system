# Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 6 (2 new/extended, 4 modified/existing)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `ui-v2/src/lib/reasonerApi.js` (+`runConsistencyCheck`) | service (frontend API client) | request-response | same file's `getJson`/`selectReasoner` (lines 5-44) | exact (extend in place) |
| `ui-v2/src/screens/ReasonerScreen.jsx` (HermiT card + run-state machine) | component/screen | request-response + event-driven (run/cancel/timer) | same file's existing load/select state machine (lines 9-60, 98-134) **+** `GraphScreen.jsx` elapsed-timer pattern (L499-534, esp. L527-534) **+** `SessionHistory.jsx` `formatRelativeDate` (L27-40) | role-match (compose 3 analogs) |
| `dg-reasoner/reasoning.py` (`_reason_worker`, `run_consistency` — enrich `unsatisfiable_classes`) | service (reasoning core) | transform/batch | same file, same functions (lines 115-219) | exact (extend in place) |
| `dg-reasoner/tests/test_routes.py` (new/updated shape assertions) | test | request-response | same file's `test_reason_consistency_returns_d10_contract` (lines 23-46) | exact (extend in place) |
| `data-service/app.py` (`/reasoner/consistency` proxy timeout bump) | controller/route (proxy) | request-response | same file, same route (lines 1168-1208) + `_structured_error_response` (lines 569-574) | exact (extend in place) |
| AbortController-based Cancel wiring in `ReasonerScreen.jsx` | event-driven (client abort) | event-driven | **none in codebase** — new pattern, skeleton below | no analog |

## Pattern Assignments

### `ui-v2/src/lib/reasonerApi.js` (service, request-response)

**Analog:** same file, lines 1-44 (existing `getJson` + `selectReasoner`)

**Imports/module header pattern** (lines 1-4):
```javascript
// Reasoner Screen backend access — reasoner registry settings.
// nginx proxies /reasoner/ to data-service. The vite dev proxy also
// forwards /reasoner to localhost:8080 for development.
```
Add a comment block above the new export following the same one-line-per-concern style.

**Existing error-unwrap helper (`getJson`, lines 5-18)** — **DO NOT reuse unmodified** for the new call (confirmed by RESEARCH Pitfall/Anti-pattern #3): `getJson` throws on any non-2xx and collapses `j?.detail?.error || j?.detail`, which loses the D-08/D-09 body-shape distinction (`{consistent:null,"error":"timeout",...}` vs `{"detail":{"error":...,"code":...}}`, both HTTP 504). Write a **dedicated** function that always parses the body and returns `{ok, status, body}` rather than throwing, so the caller in `ReasonerScreen.jsx` can branch on shape.

**New pattern to write** (mirrors `selectReasoner`'s PUT shape at lines 27-44, adapted to not throw):
```javascript
// POST /reasoner/consistency with { project, engine: "hermit" }.
// Does NOT throw on non-2xx — the 504 status is ambiguous between a genuine
// sidecar timeout (D-08, semantic "Unknown") and a data-service transport
// timeout (D-09, hard error); the caller must branch on body shape, not
// status code alone (see RESEARCH Pitfall 1). AbortController's `signal`
// lets the caller cancel the client-side wait (D-07).
export async function runConsistencyCheck(project, { signal } = {}) {
  const res = await fetch("/reasoner/consistency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project, engine: "hermit" }),
    signal,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}
```

**Caller-side branch to implement in `ReasonerScreen.jsx`** (per RESEARCH Pitfall 1, verified against `data-service/app.py` L1189-1208 and `dg-reasoner/reasoning.py` L203-210):
```javascript
if (result.body?.error === "timeout" && "consistent" in result.body) {
  // D-08 Unknown — genuine sidecar-side semantic timeout
} else if (!result.ok) {
  // D-09 hard error — transport failure; read result.body?.detail?.error / .code
} else {
  // normal success: result.body.consistent, result.body.unsatisfiable_classes
}
```

---

### `ui-v2/src/screens/ReasonerScreen.jsx` (component, request-response + event-driven)

**Analog 1 — existing load/select state machine, same file** (lines 9-60): mirror the `loading`/`loadError`/`saving`/`saveError` `useState` pairing (lines 13-17) for the new run state. Add parallel state: `runState` (`"idle"|"running"|"consistent"|"inconsistent"|"unknown"|"cancelled"`), `runError` (transport/hard error, D-09 — kept **separate** from `runState` per the CONTEXT/UI-SPEC distinction), `runResult` (last full response body), `lastCheckedAt` (ISO string, D-11), `elapsedSec`.

**Analog 2 — elapsed-timer pattern, `ui-v2/src/screens/GraphScreen.jsx` (lines 527-534, verified)**:
```javascript
// Source: ui-v2/src/screens/GraphScreen.jsx L527-534 (existing, verified)
let step = 0;
const t0 = Date.now();
const timer = setInterval(() => {
  if (step < steps.length - 1) step++;
  patchTurn(id, (t) => ({
    progress: Math.min(90, Math.round(((step + 0.5) / steps.length) * 100)),
    steps: t.steps.map((x, i) => ({
      ...x,
```
822's elapsed-seconds counter (D-07, UI-SPEC "Running… {n}s") should follow the same `t0 = Date.now()` / `setInterval` / `clearInterval`-on-every-exit-path shape — but tick a plain `elapsedSec` state (`Math.floor((Date.now() - t0) / 1000)`) rather than a multi-step progress bar. **Always `clearInterval` in both the success and catch/finally paths** (this file's real precedent guards that; do not skip it).

**Analog 3 — relative-time formatter, `ui-v2/src/components/display/SessionHistory.jsx` (lines 27-40, verified)**:
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
D-11's "Last checked: <relative time>" should import/lift this exact function rather than write a second one (it is the only relative-time convention in the codebase; `ConnectorsScreen.jsx`'s `formatDate`/`lastConnectionText` at L7/L31 is absolute-date-only and not a fit).

**Error-line pattern to reuse verbatim for D-09** (`ReasonerScreen.jsx` lines 124-132, this file, already exists):
```jsx
// Source: ui-v2/src/screens/ReasonerScreen.jsx L124-132 (existing, verified)
<div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
  Settings unavailable · {loadError}{" "}
  <span onClick={handleRetry} style={{ cursor: "pointer", textDecoration: "underline" }}>
    Retry
  </span>
</div>
```
Copy this shape for the transport/hard-error line under the HermiT card (swap copy per UI-SPEC: `Reasoner unavailable · {detail}` + inline **Retry**), using `--color-signal-ink` per UI-SPEC's destructive-role token, not `--color-signal` (UI-SPEC reserves `--color-signal` for the selection ring + Inconsistent verdict specifically; the error line's exact token is UI-SPEC's own call — cross-check against `--color-signal-ink` in `colors.css` at plan time).

**Card layout / Button+Badge usage to extend** (`ReasonerScreen.jsx` lines 160-236, this file): the HermiT card's existing per-reasoner `<div>` block (title row with `Badge`, description, "Selected —…" line at 222-232) is the exact insertion point for D-01's expanded result region — replace the "Selected — will be used when integration is complete" block (lines 222-232) with the Run button (idle) / spinner+elapsed+Cancel (running) / verdict region (settled states), gated on `r.id === "hermit"` (D-04: Pellet keeps its current placeholder badge/behavior untouched).

**Phantom-token fix (in-scope cleanup, confirmed by UI-SPEC + direct grep)**: this file currently references `--color-accent` (L176, L227) and `--surface-focus` (L179) — neither is defined under `ui-v2/src/styles/tokens/`. Replace with `--accent-selection` / `--accent-selection-bg` (see `Button.jsx` L37-44 for the real token names already used correctly elsewhere in the design system) wherever this phase touches those lines.

**Button/Badge primitives** (`ui-v2/src/components/forms/Button.jsx` lines 1-70, `ui-v2/src/components/display/Badge.jsx` lines 1-42, both read in full — small files):
- `Button` variants: `primary` / `secondary` / `outline` / `destructive`; sizes `sm`(28px)/`md`(36px)/`lg`(40px); a `disabled` prop dims to `opacity:0.45` and sets `pointer-events:none` via `cursor:"default"` — use `<Button variant="outline" size="sm" disabled={runState==="running"}>Run check</Button>` and `<Button variant="outline" size="sm">Cancel</Button>` per UI-SPEC (both achromatic outline, not `destructive` — UI-SPEC explicitly says Cancel is not destructive).
- `Badge` variants: `solid` / `soft` / `outline` / `signal` — use `variant="solid"` for Consistent, `variant="signal"` for Inconsistent, `variant="outline"` for Unknown ("Inconclusive"), no badge for Cancelled (per UI-SPEC's Verdict State Matrix).

---

### `dg-reasoner/reasoning.py` (service, transform)

**Analog:** same file, `_reason_worker` (lines 115-137) and `run_consistency` (lines 168-219)

**Current pattern to extend** (lines 124-137, verified):
```python
# Source: dg-reasoner/reasoning.py L124-137 (existing, verified)
try:
    inconsistent = list(onto.inconsistent_classes())
except AttributeError:  # pragma: no cover - owlready2 API fallback
    from owlready2 import default_world
    inconsistent = list(default_world.inconsistent_classes())

owl_nothing = "http://www.w3.org/2002/07/owl#Nothing"
iris = sorted(
    {getattr(c, "iri", str(c)) for c in inconsistent} - {owl_nothing}
)
queue.put({"unsatisfiable_classes": iris})
```
D-13's fix: after computing `iris`, resolve each IRI's owlready2 class object's `.label` (per RESEARCH Assumption A1: list-like, take first element) and build `[{iri, label}]` entries instead of a flat IRI list; fall back to the local IRI name (fragment after `#`, or last path segment) when no `rdfs:label` was loaded. `run_consistency`'s pass-through at line 212-215 (`unsatisfiable_classes = result["unsatisfiable_classes"]`) needs no structural change beyond carrying the new `{iri,label}` shape through unchanged.

**Where the label data already lives** — `dg-reasoner/ontology_export.py` lines 234-237 (verified):
```python
# Source: dg-reasoner/ontology_export.py L234-237 (existing, verified)
if "Class" in labels:
    graph.add((iri, RDF.type, OWL.Class))
    if props.get("label"):
        graph.add((iri, RDFS.label, RDFLiteral(props["label"])))
```
Confirms the `rdfs:label` triple is already present in the NTriples graph HermiT reasons over — the enrichment in `reasoning.py` reads this same in-memory ontology object, no second Neo4j round-trip needed (RESEARCH D-13 recommendation, option (a)).

---

### `dg-reasoner/tests/test_routes.py` (test, request-response)

**Analog:** same file, `test_reason_consistency_returns_d10_contract` (lines 23-46, verified)

**Existing contract-test pattern to extend**:
```python
# Source: dg-reasoner/tests/test_routes.py L23-46 (existing, verified)
D10_KEYS = {"consistent", "unsatisfiable_classes", "axiom_counts", "duration_ms", "stripped_builtin_rules"}

def test_reason_consistency_returns_d10_contract(monkeypatch):
    def fake_run_consistency(project, engine="hermit", session=None):
        assert project == "x"
        assert engine == "hermit"
        return {
            "consistent": True,
            "unsatisfiable_classes": [],
            "axiom_counts": {...},
            "duration_ms": 42,
            ...
        }
    monkeypatch.setattr(reasoning, "run_consistency", fake_run_consistency)
    response = client.post("/reason/consistency", json={"project": "x"})
    assert response.status_code == 200
    body = response.json()
    assert D10_KEYS <= set(body.keys())
```
`D10_KEYS <= set(body.keys())` is a set-membership check only — it will NOT catch the element-shape change from `str` to `{iri,label}`. Add a **new**, explicit test (per RESEARCH Pitfall 4) asserting: (a) a non-empty `unsatisfiable_classes` fixture entry has both `iri` and `label` keys, (b) `label` is non-empty and never a raw `http://...` string when the fixture Class has no `label` property (fallback-to-local-name case), mirroring this same `monkeypatch.setattr(reasoning, "run_consistency", fake_run_consistency)` style.

---

### `data-service/app.py` (controller/route, request-response)

**Analog:** same file, `/reasoner/consistency` route (lines 1168-1208) and `_structured_error_response` (lines 569-574)

**Existing proxy pattern (verified, to extend only for the timeout value + no shape change)**:
```python
# Source: data-service/app.py L1173-1208 (existing, verified)
@app.post("/reasoner/consistency")
def post_reasoner_consistency(payload: ReasonerConsistencyRequest):
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/reason/consistency",
            json={"project": payload.project, "engine": payload.engine},
            timeout=httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0),
        )
    except httpx.TimeoutException:
        raise _structured_error_response(
            "Reasoner sidecar request timed out.",
            "The dg-reasoner sidecar is slow or unreachable. Try again later.",
            "REASONER_TIMEOUT",
            504,
        )
    except httpx.ConnectError:
        raise _structured_error_response(
            "Could not connect to the reasoner sidecar.",
            "Verify the dg-reasoner service is running.",
            "REASONER_UNAVAILABLE",
            502,
        )
    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}
    return JSONResponse(status_code=response.status_code, content=body)
```
Per RESEARCH Pitfall 2, bump only the `read=5.0` value to track the sidecar's own `DG_REASONER_TIMEOUT_SECONDS` (default 90s) with margin, e.g. `read=float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", 90)) + 10`, keeping `connect=2.0` short. No other structural change — the route already passes the sidecar's JSON body straight through, which is what carries the new `{iri,label}` shape to the browser unchanged.

**`_structured_error_response` helper (lines 569-574, verified, unchanged, reuse as-is)**:
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "hint": hint, "code": code})
```
This is the exact shape the frontend's D-09 branch must parse (`body.detail.error` / `body.detail.code`) — distinct from the sidecar's own timeout body (`{"consistent": null, "error": "timeout", ...}`, no `detail` wrapper). See Shared Patterns below.

---

## Shared Patterns

### Screen-local state machine (no global store)
**Source:** `ui-v2/src/screens/ReasonerScreen.jsx` lines 9-60 (existing `loading`/`loadError`/`saving`/`saveError` pattern)
**Apply to:** the new `runState`/`runError`/`runResult`/`lastCheckedAt` state in the same file — matches the repo-wide "screen-local React state only, no global store" convention (STATE.md, Phase 815 decision).

### Elapsed-time counter (setInterval + Date.now, clear on every exit path)
**Source:** `ui-v2/src/screens/GraphScreen.jsx` lines 527-534
**Apply to:** `ReasonerScreen.jsx`'s D-07 running-state spinner + elapsed-seconds counter.

### Relative-time formatting
**Source:** `formatRelativeDate` in `ui-v2/src/components/display/SessionHistory.jsx` lines 27-40
**Apply to:** `ReasonerScreen.jsx`'s D-11 "Last checked: <relative time>" — import or lift verbatim; do not write a second formatter.

### Existing error-line treatment (D-09 transport/hard errors)
**Source:** `ui-v2/src/screens/ReasonerScreen.jsx` lines 124-132 (`loadError`/`Retry` pattern)
**Apply to:** the new HermiT-card transport-error line; same `Retry` click-handler shape, new copy per UI-SPEC.

### `_structured_error_response` body shape (backend↔frontend error contract)
**Source:** `data-service/app.py` lines 569-574, used at lines 1189-1201
**Apply to:** `reasonerApi.js`'s new response handler must branch on this exact `{"detail": {"error", "hint", "code"}}` shape vs. the sidecar's own `{"error": "timeout", "consistent": null, ...}` shape (RESEARCH Pitfall 1) — this is the single most safety-critical shared pattern in this phase.

### Button/Badge primitives (design-system-level shared pattern)
**Source:** `ui-v2/src/components/forms/Button.jsx`, `ui-v2/src/components/display/Badge.jsx` (both read in full above)
**Apply to:** Run/Cancel buttons and all four verdict badges — no new shared primitive is expected or needed (confirmed by CONTEXT `code_context` and UI-SPEC Registry Safety section).

## No Analog Found

| File/Pattern | Role | Data Flow | Reason |
|---|---|---|---|
| AbortController-based fetch cancellation (D-07 Cancel button) | event-driven (client abort) | event-driven | Confirmed via `grep -rn "AbortController" ui-v2/src` → zero hits (only false-positive `signal` color-variant matches in `Badge.jsx`/`graphEngine.js`). This is a genuinely new client-side pattern for the codebase; use the standard Web API directly (skeleton below) rather than searching further for a non-existent analog. |

**Minimal correct AbortController + fetch cancel skeleton** (new pattern, no repo precedent — for the planner to hand to implementation directly):
```javascript
// Inside ReasonerScreen.jsx's handleRunCheck:
const controller = new AbortController();
abortRef.current = controller; // React.useRef(null), so Cancel can reach it
setRunState("running");
const t0 = Date.now();
const timer = setInterval(() => setElapsedSec(Math.floor((Date.now() - t0) / 1000)), 1000);
try {
  const result = await runConsistencyCheck(project, { signal: controller.signal });
  // ... branch on result.ok / result.body per the D-08/D-09 shape rules above ...
} catch (err) {
  if (err.name === "AbortError") {
    setRunState("cancelled");
  } else {
    setRunState("error"); // rare: fetch itself threw (network-level, not a JSON response)
  }
} finally {
  clearInterval(timer);
  abortRef.current = null;
}

// Cancel button onClick:
const handleCancel = () => abortRef.current?.abort();
```
Note: `AbortController.abort()` only stops the client-side wait — the FastAPI route is a sync `def` (confirmed `data-service/app.py` L1174), so the server-side `httpx.post()` already in flight is not interrupted. This matches D-07's documented expectation exactly (RESEARCH Pattern 3) — no server-side change needed to make this true.

## Metadata

**Analog search scope:** `ui-v2/src/screens/`, `ui-v2/src/lib/`, `ui-v2/src/components/{forms,display}/`, `dg-reasoner/`, `data-service/app.py`
**Files scanned:** `ReasonerScreen.jsx`, `reasonerApi.js`, `GraphScreen.jsx` (targeted range), `SessionHistory.jsx` (targeted range), `Button.jsx`, `Badge.jsx`, `dg-reasoner/reasoning.py`, `dg-reasoner/ontology_export.py` (targeted range), `dg-reasoner/tests/test_routes.py` (targeted range), `data-service/app.py` (targeted ranges L560-590, L1141-1220)
**Pattern extraction date:** 2026-07-12
