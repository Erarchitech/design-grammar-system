# API Coverage — Phase 1301

> Full coverage by default. Opt-outs are explicit, reasoned decisions. Detector (plan + roadmap scope, 2026-10-04): `detected: true` — signals on revit-mcp (MCP), DG/Speckle endpoints and provider settings. Three external surfaces are integrated in this phase; each matrix below starts from full coverage.

## Revit MCP server (Demolinator/revit-mcp-server @ 74a8ddca, fork Erarchitech) — plans 07, 11

Read-only by owner decision D-10/D-22/D-23; write capabilities return in 1306 through a separate typed allowlist, not by restoring this set.

## Speckle server (existing self-hosted stack) — plan 09

Read-only geometry for Model Viewer through the DG proxy (D-21).

## System model endpoint `genpro` / `mimo-v2.5-pro` (OpenAI-compatible) — plans 08, 16

Single operator-managed pair (1300 D-05/D-09), user-invisible.

## Matrix

| capability | decision | reason |
|---|---|---|
| revit-mcp: get_revit_status | INTEGRATE | |
| revit-mcp: get_revit_model_info | INTEGRATE | |
| revit-mcp: get_current_view_info | INTEGRATE | |
| revit-mcp: list_levels | INTEGRATE | |
| revit-mcp: list_category_parameters | INTEGRATE | |
| revit-mcp: get_element_properties | INTEGRATE | |
| revit-mcp: list_open_documents | INTEGRATE | new in fork — document enumeration for D-13 |
| revit-mcp: get_selection_snapshot | INTEGRATE | new in fork — identity-pinned selection + parameters for D-14 |
| revit-mcp: get_selected_elements | OPT-OUT | superseded by identity-pinned get_selection_snapshot (D-13: active-document read could hit the wrong document) |
| revit-mcp: list_revit_views | OPT-OUT | not needed yet — 1301 snapshot is selection + parameters (D-14) |
| revit-mcp: get_current_view_elements | OPT-OUT | not needed yet — whole-view export exceeds the D-14 selection scope |
| revit-mcp: list_families | OPT-OUT | not needed yet — no family workflow in 1301 |
| revit-mcp: list_family_categories | OPT-OUT | not needed yet — no family workflow in 1301 |
| revit-mcp: ai_element_filter | OPT-OUT | not needed yet — server-side filtering outside D-14 selection snapshot |
| revit-mcp: export_room_data | OPT-OUT | not needed yet — room schedules are not part of the 1301 snapshot |
| revit-mcp: get_material_quantities | OPT-OUT | not needed yet — quantities are measurement scope of later phases |
| revit-mcp: analyze_model_statistics | OPT-OUT | not needed yet — whole-model statistics exceed the selection scope |
| revit-mcp: check_clashes | OPT-OUT | not needed yet — analysis feature, not a 1301 read snapshot |
| revit-mcp: get_revit_view | OPT-OUT | writes an export image to %TEMP% (file side effect) — excluded by read-only rule D-10 |
| revit-mcp: execute_revit_code | OPT-OUT | arbitrary code execution — explicitly out of scope (1300 exclusions, D-10) |
| revit-mcp: save_document | OPT-OUT | document write — explicitly out of scope (D-10) |
| revit-mcp: place_family | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: load_family | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_line_based_element | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_surface_based_element | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_level | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_grid | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_structural_framing | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_dimensions | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: tag_walls | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: tag_elements | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_sheet | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_schedule | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_room | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_room_separation | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_view | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_duct | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_pipe | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_mep_system | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: create_detail_line | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: delete_elements | OPT-OUT | model write — explicitly out of scope (G-08: no deletion) |
| revit-mcp: modify_element | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: transform_elements | OPT-OUT | model write — 1306 typed allowlist only |
| revit-mcp: set_parameter | OPT-OUT | model write — 1306 typed allowlist only (G-08 parameter writes) |
| revit-mcp: color_splash | OPT-OUT | view/model state change — out of read-only scope |
| revit-mcp: clear_colors | OPT-OUT | view/model state change — out of read-only scope |
| revit-mcp: set_active_view | OPT-OUT | UI state change — out of read-only scope |
| revit-mcp: export_document | OPT-OUT | file write — out of read-only scope |
| revit-mcp: export_ifc | OPT-OUT | file write — out of read-only scope |
| revit-mcp: link_file | OPT-OUT | model write — out of read-only scope |
| speckle: object fetch GET /objects/{projectId}/{objectId} | INTEGRATE | |
| speckle: batch object fetch POST /api/getobjects/{projectId} | INTEGRATE | |
| speckle: model/version resource resolution (GraphQL read) | INTEGRATE | server-side only |
| speckle: object upload / version create (write) | OPT-OUT | viewer is read-only; publishing stays in the existing data-service validation publish path |
| speckle: GraphQL mutations (projects, models, comments, webhooks) | OPT-OUT | explicitly out of scope — no Speckle administration from DeGram |
| speckle: user/token management | OPT-OUT | explicitly out of scope — the token never leaves the server (D-21) |
| genpro: chat completions | INTEGRATE | |
| genpro: streaming (SSE) | INTEGRATE | |
| genpro: tool/function calling and tool_choice | INTEGRATE | multi-turn tool history support probed live in plan 16 (MiMo issue #44) |
| genpro: reasoning_content passthrough | INTEGRATE | relayed verbatim; never synthesized |
| genpro: usage and served-model reporting | INTEGRATE | provenance (requested vs served), null when absent |
| genpro: request cancellation | INTEGRATE | client disconnect closes upstream |
| genpro: model listing / model selection | OPT-OUT | explicitly out of scope — no user selector (DGCL-02, D-05) |
| genpro: Anthropic-protocol endpoint | OPT-OUT | not needed — one OpenAI-compatible path; no second protocol |
| genpro: embeddings, audio, image, files, batch endpoints | OPT-OUT | not needed yet — no feature in 1301 consumes them |
| genpro: provider fallback / alternate model | OPT-OUT | explicitly out of scope — no automatic fallback (1300 D-05, D-16) |
