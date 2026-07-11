#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_v6_extensions.py — Generate the three V6 extension/facade files from their
v5 originals (originals untouched):

  DesignGrammar-BOT-extension.owl        -> DesignGrammar-BOT-extension-V6.owl
  DesignGrammar-Topologic-extension.owl  -> DesignGrammar-Topologic-extension-V6.owl
  DesignGrammar-standards-extension.owl  -> DesignGrammar-standards-extension-V6.owl   (facade)

Applies the v6.0 IRI shortening (meta#/valid#/comp#), the Knowledge->Spec rename
(spec#, dgs), Topology -> Core (dg:Topology), Reasoner/Session relocation in the
facade alignment axioms, and version bumps.
"""
import re
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
problems = {}


def check(name, text, banned):
    bad = {b: text.count(b) for b in banned if text.count(b) > 0}
    if bad:
        problems[name] = bad


def rm_lines(text, literal):
    """Remove every line consisting of indent + literal (+ newline)."""
    return re.sub(r"\n[ \t]*" + re.escape(literal), "", text)


# ============================================================
# 1. BOT extension
# ============================================================
src = (HERE / "DesignGrammar-BOT-extension.owl").read_text(encoding="utf-8")
t = src
t = t.replace("design-grammar/computation#", "design-grammar/comp#")   # ENTITY dgc (consistency)
t = t.replace("&dgc;Topology", "&dg;Topology")                          # Topology -> Core
t = t.replace("<owl:versionInfo>5.0</owl:versionInfo>", "<owl:versionInfo>6.0</owl:versionInfo>")
# prose: DG ComputationGraph topology -> DG Core topology (best-effort)
t = t.replace("DG ComputationGraph topology concepts", "DG Core topology concept (dg:Topology)")
(HERE / "DesignGrammar-BOT-extension-V6.owl").write_text(t, encoding="utf-8")
check("BOT", t, ["&dgc;Topology", "design-grammar/computation#"])
print("wrote DesignGrammar-BOT-extension-V6.owl")

# ============================================================
# 2. Topologic extension
# ============================================================
src = (HERE / "DesignGrammar-Topologic-extension.owl").read_text(encoding="utf-8")
t = src
t = t.replace("design-grammar/computation#", "design-grammar/comp#")
# remove ComputationGraph layer tags (Topology is Core / over-layer)
t = rm_lines(t, '<dg:graph rdf:resource="&dgc;ComputationGraph"/>')
# TypologyType: subClassOf ComputationGraph -> dg:Topology; any other ComputationGraph ref -> dg:Topology
t = t.replace("&dgc;ComputationGraph", "&dg;Topology")
t = t.replace("&dgc;Topology", "&dg;Topology")
t = t.replace("<owl:versionInfo>5.0</owl:versionInfo>", "<owl:versionInfo>6.0</owl:versionInfo>")
(HERE / "DesignGrammar-Topologic-extension-V6.owl").write_text(t, encoding="utf-8")
check("Topologic", t, ["&dgc;Topology", "&dgc;ComputationGraph",
                       '<dg:graph rdf:resource="&dgc;ComputationGraph"/>',
                       "design-grammar/computation#"])
print("wrote DesignGrammar-Topologic-extension-V6.owl")

# ============================================================
# 3. Standards-extension facade
# ============================================================
src = (HERE / "DesignGrammar-standards-extension.owl").read_text(encoding="utf-8")
t = src
# 3a IRI shortening + knowledge -> spec
t = t.replace("design-grammar/metagraph#", "design-grammar/meta#")
t = t.replace("design-grammar/validation#", "design-grammar/valid#")
t = t.replace('<!ENTITY dgk     "http://example.org/design-grammar/knowledge#">',
              '<!ENTITY dgs     "http://example.org/design-grammar/spec#">')
t = t.replace('xmlns:dgk="&dgk;"', 'xmlns:dgs="&dgs;"')
t = t.replace("&dgk;", "&dgs;")
# 3b moved/renamed entity refs in alignment axioms
t = t.replace("&dgs;KnowledgeSession", "&dg;Session")          # session unified into Core
t = t.replace("&dgs;knowledgeSessionId", "&dg;sessionId")
t = t.replace("&dgs;KnowledgeTag", "&dgs;SpecTag")
# (dgs:content/createdAt/noteId/source/tagName/title/updatedAt keep their local names)
# 3c distinct ontology IRI to avoid clashing with legacy DesignGrammaraligned.owl
t = t.replace('xml:base="http://example.org/design-grammar/aligned"',
              'xml:base="http://example.org/design-grammar/standards"')
t = t.replace('<owl:Ontology rdf:about="http://example.org/design-grammar/aligned">',
              '<owl:Ontology rdf:about="http://example.org/design-grammar/standards">')
# 3d version + prose touch-ups (before blanket prose rename)
t = t.replace("<owl:versionInfo>4.0</owl:versionInfo>", "<owl:versionInfo>6.0</owl:versionInfo>")
t = t.replace("parent of dgv:ValidationRun (a validation execution) and dgk:KnowledgeSession (an LLM ingest/query/update session). Aligned via R2.",
              "parent of dgv:ValidationRun (a validation execution) and dg:Session (a unified LLM-driven session). Aligned via R2.")
t = t.replace("equivalent to dgk:KnowledgeTag (a tag IS a concept in a project's tag taxonomy). Aligned via R5.",
              "equivalent to dgs:SpecTag (a tag IS a concept in a project's tag taxonomy). Aligned via R5.")
# 3e blanket prose cleanup (only prose remains for these tokens)
t = t.replace("KnowledgeSession", "Session")
t = t.replace("dgk:", "dgs:")
for w_old, w_new in (("KnowledgeTag", "SpecTag"), ("KnowledgeNote", "SpecNote"),
                     ("KnowledgeClass", "SpecClass"), ("KnowledgeGraph", "SpecGraph")):
    t = t.replace(w_old, w_new)
(HERE / "DesignGrammar-standards-extension-V6.owl").write_text(t, encoding="utf-8")
check("standards", t, ["&dgk;", "dgk:", "design-grammar/metagraph#",
                       "design-grammar/validation#", "design-grammar/knowledge#",
                       "&dgs;KnowledgeSession", "KnowledgeSession", "KnowledgeTag"])
print("wrote DesignGrammar-standards-extension-V6.owl")

# ============================================================
if problems:
    print("[WARN] residual banned tokens:")
    for f, bad in problems.items():
        print(f"  {f}: {bad}")
    sys.exit(2)
print("[OK] extension/facade files clean")
