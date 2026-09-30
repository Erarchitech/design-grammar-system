#!/usr/bin/env sh
set -e

# Regenerate the non-secret runtime config consumed by the V2 app
# (window.GRAPH_CONFIG), then hand over to nginx. See gen-config.sh.
/gen-config.sh /usr/share/nginx/html/config.js

# WR-23 (1205 review): restore the real client address from X-Forwarded-For, but
# only for requests that arrive from an explicitly trusted proxy. Without
# DG_TRUSTED_PROXIES the include stays empty, so a client can never pick its own
# address by sending the header. Each entry must be an address or CIDR; anything
# else stops the container rather than silently weakening the address-keyed
# limits.
realip=/etc/nginx/dg-realip.conf
: > "$realip"
if [ -n "${DG_TRUSTED_PROXIES:-}" ]; then
  set -f
  for entry in $(printf '%s' "$DG_TRUSTED_PROXIES" | tr ',' ' '); do
    case "$entry" in
      *[!0-9a-fA-F:./]*)
        echo "DG_TRUSTED_PROXIES: entries must be IP addresses or CIDR ranges" >&2
        exit 1
        ;;
    esac
    echo "set_real_ip_from $entry;" >> "$realip"
  done
  set +f
  if [ -s "$realip" ]; then
    echo "real_ip_header X-Forwarded-For;" >> "$realip"
    echo "real_ip_recursive on;" >> "$realip"
  fi
fi

exec nginx -g 'daemon off;'
