---
phase: 1303-pravilo-gh-obekt
plan: "04"
status: complete
completed: 2026-10-17
requirements: [DGMAP-01, DGMAP-04]
executor: "wave-1 subagent wrote tools/mapping/revit_read.py before stopping on a weekly rate limit; the controller reviewed it, wrote fixtures, tests, README and this summary"
---

# 1303-04 Summary — read-only Revit adapter

## What was built

- `tools/mapping/revit_read.py` (standard library): `RevitReadClient` for exactly four read routes (`status/`, `list_open_documents/`, `selection_snapshot/`, `element_properties/<id>`), each checked by `check_route` (path + method) before the request is built; loopback-only base URL, no proxy, redirects refused, per-call timeout, one request at a time (pyRevit shares one ExternalEvent handler), POST JSON as `text/plain; charset=utf-8`; structured revit-mcp errors mapped to `RevitReadError` codes with owner hints (BRIDGE_OFF, BUSY, IDENTITY_MISMATCH, …).
- Conversion `snapshot_to_descriptors`: uniqueId → nativeId, category, typeName → type, family from `element_properties` (or a Unicode-safe snapshot parameter when the properties text is ASCII-folded), instance + type parameters, length doubles in metres (`<name>_m`), IFC export parameters in EN/RU → `ifc.entity` / `ifc.predefinedType`, `_nonAscii` marker; per-element property failures are recorded, never fatal, and a properties response for a different element is rejected.
- CLI writes the `POST /mapping/sessions` upload body `{project, platform:"revit", label, source:{document, creationGuid, readAt, truncation}, elements}`; `--dry-run-fixture` converts saved responses offline. No DG URL, no credentials.
- Synthetic fixtures (8 Generic Models in 4 families, one EN and one RU IFC parameter) in the exact revit-mcp shapes; 14 offline tests; README.

## Verification

- `python -m unittest discover -s tools/mapping/tests -v` → **14 tests OK**.
- Dry run on the fixtures wrote an 8-element upload body; feeding it to `mapping_engine.compute` gave 4 disambiguate questions grouped by family (end-to-end contract check).
- `grep` of write route names in `revit_read.py`: they appear only in docstrings/comments; the refusal test covers set_parameter, color_splash, modify_element, delete_elements, export_ifc.

## Open issues

- Live Revit read not exercised (plan 06). The real family/type names of the RiR-generated model are unknown; the authored vocabulary for act 3 is written in plan 06 from the first read.
- `element_properties` replaces non-ASCII characters with "?"; Russian family names fall back to the snapshot `Family` parameter when present.
