#!/usr/bin/env sh
set -e

# Regenerate the non-secret runtime config consumed by the V2 app
# (window.GRAPH_CONFIG), then hand over to nginx. See gen-config.sh.
/gen-config.sh /usr/share/nginx/html/config.js

exec nginx -g 'daemon off;'
