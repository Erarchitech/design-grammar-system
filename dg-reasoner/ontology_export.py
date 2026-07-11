"""dg-reasoner Cypher -> RDF translator (REAS-04 / REAS-05).

Clean production implementation of `spec/LPG-OWL-MAPPING.md`'s normative
Metagraph->SWRL-RDF and OntoGraph->OWL mapping tables. This module is NOT a
port of the Phase 820 spike
(`.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/export.py`)
-- that script is reference material only; this translator is rebuilt
directly against the mapping spec. n10s/neosemantics is never imported here:
the sidecar's reasoning path is bolt -> Cypher -> rdflib, entirely
independent of the neo4j-side n10s plugin installed for Plan 01's smoke test.

Public entry point: `build_graph(session, project) -> rdflib.Graph`.
`session` is any object exposing a Neo4j-driver-shaped `.run(query,
**params)` method returning an iterable of mapping-like records (each
supporting `rec[key]` access, with `.single()` available on the result) --
exactly the contract `neo4j.Session` satisfies. This module never imports
`neo4j` at module scope, so `build_graph` is importable and fully unit
-testable without a live Neo4j connection or the `neo4j` package installed;
`main()` imports the real driver lazily for the CLI export path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import BNode, Graph, Literal as RDFLiteral, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

# --- namespaces (spec/LPG-OWL-MAPPING.md #Namespaces & Terminology) ---
BASE = "http://example.org/design-grammar"  # matches DesignGrammar-V7.owl xml:base
DG = Namespace(f"{BASE}#")  # dg: meta-schema (graph-layer + rule annotation properties)
DGM = Namespace(f"{BASE}/meta#")  # dgm: Metagraph-layer entity definitions (SkippedRule/SkippedAtom)
EX = Namespace(f"{BASE}/ex#")  # ex: per-project domain vocabulary (NOT the static TBox)
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")

# --- label-scoped Cypher (Export Scoping mandate: scope by LABEL, never `graph`) ---
# See spec #Export Scoping -- Pitfall 1: v8-ui-smoke has two R_DOOR_ORIENTATION_V
# atoms mistagged graph:'OntoGraph'; scoping by label (not the `graph` property)
# is the only reliable defense against silently dropping them.
ONTOGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Class OR n:DatatypeProperty OR n:ObjectProperty)
RETURN labels(n) AS labels, properties(n) AS props
"""

METAGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin)
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

# --- Atom.type (schema-legal values per cypher_template.txt) -> SWRL RDF term ---
ATOM_TYPE_MAP: dict[str, tuple[URIRef, URIRef]] = {
    "ClassAtom": (SWRL.ClassAtom, SWRL.classPredicate),
    "DataPropertyAtom": (SWRL.DatavaluedPropertyAtom, SWRL.propertyPredicate),
    "ObjectPropertyAtom": (SWRL.IndividualPropertyAtom, SWRL.propertyPredicate),
    "BuiltinAtom": (SWRL.BuiltinAtom, SWRL.builtin),
}
BUILTIN_ATOM_TYPE = "BuiltinAtom"

XSD_BY_LOCAL: dict[str, URIRef] = {
    "decimal": XSD.decimal,
    "integer": XSD.integer,
    "int": XSD.int,
    "boolean": XSD.boolean,
    "string": XSD.string,
    "float": XSD.float,
    "double": XSD.double,
    "dateTime": XSD.dateTime,
}


def xsd_datatype(stored: str | None) -> URIRef:
    """Map a stored `xsd:foo` (or bare `foo`) datatype string to its XSD IRI.

    Unknown/absent datatypes default to xsd:string per the mapping table.
    """
    if not stored:
        return XSD.string
    local = stored.split(":", 1)[-1]
    return XSD_BY_LOCAL.get(local, XSD.string)


def expand_iri(curie: str | None) -> URIRef | None:
    """Expand a stored CURIE-shaped `iri` property (`ex:Building`, `swrlb:greaterThan`).

    Full http(s) IRIs pass through unchanged. Unknown prefixes fall back to a
    deterministic `{BASE}/curie/{prefix}#{local}` IRI rather than silently
    dropping the node.
    """
    if not curie:
        return None
    if curie.startswith(("http://", "https://")):
        return URIRef(curie)
    if ":" not in curie:
        return URIRef(f"{BASE}/term/{quote(curie, safe='')}")
    prefix, local = curie.split(":", 1)
    local = quote(local, safe="")
    if prefix == "ex":
        return EX[local]
    if prefix == "swrlb":
        return SWRLB[local]
    return URIRef(f"{BASE}/curie/{quote(prefix, safe='')}#{local}")


def mint(project: str, kind: str, key: str) -> URIRef:
    """Mint a project-scoped IRI: `{BASE}/project/{project}/{kind}/{key}`."""
    return URIRef(f"{BASE}/project/{quote(project, safe='')}/{kind}/{quote(key, safe='')}")


def make_atom_list(graph: Graph, atoms_in_order: list[URIRef]) -> URIRef | BNode:
    """Build an ordered `swrl:AtomList` (typed rdf:List) for a rule's body/head.

    Encodes `HAS_BODY`/`HAS_HEAD.order` as implicit list position: each cell
    is typed `swrl:AtomList` and chained via `rdf:first`/`rdf:rest`.
    """
    if not atoms_in_order:
        return RDF.nil
    first_cell = BNode()
    cell = first_cell
    for index, atom_iri in enumerate(atoms_in_order):
        graph.add((cell, RDF.type, SWRL.AtomList))
        graph.add((cell, RDF.first, atom_iri))
        next_cell = BNode() if index < len(atoms_in_order) - 1 else RDF.nil
        graph.add((cell, RDF.rest, next_cell))
        cell = next_cell
    return first_cell


def make_argument_list(graph: Graph, terms_in_order: list) -> URIRef | BNode:
    """Build a plain `rdf:List` for a BuiltinAtom's `swrl:arguments`.

    Unlike `swrl:AtomList` cells, argument-list cells carry no extra type --
    this is a bare RDF collection encoding `ARG.pos` order for variable-arity
    builtins (spec #BuiltinAtom and swrl:arguments).
    """
    if not terms_in_order:
        return RDF.nil
    first_cell = BNode()
    cell = first_cell
    for index, term in enumerate(terms_in_order):
        graph.add((cell, RDF.first, term))
        next_cell = BNode() if index < len(terms_in_order) - 1 else RDF.nil
        graph.add((cell, RDF.rest, next_cell))
        cell = next_cell
    return first_cell


def bind_prefixes(graph: Graph) -> None:
    graph.bind("dg", DG)
    graph.bind("dgm", DGM)
    graph.bind("ex", EX)
    graph.bind("swrl", SWRL)
    graph.bind("swrlb", SWRLB)
    graph.bind("owl", OWL)
    graph.bind("xsd", XSD)


def _atom_completeness_reason(
    atom_type: str,
    has_refers_to_target: bool,
    arg_positions: set[int],
    raw_positions: list[int | None] | None = None,
) -> str | None:
    """Return None if well-formed, else a human-readable SWRL-incompleteness reason.

    Mirrors the per-atom-kind well-formedness rules a real SWRL/OWL API
    parser would enforce: ClassAtom needs ARG pos=1; DataPropertyAtom and
    ObjectPropertyAtom need both pos=1 and pos=2; BuiltinAtom needs at least
    one ARG edge (arity is variable, encoded via swrl:arguments) AND all
    positions must be present and unique (order is semantically load-bearing
    for builtins — CR-03).
    """
    if not has_refers_to_target:
        return "missing REFERS_TO target"
    if atom_type == BUILTIN_ATOM_TYPE:
        if not arg_positions:
            return "BuiltinAtom has no ARG edges"
        if raw_positions is not None:
            if any(rp is None for rp in raw_positions):
                return "BuiltinAtom has missing (null) ARG.pos value(s)"
            if len(raw_positions) != len(set(raw_positions)):
                return "BuiltinAtom has duplicate ARG.pos values"
        return None
    if atom_type == "ClassAtom":
        return None if 1 in arg_positions else "ClassAtom missing ARG pos=1"
    if atom_type in ("DataPropertyAtom", "ObjectPropertyAtom"):
        return None if {1, 2} <= arg_positions else "property atom missing ARG pos=1 and/or pos=2"
    # Not a schema-legal Atom.type (cypher_template.txt) -- route to SkippedAtom
    # rather than guessing ClassAtom and emitting a hybrid, non-spec-legal shape.
    return f"unrecognized Atom.type '{atom_type}'"


def build_graph(session, project: str) -> Graph:
    """Label-scoped translation of one project's OntoGraph + Metagraph to RDF.

    Implements every row of the Node Mapping Tables in
    `spec/LPG-OWL-MAPPING.md` (#Metagraph to SWRL RDF Mapping,
    #OntoGraph to OWL Mapping), the Edge-Property Reification section
    (`ARG.pos` -> swrl:argument1/2 or swrl:arguments; `HAS_BODY`/`HAS_HEAD
    .order` -> ordered swrl:AtomList), and the IRI Minting Strategy.

    SWRL-incomplete atoms/rules (missing REFERS_TO or required ARG edges)
    are captured -- not dropped -- as annotated `dgm:SkippedAtom` /
    `dgm:SkippedRule` individuals, excluded from any `swrl:Imp` mapping.

    Raises `AssertionError` if the label-scoped atom export count diverges
    from an independent `MATCH (a:Atom {project: $project})` count (Pitfall
    1 guard -- catches export-scoping bugs, e.g. accidentally filtering by
    the non-authoritative `graph` property instead of node label).
    """
    graph = Graph()
    bind_prefixes(graph)

    # --- OntoGraph: Class / DatatypeProperty / ObjectProperty (flat vocabulary) ---
    for record in session.run(ONTOGRAPH_QUERY, project=project):
        labels, props = record["labels"], record["props"]
        iri = expand_iri(props.get("iri"))
        if iri is None:
            continue
        if "Class" in labels:
            graph.add((iri, RDF.type, OWL.Class))
            if props.get("label"):
                graph.add((iri, RDFS.label, RDFLiteral(props["label"])))
        elif "DatatypeProperty" in labels:
            graph.add((iri, RDF.type, OWL.DatatypeProperty))
            if props.get("SWRL_label"):
                graph.add((iri, RDFS.label, RDFLiteral(props["SWRL_label"])))
            if props.get("range"):
                graph.add((iri, RDFS.range, xsd_datatype(props["range"])))
        elif "ObjectProperty" in labels:
            graph.add((iri, RDF.type, OWL.ObjectProperty))
            if props.get("label"):
                graph.add((iri, RDFS.label, RDFLiteral(props["label"])))

    # --- Metagraph: collect Rule/Atom nodes (label-scoped, Pitfall 1 defense) ---
    rules: dict[str, dict] = {}
    atoms: dict[str, dict] = {}
    exported_atom_count = 0
    for record in session.run(METAGRAPH_QUERY, project=project):
        labels, props = record["labels"], record["props"]
        if "Rule" in labels and props.get("Rule_Id"):
            rules[props["Rule_Id"]] = props
        elif "Atom" in labels and props.get("Atom_Id"):
            atoms[props["Atom_Id"]] = props
            exported_atom_count += 1
        # Var/Literal/Builtin declarations are only emitted once referenced
        # by an exported atom below -- orphan swrl-typed nodes confuse
        # downstream OWL API parsing.

    independent_atom_count = session.run(ATOM_COUNT_QUERY, project=project).single()["n"]
    if exported_atom_count != independent_atom_count:
        raise AssertionError(
            f"Atom export mismatch for project '{project}': label-scoped export saw "
            f"{exported_atom_count} atoms, independent label-based count is "
            f"{independent_atom_count} -- export-scoping bug (spec #Export Scoping, Pitfall 1)"
        )

    # --- REFERS_TO targets ---
    refers_to: dict[str, URIRef] = {}
    for record in session.run(REFERS_QUERY, project=project):
        atom_id = record["atom_id"]
        target = expand_iri(record["target_iri"])
        if atom_id in atoms and target is not None:
            refers_to[atom_id] = target

    # --- ARG edges, grouped by atom ---
    args_by_atom: dict[str, list[tuple[int, object]]] = {}
    raw_positions_by_atom: dict[str, list[int | None]] = {}  # pre-default pos for validation
    for record in session.run(ARG_QUERY, project=project):
        atom_id = record["atom_id"]
        if atom_id not in atoms:
            continue
        labels, props = record["labels"], record["props"]
        raw_pos = record["pos"]  # may be None — validated before defaulting (CR-03)
        pos = int(raw_pos) if raw_pos is not None else 0
        term: object
        if "Var" in labels and props.get("name"):
            term = mint(project, "var", props["name"].lstrip("?"))
        elif "Literal" in labels:
            term = RDFLiteral(props.get("lex", ""), datatype=xsd_datatype(props.get("datatype")))
        else:
            continue
        args_by_atom.setdefault(atom_id, []).append((pos, term))
        raw_positions_by_atom.setdefault(atom_id, []).append(raw_pos)

    # --- HAS_BODY / HAS_HEAD edges, grouped by rule + relation ---
    body_head: dict[str, dict[str, list[tuple[int, str]]]] = {}
    raw_order_by_rule: dict[str, dict[str, list[int | None]]] = {}  # pre-default order for validation
    for record in session.run(BODY_HEAD_QUERY, project=project):
        rule_id, rel, order, atom_id = record["rule_id"], record["rel"], record["ord"], record["atom_id"]
        if rule_id not in rules or atom_id not in atoms:
            continue
        body_head.setdefault(rule_id, {}).setdefault(rel, []).append(
            (int(order) if order is not None else 0, atom_id)
        )
        raw_order_by_rule.setdefault(rule_id, {}).setdefault(rel, []).append(order)

    # --- SWRL well-formedness: split atoms/rules into exported vs. skipped ---
    incomplete_atoms: dict[str, str] = {}
    for atom_id, props in atoms.items():
        positions = {pos for pos, _ in args_by_atom.get(atom_id, [])}
        raw_pos = raw_positions_by_atom.get(atom_id)
        reason = _atom_completeness_reason(
            props.get("type", ""), atom_id in refers_to, positions, raw_positions=raw_pos
        )
        if reason:
            incomplete_atoms[atom_id] = reason

    skipped_rules: dict[str, str] = {}
    for rule_id in rules:
        edges = body_head.get(rule_id, {})
        body, head = edges.get("HAS_BODY", []), edges.get("HAS_HEAD", [])
        if not body or not head:
            skipped_rules[rule_id] = "missing HAS_BODY and/or HAS_HEAD atoms"
            continue
        # Validate HAS_BODY/HAS_HEAD.order — missing or duplicate order values
        # produce nondeterministic swrl:AtomList order (WR-02).
        for rel_name in ("HAS_BODY", "HAS_HEAD"):
            raw_orders = raw_order_by_rule.get(rule_id, {}).get(rel_name, [])
            if any(o is None for o in raw_orders):
                skipped_rules[rule_id] = (
                    skipped_rules.get(rule_id, "") + f"; null {rel_name}.order"
                ).lstrip("; ")
                continue
            if len(set(raw_orders)) != len(raw_orders):
                skipped_rules[rule_id] = (
                    skipped_rules.get(rule_id, "") + f"; duplicate {rel_name}.order"
                ).lstrip("; ")
                continue
        if rule_id in skipped_rules:
            continue
        bad = sorted({atom_id for _, atom_id in body + head if atom_id in incomplete_atoms})
        if bad:
            skipped_rules[rule_id] = "incomplete atoms: " + ", ".join(bad)

    exported_rules = [rule_id for rule_id in rules if rule_id not in skipped_rules]
    swrl_atom_ids: set[str] = set()
    for rule_id in exported_rules:
        for items in body_head.get(rule_id, {}).values():
            swrl_atom_ids.update(atom_id for _, atom_id in items)

    # --- emit SWRL atoms (only those belonging to a well-formed exported rule) ---
    atom_iri = {atom_id: mint(project, "atom", atom_id) for atom_id in atoms}
    for atom_id in swrl_atom_ids:
        props = atoms[atom_id]
        atom_type = props.get("type", "")
        if atom_type not in ATOM_TYPE_MAP:
            print(f"WARNING: atom {atom_id} has unrecognized type '{atom_type}' -- defaulting to ClassAtom")
        swrl_type, predicate = ATOM_TYPE_MAP.get(atom_type, (SWRL.ClassAtom, SWRL.classPredicate))
        a_iri = atom_iri[atom_id]
        graph.add((a_iri, RDF.type, swrl_type))
        graph.add((a_iri, predicate, refers_to[atom_id]))
        if atom_type == BUILTIN_ATOM_TYPE:
            graph.add((refers_to[atom_id], RDF.type, SWRL.Builtin))

        arg_list = sorted(args_by_atom.get(atom_id, []), key=lambda pair: pair[0])
        for _, term in arg_list:
            if isinstance(term, URIRef):
                graph.add((term, RDF.type, SWRL.Variable))

        if atom_type == BUILTIN_ATOM_TYPE:
            # BuiltinAtom MUST use swrl:arguments (rdf:List) universally --
            # never argument1/2 -- because builtin arity varies (spec
            # #BuiltinAtom and swrl:arguments).
            graph.add((a_iri, SWRL.arguments, make_argument_list(graph, [term for _, term in arg_list])))
        else:
            for pos, term in arg_list:
                if pos == 1:
                    graph.add((a_iri, SWRL.argument1, term))
                elif pos == 2:
                    graph.add((a_iri, SWRL.argument2, term))
                else:
                    print(f"WARNING: non-builtin atom {atom_id} has ARG pos={pos} (>2) -- unmapped")

    # --- emit rules as swrl:Imp with ordered swrl:AtomList body/head ---
    for rule_id in exported_rules:
        props = rules[rule_id]
        r_iri = mint(project, "rule", rule_id)
        graph.add((r_iri, RDF.type, SWRL.Imp))
        graph.add((r_iri, RDFS.label, RDFLiteral(rule_id)))
        # Rule.kind/RuleName/RuleDescription have no SWRL equivalent -- become
        # dg:-namespace annotation properties per the Node Mapping Table.
        if props.get("kind"):
            graph.add((r_iri, DG.kind, RDFLiteral(props["kind"])))
        if props.get("RuleName"):
            graph.add((r_iri, DG.ruleName, RDFLiteral(props["RuleName"])))
        if props.get("RuleDescription"):
            graph.add((r_iri, DG.ruleDescription, RDFLiteral(props["RuleDescription"])))

        edges = body_head.get(rule_id, {})
        for rel, swrl_predicate in (("HAS_BODY", SWRL.body), ("HAS_HEAD", SWRL.head)):
            ordered_items = sorted(edges.get(rel, []), key=lambda pair: pair[0])
            ordered_atoms = [atom_iri[atom_id] for _, atom_id in ordered_items]
            graph.add((r_iri, swrl_predicate, make_atom_list(graph, ordered_atoms)))

    # --- captured-not-dropped: skipped rules/atoms as annotated individuals ---
    for rule_id, reason in skipped_rules.items():
        r_iri = mint(project, "rule", rule_id)
        graph.add((r_iri, RDF.type, DGM.SkippedRule))
        graph.add((r_iri, RDFS.label, RDFLiteral(rule_id)))
        graph.add((r_iri, RDFS.comment, RDFLiteral(
            f"captured by label-scoped export but not mapped to swrl:Imp -- {reason}"
        )))
    for atom_id in atoms:
        if atom_id in swrl_atom_ids:
            continue
        reason = incomplete_atoms.get(atom_id, "belongs to a rule skipped as SWRL-incomplete")
        graph.add((atom_iri[atom_id], RDF.type, DGM.SkippedAtom))
        graph.add((atom_iri[atom_id], RDFS.comment, RDFLiteral(
            f"captured by label-scoped export but excluded from SWRL mapping -- {reason}"
        )))

    return graph


def strip_hermit_unsupported(graph: Graph) -> int:
    """Remove `swrl:Imp` rules that transitively reference a `swrl:BuiltinAtom`.

    HermiT rejects any ontology containing SWRL builtin atoms outright
    ("built-in atoms are not supported yet" -- `java.lang.IllegalArgumentException`),
    and DG's violation pattern is builtin-centric (spec #SWRL Builtin
    Exclusion from Reasoner Input). Mutates `graph` in place -- callers
    building reasoner input should operate on a copy; the canonical Turtle
    export (this module's `build_graph` output) keeps the full mapping
    unfiltered. Returns the number of `swrl:Imp` individuals removed.
    """
    builtin_atoms = set(graph.subjects(RDF.type, SWRL.BuiltinAtom))

    def list_cells(head_node) -> tuple[list, list]:
        cells: list = []
        items: list = []
        node = head_node
        while node is not None and node != RDF.nil:
            cells.append(node)
            items.append(graph.value(node, RDF.first))
            node = graph.value(node, RDF.rest)
        return cells, items

    removed = 0
    for imp in list(graph.subjects(RDF.type, SWRL.Imp)):
        list_cell_nodes: list = []
        atoms_referenced: list = []
        for predicate in (SWRL.body, SWRL.head):
            for list_head in graph.objects(imp, predicate):
                cells, items = list_cells(list_head)
                list_cell_nodes.extend(cells)
                atoms_referenced.extend(item for item in items if item is not None)

        if not any(atom in builtin_atoms for atom in atoms_referenced):
            continue

        for atom in set(atoms_referenced):
            for arg_list_head in graph.objects(atom, SWRL.arguments):
                arg_cells, _ = list_cells(arg_list_head)
                for cell in arg_cells:
                    graph.remove((cell, None, None))
            graph.remove((atom, None, None))
        for cell in list_cell_nodes:
            graph.remove((cell, None, None))
        graph.remove((imp, None, None))
        removed += 1

    # prune now-unreferenced swrl:Variable / swrl:Builtin declarations
    used_terms = (
        set(graph.objects(None, SWRL.argument1))
        | set(graph.objects(None, SWRL.argument2))
        | set(graph.objects(None, RDF.first))
    )
    for variable in list(graph.subjects(RDF.type, SWRL.Variable)):
        if variable not in used_terms:
            graph.remove((variable, None, None))
    used_builtins = set(graph.objects(None, SWRL.builtin))
    for builtin in list(graph.subjects(RDF.type, SWRL.Builtin)):
        if builtin not in used_builtins:
            graph.remove((builtin, RDF.type, SWRL.Builtin))

    return removed


def main() -> None:
    """CLI: connect to live Neo4j via env vars, serialize Turtle to stdout or a file.

    Usage: python ontology_export.py [project] [out_path.ttl]
    """
    from neo4j import GraphDatabase  # lazy import -- build_graph itself needs no neo4j dependency

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")

    args = sys.argv[1:]
    project = args[0] if args else os.getenv("PROJECT", "v8-ui-smoke")
    out_path = Path(args[1]) if len(args) > 1 else None

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            graph = build_graph(session, project)
    finally:
        driver.close()

    turtle_text = graph.serialize(format="turtle")
    if out_path:
        out_path.write_text(turtle_text, encoding="utf-8")
        print(f"Wrote {out_path} ({len(graph)} triples)")
    else:
        print(turtle_text)


if __name__ == "__main__":
    main()
