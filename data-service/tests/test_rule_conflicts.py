"""Structural rule-conflict read (plan 1303-21, D-64/D-65).

Fake session rows only, no Neo4j. A fixture rule is built with the same atom
layout the ingest template writes: ClassAtom(subject), optional participants
(ClassAtom + ObjectPropertyAtom), DataPropertyAtom, BuiltinAtom, head
DataPropertyAtom on the subject.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import rule_conflicts  # noqa: E402

PROJECT = "P"


def _atom(rule_id, role, order, atom_type, ref_kind, ref_iri, args, label=""):
    return {
        "ruleId": rule_id,
        "role": role,
        "ord": order,
        "atomId": f"{rule_id}_{role}_{order}",
        "atomType": atom_type,
        "refKind": ref_kind,
        "refIri": ref_iri,
        "refLabel": label,
        "args": args,
    }


def _var(pos, name):
    return {"pos": pos, "kind": "Var", "value": name}


def _lit(pos, lex):
    return {"pos": pos, "kind": "Literal", "value": lex}


def make_rule(
    rule_id,
    subject="Opening",
    participants=(),
    prop="ex:distanceMm",
    comparator="swrlb:greaterThanOrEqual",
    limit="500",
    swrl="",
    description="",
    head=True,
    subject_class_atom=True,
):
    """Rows for one rule, as the atom read query returns them."""
    rows = []
    n = 0

    def body(atom_type, ref_kind, ref_iri, args, label=""):
        nonlocal n
        n += 1
        rows.append(_atom(rule_id, "HAS_BODY", n, atom_type, ref_kind, ref_iri, args, label))

    if subject_class_atom:
        body("ClassAtom", "Class", f"ex:{subject}", [_var(1, "?x")], subject)
    for i, cls in enumerate(participants):
        var = f"?p{i}"
        body("ClassAtom", "Class", f"ex:{cls}", [_var(1, var)], cls)
        body("ObjectPropertyAtom", "ObjectProperty", "ex:near", [_var(1, "?x"), _var(2, var)])
    body("DataPropertyAtom", "DatatypeProperty", prop, [_var(1, "?x"), _var(2, "?v")])
    body("BuiltinAtom", "Builtin", comparator, [_var(1, "?v"), _lit(2, limit)])
    if head:
        rows.append(
            _atom(
                rule_id, "HAS_HEAD", 1, "DataPropertyAtom", "DatatypeProperty",
                "ex:isViolation", [_var(1, "?x"), _lit(2, "true")],
            )
        )
    for row in rows:
        row["swrl"] = swrl or f"swrl-{rule_id}"
        row["description"] = description
    return rows


class FakeSession:
    def __init__(self, new_rows, corpus_rows):
        self.new_rows = new_rows
        self.corpus_rows = corpus_rows
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if query is rule_conflicts._NEW_RULE_ATOMS_QUERY:
            return list(self.new_rows)
        if query is rule_conflicts._CORPUS_ATOMS_QUERY:
            return list(self.corpus_rows)
        raise AssertionError("unexpected query")


def check(new_rule, *corpus_rules, rule_id="NEW"):
    corpus = [row for rule in corpus_rules for row in rule]
    session = FakeSession(new_rule, corpus)
    return rule_conflicts.structural_conflicts(session, PROJECT, rule_id), session


def test_one_class_rules_with_same_key_conflict():
    result, _ = check(make_rule("NEW", limit="500"), make_rule("OLD", limit="300"))
    assert result["conflict"] is True
    assert result["ruleId"] == "NEW"
    assert [m["ruleId"] for m in result["matches"]] == ["OLD"]
    match = result["matches"][0]
    assert match["currentValue"] == "300"
    assert match["sharedClasses"] == []
    assert match["swrl"] == "swrl-OLD"


def test_d64_example_shared_classes_sorted():
    new = make_rule("NEW", participants=("Slab", "Column", "Wall"), limit="500")
    old = make_rule("OLD", participants=("Slab", "Column"), limit="300")
    result, _ = check(new, old)
    assert result["conflict"] is True
    assert result["matches"][0]["sharedClasses"] == ["Column", "Slab"]
    assert result["matches"][0]["currentValue"] == "300"


def test_d64_example_disjoint_participants_do_not_conflict():
    result, _ = check(
        make_rule("NEW", participants=("Column",)),
        make_rule("OLD", participants=("Beam",)),
    )
    assert result["conflict"] is False
    assert result["matches"] == []


def test_d64_example_rule_without_participants_overlaps_everything_with_same_key():
    new = make_rule("NEW", participants=("Slab", "Column", "Wall"))
    old = make_rule("OLD")
    result, _ = check(new, old)
    assert result["conflict"] is True
    assert result["matches"][0]["sharedClasses"] == []


def test_new_rule_without_participants_overlaps_participant_rule():
    result, _ = check(make_rule("NEW"), make_rule("OLD", participants=("Beam",)))
    assert result["conflict"] is True
    assert result["matches"][0]["sharedClasses"] == []


def test_different_property_or_comparator_or_subject_is_not_a_conflict():
    new = make_rule("NEW")
    assert check(new, make_rule("OLD", prop="ex:otherMm"))[0]["conflict"] is False
    assert check(new, make_rule("OLD", comparator="swrlb:lessThanOrEqual"))[0]["conflict"] is False
    assert check(new, make_rule("OLD", subject="Door"))[0]["conflict"] is False


def test_the_new_rule_never_matches_itself():
    new = make_rule("NEW")
    result, _ = check(new, make_rule("NEW"))
    assert result["conflict"] is False


def test_corpus_query_excludes_superseded_rules_and_binds_project():
    query = rule_conflicts._CORPUS_ATOMS_QUERY
    assert "NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }" in query
    assert "$project" in query
    assert "$project" in rule_conflicts._NEW_RULE_ATOMS_QUERY
    _, session = check(make_rule("NEW"), make_rule("OLD"))
    for _q, params in session.calls:
        assert params["project"] == PROJECT
    assert session.calls[1][1]["propertyIris"] == ["ex:distanceMm"]
    assert session.calls[1][1]["ruleId"] == "NEW"


def test_rule_without_head_reports_no_conflict_with_reason():
    result, session = check(make_rule("NEW", head=False), make_rule("OLD"))
    assert result["conflict"] is False
    assert result["matches"] == []
    assert result["reason"] == "no-subject"
    assert len(session.calls) == 1  # the corpus is not even read


def test_rule_without_subject_class_atom_reports_no_conflict_with_reason():
    result, _ = check(make_rule("NEW", subject_class_atom=False), make_rule("OLD"))
    assert result["conflict"] is False
    assert result["reason"] == "no-subject-class"


def test_corpus_rule_without_readable_subject_is_ignored():
    result, _ = check(make_rule("NEW"), make_rule("OLD", head=False))
    assert result["conflict"] is False


def test_unknown_rule_raises_not_found():
    session = FakeSession([], [])
    with pytest.raises(rule_conflicts.RuleNotFoundError):
        rule_conflicts.structural_conflicts(session, PROJECT, "MISSING")


def test_edit_prefix_is_stripped_from_description():
    old = make_rule("OLD", description="edit Rule_Id: R_X_V — Opening at least 300 mm")
    result, _ = check(make_rule("NEW"), old)
    assert result["matches"][0]["description"] == "Opening at least 300 mm"


def test_russian_labels_work_without_any_text_grounding():
    new = make_rule("NEW", subject="Проём", participants=("Колонна", "Стена"), limit="500")
    old = make_rule("OLD", subject="Проём", participants=("Колонна",), limit="300")
    result, _ = check(new, old)
    assert result["conflict"] is True
    assert result["matches"][0]["sharedClasses"] == ["Колонна"]


def test_participant_variable_in_a_data_property_is_not_context_only():
    # ?p0 also feeds a DataPropertyAtom, so it is a checked object, not context.
    new = make_rule("NEW", participants=("Column",))
    new.append(
        _atom("NEW", "HAS_BODY", 99, "DataPropertyAtom", "DatatypeProperty", "ex:width",
              [_var(1, "?p0"), _var(2, "?w")])
    )
    for row in new:
        row.setdefault("swrl", "")
        row.setdefault("description", "")
    result, _ = check(new, make_rule("OLD", participants=("Beam",)))
    # No context participants remain on the new rule, so it overlaps by the empty-set rule.
    assert result["conflict"] is True
    assert result["matches"][0]["sharedClasses"] == []
