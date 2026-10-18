# -*- coding: UTF-8 -*-
"""
Revit MCP Extension Startup (DeGram read-only fork)

Registers only the allowlisted read routes (degram_readonly.ALLOWED_ROUTES) and
only when the pyRevit Routes host is loopback. Execute-code, save, create,
modify, delete, transform, tag, color, link, load and export routes are never
registered, so they do not exist on the wire (phase 1301 D-10, D-23).
"""

from pyrevit import routes
import importlib
import logging

import degram_readonly

logger = logging.getLogger(__name__)

# Initialize the main API
api = routes.API("revit_mcp")


def register_routes():
    """Register the allowlisted read routes; register nothing off loopback.

    Returns the list of (method, pattern) pairs that were registered.
    """
    host = degram_readonly.configured_routes_host()
    if not degram_readonly.is_loopback_host(host):
        logger.error(
            "revit_mcp routes NOT registered: pyRevit Routes host %r is not "
            "loopback (set host = 127.0.0.1 in the [routes] section of "
            "pyRevit_config.ini and restart Revit)", host)
        return []

    guard = degram_readonly.ReadOnlyApi(api)
    try:
        for module_name, function_name in degram_readonly.ALLOWED_ROUTE_MODULES:
            module = importlib.import_module("revit_mcp." + module_name)
            getattr(module, function_name)(guard)
    except Exception as e:
        logger.error("Failed to register MCP routes: %s", str(e))
        raise

    missing = degram_readonly.ALLOWED_ROUTES - set(guard.registered)
    if missing:
        logger.warning("Allowlisted routes not registered: %s", sorted(missing))
    logger.info("Registered %d read routes; dropped %d non-allowlisted route declarations",
                len(guard.registered), len(guard.dropped))
    return list(guard.registered)


# Register the read routes when the extension loads
register_routes()
