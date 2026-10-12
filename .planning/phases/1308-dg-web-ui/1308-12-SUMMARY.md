---
phase: 1308-dg-web-ui
plan: "12"
subsystem: ui-v2-graph-screen
tags: [i18n, react, graph-viewer, node-test, browser-harness]
requires:
  - phase: 1308-05
    provides: "i18n layer (t, tc, tp, describeError, formatTime, raw-text guard, swept-manifest format)"
provides:
  - "GraphScreen.jsx fully on t()/tc()/tp(), describeError and formatTime; turn state keeps codes and data and is translated at render"
  - "buildRings.orbitFallbackName(o): empty-orbit names (Core/Mid/Outer) as render-time chrome"
  - "graphApi.js relay errors through t()"
  - "dict/graph.js RU dictionary (about 150 keys, 8 plural tables) and tests/i18n-swept/graph.json manifest"
affects: [1308-14, 1308-22]
tech-stack:
  added: []
  patterns:
    - "turn state holds codes (kind, step ids, outcome {type}, metaInfo {type}, warnings [{type}]) and data; modeName/stepLabel/turnResponse/metaText turn them into text at render, so a live language switch re-labels turns already on screen"
    - "module-level t() from i18n/index.js plus a bare useT() call that only subscribes the component to the language"
    - "error objects are kept in state ({err, fb}) and describeError(err, fallback) runs at render"
key-files:
  created:
    - ui-v2/tests/i18n-swept/graph.json
  modified:
    - ui-v2/src/screens/GraphScreen.jsx
    - ui-v2/src/graph/buildRings.js
    - ui-v2/src/lib/graphApi.js
    - ui-v2/src/i18n/dict/graph.js
key-decisions:
  - "plural key is '{n} layer node', not '{n} node': i18n.test.mjs (plan 05) uses '{n} node' as its 'not in the dictionary' probe for plural()"
  - "graphEngine.js needs no edit: it draws only graph data (node label, kind, relationship type). It is still listed in the manifest so the guard covers it"
  - "empty-orbit names: ring.orbits keeps '' for an empty orbit and GraphScreen resolves names with orbitNames(ring) at render, instead of baking translated text into cached ring data"
  - "tab nouns (Загрузка/Запрос/Правка) differ from the action button verbs (Загрузить/Запросить) through tc('action', ...)"
  - "Cypher is allow-listed in the manifest (a language name, not in PROPER_NOUNS, passed as a Collapsible label)"
requirements-completed: []
duration: ~80 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 12: Graph Viewer area i18n Summary

**The Graph Viewer area (screen, ring builder, API messages) runs through the i18n layer with an RU dictionary and a raw-text-guard manifest; the session console re-labels already open turns when the language switches live, and graph data, layer names and LLM answers stay untranslated.**

## What was built

- **Task 1 (a5325de):** every literal in `GraphScreen.jsx` through `t()`/`tc()`/`tp()`: header, load/empty states, restore-point banner, layer and orbit panels, node panels, search popover and bar, session history props, session console, prompt bar, minimap, deletion dialog and conflict dialog. Turn state no longer stores translated text: `kind`, step ids, `outcome`, `metaInfo`, `warnings` and `clockAt` are rendered through `modeName`, `stepLabel`, `turnResponse`, `metaText`, `formatTime` (the browser-locale time call is gone). Load and delete errors keep the error object and render `describeError(err, fallback)`; counts use `tp` (nodes, edges, atoms, matches, rules); durations use `Intl.NumberFormat` (RU gives «0,0 с»). `buildRings.orbitFallbackName` replaces the baked `["Core","Mid","Outer"]`.
- **Task 2 (96f26dc):** `graphApi.js` relay errors (timeout, not found, cancelled, relay invalid, failed without server text) through `t()`; server `data.message` and the `ApiError` `code`/`hint` passthrough are untouched. `graph.json` lists the four files. `graphEngine.js` has no UI literal (it draws node label, kind and relationship type from data), so it is unchanged.

## Verification (real runs)

- `node --test ui-v2/tests/` (= `npm --prefix ui-v2 test`): 274 pass, 0 fail, after each commit; `npm --prefix ui-v2 run build` succeeds.
- Acceptance greps: no `toLocaleTimeString` in `GraphScreen.jsx`; 94 `t("` calls; manifest lists the four files.
- Mutation check run by hand and reverted: replacing `{t("Return to live")}` by raw text made the raw-text guard fail on `graph.json` for `GraphScreen.jsx`.
- Throwaway real-React harness (esbuild bundle of the real `GraphScreen`, headless Chrome, fake fetch, kept in the session scratchpad, not committed): rendered EN and RU, switched the language live four times; layer/orbit panels, filter, tabs, button verb, conflict dialog (2-match plural, long note), ingest turn with a refused supersede warning, and the error turn all re-labelled with no page error. RU time formatted 24 h, EN 12 h. Node check: plural forms for 1/3/5/21, `tc` pairs, `orbitFallbackName` EN/RU.
- Not verified: rendering against the live stack (no `design-grammars` rebuild here), the shared Russian wording by a Russian reader (D-38 glossary is a draft; the prohibition on translating graph content is satisfied structurally, judgment review stays with the RU visual pass), real DeGram `#degram-lang` signal.

## Deviations from Plan

**1. [Rule 3 - Blocking] plural key renamed `{n} layer node`**
- `ui-v2/tests/i18n.test.mjs` (plan 05) asserts `plural("en", "{n} node", 3) === "3 node"` as the not-in-dictionary fallback. Defining `{n} node` in the graph dictionary broke it, so the key is `{n} layer node`; the English tables still read «1 node / 2 nodes».

**2. [Process] No separate RED tests**
- The plan names the guard as the test; it was run, and a mutation check was done instead of a new failing-first test. No `test(...)` commit exists.

**3. [Process] Task 1 commit holds the Task 2 dictionary split**
- To keep each commit green, the five graphApi dictionary keys and the manifest entries for the other three files were held back from Task 1 and committed in Task 2.

No other deviations.

## Limitations

- Persisted history rows carry the response text in the language that was active when the turn was saved (the old English «Rule ingested into the metagraph.» shows as is in RU). It is stored data; it is not re-translated.
- `graphApi.js` error messages are fixed at throw time in the language of that moment, as the plan specifies (the `ApiError` code mapping is the live path).
- Shared primitives still show their own English defaults on this screen (SessionHistory «Session History / Restore / Reuse / Prompt / Result / Time / Show more», PropertiesTable «Value / Edit value», Combobox «Show all values», ScreenHeader «← Back», Collapsible/Progress internals). They belong to plans 1308-14 and 1308-22; the harness shows «Session History (1)» still English.
- `GraphScreen` still displays the stale `bolt://neo4j:7687` fallback in the header subtitle (pre-existing, not UI text).

## Known Stubs

None.

## Threat Flags

None. T-1308-12-01: all text goes through React text nodes and canvas `fillText`, interpolation is plain replacement, no HTML injection API was added. T-1308-12-02: node labels, property values, `Rule_Id`, SWRL, Cypher, layer names and LLM/server answers are rendered as data and never pass through `t()`.

## Self-Check: PASSED

- Files exist: `ui-v2/src/i18n/dict/graph.js`, `ui-v2/tests/i18n-swept/graph.json`, `ui-v2/src/screens/GraphScreen.jsx`, `ui-v2/src/graph/buildRings.js`, `ui-v2/src/lib/graphApi.js`.
- Commits exist: a5325de, 96f26dc.
