#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_v7_extensions.py — Generate the three V7 extension/facade files from their
v6 originals (V6 originals untouched):

  DesignGrammar-BOT-extension-V6.owl        -> DesignGrammar-BOT-extension-V7.owl
  DesignGrammar-Topologic-extension-V6.owl  -> DesignGrammar-Topologic-extension-V7.owl
  DesignGrammar-standards-extension-V6.owl  -> DesignGrammar-standards-extension-V7.owl   (facade)

Applies only the V7 renames from ontology/V7-INVESTIGATION.md that actually occur
in these facade files (they reference far fewer entities than the core owl):
  - version bump 6.0 -> 7.0 in all three
  - ComputationGraph -> Computgraph (prose, layer-hub casing rename) in BOT/Topologic
  - ValidationRun -> Run (&dgv;ValidationRun + prose) in the standards facade

BOT/Topologic anchor on dg:Topology, which is NOT renamed in V7 — no transform
needed for that token. The reification classes dg:ObjectProperty/dg:DatatypeProperty
are NOT referenced in any of the three facades (only the *Atom compound names
dgm:ObjectPropertyAtom/dgm:DataPropertyAtom appear, which are unrelated and already
short-named) so no ObjProperty/DataProperty transform applies here either.

owl:ObjectProperty / owl:DatatypeProperty (the OWL 2 language constructs used to
*declare* properties, e.g. <owl:ObjectProperty rdf:about="&topo;contains">) are
never touched by any replace in this script.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
problems = {}


def check(name, text, banned):
    bad = {b: text.count(b) for b in banned if text.count(b) > 0}
    if bad:
        problems[name] = bad


# ============================================================
# 1. BOT extension
# ============================================================
src = (HERE / "DesignGrammar-BOT-extension-V6.owl").read_text(encoding="utf-8")
t = src
t = t.replace("ComputationGraph", "Computgraph")  # layer-hub casing rename (prose only in this file)
t = t.replace("<owl:versionInfo>6.0</owl:versionInfo>", "<owl:versionInfo>7.0</owl:versionInfo>")
t = t.replace("BOT (Building Topology Ontology) EXTENSION (v5.0)", "BOT (Building Topology Ontology) EXTENSION (v7.0)")
(HERE / "DesignGrammar-BOT-extension-V7.owl").write_text(t, encoding="utf-8")
check("BOT", t, ["ComputationGraph", "<owl:versionInfo>6.0</owl:versionInfo>"])
print("wrote DesignGrammar-BOT-extension-V7.owl")

# ============================================================
# 2. Topologic extension
# ============================================================
src = (HERE / "DesignGrammar-Topologic-extension-V6.owl").read_text(encoding="utf-8")
t = src
t = t.replace("ComputationGraph", "Computgraph")  # layer-hub casing rename (prose only in this file)
t = t.replace("<owl:versionInfo>6.0</owl:versionInfo>", "<owl:versionInfo>7.0</owl:versionInfo>")
t = t.replace("TOPOLOGIC EXTENSION (v5.0)", "TOPOLOGIC EXTENSION (v7.0)")
(HERE / "DesignGrammar-Topologic-extension-V7.owl").write_text(t, encoding="utf-8")
check("Topologic", t, ["ComputationGraph", "<owl:versionInfo>6.0</owl:versionInfo>"])
print("wrote DesignGrammar-Topologic-extension-V7.owl")

# ============================================================
# 3. Standards-extension facade
# ============================================================
src = (HERE / "DesignGrammar-standards-extension-V6.owl").read_text(encoding="utf-8")
t = src
# ValidationRun -> Run (class + prose; "ValidationRun" is not a substring of any
# other token in this file, e.g. ValidationEntity is a distinct, non-renamed token)
t = t.replace("ValidationRun", "Run")
t = t.replace("<owl:versionInfo>6.0</owl:versionInfo>", "<owl:versionInfo>7.0</owl:versionInfo>")
t = t.replace("ALIGNED FACADE (v4.0)", "ALIGNED FACADE (v7.0)")
(HERE / "DesignGrammar-standards-extension-V7.owl").write_text(t, encoding="utf-8")
check("standards", t, ["ValidationRun", "<owl:versionInfo>6.0</owl:versionInfo>"])
print("wrote DesignGrammar-standards-extension-V7.owl")

# ============================================================
if problems:
    print("[WARN] residual banned tokens:")
    for f, bad in problems.items():
        print(f"  {f}: {bad}")
    sys.exit(2)
print("[OK] extension/facade files clean")
