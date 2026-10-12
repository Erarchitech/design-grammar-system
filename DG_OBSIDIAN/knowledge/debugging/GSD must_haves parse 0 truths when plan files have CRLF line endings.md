---
tags: [debugging, gsd, planning, windows]
date: 2026-10-12
---

# GSD must_haves parse 0 truths when plan files have CRLF line endings

## Symptom

After planning Phase 1308, `roadmap.annotate-dependencies` printed `must_haves.truths block has N content lines but parsed 0 items` for 15 of 24 plans. `frontmatter.get` and the decision-coverage gate still passed, so nothing else showed the problem. The verifier would have fallen back to LLM-derived truths.

## Root cause

`parseMustHavesBlock` (`.claude/gsd-core/bin/lib/frontmatter.cjs`) finds the block with `^(\s+)truths:\s*$` in multiline mode. With CRLF, `\s+` starts after the `\r` of the previous line and captures `\n  `, so the block indent becomes 3. The header line itself then has indent 2 ≤ 3 and stops the scan at once, leaving 0 items. The Claude `gsd-planner` subagent left CRLF in 15 files; DSH workers do the same.

Misleading checks: Git Bash `cat -A` on an LF file (plan 02) and `grep -c $'\r'` (counted every line) suggested the opposite. `JSON.stringify` of the text around `truths:` in node showed the `\r\n`.

## Fix

Normalize every phase `.md` to LF with node (`s.replace(/\r\n/g, '\n')`), then call `parseMustHavesBlock(content, 'truths')` for each plan and expect a non-zero count. `core.autocrlf` may reintroduce CRLF on checkout, so re-check before execute/verify.

## Related

- Memory note `dsh-planning-worker-patterns` (CRLF after DSH writes).
