"""F-01 (2026-10-29): the generated pyRevit program, executed the way the DG Revit connector executes it (compiled from
a Unicode string and exec'd in a fresh namespace), against a fake Revit 2026 API: ElementId has Value and no
IntegerValue, the boxes are found through the DG mapping, values and meshes come back as plain JSON-safe data."""

from __future__ import annotations

import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import property_scripts as ps  # noqa: E402
from test_property_scripts import DG, PROJECT, _Session, _rows  # noqa: E402

RULES = {"R_STR_OPENING_BEAM_V": "hasBeamIntersectionCount", "R_STR_OPENING_COLUMN_V": "hasColumnIntersectionCount"}
CATEGORIES = ["OST_GenericModel", "OST_StructuralFraming", "OST_StructuralColumns", "OST_Columns", "OST_Walls",
              "OST_Floors", "OST_Doors", "OST_Windows", "OST_SWallRectOpening", "OST_ArcWallRectOpening",
              "OST_StructuralFoundation", "OST_Roofs"]


class ElementId:
    """Revit 2026: Value only."""

    def __init__(self, value):
        self.Value = value

    def __eq__(self, other):
        return isinstance(other, ElementId) and other.Value == self.Value

    def __hash__(self):
        return hash(self.Value)


class XYZ:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class Identity:
    @staticmethod
    def OfPoint(point):
        return point


class Box:
    def __init__(self, lo, hi):
        self.Min, self.Max, self.Transform = XYZ(*lo), XYZ(*hi), Identity()


class Category:
    def __init__(self, name):
        self.Id = ElementId(-2000 - CATEGORIES.index(name))
        self.Name = name


class Element:
    def __init__(self, eid, category, lo, hi, dg_class=""):
        self.Id = ElementId(eid)
        self.UniqueId = "uid-%d" % eid
        self.Category = Category(category)
        self.Name = "element %d" % eid
        self._params = {"DG_Class": dg_class, "DG_MappingState": "confirmed" if dg_class else ""}
        self._box = Box(lo, hi)

    def LookupParameter(self, name):
        if name not in self._params:
            return None
        return types.SimpleNamespace(StorageType="String", AsString=lambda: self._params[name])

    def get_BoundingBox(self, view):
        return self._box

    def get_Geometry(self, options):
        return None


class FamilyInstance(Element):
    def __init__(self, *args, **kw):
        Element.__init__(self, *args, **kw)
        self.Symbol = types.SimpleNamespace(Name="300x300", Family=types.SimpleNamespace(Name="Box"))


def _fake_revit(monkeypatch, elements):
    bic = types.SimpleNamespace(**{n: -2000 - i for i, n in enumerate(CATEGORIES)})

    class Collector:
        def __init__(self, doc):
            self.doc, self.cat = doc, None

        def OfCategory(self, c):
            self.cat = int(c)
            return self

        def OfCategoryId(self, cid):
            self.cat = cid.Value
            return self

        def WhereElementIsNotElementType(self):
            return self

        def _items(self):
            if self.cat is None:  # FilteredElementCollector(doc) without a category filter: every element
                return list(self.doc.elements)
            return [e for e in self.doc.elements if e.Category.Id.Value == self.cat]

        def __iter__(self):
            return iter(self._items())

        def GetElementCount(self):
            return len(self._items())

    db = types.SimpleNamespace(
        BuiltInCategory=bic, FilteredElementCollector=Collector, FamilyInstance=FamilyInstance, XYZ=XYZ,
        StorageType=types.SimpleNamespace(String="String"), Options=lambda: types.SimpleNamespace(),
        ViewDetailLevel=types.SimpleNamespace(Fine="Fine"), Solid=type("Solid", (), {}),
        GeometryInstance=type("GeometryInstance", (), {}), Wall=type("Wall", (), {}))
    revit = types.ModuleType("Autodesk.Revit")
    revit.DB = db
    autodesk = types.ModuleType("Autodesk")
    autodesk.Revit = revit
    clr = types.ModuleType("clr")
    clr.AddReference = lambda name: None
    generic = types.ModuleType("System.Collections.Generic")
    generic.List = list
    for name, module in (("Autodesk", autodesk), ("Autodesk.Revit", revit), ("clr", clr),
                         ("System", types.ModuleType("System")), ("System.Collections", types.ModuleType("x")),
                         ("System.Collections.Generic", generic)):
        monkeypatch.setitem(sys.modules, name, module)

    generic_model = Category("OST_GenericModel")

    class Bindings:
        def ForwardIterator(self):
            items = iter([(types.SimpleNamespace(Name="DG_Class"), types.SimpleNamespace(Categories=[generic_model]))])

            class It:
                Key = Current = None

                def MoveNext(self):
                    try:
                        self.Key, self.Current = next(items)
                        return True
                    except StopIteration:
                        return False
            return It()

    doc = types.SimpleNamespace(elements=elements, ParameterBindings=Bindings(), Title="DG-DemoProject-2-openings_R26")
    doc.GetElement = lambda unique_id: next((e for e in doc.elements if e.UniqueId == unique_id), None)
    return doc


@pytest.fixture
def program():
    catalogue = ps.load_catalogue()
    return ps.generate(_Session(_rows(RULES)), PROJECT, None, catalogue=catalogue)["revit"]["source"]


def _execute(source, doc, family_filter="", with_context=True):
    namespace = {"__name__": "dg_property_check"}
    exec(compile(u"%s" % source, "<dg-property-check>", "exec"), namespace)  # as the connector does
    return namespace["run"](doc, family_filter, with_context)


def test_the_program_checks_the_mapped_boxes_of_a_revit_2026_model(monkeypatch, program):
    doc = _fake_revit(monkeypatch, [
        FamilyInstance(10, "OST_GenericModel", (0, 0, 0), (1, 1, 1), dg_class="OpeningBox"),   # in the beam
        FamilyInstance(11, "OST_GenericModel", (5, 5, 0), (6, 6, 1), dg_class="OpeningBox"),   # free
        FamilyInstance(12, "OST_GenericModel", (9, 9, 0), (9.5, 9.5, 1)),                      # not mapped
        Element(20, "OST_StructuralFraming", (0.5, -2, 0.5), (0.8, 3, 0.9)),                   # beam
        Element(30, "OST_StructuralColumns", (20, 20, 0), (21, 21, 3)),                         # far column
    ])

    answer = _execute(program, doc)

    json.dumps(answer)  # plain data only
    assert answer["document"] == "DG-DemoProject-2-openings_R26"
    assert [b["uniqueId"] for b in answer["boxes"]] == ["uid-10", "uid-11"]
    keys = {p["ruleId"]: i for i, p in enumerate(answer["properties"])}
    beam, column = keys["R_STR_OPENING_BEAM_V"], keys["R_STR_OPENING_COLUMN_V"]
    assert [b["values"][beam] for b in answer["boxes"]] == [1, 0]
    assert [b["values"][column] for b in answer["boxes"]] == [0, 0]
    assert all(isinstance(b["values"][beam], int) for b in answer["boxes"])
    mesh = answer["boxes"][0]["mesh"]
    assert mesh["units"] == "mm" and len(mesh["items"][0]["faces"]) == 12
    assert len(mesh["items"][0]["vertices"]) == 24 and max(mesh["items"][0]["vertices"]) == pytest.approx(304.8)
    assert answer["boxes"][0]["label"] == "Box : 300x300 [10]"
    assert "boxes: 2 (DG mapping OpeningBox)" in answer["report"]
    labels = [c["label"] for c in answer["context"]]
    assert "OST_StructuralFraming|OST_StructuralFraming : element 20 [20]" in labels
    assert answer["errors"] == 0


def test_without_a_mapping_the_family_filter_finds_the_boxes(monkeypatch, program):
    doc = _fake_revit(monkeypatch, [FamilyInstance(10, "OST_GenericModel", (0, 0, 0), (1, 1, 1)),
                                    Element(20, "OST_StructuralFraming", (0.5, -2, 0.5), (0.8, 3, 0.9))])
    answer = _execute(program, doc, "Box", with_context=False)
    assert [b["uniqueId"] for b in answer["boxes"]] == ["uid-10"]
    assert answer["context"] == []
    assert any("family filter" in line for line in answer["report"])


@pytest.mark.parametrize("engine", ["ironpython", "pythonnet"])
def test_solid_faces_are_triangulated_under_both_engines(monkeypatch, program, engine):
    """IronPython calls MeshTriangle.get_Index(k); pyRevit's CPython engine (pythonnet) may offer only Index[k]."""
    doc = _fake_revit(monkeypatch, [FamilyInstance(10, "OST_GenericModel", (0, 0, 0), (1, 1, 1), dg_class="OpeningBox")])
    db = sys.modules["Autodesk.Revit"].DB

    class Triangle:
        def __init__(self, corners):
            if engine == "ironpython":
                self.get_Index = lambda k: corners[k]
            else:
                self.Index = list(corners)

    class Mesh:
        Vertices = [XYZ(0, 0, 0), XYZ(1, 0, 0), XYZ(0, 1, 0)]
        NumTriangles = 1

        def get_Triangle(self, t):
            return Triangle((0, 1, 2))

    solid = db.Solid()
    solid.Volume = 1.0
    solid.Faces = [types.SimpleNamespace(Triangulate=lambda: Mesh()), types.SimpleNamespace(Triangulate=lambda: Mesh())]
    doc.elements[0].get_Geometry = lambda options: [solid]

    mesh = _execute(program, doc, with_context=False)["boxes"][0]["mesh"]["items"][0]
    assert mesh["faces"] == [[0, 1, 2], [3, 4, 5]]
    assert mesh["vertices"][3] == pytest.approx(304.8)


# --- Phase 1303-26 (D-79..D-81): the model snapshot of a confirmed mapping -------------------------------------------

def _snapshot_program():
    return ps.snapshot_program(ps.load_catalogue())["source"]


def _namespace(source):
    namespace = {"__name__": "dg_property_check"}
    exec(compile(u"%s" % source, "<dg-property-check>", "exec"), namespace)  # as the connector does
    return namespace


def _model():
    return [Element(20, "OST_StructuralFraming", (0, 0, 0), (1, 2, 3), dg_class="Beam"),
            Element(21, "OST_StructuralFraming", (5, 0, 0), (6, 2, 3), dg_class="Beam"),
            Element(30, "OST_Walls", (0, 0, 0), (10, 0.5, 3), dg_class="Wall"),
            Element(40, "OST_Floors", (0, 0, -1), (10, 10, 0))]


def test_the_fingerprint_covers_composition_and_position_of_the_mapped_categories(monkeypatch):
    cats = ["OST_StructuralFraming", "OST_Walls"]
    doc = _fake_revit(monkeypatch, _model())
    fingerprint = _namespace(_snapshot_program())["model_fingerprint"]
    digest, count = fingerprint(doc, cats)
    assert count == 3 and len(digest) == 64

    doc.elements.reverse()
    assert fingerprint(doc, cats) == (digest, 3)  # order of the collector does not matter

    doc.elements[0]._params["DG_Class"] = "Slab"  # a parameter edit without movement is no change
    assert fingerprint(doc, cats)[0] == digest

    doc.elements[0]._box = Box((0, 0, -1), (10, 10, 0.00001))  # a floor moved: not a mapped category
    assert fingerprint(doc, cats)[0] == digest

    beam = next(e for e in doc.elements if e.UniqueId == "uid-20")
    beam._box = Box((0, 0, 0), (1, 2, 3.0001))  # 0.03 mm: below the 1 mm rounding
    assert fingerprint(doc, cats)[0] == digest
    beam._box = Box((0.01, 0, 0), (1.01, 2, 3))  # 3 mm: a move
    assert fingerprint(doc, cats)[0] != digest

    doc = _fake_revit(monkeypatch, _model() + [Element(31, "OST_Walls", (0, 9, 0), (10, 9.5, 3))])
    assert fingerprint(doc, cats) != (digest, 3)  # a new element of a mapped category
    doc = _fake_revit(monkeypatch, _model()[1:])
    assert fingerprint(doc, cats)[1] == 2  # a deleted one


def test_the_snapshot_answers_meshes_of_the_session_elements_and_writes_nothing(monkeypatch):
    doc = _fake_revit(monkeypatch, _model())
    answer = _namespace(_snapshot_program())["snapshot"](doc, ["uid-20", "uid-30", "uid-99"],
                                                         ["OST_StructuralFraming", "OST_Walls"])
    json.dumps(answer)
    assert answer["document"] == "DG-DemoProject-2-openings_R26"
    assert answer["count"] == 3 and len(answer["fingerprint"]) == 64
    assert [e["uniqueId"] for e in answer["elements"]] == ["uid-20", "uid-30"]
    assert answer["elements"][0]["mesh"]["items"][0]["kind"] == "mesh"
    assert answer["missing"] == ["uid-99"]
    assert "Transaction(" not in _snapshot_program() and ".Set(" not in _snapshot_program()  # read-only


def test_the_check_program_reports_the_same_fingerprint_only_when_asked(monkeypatch, program):
    cats = ["OST_StructuralFraming", "OST_Walls"]
    doc = _fake_revit(monkeypatch, _model() + [FamilyInstance(10, "OST_GenericModel", (0, 0, 0), (1, 1, 1),
                                                              dg_class="OpeningBox")])
    ns = _namespace(program)
    without = ns["run"](doc, "", False)
    assert "fingerprint" not in without
    with_categories = ns["run"](doc, "", False, cats)
    snap = _namespace(_snapshot_program())["snapshot"](doc, [], cats)
    assert with_categories["fingerprint"] == snap["fingerprint"]
    assert with_categories["fingerprintCount"] == 3
