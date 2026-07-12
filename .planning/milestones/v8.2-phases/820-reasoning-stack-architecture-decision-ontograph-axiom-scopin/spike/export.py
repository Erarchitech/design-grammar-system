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
DGM = Namespace(f"{BASE}/meta#")  # spike-only annotations (SkippedRule/SkippedAtom)
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
    g.bind("dgm-spike", DGM)
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

    # --- Metagraph: collect nodes (label-scoped) ---
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
        # Var/Builtin declarations are emitted only when referenced by an
        # exported atom (orphan swrl-typed nodes confuse the OWL API parser).
        # Literal nodes become typed RDF literals at ARG-mapping time.

    # Pitfall 1 assertion: label-scoped export must see ALL atoms, including
    # the mistagged graph:'OntoGraph' ones — compare with independent count.
    independent = session.run(ATOM_COUNT_QUERY, project=project).single()["n"]
    if exported_atom_count != independent:
        raise AssertionError(
            f"Atom export mismatch: exported {exported_atom_count}, "
            f"independent label count {independent} — scoping bug (Pitfall 1)"
        )

    # --- collect structure (REFERS_TO, ARG, HAS_BODY/HAS_HEAD) ---
    refers: dict[str, URIRef] = {}
    for rec in session.run(REFERS_QUERY, project=project):
        target = expand_iri(rec["target_iri"])
        if rec["atom_id"] in atoms and target is not None:
            refers[rec["atom_id"]] = target

    args_by_atom: dict[str, list[tuple[int, object]]] = {}
    for rec in session.run(ARG_QUERY, project=project):
        atom_id = rec["atom_id"]
        if atom_id not in atoms:
            continue
        labels, props = rec["labels"], rec["props"]
        pos = int(rec["pos"]) if rec["pos"] is not None else 0
        if "Var" in labels and props.get("name"):
            term: object = mint(project, "var", props["name"].lstrip("?"))
        elif "Literal" in labels:
            term = RDFLiteral(props.get("lex", ""), datatype=xsd_datatype(props.get("datatype")))
        else:
            continue
        args_by_atom.setdefault(atom_id, []).append((pos, term))

    body_head: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for rec in session.run(BODY_HEAD_QUERY, project=project):
        rule_id, rel, ord_, atom_id = rec["rule_id"], rec["rel"], rec["ord"], rec["atom_id"]
        if rule_id not in rules or atom_id not in atoms:
            continue
        body_head.setdefault(rule_id, {}).setdefault(rel, []).append(
            (int(ord_) if ord_ is not None else 0, atom_id)
        )

    # --- SWRL well-formedness (live data has atoms with NO ARG edges at all;
    #     OWL API/HermiT refuses to translate rules containing them, so
    #     incomplete rules are captured as annotated SkippedRule/SkippedAtom
    #     individuals instead of malformed swrl:Imp structures) ---
    def atom_incomplete_reason(atom_id: str) -> str | None:
        props = atoms[atom_id]
        t = props.get("type", "")
        if atom_id not in refers:
            return "missing REFERS_TO target"
        positions = {p for p, _ in args_by_atom.get(atom_id, [])}
        if t in BUILTIN_TYPES:
            return None if positions else "BuiltinAtom has no ARG edges"
        if t == "ClassAtom" or t not in ATOM_TYPE_MAP:
            return None if 1 in positions else "ClassAtom missing ARG pos=1"
        return None if {1, 2} <= positions else "property atom missing ARG pos=1 and/or pos=2"

    incomplete_atoms = {aid: r for aid in atoms if (r := atom_incomplete_reason(aid))}

    skipped_rules: dict[str, str] = {}
    for rule_id in rules:
        edges = body_head.get(rule_id, {})
        body, head = edges.get("HAS_BODY", []), edges.get("HAS_HEAD", [])
        if not body or not head:
            skipped_rules[rule_id] = "missing HAS_BODY and/or HAS_HEAD atoms"
            continue
        bad = sorted({aid for _, aid in body + head if aid in incomplete_atoms})
        if bad:
            skipped_rules[rule_id] = "incomplete atoms: " + ", ".join(bad)

    exported_rules = [r for r in rules if r not in skipped_rules]
    swrl_atom_ids: set[str] = set()
    for rule_id in exported_rules:
        for items in body_head.get(rule_id, {}).values():
            swrl_atom_ids.update(aid for _, aid in items)

    # --- emit SWRL atoms (well-formed rules only) ---
    atom_iri: dict[str, URIRef] = {aid: mint(project, "atom", aid) for aid in atoms}
    for atom_id in swrl_atom_ids:
        props = atoms[atom_id]
        a_iri = atom_iri[atom_id]
        swrl_type, predicate = atom_kind(props)
        g.add((a_iri, RDF.type, swrl_type))
        g.add((a_iri, predicate, refers[atom_id]))
        if props.get("type") in BUILTIN_TYPES:
            g.add((refers[atom_id], RDF.type, SWRL.Builtin))
        arg_list = sorted(args_by_atom.get(atom_id, []), key=lambda t: t[0])
        for _, term in arg_list:
            if isinstance(term, URIRef):  # a minted Var — declare it
                g.add((term, RDF.type, SWRL.Variable))
        if props.get("type") in BUILTIN_TYPES:
            g.add((a_iri, SWRL.arguments, make_plain_list(g, [t for _, t in arg_list])))
        else:
            for pos, term in arg_list:
                if pos == 1:
                    g.add((a_iri, SWRL.argument1, term))
                elif pos == 2:
                    g.add((a_iri, SWRL.argument2, term))
                else:
                    print(f"WARNING: non-builtin atom {atom_id} has ARG pos={pos} (>2) — unmapped")

    # --- emit rules ---
    for rule_id in exported_rules:
        r_iri = mint(project, "rule", rule_id)
        g.add((r_iri, RDF.type, SWRL.Imp))
        g.add((r_iri, RDFS.label, RDFLiteral(rule_id)))
        edges = body_head.get(rule_id, {})
        for rel, swrl_pred in (("HAS_BODY", SWRL.body), ("HAS_HEAD", SWRL.head)):
            items = sorted(edges.get(rel, []), key=lambda t: t[0])
            g.add((r_iri, swrl_pred, make_atom_list(g, [atom_iri[a] for _, a in items])))

    # --- captured-not-dropped: skipped rules/atoms stay in the export as
    #     annotated individuals (incl. the two mistagged R_DOOR_ORIENTATION_V
    #     atoms — Pitfall 1's label-scoping catch) without swrl typing ---
    for rule_id, reason in skipped_rules.items():
        r_iri = mint(project, "rule", rule_id)
        g.add((r_iri, RDF.type, DGM.SkippedRule))
        g.add((r_iri, RDFS.label, RDFLiteral(rule_id)))
        g.add((r_iri, RDFS.comment, RDFLiteral(
            f"captured by label-scoped export but not mapped to swrl:Imp — {reason}")))
        print(f"NOTE: rule {rule_id} skipped from SWRL mapping — {reason}")
    for atom_id in atoms:
        if atom_id in swrl_atom_ids:
            continue
        reason = incomplete_atoms.get(atom_id, "belongs to a skipped rule")
        g.add((atom_iri[atom_id], RDF.type, DGM.SkippedAtom))
        g.add((atom_iri[atom_id], RDFS.comment, RDFLiteral(
            f"captured by label-scoped export but excluded from SWRL mapping — {reason}")))

    print(f"Exported project '{project}': {len(exported_rules)}/{len(rules)} rules as swrl:Imp "
          f"({len(skipped_rules)} skipped as SWRL-incomplete), "
          f"{len(atoms)} atoms captured (independent atom count: {independent} — "
          f"label-scoped, Pitfall 1 OK; {len(swrl_atom_ids)} mapped to SWRL, "
          f"{len(atoms) - len(swrl_atom_ids)} kept as dgm:SkippedAtom)")
    return g


def strip_hermit_unsupported(g: Graph) -> int:
    """Remove swrl:Imp rules that use builtin atoms from a reasoning-input graph.

    HermiT rejects any ontology containing SWRL builtin atoms outright
    ("built-in atoms are not supported yet" — java.lang.IllegalArgumentException),
    and DG's violation pattern is builtin-centric. The canonical .ttl evidence
    files keep the FULL SWRL mapping; only the reasoner input is filtered.
    The consistency contrast the spike proves lives entirely in the TBox
    class/property axioms, which are untouched. Returns removed-rule count.
    """
    builtin_atoms = set(g.subjects(RDF.type, SWRL.BuiltinAtom))

    def list_cells(node):
        cells = []
        while node is not None and node != RDF.nil:
            first = g.value(node, RDF.first)
            cells.append((node, first))
            node = g.value(node, RDF.rest)
        return cells

    removed = 0
    for imp in list(g.subjects(RDF.type, SWRL.Imp)):
        cells, atoms_of = [], []
        for pred in (SWRL.body, SWRL.head):
            for head in g.objects(imp, pred):
                for cell, item in list_cells(head):
                    cells.append(cell)
                    if item is not None:
                        atoms_of.append(item)
        if not any(a in builtin_atoms for a in atoms_of):
            continue
        for atom in set(atoms_of):
            for args_head in g.objects(atom, SWRL.arguments):
                for cell, _ in list_cells(args_head):
                    g.remove((cell, None, None))
            g.remove((atom, None, None))
        for cell in cells:
            g.remove((cell, None, None))
        g.remove((imp, None, None))
        removed += 1

    # prune now-unreferenced swrl:Variable / swrl:Builtin declarations
    used_terms = set(g.objects(None, SWRL.argument1)) | set(g.objects(None, SWRL.argument2)) \
        | set(g.objects(None, RDF.first))
    for var in list(g.subjects(RDF.type, SWRL.Variable)):
        if var not in used_terms:
            g.remove((var, None, None))
    used_builtins = set(g.objects(None, SWRL.builtin))
    for b in list(g.subjects(RDF.type, SWRL.Builtin)):
        if b not in used_builtins:
            g.remove((b, RDF.type, SWRL.Builtin))
    return removed


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
