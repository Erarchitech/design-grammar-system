# -*- coding: utf-8 -*-
"""MCP tool modules (DeGram read-only fork).

Each module in this package defines ``register_<name>_tools(mcp, ...)`` and
pairs with a route module in ``revit_mcp/``. Only modules that host at least one
allowlisted tool are listed in ``_MODULES``; the other upstream modules stay on
disk but are never imported. Registration additionally goes through
``ReadOnlyToolRegistry``, so a mixed module can only ever register names in
``degram_readonly.ALLOWED_TOOLS`` (phase 1301 D-10).
"""

import json
from importlib import import_module

import degram_readonly

# (module, registration function, HTTP helpers it takes after `mcp`)
_ALL = ("get", "post", "image")
_MODULES = (
    ("status_tools", "register_status_tools", ("get",)),
    ("view_tools", "register_view_tools", _ALL),
    ("model_tools", "register_model_tools", ("get",)),
    ("colors_tools", "register_colors_tools", ("get", "post")),
    ("parameter_tools", "register_parameter_tools", _ALL),
    ("degram_tools", "register_degram_tools", ("get", "post")),
)


def structured_helper(helper):
    """Wrap a client helper so error outcomes reach the tool layer as JSON text.

    ``format_response`` passes strings through unchanged, so a structured
    outcome (``status == "error"`` plus a ``code``) is serialized once, here,
    instead of being reworded into an ``Error:`` paragraph. It lives here and
    not in ``degram_readonly`` because that module is also loaded by the
    IronPython ``startup.py``, which cannot parse ``async def``.
    """

    async def wrapper(*args, **kwargs):
        result = await helper(*args, **kwargs)
        if degram_readonly.is_outcome(result):
            return json.dumps(result, ensure_ascii=False)
        return result

    return wrapper


def register_tools(mcp_server, revit_get, revit_post, revit_image):
    """Register the allowlisted tools with ``mcp_server``."""
    guarded = degram_readonly.ReadOnlyToolRegistry(mcp_server)
    helpers = {
        "get": structured_helper(revit_get),
        "post": structured_helper(revit_post),
        "image": revit_image,
    }
    for module_name, func_name, needs in _MODULES:
        register = getattr(import_module("." + module_name, __name__), func_name)
        register(guarded, *(helpers[n] for n in needs))
