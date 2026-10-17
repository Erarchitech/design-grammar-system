---
phase: 1303-pravilo-gh-obekt
plan: "05"
status: complete
completed: 2026-10-17
requirements: [DGMAP-02, DGMAP-03, DGMAP-06]
executor: "wave-1 subagent wrote mappingApi.js, MappingPanel.jsx, the error codes and the tests before stopping on a weekly rate limit; the controller reviewed them, mounted the panel, added the RU dictionary and the i18n manifest entries, and wrote this summary"
---

# 1303-05 Summary — Mapping panel in the DG Web UI

## What was built

- `ui-v2/src/lib/mappingApi.js` — `apiFetch` wrappers for the seven `/data-service/mapping/*` routes (`listSessions`, `getSession`, `createSession`, `postDecision`, `applySession`, `listProfiles`, `createProfile`); project in the query for GET and in the body for POST (a body `project` from an imported file is replaced by the active project).
- `ui-v2/src/screens/MappingPanel.jsx` — collapsed «Меппинг / Mapping» panel under the project settings of the Projects screen; loads only when opened and while the screen is active. Sections: session selector and «Import descriptors (JSON)» (validates JSON, element list, unique nativeIds, platform, 5000 limit; warns when the file names another project), five-segment progress (confirmed / auto by profile / suggested / ambiguous / unmapped) with local CSS colour tokens and dark variants, question cards (RU/EN canonical text by UI language, groups with representatives, candidates with confidence and evidence, consequences table, option buttons; batch-assign with a group checklist), profiles table, «Apply mapping» with per-class counts, aria-live notices.
- `ProjectsScreen.jsx` mounts exactly one `<MappingPanel key={project} project={project} active={active} />`; its own initial requests are unchanged.
- i18n: 85 new keys with Russian in `src/i18n/dict/screens.js` (4 plural tables with EN `one/other` and RU `one/few/many`), `MAPPING_*` error codes in both halves of `errors.js`, the two new files listed in `tests/i18n-swept/projects.json`.
- Tests: `ui-v2/tests/mapping-api.test.mjs` (URLs, methods, CSRF, bodies, error codes, mount and loading rules, palette) and seven new cases in `api-security.test.mjs`.

## Verification

- `node --test ui-v2/tests/*.test.mjs` → **322 / 322 pass** (before the controller's completion: 319 pass, 3 fail — RU entries, manifest, mount).
- `npm --prefix ui-v2 run build` → built (the existing chunk-size warning only).

## Decisions

- No nginx change: the generic `/data-service/` location keeps the 1 MB request limit (nginx.conf ships in the 1309 hosting bundle and its proxy locations are pinned by `test_static_proxy_boundary.py`). The Revit reader keeps uploads small instead (`--max-parameters`, default 40, plus a size warning); the Grasshopper script talks to `:8000` directly.

## Open issues

- Not yet seen in a browser; the manual `*.browser.jsx` runners were not executed. Live check in plan 06.
