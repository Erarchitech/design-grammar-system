"""Structural rule-conflict read (Phase 1303 plan 21, D-64/D-65, DGOPN-06).

Compares a rule that has ALREADY been written with the active rules of the
same project, using only what is stored in the graph: atoms, their referents
and their arguments. No LLM, no rule text, no tokenisation, so a Russian rule
is checked exactly like an English one (the pre-ingest text check in
``dg_context.check_rule_conflict`` grounds English labels only and is kept for
other callers).

Conflict key (D-64): ``(subject class IRI, DatatypeProperty IRI, comparator
builtin IRI)``.
  * subject = the variable at position 1 of the first head atom; its class is
    the referent of the body ClassAtom on that variable;
  * property = the body DataPropertyAtom whose position-1 variable is the
    subject; its position-2 variable is the measured value;
  * comparator = the body BuiltinAtom whose position-1 variable is that value.

Participants (D-64, refined 2026-10-21 in 1303-CONTEXT.md): the classes of the
rule's context ClassAtoms, the subject excluded. Two rules conflict when a key
is equal AND either context set is empty OR the two sets share a class. A rule
without participants applies regardless of them, so it overlaps every rule with
the same key; two one-class rules with the same key conflict exactly as before.

The context-only variable definition mirrors the C# classifier
``DG/src/DG.Core/Parsing/RuleVariableRoles.cs`` (plan 1303-19): not the
subject, in a body atom, in no head atom, and every body atom that mentions it
is a ClassAtom or an ObjectPropertyAtom. Keep the two in step.

Reads are project-scoped (``$project`` is a bound parameter in both queries)
and exclude any rule with an outgoing SUPERSEDED_BY edge, like
``dg_context._RULE_CONFLICT_QUERY``.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Same regex dg_context._EDIT_PREFIX_PATTERN uses; duplicated so this module
# has no import-time dependency on the Neo4j driver module.
_EDIT_PREFIX_PATTERN = re.compile(r"^edit\s+Rule_Id:\s*\S+\s*[—–-]\s*", re.IGNORECASE)

REASON_NO_SUBJECT = "no-subject"
REASON_NO_SUBJECT_CLASS = "no-subject-class"
REASON_NO_KEY = "no-key"


class RuleNotFoundError(LookupError):
    """The rule does not exist in the project."""


# One row per atom of the rule (body and head). Args are aggregated per atom.
# Var nodes are MERGEd by name per project, so identity is taken from the
# atoms' own ARG edges, never from a shared Var node.
_ATOM_PROJECTION = """
OPTIONAL MATCH (r)-[rel:HAS_BODY|HAS_HEAD]->(a:Atom)
OPTIONAL MATCH (a)-[:REFERS_TO]->(ref)
OPTIONAL MATCH (a)-[ar:ARG]->(arg)
WITH r, rel, a, ref, collect(
    CASE WHEN ar IS NULL THEN NULL ELSE {
        pos: ar.pos,
        kind: CASE WHEN arg:Var THEN 'Var' WHEN arg:Literal THEN 'Literal' ELSE 'Other' END,
        value: coalesce(arg.name, arg.lex)
    } END
) AS args
RETURN r.Rule_Id AS ruleId,
       coalesce(r.SWRL, '') AS swrl,
       coalesce(r.RuleDescription, r.description, '') AS description,
       type(rel) AS role,
       rel.order AS ord,
       a.Atom_Id AS atomId,
       a.type AS atomType,
       CASE WHEN ref IS NULL THEN NULL ELSE labels(ref)[0] END AS refKind,
       ref.iri AS refIri,
       coalesce(ref.label, ref.SWRL_label, '') AS refLabel,
       args
ORDER BY ruleId, role, ord
"""

_NEW_RULE_ATOMS_QUERY = (
    """
MATCH (r:Rule {project: $project, graph: 'Metagraph', Rule_Id: $ruleId})
"""
    + _ATOM_PROJECTION
)

# Active rules of the project other than the new one that measure one of the
# new rule's properties. The property filter only narrows the read; the key
# comparison below is the authority.
_CORPUS_ATOMS_QUERY = (
    """
MATCH (r:Rule {project: $project, graph: 'Metagraph'})
WHERE r.Rule_Id <> $ruleId
  AND NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }
  AND EXISTS {
    (r)-[:HAS_BODY]->(:Atom {type: 'DataPropertyAtom'})-[:REFERS_TO]->(p:DatatypeProperty)
    WHERE p.iri IN $propertyIris
  }
"""
    + _ATOM_PROJECTION
)


def _norm_var(name: Any) -> str:
    text = str(name or "").strip()
    if text.startswith("?"):
        text = text[1:]
    return text.lower()


def _display_class(iri: str, label: str) -> str:
    if label:
        return label
    return iri.split(":", 1)[1] if ":" in iri else iri


def _arg(atom: dict[str, Any], pos: int) -> dict[str, Any] | None:
    for item in atom.get("args") or []:
        if item.get("pos") == pos:
            return item
    return None


def _var_at(atom: dict[str, Any], pos: int) -> str:
    item = _arg(atom, pos)
    if item and item.get("kind") == "Var":
        return _norm_var(item.get("value"))
    return ""


def _variables(atom: dict[str, Any]) -> set[str]:
    return {
        _norm_var(a.get("value"))
        for a in (atom.get("args") or [])
        if a.get("kind") == "Var" and _norm_var(a.get("value"))
    }


def _sorted_atoms(rows: Iterable[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    atoms = [r for r in rows if r.get("atomId") and r.get("role") == role]
    return sorted(atoms, key=lambda a: (a.get("ord") is None, a.get("ord") or 0, a["atomId"]))


def _analyze(rule_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the keys and the context participant set of one rule.

    Returns ``{"keys": set, "participants": {iri: display}, "reason": str|None,
    "comparators": {key: currentValue}}``. ``keys`` is empty when the rule has
    no readable key, with ``reason`` saying why.
    """
    body = _sorted_atoms(rule_rows, "HAS_BODY")
    head = _sorted_atoms(rule_rows, "HAS_HEAD")

    subject = _var_at(head[0], 1) if head else ""
    if not subject:
        return {"keys": set(), "participants": {}, "reason": REASON_NO_SUBJECT, "values": {}}

    subject_class = next(
        (
            a
            for a in body
            if a.get("atomType") == "ClassAtom"
            and a.get("refKind") == "Class"
            and a.get("refIri")
            and _var_at(a, 1) == subject
        ),
        None,
    )
    if subject_class is None:
        return {"keys": set(), "participants": {}, "reason": REASON_NO_SUBJECT_CLASS, "values": {}}

    # Context-only variables (mirror of RuleVariableRoles.cs).
    head_vars: set[str] = set()
    for atom in head:
        head_vars |= _variables(atom)
    candidates: set[str] = set()
    for atom in body:
        candidates |= _variables(atom)
    context_only: set[str] = set()
    for var in candidates:
        if var == subject or var in head_vars:
            continue
        mentioning = [a for a in body if var in _variables(a)]
        if mentioning and all(
            a.get("atomType") in ("ClassAtom", "ObjectPropertyAtom") for a in mentioning
        ):
            context_only.add(var)

    participants: dict[str, str] = {}
    for atom in body:
        if (
            atom.get("atomType") == "ClassAtom"
            and atom.get("refKind") == "Class"
            and atom.get("refIri")
            and _var_at(atom, 1) in context_only
        ):
            participants[atom["refIri"]] = _display_class(atom["refIri"], atom.get("refLabel") or "")

    keys: set[tuple[str, str, str]] = set()
    values: dict[tuple[str, str, str], Any] = {}
    for prop in body:
        if (
            prop.get("atomType") != "DataPropertyAtom"
            or prop.get("refKind") != "DatatypeProperty"
            or not prop.get("refIri")
            or _var_at(prop, 1) != subject
        ):
            continue
        value_var = _var_at(prop, 2)
        if not value_var:
            continue
        for cmp_atom in body:
            if (
                cmp_atom.get("atomType") != "BuiltinAtom"
                or cmp_atom.get("refKind") != "Builtin"
                or not cmp_atom.get("refIri")
                or _var_at(cmp_atom, 1) != value_var
            ):
                continue
            key = (subject_class["refIri"], prop["refIri"], cmp_atom["refIri"])
            keys.add(key)
            limit = _arg(cmp_atom, 2)
            values.setdefault(key, limit.get("value") if limit and limit.get("kind") == "Literal" else None)

    if not keys:
        return {"keys": set(), "participants": participants, "reason": REASON_NO_KEY, "values": {}}
    return {"keys": keys, "participants": participants, "reason": None, "values": values}


def _group_by_rule(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rule_id = row.get("ruleId")
        if rule_id:
            grouped.setdefault(rule_id, []).append(row)
    return grouped


def _clean_description(raw: str) -> str:
    return _EDIT_PREFIX_PATTERN.sub("", raw or "").strip()


def _read(session: Any, query: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(record) for record in session.run(query, **params)]


def structural_conflicts(session: Any, project: str, rule_id: str) -> dict[str, Any]:
    """Active rules of ``project`` that conflict with the written rule ``rule_id``.

    Returns ``{"ruleId", "conflict", "matches": [{ruleId, swrl, description,
    currentValue, sharedClasses}]}`` plus ``"reason"`` when the rule has no
    readable key (never a conflict then). Raises ``RuleNotFoundError`` when the
    rule is not in the project.
    """
    new_rows = _read(session, _NEW_RULE_ATOMS_QUERY, project=project, ruleId=rule_id)
    if not new_rows:
        raise RuleNotFoundError(rule_id)

    new = _analyze(new_rows)
    result: dict[str, Any] = {"ruleId": rule_id, "conflict": False, "matches": []}
    if not new["keys"]:
        result["reason"] = new["reason"]
        return result

    property_iris = sorted({key[1] for key in new["keys"]})
    corpus = _group_by_rule(
        _read(session, _CORPUS_ATOMS_QUERY, project=project, ruleId=rule_id, propertyIris=property_iris)
    )

    matches: list[dict[str, Any]] = []
    for other_id in sorted(corpus):
        if other_id == rule_id:
            continue
        rows = corpus[other_id]
        other = _analyze(rows)
        shared_keys = new["keys"] & other["keys"]
        if not shared_keys:
            continue
        shared_iris = set(new["participants"]) & set(other["participants"])
        if new["participants"] and other["participants"] and not shared_iris:
            continue
        shared_names = sorted(
            {new["participants"][iri] for iri in shared_iris}, key=lambda n: (n.lower(), n)
        )
        first = rows[0]
        key = sorted(shared_keys)[0]
        matches.append(
            {
                "ruleId": other_id,
                "swrl": first.get("swrl") or "",
                "description": _clean_description(first.get("description") or ""),
                "currentValue": other["values"].get(key),
                "sharedClasses": shared_names,
            }
        )

    result["conflict"] = bool(matches)
    result["matches"] = matches
    return result
