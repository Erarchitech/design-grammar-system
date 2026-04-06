// KnowledgeGraph Schema Reference (v1.1)
// Canonical node shapes, relationships, and indexes for the Project Knowledge Graph.
// Run once against Neo4j to bootstrap. All statements are idempotent (MERGE / IF NOT EXISTS).

// --- Full-text index ---
CREATE FULLTEXT INDEX knowledge_note_search IF NOT EXISTS
FOR (n:KnowledgeNote) ON EACH [n.title, n.content];

// --- KnowledgeNote ---
// Key property: noteId (UUID string, unique per project)
// Required properties: graph, project, noteId, title, content, source, createdAt, updatedAt
// Optional properties: tags (list of strings — denormalized copy for display)
//
// Example MERGE:
// MERGE (n:KnowledgeNote {noteId: $noteId, project: $project, graph: 'KnowledgeGraph'})
// SET n.title = $title, n.content = $content, n.source = $source,
//     n.createdAt = $createdAt, n.updatedAt = $updatedAt

// --- KnowledgeTag ---
// Key property: name (lowercase tag string, unique per project)
// Required properties: graph, project, name
//
// Example MERGE:
// MERGE (t:KnowledgeTag {name: $tagName, project: $project, graph: 'KnowledgeGraph'})

// --- TAGGED_WITH relationship (KnowledgeNote -> KnowledgeTag) ---
// No properties on the relationship itself.
//
// Example:
// MATCH (n:KnowledgeNote {noteId: $noteId, project: $project})
// MATCH (t:KnowledgeTag {name: $tagName, project: $project})
// MERGE (n)-[:TAGGED_WITH]->(t)

// --- KnowledgeSession ---
// Key property: sessionId (UUID string)
// Required properties: graph, project, sessionId, mode, prompt, result, createdAt
// mode values: 'insert' | 'update' | 'query'
//
// Example MERGE:
// MERGE (s:KnowledgeSession {sessionId: $sessionId, project: $project, graph: 'KnowledgeGraph'})
// SET s.mode = $mode, s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt

// --- Graph isolation ---
// Every node MUST include:  graph: 'KnowledgeGraph', project: $project
// Query filter pattern:     WHERE n.graph = 'KnowledgeGraph' AND n.project = $project
// This mirrors OntoGraph / Metagraph / ValidationGraph isolation in the same Neo4j database.
