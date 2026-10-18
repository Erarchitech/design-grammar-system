# -*- coding: UTF-8 -*-
"""
DG Revit connector - pyRevit extension startup.

Design Grammars' own fork of revit-mcp. The owner lifted every Revit
restriction on 2026-10-18 (D-45), so this extension registers every upstream
route, writes included: parameters, element creation and deletion, colour and
graphic overrides, selection, view operations and code execution.

The only gate left is transport hygiene: nothing is registered unless the
pyRevit Routes host is loopback, so the write routes cannot be reached from
another machine.

Routes are served under the pyRevit Routes API name ``dg_revit``, beside the
still-installed ``revit_mcp`` extension of the upstream project.
"""

from pyrevit import routes
import importlib
import logging

import dg_transport

logger = logging.getLogger(__name__)

#: pyRevit Routes API name of this extension.
API_NAME = "dg_revit"

#: (module under dg_revit_mcp, register function) - every upstream route module
#: at Demolinator/revit-mcp-server merge base 74a8ddc, in registration order,
#: plus the fork's identity-pinned document read routes.
ROUTE_MODULES = (
    ("status", "register_status_routes"),
    ("model_info", "register_model_info_routes"),
    ("views", "register_views_routes"),
    ("placement", "register_placement_routes"),
    ("colors", "register_color_routes"),
    ("code_execution", "register_code_execution_routes"),
    ("building", "register_building_routes"),
    ("editing", "register_editing_routes"),
    ("structure", "register_structure_routes"),
    ("annotation", "register_annotation_routes"),
    ("analysis", "register_analysis_routes"),
    ("documentation", "register_documentation_routes"),
    ("rooms", "register_room_routes"),
    ("view_management", "register_view_management_routes"),
    ("tags", "register_tag_routes"),
    ("transforms", "register_transform_routes"),
    ("mep", "register_mep_routes"),
    ("parameters", "register_parameter_routes"),
    ("interop", "register_interop_routes"),
    ("detail", "register_detail_routes"),
    ("clash", "register_clash_routes"),
    ("document", "register_document_routes"),
    ("documents", "register_document_read_routes"),
)

#: DG connector routes. Written by a later task, so their absence is not an
#: error: the extension then serves every Revit route and the MCP tools that
#: depend on these four routes answer EXTENSION_NOT_LOADED until it lands.
DG_CONNECTOR_MODULE = "dg_connector_routes"
DG_CONNECTOR_FUNCTION = "register_dg_connector_routes"

# Initialize the main API
api = routes.API(API_NAME)


def register_routes():
    """Register every DG Revit connector route; register nothing off loopback.

    Returns the list of (module, register function) pairs that were registered.
    """
    host = dg_transport.configured_routes_host()
    if not dg_transport.is_loopback_host(host):
        logger.error(
            "dg_revit routes NOT registered: pyRevit Routes host %r is not "
            "loopback (set host = 127.0.0.1 in the [routes] section of "
            "pyRevit_config.ini and restart Revit)", host)
        return []

    registered = []
    try:
        for module_name, function_name in ROUTE_MODULES:
            module = importlib.import_module("dg_revit_mcp." + module_name)
            getattr(module, function_name)(api)
            registered.append((module_name, function_name))
    except Exception as e:
        logger.error("Failed to register DG Revit routes: %s", str(e))
        raise

    try:
        connector = importlib.import_module("dg_revit_mcp." + DG_CONNECTOR_MODULE)
    except ImportError:
        logger.info(
            "dg_revit_mcp.%s is not installed; DG connector routes not registered",
            DG_CONNECTOR_MODULE)
    else:
        getattr(connector, DG_CONNECTOR_FUNCTION)(api)
        registered.append((DG_CONNECTOR_MODULE, DG_CONNECTOR_FUNCTION))

    logger.info("Registered %d route modules under the Routes API %r",
                len(registered), API_NAME)
    return registered


# Register the routes when the extension loads
register_routes()
