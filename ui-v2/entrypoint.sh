#!/usr/bin/env sh
set -e

# Regenerate the runtime config consumed by the V2 app (window.GRAPH_CONFIG)
# from environment variables. Values fall back to the compose-stack defaults.
out=/usr/share/nginx/html/config.js

cat > "$out" <<EOF
window.GRAPH_CONFIG = {
  neo4jUri: "${NEO4J_URI:-bolt://localhost:7687}",
  neo4jHttp: "${NEO4J_HTTP:-/neo4j}",
  neo4jUser: "${NEO4J_USER:-neo4j}",
  neo4jPassword: "${NEO4J_PASSWORD:-12345678}",
  n8nWebhook: "${N8N_WEBHOOK:-/n8n/webhook/dg/rules-ingest}",
  n8nQueryWebhook: "${N8N_QUERY_WEBHOOK:-/n8n/webhook/dg/graph-query}",
  dataServiceUrl: "${DATA_SERVICE_URL:-/data-service}",
  speckleBaseUrl: "${SPECKLE_BASE_URL:-http://localhost:8090}",
  speckleReadToken: "${SPECKLE_READ_TOKEN:-}"
};
EOF

exec nginx -g 'daemon off;'
