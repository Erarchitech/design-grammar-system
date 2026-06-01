#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate export_to_markdown_v6.py from export_to_markdown.py with v6.0 changes
(5 layers, meta#/valid#/spec#/comp# namespaces, SpecGraph rename, -V6 paths)."""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
s = (HERE / "export_to_markdown.py").read_text(encoding="utf-8")

# --- namespaces: shorten + dgk->dgs + add dgc ---
s = s.replace('"dgm": "http://example.org/design-grammar/metagraph#",',
              '"dgm": "http://example.org/design-grammar/meta#",')
s = s.replace('"dgv": "http://example.org/design-grammar/validation#",',
              '"dgv": "http://example.org/design-grammar/valid#",')
s = s.replace('    "dgk": "http://example.org/design-grammar/knowledge#",\n}',
              '    "dgs": "http://example.org/design-grammar/spec#",\n'
              '    "dgc": "http://example.org/design-grammar/comp#",\n}')

# --- layer names ---
s = s.replace(
    '''LAYER_NAMES = {
    "dg": "0. Core / Cross-cutting",
    "dgm": "2. Metagraph (SWRL rule structure)",
    "dgv": "3. ValidationGraph (validation runs, design state, integration)",
    "dgk": "4. KnowledgeGraph (project notes, tags, sessions)",
}''',
    '''LAYER_NAMES = {
    "dg": "0. Core + OntoGraph (over-layer entities + dynamic domain meta-schema)",
    "dgm": "2. Metagraph (SWRL rule structure)",
    "dgv": "3. ValidationGraph (validation runs, integration, Reasoner)",
    "dgs": "4. SpecGraph (project specification notes, tags)",
    "dgc": "5. ComputationGraph (DCM parametric design model)",
}''')

# --- prefix iteration lists ---
s = s.replace('["dg", "dgm", "dgv", "dgk"]', '["dg", "dgm", "dgv", "dgs", "dgc"]')
s = s.replace('for prefix in ["dgm", "dgv"]:', 'for prefix in ["dgm", "dgv", "dgc"]:')

# --- layer-overview prose + table ---
s = s.replace("partitions its content into four logical layers",
              "partitions its content into a Core band plus five logical layers")
s = s.replace(
    '''    out.append("| `dg` | `http://example.org/design-grammar#` | Cross-cutting + OntoGraph (dynamic domain ontology meta-schema) | Reifies OWL Class/DatatypeProperty/ObjectProperty as Neo4j nodes for query-ability |")
    out.append("| `dgm` | `http://example.org/design-grammar/metagraph#` | Metagraph | SWRL rule structure: Rule, Atom subtypes, Variable subtypes, Literal, Builtin |")
    out.append("| `dgv` | `http://example.org/design-grammar/validation#` | ValidationGraph | Validation runs, entity results, design state composition, integration config |")
    out.append("| `dgk` | `http://example.org/design-grammar/knowledge#` | KnowledgeGraph | Project notes, tags, knowledge sessions |")''',
    '''    out.append("| `dg` | `http://example.org/design-grammar#` | Core (over-layer) + OntoGraph | Gero FBS Object/Function/Behavior/Structure, Geometry, Topology, DesignState{ObjectState,DefState}, Session; and the reified OWL Class/DatatypeProperty/ObjectProperty meta-schema |")
    out.append("| `dgm` | `http://example.org/design-grammar/meta#` | Metagraph | SWRL rule structure: Rule, Atom subtypes, Variable subtypes, Literal, Builtin, RuleSet |")
    out.append("| `dgv` | `http://example.org/design-grammar/valid#` | ValidationGraph | Validation runs, entity results, integration config, Reasoner (= GH Validator) |")
    out.append("| `dgs` | `http://example.org/design-grammar/spec#` | SpecGraph | Project specification notes and tags (formerly KnowledgeGraph) |")
    out.append("| `dgc` | `http://example.org/design-grammar/comp#` | ComputationGraph | DCM parametric model: Algorithm, Procedure, Pattern, Parameter, Interface |")''')

# --- namespace reference block ---
s = s.replace(
    '''    out.append("dg   = http://example.org/design-grammar#")
    out.append("dgm  = http://example.org/design-grammar/metagraph#")
    out.append("dgv  = http://example.org/design-grammar/validation#")
    out.append("dgk  = http://example.org/design-grammar/knowledge#")''',
    '''    out.append("dg   = http://example.org/design-grammar#  (Core + OntoGraph)")
    out.append("dgm  = http://example.org/design-grammar/meta#")
    out.append("dgv  = http://example.org/design-grammar/valid#")
    out.append("dgs  = http://example.org/design-grammar/spec#")
    out.append("dgc  = http://example.org/design-grammar/comp#")''')

# --- render rdfs:subPropertyOf for object properties (so the v6 partonomy is
#     visible in the markdown — e.g. each ERD has-* property shows it is a
#     subPropertyOf dg:hasPart). ---
s = s.replace(
    '            inverse_of = collect_resources(elem, "owl", "inverseOf")\n'
    '            disjoint_with = collect_resources(elem, "owl", "propertyDisjointWith")\n',
    '            inverse_of = collect_resources(elem, "owl", "inverseOf")\n'
    '            disjoint_with = collect_resources(elem, "owl", "propertyDisjointWith")\n'
    '            super_props = collect_resources(elem, "rdfs", "subPropertyOf")\n')
s = s.replace(
    '            if disjoint_with:\n'
    '                out.append(f"- **Disjoint with (property):** {\', \'.join(f\'`{localname(p)}`\' for p in disjoint_with)}")\n',
    '            if disjoint_with:\n'
    '                out.append(f"- **Disjoint with (property):** {\', \'.join(f\'`{localname(p)}`\' for p in disjoint_with)}")\n'
    '            if super_props:\n'
    '                out.append(f"- **Sub-property of:** {\', \'.join(f\'`{localname(p)}`\' for p in super_props)}")\n')

# --- file paths + links: original -> V6 ---
s = s.replace("DesignGrammar.owl", "DesignGrammar-V6.owl")
s = s.replace("DesignGrammar.md", "DesignGrammar-V6.md")

(HERE / "export_to_markdown_v6.py").write_text(s, encoding="utf-8")
print("wrote export_to_markdown_v6.py")
