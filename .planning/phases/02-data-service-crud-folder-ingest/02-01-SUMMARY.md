---
phase: 02-data-service-crud-folder-ingest
plan: "01"
subsystem: data-service
tags: [folder-ingest, path-traversal, knowledge-graph, fastapi, docker]
dependency_graph:
  requires: []
  provides: [POST /knowledge/ingest/folder, KNOWLEDGE_REPO_ROOT volume mount]
  affects: [docker-compose.yml, data-service/app.py]
tech_stack:
  added: [hashlib (stdlib)]
  patterns: [Path.resolve() + startswith() path traversal guard, deterministic SHA-256 note IDs, YAML frontmatter parsing, MERGE upsert for idempotent re-ingest]
key_files:
  created: []
  modified:
    - docker-compose.yml
    - data-service/app.py
decisions:
  - Path traversal protection via resolve() + startswith() — prevents symlink escape and ../traversal; returns HTTP 403 on violation without revealing mount path
  - Deterministic note IDs via SHA-256(project:source_path) — enables idempotent re-ingest (UPDATE not INSERT on second call)
  - MAX_FILE_SIZE = 100KB — prevents memory exhaustion from large files before read_text is called
  - Tags stored on KnowledgeNote.tags list AND as separate KnowledgeTag nodes with TAGGED_WITH relationships — supports both property-based filtering and graph traversal queries
metrics:
  duration: ~8 minutes
  completed: "2026-04-06"
  tasks_completed: 2
  files_modified: 2
---

# Phase 02 Plan 01: Folder Ingest Endpoint Summary

Docker volume mount configured and folder ingest endpoint live at POST /knowledge/ingest/folder with path traversal protection, idempotent MERGE upsert, file size guard, and frontmatter tag extraction.

## What Was Built

### Task 1: Docker Volume Mount (commit dd072bc)
Added to `data-service` in `docker-compose.yml`:
- Volume mount: `.:/mnt/repo:ro` — repo root as read-only for folder ingest
- Environment variable: `DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` — mount root for path validation

### Task 2: Folder Ingest Endpoint (commit f10c0a7)
Added to `data-service/app.py`:

**Constants:**
- `KNOWLEDGE_REPO_ROOT = FilePath(os.getenv("DG_KNOWLEDGE_REPO_ROOT", "/mnt/repo"))`

**Pydantic model:** `FolderIngestRequest` with `project: str` and `path: str` fields.

**Helper functions:**
- `validate_ingest_path(user_path)` — resolves against KNOWLEDGE_REPO_ROOT, raises HTTP 403 if outside root, HTTP 400 if not a directory
- `extract_title_from_md(file_path)` — returns (title, content); title from first `# heading` or filename
- `extract_frontmatter_tags(content)` — parses YAML frontmatter `tags:` field (list or comma-separated)
- `generate_note_id(project, source_path)` — SHA-256 deterministic 16-char hex ID for idempotent re-ingest

**Endpoint:** `POST /knowledge/ingest/folder`
- Recursively finds all `.md` files under validated path
- Skips files >100KB and non-UTF-8 files (graceful, counted as skipped)
- MERGE upsert on `KnowledgeNote {noteId, project, graph}` — re-ingest updates, does not duplicate
- Creates `KnowledgeTag` nodes and `TAGGED_WITH` relationships for frontmatter tags
- Returns `{"inserted": N, "skipped": M}`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate `urlparse` import**
- Found during: Task 2 (reading app.py)
- Issue: `from urllib.parse import urlparse` appeared twice (lines 10-11)
- Fix: Removed duplicate; added `import hashlib` in same pass
- Files modified: data-service/app.py
- Commit: f10c0a7

## Known Stubs

None — all data paths are wired to Neo4j via the existing `write_query` helper.

## Threat Flags

None — no new trust boundaries introduced beyond those already modeled in the plan's threat_model. The `validate_ingest_path` mitigation for T-02-01 is implemented exactly as specified.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| docker-compose.yml exists | FOUND |
| data-service/app.py exists | FOUND |
| 02-01-SUMMARY.md created | FOUND |
| commit dd072bc (Task 1) | FOUND |
| commit f10c0a7 (Task 2) | FOUND |
