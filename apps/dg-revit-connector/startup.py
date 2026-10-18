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

On top of the routes, the DG connector is armed here: the poll thread of the
mapping apply loop and the one ``ExternalEvent`` that runs its Revit writes
(``lib/dg_connector/runner.py``). A failure there is logged and never breaks
route registration.
"""

import importlib
import logging
import os
import sys

from pyrevit import routes

import dg_transport

#: pyRevit Routes API name of this extension.
API_NAME = "dg_revit"

#: Directory of this extension (the folder holding this file).
EXTENSION_DIR = os.path.dirname(os.path.abspath(__file__))

#: The extension's pure connector library (``lib/dg_connector``).
LIB_DIR = os.path.join(EXTENSION_DIR, "lib")

# pyRevit puts <extension>/lib on sys.path for ribbon button scripts, but the
# startup engine is not guaranteed to see it, so it is inserted before
# dg_connector is imported (D-47).
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

logger = logging.getLogger(__name__)

try:
    # The pure connector library plus the Revit-side runner of the apply loop.
    # A broken library must not take every Revit route down with it, so the
    # failure is logged and the connector commands are simply not armed.
    import dg_connector  # noqa: F401 - importing it proves lib/ is on sys.path
    from dg_connector import runner as dg_runner
except Exception as dg_import_error:
    dg_connector = None
    dg_runner = None
    logger.error("dg_connector (lib/) failed to import: %s", str(dg_import_error))

#: (module under dg_revit_mcp, register function) - every upstream route module
#: at Demolinator/revit-mcp-server merge base 74a8ddc, in registration order,
#: plus the fork's identity-pinned document read routes and the DG connector
#: routes of the Design Grammars mapping session.
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
    ("dg_connector_routes", "register_dg_connector_routes"),
)

#: The DG connector route module: a broken import of *this* module is reported
#: as a warning and tolerated, because the Revit routes still make sense without
#: the mapping session (the four DG tools then answer EXTENSION_NOT_LOADED).
DG_CONNECTOR_MODULE = "dg_connector_routes"

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
    for module_name, function_name in ROUTE_MODULES:
        try:
            module = importlib.import_module("dg_revit_mcp." + module_name)
        except ImportError as import_error:
            if module_name == DG_CONNECTOR_MODULE:
                logger.warning(
                    "dg_revit_mcp.%s failed to import, DG connector routes NOT "
                    "registered: %s", DG_CONNECTOR_MODULE, str(import_error))
                continue
            logger.error("Failed to register DG Revit routes: %s", str(import_error))
            raise
        try:
            getattr(module, function_name)(api)
        except Exception as e:
            logger.error("Failed to register DG Revit routes: %s", str(e))
            raise
        registered.append((module_name, function_name))

    logger.info("Registered %d route modules under the Routes API %r",
                len(registered), API_NAME)
    return registered


# Register the routes when the extension loads
register_routes()

# Arm the DG connector: one ExternalEvent and one daemon poll thread per Revit
# process (runner.install is idempotent). A failure here must never break route
# registration, so it is only logged.
if dg_runner is not None:
    try:
        dg_runner.install(__revit__, EXTENSION_DIR)
    except Exception as install_error:
        logger.error("DG connector runner install failed: %s", str(install_error))
