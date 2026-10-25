#!/usr/bin/env bash
# Load the two core DG workflows into a FRESH n8n volume and publish them (n8n 2.4.8).
# Verified on the real server 2026-10-24: `import:workflow` needs an `id` in the JSON (the file's own
# id is kept, otherwise the file name is used); the older activation verb is deprecated, `publish:workflow
# --id=<id>` is the current one; n8n must be restarted afterwards because it runs the PUBLISHED
# version. The repository copies may be older than the live workflows the owner used earlier:
# compare before relying on them. Safe to re-run (same id = same workflow).
set -euo pipefail

cd "$(dirname "$0")/../../.."
FILES=(-f docker-compose.yml -f docker-compose.multi-user.yml -f docker-compose.hosted.yml -f docker-compose.server.yml)
dc() { docker compose "${FILES[@]}" "$@"; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for name in rules-to-metagraph graph-query-mcp; do
    # Prepare the file and print the id n8n will store (the file's own id wins over the file name).
    workflow_id="$(python3 - "$name" "$tmp" <<'PY'
import json, sys
from pathlib import Path
name, tmp = sys.argv[1], Path(sys.argv[2])
data = json.loads(Path("n8n/workflows", name + ".json").read_text(encoding="utf-8"))
data.setdefault("id", name)
(tmp / (name + ".json")).write_text(json.dumps(data), encoding="utf-8")
print(data["id"])
PY
)"
    docker cp "$tmp/$name.json" "n8n:/tmp/$name.json"
    docker exec n8n n8n import:workflow --input="/tmp/$name.json"
    docker exec n8n n8n publish:workflow --id="$workflow_id"
done
dc restart n8n
echo "n8n workflows imported and published. Verify with test/smoke_rules_ingest.sh and test/smoke_graph_query.sh."
