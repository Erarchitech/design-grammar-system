# Phase 20: E2E Validation and Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 20-e2e-validation-and-docs
**Areas discussed:** E2E Test Scope & Failure Handling, Release Notes Structure & Depth, Docs Update Strategy & Depth, DG_OBSIDIAN & Graphify Refresh

---

## E2E Test Scope & Failure Handling

### Q1: E2E execution approach

| Option | Description | Selected |
|--------|-------------|----------|
| Manual checklist + Docker automation | Scripted walkthrough with explicit steps. GH manual, Docker automated via curl/cypher. | ✓ |
| Ad-hoc manual walkthrough | Walk through chain in GH, verify visually, no formal checklist. | |
| Full automated E2E (GH scripting) | Formal test script driving full chain. Requires Rhino scripting. | |

**User's choice:** Manual checklist + Docker automation (Recommended)
**Notes:** Grasshopper requires Rhino 8 running, making full CI automation impractical. Docker side is automatable.

### Q2: Test data

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing project data | Test against accumulated dev data in Neo4j. | |
| Create fresh test fixture | 2-3 representative rules + simple geometry. Clean baseline. | |
| Both fresh + existing | Fresh fixture for checklist, existing project as secondary smoke test. | ✓ |

**User's choice:** Both fresh + existing
**Notes:** Fresh fixture ensures reproducibility. Existing data catches regressions.

### Q3: Failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fix critical bugs inline | Fix chain-breaking bugs as part of Phase 20. | ✓ |
| Log all issues for follow-up | Note every issue, create tracker for bug-fix phase. | |
| Fix blockers only, log rest | Fix crash-level bugs, log cosmetic/warning issues. | |

**User's choice:** Fix critical bugs inline (Recommended)
**Notes:** Phase 20 is the last chance to catch v7.0 bugs before release.

### Q4: Pass bar

| Option | Description | Selected |
|--------|-------------|----------|
| Full chain, all outputs verified | Every step produces correct output, no component errors, no data loss. | ✓ |
| No-crash smoke test | Chain runs without crashes, visual inspection of key checkpoints. | |
| Full chain + round-trip + side effects | All outputs verified + DESIGN STATE round-trip + slider movement verification. | |

**User's choice:** Full chain, all outputs verified (Recommended)
**Notes:** Thorough but not exhaustive — round-trip and side-effect verification are stretch goals, not blockers.

---

## Release Notes Structure & Depth

### Q1: Location

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated RELEASE-NOTES-v7.0.md | New docs/ file with component-by-component breakage, re-wiring table, port-IRI map link. | ✓ |
| CHANGELOG.md section | Add v7.0 section to existing root CHANGELOG. | |
| Both: summary + full guide | CHANGELOG gets brief summary + link to full RELEASE-NOTES. | |

**User's choice:** Dedicated `docs/RELEASE-NOTES-v7.0.md` (Recommended)
**Notes:** Standalone file, referenced from README.md.

### Q2: Component documentation depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full re-wiring guide per component | Old name, new name, what broke, step-by-step re-wiring with port names. | ✓ |
| Table + brief notes | One row per component: Old | New | What Changed | Notes. | |
| Narrative summary only | High-level what changed + why. Re-wiring left to port-IRI map. | |

**User's choice:** Full re-wiring guide per component (Recommended)
**Notes:** Architects need concrete steps, not just awareness of breakage.

### Q3: Coverage beyond components

| Option | Description | Selected |
|--------|-------------|----------|
| Complete: breakage + features + upgrade | Breakage table, re-wiring guide, new features, known limitations, upgrade steps, port-IRI map reference. | ✓ |
| Breakage only | Component breakage and re-wiring guide only. | |
| Breakage + features, no upgrade guide | Breakage guide + new features summary. No upgrade steps. | |

**User's choice:** Complete: breakage + features + upgrade (Recommended)
**Notes:** Sections: Breaking Changes, New Features, Upgrade Guide.

### Q4: Wiring diagram format

| Option | Description | Selected |
|--------|-------------|----------|
| ASCII wiring diagrams | Text-only diagrams showing old → new wiring. Works in any editor. | ✓ |
| Step-by-step instructions only | Numbered steps per component group. | |
| Both diagrams + steps | ASCII diagram + numbered steps per group. | |

**User's choice:** ASCII wiring diagrams (Recommended)
**Notes:** Diagrams show the big picture. Steps implied by the diagram structure.

---

## Docs Update Strategy & Depth

### Q1: Overall strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted update per doc | CLAUDE.md: schema + factual sections. copilot-instructions.md: full rewrite. spec/DATABASE.md: labels/relationships. README.md: component count/status. | ✓ |
| Full rewrite of all docs | Cleanest but risks losing institutional knowledge. | |
| Minimal find-and-replace patches | Surgical v3→v4 only. Risk of stale references surviving. | |

**User's choice:** Targeted update per doc (Recommended)
**Notes:** Each doc gets the depth it needs, not a blanket approach.

### Q2: copilot-instructions.md depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full schema + components rewrite | Graph Schema v4 + 14-component architecture + updated Patterns/Conventions. | ✓ |
| Replace entire file | Fresh v7.0 context. Risk: might lose useful conventions. | |
| Schema update only | Update schema section to v4. Leave rest alone. | |

**User's choice:** Full schema + components rewrite (Recommended)
**Notes:** Most impactful doc — AI assistants read it first.

### Q3: CLAUDE.md depth

| Option | Description | Selected |
|--------|-------------|----------|
| Update schema + factual sections | Graph Schema section, Schema Change Propagation list, Known Gotchas, Tech Stack Summary. | ✓ |
| Full audit and refresh | Update everything referencing v3 or old component names + Architecture + Service Map. | |
| Schema section only | Just update Graph Schema to v4. | |

**User's choice:** Update schema + factual sections (Recommended)
**Notes:** Architecture overview and Key Design Decisions are still accurate.

### Q4: Verification approach

| Option | Description | Selected |
|--------|-------------|----------|
| SC#3 grep gate + manual review | grep for v3 references + manual review for correct names/labels. | ✓ |
| SC#3 grep gate only | Mechanical, unambiguous. | |
| Grep + manual + ontology audit | Gate + manual + spot-check against DesignGrammar-V7.owl for IRI accuracy. | |

**User's choice:** SC#3 grep gate + manual review (Recommended)
**Notes:** grep catches mechanical errors, manual review catches semantic ones.

---

## DG_OBSIDIAN & Graphify Refresh

### Q1: Stale note handling

| Option | Description | Selected |
|--------|-------------|----------|
| Annotate in-place as superseded | Add frontmatter + banner. Notes remain searchable. | |
| Archive stale notes | Move to DG_OBSIDIAN/archive/. Clean vault. Link from index. | ✓ |
| Delete dead, update outdated | Delete CLASSIFICATOR/VALIDATION RUNS notes. Update renamed references. | |

**User's choice:** Archive stale notes
**Notes:** Clean separation between current and historical. Archive linked from index.

### Q2: Graphify regeneration

| Option | Description | Selected |
|--------|-------------|----------|
| Full regeneration via refresh script | `scripts/refresh_graphify.sh` — picks up all Phase 13-19 changes. | ✓ |
| Incremental graphify update | `graphify update` — faster but may leave stale community structures. | |
| Full regen + verification audit | Full regeneration + verify no stale community notes survive. | |

**User's choice:** Full regeneration via refresh script (Recommended)
**Notes:** Clean regeneration ensures no stale references survive.

### Q3: Vault housekeeping

| Option | Description | Selected |
|--------|-------------|----------|
| Update index + session note + priorities | Update index.md, create Phase 20 session note, update priorities for milestone completion. | ✓ |
| Schema note + archive only | Just update atlas note + archive component notes. | |
| Substantive updates, skip ceremony | Archive notes, update schema, regenerate graphify. No session notes. | |

**User's choice:** Update index + session note + priorities (Recommended)
**Notes:** Follow the session protocol in CLAUDE.md for consistency.

---

## Claude's Discretion

- Exact E2E checklist steps and checkpoint format
- Exact release notes wording, section structure, and ASCII diagram content
- Which specific DG_OBSIDIAN notes get archived vs updated in-place
- README.md and spec/DATABASE.md update specifics
- Session note title and structure
- Whether to create a combined Docker-side E2E test script or inline curl commands
- Exact grep patterns for SC#3 verification gate
- Order of operations: E2E first (may surface bugs) → docs → release notes → DG_OBSIDIAN last

## Deferred Ideas

None — discussion stayed within phase scope.
