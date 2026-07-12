"""Spike part (b): hybrid export + seeded TBox contradiction -> expect unsatisfiable.

Loads output/hybrid_export.ttl (static DesignGrammar-V7.owl TBox UNION the live
v8-ui-smoke export PLUS curated `ex:Door owl:disjointWith ex:Window` PLUS the
seeded contradiction `ex:SlidingDoor rdfs:subClassOf ex:Door, ex:Window`) and
runs sync_reasoner() (HermiT). Expected result: ex:SlidingDoor is reported
unsatisfiable/inconsistent — the non-trivial result the naive export missed,
because SlidingDoor is forced under two disjoint parents.

The contradiction is PURE TBox (Pitfall 4): no individuals, no ABox — matching
the milestone's rule-authoring-time reasoning scope.

Evidence written to output/hybrid_result.txt for 820-DECISION.md.
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from owlready2 import get_ontology, sync_reasoner

from export import strip_hermit_unsupported

OUT_DIR = Path(__file__).resolve().parent / "output"
TTL = OUT_DIR / "hybrid_export.ttl"
NT = OUT_DIR / "hybrid_export.nt"
RESULT = OUT_DIR / "hybrid_result.txt"


def inconsistent_of(onto) -> list:
    try:
        return list(onto.inconsistent_classes())
    except AttributeError:
        from owlready2 import default_world
        return list(default_world.inconsistent_classes())


def main() -> None:
    # owlready2 has no Turtle parser — round-trip through rdflib to NTriples.
    # HermiT rejects SWRL builtin atoms — strip them from the reasoner input.
    g = Graph()
    g.parse(TTL, format="turtle")
    stripped = strip_hermit_unsupported(g)
    g.serialize(destination=str(NT), format="nt", encoding="utf-8")

    onto = get_ontology(NT.as_uri()).load()
    with onto:
        sync_reasoner()  # HermiT (bundled JAR; requires JRE 17)

    inconsistent = inconsistent_of(onto)
    iris = [getattr(c, "iri", str(c)) for c in inconsistent]
    hit = any("SlidingDoor" in i for i in iris)
    lines = [
        "Spike part (b) — hybrid: static DesignGrammar-V7.owl TBox + live v8-ui-smoke export",
        "                 + curated ex:Door owl:disjointWith ex:Window",
        "                 + seeded ex:SlidingDoor rdfs:subClassOf ex:Door, ex:Window",
        f"source: {TTL.name} (converted to {NT.name} for owlready2)",
        "reasoner: HermiT via owlready2 sync_reasoner()",
        f"builtin-using SWRL rules stripped from reasoner input: {stripped} "
        "(HermiT: 'built-in atoms are not supported yet'; TBox axioms untouched)",
        "",
        f"Inconsistent classes: {inconsistent!r}",
        f"IRIs: {iris!r}",
        f"Count: {len(inconsistent)}",
        "",
    ]
    if hit:
        lines.append(
            "RESULT: ex:SlidingDoor is unsatisfiable — HermiT caught the seeded "
            "TBox contradiction that the naive export could not express. This is "
            "the non-trivial answer the hybrid axiom scoping (static TBox + live "
            "export + curated disjointness) makes possible."
        )
        lines.append("ASSERTION (SlidingDoor unsatisfiable): PASS")
    else:
        lines.append("ASSERTION (SlidingDoor unsatisfiable): FAIL — contradiction not detected")
    RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
