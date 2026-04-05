# Concerns

## Security

### Hardcoded Credentials (HIGH)
- **Neo4j credentials** (`neo4j/12345678`) hardcoded in `docker-compose.yml`, `config.template.js`, `entrypoint.sh`, and C# component defaults (`ConnectorComponent.cs`)
- **n8n credentials** (email + password) in `docker-compose.yml` and `config.template.js`
- These are committed to the repository and visible in plain text
- **Risk:** Credential exposure if repo is public or shared; rotation is difficult

### Client-Side Authentication Only (HIGH)
- User authentication is entirely in `localStorage` with SHA-256 hashed passwords
- No server-side session management, no JWT, no backend auth endpoint
- Anyone with browser dev tools can read/modify `dg_users` and `dg_current_user`
- Password hashing uses a static salt `"dg_salt_"` — not per-user salt
- **Risk:** No real authentication; any user can impersonate any other user

### Neo4j Direct Access from Browser (MEDIUM)
- `graph-viewer/index.html` connects to Neo4j HTTP API directly via `/neo4j/` proxy
- NeoVis.js executes Cypher queries constructed in client-side JavaScript
- `buildCypher()` includes project name via string concatenation with basic escaping (`replace(/'/g, "")`)
- **Risk:** Potential Cypher injection if project names bypass sanitization

### MCP Read-Only Check (LOW)
- `data-service/app.py` has `is_write_query()` using regex to block writes via MCP
- Regex approach: `\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b`
- **Risk:** Regex-based write detection could be bypassed with creative Cypher syntax

## Technical Debt

### Single-File SPA (HIGH impact on maintainability)
- `graph-viewer/index.html` is a 2425-line file containing ALL UI code, CSS, and JavaScript
- No module system, no component files, no build toolchain
- Uses `React.createElement` without JSX — verbose and error-prone
- Adding new features requires careful manual state management in a single scope
- **Impact:** High cognitive load for any UI modification; difficult to onboard new developers

### No Python or JavaScript Tests (MEDIUM)
- `data-service/app.py` (~870 lines) has zero tests
- `graph-viewer/index.html` has zero tests
- `graph-viewer/model-viewer/` has zero tests
- Only `DG.Core` C# library has unit tests
- **Impact:** Regression risk for backend API changes and UI modifications

### No CI/CD Pipeline (MEDIUM)
- No GitHub Actions, no automated testing, no deployment automation
- Tests run manually via `dotnet test`
- Docker builds are manual: `docker compose build --no-cache design-grammars`
- **Impact:** Manual release process; easy to ship untested changes

### In-Memory Execution Tracking (LOW)
- `EXECUTION_RESULTS` and `WORKFLOW_STATUS` in `data-service/app.py` are plain Python dicts
- Data lost on container restart
- Not thread-safe (though single-worker uvicorn mitigates this)
- **Impact:** Stale execution status if data-service restarts mid-workflow

### Stale Worktrees
- `.claude/worktrees/` contains multiple GSD worktrees (`epic-heyrovsky`, `distracted-bouman`, `hopeful-shamir`, `exciting-dijkstra`, `magical-leavitt`) with duplicated `.github/copilot-instructions.md` and potentially divergent code
- **Impact:** Confusion about canonical code; wasted disk space

## Architecture Concerns

### Tight Coupling to Neo4j Across All Layers
- Every layer (JS SPA, Python backend, C# library, n8n workflows) embeds Neo4j Cypher queries
- Schema changes require coordinated updates across 5+ locations
- The `.github/copilot-instructions.md` documents this as "mandatory dependency propagation" but enforcement is manual
- **Impact:** Schema migration is labor-intensive and error-prone

### LLM Output Reliability
- Cypher generation depends on Ollama `llama3.1:latest` following structured prompts correctly
- No formal output validation beyond n8n executing the Cypher (which may fail or produce wrong results)
- Prompt structure is embedded in n8n workflow JSON (not easily versioned or tested)
- **Impact:** LLM hallucinations could create malformed graph data

### Mixed Multi-Target .NET
- `DG.Core` targets both `net7.0` and `net9.0`
- `DG.Grasshopper` targets only `net7.0-windows` (Rhino 8 requirement)
- `DG.Tests` targets `net9.0`
- **Impact:** Potential runtime compatibility issues; .NET 7 is out of support (EOL Nov 2024)

## Performance Concerns

### No Pagination or Limits on Graph Queries
- `buildCypher()` in the SPA fetches all matching nodes without `LIMIT`
- Large projects with many rules/atoms could produce very large NeoVis visualizations
- `fetchExistingRules()` fetches all rules for a project without pagination
- **Impact:** UI freezing or OOM for projects with hundreds of rules

### Ollama Cold Start
- First LLM query after container start requires model loading (10+ seconds for llama3.1)
- No model preloading configured
- **Impact:** Poor first-query experience for users

## Fragile Areas

### `entrypoint.sh` sed Substitution
- Config generation uses `sed` with hardcoded placeholder strings
- If default values appear in unintended places, substitution produces wrong config
- E.g., replacing `neo4j` (the user) also matches the string in `bolt://neo4j:7687`
- **Impact:** Config corruption if environment values contain special characters

### `config.template.js` as Template
- Template approach relies on exact string matching for substitution
- Adding new config values requires coordinating `config.template.js`, `entrypoint.sh`, and `docker-compose.yml`
- **Impact:** Easy to add a config value in one place but forget the others

### Cypher String Concatenation in `buildCypher()`
- Project name injected via string concatenation: `", project:'" + project.replace(/'/g, "") + "'"`
- Escaping is minimal (only single-quote removal)
- **Impact:** Potential injection if project names contain unexpected characters despite sanitization at creation time
