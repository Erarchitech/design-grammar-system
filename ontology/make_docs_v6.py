#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate ONTOLOGY-ALIGNMENT-V6.md and HIERARCHY-OPTIMIZATION-V6.md from their
originals, applying the v6.0 renames (Core band, IRI shortening, Knowledge->Spec,
Reasoner/Session/DesignState relocations) and a v6.0 banner. Originals untouched."""
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

V6_BANNER = (
    "> **v6.0 update.** This document was carried forward from the v5 alignment audit. "
    "In v6.0 the ontology gained a top-level **`dg:Core`** band of over-layer entities "
    "(Gero FBS Object/Function/Behavior/Structure, Geometry, Topology, "
    "DesignState{ObjectState,DefState}, and a unified `dg:Session`); the layer IRIs were "
    "shortened (`meta#`/`valid#`/`comp#`); the **KnowledgeGraph layer was renamed to "
    "SpecGraph** (`spec#`: SpecClass/SpecNote/SpecTag); **Reasoner** moved to the "
    "ValidationGraph (= the Grasshopper \"Validator\" component); `dgc:ParametricState` was "
    "dropped; and four bridges were added (`dg:objectRef`, `dg:definesFunction`, "
    "`dgv:refersToGeometry`, `dgm:validates`). Core entities are cross-cutting and have no "
    "external alignment of their own. Entity IRIs below are shown in their v6.0 namespaces.\n"
)


def common_renames(s: str) -> str:
    # specific knowledge entity renames first
    s = s.replace("dgk:KnowledgeSession", "dg:Session")
    s = s.replace("dgk:knowledgeSessionId", "dg:sessionId")
    s = s.replace("dgk:KnowledgeTag", "dgs:SpecTag")
    s = s.replace("dgk:KnowledgeNote", "dgs:SpecNote")
    s = s.replace("dgk:KnowledgeClass", "dgs:SpecClass")
    s = s.replace("dgk:", "dgs:")
    # moved state classes (avoid DesignStateParameter)
    s = re.sub(r"dgv:DesignState(?![A-Za-z])", "dg:DesignState", s)
    s = s.replace("dgv:DefState", "dg:DefState")
    s = s.replace("dgv:ObjectState", "dg:ObjectState")
    # FBS / geometry / topology moved to Core
    for nm in ("Object", "Function", "Behavior", "Structure", "Geometry", "Topology"):
        s = s.replace(f"dgc:{nm}", f"dg:{nm}")
    # Reasoner moved to ValidationGraph
    s = s.replace("dgm:Reasoner", "dgv:Reasoner")
    # layer / prose names
    s = s.replace("KnowledgeGraph", "SpecGraph")
    s = s.replace("KnowledgeSession", "Session")
    s = s.replace("KnowledgeNote", "SpecNote")
    s = s.replace("KnowledgeTag", "SpecTag")
    s = s.replace("KnowledgeClass", "SpecClass")
    # IRI fragment shortening
    s = s.replace("/metagraph#", "/meta#")
    s = s.replace("/validation#", "/valid#")
    s = s.replace("/computation#", "/comp#")
    s = s.replace("/knowledge#", "/spec#")
    # file references -> V6
    s = s.replace("DesignGrammar-aligned.owl", "DesignGrammar-standards-extension-V6.owl")
    s = s.replace("DesignGrammar.owl", "DesignGrammar-V6.owl")
    s = s.replace("DesignGrammar.md", "DesignGrammar-V6.md")
    s = s.replace("catalog-v001.xml", "catalog-v001-V6.xml")
    return s


def insert_banner(s: str) -> str:
    """Insert the v6 banner after the first leading blockquote (the doc's intro)."""
    lines = s.splitlines(keepends=True)
    out, inserted = [], False
    for i, ln in enumerate(lines):
        out.append(ln)
        if not inserted and i > 0 and ln.startswith(">") and (i + 1 >= len(lines) or not lines[i + 1].startswith(">")):
            out.append("\n" + V6_BANNER)
            inserted = True
    if not inserted:  # fallback: after first H1
        out = []
        for ln in lines:
            out.append(ln)
            if ln.startswith("# ") and not inserted:
                out.append("\n" + V6_BANNER + "\n")
                inserted = True
    return "".join(out)


for src_name, dst_name in (
    ("ONTOLOGY-ALIGNMENT.md", "ONTOLOGY-ALIGNMENT-V6.md"),
    ("HIERARCHY-OPTIMIZATION.md", "HIERARCHY-OPTIMIZATION-V6.md"),
):
    s = (HERE / src_name).read_text(encoding="utf-8")
    s = common_renames(s)
    s = insert_banner(s)
    s = s.replace("File structure (v4.0)", "File structure (v6.0)")
    s = s.replace("**Core ontology (v4.0)**", "**Core ontology (v6.0)**")
    s = s.replace("**Aligned facade (v4.0)**", "**Aligned facade (v6.0)**")
    # hierarchy-doc framing
    s = s.replace("42 classes under 4 layer hubs", "Core band + 5 layer hubs")
    s = s.replace("4 layer hubs", "5 layer hubs")
    s = s.replace("four layer hubs", "five layer hubs (under a Core band)")
    (HERE / dst_name).write_text(s, encoding="utf-8")
    print(f"wrote {dst_name}")
