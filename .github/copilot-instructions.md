# Copilot Instructions for design-grammar-system

## Overview
This repo orchestrates a Dockerized pipeline for parsing architectural design rules into SWRL + graph atoms, generating a custom ontology, and storing both in Neo4j. LLM-based Cypher generation is constrained at inference time via structured prompts embedding the v3 schema and few-shot examples (no fine-tuned model required). It also includes a graph-query workflow (MCP) that turns natural-language questions into read-only Cypher and returns a short answer. A lightweight graph-viewer UI provides ingest, query, and visualization.

## Current canonical graph model (v3)
Use the v3 schema as the source of truth for all code changes, prompts, generated Cypher, and UI labels.

### Graph separation
- `graph = 'OntoGraph'` for ontology terms.
- `graph = 'Metagraph'` for rules, atoms, variables, literals, and builtins.
- Every persisted node must include `project` and `graph`.

### Canonical node labels and properties
- `Class`: key `iri`, display property `label`
- `DatatypeProperty`: key `iri`, display property `SWRL_label`
- `ObjectProperty`: key `iri`, display property `label`
- `Builtin`: key `iri`, display property `label`
- `Rule`: key `Rule_Id`
- `Atom`: key `Atom_Id`; required properties `Atom_Id`, `type`, `iri`, `SWRL_label`, `project`, `graph`
- `Var`: key `name`
- `Literal`: key `lex` + `datatype`

## Canonical relationships
Use these relationship types in generated Cypher and UI assumptions:
- `HAS_BODY`
- `HAS_HEAD`
- `REFERS_TO`
- `ARG`

Do not use legacy assumptions like `Rule.id`, `Atom.id`, `Atom.Id`, `DatatypeProperty.label`, or `HAS_ATOM` unless you are explicitly writing a migration.

## Mandatory dependency propagation for schema v3
Whenever you change graph generation or query logic, update all affected layers together:
1. cypher template (`cypher_template.txt`)
2. dataset schema reference (`training/dataset_schema.json`)
3. n8n workflow prompts and validators
4. graph-viewer configuration
5. any Cypher templates or parsing logic in Python/JS

## Required property migrations
- `Rule.id` -> `Rule.Rule_Id`
- `DatatypeProperty.label` -> `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` -> `Atom.Atom_Id`
- add `Atom.iri`
- add `Atom.SWRL_label`

Any code that reads, renders, queries, validates, or exports the graph must be checked against these changes.

## Architecture

### Docker services (`docker-compose.yml`)
- **Neo4j** (`neo4j:5`): Single database, port 7474/7687. Auth: `neo4j/12345678`. Ontology and rules separated by `graph` property (`OntoGraph` / `Metagraph`).
- **n8n** (`n8nio/n8n`): Two workflows:
  - `n8n/workflows/rules-to-metagraph.json` → `/webhook/dg/rules-ingest`
  - `n8n/workflows/graph-query-mcp.json` → `/webhook/dg/graph-query`
- **Ollama** (`ollama/ollama:latest`): LLM inference, GPU-enabled, port 11435→11434. Default model: `llama3.1:latest` (env `OLLAMA_MODEL`).
- **data-service** (FastAPI): MCP endpoint (`/mcp`) plus in-memory execution tracking (`/execution-result`).
- **graph-viewer**: Static UI + Nginx proxy for `/neo4j`, `/n8n`, `/data-service`. Port 8080.

## LLM integration (prompt-based)

Instead of a fine-tuned model, Cypher generation is constrained at inference time
via structured prompts that embed the v3 schema rules and a few-shot example.

### Prompt structure for rules-ingest workflow
The `Build LLM Prompt` node in `rules-to-metagraph.json` constructs a prompt with:
1. **Schema constraints** — allowed labels, relationships, key properties, graph assignments.
2. **Node key conventions** — `Rule_Id`, `Atom_Id`, `SWRL_label`, etc.
3. **Semantic mapping** — how NL constraint phrases map to SWRL builtins.
4. **Few-shot example** — a complete v3-compliant Cypher block for a height violation rule.
5. **The user's NL rule** — appended at the end.

### Prompt structure for graph-query workflow
The `Build Cypher Prompt` node in `graph-query-mcp.json` constructs a prompt with:
1. **v3 data model description** — node labels, key/display properties, relationship types.
2. **Live schema context** — labels, relationships, property keys fetched from Neo4j via MCP.
3. **Guidance** — query patterns for numeric limits, rule listing, keyword matching.
4. **The user's question** — appended at the end.

### Reference files
| File | Purpose |
|---|---|
| `cypher_template.txt` | v3 Cypher template with placeholders — source of truth for prompt structure |
| `training/dataset_schema.json` | v3 dataset schema — defines allowed node types, keys, properties, connections |
| `training/updated_cypher_reference_examples_v3.cypher` | Complete Cypher examples for reference |

## Files to inspect first when making repo-wide schema updates
- `n8n/workflows/*.json`
- `data-service/app.py`
- `graph-viewer/index.html`
- `graph-viewer/config.template.js`
- `training/dataset_schema.json`
- `cypher_template.txt`

---
Always prefer the v3 schema conventions above over older examples elsewhere in the repo.
