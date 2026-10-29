# -*- coding: utf-8 -*-
"""DG connector tools: the Design Grammars mapping session inside Revit.

The four tools here map one-to-one onto the DG connector routes that the
``dg_revit`` Routes API serves (``dg_revit_mcp/dg_connector_routes.py``):

* ``dg_mapping_status``       -> GET  ``/mapping_status/``
* ``dg_start_mapping``        -> POST ``/start_mapping/``
* ``dg_show_elements``        -> POST ``/show_elements/``
* ``dg_clear_mapping_colours``-> POST ``/clear_colours/``

Every tool returns JSON text: either the route payload or a structured outcome
``{"status": "error", "code": ..., "error": ...}`` (never a free-text
``Error:`` string). Argument checks happen here, before any HTTP call, so an
invalid request never reaches Revit.
"""

import json
from typing import List

import dg_transport
from .utils import Context

#: The Revit connector reads at most this many elements per mapping session
#: (selection, else the model instances visible in the active view; D-48).
MAX_ELEMENTS = 5000


def _as_text(result) -> str:
    if isinstance(result, str):
        return result  # already a serialized outcome
    return json.dumps(result, ensure_ascii=False)


def _bad_request(message, **extra) -> str:
    """Serialize a BAD_REQUEST outcome without calling Revit."""
    return json.dumps(dg_transport.error_outcome("BAD_REQUEST", message, **extra),
                      ensure_ascii=False)


def register_dg_connector_tools(mcp, revit_get, revit_post):
    """Register the four DG connector tools."""

    @mcp.tool()
    async def dg_mapping_status(ctx: Context = None) -> str:
        """Read the state of the Design Grammars mapping session of open Revit.

        Returns whether a connector session is signed in, whether a mapping
        session is open, its sessionId, label, document key and view, how many
        elements it holds, the answer/apply progress, and the last message.
        Use it before dg_start_mapping to see whether a session already exists,
        and after an apply or an answer to follow the connector.

        The connector colours elements by mapping state in the active view
        (orange ambiguous, yellow suggested, green confirmed, blue auto by
        profile), so a session's progress is visible in the model as well.
        """
        return _as_text(await revit_get("/mapping_status/", ctx))

    @mcp.tool()
    async def dg_start_mapping(ctx: Context = None) -> str:
        """Start a Design Grammars mapping session for the active Revit model.

        The connector reads the scope, sends it to DG as ElementDescriptors and
        keeps the returned session open: the selection when it is not empty,
        otherwise every model element instance visible in the active view
        (annotations, views and types excluded), at most 5000 elements. It then
        colours those elements by mapping state in the active view.

        The session is created on command only, never on a document change.
        Requires a signed-in connector session (POST /auth/login then
        /auth/connector-session with connector_id "revit"); without one the
        outcome is BAD_REQUEST / SETUP_INCOMPLETE. There is at most one open
        session at a time: starting a new one replaces it.

        A started result also carries ``scope`` ("selection" when only the
        selected elements were read, else "view") and ``read`` (elements sent),
        so the caller can say when a leftover selection narrowed the read.
        """
        return _as_text(await revit_post("/start_mapping/", {}, ctx))

    @mcp.tool()
    async def dg_show_elements(unique_ids: List[str], ctx: Context = None) -> str:
        """Select the given Revit elements and zoom the active view to them.

        Args:
            unique_ids: Revit UniqueId strings, as carried by mapping-session
                rows (``nativeId`` of a Revit descriptor). The list must not be
                empty and must not exceed 5000 ids; otherwise the outcome is
                BAD_REQUEST and Revit is not called.

        The elements are selected in the active document
        (Selection.SetElementIds) and shown (UIDocument.ShowElements). Ids that
        are not in the model are reported in the result instead of failing the
        whole call. Reads nothing and changes no element or parameter; the
        active view is only zoomed.
        """
        if not isinstance(unique_ids, (list, tuple)):
            return _bad_request("unique_ids must be a list of Revit UniqueId strings",
                                field="unique_ids")
        ids = []
        for value in unique_ids:
            text = "" if value is None else str(value).strip()
            if text:
                ids.append(text)
        if not ids:
            return _bad_request(
                "unique_ids is empty; pass at least one Revit UniqueId (the selection "
                "else the visible model instances are the mapping scope)",
                field="unique_ids", count=0)
        if len(ids) > MAX_ELEMENTS:
            return _bad_request(
                "unique_ids has {} ids, more than the {}-element limit of one Revit "
                "mapping session".format(len(ids), MAX_ELEMENTS),
                field="unique_ids", count=len(ids), maxElements=MAX_ELEMENTS)
        return _as_text(await revit_post("/show_elements/", {"uniqueIds": ids}, ctx))

    @mcp.tool()
    async def dg_clear_mapping_colours(ctx: Context = None) -> str:
        """Remove the DG mapping colours from the active view in Revit.

        Clears the graphic overrides the connector wrote for the mapping states
        (confirmed, auto by profile, suggested, ambiguous) so the model shows
        its own materials again. It does not close the mapping session, delete
        it, or touch the DG_Class / DG_MappingState parameters: call
        dg_mapping_status to see whether a session is still open.
        """
        return _as_text(await revit_post("/clear_colours/", {}, ctx))
