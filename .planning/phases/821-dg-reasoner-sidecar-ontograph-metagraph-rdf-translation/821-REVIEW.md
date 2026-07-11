---
phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
reviewed: 2026-07-11T23:09:15Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - data-service/app.py
  - dg-reasoner/app.py
  - dg-reasoner/ontology_export.py
  - dg-reasoner/reasoning.py
  - dg-reasoner/requirements.txt
  - dg-reasoner/tests/conftest.py
  - dg-reasoner/tests/fixtures/metagraph_fixture.json
  - dg-reasoner/tests/test_health.py
  - dg-reasoner/tests/test_n10s_smoke.py
  - dg-reasoner/tests/test_ontology_export.py
  - dg-reasoner/tests/test_roundtrip_integration.py
  - dg-reasoner/tests/test_routes.py
  - ontology/dg-disjointness.ttl
findings:
  critical: 3
  warning: 6
  info: 5
  total: 14
status: issues_found
---

# Phase 821: Code Review Report

**Reviewed:** 2026-07-11T23:09:15Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the new `dg-reasoner` sidecar (Cypher→RDF translator, hybrid HermiT
consistency check, pySHACL plumbing) plus the 49-line proxy addition to
`data-service/app.py` and the new `ontology/dg-disjointness.ttl` overlay.
`git diff 369e0bbef880c21a807a168a99a9b4a885df5c87^..HEAD` confirms every
`dg-reasoner/*` file is wholly new for this phase; `data-service/app.py`'s
only change is the `POST /reasoner/consistency` proxy route.

The unit-test tier (`test_health.py`, `test_ontology_export.py`,
`test_routes.py`) is solid and the fixture-driven structural tests for
`build_graph()` genuinely exercise ARG.pos / HAS_BODY / HAS_HEAD.order
reification for the documented worked example. However, three findings
undermine the two riskiest pieces the phase brief called out explicitly:

1. The `data-service` → `dg-reasoner` proxy's read timeout (5s) is far
   shorter than the sidecar's own advertised hard reasoning timeout (90s),
   so the proxy will almost always time out on real HermiT runs before the
   sidecar can finish — the feature is effectively non-functional for
   anything but trivial ontologies.
2. `reasoning.py`'s timeout-kill path (`process.terminate()`) only signals
   the Python `multiprocessing.Process`, not the Java/HermiT subprocess
   Owlready2 shells out to underneath it (confirmed by the Dockerfile:
   `openjdk-21-jre-headless`, "HermiT via owlready2 shells out to java") —
   risking orphaned JVM processes on every timeout, which breaks the D-09
   "hard timeout" resource-bounding contract the module's own docstring
   claims to provide.
3. `ontology_export.py` silently coerces a missing/`null` `ARG.pos` to `0`
   with zero validation. For `BuiltinAtom`s (where argument order is
   logically significant — `swrlb:greaterThan(?h, 9)` is not the same
   constraint as `swrlb:greaterThan(9, ?h)`) this can silently produce a
   wrong or Neo4j-record-order-dependent `swrl:arguments` list with no
   warning anywhere, exactly the "silent data loss" risk the phase brief
   flagged as highest priority.

## Critical Issues

### CR-01: Reasoner proxy read timeout (5s) is shorter than the sidecar's own hard timeout (90s)

**File:** `data-service/app.py:1182-1194`
**Issue:**
```python
response = httpx.post(
    f"{DG_REASONER_URL}/reason/consistency",
    json={"project": payload.project, "engine": payload.engine},
    timeout=httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0),
)
```
`dg-reasoner/reasoning.py` and `dg-reasoner/app.py` both default
`DG_REASONER_TIMEOUT_SECONDS` to **90 seconds** — that is the sidecar's own
documented hard wall-clock bound on the HermiT/JVM subprocess
(`reasoning.py:47-49`, `app.py:28-29`). The proxy route added here uses a
`read=5.0` second httpx timeout. Any real HermiT consistency check against
a non-trivial ontology (JVM startup alone is commonly >1-2s; OWL loading +
reasoning easily exceeds 5s) will raise `httpx.TimeoutException` in the
proxy and return a spurious `504 REASONER_TIMEOUT` to the caller **even
though the sidecar is still working and may well complete successfully
within its own 90-second budget**. As written, `POST /reasoner/consistency`
will falsely report "timeout" for the overwhelming majority of legitimate
requests, making the D-06 proxy non-functional for its stated purpose. The
sidecar-hang protection this route is meant to provide is a legitimate
goal, but the chosen value defeats the feature itself rather than just
bounding worst-case hangs.
**Fix:** Raise the read timeout to comfortably exceed
`DG_REASONER_TIMEOUT_SECONDS` (e.g. `read=95.0`, or read the env var so the
two stay in lock-step), while keeping `connect`/`write`/`pool` short:
```python
timeout=httpx.Timeout(connect=2.0, read=95.0, write=2.0, pool=2.0),
```
If a genuinely fast fail-fast UX is required, consider an async job/poll
pattern instead of shrinking the synchronous read timeout below the known
worst-case duration.

### CR-02: `process.terminate()` may not kill the underlying Java/HermiT subprocess, risking orphaned JVMs on every timeout

**File:** `dg-reasoner/reasoning.py:140-165`
**Issue:**
```python
process.start()
process.join(timeout_seconds)

if process.is_alive():
    process.terminate()
    process.join(5)
    return {"timeout": True}
```
`_reason_worker` (line 115-137) calls Owlready2's `sync_reasoner()`, which
shells out to the bundled HermiT JAR via a Java `subprocess` (confirmed by
`dg-reasoner/Dockerfile:3-9`: "HermiT via owlready2 shells out to java").
`multiprocessing.Process.terminate()` sends `SIGTERM` only to the immediate
child PID (the Python worker process) — it does **not** signal any further
descendant processes that child may have spawned (Java is not in the same
process group and `terminate()`/`kill()` are not propagated to
grandchildren). If the worker is blocked inside `subprocess.Popen(...).wait()`
/`communicate()` waiting on the JVM when SIGTERM arrives, killing the
Python process typically does **not** kill the running Java process; it
becomes an orphan re-parented to init and continues consuming CPU/memory
until it finishes on its own. Every timed-out consistency check therefore
risks leaking a live JVM process, defeating the very purpose of the "hard
wall-clock bound" this module's docstring (lines 1-20) claims to enforce
("Killing the child process also kills its java grandchild (D-09)" — this
claim is not backed by anything in the code).
**Fix:** Put the worker (and therefore the Java subprocess) in its own
process group so the whole group can be killed, e.g.:
```python
# in _reason_worker, before invoking sync_reasoner(), or by launching the
# multiprocessing.Process with a wrapper that calls os.setsid() (POSIX):
def _reason_worker(nt_path, queue):
    import os
    os.setsid()
    ...

# and on timeout, kill the whole group instead of just the child:
if process.is_alive():
    os.killpg(process.pid, signal.SIGKILL)
    process.join(5)
    return {"timeout": True}
```
At minimum, verify empirically (a load test that forces several timeouts)
that no `java` process survives `process.terminate()`, and track/kill any
subprocess PID that Owlready2 exposes if `os.setsid()` is not viable in the
container.

### CR-03: `ARG.pos` silently defaults to `0` with no validation — can silently corrupt `swrl:arguments` order for BuiltinAtoms

**File:** `dg-reasoner/ontology_export.py:281-295, 346-363`
**Issue:** The ARG-edge collection loop coerces a missing/`null` `pos`
straight to `0` with no logging or validation:
```python
pos = int(record["pos"]) if record["pos"] is not None else 0
...
args_by_atom.setdefault(atom_id, []).append((pos, term))
```
`_atom_completeness_reason` (lines 184-204) only requires a `BuiltinAtom`
to have **at least one** ARG edge (`None if arg_positions else "BuiltinAtom
has no ARG edges"`) — it never checks that positions are distinct or valid.
So a `BuiltinAtom` with, say, one edge missing `pos` and two edges with
real positions passes completeness trivially (`arg_positions` is simply
non-empty). At emission time:
```python
arg_list = sorted(args_by_atom.get(atom_id, []), key=lambda pair: pair[0])
...
graph.add((a_iri, SWRL.arguments, make_argument_list(graph, [term for _, term in arg_list])))
```
If **two or more** ARG edges for the same builtin atom end up with the
defaulted `pos=0` (e.g. two edges both missing `pos` due to an upstream
ingestion bug), Python's stable sort leaves them in whatever order
`ARG_QUERY` happened to return them in — and `ARG_QUERY` (lines 69-73) has
**no `ORDER BY`**, so that order is Neo4j-implementation-defined and not
guaranteed reproducible. Argument order is semantically load-bearing for
builtins (`swrlb:greaterThan(?h, 9)` ≠ `swrlb:greaterThan(9, ?h)`), so this
path can silently produce a wrong or nondeterministic SWRL constraint in
the canonical Turtle export with **no warning printed anywhere** — unlike
the non-builtin branch (line 356-363), which at least prints a warning for
out-of-range `pos` values. This is exactly the "silent data loss" risk the
phase brief flagged `ARG.pos` reification as highest-risk for.
**Fix:** Treat a missing/duplicate `pos` on a `BuiltinAtom`'s ARG edges as
an incompleteness reason (route the atom to `dgm:SkippedAtom` instead of
silently defaulting), and validate uniqueness of positions before sorting:
```python
def _atom_completeness_reason(atom_type, has_refers_to_target, arg_positions, raw_positions):
    ...
    if atom_type == BUILTIN_ATOM_TYPE:
        if not arg_positions:
            return "BuiltinAtom has no ARG edges"
        if None in raw_positions or len(raw_positions) != len(set(raw_positions)):
            return "BuiltinAtom has missing or duplicate ARG.pos values"
        return None
```
and pass the un-defaulted `record["pos"]` values through for this check
rather than defaulting to `0` before it can be inspected.

## Warnings

### WR-01: Neo4j session held open for the full HermiT run (up to 90s) instead of being released after the graph is built

**File:** `dg-reasoner/app.py:73-78, 87-88`; `dg-reasoner/reasoning.py:183-190, 231-238`
**Issue:** `app.py`'s routes open the session and pass it in:
```python
with driver.session() as session:
    result = reasoning.run_consistency(payload.project, payload.engine, session=session)
```
Inside `reasoning.run_consistency`, the session is only closed when the
function itself opened it (`owns_session = session is None`). Since
`app.py` always injects an already-open session, `owns_session` is `False`,
so `reasoning.py`'s own `finally: session.close()` never fires — the
session stays open for the *entire* pipeline (union build, HermiT
subprocess up to `DG_REASONER_TIMEOUT_SECONDS`), and is only released when
`app.py`'s outer `with` block exits after `run_consistency` returns. The
session is not needed once `_hybrid_union` finishes pulling data (line 187)
— holding it open for up to 90 seconds per request needlessly occupies a
Neo4j driver connection-pool slot and could exhaust the pool under
concurrent consistency-check load, or trip Neo4j-side idle/session
timeouts.
**Fix:** Close (or scope) the session in `app.py` before invoking the
long-running consistency check, e.g. build the union graph inside the
`with` block and hand the already-built `Graph` (not the live session)
into a separate synchronous reasoning call, or have `run_consistency`
close any injected session itself right after `_hybrid_union` returns.

### WR-02: `HAS_BODY`/`HAS_HEAD.order` also silently defaults to `0` with no validation

**File:** `dg-reasoner/ontology_export.py:297-305`
**Issue:**
```python
body_head.setdefault(rule_id, {}).setdefault(rel, []).append(
    (int(order) if order is not None else 0, atom_id)
)
```
Same defaulting pattern as CR-03, and `BODY_HEAD_QUERY` (lines 57-61) also
has no `ORDER BY`. If `order` is ever missing/duplicated for more than one
atom within the same rule+relation, the resulting `swrl:AtomList` order
becomes dependent on Neo4j's unspecified record order, with no warning.
This is somewhat lower severity than CR-03 because SWRL rule body/head
order is not logically significant for HermiT's reasoning (conjunction is
commutative), but it is still a fidelity/traceability defect against the
"structural fidelity" goal the test suite (`test_ontology_export.py`)
explicitly exercises for this exact ordering.
**Fix:** Same approach as CR-03 — surface missing/duplicate `order` values
as an incompleteness reason (or at minimum a printed warning) rather than
silently defaulting to `0`.

### WR-03: `multiprocessing.Process` (fork start method) spawned from inside a threaded FastAPI request handler

**File:** `dg-reasoner/reasoning.py:140-165`
**Issue:** `python:3.11-slim` is Linux, where the default `multiprocessing`
start method is `fork`. `_reason_with_timeout` is invoked synchronously
from a FastAPI `def` route handler, which Starlette/Uvicorn runs inside a
worker thread pool alongside the asyncio event loop. Forking mid-request
from a multi-threaded process is a well-known hazard: only the calling
thread is duplicated in the child, but any locks held by *other* threads
at the instant of `fork()` (e.g. internal locks in `logging`, `ssl`, or
the `neo4j` driver's connection pool) are copied in whatever state they
were in — if the child later touches anything protected by such a lock
(e.g. the implicit `print()` calls in `_reason_worker`), it can hang
indefinitely with no relationship to `DG_REASONER_TIMEOUT_SECONDS` (the
hang happens before the worker ever reaches the timed section). This is
intermittent and load-dependent rather than deterministic, which makes it
hard to catch in the always-on unit tests.
**Fix:** Explicitly request the `spawn` start method for this process
(`multiprocessing.get_context("spawn").Process(...)`), which avoids
inheriting parent-process lock state entirely at the cost of slightly
higher subprocess startup latency — an acceptable trade-off given the
90-second timeout budget already in place.

### WR-04: `POST /shacl/validate` has no timeout guard at all

**File:** `dg-reasoner/app.py:81-88`; `dg-reasoner/reasoning.py:222-251`
**Issue:** `run_consistency` is wrapped in a hard `DG_REASONER_TIMEOUT_SECONDS`
subprocess bound (D-09). `run_shacl` has no equivalent protection —
`pyshacl_validate(...)` runs in-process with no timeout wrapper. Today this
is harmless because the shapes graph is deliberately empty ("Empty shapes
always conform, by construction" — line 240-243), but the module's own
docstring documents that "real shapes land in Phase 823." Once real SHACL
shapes are introduced, a slow or pathological validation (e.g. shapes with
heavy SPARQL-based constraints) could hang this route indefinitely with no
server-side guard, unlike the consistency endpoint.
**Fix:** Apply the same timeout-bounded subprocess pattern used for
`run_consistency` to `run_shacl` before Phase 823 introduces real shapes.

### WR-05: Hardcoded default Neo4j credential fallback duplicated into the new sidecar files

**File:** `dg-reasoner/app.py:26`; `dg-reasoner/reasoning.py:45`
**Issue:**
```python
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
```
This mirrors an existing convention in `data-service/app.py`, but it is
still a literal hardcoded credential fallback, matches the classic
hardcoded-secret pattern, and is now duplicated a third time across the
codebase. If any deployment forgets to set `NEO4J_PASSWORD`, both services
silently authenticate with a well-known weak password rather than failing
loudly.
**Fix:** At minimum, keep consistent with the existing convention, but
consider failing fast (raise at startup) when `NEO4J_PASSWORD` is unset in
non-dev environments, rather than silently falling back to a known
default.

### WR-06: Pre-existing Cypher-injection surface in `data-service/app.py` (not part of this phase's diff, found while reviewing the required file)

**File:** `data-service/app.py:278-279, 878-882`
**Issue:** `create_node` builds Cypher via unsanitized f-string label
interpolation:
```python
@app.post("/create_node/")
def create_node(label: str, name: str):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{label: $name}})", name=name)
```
`label` is attacker-controlled and injected directly into the query text
(Neo4j has no way to bind-parameter a label name), allowing arbitrary
Cypher clause injection via the `label` field. Separately, `is_write_query`
(lines 278-279) gates the `/mcp` `neo4j_query` tool with a keyword
blocklist (`CREATE|MERGE|DELETE|SET|REMOVE|DROP`) that is bypassable via
camelCase procedure names with no word boundary around the keyword (e.g.
`db.index.fulltext.createNodeIndex` — `\bcreate\b` does not match "create"
immediately followed by "NodeIndex"), or via write/SSRF-capable APOC
procedures that don't contain any of the blocklisted words at all. This is
pre-existing code untouched by this phase's diff
(`git diff 369e0bbef880c21a807a168a99a9b4a885df5c87^..HEAD -- data-service/app.py`
only shows the new `/reasoner/consistency` proxy route), so it is flagged
here for visibility rather than as a defect introduced by this phase.
**Fix:** Validate `label` against an allowlist of known node labels before
interpolation (or remove the endpoint if unused); replace the read-only
Cypher gate with a real query classifier (e.g. `EXPLAIN`-based dry run, or
an allowlisted procedure list) rather than a keyword blocklist.

## Info

### IN-01: Redundant exception tuple in the sidecar's health check

**File:** `dg-reasoner/app.py:42`
**Issue:**
```python
except (ServiceUnavailable, Neo4jError, Exception):  # pragma: no cover - defensive
```
`Exception` already subsumes `ServiceUnavailable` and `Neo4jError`, making
the tuple misleading — it reads as if three specific cases are handled,
but it is really just a bare `except Exception`.
**Fix:** `except Exception:` (or narrow it to the two Neo4j-specific types
if a bare catch-all isn't actually desired).

### IN-02: Unused/dead `DG_REASONER_TIMEOUT_SECONDS` constant in `app.py`

**File:** `dg-reasoner/app.py:28-29`
**Issue:**
```python
# Reserved for the reasoning pipeline's hard subprocess timeout (Plan 821-03).
DG_REASONER_TIMEOUT_SECONDS = int(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90"))
```
This module-level constant is never referenced anywhere else in `app.py` —
the actual timeout logic lives entirely in `reasoning.py`'s own copy of the
same env var (`reasoning.py:49`). Having two independent declarations of
the same env-driven constant is confusing and can drift silently if only
one file's default is ever updated.
**Fix:** Remove the unused declaration from `app.py`, or import it from
`reasoning` if it needs to be surfaced from this module.

### IN-03: Emission code's "unrecognized Atom.type" fallback is inconsistent with its own completeness check

**File:** `dg-reasoner/ontology_export.py:196-204, 333-339, 356-363`
**Issue:** `_atom_completeness_reason` treats an atom of an unrecognized
`type` like a binary atom, requiring `{1, 2} <= arg_positions` (lines
202-204). But the emission code defaults any unrecognized type to
`SWRL.ClassAtom` (a unary SWRL atom class that should only carry
`argument1`):
```python
swrl_type, predicate = ATOM_TYPE_MAP.get(atom_type, (SWRL.ClassAtom, SWRL.classPredicate))
```
The subsequent arg-emission loop (lines 356-363) is unconditional on
`swrl_type` and will still emit both `argument1` and `argument2` for such
an atom, producing an internally inconsistent
`swrl:ClassAtom`+`argument2` combination. This path is currently
unreachable given `Atom.type` is schema-constrained to four legal values
(`cypher_template.txt`), so it's low-severity, but the fallback should
either fully commit to "treat as ClassAtom" (drop args beyond pos 1) or
route to `dgm:SkippedAtom` instead of emitting a hybrid, non-spec-legal
atom shape.
**Fix:** Make the fallback route unrecognized-type atoms to
`dgm:SkippedAtom` (captured-not-dropped, consistent with the module's
stated philosophy) rather than guessing `ClassAtom` and emitting mismatched
arguments.

### IN-04: Lazy Neo4j driver singleton has no lock, allowing duplicate driver construction under concurrent first requests

**File:** `dg-reasoner/reasoning.py:59-74`
**Issue:**
```python
_driver = None

def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver
```
Two concurrent requests that both hit `_get_driver()` before either has
assigned `_driver` can each construct a separate `GraphDatabase.driver()`
instance; the second overwrites the first, which is never explicitly
closed. Low impact (small resource waste, not a correctness bug), but
worth a lock given this runs in a multi-threaded ASGI server.
**Fix:** Guard the lazy initialization with a `threading.Lock()`.

### IN-05: Inconsistent dependency pinning in `dg-reasoner/requirements.txt`

**File:** `dg-reasoner/requirements.txt:1-13`
**Issue:** `owlready2`, `rdflib`, `pyshacl`, `owlrl`, `neo4j`, and `starlette`
are all pinned to exact versions, but `fastapi`, `uvicorn`, `pytest`, and
`httpx` are left completely unpinned. This undermines reproducible builds
for exactly the dependencies (`fastapi`/`httpx`) most load-bearing for this
phase's new HTTP surface.
**Fix:** Pin `fastapi`, `uvicorn`, `pytest`, and `httpx` to known-good
versions, consistent with the rest of the file.

---

_Reviewed: 2026-07-11T23:09:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
