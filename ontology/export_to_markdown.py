"""
Export DesignGrammar.owl to a NotebookLM-friendly markdown file.

Produces ontology/DesignGrammar.md — a human-readable, well-structured
rendering of every class, property, enum, and example instance, with
characteristics, domains, ranges, comments, and parent links inlined.

Run from project root:
    python ontology/export_to_markdown.py
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Optional

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dg": "http://example.org/design-grammar#",
    "dgm": "http://example.org/design-grammar/metagraph#",
    "dgv": "http://example.org/design-grammar/validation#",
    "dgk": "http://example.org/design-grammar/knowledge#",
}

PREFIX_BY_NS = {v: k for k, v in NS.items()}

# Layer assignment by prefix
LAYER_NAMES = {
    "dg": "0. Core / Cross-cutting",
    "dgm": "2. Metagraph (SWRL rule structure)",
    "dgv": "3. ValidationGraph (validation runs, design state, integration)",
    "dgk": "4. KnowledgeGraph (project notes, tags, sessions)",
}


def localname(iri: str) -> str:
    """Return prefix:localname for a full IRI, or the iri itself if unknown."""
    for ns_uri, prefix in PREFIX_BY_NS.items():
        if iri.startswith(ns_uri):
            return f"{prefix}:{iri[len(ns_uri):]}"
    return iri


def prefix_of(iri: str) -> str:
    for ns_uri, prefix in PREFIX_BY_NS.items():
        if iri.startswith(ns_uri):
            return prefix
    return ""


def get_attr(elem, ns: str, name: str) -> Optional[str]:
    return elem.get(f"{{{NS[ns]}}}{name}")


def get_about(elem) -> Optional[str]:
    return get_attr(elem, "rdf", "about")


def get_resource(elem) -> Optional[str]:
    return get_attr(elem, "rdf", "resource")


def get_text(elem, ns: str, name: str) -> Optional[str]:
    child = elem.find(f"{{{NS[ns]}}}{name}")
    if child is None:
        return None
    text = child.text
    return text.strip() if text else None


def collect_texts(elem, ns: str, name: str) -> list[str]:
    return [c.text.strip() for c in elem.findall(f"{{{NS[ns]}}}{name}") if c.text]


def collect_resources(elem, ns: str, name: str) -> list[str]:
    return [
        r for c in elem.findall(f"{{{NS[ns]}}}{name}")
        if (r := get_resource(c))
    ]


def collect_types(elem) -> list[str]:
    """Return all rdf:type resources on this element."""
    return collect_resources(elem, "rdf", "type")


def is_inline_class_union(class_elem) -> Optional[list[str]]:
    """If an owl:Class node has owl:unionOf as a Collection, return member IRIs."""
    union = class_elem.find(f"{{{NS['owl']}}}unionOf")
    if union is None:
        return None
    members = []
    for sub in union.findall(f"{{{NS['owl']}}}Class"):
        if (r := get_about(sub)) or (r := get_resource(sub)):
            members.append(r)
    return members


def parse_domain_or_range(parent_elem, kind: str) -> str:
    """kind = 'domain' or 'range'. Returns formatted text."""
    domain_elem = parent_elem.find(f"{{{NS['rdfs']}}}{kind}")
    if domain_elem is None:
        return "—"
    # Simple resource form
    if (r := get_resource(domain_elem)):
        return localname(r)
    # Union form
    cls = domain_elem.find(f"{{{NS['owl']}}}Class")
    if cls is not None:
        members = is_inline_class_union(cls)
        if members:
            return " ∪ ".join(localname(m) for m in members)
    return "(complex)"


def parse_characteristics(types: list[str]) -> list[str]:
    """Return short labels for OWL property characteristics."""
    chars = []
    char_map = {
        f"{NS['owl']}FunctionalProperty": "Functional",
        f"{NS['owl']}InverseFunctionalProperty": "InverseFunctional",
        f"{NS['owl']}TransitiveProperty": "Transitive",
        f"{NS['owl']}SymmetricProperty": "Symmetric",
        f"{NS['owl']}AsymmetricProperty": "Asymmetric",
        f"{NS['owl']}ReflexiveProperty": "Reflexive",
        f"{NS['owl']}IrreflexiveProperty": "Irreflexive",
    }
    for t in types:
        if t in char_map:
            chars.append(char_map[t])
    return chars


def parse_one_of(class_elem) -> list[str]:
    """If a Class has owl:equivalentClass with owl:oneOf, return enum member IRIs."""
    for eq in class_elem.findall(f"{{{NS['owl']}}}equivalentClass"):
        inner_cls = eq.find(f"{{{NS['owl']}}}Class")
        if inner_cls is None:
            continue
        one_of = inner_cls.find(f"{{{NS['owl']}}}oneOf")
        if one_of is None:
            continue
        members = []
        for ind in one_of.findall(f"{{{NS['owl']}}}NamedIndividual"):
            r = get_about(ind) or get_resource(ind)
            if r:
                members.append(r)
        return members
    return []


def parse_subclass_restrictions(class_elem) -> list[str]:
    """Find SubClassOf restrictions (e.g. hasIdRef max 0)."""
    out = []
    for sc in class_elem.findall(f"{{{NS['rdfs']}}}subClassOf"):
        r = get_resource(sc)
        if r:
            continue  # plain superclass, handled separately
        # restriction form
        restriction = sc.find(f"{{{NS['owl']}}}Restriction")
        if restriction is None:
            continue
        on_prop = restriction.find(f"{{{NS['owl']}}}onProperty")
        prop_iri = get_resource(on_prop) if on_prop is not None else None
        on_class = restriction.find(f"{{{NS['owl']}}}onClass")
        on_class_iri = get_resource(on_class) if on_class is not None else None
        # find cardinality assertion
        for tag, kind in [
            ("maxQualifiedCardinality", "max"),
            ("minQualifiedCardinality", "min"),
            ("qualifiedCardinality", "exactly"),
            ("maxCardinality", "max"),
            ("minCardinality", "min"),
            ("cardinality", "exactly"),
        ]:
            card = restriction.find(f"{{{NS['owl']}}}{tag}")
            if card is not None and prop_iri:
                desc = f"{localname(prop_iri)} {kind} {card.text}"
                if on_class_iri:
                    desc += f" of {localname(on_class_iri)}"
                out.append(desc)
                break
    return out


def parse_disjoint_groups(root) -> list[list[str]]:
    """Find AllDisjointClasses axioms."""
    groups = []
    for desc in root.findall(f"{{{NS['rdf']}}}Description"):
        types = collect_types(desc)
        if f"{NS['owl']}AllDisjointClasses" not in types:
            continue
        members_elem = desc.find(f"{{{NS['owl']}}}members")
        if members_elem is None:
            continue
        members = []
        for cls in members_elem.findall(f"{{{NS['owl']}}}Class"):
            r = get_about(cls) or get_resource(cls)
            if r:
                members.append(r)
        if members:
            groups.append(members)
    return groups


def parse_individual_properties(ind_elem) -> dict[str, list[str]]:
    """Return {property_localname: [values]} for a NamedIndividual."""
    props = defaultdict(list)
    for child in ind_elem:
        tag = child.tag
        if tag in {
            f"{{{NS['rdf']}}}type",
            f"{{{NS['rdfs']}}}label",
            f"{{{NS['rdfs']}}}comment",
        }:
            continue
        # Property name
        prop_iri = tag.replace("{", "").replace("}", "#")
        # Convert tag to prefix:localname
        for ns_uri, prefix in PREFIX_BY_NS.items():
            if tag.startswith(f"{{{ns_uri}}}"):
                prop_local = f"{prefix}:{tag[len(ns_uri) + 2:]}"
                break
        else:
            prop_local = tag
        if (r := get_resource(child)):
            props[prop_local].append(localname(r))
        elif child.text:
            value = child.text.strip()
            if value:
                props[prop_local].append(f'"{value}"')
    return props


# ---------------------------------------------------------------------------


def main():
    project_root = Path(__file__).resolve().parent.parent
    owl_path = project_root / "ontology" / "DesignGrammar.owl"
    md_path = project_root / "ontology" / "DesignGrammar.md"

    tree = ET.parse(owl_path)
    root = tree.getroot()

    # Index all named elements by IRI
    classes: dict[str, ET.Element] = {}
    obj_props: dict[str, ET.Element] = {}
    dt_props: dict[str, ET.Element] = {}
    ann_props: dict[str, ET.Element] = {}
    individuals: dict[str, ET.Element] = {}

    for child in root:
        tag = child.tag
        about = get_about(child)
        if not about:
            continue
        if tag == f"{{{NS['owl']}}}Class":
            classes[about] = child
        elif tag == f"{{{NS['owl']}}}ObjectProperty":
            obj_props[about] = child
        elif tag == f"{{{NS['owl']}}}DatatypeProperty":
            dt_props[about] = child
        elif tag == f"{{{NS['owl']}}}AnnotationProperty":
            ann_props[about] = child
        elif tag == f"{{{NS['owl']}}}NamedIndividual":
            individuals[about] = child

    # Find ontology header
    onto_elem = root.find(f"{{{NS['owl']}}}Ontology")
    onto_comment = get_text(onto_elem, "rdfs", "comment") if onto_elem is not None else ""
    version_info = get_text(onto_elem, "owl", "versionInfo") if onto_elem is not None else "?"

    # Bucket by layer
    def bucket(iri: str) -> str:
        return prefix_of(iri)

    classes_by_layer = defaultdict(list)
    for iri in classes:
        classes_by_layer[bucket(iri)].append(iri)
    op_by_layer = defaultdict(list)
    for iri in obj_props:
        op_by_layer[bucket(iri)].append(iri)
    dp_by_layer = defaultdict(list)
    for iri in dt_props:
        dp_by_layer[bucket(iri)].append(iri)
    ind_by_layer = defaultdict(list)
    for iri in individuals:
        ind_by_layer[bucket(iri)].append(iri)

    for d in (classes_by_layer, op_by_layer, dp_by_layer, ind_by_layer):
        for k in d:
            d[k].sort()

    disjoint_groups = parse_disjoint_groups(root)

    # ------------- Render markdown -------------
    out = []

    out.append("# Design Grammar System — Ontology Reference")
    out.append("")
    out.append(f"**Version:** {version_info}  ")
    out.append(f"**Source:** `[DesignGrammar.owl](DesignGrammar.owl)`  ")
    out.append("**Format:** Human-readable export for NotebookLM ingestion (mind maps, audio overviews, Q&A).  ")
    out.append("")
    out.append("> This document is a one-to-one rendering of the OWL ontology in plain markdown. Every class, property, enum, axiom, and example instance is listed with its label, comment, parent classes/properties, OWL characteristics, domain, range, and disjointness relations. Use the source OWL file for any reasoner-bound work; use this document for human review and AI ingestion.")
    out.append("")

    if onto_comment:
        out.append("## Ontology overview")
        out.append("")
        for line in onto_comment.split("\n"):
            line = line.strip()
            if line:
                out.append(f"> {line}")
        out.append("")

    # Table of contents
    out.append("## Contents")
    out.append("")
    out.append("- [Graph layers](#graph-layers)")
    out.append("- [Classes by layer](#classes-by-layer)")
    out.append("- [Object properties by layer](#object-properties-by-layer)")
    out.append("- [Datatype properties by layer](#datatype-properties-by-layer)")
    out.append("- [Enumerated value classes (closed sets)](#enumerated-value-classes-closed-sets)")
    out.append("- [Disjointness axioms](#disjointness-axioms)")
    out.append("- [Example instances (ABox)](#example-instances-abox)")
    out.append("- [Namespace reference](#namespace-reference)")
    out.append("")

    # Layer overview
    out.append("## Graph layers")
    out.append("")
    out.append("The DG ontology partitions its content into four logical layers, each tagged with a `dg:graph` annotation on every class. All four layers persist into a single Neo4j database, isolated by the `dg:project` annotation.")
    out.append("")
    out.append("| Prefix | Namespace | Layer | Role |")
    out.append("|---|---|---|---|")
    out.append("| `dg` | `http://example.org/design-grammar#` | Cross-cutting + OntoGraph (dynamic domain ontology meta-schema) | Reifies OWL Class/DatatypeProperty/ObjectProperty as Neo4j nodes for query-ability |")
    out.append("| `dgm` | `http://example.org/design-grammar/metagraph#` | Metagraph | SWRL rule structure: Rule, Atom subtypes, Variable subtypes, Literal, Builtin |")
    out.append("| `dgv` | `http://example.org/design-grammar/validation#` | ValidationGraph | Validation runs, entity results, design state composition, integration config |")
    out.append("| `dgk` | `http://example.org/design-grammar/knowledge#` | KnowledgeGraph | Project notes, tags, knowledge sessions |")
    out.append("")

    # Classes by layer
    out.append("## Classes by layer")
    out.append("")

    for prefix in ["dg", "dgm", "dgv", "dgk"]:
        if not classes_by_layer.get(prefix):
            continue
        layer = LAYER_NAMES.get(prefix, prefix)
        out.append(f"### Layer {prefix} — {layer}")
        out.append("")
        for iri in classes_by_layer[prefix]:
            elem = classes[iri]
            label = get_text(elem, "rdfs", "label") or localname(iri)
            comment = get_text(elem, "rdfs", "comment") or ""
            parents = collect_resources(elem, "rdfs", "subClassOf")
            restrictions = parse_subclass_restrictions(elem)
            one_of = parse_one_of(elem)
            graph = get_text(elem, "dg", "graph")

            out.append(f"#### `{localname(iri)}` — {label}")
            out.append("")
            if comment:
                out.append(comment)
                out.append("")
            if parents:
                parent_list = ", ".join(f"`{localname(p)}`" for p in parents)
                out.append(f"- **Parent class(es):** {parent_list}")
            if restrictions:
                out.append(f"- **Restrictions:** {'; '.join(restrictions)}")
            if one_of:
                values = ", ".join(f"`{localname(m)}`" for m in one_of)
                out.append(f"- **Closed enum (owl:oneOf):** {values}")
            if graph:
                out.append(f"- **Graph layer annotation:** {graph}")
            out.append("")

    # Object properties by layer
    out.append("## Object properties by layer")
    out.append("")

    for prefix in ["dg", "dgm", "dgv", "dgk"]:
        if not op_by_layer.get(prefix):
            continue
        layer = LAYER_NAMES.get(prefix, prefix)
        out.append(f"### Layer {prefix} — {layer}")
        out.append("")
        for iri in op_by_layer[prefix]:
            elem = obj_props[iri]
            label = get_text(elem, "rdfs", "label") or localname(iri)
            comment = get_text(elem, "rdfs", "comment") or ""
            types = collect_types(elem)
            chars = parse_characteristics(types)
            domain = parse_domain_or_range(elem, "domain")
            range_ = parse_domain_or_range(elem, "range")
            inverse_of = collect_resources(elem, "owl", "inverseOf")
            disjoint_with = collect_resources(elem, "owl", "propertyDisjointWith")

            out.append(f"#### `{localname(iri)}` — {label}")
            out.append("")
            if comment:
                out.append(comment)
                out.append("")
            out.append(f"- **Domain:** `{domain}`")
            out.append(f"- **Range:** `{range_}`")
            if chars:
                out.append(f"- **Characteristics:** {', '.join(chars)}")
            if inverse_of:
                out.append(f"- **Inverse of:** {', '.join(f'`{localname(p)}`' for p in inverse_of)}")
            if disjoint_with:
                out.append(f"- **Disjoint with (property):** {', '.join(f'`{localname(p)}`' for p in disjoint_with)}")
            out.append("")

    # Datatype properties by layer
    out.append("## Datatype properties by layer")
    out.append("")

    for prefix in ["dg", "dgm", "dgv", "dgk"]:
        if not dp_by_layer.get(prefix):
            continue
        layer = LAYER_NAMES.get(prefix, prefix)
        out.append(f"### Layer {prefix} — {layer}")
        out.append("")
        out.append("| Property | Label | Domain | Range | Characteristics | Description |")
        out.append("|---|---|---|---|---|---|")
        for iri in dp_by_layer[prefix]:
            elem = dt_props[iri]
            label = get_text(elem, "rdfs", "label") or localname(iri)
            comment = (get_text(elem, "rdfs", "comment") or "").replace("|", "\\|").replace("\n", " ")
            types = collect_types(elem)
            chars = parse_characteristics(types)
            domain = parse_domain_or_range(elem, "domain")
            range_ = parse_domain_or_range(elem, "range")
            chars_str = ", ".join(chars) if chars else "—"
            out.append(
                f"| `{localname(iri)}` | {label} | `{domain}` | `{range_}` | {chars_str} | {comment} |"
            )
        out.append("")

    # Enum closed sets
    out.append("## Enumerated value classes (closed sets)")
    out.append("")
    out.append("Six enum classes are closed via `owl:oneOf` — their value space is fixed. Any individual asserted as a member that is not one of the listed individuals triggers an inconsistency.")
    out.append("")
    enum_classes = []
    for prefix in ["dgm", "dgv"]:
        for iri in classes_by_layer.get(prefix, []):
            members = parse_one_of(classes[iri])
            if members:
                enum_classes.append((iri, members))

    for iri, members in enum_classes:
        elem = classes[iri]
        label = get_text(elem, "rdfs", "label") or localname(iri)
        comment = get_text(elem, "rdfs", "comment") or ""
        out.append(f"### `{localname(iri)}` — {label}")
        out.append("")
        if comment:
            out.append(comment)
            out.append("")
        out.append("**Allowed values:**")
        out.append("")
        for m in members:
            ind_elem = individuals.get(m)
            if ind_elem is None:
                out.append(f"- `{localname(m)}`")
                continue
            ind_label = get_text(ind_elem, "rdfs", "label") or localname(m)
            ind_comment = get_text(ind_elem, "rdfs", "comment") or ""
            line = f"- `{localname(m)}` — **{ind_label}**"
            if ind_comment:
                line += f": {ind_comment}"
            out.append(line)
        out.append("")

    # Disjointness axioms
    out.append("## Disjointness axioms")
    out.append("")
    out.append("Each group below is `owl:AllDisjointClasses` — no individual may simultaneously belong to two classes in the same group.")
    out.append("")
    for i, group in enumerate(disjoint_groups, 1):
        members = ", ".join(f"`{localname(m)}`" for m in group)
        out.append(f"{i}. {members}")
    out.append("")

    # Example instances
    out.append("## Example instances (ABox)")
    out.append("")
    out.append("The ontology ships with a representative ABox of named individuals demonstrating each class and binding pattern. Listed below by layer.")
    out.append("")
    for prefix in ["dg", "dgm", "dgv", "dgk"]:
        iris = ind_by_layer.get(prefix, [])
        if not iris:
            continue
        layer = LAYER_NAMES.get(prefix, prefix)
        out.append(f"### Layer {prefix} — {layer}")
        out.append("")
        # Group by rdf:type
        by_type = defaultdict(list)
        for iri in iris:
            elem = individuals[iri]
            types = collect_types(elem)
            type_label = ", ".join(localname(t) for t in types) if types else "(untyped)"
            by_type[type_label].append((iri, elem))

        for type_label in sorted(by_type.keys()):
            items = by_type[type_label]
            out.append(f"#### Type: `{type_label}` ({len(items)} individual{'s' if len(items) != 1 else ''})")
            out.append("")
            for iri, elem in items:
                label = get_text(elem, "rdfs", "label") or localname(iri)
                comment = get_text(elem, "rdfs", "comment") or ""
                props = parse_individual_properties(elem)
                out.append(f"- **`{localname(iri)}`** — {label}")
                if comment:
                    out.append(f"  - _Comment:_ {comment}")
                for prop_name, values in sorted(props.items()):
                    val_str = ", ".join(values)
                    out.append(f"  - `{prop_name}`: {val_str}")
            out.append("")

    # Namespace reference
    out.append("## Namespace reference")
    out.append("")
    out.append("```")
    out.append("dg   = http://example.org/design-grammar#")
    out.append("dgm  = http://example.org/design-grammar/metagraph#")
    out.append("dgv  = http://example.org/design-grammar/validation#")
    out.append("dgk  = http://example.org/design-grammar/knowledge#")
    out.append("owl  = http://www.w3.org/2002/07/owl#")
    out.append("rdf  = http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    out.append("rdfs = http://www.w3.org/2000/01/rdf-schema#")
    out.append("xsd  = http://www.w3.org/2001/XMLSchema#")
    out.append("```")
    out.append("")

    out.append("---")
    out.append("")
    out.append(f"*Auto-generated from `[DesignGrammar.owl](DesignGrammar.owl)` v{version_info}. Counts: "
               f"{sum(len(v) for v in classes_by_layer.values())} classes, "
               f"{sum(len(v) for v in op_by_layer.values())} object properties, "
               f"{sum(len(v) for v in dp_by_layer.values())} datatype properties, "
               f"{sum(len(v) for v in ind_by_layer.values())} named individuals, "
               f"{len(disjoint_groups)} disjointness axioms.*")

    md_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {md_path} ({md_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
