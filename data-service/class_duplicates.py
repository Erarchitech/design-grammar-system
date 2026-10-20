"""Near-duplicate classes and data properties of a project (Phase 1303-15, owner 2026-10-20).

HermiT cannot see that two differently named classes mean the same thing: in the open world they simply coexist.
After four opening rules the project held Opening (the MEP opening box) next to WallOpening, and a rule property
hasMinHostOpeningClearanceMm next to the vocabulary's hasMinOpeningClearanceMm. This module finds such pairs
deterministically from their names (camel-case tokens, simple singularisation, a small synonym table) and lets a
person settle each pair:

* ``use_existing`` -> the new entity is merged into the existing one (relationships moved, rule SWRL rewritten);
* ``keep_new`` / ``distinct`` -> ``(a)-[:DISTINCT_FROM]->(b)``, exported for classes as owl:disjointWith.

A settled pair is not reported again. Nothing is merged or deleted automatically.
"""

from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Iterable

# Words that name the same thing in this domain. Kept small and explicit: a wrong synonym is a false alarm the
# user dismisses once, a missing one is a duplicate nobody sees.
SYNONYMS: tuple[frozenset[str], ...] = (
    frozenset({"opening", "hole", "penetration", "aperture", "void", "sleeve", "cutout"}),
    frozenset({"beam", "girder", "joist", "framing"}),
    frozenset({"column", "pillar", "pier", "post"}),
    frozenset({"floor", "slab", "deck"}),
    frozenset({"wall", "partition"}),
    frozenset({"door", "doorway"}),
    frozenset({"window", "glazing"}),
)
# Tokens that qualify a property without changing what it measures.
PROPERTY_FILLERS = frozenset({"has", "host", "value", "the", "of", "to", "nearest", "any", "total"})
UNIT_TOKENS = frozenset({"mm", "m", "cm", "deg", "count", "ratio", "pct"})

_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def tokens(name: str) -> list[str]:
    local = (name or "").rsplit("#", 1)[-1].rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    out = []
    for t in _CAMEL.findall(local):
        t = t.lower()
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        out.append(t)
    return out


def _canon(token: str) -> str:
    for group in SYNONYMS:
        if token in group:
            return min(group)
    return token


# A trailing generic word names the carrier, not the concept: OpeningBox is an opening.
GENERIC_HEADS = frozenset({"box", "element", "item", "object", "instance", "family", "type", "family"})


def _class_tokens(name: str) -> list[str]:
    raw = tokens(name)
    while len(raw) > 1 and raw[-1] in GENERIC_HEADS:
        raw = raw[:-1]
    return raw


def class_reason(a: str, b: str) -> str | None:
    """A pair is a candidate only when both names have the same head noun (last word, synonyms folded): Opening /
    WallOpening / OpeningBox are all openings; Wall / WallOpening and Facade / FacadeModule are not."""
    ra, rb = _class_tokens(a), _class_tokens(b)
    ta, tb = [_canon(t) for t in ra], [_canon(t) for t in rb]
    if not ta or not tb or ta[-1] != tb[-1]:
        return None
    if ta == tb:
        return "same name" if ra == rb and tokens(a) == tokens(b) else "same concept, different wording"
    extra = sorted(set(ra) ^ set(rb))
    if set(ta) <= set(tb) or set(tb) <= set(ta):
        return f"both are a kind of '{ra[-1]}'; one adds {', '.join(extra)}"
    if len(set(ta) ^ set(tb)) <= 2:
        return f"both are a kind of '{ra[-1]}' ({', '.join(extra)})"
    return None


def property_reason(a: str, b: str) -> str | None:
    ta = [_canon(t) for t in tokens(a) if t not in PROPERTY_FILLERS]
    tb = [_canon(t) for t in tokens(b) if t not in PROPERTY_FILLERS]
    if not ta or not tb or ta == tb and tokens(a) == tokens(b):
        return None
    if ta == tb:
        return "same measure, wording differs"
    unit_a = [t for t in ta if t in UNIT_TOKENS]
    unit_b = [t for t in tb if t in UNIT_TOKENS]
    if unit_a == unit_b and len(set(ta) ^ set(tb)) <= 1 and len(set(ta) & set(tb)) >= 2:
        return "differs by one qualifier"
    return None


def candidates(classes: Iterable[dict], properties: Iterable[dict],
               resolved: Iterable[tuple[str, str]] = ()) -> list[dict[str, Any]]:
    """Pairs worth a decision. ``classes``/``properties``: {iri, label}; ``resolved``: settled (iri, iri) pairs."""
    settled = {frozenset(p) for p in resolved}
    out: list[dict[str, Any]] = []
    for kind, items, reason_of in (("Class", classes, class_reason), ("DatatypeProperty", properties, property_reason)):
        items = sorted({(i["iri"], i.get("label") or i["iri"]) for i in items if i.get("iri")})
        for (ia, la), (ib, lb) in combinations(items, 2):
            if frozenset((ia, ib)) in settled:
                continue
            reason = reason_of(la, lb)
            if reason:
                out.append({"kind": kind, "a": {"iri": ia, "label": la}, "b": {"iri": ib, "label": lb},
                            "reason": reason})
    return out


LOAD_QUERY = (
    "MATCH (n {project:$project}) WHERE n:Class OR n:DatatypeProperty "
    "RETURN labels(n)[0] AS kind, n.iri AS iri, coalesce(n.label, n.SWRL_label, n.iri) AS label"
)
RESOLVED_QUERY = (
    "MATCH (a {project:$project})-[:DISTINCT_FROM]->(b {project:$project}) RETURN a.iri AS a, b.iri AS b"
)


def snapshot(session: Any, project: str) -> list[str]:
    """The class and property iris a project has now (taken before an ingest starts)."""
    return sorted({r["iri"] for r in session.run(LOAD_QUERY, project=project).data() if r.get("iri")})


def find(session: Any, project: str, new_iris: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Open candidate pairs. With ``new_iris`` only pairs that involve at least one of them, with the new entity
    as ``a`` and the one it resembles as ``b`` (the ingest question: use ``b`` instead of ``a``?)."""
    rows = session.run(LOAD_QUERY, project=project).data()
    resolved = [(r["a"], r["b"]) for r in session.run(RESOLVED_QUERY, project=project).data()]
    found = candidates([r for r in rows if r["kind"] == "Class"],
                       [r for r in rows if r["kind"] == "DatatypeProperty"], resolved)
    if new_iris is None:
        return found
    new = set(new_iris)
    out = []
    for c in found:
        a_new, b_new = c["a"]["iri"] in new, c["b"]["iri"] in new
        if not (a_new or b_new):
            continue
        if b_new and not a_new:
            c = {**c, "a": c["b"], "b": c["a"]}
        out.append({**c, "existing": not (a_new and b_new)})
    return out


DISTINCT_QUERY = (
    "MATCH (a {project:$project, iri:$a}), (b {project:$project, iri:$b}) "
    "WHERE labels(a)[0] = labels(b)[0] AND (a:Class OR a:DatatypeProperty) "
    "MERGE (a)-[r:DISTINCT_FROM]->(b) SET r.decidedBy = $actor, r.decidedAt = $at RETURN count(r) AS n"
)
_REL_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def merge(session: Any, project: str, drop: str, keep: str) -> dict[str, Any]:
    """Operator chose the existing entity: every relationship of ``drop`` moves to ``keep`` (same type, direction
    and properties), the rules' SWRL text and atom labels are rewritten to the kept name, and ``drop`` is deleted.
    Both must be of the same kind in the project. No APOC: relationship types come from the graph and are checked
    against an identifier pattern before they are written into the statement."""
    pair = session.run(
        "MATCH (d {project:$project, iri:$drop}), (k {project:$project, iri:$keep}) "
        "WHERE labels(d)[0] = labels(k)[0] AND (d:Class OR d:DatatypeProperty) AND d <> k "
        "RETURN labels(d)[0] AS kind, coalesce(d.label, d.SWRL_label, d.iri) AS dropLabel, "
        "coalesce(k.label, k.SWRL_label, k.iri) AS keepLabel",
        project=project, drop=drop, keep=keep).single()
    if pair is None:
        return {"merged": False}
    rels = session.run(
        "MATCH (d {project:$project, iri:$drop})-[r]-(o) "
        "RETURN type(r) AS type, startNode(r) = d AS outgoing, elementId(o) AS other, properties(r) AS props",
        project=project, drop=drop).data()
    moved = 0
    for rel in rels:
        if not _REL_TYPE.match(rel["type"]):
            raise ValueError(f"unexpected relationship type {rel['type']!r}")
        pattern = "(k)-[r:%s]->(o)" if rel["outgoing"] else "(o)-[r:%s]->(k)"
        session.run(
            "MATCH (k {project:$project, iri:$keep}), (o) WHERE elementId(o) = $other "
            f"MERGE {pattern % rel['type']} SET r += $props",
            project=project, keep=keep, other=rel["other"], props=rel["props"] or {}).consume()
        moved += 1
    drop_local = local(pair["dropLabel"])
    keep_local = local(pair["keepLabel"])
    rules = session.run(
        "MATCH (r:Rule {project:$project})-[:HAS_BODY|HAS_HEAD]->(:Atom)-[:REFERS_TO]->(k {project:$project, iri:$keep}) "
        "RETURN DISTINCT elementId(r) AS id, r.SWRL AS swrl",
        project=project, keep=keep).data()
    word = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(drop_local) + r"(?![A-Za-z0-9_])")
    for rule in rules:
        if rule["swrl"] and word.search(rule["swrl"]):
            session.run("MATCH (r) WHERE elementId(r) = $id SET r.SWRL = $swrl",
                        id=rule["id"], swrl=word.sub(keep_local, rule["swrl"])).consume()
    session.run(
        "MATCH (a:Atom {project:$project})-[:REFERS_TO]->(k {project:$project, iri:$keep}) "
        "WHERE a.SWRL_label = $dropLabel SET a.SWRL_label = $keepLabel",
        project=project, keep=keep, dropLabel=pair["dropLabel"], keepLabel=pair["keepLabel"]).consume()
    session.run("MATCH (d {project:$project, iri:$drop}) DETACH DELETE d", project=project, drop=drop).consume()
    return {"merged": True, "kind": pair["kind"], "kept": pair["keepLabel"], "dropped": pair["dropLabel"],
            "movedRelationships": moved, "rulesRewritten": len(rules)}


def local(name: str) -> str:
    return (name or "").rsplit("#", 1)[-1].rsplit("/", 1)[-1].rsplit(":", 1)[-1]


def resolve(session: Any, project: str, a: str, b: str, decision: str, actor: str | None, at: str) -> dict:
    """``use_existing``: merge ``a`` (new) into ``b`` (existing); ``keep_new``/``distinct``: record that they are
    different concepts (owl:disjointWith for classes in the reasoner export)."""
    if decision == "use_existing":
        return merge(session, project, drop=a, keep=b)
    if decision in ("keep_new", "distinct"):
        row = session.run(DISTINCT_QUERY, project=project, a=a, b=b, actor=actor, at=at).single()
        return {"distinct": bool(row and row["n"])}
    raise ValueError("decision must be use_existing, keep_new or distinct")
