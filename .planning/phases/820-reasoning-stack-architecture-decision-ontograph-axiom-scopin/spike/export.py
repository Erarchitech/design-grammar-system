"""Spike exporter: live Neo4j OntoGraph/Metagraph -> RDF (Turtle), label-scoped.

Throwaway spike for Phase 820 (REAS-04 axiom-scoping evidence). NOT the seed
of dg-reasoner — Phase 821 builds clean against spec/LPG-OWL-MAPPING.md.

Produces (under spike/output/):
  naive_export.ttl   — flat export of the live project's OntoGraph + Metagraph
                       (SWRL RDF vocabulary), no static TBox — spike part (a)
  axiom_counts.txt   — rdflib-parsed (authoritative, NOT grep) axiom counts
                       for ontology/DesignGrammar-V7.owl (Pitfall 2)
  hybrid_export.ttl  — with --hybrid: static DesignGrammar-V7.owl TBox UNION
                       the live export PLUS curated ex:Door owl:disjointWith
                       ex:Window PLUS seeded contradiction ex:SlidingDoor
                       rdfs:subClassOf both — spike part (b), TBox-only
                       (no individuals minted; Pitfall 4)

Export scoping is by node LABEL, never by the `graph` property (Pitfall 1:
v8-ui-smoke's two R_DOOR_ORIENTATION_V atoms carry graph:'OntoGraph' and would
be silently dropped by any {project, graph:'Metagraph'} query).

Credentials are read from NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD env vars
(dev-safe defaults matching data-service/app.py) — never hardcoded (T-820-01).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

from neo4j import GraphDatabase
from rdflib import BNode, Graph, Literal as RDFLiteral, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

# --- connection settings (env vars, dev-safe defaults per data-service/app.py) ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# --- namespaces ---
BASE = "http://example.org/design-grammar"  # DesignGrammar-V7.owl xml:base
# ex: is per-project dynamically-generated domain vocabulary — a namespace
# SEPARATE from the V7 meta-schema's dg/dgm/dgv/dgs (do not conflate).
EX = Namespace(f"{BASE}/ex#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")

# --- paths ---
SPIKE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SPIKE_DIR.parents[3]  # spike -> phase -> phases -> .planning -> root
OUT_DIR = SPIKE_DIR / "output"
OWL_PATH = Path(os.getenv("DG_OWL_PATH", str(REPO_ROOT / "ontology" / "DesignGrammar-V7.owl")))

# --- Cypher: scope by LABEL, never by the `graph` property (Pitfall 1) ---
METAGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin)
RETURN labels(n) AS labels, properties(n) AS props
"""

ONTOGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Class OR n:DatatypeProperty OR n:ObjectProperty)
RETURN labels(n) AS labels, properties(n) AS props
"""

BODY_HEAD_QUERY = """
MATCH (r:Rule)-[e:HAS_BODY|HAS_HEAD]->(a:Atom)
WHERE r.project = $project
RETURN r.Rule_Id AS rule_id, type(e) AS rel, e.`order` AS ord, a.Atom_Id AS atom_id
"""

REFERS_QUERY = """
MATCH (a:Atom)-[:REFERS_TO]->(t)
WHERE a.project = $project
RETURN a.Atom_Id AS atom_id, t.iri AS target_iri
"""

ARG_QUERY = """
MATCH (a:Atom)-[g:ARG]->(x)
WHERE a.project = $project
RETURN a.Atom_Id AS atom_id, g.`pos` AS pos, labels(x) AS labels, properties(x) AS props
"""

ATOM_COUNT_QUERY = "MATCH (a:Atom {project: $project}) RETURN count(a) AS n"

XSD_LOCAL = {
    "decimal": XSD.decimal, "integer": XSD.integer, "int": XSD.int,
    "boolean": XSD.boolean, "string": XSD.string, "float": XSD.float,
    "double": XSD.double, "dateTime": XSD.dateTime,
}

ATOM_TYPE_MAP = {
    "ClassAtom": (SWRL.ClassAtom, SWRL.classPredicate),
    "DataPropertyAtom": (SWRL.DatavaluedPropertyAtom, SWRL.propertyPredicate),
    "ObjectPropertyAtom": (SWRL.IndividualPropertyAtom, SWRL.propertyPredicate),
    "BuiltinAtom": (SWRL.BuiltinAtom, SWRL.builtin),
    # Live-data type drift (same R_DOOR_ORIENTATION_V rule as the graph-property
    # mistagging, Pitfall 1 family): two atoms carry the REFERS_TO target's kind
    # instead of the atom kind. Alias them so the mapping keeps fidelity.
    "DatatypeProperty": (SWRL.DatavaluedPropertyAtom, SWRL.propertyPredicate),
    "Builtin": (SWRL.BuiltinAtom, SWRL.builtin),
}

BUILTIN_TYPES = {"BuiltinAtom", "Builtin"}


def atom_kind(props: dict) -> tuple[URIRef, URIRef]:
    """SWRL type + predicate for an Atom node, warning on unknown type values."""
    t = props.get("type", "")
    if t not in ATOM_TYPE_MAP:
        print(f"WARNING: atom {props.get('Atom_Id')} has unknown type '{t}' — defaulting to ClassAtom")
    return ATOM_TYPE_MAP.get(t, (SWRL.ClassAtom, SWRL.classPredicate))


def expand_iri(curie: str | None) -> URIRef | None:
    """Expand stored CURIE-shaped iri strings (ex:Building, swrlb:greaterThan)."""
    if not curie:
        return None
    if curie.startswith(("http://", "https://")):
        return URIRef(curie)
    if ":" in curie:
        prefix, local = curie.split(":", 1)
        local = quote(local, safe="")
        if prefix == "ex":
            return EX[local]
        if prefix == "swrlb":
            return SWRLB[local]
        return URIRef(f"{BASE}/curie/{quote(prefix, safe='')}#{local}")
    return URIRef(f"{BASE}/term/{quote(curie, safe='')}")


def xsd_datatype(dt: str | None) -> URIRef:
    if not dt:
        return XSD.string
    local = dt.split(":", 1)[-1]
    return XSD_LOCAL.get(local, XSD.string)


def mint(project: str, kind: str, key: str) -> URIRef:
    return URIRef(f"{BASE}/project/{quote(project, safe='')}/{kind}/{quote(key, safe='')}")


def make_atom_list(g: Graph, items: list[URIRef]) -> URIRef | BNode:
    """Build a swrl:AtomList (typed rdf:List) preserving edge `order`."""
    if not items:
        return RDF.nil
    head = BNode()
    cur = head
    for i, item in enumerate(items):
        g.add((cur, RDF.type, SWRL.AtomList))
        g.add((cur, RDF.first, item))
        nxt = BNode() if i < len(items) - 1 else RDF.nil
        g.add((cur, RDF.rest, nxt))
        cur = nxt
    return head


def make_plain_list(g: Graph, items: list) -> URIRef | BNode:
    if not items:
        return RDF.nil
    head = BNode()
    cur = head
    for i, item in enumerate(items):
        g.add((cur, RDF.first, item))
        nxt = BNode() if i < len(items) - 1 else RDF.nil
        g.add((cur, RDF.rest, nxt))
        cur = nxt
    return head


def bind_prefixes(g: Graph) -> None:
    g.bind("ex", EX)
    g.bind("swrl", SWRL)
    g.bind("swrlb", SWRLB)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)


def build_rdf_graph(session, project: str) -> Graph:
    """Label-scoped export of one project's OntoGraph + Metagraph to RDF."""
    g = Graph()
    bind_prefixes(g)

    # --- OntoGraph: Class / DatatypeProperty / ObjectProperty ---
    for rec in session.run(ONTOGRAPH_QUERY, project=project):
        labels, props = rec["labels"], rec["props"]
        iri = expand_iri(props.get("iri"))
        if iri is None:
            continue
        if "Class" in labels:
            g.add((iri, RDF.type, OWL.Class))
            if props.get("label"):
                g.add((iri, RDFS.label, RDFLiteral(props["label"])))
        elif "DatatypeProperty" in labels:
            g.add((iri, RDF.type, OWL.DatatypeProperty))
            if props.get("SWRL_label"):
                g.add((iri, RDFS.label, RDFLiteral(props["SWRL_label"])))
            if props.get("range"):
                g.add((iri, RDFS.range, xsd_datatype(props["range"])))
        elif "ObjectProperty" in labels:
            g.add((iri, RDF.type, OWL.ObjectProperty))
            if props.get("label"):
                g.add((iri, RDFS.label, RDFLiteral(props["label"])))

    # --- Metagraph nodes ---
    atoms: dict[str, dict] = {}      # Atom_Id -> props
    rules: dict[str, dict] = {}      # Rule_Id -> props
    exported_atom_count = 0
    for rec in session.run(METAGRAPH_QUERY, project=project):
        labels, props = rec["labels"], rec["props"]
        if "Rule" in labels and props.get("Rule_Id"):
            rules[props["Rule_Id"]] = props
        elif "Atom" in labels and props.get("Atom_Id"):
            atoms[props["Atom_Id"]] = props
            exported_atom_count += 1
        elif "Builtin" in labels:
            iri = expand_iri(props.get("iri"))
            if iri is not None:
                g.add((iri, RDF.type, SWRL.Builtin))
        elif "Var" in labels and props.get("name"):
            var_iri = mint(project, "var", props["name"].lstrip("?"))
            g.add((var_iri, RDF.type, SWRL.Variable))
        # Literal nodes become typed RDF literals at ARG-mapping time, not nodes

    # Pitfall 1 assertion: label-scoped export must see ALL atoms, including
    # the mistagged graph:'OntoGraph' ones — compare with independent count.
    independent = session.run(ATOM_COUNT_QUERY, project=project).single()["n"]
    if exported_atom_count != independent:
        raise AssertionError(
            f"Atom export mismatch: exported {exported_atom_count}, "
            f"independent label count {independent} — scoping bug (Pitfall 1)"
        )

    # --- Atom individuals ---
    atom_iri: dict[str, URIRef] = {}
    for atom_id, props in atoms.items():
        a_iri = mint(project, "atom", atom_id)
        atom_iri[atom_id] = a_iri
        swrl_type, _ = atom_kind(props)
        g.add((a_iri, RDF.type, swrl_type))

    # --- REFERS_TO -> classPredicate / propertyPredicate / builtin ---
    for rec in session.run(REFERS_QUERY, project=project):
        atom_id, target = rec["atom_id"], expand_iri(rec["target_iri"])
        if atom_id not in atoms or target is None:
            continue
        _, predicate = atom_kind(atoms[atom_id])
        g.add((atom_iri[atom_id], predicate, target))

    # --- ARG.pos -> swrl:argument1/2 (binary atoms) or swrl:arguments list (builtins) ---
    args_by_atom: dict[str, list[tuple[int, object]]] = {}
    for rec in session.run(ARG_QUERY, project=project):
        atom_id = rec["atom_id"]
        if atom_id not in atoms:
            continue
        labels, props = rec["labels"], rec["props"]
        pos = rec["pos"] if rec["pos"] is not None else 0
        if "Var" in labels and props.get("name"):
            term: object = mint(project, "var", props["name"].lstrip("?"))
        elif "Literal" in labels:
            term = RDFLiteral(props.get("lex", ""), datatype=xsd_datatype(props.get("datatype")))
        else:
            continue
        args_by_atom.setdefault(atom_id, []).append((int(pos), term))

    for atom_id, arg_list in args_by_atom.items():
        arg_list.sort(key=lambda t: t[0])
        a_iri = atom_iri[atom_id]
        if atoms[atom_id].get("type") in BUILTIN_TYPES:
            g.add((a_iri, SWRL.arguments, make_plain_list(g, [t for _, t in arg_list])))
        else:
            for pos, term in arg_list:
                if pos == 1:
                    g.add((a_iri, SWRL.argument1, term))
                elif pos == 2:
                    g.add((a_iri, SWRL.argument2, term))
                else:
                    print(f"WARNING: non-builtin atom {atom_id} has ARG pos={pos} (>2) — unmapped")

    # --- Rules: swrl:Imp with ordered swrl:body / swrl:head AtomLists ---
    body_head: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for rec in session.run(BODY_HEAD_QUERY, project=project):
        rule_id, rel, ord_, atom_id = rec["rule_id"], rec["rel"], rec["ord"], rec["atom_id"]
        if rule_id not in rules or atom_id not in atoms:
            continue
        body_head.setdefault(rule_id, {}).setdefault(rel, []).append(
            (int(ord_) if ord_ is not None else 0, atom_id)
        )

    for rule_id, props in rules.items():
        r_iri = mint(project, "rule", rule_id)
        g.add((r_iri, RDF.type, SWRL.Imp))
        g.add((r_iri, RDFS.label, RDFLiteral(rule_id)))
        edges = body_head.get(rule_id, {})
        for rel, swrl_pred in (("HAS_BODY", SWRL.body), ("HAS_HEAD", SWRL.head)):
            items = sorted(edges.get(rel, []), key=lambda t: t[0])
            g.add((r_iri, swrl_pred, make_atom_list(g, [atom_iri[a] for _, a in items])))

    print(f"Exported project '{project}': {len(rules)} rules, {len(atoms)} atoms "
          f"(independent atom count: {independent} — label-scoped, Pitfall 1 OK)")
    return g


def count_tbox_axioms(owl_path: Path, out_path: Path) -> None:
    """Authoritative rdflib-parsed axiom counts (Pitfall 2: never grep)."""
    tbox = Graph()
    tbox.parse(owl_path, format="xml")
    counts = {
        "rdfs:subClassOf": len(list(tbox.triples((None, RDFS.subClassOf, None)))),
        "rdfs:domain": len(list(tbox.triples((None, RDFS.domain, None)))),
        "rdfs:range": len(list(tbox.triples((None, RDFS.range, None)))),
        "owl:disjointWith": len(list(tbox.triples((None, OWL.disjointWith, None)))),
        "owl:Class declarations": len(list(tbox.triples((None, RDF.type, OWL.Class)))),
    }
    lines = [
        f"DesignGrammar-V7.owl TBox axiom counts — rdflib-parsed (authoritative, not grep)",
        f"source: {owl_path.name}, total triples: {len(tbox)}",
        "",
    ]
    lines += [f"{k}: {v}" for k, v in counts.items()]
    lines += [
        "",
        "Note: owl:disjointWith == 0 is the empirical justification for curating",
        "disjointness axioms into the hybrid TBox — without them, consistency",
        "checking cannot meaningfully fail (the trivial-consistency false positive).",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    for k, v in counts.items():
        print(f"  {k}: {v}")


def export_naive(g: Graph, out_path: Path) -> None:
    g.serialize(destination=str(out_path), format="turtle", encoding="utf-8")
    print(f"Wrote {out_path} ({len(g)} triples)")


def export_hybrid(dynamic: Graph, owl_path: Path, out_path: Path) -> None:
    """Static V7 TBox + live export + curated disjointness + seeded contradiction.

    PURE TBox construction (Pitfall 4): no individuals minted, no ABox.
    ex:Door and ex:Window are the curated disjoint pair; ex:SlidingDoor is
    forced under both — HermiT must report it unsatisfiable.
    """
    g = Graph()
    bind_prefixes(g)
    g.parse(owl_path, format="xml")          # static TBox
    for triple in dynamic:                   # live label-scoped export
        g.add(triple)
    # curated disjointness (design-time artifact — the axiom V7 lacks)
    g.add((EX.Door, RDF.type, OWL.Class))
    g.add((EX.Window, RDF.type, OWL.Class))
    g.add((EX.Door, OWL.disjointWith, EX.Window))
    # seeded TBox contradiction: SlidingDoor under two disjoint parents
    g.add((EX.SlidingDoor, RDF.type, OWL.Class))
    g.add((EX.SlidingDoor, RDFS.subClassOf, EX.Door))
    g.add((EX.SlidingDoor, RDFS.subClassOf, EX.Window))
    g.serialize(destination=str(out_path), format="turtle", encoding="utf-8")
    print(f"Wrote {out_path} ({len(g)} triples)")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    hybrid = "--hybrid" in args
    positional = [a for a in args if not a.startswith("--")]
    project = positional[0] if positional else os.getenv("PROJECT", "v8-ui-smoke")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            dynamic = build_rdf_graph(session, project)
    finally:
        driver.close()

    export_naive(dynamic, OUT_DIR / "naive_export.ttl")
    count_tbox_axioms(OWL_PATH, OUT_DIR / "axiom_counts.txt")
    if hybrid:
        export_hybrid(dynamic, OWL_PATH, OUT_DIR / "hybrid_export.ttl")


if __name__ == "__main__":
    main()
