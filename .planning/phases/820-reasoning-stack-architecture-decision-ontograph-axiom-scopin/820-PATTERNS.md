# Phase 820: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping - Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 8 (all new; phase produces documents + a throwaway spike, no production code)
**Analogs found:** 6 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `spec/LPG-OWL-MAPPING.md` | config/spec (durable doc) | transform (schema mapping) | `spec/DATABASE.md` | exact (same directory, same "schema reference doc" role) |
| `.planning/phases/820-.../820-DECISION.md` | doc (decision record) | transform (evidence → conclusion) | `spec/DECISIONS.md` | exact (ADR format, same repo) |
| `.planning/PROJECT.md` Key Decisions row edit | config (planning table) | CRUD (update existing row) | `.planning/PROJECT.md` itself, line 134 (Pending sidecar row) | exact — editing existing table, not a new file |
| `spike/requirements.txt` | config | batch | `data-service/requirements.txt` | role-match (unpinned vs pinned, but same "flat pip list" convention) |
| `spike/export.py` | service/utility (Neo4j → RDFLib export) | batch/transform | `data-service/app.py` (driver init + Cypher query block) | role-match (same neo4j driver usage pattern, different shape — read-only export vs FastAPI CRUD) |
| `spike/run_naive.py` / `spike/run_hybrid.py` | utility (throwaway script) | batch | `data-service/reasoner.py` (registry/id concept, not persistence) | partial — reasoner.py is a settings module, not a runner, but is the only reasoning-domain file in the repo |
| `spike/README.md` | doc | — | none | no analog — no other spike/README precedent in repo |
| `spec/LPG-OWL-MAPPING.md` ValidGraph informative sketch | doc subsection | — | `spec/DATABASE.md` ValidGraph section (lines describing DesignState/Run) | exact |

## Pattern Assignments

### `spec/LPG-OWL-MAPPING.md` (spec doc)

**Analog:** `spec/DATABASE.md` (full file is the schema source of truth; read lines 1-80)

**Structure pattern** (lines 1-16):
```markdown
# Database Schema (Neo4j Graph v4)

## Overview

All data lives in a **single Neo4j 5 database**. Logical separation uses the `graph` property on every node. Project isolation uses the `project` property. All Cypher queries filter by `project:'<n>'`.

## Graph Separation

| `graph` Value | Node Labels | Purpose |
|---------------|-------------|---------|
| `OntoGraph` | Class, DatatypeProperty, ObjectProperty | Domain ontology terms |
| `Metagraph` | Rule, Atom, Builtin, Var, Literal | SWRL rules and atom structures |
```

**Node/example pattern** (lines 18-60, repeated per label): a bolded label name, one-line description, then a fenced Cypher-literal example:
```
**Atom** — An individual SWRL atom (class assertion, property, or builtin)
\`\`\`
(:Atom {Atom_Id: "R_URB_HEIGHT_MAX_75_V_A1", iri: "ex:Building", SWRL_label: "Building(?b)", graph: "Metagraph", project: "1"})
\`\`\`
```

**Apply to LPG-OWL-MAPPING.md:** Mirror this exact "label bold — one-liner — fenced example" pattern per Metagraph/OntoGraph node, but use Turtle fenced blocks instead of Cypher-literal blocks (per CONTEXT.md's SWRL vocabulary table, e.g. the `:R_BUILDING_MAX_STOREY_9_V a swrl:Imp ; ...` example already drafted in RESEARCH.md § Pattern 1). Use a top-level `## Overview` section stating scope (normative for OntoGraph+Metagraph, informative for ValidGraph) exactly as DATABASE.md's Overview states graph separation up front. Because this is a new document (not modifying DATABASE.md), the planner has full discretion on internal headings per CONTEXT.md — but should keep the file next to DATABASE.md and cross-reference it (DATABASE.md § Graph Separation table is the authoritative node/property list this file must stay consistent with; do not duplicate — link back and only add the RDF-mapping columns).

---

### `.planning/phases/820-.../820-DECISION.md` (decision record with spike evidence)

**Analog:** `spec/DECISIONS.md` (ADR-1 through ADR-6, full file read)

**ADR entry pattern** (lines 1-19, ADR-1/ADR-2 shown as template):
```markdown
## ADR-2: SWRL Parsing Uses Bespoke Regex

**Context:** SWRL atom strings like `Building(?b)` and `greaterThan(?h, 75)` need parsing in C#.

**Decision:** Custom regex parser in `SwrlRuleParser.cs` instead of a vendor OWL/SWRL library.

**Consequences:** Lightweight, no heavy OWL dependency. But: fragile for edge cases, must be updated manually for new atom patterns. Covered by unit tests (`SwrlRuleParserTests.cs`).

---
```

**Apply to 820-DECISION.md:** Use the same three-part `**Context:** / **Decision:** / **Consequences:**` shape per decision (one ADR-style entry each for: (1) hybrid axiom-scoping, (2) sidecar confirmation). Extend the "Consequences" field with a `**Evidence:**` subsection unique to this phase (axiom counts, HermiT before/after stdout excerpts) since RESEARCH.md's Validation Architecture table requires the spike's assertions to be captured as evidence, and DECISIONS.md's existing ADRs have no evidence subsection to copy (this phase's addition, not a deviation from the pattern — DECISIONS.md ADRs are terse because they don't cite spike output; this phase's entries should follow the same Context/Decision/Consequences skeleton but append Evidence at the end, still capped at what fits one ADR block).

---

### `.planning/PROJECT.md` Key Decisions table (row edit, not new file)

**Analog:** the table itself, line 134 (existing Pending row) plus the "✓ Good"/"— Pending" convention visible across lines 107-134

**Row pattern** (existing, to be edited in place — read via Bash grep above):
```
| Reasoning runs in new `dg-reasoner` sidecar (Owlready2/HermiT/Openllet + pySHACL), not embedded in `data-service` | Isolates the JVM subprocess's failure modes (hang/OOM/crash) from `data-service`'s Speckle-publish/validation-run hot path; DL reasoning is worst-case exponential and the rule corpus grows unboundedly | — Pending — v8.2 (research-recommended, resolves STACK.md vs ARCHITECTURE.md conflict) |
```

**Apply:** Flip `— Pending — v8.2 (...)` to `✓ Shipped — v8.2 (spike evidence: see 820-DECISION.md)` (or `✓ Good`, matching the verb used by other shipped rows — `✓ Shipped` is used for rows tied to a specific phase's deliverable, e.g. line "Var merge key includes `project`" → `✓ Shipped — v3.0 Phase 7`; use that verb since this row cites a phase artifact). Add a **new row** for the axiom-scoping decision itself (hybrid TBox union), following the same 3-column `| Decision | Rationale | Outcome |` shape, Outcome citing `820-DECISION.md`.

---

### `spike/requirements.txt` (pinned pip list)

**Analog:** `data-service/requirements.txt` (full file, 7 lines, read above)

**Pattern:** Flat list, one package per line, pin only where the codebase already pins (`specklepy==3.2.4`), otherwise bare package name. Spike deviates intentionally per RESEARCH.md (all three spike packages pinned: `owlready2==0.51`, `rdflib==7.6.0`, `neo4j==6.2.0`) since it's throwaway and reproducibility of the exact spike run matters more than picking up patches — follow RESEARCH.md's own `requirements.txt` block (already fully specified in RESEARCH.md § Standard Stack → Installation), not data-service's unpinned convention.

---

### `spike/export.py` (Neo4j → RDFLib export)

**Analog:** `data-service/app.py` lines 1-67 (imports + driver init)

**Imports pattern** (lines 1-17):
```python
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Any
import time
import urllib.request
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from neo4j import GraphDatabase
from neo4j.graph import Node, Path, Relationship
from pydantic import BaseModel, Field
```

**Driver init pattern** (lines 63-67):
```python
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
```

**Apply to spike/export.py:** Reuse the exact `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` env-var names and default fallback pattern (matches RESEARCH.md's Security Domain requirement to read credentials from env vars, never hardcode). Import `from neo4j import GraphDatabase` the same way. Do NOT import FastAPI/pydantic (spike is a standalone script, not a service) — only the neo4j driver import line and `from __future__ import annotations` / `os` / `pathlib` carry over. Use RESEARCH.md's own already-drafted `METAGRAPH_QUERY`/`ONTOGRAPH_QUERY` Cypher (§ Code Examples "Correct export scoping") which is the concrete query this file must contain — scoped by label per Pitfall 1, not by the `graph` property.

**Error handling note:** `data-service/app.py` has no try/except around the driver init itself (connection errors surface at query time via FastAPI's exception handling); the throwaway spike can be even simpler — let exceptions propagate to stdout/traceback, since `spike/README.md` documents manual reproduction, not automated resilience.

---

### `spike/run_naive.py` / `spike/run_hybrid.py` (reasoner-invocation scripts)

**Analog:** `data-service/reasoner.py` (full file, 67 lines, read above) — weak analog (it's a settings-persistence module, not a runner), used only for the reasoner-id vocabulary (`hermit`/`pellet`) and the file's own docstring convention.

**Docstring/header convention** (lines 1-8):
```python
"""Reasoner registry and settings persistence — HermiT/Pellet placeholder selection.

Mirrors the connectors.py / llm_gateway settings-persistence style: JSON file
under DATA_DIR, small load/save helpers, module-level file path constant.

Reasoner settings need no encryption (no secrets). The registry is structured
so real integrated reasoners can later carry status: "integrated".
"""
```

**Apply:** Give both run scripts a similar one-paragraph module docstring stating what part (a)/(b) of the spike proves and what "Source:" it follows (RESEARCH.md already drafts the literal script bodies in § Code Examples "Owlready2 spike skeleton" — copy those verbatim as the starting point, they are the authoritative content, not this repo's reasoner.py). No settings-persistence machinery is needed here (spike is stateless, single-run) — reasoner.py's `load_settings`/`save_settings` JSON-file pattern is NOT applicable to the spike scripts themselves; it only informs the recognized reasoner-id vocabulary (`"hermit"`) if `820-DECISION.md` needs to reference the production reasoner registry for consistency.

---

### `spike/README.md`

**No analog found.** No existing README/reproduction-steps precedent in this repo's throwaway-script style. Use RESEARCH.md's own "Environment Availability" and "Validation Architecture → Quick run command" sections directly as the README's content skeleton (env vars to set, JRE/container requirement, `python spike/run_naive.py && python spike/run_hybrid.py` command) — RESEARCH.md is the primary source here, not a codebase analog.

## Shared Patterns

### Credential handling (env vars, never hardcoded)
**Source:** `data-service/app.py` lines 63-65 (`NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` via `os.getenv` with dev-safe defaults)
**Apply to:** `spike/export.py`, `spike/README.md` (documents the three env vars)
```python
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
```
Note: RESEARCH.md's Security Domain section explicitly calls out this exact requirement for the spike since `spike/` is committed to git.

### Decision-recording (ADR three-part shape)
**Source:** `spec/DECISIONS.md` (all 6 ADRs)
**Apply to:** `820-DECISION.md`'s two entries, and the new/edited `.planning/PROJECT.md` Key Decisions rows (condensed to the table's 3-column shape instead of the full ADR prose)
```markdown
**Context:** ...
**Decision:** ...
**Consequences:** ...
```

### Schema-reference doc shape (bold label — description — fenced example)
**Source:** `spec/DATABASE.md` lines 18-60
**Apply to:** `spec/LPG-OWL-MAPPING.md`'s per-node/per-relationship mapping entries

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `spike/README.md` | doc | — | No prior spike/throwaway-script directory exists in this repo; use RESEARCH.md's Environment Availability + Validation Architecture sections as the direct content source instead |
| `spike/run_naive.py` / `spike/run_hybrid.py` (script bodies) | utility | batch | No OWL/reasoning runner script precedent exists; `data-service/reasoner.py` only supplies the id vocabulary, not a runnable-script pattern — use RESEARCH.md's already-drafted Owlready2 skeletons (§ Code Examples) as the primary source |

## Metadata

**Analog search scope:** `spec/` (DATABASE.md, DECISIONS.md), `data-service/` (app.py, reasoner.py, requirements.txt), `.planning/PROJECT.md`
**Files scanned:** 5 read directly + 1 grep (PROJECT.md Key Decisions table) + graphify query (returned no closer analog — this phase's outputs are docs/spike scripts outside graphify's code-symbol graph)
**Pattern extraction date:** 2026-07-11
