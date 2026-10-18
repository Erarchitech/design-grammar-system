# Phase 1303: Правило ↔ GH ↔ объект — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-18
**Phase:** 1303-pravilo-gh-obekt (MVP slice, Revit discussion for plan 1303-11)
**Areas discussed:** Revit launch, GH → Revit transfer, Revit click in DeGram, live verification, the DG revit-mcp fork, connector sign-in, DeGram adapter, Revit writes, read scope, session trigger, gold roles, test model

Earlier rounds (D-01..D-43) were recorded in the CONTEXT amendments of 2026-10-17/18; this log covers the Revit round only.

Facts shown before the questions:
- the five cross-platform GH profiles select on `geometry.vertexCount` only, and Revit descriptors carry no geometry;
- the populations of `ms-56907a90d11f` are BTP 250, GP 125, GFU 26, HU 100, Facade 1, so a 125-group of triangles would get «GlassPanel»;
- the LLM proposal is keyed by GH streams and is never asked for Revit;
- Revit sessions have `document = null`, so DeGram filters them out;
- `POST /mapping/sessions` is connector + member only.

---

## Revit launch

| Option | Description | Selected |
|--------|-------------|----------|
| DeGram + Web UI import (Recommended) | DeGram «Запустить меппинг» reads the selection and creates the session with the delegated token (route policy change); `revit_read.py` import stays as a fallback | ✓ (with an amendment) |
| Web UI import only | No boundary change | |
| DeGram only | Import removed for Revit | |

**User's choice:** option 1, «но нужно разрешить запись и редактирование параметров и создание и удаление элементов в revit. сними все ограничения.»
**Notes:** Mid-turn: «сделай самостоятельный форк revit-mcp для коннектора — то есть у Design Grammars будет свой форк revit mcp». This led to D-44, D-45 and to the follow-up questions below.

## GH → Revit transfer

| Option | Description | Selected |
|--------|-------------|----------|
| LLM + group population (Recommended) | One LLM call per Revit session with the applied GH session as context; profiles by family/type | |
| New read route: adaptive points | `geometry.vertexCount` from Revit, so GH `*` profiles apply directly | ✓ |
| Both | | |
| Deterministic only | Names, parameters, IFC, population, owner vocabulary | |

**User's choice:** adaptive points (D-49). The population fix is kept as a correction of the false hint.

## Revit click in DeGram

| Option | Description | Selected |
|--------|-------------|----------|
| Not clickable (Recommended) | Revit stays read-only | |
| Copy ElementId | Clipboard only | |
| Show in Revit (select + zoom) | A Revit UI write; needs an explicit owner decision | ✓ |

**User's choice:** show in Revit (D-51).

## Live verification under the demo cold start

| Option | Description | Selected |
|--------|-------------|----------|
| Live read, then retire (Recommended) | Revit-learned profiles retired after the test; GH transfer proven by an offline recompute | ✓ |
| Keep Revit profiles | | |
| After the demo only | | |

**User's choice:** live read, then retire (D-52). Claude added that `*` vertex-count profiles reactivated by a Revit answer are retired too.

## Where the DG fork lives

| Option | Description | Selected |
|--------|-------------|----------|
| Inside the DG repository (Recommended) | `apps/dg-revit-connector/`, plain files, no new GitHub repository, no push | ✓ |
| New GitHub repository | Public repo + submodule; publication needs authorization | |
| Separate local repository | `D:\dgb\dg-revit-connector`, decided after the demo | |

**User's choice:** inside the DG repository (D-44).

## How the Revit connector works with DG

| Option | Description | Selected |
|--------|-------------|----------|
| Like CONNECTOR in GH (Recommended) | Sign-in → `dgk_` (connector `revit`); the connector creates and applies sessions; DeGram starts it by command | ✓ |
| No DG sign-in | DeGram creates sessions with the delegated token (route policy change) | |

**User's choice:** like CONNECTOR (D-47).

## DeGram's Revit adapter

| Option | Description | Selected |
|--------|-------------|----------|
| DeGram moves to the DG fork (Recommended) | All tools including writes | ✓ |
| DeGram stays on the read-only fork | Only the connector writes | |

**User's choice:** DeGram moves to the DG fork (D-46).

## What the connector writes after mapping (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Colours by mapping state in the view | Temporary graphic overrides, cleared by command | ✓ |
| Shared parameters `DG_Class` / `DG_MappingState` | Visible in schedules and IFC | ✓ |
| Nothing automatically | | |

**User's choice:** both (D-50).

## Read scope

| Option | Description | Selected |
|--------|-------------|----------|
| Selection, else all in the active view (Recommended) | | ✓ |
| Whole model | | |
| Selection only | | |

**User's choice:** selection, else the active view (D-48).

## Session trigger

| Option | Description | Selected |
|--------|-------------|----------|
| On command (Recommended) | Ribbon button or DeGram; connector applies after the last answer | ✓ |
| Automatic like GH | On every model change | |

**User's choice:** on command (D-48).

## Gold roles for hexagonal modules

| Option | Description | Selected |
|--------|-------------|----------|
| HexagonalUnit only, as in GH (Recommended) | | ✓ |
| HexagonalUnit + FacadeModule | | |
| FacadeModule for all modules | | |

**User's choice:** HexagonalUnit only (D-52).

## Test model

| Option | Description | Selected |
|--------|-------------|----------|
| Copy of the facade model (Recommended) | `…-dg-mapping.rvt`, not in git | ✓ |
| Original | | |

**User's choice:** copy (D-52).

## Claude's Discretion

- Transport hygiene stays as is: loopback-only Routes and DG URLs; stdio-only MCP in DeGram (D-45).
- The connector installs beside the existing `revit-mcp.extension` under its own Routes API name (D-44).
- Colour refresh moments, the polling mechanism for apply, and the shared-parameter file layout.
- The plan split by committing repository (D-53).

## Deferred Ideas

- LLM vote for Revit family groups.
- Automatic Revit sessions on `DocumentChanged`.
- A separate GitHub repository for the connector.
- What happens to the read-only `apps/revit-mcp` submodule at the merge.
- View filters and legends.
