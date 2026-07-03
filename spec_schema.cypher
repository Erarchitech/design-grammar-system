// SpecGraph Schema Reference (v1.1)
// Canonical node shapes, relationships, and indexes for the Project SpecGraph.
// Run once against Neo4j to bootstrap. All statements are idempotent (MERGE / IF NOT EXISTS).

// --- Full-text index ---
CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS
FOR (n:SpecNote) ON EACH [n.title, n.content];

// --- SpecNote ---
// Key property: noteId (UUID string, unique per project)
// Required properties: graph, project, noteId, title, content, source, createdAt, updatedAt
// Optional properties: tags (list of strings — denormalized copy for display)
//
// Example MERGE:
// MERGE (n:SpecNote {noteId: $noteId, project: $project, graph: 'SpecGraph'})
// SET n.title = $title, n.content = $content, n.source = $source,
//     n.createdAt = $createdAt, n.updatedAt = $updatedAt

// --- SpecTag ---
// Key property: name (lowercase tag string, unique per project)
// Required properties: graph, project, name
//
// Example MERGE:
// MERGE (t:SpecTag {name: $tagName, project: $project, graph: 'SpecGraph'})

// --- TAGGED_WITH relationship (SpecNote -> SpecTag) ---
// No properties on the relationship itself.
//
// Example:
// MATCH (n:SpecNote {noteId: $noteId, project: $project})
// MATCH (t:SpecTag {name: $tagName, project: $project})
// MERGE (n)-[:TAGGED_WITH]->(t)

// --- SpecSession ---
// Key property: sessionId (UUID string)
// Required properties: graph, project, sessionId, mode, prompt, result, createdAt
// mode values: 'insert' | 'update' | 'query'
//
// Example MERGE:
// MERGE (s:SpecSession {sessionId: $sessionId, project: $project, graph: 'SpecGraph'})
// SET s.mode = $mode, s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt

// --- Graph isolation ---
// Every node MUST include:  graph: 'SpecGraph', project: $project
// Query filter pattern:     WHERE n.graph = 'SpecGraph' AND n.project = $project
// This mirrors OntoGraph / Metagraph / ValidGraph isolation in the same Neo4j database.
