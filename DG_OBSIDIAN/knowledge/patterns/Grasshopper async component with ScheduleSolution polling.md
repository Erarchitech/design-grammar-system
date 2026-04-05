---
tags: [pattern, grasshopper, async, csharp]
date: 2026-04-05
---

# Grasshopper Async Component with ScheduleSolution Polling

## Pattern

Grasshopper components can't use `async/await` directly because `SolveInstance()` is synchronous. DG components use a task-caching + document scheduling pattern to simulate async behavior.

## Implementation

```csharp
// In SolveInstance():
if (_cachedTask == null || requestKeyChanged) {
    _cachedTask = Task.Run(() => DoExpensiveWork(cancellationToken));
    _cachedRequestKey = currentKey;
}

if (!_cachedTask.IsCompleted) {
    OnPingDocument()?.ScheduleSolution(200, _ => ExpireSolution(true));
    return; // exit early, will re-enter when scheduled
}

// Task completed — read result
var result = _cachedTask.Result;
```

## Key Elements

- **Request key** — hash of input parameters; if unchanged, reuse cached task
- **ScheduleSolution** — re-triggers `SolveInstance()` after 200ms delay
- **Cancellation** — old tasks cancelled if parameters change (`_cts.Cancel()`)
- **Timeout** — `WaitAsync(TimeSpan.FromSeconds(6))` prevents infinite hangs

## Used In

| Component | Async Operation |
|-----------|----------------|
| `ConnectorComponent` | Neo4j connection + ping |
| `MetagraphComponent` | Rule loading from Neo4j |
| `ValidatorComponent` | HTTP POST to data-service |

## Why Not Events

Grasshopper's SDK doesn't support event-driven updates cleanly. ScheduleSolution is the idiomatic approach for periodic re-evaluation.

## Related

- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[Conditional compilation guards Grasshopper SDK availability]]
