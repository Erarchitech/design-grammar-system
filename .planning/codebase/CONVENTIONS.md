# Code Conventions

## C# (.NET)

### Style
- **Nullable annotations** enabled (`<Nullable>enable</Nullable>`)
- **Implicit usings** enabled
- **File-scoped namespaces** (no braces around entire file)
- **Latest C# language version** (`<LangVersion>latest</LangVersion>` in Grasshopper project)
- **Primary constructors** not used; traditional constructor style

### Naming
- PascalCase for types, methods, properties: `RuleEvaluator`, `EvaluateRule()`, `BodyAtoms`
- camelCase for locals and parameters: `atomCache`, `ruleId`
- `I`-prefixed interfaces: `INeo4jConnectorService`, `IRuleRepository`
- Private fields: `_connectorService`, `_loadTask`, `_activeRequestKey`
- Constants: `private const string RulesQuery`, `private static readonly TimeSpan QueryTimeout`

### Patterns
- **Interface segregation** — data access uses `INeo4jConnectorService` and `IRuleRepository` interfaces with concrete implementations
- **Static utility classes** — `VariableBinder`, `SwrlRuleParser` are static with no instance state
- **Sealed classes** — most concrete classes are `sealed` (`Neo4jConnectorService`, `ConnectorComponent`, etc.)
- **Async/await** with explicit timeout via `.WaitAsync(TimeSpan)` for Neo4j operations
- **Collection properties** as `Collection<T>` with init in constructor: `public Collection<Atom> BodyAtoms { get; } = new()`
- **`init` accessors** for immutable model properties: `public string Id { get; init; }`
- **Conditional compilation** — `#if GRASSHOPPER_SDK` wraps all Grasshopper components (compiles only when Rhino SDKs found)

### Error Handling
- Neo4j connectivity: catch `TimeoutException`, `OperationCanceledException`, generic `Exception` — return status object
- Rule evaluation: catch generic `Exception` per binding row, record `firstError`, continue evaluation
- No global exception handlers or middleware in the C# layer

## Python

### Style
- **Type hints** throughout: `dict[str, Any]`, `list[dict[str, Any]]`, `str | None`
- **`from __future__ import annotations`** at file top for forward references
- **Pydantic `BaseModel`** for all request/response payloads with `Field(default_factory=...)` defaults
- **Dataclasses** for internal value types: `@dataclass(frozen=True) class SpeckleConnectionSettings`
- **f-strings** for string formatting
- **Docstrings**: minimal — functions are self-documenting via type hints

### Naming
- snake_case for functions, variables: `get_speckle_settings()`, `normalize_value()`
- PascalCase for classes and Pydantic models: `ExecutionResult`, `SpeckleProjectConfigPayload`
- SCREAMING_SNAKE for module-level constants: `EXECUTION_RESULTS`, `VALIDATION_GRAPH`, `DATA_DIR`

### Patterns
- **FastAPI decorators** for REST endpoints: `@app.get(...)`, `@app.post(...)`
- **Driver module-level singleton**: `driver = GraphDatabase.driver(...)` created at import time
- **Helper functions** for query execution: `read_single()`, `read_many()`, `write_query()` wrap Neo4j sessions
- **`normalize_*` functions** for input sanitization: URLs, Speckle project IDs, model IDs
- **`mask_token()`** to safely preview secrets in API responses

### Error Handling
- `HTTPException` with status codes 400/404/500 for API errors
- `SpeckleValidationError` (custom `RuntimeError`) caught and re-raised as `HTTPException`
- Generic `Exception` caught at endpoint level with descriptive messages

## JavaScript (SPA — `index.html`)

### Style
- **No build step, no JSX** — all React via `React.createElement` aliased as `const e = React.createElement`
- **React hooks** — `useState`, `useEffect`, `useRef` used throughout functional components
- **Inline styles** via CSS custom properties (`:root` variables) in `<style>` block
- **ES2020+ syntax** — `async/await`, `?.`, `??`, arrow functions, template literals

### Naming
- camelCase for variables/functions: `buildCypher()`, `fetchExistingRules()`, `currentProject`
- PascalCase for React components: `RegisterPage`, `HomePage`, `GraphViewerPage`, `AppRouter`
- UI-specific: `MODE_OPTIONS` (constant array), `getDataServiceBaseUrl()` (utility)

### Patterns
- **Single-file SPA** — all components, styles, and logic in one HTML file (~2425 lines)
- **Component-as-function** with props destructuring: `function HomePage(props) { const user = props.user; ... }`
- **State machine routing** via `AppRouter` managing `page` state: `register → home → project → graph`
- **localStorage** for user/project persistence: `dg_users`, `dg_current_user`
- **Password hashing** via `SubtleCrypto.digest('SHA-256')` with `"dg_salt_"` prefix
- **Project name sanitization**: `name.trim().replace(/[^a-zA-Z0-9 _\-]/g, "")`
- **Polling pattern** for execution results: `setInterval` → `fetch /execution-result/` → check status

### Error Handling
- `try/catch` around `fetch` calls with `setError()` state updates
- Form validation via state-based error messages
- No global error boundary

## Cross-Cutting Conventions

- **v3 Schema compliance** — all Cypher, prompts, UI labels, and data access code must align with the canonical graph model documented in `.github/copilot-instructions.md`
- **Project isolation** — every graph query filters by `project` property; never operate on unscoped data
- **Graph separation** — `OntoGraph` for ontology, `Metagraph` for rules, `ValidationGraph` for validation
- **No ORM** — raw Cypher queries everywhere (Python, C#, JS)
- **Design file sync** — `.pen` files in `graph-viewer/interface/` should be updated when `index.html` UI changes
