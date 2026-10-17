# tools/mapping — read-only Revit reader for DG mapping

`revit_read.py` reads the elements the owner **selected** in Revit and writes an upload file for DG mapping (Phase 1303 MVP slice, plan 04). It is the Revit side of act 3 of the hexagonal-facade demo.

## What it reads

Only four read routes of the revit-mcp pyRevit extension on loopback (`http://127.0.0.1:48884/revit_mcp/`): `status/`, `list_open_documents/`, `selection_snapshot/` (pinned to the active document by `creationGuid`/`pathName`, up to 1000 elements and 200 instance parameters each) and `element_properties/<id>` (family, type and type parameters). Every request is checked against `ALLOWED_PATHS` before it is built; any other route (`set_parameter/`, `color_splash/`, `export_ifc/`, …) is refused before network activity. The base URL must be loopback, redirects are never followed, every call has a timeout.

The script never writes to Revit, never contacts DG and never reads, stores or sends credentials.

Revit has no read route that lists all elements or returns adaptive-point counts, so: select the facade elements first. The descriptors carry category, family, type, instance and type parameters (length doubles also in metres as `<name>_m`) and the IFC export parameter when present (`IfcExportAs` / `Export to IFC As` / `Экспорт в IFC как`).

## Owner steps

1. Open the facade model in Revit 2024 with pyRevit Routes and the revit-mcp extension loaded.
2. Select the facade modules and panels (≤ 1000 elements).
3. Run `python tools/mapping/revit_read.py --out <file.json> --label act3-revit-read1` from the repository root.
4. In the DG Web UI: Projects → `v12-hexagonal-facade-01` → Mapping → Import descriptors (JSON) → pick the file.

Options: `--no-properties` (skip `element_properties`, no family names), `--timeout 120` (large selections, slow Revit), `--dry-run-fixture <snapshot.json> [--properties-fixture <props.json>]` (offline conversion of saved responses).

Exit codes: 0 written, 1 Revit/IO error (with a hint), 3 empty selection.

## Tests

`python -m unittest discover -s tools/mapping/tests -v` — offline, with a stub opener and synthetic fixtures in the exact revit-mcp response shapes (`tests/fixtures/*.json`, marked `_note: SYNTHETIC`).
