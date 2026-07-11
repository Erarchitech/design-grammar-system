---
phase: 814-reasoner-screen
reviewed: 2026-07-11T20:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - data-service/reasoner.py
  - data-service/tests/test_reasoner.py
  - ui-v2/src/lib/reasonerApi.js
  - data-service/app.py
  - ui-v2/src/screens/ReasonerScreen.jsx
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 814: Code Review Report -- Reasoner Screen

**Reviewed:** 2026-07-11T20:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 814 reasoner-screen implementation: a settings persistence backend (`reasoner.py`), two FastAPI endpoints in `app.py`, a JS API client (`reasonerApi.js`), and a React screen (`ReasonerScreen.jsx`). The implementation correctly fulfills the REAS-01..03 contract (GET returns registry, PUT persists selection, unknown IDs rejected with 422). Four warnings were found: a race condition in file-based settings persistence (no locking, multi-worker unsafe), a design fragility in `save_settings` that overwrites the entire file (will silently drop future extended fields), missing error handling for disk-write failures in the PUT endpoint, and an unused `project` prop in the React component. Four info items note code duplication and minor quality gaps.

## Warnings

### WR-01: Race condition in settings persistence under multiple workers

**File:** `data-service/reasoner.py:60-66`
**Issue:** `save_settings` calls `write_text()` on the shared settings file with no file locking or atomic-write pattern. FastAPI/uvicorn commonly runs with multiple workers (e.g., `uvicorn --workers 4`). Two concurrent `PUT /reasoner/settings` requests from different workers will both open and overwrite the same file; the last writer wins, silently losing one of the selections. This is the same class of TOCTOU race as unsynchronized file-based settings stores.

Additionally, `load_settings` at line 52 reads the file while a concurrent `save_settings` may be mid-write, potentially reading a truncated or partially-written file, which `json.JSONDecodeError` catches and silently returns `{}` -- the selection appears lost from the reader's perspective.

**Fix:** Adopt a two-step atomic write pattern: write to a temporary file, then `os.replace()` (atomic on POSIX, near-atomic on Windows). Add a `threading.Lock` for single-process safety, and note in the docstring that multi-worker deployments share the file and should either pin to 1 worker for this endpoint or accept last-writer-wins semantics as a documented limitation.

```python
import tempfile
import threading

_settings_lock = threading.Lock()

def save_settings(settings: dict[str, Any]) -> None:
    REASONER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = REASONER_SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(REASONER_SETTINGS_FILE)
```

If multi-worker is desired, document that this endpoint is intended for an admin UI with exclusive access and consider a database-backed store.

---

### WR-02: `save_settings` overwrites entire file, silently dropping unknown fields

**File:** `data-service/app.py:1155`
**Issue:** The PUT handler calls `reasoner.save_settings({"selected": payload.reasoner})`, which writes only `{"selected": "hermit"}` to the file. This replaces the entire file content. If the `reasoner-settings.json` format is ever extended with additional fields (e.g., `"mode"`, `"timeout"`, `"options"`), any subsequent PUT call will wipe them. The correct pattern (used elsewhere in the codebase, e.g., the LLM settings flow at lines 943-955) is: `load_settings()` to get the full dict, mutate the relevant key, `save_settings()` the full dict.

**Fix:**

```python
@app.put("/reasoner/settings")
def put_reasoner_settings(payload: ReasonerSettingsPayload):
    if payload.reasoner not in reasoner.REASONER_IDS:
        raise _structured_error_response(...)
    settings = reasoner.load_settings()
    settings["selected"] = payload.reasoner
    reasoner.save_settings(settings)
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": payload.reasoner,
    }
```

---

### WR-03: No error handling for `save_settings` disk-write failure

**File:** `data-service/app.py:1145-1159`
**Issue:** `reasoner.save_settings()` (reasoner.py:60-66) can raise `OSError` if the data directory is not writable, disk is full, or a permissions issue occurs. The endpoint has no try-except around the call, so this propagates as a raw FastAPI 500 error. While a 500 is acceptable for an unexpected failure, providing a structured error response (matching the style of `_structured_error_response` used elsewhere) would be more informative for API consumers and consistent with the codebase patterns.

**Fix:**

```python
@app.put("/reasoner/settings")
def put_reasoner_settings(payload: ReasonerSettingsPayload):
    if payload.reasoner not in reasoner.REASONER_IDS:
        raise _structured_error_response(...)
    try:
        reasoner.save_settings({"selected": payload.reasoner})
    except OSError as exc:
        raise _structured_error_response(
            f"Failed to persist reasoner selection: {exc}",
            "Check that the data directory is writable.",
            "REASONER_PERSIST_ERROR",
            500,
        ) from exc
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": payload.reasoner,
    }
```

---

### WR-04: Unused `project` prop in ReasonerScreen component

**File:** `ui-v2/src/screens/ReasonerScreen.jsx:9`
**Issue:** The component destructures `{ active, onBack, project }` but `project` is never referenced anywhere in the component body or JSX. This is dead code -- callers may pass a project prop that is silently ignored. If the reasoner settings are intended to be project-scoped in the future, the prop is a signal without implementation; otherwise it should be removed to avoid confusion.

**Fix:** Remove `project` from the destructured props, or if the intention is to scope reasoner settings per project, implement project-scoped storage (e.g., include `project` in the saved settings dict) and filter accordingly.

---

## Info

### IN-01: Duplicated load-settings logic between `useEffect` and `handleRetry`

**File:** `ui-v2/src/screens/ReasonerScreen.jsx:25-31` and `:53-59`
**Issue:** The same `getReasonerSettings().then().catch().finally()` block appears in two places: the mount effect and the retry handler. Duplication of async fetch logic creates a maintenance hazard (fix a bug in one, miss the other).

**Fix:** Extract into a shared helper function (e.g., `loadSettings`) called from both paths:

```jsx
const loadSettings = React.useCallback(() => {
  setLoading(true);
  setLoadError("");
  setSaveError("");
  getReasonerSettings()
    .then((s) => {
      setReasoners(s.reasoners || []);
      setSelected(s.selected || null);
    })
    .catch((err) => setLoadError(err.message || "Failed to load settings"))
    .finally(() => setLoading(false));
}, []);
```

---

### IN-02: `load_settings` silently swallows `OSError`

**File:** `data-service/reasoner.py:53`
**Issue:** The `except (OSError, json.JSONDecodeError)` clause at line 53 returns `{}` for any filesystem error (permissions, missing directory that is not the file's parent). If the file exists but is unreadable due to permissions, the system provides no diagnostic log or warning. This can make deployment issues (e.g., container running as non-root user, `/app/data` not mounted) hard to diagnose.

**Fix:** Log the error at warning level before returning the empty dict:

```python
import logging
logger = logging.getLogger(__name__)

try:
    payload = json.loads(REASONER_SETTINGS_FILE.read_text(encoding="utf-8"))
except OSError:
    logger.warning("Cannot read reasoner settings file", exc_info=True)
    return {}
except json.JSONDecodeError:
    return {}
```

---

### IN-03: Missing React effect cleanup on unmount

**File:** `ui-v2/src/screens/ReasonerScreen.jsx:20-32`
**Issue:** The `useEffect` has no cleanup function. If the component unmounts before the fetch resolves, `setReasoners`, `setSelected`, or `setLoading` will be called on an unmounted component. In React 18+ strict mode this logs warnings; more importantly, it can cause a brief flash of stale data if the component is rapidly re-mounted (the old promise resolves after the new one is in flight).

**Fix:** Use an abort controller or a mounted flag:

```jsx
React.useEffect(() => {
    if (!active) return;
    let mounted = true;
    setLoading(true);
    setLoadError("");
    getReasonerSettings()
      .then((s) => {
        if (!mounted) return;
        setReasoners(s.reasoners || []);
        setSelected(s.selected || null);
      })
      .catch((err) => { if (mounted) setLoadError(...) })
      .finally(() => { if (mounted) setLoading(false) });
    return () => { mounted = false; };
}, [active]);
```

---

### IN-04: `reasoner` field in `ReasonerSettingsPayload` allows empty string

**File:** `data-service/app.py:1131-1132`
**Issue:** The Pydantic model defines `reasoner: str` with no `min_length` constraint. An empty string passes Pydantic field validation but then fails the `not in reasoner.REASONER_IDS` check, producing the generic "Unknown reasoner" error message instead of a more helpful "reasoner id is required" message.

**Fix:** Add a `min_length` constraint:

```python
class ReasonerSettingsPayload(BaseModel):
    reasoner: str = Field(..., min_length=1)
```

---

_Reviewed: 2026-07-11T20:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
