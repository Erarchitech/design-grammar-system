"""Synthetic hexagonal-facade fixtures for the mapping engine (Phase 1303).

Populations follow test/v12-hexagonal-facade-01/3a-V1-summary.txt (V1):
100 HexagonalUnit, 25 GroundFloorUnit, 125 GlassPanel, 125
BottomTriangularPanel, 1 Facade. Geometry values are representative, not
measured; the rule rows mirror rules-approved.json (checked by a test when
the file is present).
"""

from __future__ import annotations

from mapping_engine import ClassInfo

CLASS_NAMES = (
    "HexagonalUnit",
    "GroundFloorUnit",
    "GlassPanel",
    "BottomTriangularPanel",
    "Facade",
    "FacadeModule",
    "PatternNode",
)

# (Rule_Id in the graph, class, data property, violation builtin, threshold)
FACADE_RULES = (
    ("R_GLASS_ASPECTRATIO_MIN_1.3_V", "GlassPanel", "hasAspectRatio", "lessThan", "1.3"),
    ("R_GLASS_ASPECTRATIO_MAX_6_V", "GlassPanel", "hasAspectRatio", "greaterThan", "6.0"),
    ("R_GEO_HEXUNIT_LEVELOFFSET_MAX_0_01_V", "HexagonalUnit", "hasLevelOffsetM", "greaterThan", "0.01"),
    ("R_BTP_HASVERTEXCOUNT_REQ_3_V", "BottomTriangularPanel", "hasVertexCount", "notEqual", "3"),
    ("R_GLASS_PLANARITYDEVIATION_MAX_0p005_V", "GlassPanel", "hasPlanarityDeviationM", "greaterThan", "0.005"),
    ("R_GP_WIDTH_MIN_4.5_V", "GlassPanel", "hasWidthM", "lessThan", "4.5"),
    ("R_FACADE_TOTALHEIGHT_MAX_120_V", "Facade", "hasTotalHeightM", "greaterThan", "120"),
    ("R_HEX_HASGAPCOUNT_MAX_0_V", "HexagonalUnit", "hasGapCount", "greaterThan", "0"),
    ("R_GFU_HASGAPCOUNT_MAX_0_V", "GroundFloorUnit", "hasGapCount", "greaterThan", "0"),
    ("R_GF_HASVERTEXCOUNT_REQ_5_V", "GroundFloorUnit", "hasVertexCount", "notEqual", "5"),
    ("R_HEX_HASVERTEXCOUNT_REQ_6_V", "HexagonalUnit", "hasVertexCount", "notEqual", "6"),
)

# Rules without a numeric comparison still count for rule impact (A1 control rule).
EXTRA_RULE_CLASSES = {"FacadeModule": ["R_FAC_A1_CONTROL_V"]}

REVIT_SYNONYMS = {
    "HexagonalUnit": ("hex",),
    "GroundFloorUnit": ("pent",),
    "GlassPanel": ("glass",),
    "BottomTriangularPanel": ("tri",),
    "Facade": ("frame",),
}


def facade_classes(synonyms=None):
    synonyms = synonyms or {}
    return [ClassInfo(f"ex:{name}", name, tuple(synonyms.get(name, ()))) for name in CLASS_NAMES]


def facade_rule_rows():
    return [
        {
            "ruleId": rule_id,
            "classIri": f"ex:{cls}",
            "propertyIri": f"ex:{prop}",
            "builtinIri": f"swrlb:{builtin}",
            "lex": lex,
            "datatype": "xsd:decimal",
        }
        for rule_id, cls, prop, builtin, lex in FACADE_RULES
    ]


def _gh(key, src, i):
    return f"gh:{key}:{src}:{{0;{i}}}:0"


def facade_descriptors(key="facade-v1", narrow=0, steep=0):
    """V1-like population; `narrow` glass panels get width 4.4 m, `steep` get aspect 6.3."""
    out = []
    for i in range(100):
        out.append(
            {
                "nativeId": _gh(key, "HU", i),
                "source": "HU",
                "geometry": {"kind": "curve", "vertexCount": 6, "gapCount": 0, "closed": True, "zMinM": 3.0 + i % 4},
                "properties": {"hasVertexCount": 6, "hasGapCount": 0, "hasLevelOffsetM": 0.0},
            }
        )
    for i in range(25):
        out.append(
            {
                "nativeId": _gh(key, "HU", 100 + i),
                "source": "HU",
                "geometry": {"kind": "curve", "vertexCount": 5, "gapCount": 0, "closed": True, "zMinM": 0.0},
                "properties": {"hasVertexCount": 5, "hasGapCount": 0, "hasLevelOffsetM": 0.0},
            }
        )
    for i in range(125):
        width = 4.4 if i < narrow else 4.8
        aspect = 6.3 if narrow <= i < narrow + steep else 2.4
        out.append(
            {
                "nativeId": _gh(key, "PB", i),
                "source": "PB",
                "geometry": {"kind": "surface", "vertexCount": 4, "closed": True, "planarityDeviationM": 0.001, "widthM": width},
                "properties": {"hasAspectRatio": aspect, "hasPlanarityDeviationM": 0.001, "hasWidthM": width},
            }
        )
    for i in range(125):
        out.append(
            {
                "nativeId": _gh(key, "PA", i),
                "source": "PA",
                "geometry": {"kind": "surface", "vertexCount": 3, "closed": True},
                "properties": {"hasVertexCount": 3},
            }
        )
    out.append(
        {
            "nativeId": _gh(key, "F", 0),
            "source": "F",
            "geometry": {"kind": "box", "heightM": 114.275},
            "properties": {"hasTotalHeightM": 114.275},
        }
    )
    return out


def facade_v1_descriptors():
    return facade_descriptors("facade-v1")


def facade_v2_descriptors():
    return facade_descriptors("facade-v2", narrow=57, steep=12)


REVIT_FAMILIES = (
    ("Facade_Module_Hex", 100, "HexagonalUnit"),
    ("Facade_Module_Pent", 25, "GroundFloorUnit"),
    ("Facade_Panel_Glass", 125, "GlassPanel"),
    ("Facade_Panel_Tri", 125, "BottomTriangularPanel"),
    ("Facade_Frame", 1, "Facade"),
)


def revit_like_descriptors(read="r1"):
    out = []
    for family, count, _ in REVIT_FAMILIES:
        for i in range(count):
            out.append(
                {
                    "nativeId": f"{read}-{family}-{i:04d}",
                    "platform": "revit",
                    "category": "Generic Models",
                    "family": family,
                    "type": "Standard",
                    "name": f"{family} : Standard",
                    "ifc": {"entity": "IfcBuildingElementProxy"},
                    "parameters": {"Mark": f"{i}"},
                }
            )
    return out


def gold_labels(descriptors):
    gold = {}
    for d in descriptors:
        nid = d["nativeId"]
        if "family" in d:
            cls = next(c for f, _, c in REVIT_FAMILIES if f == d["family"])
        elif d["source"] == "HU":
            cls = "HexagonalUnit" if d["geometry"]["vertexCount"] == 6 else "GroundFloorUnit"
        else:
            cls = {"PB": "GlassPanel", "PA": "BottomTriangularPanel", "F": "Facade"}[d["source"]]
        gold[nid] = {cls}
    return gold
