---
tags: [debugging, tooling, perplexity, mcp]
date: 2026-07-13
---

# Perplexity MCP: parallel calls crash the shared Chrome profile lock

## Symptom

Issuing multiple `mcp__Perplexity__*` tool calls in the same message (parallel) fails every call with:

```
Error: browserType.launchPersistentContext: Target page, context or browser has been closed
```

The Perplexity MCP server drives one headless Chrome instance against a single persistent profile (`~/.perplexity-mcp/profiles/<account>/browser-data`). Parallel `launchPersistentContext` calls race the profile's own lock file; the loser(s) fail, and a "winner" Chrome process can be left running and holding the lock, so even subsequent *sequential* calls keep failing until it's cleared.

## Root cause

Single shared browser profile + Playwright's `launchPersistentContext`, which is not designed for concurrent launches against the same user-data-dir.

## Fix

1. Find orphaned Chrome processes tied to the profile: filter `Win32_Process` where `Name='chrome.exe'` and `CommandLine` matches `perplexity-mcp`.
2. Kill the root process in that tree (verify it's the perplexity profile, not the user's regular browser, by checking `user-data-dir` in the command line).
3. Delete the stale `lockfile` in the profile's `browser-data` directory.
4. Retry — issuing calls **strictly one at a time**, never in parallel.

## Prevention

Always call Perplexity MCP tools sequentially, one call per turn. This applies to subagent prompts too — if a subagent is told to use Perplexity MCP for research, its instructions must say "one call at a time" explicitly, since the failure mode isn't obvious from a single subagent's perspective (it just sees its own call fail).

Note also: GSD subagent tool namespaces (e.g. references to `mcp__perplexity__*` lowercase) do not match this session's actual server name `mcp__Perplexity__*` (capital P) — subagents following generic instructions to "use Perplexity MCP" may silently fall back to WebSearch instead. Perplexity sweeps are more reliable run at the orchestrator level, with findings seeded into subagent prompts as context.

## Related

- [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|session where this was hit and fixed]]
