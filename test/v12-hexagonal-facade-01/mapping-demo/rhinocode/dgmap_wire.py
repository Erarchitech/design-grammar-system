#! python3
"""Wire the DG MAPPING script component on the -mapping.gh copy (Phase 1303 MVP slice).

- Mirrors the sources of the measure script component (the C# script with inputs
  PB, HU, GU, PA, F, LZ — gh-measure-rules.cs) onto the same-named inputs of DG MAPPING.
- CONNECTOR.Session -> DG MAPPING.Token (the token value is never read or written here).
- METAGRAPH.Objects -> DG MAPPING.OntoClasses (classes matched by name, not by index).
- Sets Project / Url / DefinitionKey / Classes defaults on unwired inputs.

Usage: RhinoCode.exe script <this file>   (log: %TEMP%\\dgmap-rhinocode.log)
"""

import importlib
import os
import sys

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
except NameError:  # a runner that does not set __file__
    sys.path.insert(0, r"C:\Users\Admin\source\repos\dg-mapping\test\v12-hexagonal-facade-01\mapping-demo\rhinocode")

import dgmap_common as c  # noqa: E402

importlib.reload(c)  # Rhino keeps modules loaded between runs

PROJECT = "v12-hexagonal-facade-01"
URL = "http://localhost:8000"
DEFINITION_KEY = "facade-v1"
CLASS_ORDER = "GlassPanel\nHexagonalUnit\nGroundFloorUnit\nBottomTriangularPanel\nFacade"
CONNECTOR_NAMES = ("CONNECTOR",)
METAGRAPH_NAMES = ("METAGRAPH",)


def _find_measure_script(doc, mapping):
    hits = []
    for o in doc.Objects:
        if o is mapping or not hasattr(o, "Params"):
            continue
        names = {p.Name for p in o.Params.Input}
        if set(c.STREAM_INPUTS).issubset(names):
            hits.append(o)
    if len(hits) != 1:
        raise RuntimeError("expected one measure script with inputs {}, found {}".format(c.STREAM_INPUTS, len(hits)))
    return hits[0]


def _first(doc, names):
    for name in names:
        found = c.objects_by_nickname(doc, name)
        if len(found) == 1:
            return found[0]
    raise RuntimeError("none of {} found exactly once".format(names))


def main(log_path):
    doc = c.gh_document()
    c.log(log_path, "wire: definition " + c.require_copy(doc))
    mapping = c.one_by_nickname(doc, c.MAPPING_NICK)
    measure = _find_measure_script(doc, mapping)
    for name in c.STREAM_INPUTS:
        target = c.input_param(mapping, name)
        target.RemoveAllSources()
        for source in c.input_param(measure, name).Sources:
            target.AddSource(source)
        c.log(log_path, "wire: {} <- {} source(s)".format(name, target.SourceCount))
    connector = _first(doc, CONNECTOR_NAMES)
    token = c.input_param(mapping, "Token")
    token.RemoveAllSources()
    token.AddSource(c.output_param(connector, "Session"))
    c.log(log_path, "wire: Token <- CONNECTOR.Session")
    metagraph = _first(doc, METAGRAPH_NAMES)
    onto = c.input_param(mapping, "OntoClasses")
    onto.RemoveAllSources()
    onto.AddSource(c.output_param(metagraph, "Objects"))
    c.log(log_path, "wire: OntoClasses <- METAGRAPH.Objects")
    for name, value in (("Project", PROJECT), ("Url", URL), ("DefinitionKey", DEFINITION_KEY)):
        if c.input_param(mapping, name).SourceCount == 0:
            c.set_input_value(mapping, name, value)
    classes = c.input_param(mapping, "Classes")
    if classes.SourceCount == 0:
        classes.PersistentData.Clear()
        from Grasshopper.Kernel.Types import GH_String

        for label in CLASS_ORDER.split("\n"):
            classes.PersistentData.Append(GH_String(label))
        classes.ExpireSolution(False)
    for name in ("Run", "Refresh", "Apply", "DryRun"):
        if c.input_param(mapping, name).SourceCount == 0:
            c.set_input_value(mapping, name, False)
    c.solve(doc)
    c.log(log_path, "wire: done")


c.run_main(main, c.DEFAULT_LOG)  # RhinoCode passes no script arguments
