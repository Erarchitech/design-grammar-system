# Copilot Instructions for design-grammar-system

## Overview
This repo orchestrates a Dockerized pipeline for parsing architectural design rules into SWRL + graph atoms, generating a custom ontology, and storing both in Neo4j. It also includes a graph-query workflow (MCP) that turns natural-language questions into read-only Cypher and returns a short answer. A lightweight graph-viewer UI provides ingest, query, and visualization.

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
1. training dataset examples
2. schema reference
3. n8n workflow prompts and validators
4. graph-viewer configuration
5. any Cypher templates or parsing logic in Python/JS

## Required property migrations
- `Rule.id` -> `Rule.Rule_Id`
- `DatatypeProperty.label` -> `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` -> `Atom.Atom_Id`
- add `Atom.iri`
- add `Atom.SWRL_label`

Any code that reads, renders, queries, validates, exports, or trains on the graph must be checked against these changes.

## Architecture
- **Neo4j**: Single database. Ontology and rules are separated by `graph` property values `OntoGraph` and `Metagraph`.
- **n8n**: Two workflows:
  - `n8n/workflows/rules-to-metagraph.json` (`/webhook/dg/rules-ingest`)
  - `n8n/workflows/graph-query-mcp.json` (`/webhook/dg/graph-query`)
- **Ollama**: LLM inference. Default model `llama3.1-dg:latest`.
- **data-service**: FastAPI for MCP (`/mcp`) plus in-memory execution tracking (`/execution-result`).
- **graph-viewer**: Static UI + Nginx proxy for `/neo4j`, `/n8n`, `/data-service`.

## Training (LoRA) and dataset
- Canonical dataset file: `training/training_dataset_v3.json`
- Canonical schema reference: `training/dataset_schema_v3.json`
- Training samples are JSON Lines with required fields `prompt` and `cypher`.
- All training Cypher examples must:
  - use `DatatypeProperty.SWRL_label`
  - create atoms with `Atom_Id`
  - set `Atom.iri`
  - set `Atom.SWRL_label`
  - include `project` and `graph` on persisted nodes

## Files to inspect first when making repo-wide schema updates
- `n8n/workflows/*.json`
- `data-service/app.py`
- `graph-viewer/index.html`
- `graph-viewer/config.template.js`
- training dataset and schema files

---
Always prefer the v3 schema conventions above over older examples elsewhere in the repo.
