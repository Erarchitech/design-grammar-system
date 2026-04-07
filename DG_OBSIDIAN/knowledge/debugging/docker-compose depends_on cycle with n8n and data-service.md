---
tags: [debugging, docker, phase-04]
date: 2026-04-07
status: resolved
---

# docker-compose depends_on cycle with n8n and data-service

## Problem

Adding `n8n` to data-service `depends_on` in docker-compose.yml created a circular dependency:

```
data-service -> n8n -> data-service
```

Docker Compose refused to build with error: `dependency cycle detected: data-service -> n8n -> data-service`.

## Root Cause

n8n's Post Result node calls `http://data-service:8000/execution-result`, so n8n already depends_on data-service. Adding the reverse dependency created a cycle.

## Fix

Removed `n8n` from data-service `depends_on`. The `N8N_INTERNAL_URL` env var remains — data-service resolves n8n via Docker DNS at runtime (when the propose endpoint is called), not at container startup. If n8n isn't running, the propose endpoint returns 502.

## Lesson

Service A calling service B at runtime ≠ service A depends_on service B. Use `depends_on` only for startup ordering requirements, not for runtime HTTP call targets.
