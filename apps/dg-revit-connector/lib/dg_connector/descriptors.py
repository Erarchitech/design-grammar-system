# -*- coding: utf-8 -*-
"""Revit element rows -> mapping ElementDescriptors (contract section 1 and 8.1).

The Revit reader (``revit_io.element_row`` of a later task) turns a Revit
element into exactly one plain dict, the *element row*::

    {
        "uniqueId": "5f3c...-0001b00",   # Element.UniqueId -> mapping nativeId
        "elementId": 100101,             # ElementId.IntegerValue (diagnostics only)
        "category": "Generic Models",    # Element.Category.Name, "" when absent
        "family": "Facade_Module_Hex",   # FamilyInstance.Symbol.Family.Name, "" if not a family instance
        "typeName": "Hex",               # ElementType.Name / FamilySymbol.Name
        "parameters": [                  # INSTANCE parameter rows, revit-mcp
            {                            # selection_snapshot shape
                "name": "Offset from Host",
                "storageType": "Double",  # or String / Integer / ElementId / ...
                "unit": "Millimeters",    # unit label, None for unitless types
                "displayValue": "304.8 mm",
                "value": 1.0,             # raw internal value (feet for lengths)
            },
            ...
        ],
        "typeParameters": [              # TYPE parameter rows, revit-mcp
            {"name": "Type Mark", "value": "H"},
            ...
        ],
        "adaptivePointCount": 6,         # placement points of an adaptive
                                         # component instance, None otherwise
    }

``parameters`` rows have the same shape as the revit-mcp ``selection_snapshot``
instance rows; ``typeParameters`` rows have the same shape as
``element_properties`` parameters. The conversion rules are ported exactly from
``tools/mapping/revit_read.py``:

* the display value wins (``displayValue``), the raw value is the fallback;
* the first parameter of a given name wins, order is preserved;
* a ``Double`` parameter whose unit is a length gets a second entry
  ``<name>_m`` in metres (Revit's internal length value is always feet);
* type parameters are added only when the instance has no parameter of that
  name and the name carries no ``?`` (element_properties replaces non-ASCII
  characters with ``?``);
* IFC export parameters (English and Russian UI names) produce ``ifc``;
* when the family name is missing or carries a ``?``, the family is recovered
  from the ``Family`` / ``Family and Type`` instance parameter;
* any ``?`` in the category, family or type sets the ``_nonAscii`` marker.

On top of the port, ``geometry.vertexCount`` is added only when
``adaptivePointCount`` is a positive integer. ``widthM`` / ``heightM`` /
``planarityDeviationM`` are deliberately never produced, so the Grasshopper
range rules are never fed Revit bounding boxes (D-48).

Standard library only; Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""
from __future__ import unicode_literals

import math
import re

try:
    _UNICODE_TYPE = unicode
    _TEXT_TYPES = (basestring,)
except NameError:
    _UNICODE_TYPE = str
    _TEXT_TYPES = (str,)

#: Value of the descriptor's ``platform`` field; nativeId is the Revit UniqueId.
PLATFORM = "revit"

#: Default and maximum number of descriptors one session may carry (contract
#: section 2: MAPPING_TOO_MANY_ELEMENTS above 5000).
MAX_ELEMENTS = 5000

FEET_TO_METRES = 0.3048

#: IFC export parameter names (English and Russian UI) ->
#: ifc.entity / ifc.predefinedType.
IFC_ENTITY_PARAMETERS = ("IfcExportAs", "Export to IFC As", "Экспорт в IFC как", "Экспортировать в IFC как")
IFC_PREDEFINED_TYPE_PARAMETERS = ("IfcExportType", "Export Type to IFC As", "Тип экспорта в IFC")
_IFC_ENTITY_KEYS = frozenset(name.lower() for name in IFC_ENTITY_PARAMETERS)
_IFC_PREDEFINED_KEYS = frozenset(name.lower() for name in IFC_PREDEFINED_TYPE_PARAMETERS)

#: Instance parameters that may carry a Unicode-safe family name (the Revit
#: reader cannot report a non-ASCII family name unescaped in every route).
FAMILY_PARAMETERS = ("Family", "Семейство")
FAMILY_AND_TYPE_PARAMETERS = ("Family and Type", "Семейство и типоразмер")

#: Marks a descriptor whose category/family/type was reported with "?".
NON_ASCII_MARKER = "_nonAscii"

# Unit labels (LabelUtils.GetLabelForUnit, or a ForgeTypeId string as fallback).
_NOT_LENGTH_MARKERS = (
    "square", "cubic", "квадрат", "кубич", "radian", "degree", "радиан", "градус",
    "second", "секунд", "minute", "hour", " per ", "/", "newton", "ньютон", "kip",
    "pound", "фунт", "watt", "ватт", "pascal", "паскал",
)
_LENGTH_MARKERS = (
    "millimet", "centimet", "decimet", "meter", "metre", "feet", "foot", "inch",
    "миллиметр", "сантиметр", "дециметр", "метр", "фут", "дюйм",
)
_LENGTH_TOKENS = frozenset(["mm", "cm", "dm", "m", "ft", "in", "мм", "см", "дм", "м"])


# --- small helpers ------------------------------------------------------------

def _text(value):
    """Preserve IronPython 2 Unicode parameter names and values."""
    if value is None:
        return u""
    if isinstance(value, _UNICODE_TYPE):
        return value
    if isinstance(value, _TEXT_TYPES):
        try:
            return value.decode("utf-8", "replace")
        except Exception:
            pass
    try:
        return _UNICODE_TYPE(value)
    except Exception:
        return _UNICODE_TYPE(str(value), "utf-8", "replace")


def _is_number(value):
    """True for finite numeric values, including IronPython 2.7 numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return not math.isinf(value) and not math.isnan(value)
    except (TypeError, ValueError):
        return False


def _positive_int(value):
    """``value`` when it is a positive int (bool excluded), else None."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


# --- conversion rules (ported from tools/mapping/revit_read.py) ---------------

def is_length_unit(label):
    """True when a Double parameter's unit label is a length unit (raw value = feet)."""
    text = " {} ".format(_text(label).strip().lower())
    if not text.strip():
        return False
    if any(marker in text for marker in _NOT_LENGTH_MARKERS):
        return False
    if any(marker in text for marker in _LENGTH_MARKERS):
        return True
    return any(token in _LENGTH_TOKENS for token in re.split(r"[^a-zа-яё]+", text))


def length_in_metres(row):
    """Metres for a parameter row holding a length, else None.

    The raw ``value`` of a Double length parameter is Revit's internal value,
    which is always feet whatever the display unit (``displayValue``/``unit``).
    """
    if _text(row.get("storageType")) != "Double" or not is_length_unit(row.get("unit")):
        return None
    value = row.get("value")
    if not _is_number(value):
        return None
    return round(float(value) * FEET_TO_METRES, 9)


def parameter_value(row):
    """Display value of an instance parameter row, else its raw value, else None."""
    display = row.get("displayValue")
    if isinstance(display, _TEXT_TYPES) and display.strip():
        return display
    value = row.get("value")
    if isinstance(value, _TEXT_TYPES):
        return value if value.strip() else None
    return value if _is_number(value) else None


def _ifc_split(text, entity_parameter):
    head, _, tail = text.partition(".")
    if head[:3].lower() == "ifc":  # "IfcPlate" or "IfcPlate.CURTAIN_PANEL"
        return head.strip(), (tail.strip() or None)
    if entity_parameter:  # e.g. "DontExport"
        return text, None
    return None, text  # a predefined type such as "USERDEFINED"


def ifc_from_parameters(pairs):
    """``{entity, predefinedType}`` from (name, value) pairs in priority order, or None.

    The first non-empty value wins per field. A predefined-type parameter whose
    value names an entity ("Ifc...") is used as an entity hint instead.
    """
    entity = predefined = None
    for name, value in pairs:
        key = _text(name).strip().lower()
        if key in _IFC_ENTITY_KEYS:
            entity_parameter = True
        elif key in _IFC_PREDEFINED_KEYS:
            entity_parameter = False
        else:
            continue
        text = _text(value).strip()
        if not text:
            continue
        found_entity, found_predefined = _ifc_split(text, entity_parameter)
        if entity is None and found_entity:
            entity = found_entity
        if predefined is None and found_predefined:
            predefined = found_predefined
    if entity is None and predefined is None:
        return None
    return {"entity": entity, "predefinedType": predefined}


def family_from_parameters(rows):
    """Unicode-safe family name from instance parameter rows, or ""."""
    for row in rows:
        name = _text(row.get("name")).strip()
        value = _text(row.get("displayValue")).strip()
        if not value:
            continue
        if name in FAMILY_PARAMETERS:
            return value
        if name in FAMILY_AND_TYPE_PARAMETERS and ": " in value:
            return value.split(": ", 1)[0].strip()
    return ""


# family_from_parameters is the ported name of revit_read._family_from_snapshot.
_family_from_snapshot = family_from_parameters


# --- row -> descriptor --------------------------------------------------------

def row_to_descriptor(row):
    """One element row -> ElementDescriptor dict, or None when it has no uniqueId."""
    if not isinstance(row, dict):
        return None
    native_id = _text(row.get("uniqueId")).strip()
    if not native_id:
        return None

    rows = [item for item in (row.get("parameters") or []) if isinstance(item, dict)]
    property_rows = [item for item in (row.get("typeParameters") or []) if isinstance(item, dict)]

    category = _text(row.get("category"))
    family = _text(row.get("family"))
    type_name = _text(row.get("typeName"))
    if not family or "?" in family:
        family = family_from_parameters(rows) or family

    parameters = {}
    for item in rows:
        name = _text(item.get("name")).strip()
        value = parameter_value(item)
        if name and value is not None and name not in parameters:
            parameters[name] = value
    for item in rows:
        metres = length_in_metres(item)
        name = _text(item.get("name")).strip()
        if name and metres is not None:
            parameters.setdefault(name + "_m", metres)
    for item in property_rows:  # type parameters: only when the instance has none
        name = _text(item.get("name")).strip()
        value = _text(item.get("value"))
        if name and "?" not in name and value.strip() and name not in parameters:
            parameters[name] = value

    pairs = [(item.get("name"), parameter_value(item)) for item in rows]
    pairs += [(item.get("name"), item.get("value")) for item in property_rows]
    ifc = ifc_from_parameters(pairs)

    if any("?" in text for text in (category, family, type_name)):
        parameters[NON_ASCII_MARKER] = True

    descriptor = {"nativeId": native_id, "platform": PLATFORM}
    if category:
        descriptor["category"] = category
    if family:
        descriptor["family"] = family
    if type_name:
        descriptor["type"] = type_name
    if family and type_name:
        descriptor["name"] = "{} : {}".format(family, type_name)
    if ifc is not None:
        descriptor["ifc"] = ifc
    point_count = _positive_int(row.get("adaptivePointCount"))
    if point_count is not None:
        descriptor["geometry"] = {"vertexCount": point_count}
    descriptor["parameters"] = parameters
    return descriptor


def rows_to_descriptors(rows, max_elements=MAX_ELEMENTS):
    """Element rows -> descriptors; no uniqueId and repeats are skipped, order is kept.

    At most ``max_elements`` descriptors are returned (the contract cap is
    5000). Rows without a uniqueId and rows repeating an already seen uniqueId
    are dropped rather than raising, because a Revit selection can contain both.
    """
    try:
        limit = int(max_elements)
    except (TypeError, ValueError):
        raise ValueError("max_elements must be an integer")
    if limit <= 0:
        return []
    descriptors = []
    seen = set()
    for row in rows or []:
        descriptor = row_to_descriptor(row)
        if descriptor is None or descriptor["nativeId"] in seen:
            continue
        seen.add(descriptor["nativeId"])
        descriptors.append(descriptor)
        if len(descriptors) >= limit:
            break
    return descriptors
