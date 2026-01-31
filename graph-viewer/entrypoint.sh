#!/usr/bin/env sh
set -e

# Write config.js from environment or defaults
tmpl=/usr/share/nginx/html/config.template.js
out=/usr/share/nginx/html/config.js

NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687}
NEO4J_HTTP=${NEO4J_HTTP:-/neo4j}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-12345678}

# Basic replacement to keep it simple
sed \
  -e "s|bolt://localhost:7687|${NEO4J_URI}|" \
  -e "s|/neo4j|${NEO4J_HTTP}|" \
  -e "s|neo4j|${NEO4J_USER}|" \
  -e "s|12345678|${NEO4J_PASSWORD}|" \
  "$tmpl" > "$out"

exec nginx -g 'daemon off;'
