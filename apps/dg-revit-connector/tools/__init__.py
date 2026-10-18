# -*- coding: utf-8 -*-
"""MCP tool modules (DG Revit connector).

Each module in this package defines ``register_<name>_tools(mcp, ...)`` and
pairs with a route module in ``dg_revit_mcp/``. ``_MODULES`` lists every
upstream module plus the DG ones, so the MCP server exposes the same surface as
the extension: the owner lifted every Revit restriction on 2026-10-18 (D-45),
and there is no read-only registry guard any more.
"""

import json
from importlib import import_module

import dg_transport

# (module, registration function, HTTP helpers it takes after `mcp`)
_ALL = ("get", "post", "image")
_READ_WRITE = ("get", "post")
_MODULES = (
    ("status_tools", "register_status_tools", ("get",)),
    ("view_tools", "register_view_tools", _ALL),
    ("family_tools", "register_family_tools", _READ_WRITE),
    ("model_tools", "register_model_tools", ("get",)),
    ("colors_tools", "register_colors_tools", _READ_WRITE),
    ("code_execution_tools", "register_code_execution_tools", _ALL),
    ("building_tools", "register_building_tools", _ALL),
    ("editing_tools", "register_editing_tools", _ALL),
    ("structure_tools", "register_structure_tools", _ALL),
    ("annotation_tools", "register_annotation_tools", _ALL),
    ("analysis_tools", "register_analysis_tools", _ALL),
    ("documentation_tools", "register_documentation_tools", _ALL),
    ("room_tools", "register_room_tools", _ALL),
    ("view_management_tools", "register_view_management_tools", _ALL),
    ("tag_tools", "register_tag_tools", _ALL),
    ("transform_tools", "register_transform_tools", _ALL),
    ("mep_tools", "register_mep_tools", _ALL),
    ("parameter_tools", "register_parameter_tools", _ALL),
    ("interop_tools", "register_interop_tools", _ALL),
    ("detail_tools", "register_detail_tools", _ALL),
    ("clash_tools", "register_clash_tools", _ALL),
    ("document_tools", "register_document_tools", _ALL),
    ("degram_tools", "register_degram_tools", _READ_WRITE),
    ("dg_connector_tools", "register_dg_connector_tools", _READ_WRITE),
)


def structured_helper(helper):
    """Wrap a client helper so error outcomes reach the tool layer as JSON text.

    ``format_response`` passes strings through unchanged, so a structured
    outcome (``status == "error"`` plus a ``code``) is serialized once, here,
    instead of being reworded into an ``Error:`` paragraph. It lives here and
    not in ``dg_transport`` because that module is also loaded by the
    IronPython ``startup.py``, which cannot parse ``async def``.
    """

    async def wrapper(*args, **kwargs):
        result = await helper(*args, **kwargs)
        if dg_transport.is_outcome(result):
            return json.dumps(result, ensure_ascii=False)
        return result

    return wrapper


def register_tools(mcp_server, revit_get, revit_post, revit_image):
    """Register every DG Revit connector tool with ``mcp_server``."""
    helpers = {
        "get": structured_helper(revit_get),
        "post": structured_helper(revit_post),
        "image": revit_image,
    }
    for module_name, func_name, needs in _MODULES:
        register = getattr(import_module("." + module_name, __name__), func_name)
        register(mcp_server, *(helpers[n] for n in needs))
