---
tags: [debugging, phase-36, critical, wire-protocol]
date: 2026-07-19
title: Phase 36 CR-01 — Publish wire contract mismatch
severity: Critical
status: fixed
---

# CR-01 — Publish Wire Contract Mismatch

## Root Cause

C# Grasshopper `ComputgraphPublishClient` serializes with `JsonNamingPolicy.CamelCase`:

```csharp
client.Publish(new ComputgraphPublishRequest 
{ 
    Project = "default", 
    CgContext = contextJson  // serializes as {"cgContext": "..."}
});
```

But FastAPI `data-service/app.py:1339` declares:

```python
class ComputgraphPublishRequest(BaseModel):
    project: str
    cg_context: dict  # expects snake_case, no alias
```

**Wire mismatch:** Client sends `{"cgContext": "..."}`, server declares `cg_context` — Pydantic rejects as 422 "Field required: cg_context".

## Impact

Every invocation of the GH COMPUTGRAPH PUBLISH component returns 422 before reaching validation logic. The publish flow is **dead on arrival**.

## Why It Wasn't Caught

Unit tests in `data-service/tests/test_app.py` call `publish_structure()` directly and never cross the HTTP boundary:

```python
result = publish_structure(  # Direct call, bypasses POST validation
    cgContext=context,
    project="default"
)
```

## Fix

Renamed the pydantic field to match the wire format:

```python
class ComputgraphPublishRequest(BaseModel):
    project: str
    cgContext: dict  # matches camelCase wire contract
```

This aligns with every other GH-facing model in app.py (`statePayloadJson`, `ruleResults`, etc.) which all use camelCase.

**Commit:** `2ca8030` — fix(36): CR-01 ComputgraphPublishRequest.cg_context camelCase wire contract

## Prevention

- Add HTTP-level integration tests that cross the wire (Pydantic contract boundary) for all GH-facing endpoints
- Audit all pydantic models in app.py for field naming consistency (already done; all now camelCase on wire)

## Related

- [[debugging/Phase 36 property truncation data loss|CR-02 truncation root cause (paired critical issue)]]
- Schema propagation rule: wire contracts must be synchronized with C# serialization policy changes
