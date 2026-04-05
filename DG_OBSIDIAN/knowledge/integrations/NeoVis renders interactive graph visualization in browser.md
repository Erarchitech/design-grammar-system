---
tags: [integration, neovis, visualization, graph]
date: 2026-04-05
---

# NeoVis Renders Interactive Graph Visualization in Browser

## How It Works

NeoVis.js connects directly to Neo4j via bolt protocol from the browser. It executes Cypher queries and renders the result as an interactive force-directed graph.

## Configuration (`config.template.js`)

### Node Visual Groups

| Label | Color | Display Property |
|-------|-------|-----------------|
| Rule | Blue (#6da7ff) | `Rule_Id` |
| Atom | Gray (#b7c0cc) | `Atom_Id`, secondary: `SWRL_label` |
| Class | Green (#78c38a) | `label` |
| DatatypeProperty | Orange (#ffb36b) | `SWRL_label` |
| ObjectProperty | Deep orange (#ff8f3a) | `label` |
| Builtin | Neutral gray (#9aa4b2) | `label` |
| Var | Purple (#c6b5ff) | `name` |
| Literal | Warm yellow (#ffd6a5) | `lex` |

### Relationship Types

`HAS_BODY`, `HAS_HEAD`, `REFERS_TO`, `ARG` — all with captions and thickness 2.

### Graph Queries (built by `buildCypher()`)

**MetaGraph**: matches Rules → Atoms (HAS_BODY/HAS_HEAD) → Vars/Literals (ARG) + REFERS_TO  
**OntoGraph**: matches Classes, ObjectProperties, DataProperties

All filtered by `project:'<name>'`.

## Interaction

- Click node → open right detail panel with all properties
- Right-click node → context menu (delete option)
- Inline property editing in right panel → `SET n[$key]=$value` via Neo4j HTTP

## Related

- [[UI is a single-file React 18 SPA with no build step]]
- [[Neo4j provides graph storage with project-scoped isolation]]
- [[Graph schema v3 is the canonical data model]]
