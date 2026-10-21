---
tags: [debugging, graph-viewer, data-service, neo4j]
date: 2026-10-21
status: fixed (commit 093ea13, deployed dg-mapping-data-service:093ea13)
---

# Graph Viewer cap hid rules behind validation history

**Symptom.** A newly ingested rule (`R_OpeningSlabEdgeClearance500`, `str-openings-01`) appeared in the Edit picker but not in the Graph Viewer.

**Cause.**
- The Edit picker reads `GET /rules/{project}` with no cap.
- The viewer reads `GET /graph/{project}`, which returned `LIMIT 2000` nodes and `LIMIT 8000` relationships with no `ORDER BY`, so in practice in id order.
- 71,524 of the project's 71,955 nodes are `ValidationEntity` (71,524 `HAS_ENTITY` relationships). The 2,000th node had id 8,986; the new rule had id 78,932, and its relationships ids from 78,502.
- The four older rules (ids ≤ 7,032) were inside the cap by chance.

**Fix.** `GRAPH_NODES_QUERY` and `GRAPH_RELS_QUERY` sort validation labels (`GRAPH_COMPACT_VALIDATION_LABELS`) last, then by id, as the DeGram compact read already did. The caps stay.

**Verification.**
- `test_graph_routes.py` 74/74; the 168 access tests on `/graph` pass.
- In the container: 5/5 rules returned (before the owner deleted the rule).

**Open.**
- The cap remains: a project with more than 2,000 non-validation nodes would hit it again.
- `feature/hosting-dg-pilot` still has the old queries.

Session: [[sessions/2026-10-21 Multi-participant rules design, plans 1303-19 to 23 and Graph Viewer cap fix]].
