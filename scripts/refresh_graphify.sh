#!/usr/bin/env bash
# refresh_graphify.sh — regenerate the Obsidian conceptual notes from the
# current graphify-out/graph.json. Diff-based: only changed notes are rewritten.
# No LLM / no token cost.
#
# Run from the project root after the graph has been rebuilt:
#   bash scripts/refresh_graphify.sh
#
# IMPORTANT — graph rebuilds go through the SLASH flow, not this script:
#   /graphify --update     (in Claude Code) — incremental, respects scoping +
#                          semantic extraction for docs. Then run THIS script.
#
# Do NOT use the bare `graphify update .` CLI here: it re-scans the whole repo
# without the slash flow's scoping, indexes graphify's own DG_OBSIDIAN output
# and the .planning/ churn, and balloons the graph (1836 -> 4000+ nodes). The
# .graphifyignore file guards against this, but the slash flow is still the
# correct rebuild path because it also runs semantic (LLM) extraction on docs.
#
# NEVER run `graphify install` — it would overwrite the project's thin SKILL.md.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

if [ ! -f graphify-out/.graphify_python ]; then
  echo "error: graphify-out/.graphify_python not found. Run /graphify first." >&2
  exit 1
fi
if [ ! -f graphify-out/graph.json ]; then
  echo "error: graphify-out/graph.json not found. Run /graphify first." >&2
  exit 1
fi

PY=$(tr -d '\r\n' < graphify-out/.graphify_python | sed 's/^\xEF\xBB\xBF//')
export PYTHONIOENCODING=utf-8

echo "Regenerating Obsidian conceptual notes (diff-based)..."
"$PY" scripts/export_graphify_conceptual.py || { echo "conceptual export failed" >&2; exit 1; }

echo "Done. Obsidian notes refreshed from current graph.json."
