#!/usr/bin/env bash
# ==============================================================================
# Phase 14 smoke test: Graph query — SCHM-10 Wave 0 harness
# ==============================================================================
#
# PURPOSE
#   POSTs a natural-language query to the n8n graph-query webhook, then inspects
#   the generated Cypher in the response to verify it references r.SWRL (the v4
#   PascalCase property name) rather than exclusively r.text (v3). The test
#   passes when the generated Cypher uses r.SWRL.
#
# PREREQUISITES
#   - Docker stack running (`docker compose up -d`)
#   - n8n workflow `graph-query-mcp.json` is **imported and active** in n8n
#     (editing the JSON file on disk has NO runtime effect — see GOTCHA below)
#   - n8n webhook is reachable at http://localhost:8080/n8n/webhook/dg/graph-query
#   - Ollama running (cold-start latency 40-70s handled via curl --max-time)
#
# N8N RE-IMPORT GOTCHA
#   Editing n8n/workflows/graph-query-mcp.json on disk has zero effect on the
#   running n8n instance — n8n stores its workflow definitions in its own SQLite
#   DB (`n8n_data` volume). After editing the JSON file, you MUST re-import it:
#
#   1. Inject a top-level "id" field into a scratch copy of the JSON (n8n's
#      import:workflow command requires it, but the committed JSON does not have
#      one — the file uses only per-node ids).
#   2. docker cp the scratch copy into the container:
#        docker cp ./n8n/workflows/graph-query-mcp.json n8n:/tmp/graph-query-mcp.json
#   3. Import:
#        docker exec n8n n8n import:workflow --input=/tmp/graph-query-mcp.json
#   4. Activate:
#        docker exec n8n n8n update:workflow --active=true --id=<workflow-id>
#   5. Restart n8n:
#        docker restart n8n
#
#   See DG_OBSIDIAN/sessions/2026-06-23 New PC Docker setup and n8n workflow
#   fix.md for the complete workaround with exact commands.
#
# USAGE
#   bash test/smoke_graph_query.sh
#
# EXIT CODES
#   0 — all assertions passed
#   1 — one or more assertions failed
# ==============================================================================

set -euo pipefail

BASE_URL="http://localhost:8080"
PROJECT="phase14-smoke"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1 — $2"; ((FAIL++)); }

echo "=== Phase 14 Smoke: Graph Query (SCHM-10) ==="
echo ""

# -------------------------------------------------------
# Step 1: Send a NL query via n8n webhook
# -------------------------------------------------------
echo "[Step 1] POST /n8n/webhook/dg/graph-query"

QUERY_RESP=$(curl -s --max-time 180 -X POST \
  "${BASE_URL}/n8n/webhook/dg/graph-query" \
  -H "Content-Type: application/json" \
  -d '{"prompt_text":"List all rules with their SWRL text","project_name":"phase14-smoke"}')

echo "  Raw response (first 500 chars):"
echo "$QUERY_RESP" | head -c 500
echo ""
echo ""

# -------------------------------------------------------
# Step 2: Inspect the response for generated Cypher
# -------------------------------------------------------
echo "[Step 2] Inspecting generated Cypher for r.SWRL reference"

# The graph-query workflow returns a JSON payload — the generated Cypher may be
# nested inside the response under various possible keys depending on n8n node
# output shape. Attempt to extract it and check for r.SWRL usage.

EXTRACT_RESULT=$(echo "$QUERY_RESP" | python -c "
import sys, json, re

data = json.load(sys.stdin)

# Try common response shapes
candidate = None

# Shape 1: direct string response
if isinstance(data, str):
    candidate = data
# Shape 2: { result: '...' } or { cypher: '...' }
elif isinstance(data, dict):
    for key in ['result', 'cypher', 'generatedCypher', 'query', 'response', 'output', 'text']:
        if key in data and isinstance(data[key], str) and len(data[key]) > 10:
            candidate = data[key]
            break
    # Shape 3: nested in executionData or workflow result
    if not candidate and 'executionData' in data:
        candidate = json.dumps(data['executionData'])
    # Shape 4: spew the whole JSON for manual inspection
    if not candidate:
        candidate = json.dumps(data, indent=2)

if candidate:
    # Check for r.SWRL reference (positive signal)
    has_swrl = 'r.SWRL' in candidate or 'r\\.SWRL' in candidate or 'SWRL' in candidate
    # Check for exclusive r.text usage (negative signal — only r.text, no SWRL)
    text_only = bool(re.search(r'r\\.text', candidate)) and not has_swrl

    if has_swrl:
        print('SWRL_FOUND')
        sys.exit(0)
    elif text_only:
        print('TEXT_ONLY')
        sys.exit(2)
    else:
        # Ambiguous — neither r.SWRL nor r.text found; dump snippet for inspection
        print('AMBIGUOUS')
        print(candidate[:300])
        sys.exit(3)
else:
    print('NO_CYPHER')
    sys.exit(4)
" 2>&1)

EXIT_CODE=$?

case $EXIT_CODE in
  0)
    pass "Generated Cypher references r.SWRL"
    ;;
  2)
    fail "r.SWRL check" "Generated Cypher references only r.text (old v3 workflow still active)"
    ;;
  3)
    fail "r.SWRL check" "Ambiguous response — neither r.SWRL nor r.text recognized"
    echo "  Response snippet:"
    echo "$EXTRACT_RESULT"
    ;;
  *)
    fail "r.SWRL check" "Could not extract generated Cypher from response (exit $EXIT_CODE)"
    echo "  Response:"
    echo "$QUERY_RESP" | head -c 400
    ;;
esac

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
