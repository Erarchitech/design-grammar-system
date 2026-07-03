#!/usr/bin/env bash
# Phase 4 integration test: Update flow endpoints
# Requires: docker compose up -d (all services running)
# Usage: bash test/test_phase04_update_flow.sh

set -euo pipefail
BASE="http://localhost:8000"
PROJECT="test-update-flow"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1 — $2"; ((FAIL++)); }

echo "=== Phase 4: Update Flow Integration Tests ==="
echo ""

# --- Setup: Create a test note via folder ingest or direct CRUD ---
echo "[Setup] Creating test note..."
# Use the existing PUT endpoint to ensure a note exists
NOTE_ID="test-update-$(date +%s)"
# First create via Cypher (direct write through data-service debug or use ingest)
# Simpler: use the /knowledge/ingest/folder with a known .md file
# Actually simplest: call the match endpoint and use whatever notes exist
# For a real integration test, we need a known note. Create one via Neo4j HTTP API.

# Create a test note directly via Neo4j HTTP API
NEO4J_URL="http://localhost:7474/db/neo4j/tx/commit"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
curl -s -X POST "$NEO4J_URL" \
  -H "Content-Type: application/json" \
  -u neo4j:12345678 \
  -d "{
    \"statements\": [{
      \"statement\": \"MERGE (n:SpecNote {noteId: '$NOTE_ID', project: '$PROJECT', graph: 'SpecGraph'}) SET n.title = 'Test Update Note', n.content = 'The building has a maximum height of 50 meters and minimum setback of 5 meters.', n.updatedAt = '$NOW', n.createdAt = '$NOW'\"
    }]
  }" > /dev/null 2>&1
echo "  Created note: $NOTE_ID"
echo ""

# --- Test 1: Match endpoint ---
echo "[Test 1] POST /knowledge/update/match"
MATCH_RESP=$(curl -s -X POST "$BASE/knowledge/update/match" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"building height\", \"project\": \"$PROJECT\"}")

if echo "$MATCH_RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert 'candidates' in d" 2>/dev/null; then
  pass "Match returns candidates array"
else
  fail "Match response" "$MATCH_RESP"
fi

# --- Test 2: Match with empty prompt returns 400 ---
echo "[Test 2] POST /knowledge/update/match (empty prompt)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/knowledge/update/match" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"   \", \"project\": \"$PROJECT\"}")
if [ "$STATUS" = "400" ]; then
  pass "Empty prompt returns 400"
else
  fail "Empty prompt" "Expected 400, got $STATUS"
fi

# --- Test 3: Propose endpoint (requires n8n + Ollama running) ---
echo "[Test 3] POST /knowledge/update/propose"
echo "  (This test requires n8n knowledge-update workflow imported and active + Ollama running)"
PROPOSE_RESP=$(curl -s --max-time 180 -X POST "$BASE/knowledge/update/propose" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Change maximum height to 75 meters\", \"project\": \"$PROJECT\", \"noteIds\": [\"$NOTE_ID\"]}")

if echo "$PROPOSE_RESP" | python -c "import sys,json; d=json.load(sys.stdin); diffs=d['diffs']; assert len(diffs)==1; assert 'diffHtml' in diffs[0]; assert 'updatedAt' in diffs[0]" 2>/dev/null; then
  pass "Propose returns diffs with diffHtml and updatedAt"
  # Extract updatedAt for confirm test
  UPDATED_AT=$(echo "$PROPOSE_RESP" | python -c "import sys,json; d=json.load(sys.stdin); print(d['diffs'][0]['updatedAt'])")
  PROPOSED=$(echo "$PROPOSE_RESP" | python -c "import sys,json; d=json.load(sys.stdin); print(d['diffs'][0]['proposedContent'])")
else
  fail "Propose response" "$PROPOSE_RESP"
  UPDATED_AT=""
  PROPOSED=""
fi

# --- Test 4: Confirm endpoint ---
if [ -n "$UPDATED_AT" ]; then
  echo "[Test 4] POST /knowledge/update/confirm"
  CONFIRM_RESP=$(curl -s -X POST "$BASE/knowledge/update/confirm" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"Change maximum height to 75 meters\", \"project\": \"$PROJECT\", \"notes\": [{\"noteId\": \"$NOTE_ID\", \"content\": \"The building has a maximum height of 75 meters and minimum setback of 5 meters.\", \"updatedAt\": \"$UPDATED_AT\"}]}")

  if echo "$CONFIRM_RESP" | python -c "import sys,json; d=json.load(sys.stdin); assert len(d['affectedNodes']) > 0; assert d['sessionId'].startswith('ks-')" 2>/dev/null; then
    pass "Confirm writes and returns affectedNodes + sessionId"
  else
    fail "Confirm response" "$CONFIRM_RESP"
  fi

  # --- Test 5: Confirm with stale updatedAt returns 409 ---
  echo "[Test 5] POST /knowledge/update/confirm (stale updatedAt)"
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/knowledge/update/confirm" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"stale test\", \"project\": \"$PROJECT\", \"notes\": [{\"noteId\": \"$NOTE_ID\", \"content\": \"anything\", \"updatedAt\": \"1970-01-01T00:00:00+00:00\"}]}")
  if [ "$STATUS" = "409" ]; then
    pass "Stale updatedAt returns 409"
  else
    fail "Stale updatedAt" "Expected 409, got $STATUS"
  fi
else
  echo "[Test 4] SKIPPED (propose failed)"
  echo "[Test 5] SKIPPED (propose failed)"
fi

# --- Cleanup ---
echo ""
echo "[Cleanup] Removing test note..."
curl -s -X POST "$NEO4J_URL" \
  -H "Content-Type: application/json" \
  -u neo4j:12345678 \
  -d "{\"statements\": [{\"statement\": \"MATCH (n:SpecNote {noteId: '$NOTE_ID'}) DETACH DELETE n\"}]}" > /dev/null 2>&1
curl -s -X POST "$NEO4J_URL" \
  -H "Content-Type: application/json" \
  -u neo4j:12345678 \
  -d "{\"statements\": [{\"statement\": \"MATCH (s:SpecSession {project: '$PROJECT'}) DETACH DELETE s\"}]}" > /dev/null 2>&1

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
