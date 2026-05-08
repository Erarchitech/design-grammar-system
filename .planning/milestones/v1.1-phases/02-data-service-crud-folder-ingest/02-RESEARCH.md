# Phase 02: data-service CRUD + Folder Ingest - Research

**Researched:** 2026-04-06
**Domain:** Python FastAPI REST endpoints, Neo4j CRUD, filesystem ingest with path traversal protection
**Confidence:** HIGH

## Summary

Phase 2 adds REST endpoints to the existing `data-service` FastAPI app for knowledge note CRUD and folder-based markdown ingestion. The existing codebase already has all necessary infrastructure: Neo4j driver, Pydantic models, helper functions (`read_single`, `read_many`, `write_query`), the `KNOWLEDGE_GRAPH` constant, and the full-text index created at startup (Phase 1). The Nginx proxy already routes `/data-service/*` to the data-service container, so no proxy changes are needed.

The main technical considerations are: (1) path traversal prevention for the folder ingest endpoint, (2) Docker volume mount configuration to give data-service read-only access to a repository directory, and (3) markdown file parsing to extract title and content for KnowledgeNote nodes.

**Primary recommendation:** Add all new endpoints directly to `data-service/app.py` following existing patterns. Use `pathlib.Path.resolve()` for path traversal protection. Mount the repo directory as a read-only Docker volume. Parse markdown files with Python stdlib only (no new dependencies).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSK-02 | User can insert knowledge from a local repository folder -- data-service reads `.md` files and creates KnowledgeNote nodes | Folder ingest endpoint pattern, markdown parsing, recursive file walk |
| INSK-03 | Folder path input is validated server-side to prevent path traversal outside allowed root | Path traversal protection via `pathlib.Path.resolve()` + prefix check against allowed mount root |
| INFR-01 | data-service exposes `/knowledge/*` REST endpoint group | All endpoints added to existing FastAPI app following established patterns |
| INFR-03 | Docker Compose mounts a read-only volume for repository folder access by data-service | New `volumes` entry in docker-compose.yml with `:ro` flag |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No new Docker services** -- all endpoints added to existing data-service FastAPI app [VERIFIED: CLAUDE.md + STATE.md]
- **Knowledge graph uses `graph:"KnowledgeGraph"` isolation** -- every node gets `graph: 'KnowledgeGraph'` and `project` property [VERIFIED: knowledge_schema.cypher]
- **No JSX build** for main UI -- not relevant to this backend-only phase [VERIFIED: CLAUDE.md]
- **Docker layer caching** -- `--no-cache` required when rebuilding containers [VERIFIED: CLAUDE.md]

## Standard Stack

### Core (already in requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | REST framework | Already used in data-service [VERIFIED: local install] |
| neo4j | (pinned by requirements.txt) | Neo4j driver | Already used in data-service [VERIFIED: data-service/app.py] |
| pydantic | (bundled with FastAPI) | Request/response models | Already used for all existing payloads [VERIFIED: data-service/app.py] |
| uvicorn | (pinned by requirements.txt) | ASGI server | Already used as data-service entrypoint [VERIFIED: Dockerfile] |

### Supporting (Python stdlib -- no new dependencies)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File path handling, traversal protection | Folder ingest path validation |
| uuid | stdlib | Generate noteId for new notes | Already used in app.py for run IDs |
| datetime | stdlib | Timestamps for createdAt/updatedAt | Already used in app.py |

### No New Dependencies Required

This phase requires **zero new pip packages**. All functionality uses Python stdlib + existing dependencies. The markdown files are read as plain text (title extracted from first `# ` heading or filename). [VERIFIED: requirements.txt contains fastapi, uvicorn, neo4j, specklepy]

## Architecture Patterns

### Endpoint Structure

All new endpoints go under the `/knowledge/` prefix, matching INFR-01. The Nginx proxy already strips `/data-service/` and forwards to the container, so `/data-service/knowledge/*` maps to `/knowledge/*` inside the container. [VERIFIED: graph-viewer/nginx.conf line 28-35]

```
/knowledge/ingest/folder     POST   Folder ingest (INSK-02)
/knowledge/notes/{project}   GET    List notes (CRUD read-list)
/knowledge/note/{id}         GET    Read single note (CRUD read)
/knowledge/note/{id}         PUT    Update note (CRUD update)
/knowledge/note/{id}         DELETE Delete note (CRUD delete)
```

### Pattern 1: Follow Existing Validation Endpoint Patterns

**What:** All existing endpoints in `app.py` follow a consistent pattern: Pydantic model for request body, helper functions (`read_single`, `read_many`, `write_query`) for Neo4j access, direct return of dicts. [VERIFIED: data-service/app.py]

**When to use:** Every new endpoint.

**Example:**
```python
# Source: data-service/app.py existing pattern
class FolderIngestRequest(BaseModel):
    project: str
    path: str  # relative path inside mount root

class NoteUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None

@app.post("/knowledge/ingest/folder")
def ingest_folder(payload: FolderIngestRequest):
    # validate path, walk .md files, create KnowledgeNote nodes
    ...
    return {"inserted": N, "skipped": M}
```

### Pattern 2: Path Traversal Protection

**What:** Use `pathlib.Path.resolve()` to canonicalize user-provided paths, then verify the resolved path starts with the allowed mount root. This prevents `../` traversal attacks. [VERIFIED: Python pathlib docs -- resolve() eliminates symlinks and `..` components]

**Example:**
```python
KNOWLEDGE_REPO_ROOT = Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", "/mnt/repo"))

def validate_ingest_path(user_path: str) -> Path:
    """Resolve and validate that path is within allowed mount root."""
    # Join with mount root if relative, or use absolute
    candidate = (KNOWLEDGE_REPO_ROOT / user_path).resolve()
    # Verify it's still under the allowed root
    if not str(candidate).startswith(str(KNOWLEDGE_REPO_ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Path outside allowed repository root")
    if not candidate.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    return candidate
```

### Pattern 3: Markdown Title Extraction

**What:** Extract title from first `# ` heading in markdown file. Fall back to filename (without `.md` extension) if no heading found. No markdown parsing library needed -- a simple line scan suffices for title extraction, and content is stored as raw markdown text. [ASSUMED]

**Example:**
```python
def extract_title_from_md(file_path: Path) -> tuple[str, str]:
    """Return (title, content) from a markdown file."""
    content = file_path.read_text(encoding="utf-8")
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped[2:].strip(), content
    # Fallback: filename without extension
    return file_path.stem.replace("-", " ").replace("_", " "), content
```

### Pattern 4: Docker Volume Mount (read-only)

**What:** Add a read-only bind mount in `docker-compose.yml` so data-service can access the host repository directory. [VERIFIED: docker-compose.yml existing volume pattern]

**Example:**
```yaml
data-service:
  volumes:
    - ./data-service/data:/app/data           # existing
    - .:/mnt/repo:ro                          # new: repo root, read-only
```

The mount path `.` (repo root) gives access to `DG_OBSIDIAN/` and any other folder the architect wants to ingest. The `:ro` flag ensures data-service cannot modify the host filesystem. The env var `DG_KNOWLEDGE_REPO_ROOT=/mnt/repo` tells the ingest endpoint where the mount root is.

### Pattern 5: Note ID as MERGE Key

**What:** Use `noteId` (UUID) as the primary key for KnowledgeNote nodes, consistent with the schema from Phase 1. For folder ingest, generate a deterministic ID from `project + source_path` so re-ingesting the same file updates rather than duplicates. [ASSUMED]

**Example:**
```python
import hashlib

def generate_note_id(project: str, source_path: str) -> str:
    """Deterministic ID from project + source path for idempotent ingest."""
    return hashlib.sha256(f"{project}:{source_path}".encode()).hexdigest()[:16]
```

This means re-running folder ingest on the same directory is idempotent -- existing notes get updated (MERGE), new files get inserted.

### Anti-Patterns to Avoid
- **Using `os.path.join` without resolve:** Does NOT prevent `../../etc/passwd` traversal -- always use `Path.resolve()` + prefix check
- **Storing full host paths in Neo4j:** Store the path relative to mount root only, so the data remains portable across environments
- **Reading file content synchronously for very large files:** The REQUIREMENTS.md says content > 100KB is out of scope, but still guard with a size check to avoid memory issues

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path traversal protection | Custom string manipulation | `pathlib.Path.resolve()` + prefix check | Handles symlinks, `..`, `.`, redundant separators correctly |
| UUID generation | Custom ID format | `uuid.uuid4().hex` or deterministic hash | Already used throughout app.py |
| JSON serialization | Manual dict building | Pydantic `model_dump()` | Already used for all existing response models |

## Common Pitfalls

### Pitfall 1: Path Traversal via Symlinks
**What goes wrong:** User creates a symlink inside the mount that points outside the allowed root. `Path.resolve()` follows symlinks, so a symlink to `/etc` would resolve to `/etc` and fail the prefix check. This is correct behavior -- the prefix check catches it.
**Why it happens:** Developers sometimes check the path before resolving, which misses symlink attacks.
**How to avoid:** Always call `.resolve()` FIRST, then check the prefix. The current pattern does this correctly.
**Warning signs:** Tests that only check `..` but not symlinks.

### Pitfall 2: Docker Mount Not Available at Dev Time
**What goes wrong:** Running `uvicorn` locally (not in Docker) means `/mnt/repo` doesn't exist.
**Why it happens:** The volume mount only exists inside the container.
**How to avoid:** Use an env var (`DG_KNOWLEDGE_REPO_ROOT`) with a sensible default that works locally (e.g., the current directory or a test fixtures path). The env var is already the established pattern (see `DG_DATA_DIR`). [VERIFIED: data-service/app.py line 41]
**Warning signs:** Tests that assume Docker paths.

### Pitfall 3: Encoding Issues with Markdown Files
**What goes wrong:** Non-UTF-8 files cause `UnicodeDecodeError` and crash the entire ingest.
**Why it happens:** Obsidian typically uses UTF-8, but user repos may contain legacy encodings.
**How to avoid:** Wrap file reads in try/except, skip files that fail to decode, count them as "skipped" in the response.
**Warning signs:** Ingest works in test but fails on real user repos.

### Pitfall 4: Neo4j Transaction Size for Large Folders
**What goes wrong:** Ingesting hundreds of files in a single transaction can timeout or OOM.
**Why it happens:** Neo4j has transaction memory limits.
**How to avoid:** Use `UNWIND` with batched parameters (50-100 notes per batch) rather than individual MERGE per file, or process files individually with auto-commit. For note-scale data (hundreds, not millions), individual MERGE per file is acceptable. [ASSUMED]
**Warning signs:** Ingest works for 5 files but hangs for 200.

### Pitfall 5: Re-ingest Creates Duplicate Notes
**What goes wrong:** Running folder ingest twice creates duplicate KnowledgeNote nodes.
**Why it happens:** Using random UUIDs as noteId means each ingest creates new nodes.
**How to avoid:** Use a deterministic noteId derived from project + relative file path, then MERGE on that key. Re-ingest updates existing notes.
**Warning signs:** Note count doubles after re-running ingest.

## Code Examples

### Complete Folder Ingest Flow
```python
# Source: Composed from existing data-service patterns + knowledge_schema.cypher

@app.post("/knowledge/ingest/folder")
def ingest_folder(payload: FolderIngestRequest):
    root = validate_ingest_path(payload.path)
    md_files = list(root.rglob("*.md"))

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for md_file in md_files:
        try:
            title, content = extract_title_from_md(md_file)
            relative_path = str(md_file.relative_to(KNOWLEDGE_REPO_ROOT))
            note_id = generate_note_id(payload.project, relative_path)

            write_query(
                "MERGE (n:KnowledgeNote {noteId: $noteId, project: $project, graph: $graph}) "
                "SET n.title = $title, n.content = $content, n.source = $source, "
                "    n.createdAt = coalesce(n.createdAt, $now), n.updatedAt = $now",
                {
                    "noteId": note_id,
                    "project": payload.project,
                    "graph": KNOWLEDGE_GRAPH,
                    "title": title,
                    "content": content,
                    "source": relative_path,
                    "now": now,
                },
            )
            inserted += 1
        except Exception:
            skipped += 1

    return {"inserted": inserted, "skipped": skipped}
```

### CRUD Read Endpoints
```python
# Source: Follows existing read_many/read_single patterns from app.py

@app.get("/knowledge/notes/{project}")
def list_knowledge_notes(project: str):
    rows = read_many(
        "MATCH (n:KnowledgeNote {project: $project, graph: $graph}) "
        "RETURN n.noteId AS noteId, n.title AS title, n.source AS source, "
        "       n.createdAt AS createdAt, n.updatedAt AS updatedAt "
        "ORDER BY n.updatedAt DESC",
        {"project": project, "graph": KNOWLEDGE_GRAPH},
    )
    return {"project": project, "notes": rows}

@app.get("/knowledge/note/{note_id}")
def get_knowledge_note(note_id: str):
    row = read_single(
        "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
        "RETURN n.noteId AS noteId, n.title AS title, n.content AS content, "
        "       n.source AS source, n.tags AS tags, n.project AS project, "
        "       n.createdAt AS createdAt, n.updatedAt AS updatedAt",
        {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return row
```

### CRUD Update and Delete
```python
@app.put("/knowledge/note/{note_id}")
def update_knowledge_note(note_id: str, payload: NoteUpdateRequest):
    existing = read_single(
        "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) RETURN n.noteId AS noteId",
        {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Note not found")

    set_clauses = ["n.updatedAt = $now"]
    params = {"noteId": note_id, "graph": KNOWLEDGE_GRAPH, "now": datetime.now(timezone.utc).isoformat()}
    if payload.title is not None:
        set_clauses.append("n.title = $title")
        params["title"] = payload.title
    if payload.content is not None:
        set_clauses.append("n.content = $content")
        params["content"] = payload.content
    if payload.tags is not None:
        set_clauses.append("n.tags = $tags")
        params["tags"] = payload.tags

    write_query(
        f"MATCH (n:KnowledgeNote {{noteId: $noteId, graph: $graph}}) SET {', '.join(set_clauses)}",
        params,
    )
    return {"status": "updated", "noteId": note_id}

@app.delete("/knowledge/note/{note_id}")
def delete_knowledge_note(note_id: str):
    existing = read_single(
        "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) RETURN n.noteId AS noteId",
        {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Note not found")

    write_query(
        "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) DETACH DELETE n",
        {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
    )
    return {"status": "deleted", "noteId": note_id}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ (2023) | Both work; existing codebase uses `on_event` -- stay consistent [VERIFIED: data-service/app.py line 538] |

**Note:** FastAPI `on_event("startup")` is technically deprecated in favor of `lifespan`, but the existing codebase uses it and it still works. Consistency with existing code is more important than chasing deprecation warnings for this project. [VERIFIED: data-service/app.py]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Simple line-scan for `# ` heading is sufficient for markdown title extraction (no parsing library needed) | Architecture Patterns / Pattern 3 | LOW -- worst case: fallback to filename works fine |
| A2 | Individual MERGE per file is acceptable for note-scale data (hundreds of files) | Common Pitfalls / Pitfall 4 | LOW -- can batch with UNWIND if perf is an issue |
| A3 | Deterministic noteId from project+path is preferred over random UUID for idempotent re-ingest | Architecture Patterns / Pattern 5 | MEDIUM -- if user wants multiple versions of same file, this would overwrite |
| A4 | Mount root should be `.` (entire repo root) rather than just `DG_OBSIDIAN/` | Architecture Patterns / Pattern 4 | LOW -- user may want to ingest from other directories too; can restrict via env var |

## Open Questions

1. **What directory should be mounted as the ingest root?**
   - What we know: The Obsidian vault is at `DG_OBSIDIAN/`, but users may have other markdown folders
   - What's unclear: Whether to mount just `DG_OBSIDIAN/` or the entire repo root
   - Recommendation: Mount repo root (`.`) as `/mnt/repo:ro` and let the user specify subdirectories in the API call. The path traversal check ensures they stay within bounds.

2. **Should folder ingest extract tags from markdown frontmatter?**
   - What we know: Obsidian files often have YAML frontmatter with `tags:` field. The schema supports both a `tags` list on the node and `KnowledgeTag` nodes via `TAGGED_WITH`.
   - What's unclear: Whether Phase 2 should parse frontmatter or defer tag extraction to Phase 3 (LLM-based)
   - Recommendation: Extract tags from YAML frontmatter if present (simple regex or split on `---` delimiters). This is low effort and makes folder-ingested notes immediately searchable by tag. Defer complex tag inference to LLM phases.

3. **Should the ingest endpoint be synchronous or async?**
   - What we know: Existing endpoints are synchronous. The folder walk for a typical Obsidian vault (50-200 files) takes seconds.
   - What's unclear: Whether very large vaults would cause HTTP timeout
   - Recommendation: Synchronous is fine for Phase 2. The success criteria specifies a synchronous `{inserted: N, skipped: M}` return. Can add async with polling later if needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in data-service (internal Docker network) |
| V3 Session Management | no | Stateless REST API |
| V4 Access Control | yes | Path traversal prevention via resolve() + prefix check |
| V5 Input Validation | yes | Pydantic models for all request bodies; path validation for folder ingest |
| V6 Cryptography | no | No secrets handled in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `../` | Tampering | `Path.resolve()` + prefix check against `KNOWLEDGE_REPO_ROOT` |
| Path traversal via symlinks | Tampering | `Path.resolve()` follows symlinks before prefix check |
| Oversized file content | DoS | Check file size before reading; skip files > 100KB (per Out of Scope in REQUIREMENTS.md) |
| Malicious markdown content | Tampering | Content stored as-is in Neo4j; no server-side execution. XSS risk is a UI concern (Phase 5+) |

## Sources

### Primary (HIGH confidence)
- data-service/app.py -- existing endpoint patterns, helper functions, Neo4j driver usage
- knowledge_schema.cypher -- canonical node shapes and properties from Phase 1
- docker-compose.yml -- existing volume mount patterns and service configuration
- graph-viewer/nginx.conf -- existing proxy rules confirming `/data-service/` routing
- REQUIREMENTS.md -- requirement definitions for INSK-02, INSK-03, INFR-01, INFR-03

### Secondary (MEDIUM confidence)
- Python pathlib documentation -- `Path.resolve()` behavior for symlinks and `..` [CITED: docs.python.org/3/library/pathlib.html]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns verified in existing codebase
- Architecture: HIGH -- follows established data-service patterns exactly
- Pitfalls: HIGH -- path traversal is well-understood; Neo4j patterns verified in Phase 1
- Docker mount: HIGH -- standard Docker Compose volume syntax

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable -- no fast-moving dependencies)
