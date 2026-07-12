"""Spike part (a): naive flat export -> HermiT -> expect trivially 'consistent'.

Loads output/naive_export.ttl (live v8-ui-smoke OntoGraph + Metagraph only, no
static TBox, no curated axioms) and runs Owlready2's sync_reasoner() (HermiT —
the data-service/reasoner.py default engine id). Expected result: an EMPTY
inconsistent-classes list — the documented trivial-consistency false positive:
the naive export contains no axioms connecting the flat domain terms, so
nothing can possibly be unsatisfiable.

Owlready2 cannot parse Turtle (RDF/XML, OWL/XML, NTriples only), so the
canonical .ttl evidence file is converted to .nt via rdflib before loading.

Evidence written to output/naive_result.txt for 820-DECISION.md.
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from owlready2 import get_ontology, sync_reasoner

from export import strip_hermit_unsupported

OUT_DIR = Path(__file__).resolve().parent / "output"
TTL = OUT_DIR / "naive_export.ttl"
NT = OUT_DIR / "naive_export.nt"
RESULT = OUT_DIR / "naive_result.txt"


def inconsistent_of(onto) -> list:
    try:
        return list(onto.inconsistent_classes())
    except AttributeError:  # older/newer API surface: fall back to the world
        from owlready2 import default_world
        return list(default_world.inconsistent_classes())


def main() -> None:
    # owlready2 has no Turtle parser — round-trip through rdflib to NTriples.
    # HermiT rejects SWRL builtin atoms outright, so builtin-using rules are
    # stripped from the reasoner input only (the .ttl evidence keeps them all).
    g = Graph()
    g.parse(TTL, format="turtle")
    stripped = strip_hermit_unsupported(g)
    g.serialize(destination=str(NT), format="nt", encoding="utf-8")

    onto = get_ontology(NT.as_uri()).load()
    with onto:
        sync_reasoner()  # HermiT (bundled JAR; requires JRE 17)

    inconsistent = inconsistent_of(onto)
    lines = [
        "Spike part (a) — naive flat export of live v8-ui-smoke OntoGraph/Metagraph",
        f"source: {TTL.name} (converted to {NT.name} for owlready2)",
        "reasoner: HermiT via owlready2 sync_reasoner()",
        f"builtin-using SWRL rules stripped from reasoner input: {stripped} "
        "(HermiT: 'built-in atoms are not supported yet'; TBox axioms untouched)",
        "",
        f"Inconsistent classes: {inconsistent!r}",
        f"Count: {len(inconsistent)}",
        "",
    ]
    if not inconsistent:
        lines.append(
            "RESULT: zero inconsistent classes — the naive export reasons as "
            "trivially 'consistent'. This is the documented FALSE POSITIVE: the "
            "flat export carries no subClassOf/domain/range/disjointWith axioms, "
            "so no class can be unsatisfiable regardless of the rules' content."
        )
        lines.append("ASSERTION (expected empty): PASS")
    else:
        lines.append("ASSERTION (expected empty): FAIL — naive export was NOT trivially consistent")
    RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
