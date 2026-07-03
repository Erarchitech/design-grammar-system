#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate export_to_markdown_v7.py from export_to_markdown_v6.py with v7.0
changes (-V7 file paths, Ontograph/Validgraph/Computgraph layer-hub casing,
ObjState/ParamState/PropState state trio, ObjProperty/DataProperty reification
rename in the Core+OntoGraph prose row)."""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
s = (HERE / "export_to_markdown_v6.py").read_text(encoding="utf-8")

# --- module docstring + file paths: -V6 -> -V7 ---
s = s.replace("DesignGrammar-V6.owl", "DesignGrammar-V7.owl")
s = s.replace("DesignGrammar-V6.md", "DesignGrammar-V7.md")

# --- LAYER_NAMES: layer-hub casing rename (Ontograph/Validgraph/Computgraph) ---
s = s.replace(
    '''LAYER_NAMES = {
    "dg": "0. Core + OntoGraph (over-layer entities + dynamic domain meta-schema)",
    "dgm": "2. Metagraph (SWRL rule structure)",
    "dgv": "3. ValidationGraph (validation runs, integration, Reasoner)",
    "dgs": "4. SpecGraph (project specification notes, tags)",
    "dgc": "5. ComputationGraph (DCM parametric design model)",
}''',
    '''LAYER_NAMES = {
    "dg": "0. Core + Ontograph (over-layer entities + dynamic domain meta-schema)",
    "dgm": "2. Metagraph (SWRL rule structure)",
    "dgv": "3. Validgraph (validation runs, integration, Reasoner)",
    "dgs": "4. SpecGraph (project specification notes, tags)",
    "dgc": "5. Computgraph (DCM parametric design model)",
}''')

# --- graph-layers table row: OntoGraph->Ontograph, state trio, reification rename ---
s = s.replace(
    '    out.append("| `dg` | `http://example.org/design-grammar#` | Core (over-layer) + OntoGraph | Gero FBS Object/Function/Behavior/Structure, Geometry, Topology, DesignState{ObjectState,DefState}, Session; and the reified OWL Class/DatatypeProperty/ObjectProperty meta-schema |")',
    '    out.append("| `dg` | `http://example.org/design-grammar#` | Core (over-layer) + Ontograph | Gero FBS Object/Function/Behavior/Structure, Geometry, Topology, DesignState{ObjState,ParamState,PropState}, Session; and the reified OWL Class/DataProperty/ObjProperty meta-schema |")')
s = s.replace(
    '    out.append("| `dgv` | `http://example.org/design-grammar/valid#` | ValidationGraph | Validation runs, entity results, integration config, Reasoner (= GH Validator) |")',
    '    out.append("| `dgv` | `http://example.org/design-grammar/valid#` | Validgraph | Validation runs, entity results, integration config, Reasoner (= GH Validator) |")')
s = s.replace(
    '    out.append("| `dgc` | `http://example.org/design-grammar/comp#` | ComputationGraph | DCM parametric model: Algorithm, Procedure, Pattern, Parameter, Interface |")',
    '    out.append("| `dgc` | `http://example.org/design-grammar/comp#` | Computgraph | DCM parametric model: Algorithm, Procedure, Pattern, Parameter, Interface |")')

# --- namespace reference block: OntoGraph->Ontograph ---
s = s.replace(
    '    out.append("dg   = http://example.org/design-grammar#  (Core + OntoGraph)")',
    '    out.append("dg   = http://example.org/design-grammar#  (Core + Ontograph)")')

(HERE / "export_to_markdown_v7.py").write_text(s, encoding="utf-8")
print("wrote export_to_markdown_v7.py")
