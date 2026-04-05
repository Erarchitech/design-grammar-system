# Architectural Decisions

## ADR-1: Single-File React SPA Avoids Build Tooling

**Context:** The main UI needs rapid iteration without complex build pipelines.

**Decision:** Ship `graph-viewer/index.html` as a single file with `React.createElement` calls, React 18 loaded from CDN. No JSX, no Webpack, no Vite for the main app.

**Consequences:** No hot-reload, no tree-shaking, all code in one file (large). But: zero build step, instant deploys, no Node.js dependency for the main UI. The Model Viewer (which needs Three.js/Speckle) uses Vite separately.

---

## ADR-2: SWRL Parsing Uses Bespoke Regex

**Context:** SWRL atom strings like `Building(?b)` and `greaterThan(?h, 75)` need parsing in C#.

**Decision:** Custom regex parser in `SwrlRuleParser.cs` instead of a vendor OWL/SWRL library.

**Consequences:** Lightweight, no heavy OWL dependency. But: fragile for edge cases, must be updated manually for new atom patterns. Covered by unit tests (`SwrlRuleParserTests.cs`).

---

## ADR-3: Project Isolation via Property Filtering

**Context:** Multiple projects need isolated rule sets in Neo4j.

**Decision:** Every node carries a `project` property. All Cypher queries filter by `project:'<n>'`. Single database, no separate DBs per project.

**Consequences:** Simple deployment (one Neo4j instance), easy cross-project queries if needed. But: no hard isolation, must be diligent about filtering. A missing `WHERE project = ...` clause leaks data between projects.

---

## ADR-4: LLM Prompts Embed Schema Constraints

**Context:** The LLM must generate valid v3 Cypher from natural language rules.

**Decision:** Embed the full schema (node labels, property names, relationship types, few-shot examples) directly in the n8n workflow prompt. No fine-tuning of the base model for schema compliance.

**Consequences:** Schema changes require updating the prompt text in n8n workflows. But: no training infrastructure needed, rapid iteration on prompt engineering, works with any Ollama model.

---

## ADR-5: Client-Side Password Hashing

**Context:** User authentication for the SPA prototype.

**Decision:** Hash passwords client-side with `SubtleCrypto.digest('SHA-256', ...)`, store in `localStorage`.

**Consequences:** No server-side auth, no session tokens, no password recovery. Adequate for prototype/internal use. **Must be replaced** with server-side auth (bcrypt + JWT) before production deployment.

---

## ADR-6: Validation Results Publish to Speckle as Overlay Versions

**Context:** Validation pass/fail results need 3D visualization.

**Decision:** The Grasshopper VALIDATOR component builds a validation package, POSTs it to `data-service/validation/publish`, which creates a new Speckle version with color-coded geometry.

**Consequences:** Validation results are persistent and shareable via Speckle URLs. But: each validation run creates a new Speckle version (storage grows). Model Viewer fetches manifests from data-service and loads 3D overlays from Speckle.

---

## ADR-7: Violation Rules Invert the Constraint in SWRL Body

**Context:** SWRL rules need to detect violations, not compliance.

**Decision:** Body atoms express the violation condition. "Maximum height 75m" becomes `swrlb:greaterThan(?h, 75)` in the body — the rule fires when the value **exceeds** the limit.

**Consequences:** Counterintuitive for newcomers (the body says "greater than" for a maximum constraint). But: matches standard SWRL violation pattern semantics. LLM prompt must clearly explain this inversion.

---

## ADR-8: Async Polling for n8n Workflow Tracking

**Context:** LLM inference via Ollama can take 10-60 seconds. The UI cannot block.

**Decision:** n8n webhooks return an immediate 200 ACK. The workflow stores its result via `POST /data-service/execution-result`. The UI polls `GET /data-service/execution-result/{id}` until completion.

**Consequences:** Non-blocking UI, progress indication possible. But: polling interval tuning needed, no WebSocket push. Execution results are ephemeral (in-memory dict in data-service).

---

## ADR-9: Config Injection via entrypoint.sh sed Replacement

**Context:** The SPA needs runtime configuration (Neo4j URL, n8n webhook URLs) that differs between environments.

**Decision:** `config.template.js` contains `__PLACEHOLDER__` strings. `entrypoint.sh` runs `sed` to replace them with environment variable values at container startup, producing `config.js`.

**Consequences:** No rebuild needed for config changes, just restart the container. But: `sed` replacements are fragile (special characters in values need escaping). Template and entrypoint must stay in sync.
