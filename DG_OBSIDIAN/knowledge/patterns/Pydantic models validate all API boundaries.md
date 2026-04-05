---
tags: [pattern, fastapi, pydantic, validation]
date: 2026-04-05
---

# Pydantic Models Validate All API Boundaries

## Pattern

Every request/response body in `data-service/app.py` is a Pydantic `BaseModel`. FastAPI automatically validates incoming JSON against these models and returns 422 for invalid payloads.

## Models

| Model | Endpoint | Direction |
|-------|----------|-----------|
| `ExecutionResult` | `/execution-result` | Request body |
| `SpeckleProjectConfigPayload` | `/integration/speckle/project/{p}` | Request/Response |
| `SpeckleSettingsPayload` | `/settings/speckle` | Request body |
| `ValidationPublishRequest` | `/validation/publish` | Request body |
| `ValidationPublishRulePayload` | Nested in publish | — |
| `ValidationPublishEntityPayload` | Nested in publish | — |
| `ValidationGeometryPayload` | Nested in entity | — |
| `ValidationGeometryItemPayload` | Nested in geometry | — |

## Benefits

- **Automatic type coercion** — strings to ints, etc.
- **Default values** — `Field(default_factory=list)` for optional collections
- **Documentation** — auto-generated OpenAPI schema at `/docs`
- **Error messages** — detailed 422 response with field-level errors

## Example

```python
class ValidationPublishRulePayload(BaseModel):
    ruleId: str
    ruleName: str = ""
    ruleDescription: str = ""
```

Missing `ruleId` → 422 with `"field required"` error.

## Related

- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
- [[FastAPI data-service bridges MCP Neo4j and Speckle]]
