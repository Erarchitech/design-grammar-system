#!/usr/bin/env bash
# ==============================================================================
# Phase 14 smoke test: Rule ingest — SCHM-09 Wave 0 harness
# ==============================================================================
#
# PURPOSE
#   POSTs a natural-language rule to the n8n rules-ingest webhook, then queries
#   Neo4j to verify the written Rule node carries the `.SWRL` property (v4
#   PascalCase). The test passes only when `.SWRL` is present — absence means
#   either the old (v3) workflow definition is still active in n8n or the new
#   workflow does not populate `.SWRL`.
#
# PREREQUISITES
#   - Docker stack running (`docker compose up -d`)
#   - n8n workflow `rules-to-metagraph.json` is **imported and active** in n8n
#     (editing the JSON file on disk has NO runtime effect — see GOTCHA below)
#   - n8n webhook is reachable at http://localhost:8080/n8n/webhook/dg/rules-ingest
#   - Neo4j is reachable at http://localhost:7474/db/neo4j/tx/commit
#   - Ollama running (cold-start latency 40-70s handled via curl --max-time)
#
# N8N RE-IMPORT GOTCHA
#   Editing n8n/workflows/rules-to-metagraph.json on disk has zero effect on the
#   running n8n instance — n8n stores its workflow definitions in its own SQLite
#   DB (`n8n_data` volume). After editing the JSON file, you MUST re-import it:
#
#   1. Inject a top-level "id" field into a scratch copy of the JSON (n8n's
#      import:workflow command requires it, but the committed JSON does not have
#      one — the file uses only per-node ids).
#   2. docker cp the scratch copy into the container:
#        docker cp ./n8n/workflows/rules-to-metagraph.json n8n:/tmp/rules-to-metagraph.json
#   3. Import:
#        docker exec n8n n8n import:workflow --input=/tmp/rules-to-metagraph.json
#   4. Activate:
#        docker exec n8n n8n update:workflow --active=true --id=<workflow-id>
#   5. Restart n8n:
#        docker restart n8n
#
#   See DG_OBSIDIAN/sessions/2026-06-23 New PC Docker setup and n8n workflow
#   fix.md for the complete workaround with exact commands.
#
# USAGE
#   bash test/smoke_rules_ingest.sh
#
# EXIT CODES
#   0 — all assertions passed
#   1 — one or more assertions failed
# ==============================================================================

set -euo pipefail

BASE_URL="http://localhost:8080"
NEO4J_URL="http://localhost:7474/db/neo4j/tx/commit"
PROJECT="phase14-smoke"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1 — $2"; ((FAIL++)); }

echo "=== Phase 14 Smoke: Rules Ingest (SCHM-09) ==="
echo ""

# -------------------------------------------------------
# Step 1: Ingest a rule via n8n webhook
# -------------------------------------------------------
echo "[Step 1] POST /n8n/webhook/dg/rules-ingest"

INGEST_RESP=$(curl -s --max-time 180 -X POST \
  "${BASE_URL}/n8n/webhook/dg/rules-ingest" \
  -H "Content-Type: application/json" \
  -d '{"rules_text":"Maximum height of each Warehouse must be 40 m.","project_name":"phase14-smoke"}')

echo "  Ingest response: $(echo "$INGEST_RESP" | head -c 200)"
echo ""

# -------------------------------------------------------
# Step 2: Wait for the workflow to finish (short backoff)
# -------------------------------------------------------
echo "[Step 2] Waiting for workflow completion..."
sleep 5

# -------------------------------------------------------
# Step 3: Query Neo4j for the written Rule node
# -------------------------------------------------------
echo "[Step 3] Querying Neo4j for written Rule node with .SWRL"

SWRL_QUERY='{"statements":[{"statement":"MATCH (r:Rule {project:'\''phase14-smoke'\''}) RETURN r.Rule_Id AS id, r.SWRL AS swrl, r.text AS text ORDER BY r.Rule_Id LIMIT 5"}]}'

NEO4J_RESP=$(curl -s --max-time 30 -X POST "$NEO4J_URL" \
  -H "Content-Type: application/json" \
  -u neo4j:12345678 \
  -d "$SWRL_QUERY")

echo "  Neo4j response: $(echo "$NEO4J_RESP" | head -c 300)"
echo ""

# -------------------------------------------------------
# Step 4: Assert that at least one row has a non-empty .SWRL
# -------------------------------------------------------
echo "[Step 4] Asserting at least one Rule node carries non-empty .SWRL"

if echo "$NEO4J_RESP" | python -c "
import sys, json
data = json.load(sys.stdin)
rows = data['results'][0]['data']
for row in rows:
    swrl = row['row'][1]
    if swrl and swrl.strip():
        print(f'  Found .SWRL: {swrl[:80]}...')
        sys.exit(0)
print('  ERROR: No Rule node with a non-empty .SWRL property found.')
print('  This means the n8n workflow definition is still the old v3 version')
print('  (which writes r.text, not r.SWRL). Re-import the edited workflow')
print('  JSON per the N8N RE-IMPORT GOTCHA above and re-run this test.')
sys.exit(1)
" 2>&1; then
  pass "Ingested Rule node carries .SWRL property"
else
  fail ".SWRL check" "No non-empty .SWRL found in any Rule node"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
