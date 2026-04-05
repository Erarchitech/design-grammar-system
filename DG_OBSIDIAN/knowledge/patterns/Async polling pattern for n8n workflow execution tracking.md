---
tags: [pattern, async, polling, n8n, workflow]
date: 2026-04-05
---

# Async Polling Pattern for n8n Workflow Execution Tracking

## Pattern

n8n workflows return an immediate 200 acknowledgment, then process asynchronously. The UI polls for completion.

## Implementation

### n8n Side
1. Webhook node sends immediate "Respond Ack" (200 with `executionId`)
2. Workflow continues processing, POSTing status updates to `/execution-result`:
   ```json
   {"executionId": "abc-123", "status": "running", "step": 2, "progress": 40}
   ```
3. Final step POSTs `status: "completed"` with payload

### UI Side (GraphViewerPage)
```javascript
// After sending webhook:
const poll = setInterval(async () => {
  const res = await fetch(`/data-service/execution-result/${executionId}`);
  const data = await res.json();
  setProgress(data.progress);
  setStep(data.step);
  if (data.status === 'completed' || data.status === 'error') {
    clearInterval(poll);
    // handle result
  }
}, 1500); // every 1.5 seconds
```

### Step Breakdown

**Ingest (5 steps)**: Send rules → LLM parse → Write graph → Annotate properties → Reload graph  
**Query (5 steps)**: Send prompt → Generate cypher → Query graph → Generate response → Complete

Timer shows elapsed time per step.

## Why This Pattern

- n8n webhook timeout is limited; LLM inference can take 30-60 seconds
- Immediate 200 prevents browser/proxy timeouts
- Step-by-step progress gives user feedback during long operations

## Related

- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[FastAPI data-service bridges MCP Neo4j and Speckle]]
