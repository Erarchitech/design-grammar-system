# -*- coding: utf-8 -*-
"""DeGram document tools: enumerate open documents and read a pinned selection.

Both tools return JSON text: either the route payload or a structured outcome
``{"status": "error", "code": ..., "error": ...}`` (never a free-text "Error:").
"""

import json
from typing import Any, Dict

from .utils import Context

MAX_ELEMENTS_DEFAULT = 200
MAX_PARAMETERS_DEFAULT = 50


def _as_text(result) -> str:
    if isinstance(result, str):
        return result  # already a serialized outcome
    return json.dumps(result, ensure_ascii=False)


def register_degram_tools(mcp, revit_get, revit_post):
    """Register list_open_documents and get_selection_snapshot."""

    @mcp.tool()
    async def list_open_documents(ctx: Context = None) -> str:
        """List every open Revit project document so one can be pinned by identity.

        Skips linked and family documents. Each row has title, pathName (empty
        when the project is unsaved), creationGuid, isActive and isModified.
        Reads never pick a document implicitly; pass a row's creationGuid and
        pathName as ``identity`` to get_selection_snapshot.
        """
        return _as_text(await revit_get("/list_open_documents/", ctx))

    @mcp.tool()
    async def get_selection_snapshot(
        identity: Dict[str, Any],
        max_elements: int = MAX_ELEMENTS_DEFAULT,
        max_parameters: int = MAX_PARAMETERS_DEFAULT,
        ctx: Context = None,
    ) -> str:
        """Read the current selection of the pinned, active Revit document.

        Args:
            identity: ``{"creationGuid": ..., "pathName": ...}`` of the pinned
                document, as returned by list_open_documents. If that document
                is not open the outcome is DOCUMENT_NOT_OPEN; if it is open but
                not the active document (or its path differs) the outcome is
                IDENTITY_MISMATCH. No other document is ever read instead.
            max_elements: Cap on returned elements (default 200).
            max_parameters: Cap on parameters per element (default 50).

        Returns per element: uniqueId, elementId, category, typeName and
        parameters (name, storageType, unit, displayValue, value), plus a
        truncation block that discloses anything cut by the caps.
        """
        body: Dict[str, Any] = {
            "identity": identity,
            "max_elements": max_elements,
            "max_parameters": max_parameters,
        }
        return _as_text(await revit_post("/selection_snapshot/", body, ctx))
