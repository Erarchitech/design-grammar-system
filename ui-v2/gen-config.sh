#!/usr/bin/env sh
# Generate the browser runtime config (window.GRAPH_CONFIG) for the V2 app.
#
# Usage: sh gen-config.sh [OUT]      (default OUT: /usr/share/nginx/html/config.js)
#
# Phase 1205 D-12: this reads exactly two environment variables and writes
# exactly two non-secret keys. Nothing else from the container environment is
# ever copied into a browser-readable file, even if it is present.
set -e

out="${1:-/usr/share/nginx/html/config.js}"

# Escape backslash and double quote so a hostile value cannot break out of the
# JS string literal; strip CR/LF so it stays on one line.
js_escape() {
  printf '%s' "$1" | tr -d '\r\n' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

data_service_url="$(js_escape "${DATA_SERVICE_URL:-/data-service}")"
speckle_base_url="$(js_escape "${SPECKLE_BASE_URL:-http://localhost:8090}")"

cat > "$out" <<EOF
// generated at container start; carries no secret - Phase 1205 D-12
window.GRAPH_CONFIG = {
  dataServiceUrl: "${data_service_url}",
  speckleBaseUrl: "${speckle_base_url}"
};
EOF
