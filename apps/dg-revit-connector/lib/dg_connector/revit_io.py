# -*- coding: utf-8 -*-
"""Revit API side of the DG connector: read, colour, clear, write and show.

This is the only library module that talks to Revit. It runs inside Revit under
IronPython 3.4 (``from pyrevit import DB``) and produces plain dicts, so the
pure modules (``descriptors``, ``loop``, ``palette``) stay testable without
Revit and this module stays as thin as possible.

Contents (D-47, D-48, D-50, D-51, contract sections 8.1-8.4):

``collect_scope``
    The mapping scope: the selection when it is not empty, else the model
    element instances visible in the active view (no annotations, views, types
    or view-specific elements), capped at 5000. Returns ``(elements, total)``,
    so the caller can report how many were left unread.
``element_row``
    One Revit element -> one plain dict, the row contract of
    :mod:`dg_connector.descriptors` (UniqueId, element id, category, family,
    type, instance and type parameter rows, adaptive placement-point count).
``read_rows``
    Many elements -> ``(rows, skipped)``. A bad parameter is skipped and
    counted; a bad element never aborts the read.
``apply_colours`` / ``clear_colours``
    Solid-fill graphic overrides in one view by mapping state, in the
    Grasshopper palette. One Revit transaction each ("DG mapping colours" /
    "DG mapping colours (clear)"), so each is one undo step.
``write_parameters``
    Binds the shared instance text parameters ``DG_Class`` and
    ``DG_MappingState`` from the shipped shared-parameter file to the
    categories of the mapped elements and sets their values, in one transaction
    ("DG mapping parameters").
``show_elements``
    Selects the given UniqueIds and zooms the active view to them.
``palette_overridden_ids``
    UniqueIds of the elements a view shows in a DG palette colour: what
    "clear colours" removes when the session cannot be read from DG.

Nothing here raises for one bad element or one bad parameter: the caller gets
counts, because a mapping read must survive a model with a broken family.

Python 3.4 syntax (IronPython 3.4 under Revit).
"""

import logging

from pyrevit import DB

from . import palette

logger = logging.getLogger(__name__)

#: Shared instance text parameters the connector writes (contract section 8.4).
DG_CLASS_PARAMETER = "DG_Class"
DG_STATE_PARAMETER = "DG_MappingState"

#: Group of the shared definitions inside ``DG_SharedParameters.txt``.
SHARED_PARAMETER_GROUP = "DG"

#: Transaction names: one undo step per write (D-50).
COLOURS_TRANSACTION = "DG mapping colours"
CLEAR_TRANSACTION = "DG mapping colours (clear)"
PARAMETERS_TRANSACTION = "DG mapping parameters"

#: The connector reads at most this many elements per session (contract section 2).
MAX_ELEMENTS = 5000

#: State written to ``DG_MappingState`` when the session carries none.
UNMAPPED_STATE = "unmapped"


# --- small helpers ------------------------------------------------------------

def _text(value):
    """Unicode-safe text; None becomes an empty string."""
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def _norm_path(path):
    return _text(path).replace("/", "\\").lower()


def element_id_value(element_or_id):
    """Integer value of an Element, an ElementId or a category id.

    Revit 2024 exposes ``ElementId.Value`` (64 bit); older versions expose
    ``ElementId.IntegerValue``. Both are read here, never assumed.
    """
    if element_or_id is None:
        raise ValueError("cannot read the value of an empty element id")
    target = getattr(element_or_id, "Id", element_or_id)
    try:
        return int(target.Value)
    except (AttributeError, TypeError, ValueError):
        return int(target.IntegerValue)


def element_id(value):
    """A Revit ``ElementId`` for an integer value (2024+ System.Int64 first)."""
    try:
        import System
        return DB.ElementId(System.Int64(int(value)))
    except Exception:
        return DB.ElementId(int(value))


def _element_id_list(element_ids):
    """``System.Collections.Generic.List[DB.ElementId]`` for the Selection API."""
    try:
        from System.Collections.Generic import List
        net_list = List[DB.ElementId]()
        for item in element_ids:
            net_list.Add(item)
        return net_list
    except Exception:  # CPython without Revit (tests): a plain list is enough
        return list(element_ids)


def _unit_label(parameter):
    """Display label of the parameter unit, or "" when it has none (Revit 2022+)."""
    try:
        unit_id = parameter.GetUnitTypeId()
    except Exception:
        return ""
    if unit_id is None:
        return ""
    try:
        return _text(DB.LabelUtils.GetLabelForUnit(unit_id))
    except Exception:
        try:
            return _text(unit_id.TypeId)
        except Exception:
            return ""


def _raw_value(parameter, storage):
    """Raw value by storage type: text, number or integer."""
    if storage == "String":
        value = parameter.AsString()
        return None if value is None else _text(value)
    if storage == "Integer":
        return int(parameter.AsInteger())
    if storage == "Double":
        return float(parameter.AsDouble())  # Revit internal units (feet), see unit
    if storage == "ElementId":
        return element_id_value(parameter.AsElementId())
    return None


def _parameter_row(parameter):
    """Instance parameter row, the revit-mcp ``selection_snapshot`` shape.

    Ported from ``dg_revit_mcp/documents.py`` ``_parameter_row`` so a snapshot
    route and the DG read agree on the shape.
    """
    storage = _text(parameter.StorageType)
    row = {
        "name": _text(parameter.Definition.Name),
        "storageType": storage,
        "unit": _unit_label(parameter) if storage == "Double" else "",
        "displayValue": "",
        "value": None,
    }
    if not parameter.HasValue:
        return row
    try:
        if storage == "String":
            row["displayValue"] = _text(parameter.AsString())
        else:
            row["displayValue"] = _text(parameter.AsValueString())
    except Exception:
        row["displayValue"] = ""
    try:
        row["value"] = _raw_value(parameter, storage)
    except Exception:
        row["value"] = None
    return row


def _type_parameter_row(parameter):
    """Type parameter row: only the name and the display value."""
    try:
        value = parameter.AsValueString()
    except Exception:
        value = None
    return {"name": _text(parameter.Definition.Name), "value": _text(value)}


def _ordered_parameters(element):
    try:
        return list(element.GetOrderedParameters())
    except Exception:
        return []


def _parameter_rows(element):
    """(row list, number of parameters that could not be read)."""
    rows = []
    skipped = 0
    seen = set()
    for parameter in _ordered_parameters(element):
        try:
            name = _text(parameter.Definition.Name)
            if not name or name in seen:
                continue
            seen.add(name)
            rows.append(_parameter_row(parameter))
        except Exception:
            skipped += 1
    return rows, skipped


def _type_parameter_rows(type_element):
    rows = []
    seen = set()
    if type_element is None:
        return rows
    for parameter in _ordered_parameters(type_element):
        try:
            name = _text(parameter.Definition.Name)
            if not name or name in seen:
                continue
            seen.add(name)
            rows.append(_type_parameter_row(parameter))
        except Exception:
            continue
    return rows


# --- reading ------------------------------------------------------------------

def _type_element(doc, element):
    try:
        type_id = element.GetTypeId()
    except Exception:
        return None
    if type_id is None:
        return None
    try:
        if type_id == DB.ElementId.InvalidElementId:
            return None
    except Exception:
        pass
    try:
        return doc.GetElement(type_id)
    except Exception:
        return None


def _type_name(doc, element, type_element):
    if type_element is not None:
        try:
            return _text(type_element.Name)
        except AttributeError:
            try:
                return _text(DB.Element.Name.__get__(type_element))
            except Exception:
                return ""
        except Exception:
            return ""
    try:
        return _text(element.Name)
    except Exception:
        return ""


def _category_name(element):
    try:
        category = element.Category
        if category is None:
            return ""
        return _text(category.Name)
    except Exception:
        return ""


def _family_name(element, type_element):
    """``FamilyInstance.Symbol.Family.Name``, else the type's ``FamilyName``."""
    try:
        symbol = element.Symbol
    except Exception:
        symbol = None
    if symbol is not None:
        try:
            family = symbol.Family
            if family is not None:
                return _text(family.Name)
        except Exception:
            pass
    if type_element is not None:
        try:
            return _text(type_element.FamilyName)
        except Exception:
            return ""
    return ""


def _adaptive_point_count(element):
    """Placement points of an adaptive component instance, else None."""
    try:
        utility = DB.AdaptiveComponentInstanceUtils
        is_adaptive = utility.IsAdaptiveComponentInstance(element)
        if is_adaptive is not True:  # a .NET bool, or a test double: only True counts
            return None
        references = utility.GetInstancePlacementPointElementRefIds(element)
        count = len(list(references))
        return count if count > 0 else None
    except Exception:
        return None


def element_row(doc, element):
    """One Revit element -> one element row dict, or None when it is unreadable.

    The row follows the contract in the :mod:`dg_connector.descriptors`
    docstring. A single bad parameter is skipped and counted in
    ``skippedParameters``; it never aborts the row.
    """
    if element is None:
        return None
    try:
        unique_id = _text(element.UniqueId)
    except Exception:
        return None
    if not unique_id:
        return None
    type_element = _type_element(doc, element)
    parameters, skipped = _parameter_rows(element)
    row = {
        "uniqueId": unique_id,
        "elementId": None,
        "category": _category_name(element),
        "family": _family_name(element, type_element),
        "typeName": _type_name(doc, element, type_element),
        "parameters": parameters,
        "typeParameters": _type_parameter_rows(type_element),
        "adaptivePointCount": _adaptive_point_count(element),
        "skippedParameters": skipped,
    }
    try:
        row["elementId"] = element_id_value(element)
    except Exception:
        row["elementId"] = None
    return row


def read_rows(doc, elements):
    """Element rows for ``elements`` -> ``(rows, skipped elements)``.

    An element whose row cannot be built is skipped and counted, so one broken
    family never aborts the whole mapping read.
    """
    rows = []
    skipped = 0
    for element in elements or []:
        try:
            row = element_row(doc, element)
        except Exception as error:
            logger.warning("DG: reading an element failed: %s", _text(error))
            row = None
        if row is None:
            skipped += 1
            continue
        rows.append(row)
    return rows, skipped


def _selection_element_ids(uidoc):
    if uidoc is None:
        return []
    try:
        return list(uidoc.Selection.GetElementIds())
    except Exception:
        return []


def _is_model_element(element):
    """True for a model-category element that is not view-specific."""
    try:
        category = element.Category
        if category is None:
            return False
        if category.CategoryType != DB.CategoryType.Model:
            return False
    except Exception:
        return False
    try:
        if element.ViewSpecific:
            return False
    except Exception:
        pass  # no ViewSpecific property: keep the element
    return True


def collect_scope(doc, uidoc, max_elements=MAX_ELEMENTS):
    """The mapping scope -> ``(elements, total)``.

    The selection when it is not empty (every selected element, in selection
    order), otherwise the model element instances visible in the active view:
    ``FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()``
    with a ``CategoryType.Model`` category that is not view-specific.

    ``elements`` holds at most ``max_elements`` (default and cap 5000);
    ``total`` is how many were in scope, so ``total - len(elements)`` is the
    truncation the caller reports.
    """
    try:
        limit = int(max_elements)
    except (TypeError, ValueError):
        limit = MAX_ELEMENTS
    if limit <= 0:
        limit = MAX_ELEMENTS

    selection = _selection_element_ids(uidoc)
    if selection:
        elements = []
        for selected_id in selection:
            try:
                element = doc.GetElement(selected_id)
            except Exception:
                element = None
            if element is not None:
                elements.append(element)
        return elements[:limit], len(elements)

    try:
        view = doc.ActiveView
    except Exception:
        view = None
    if view is None or doc is None:
        return [], 0

    elements = []
    total = 0
    try:
        collector = DB.FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
        for element in collector:
            if not _is_model_element(element):
                continue
            total += 1
            if len(elements) < limit:
                elements.append(element)
    except Exception as error:
        logger.warning("DG: collecting the active view failed: %s", _text(error))
    return elements, total


# --- colours ------------------------------------------------------------------

def _solid_fill_pattern_id(doc):
    """ElementId of the document's solid fill pattern, or None."""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
        for pattern_element in collector:
            try:
                if pattern_element.GetFillPattern().IsSolidFill:
                    return pattern_element.Id
            except Exception:
                continue
    except Exception:
        return None
    return None


def override_settings(colour, solid_fill_id):
    """Solid-fill :class:`DB.OverrideGraphicSettings` for an RGB tuple."""
    settings = DB.OverrideGraphicSettings()
    revit_colour = DB.Color(int(colour[0]), int(colour[1]), int(colour[2]))
    if solid_fill_id is not None:
        try:
            settings.SetSurfaceForegroundPatternId(solid_fill_id)
            settings.SetCutForegroundPatternId(solid_fill_id)
        except Exception:
            pass
    settings.SetSurfaceForegroundPatternColor(revit_colour)
    settings.SetCutForegroundPatternColor(revit_colour)
    settings.SetProjectionLineColor(revit_colour)
    return settings


class _QuietFailures(DB.IFailuresPreprocessor):
    """Never let a Revit failure open a modal dialog during a DG transaction.

    Warnings are deleted (the write proceeds); an error rolls the transaction
    back. A modal dialog would otherwise block a Routes request or the
    ExternalEvent queue until somebody clicks it (same policy as
    ``dg_revit_mcp/utils.suppress_warnings``).
    """

    def PreprocessFailures(self, failures_accessor):
        try:
            failures_accessor.DeleteAllWarnings()
            for failure in failures_accessor.GetFailureMessages():
                if failure.GetSeverity() == DB.FailureSeverity.Error:
                    return DB.FailureProcessingResult.ProceedWithRollBack
        except Exception:
            pass
        return DB.FailureProcessingResult.Continue


def _start(doc, name):
    """A started transaction ``name`` that never shows a failure dialog."""
    transaction = DB.Transaction(doc, name)
    transaction.Start()
    try:
        options = transaction.GetFailureHandlingOptions()
        options.SetForcedModalHandling(False)
        options.SetClearAfterRollback(True)
        options.SetFailuresPreprocessor(_QuietFailures())
        transaction.SetFailureHandlingOptions(options)
    except Exception:
        pass  # best effort: the write itself does not depend on it
    return transaction


def _roll_back(transaction):
    try:
        if transaction.GetStatus() == DB.TransactionStatus.Started:
            transaction.RollBack()
            return
    except Exception:
        pass
    try:
        transaction.RollBack()
    except Exception:
        pass


def apply_colours(doc, view, states_by_uid):
    """Solid-fill overrides by mapping state in ``view`` -> number coloured.

    One transaction "DG mapping colours". Per-element failures (a deleted
    element, a locked view) are logged and counted, never raised.
    """
    if doc is None or view is None:
        return 0
    states = states_by_uid if isinstance(states_by_uid, dict) else {}
    if not states:
        return 0
    solid_fill_id = _solid_fill_pattern_id(doc)
    transaction = _start(doc, COLOURS_TRANSACTION)
    coloured = 0
    try:
        for unique_id in list(states.keys()):
            try:
                element = doc.GetElement(_text(unique_id))
                if element is None:
                    continue
                settings = override_settings(palette.colour_for(states.get(unique_id)),
                                             solid_fill_id)
                view.SetElementOverrides(element.Id, settings)
                coloured += 1
            except Exception as error:
                logger.warning("DG: colouring %s failed: %s", _text(unique_id), _text(error))
        transaction.Commit()
    except Exception:
        _roll_back(transaction)
        raise
    return coloured


def clear_colours(doc, view, unique_ids):
    """Remove the overrides of ``unique_ids`` in ``view`` -> number cleared.

    One transaction "DG mapping colours (clear)" with an empty
    ``OverrideGraphicSettings`` per element.
    """
    if doc is None or view is None:
        return 0
    ids = list(unique_ids or [])
    if not ids:
        return 0
    transaction = _start(doc, CLEAR_TRANSACTION)
    cleared = 0
    try:
        for unique_id in ids:
            try:
                element = doc.GetElement(_text(unique_id))
                if element is None:
                    continue
                view.SetElementOverrides(element.Id, DB.OverrideGraphicSettings())
                cleared += 1
            except Exception as error:
                logger.warning("DG: clearing %s failed: %s", _text(unique_id), _text(error))
        transaction.Commit()
    except Exception:
        _roll_back(transaction)
        raise
    return cleared


def palette_overridden_ids(doc, view):
    """UniqueIds of the elements ``view`` shows in a DG palette colour.

    The fallback of "clear colours" when the session's element list cannot be
    read from DG (signed out, token expired, DG down): an element whose surface
    foreground colour override is exactly one of the
    :data:`dg_connector.palette.STATE_COLOURS` was painted by the connector.
    Unreadable elements are skipped.
    """
    if doc is None or view is None:
        return []
    colours = set(tuple(colour) for colour in palette.STATE_COLOURS.values())
    found = []
    try:
        collector = DB.FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
        for element in collector:
            try:
                colour = view.GetElementOverrides(element.Id).SurfaceForegroundPatternColor
                if colour is None or not colour.IsValid:
                    continue
                rgb = (int(colour.Red), int(colour.Green), int(colour.Blue))
                if rgb in colours:
                    found.append(_text(element.UniqueId))
            except Exception:
                continue
    except Exception as error:
        logger.warning("DG: scanning the view for mapping colours failed: %s", _text(error))
    return found


# --- shared parameters --------------------------------------------------------

def _restore_shared_parameter_file(application, previous):
    """Put the user's shared-parameter file back (``""`` when there was none)."""
    target = "" if previous is None else previous
    try:
        application.SharedParametersFilename = target
    except Exception:
        try:
            application.SharedParametersFilename = ""
        except Exception:
            pass


def shared_definitions(app, shared_file):
    """``{name: ExternalDefinition}`` of the DG group, or raise.

    ``app.SharedParametersFilename`` is switched to ``shared_file`` only for the
    duration of the lookup and restored in ``finally``, so the user's own
    shared-parameter file is never left changed.
    """
    try:
        previous = app.SharedParametersFilename
    except Exception:
        previous = None
    try:
        app.SharedParametersFilename = shared_file
        definition_file = app.OpenSharedParameterFile()
        if definition_file is None:
            raise RuntimeError("Revit opened no shared-parameter file at {!r}".format(shared_file))
        group = _shared_group(definition_file)
        if group is None:
            raise RuntimeError("the shared-parameter group {!r} is missing".format(
                SHARED_PARAMETER_GROUP))
        definitions = {}
        for name in (DG_CLASS_PARAMETER, DG_STATE_PARAMETER):
            definition = _shared_definition(group, name)
            if definition is None:
                raise RuntimeError("the shared parameter {!r} is missing".format(name))
            definitions[name] = definition
        return definitions
    finally:
        _restore_shared_parameter_file(app, previous)


def _shared_group(definition_file):
    try:
        groups = definition_file.Groups
        if groups is None:
            return None
        try:
            return groups.get_Item(SHARED_PARAMETER_GROUP)
        except Exception:
            pass
        for group in groups:
            try:
                if _text(group.Name) == SHARED_PARAMETER_GROUP:
                    return group
            except Exception:
                continue
    except Exception:
        return None
    return None


def _shared_definition(group, name):
    try:
        definitions = group.Definitions
        if definitions is None:
            return None
        try:
            return definitions.get_Item(name)
        except Exception:
            pass
        for definition in definitions:
            try:
                if _text(definition.Name) == name:
                    return definition
            except Exception:
                continue
    except Exception:
        return None
    return None


def _bound_categories(doc, name):
    """``Category`` objects the parameter ``name`` is bound to, or None if unbound.

    The categories are taken from the binding itself: a Category is not an
    Element, so it cannot be recovered from its id with ``doc.GetElement``.
    """
    try:
        iterator = doc.ParameterBindings.ForwardIterator()
        iterator.Reset()
        while iterator.MoveNext():
            try:
                key_name = _text(iterator.Key.Name)
            except Exception:
                continue
            if key_name != name:
                continue
            found = []
            try:
                for category in iterator.Current.Categories:
                    if category is not None:
                        found.append(category)
            except Exception:
                pass
            return found
    except Exception:
        return None
    return None


def _category_key(category):
    try:
        return element_id_value(category.Id)
    except Exception:
        return _text(getattr(category, "Name", ""))


def _category_set(app, categories):
    category_set = app.Create.NewCategorySet()
    for category in categories:
        try:
            category_set.Insert(category)
        except Exception:
            continue
    return category_set


def bind_definition(doc, app, definition, categories):
    """Bind ``definition`` as an instance parameter to ``categories`` -> bool.

    An unbound parameter is inserted (group Data). An already bound parameter
    is re-inserted with the union of its current and the new categories, so a
    later session over new categories widens the binding and never drops a
    category (and with it the values) that was bound before. When every
    category is already bound nothing is changed.
    """
    name = _text(definition.Name)
    wanted = [category for category in categories if category is not None]
    existing = _bound_categories(doc, name)
    if existing is None:
        if not wanted:
            return False
        binding = app.Create.NewInstanceBinding(_category_set(app, wanted))
        try:
            return bool(doc.ParameterBindings.Insert(definition, binding, DB.GroupTypeId.Data))
        except Exception as error:
            logger.warning("DG: binding %s failed: %s", name, _text(error))
            return False
    known = set(_category_key(category) for category in existing)
    added = [category for category in wanted if _category_key(category) not in known]
    if not added:
        return True  # already bound to every category it needs
    union = list(existing) + added
    try:
        return bool(doc.ParameterBindings.ReInsert(
            definition, app.Create.NewInstanceBinding(_category_set(app, union)),
            DB.GroupTypeId.Data))
    except Exception as error:
        logger.warning("DG: re-binding %s failed: %s", name, _text(error))
        return False


def _writable_categories(doc, unique_ids):
    """Categories of the given elements that allow bound parameters."""
    categories = []
    seen = set()
    for unique_id in unique_ids:
        try:
            element = doc.GetElement(_text(unique_id))
        except Exception:
            element = None
        if element is None:
            continue
        try:
            category = element.Category
        except Exception:
            category = None
        if category is None:
            continue
        try:
            if not category.AllowsBoundParameters:
                continue
        except Exception:
            continue
        try:
            key = element_id_value(category.Id)
        except Exception:
            key = _text(category.Id)
        if key in seen:
            continue
        seen.add(key)
        categories.append(category)
    return categories


def _set_text_parameter(element, name, value):
    parameter = None
    try:
        parameter = element.LookupParameter(name)
    except Exception:
        parameter = None
    if parameter is None:
        return False
    try:
        return bool(parameter.Set(_text(value)))
    except Exception:
        return False


def write_parameters(doc, app, shared_file, roles_by_uid, states_by_uid):
    """Write ``DG_Class`` / ``DG_MappingState`` -> ``{written, skipped, categories}``.

    The shared definitions are read from ``shared_file`` (the shipped
    ``DG_SharedParameters.txt``): ``app.SharedParametersFilename`` is switched
    for the lookup and restored in ``finally``. Both parameters are bound as
    instance parameters to the categories of the mapped elements that allow
    bound parameters, then set in one transaction "DG mapping parameters".

    ``DG_Class`` is the class labels joined by ``";"`` (empty when the element
    has none); ``DG_MappingState`` is the element's mapping state.
    """
    roles = roles_by_uid if isinstance(roles_by_uid, dict) else {}
    states = states_by_uid if isinstance(states_by_uid, dict) else {}
    result = {"written": 0, "skipped": 0, "categories": 0}
    if doc is None or app is None or not shared_file:
        raise ValueError("writing DG parameters needs a document, the application "
                         "and the shared-parameter file")

    unique_ids = []
    for unique_id in list(states.keys()) + list(roles.keys()):
        text = _text(unique_id).strip()
        if text and text not in unique_ids:
            unique_ids.append(text)

    definitions = shared_definitions(app, shared_file)  # external: may raise
    categories = _writable_categories(doc, unique_ids)

    transaction = _start(doc, PARAMETERS_TRANSACTION)
    try:
        bound = 0
        for name in (DG_CLASS_PARAMETER, DG_STATE_PARAMETER):
            try:
                if bind_definition(doc, app, definitions[name], categories):
                    bound += 1
            except Exception as error:
                logger.warning("DG: binding %s failed: %s", name, _text(error))
        try:
            doc.Regenerate()  # make a new binding visible to LookupParameter
        except Exception:
            pass
        result["categories"] = len(categories)
        for unique_id in unique_ids:
            element = None
            try:
                element = doc.GetElement(unique_id)
            except Exception:
                element = None
            if element is None:
                result["skipped"] += 1
                continue
            labels = roles.get(unique_id) or []
            class_text = ";".join([_text(label) for label in labels if _text(label).strip()])
            state_text = _text(states.get(unique_id)).strip() or UNMAPPED_STATE
            wrote_class = _set_text_parameter(element, DG_CLASS_PARAMETER, class_text)
            wrote_state = _set_text_parameter(element, DG_STATE_PARAMETER, state_text)
            if wrote_class and wrote_state:
                result["written"] += 1
            else:
                result["skipped"] += 1
        transaction.Commit()
    except Exception:
        _roll_back(transaction)
        raise
    if bound == 0:
        logger.warning("DG: neither %s nor %s could be bound", DG_CLASS_PARAMETER,
                       DG_STATE_PARAMETER)
    return result


# --- showing elements ---------------------------------------------------------

def show_elements(uidoc, doc, unique_ids):
    """Select the given UniqueIds and zoom the active view -> ``{found, shown, missing}``.

    UniqueIds that are not in the model are reported in ``missing`` instead of
    failing the call (D-51).
    """
    result = {"found": 0, "shown": 0, "missing": []}
    ids = []
    for value in unique_ids or []:
        unique_id = _text(value).strip()
        if not unique_id:
            continue
        element = None
        if doc is not None:
            try:
                element = doc.GetElement(unique_id)
            except Exception:
                element = None
        if element is None:
            result["missing"].append(unique_id)
            continue
        ids.append(element.Id)
    result["found"] = len(ids)
    if not ids or uidoc is None:
        return result
    element_ids = _element_id_list(ids)
    try:
        uidoc.Selection.SetElementIds(element_ids)
    except Exception as error:
        logger.warning("DG: selecting the elements failed: %s", _text(error))
        return result
    try:
        uidoc.ShowElements(element_ids)
    except Exception as error:
        logger.warning("DG: zooming to the elements failed: %s", _text(error))
        return result
    result["shown"] = len(ids)
    return result
