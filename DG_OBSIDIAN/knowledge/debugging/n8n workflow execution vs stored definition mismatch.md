# n8n: Workflow Execution vs Stored Definition Mismatch

**Date found:** 2026-07-19 (Phase 29 gap-closure session)  
**Severity:** high (affects live graph-query webhook, bypasses security gates)  
**Status:** open (user deferred manual fix; root cause unknown)

## The problem

The live n8n `dg/graph-query` webhook (active workflow `b2c3d4e5-f6a7-8901-bcde-f12345678901`, "DG Graph Query (MCP)") executes an **old workflow version** that does NOT call the context-layer endpoints, despite the **stored definition being correct**.

### Evidence

**Stored definition (from n8n REST API `GET /rest/workflows/b2c3d4e5...`):**
- 17 nodes, correct context-layer architecture
- `Assemble Context` → `POST /context/assemble`
- `Generate Validated Cypher` → `POST /context/generate-cypher`
- `updatedAt: 2026-07-19T00:02:00.050Z` (freshly updated by 29-07 PATCH)

**Actual execution (observed via data-service logs, executions 200–205):**
- Only `POST /mcp` + `POST /llm/generate` fire
- Never `POST /context/assemble` or `/context/generate-cypher`
- LLM emits `:DesignState` queries (old, pre-29 architecture)

### Attempted fixes (all failed to change routing)

1. **API reactivation:** `PATCH /rest/workflows/{id} {active: false}` → response stayed `active: true` (no state transition, no reload)
2. **Full restart:** `docker compose restart n8n` → n8n healthz 200 within ~6s; execution 205 (post-restart) still bypassed `/context/*`

### Root cause (unknown)

Hypothesis areas (none yet verified):
- n8n internal workflow cache not invalidated by PATCH or restart
- Webhook registration stuck on old route (stale reverse-proxy or ingress mapping)
- Active-flag toggle doesn't reload; only a full unload+reload would (not exposed via API)
- Multiple active "DG Graph Query" workflows confusing the router (5 stale duplicates exist; only `b2c3d4e5` should be active, and it is)

## Impact

- ✗ CTXA-04 (validate_cypher security gate) not enforced for live graph queries
- ✗ Design-state queries never see the corrected `:ValidationRun` schema + live `existing_design_states` data
- ✓ Code is correct and committed; issue is purely operational (n8n instance state)

## Resolution path (manual)

User will:
1. Manually **paste `n8n/workflows/graph-query-mcp.json` content into the n8n UI editor** (not via REST API)
2. Confirm re-run hits `/context/*` + answer is correct
3. If still broken: consider deleting all 5 stale duplicate "DG Graph Query" workflows and re-pasting fresh

## Future investigation

If manual paste doesn't fix it:
- Check n8n logs for webhook registration errors or conflicts
- Verify the 5 stale duplicates aren't somehow intercepting the webhook path (one is `F0RCL8vKpzRcEbzp`, another `bg9fvbEZS98K1V1y`, etc. — check which is registered on `dg/graph-query`)
- Consider a full n8n rebuild / purge of the workflows table (destructive; last resort)
- n8n version / configuration constraints (do other workflows exhibit this after PATCH + restart?)

## Related

- [[n8n Workflows Had a Fatal Quote Bug and Silent Project-Scoping Failure]] — prior n8n routing issue (2026-03 or earlier), resolved via reconciliation
- CLAUDE.md "reconcile live n8n workflows with n8n/workflows/*.json" — ongoing n8n drift reconciliation work
