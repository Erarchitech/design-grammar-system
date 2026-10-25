#!/usr/bin/env bash
# Build and start the DG stand from the repository root on the server. Safe to re-run.
# Prerequisites: bootstrap-server.sh done; a private env file created next to docker-compose.yml
# by deploy/hosted/server/make_env.py; DNS A records for the three host names point at this server.
set -euo pipefail

cd "$(dirname "$0")/../../.."
FILES=(-f docker-compose.yml -f docker-compose.multi-user.yml -f docker-compose.hosted.yml -f docker-compose.server.yml)
dc() { docker compose "${FILES[@]}" "$@"; }

if [ ! -f .env ]; then
    echo "environment file missing: run deploy/hosted/server/make_env.py first" >&2
    exit 1
fi

# Compose >= 2.24.4 is required for the !override / !reset tags.
version="$(docker compose version --short)"
if [ "$(printf '%s\n2.24.4\n' "$version" | sort -V | head -n1)" != "2.24.4" ]; then
    echo "docker compose $version is too old (need >= 2.24.4)" >&2
    exit 1
fi

dc config --quiet
dc build
dc up -d

# Speckle creates its own schema and registers its built-in apps on first start. The bootstrap SQL
# inserts into tables (scopes, server_apps_scopes, token_scopes) that reference those apps by key
# (spklwebapp, explorer), so it must run only after both the tables and the apps exist; mounting it
# into PostgreSQL's first-init directory fails on an empty database. Idempotent (ON CONFLICT DO NOTHING).
ready=0
for _ in $(seq 1 90); do
    state="$(dc exec -T speckle-postgres psql -U speckle -d speckle -tAc \
        "select (to_regclass('public.scopes') is not null)
             and (to_regclass('public.server_apps_scopes') is not null)
             and (to_regclass('public.token_scopes') is not null)
             and (to_regclass('public.user_server_app_tokens') is not null)
             and (to_regclass('public.server_apps') is not null)
             and (select count(*) from server_apps where id in ('spklwebapp', 'explorer')) = 2" 2>/dev/null || true)"
    if [ "$state" = "t" ]; then
        ready=1
        break
    fi
    sleep 5
done
if [ "$ready" -ne 1 ]; then
    echo "Speckle schema did not appear within 7.5 minutes. Check: docker compose logs speckle-server speckle-postgres" >&2
    exit 1
fi
if ! dc exec -T speckle-postgres psql -U speckle -d speckle -v ON_ERROR_STOP=1 -f - < speckle/bootstrap-local.sql; then
    echo "Speckle bootstrap SQL failed; the stack is running. Re-run deploy.sh (the SQL is idempotent) or inspect: docker compose logs speckle-server" >&2
    exit 1
fi

dc ps
dg_host="$(grep -E '^HOSTED_DG_HOST=' .env | cut -d= -f2- || true)"
echo "DG stand started. Open https://${dg_host} once the certificates are issued (first start can take a minute)."
echo "Initial administrator: user and password are in the private env file (DG_BOOTSTRAP_ADMIN_*). Change the password after first login."
