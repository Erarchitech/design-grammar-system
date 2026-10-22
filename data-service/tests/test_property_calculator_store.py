"""Store-level checks of the calculator review lifecycle (Phase 1303-16, DGOPN-05; D-54, D-56, D-58..D-60).

Everything runs without Neo4j against ``_RowStore``, a stateful fake that dispatches on the identity of the store's
query constants and applies each statement's effect like its WHERE/SET clauses. A statement it does not know fails
the test, so a new query cannot slip past the fake.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import property_calculator_llm as pcl  # noqa: E402
import property_calculator_store as store  # noqa: E402

PROJECT = "str-openings-01"
OTHER = "str-openings-02"
IRI = "http://dg.example/onto#hasOpeningHeightMm"
IRI2 = "http://dg.example/onto#hasColumnIntersectionCount"
SHA_A = "a" * 64
SHA_B = "b" * 64


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return [dict(r) for r in self._rows]

    def consume(self):
        return None


# SAVE_QUERY parameter -> stored property name (same name except paramsJson, kept as is)
_SAVE_FIELDS = ("calculator", "origin", "paramsJson", "function", "source", "sha256", "provider", "model", "unit",
                "explanation", "createdAt", "createdBy", "status", "reviewStatus", "catalogueId",
                "regenerateRequested")
_STATE_FIELDS = ("dataPropertyIri", "sha256", "status", "reviewStatus", "catalogueId", "createdAt", "createdBy",
                 "regenerateRequested", "rejectedSha256Json")
_LOAD_FIELDS = ("dataPropertyIri", "calculator", "origin", "paramsJson", "function", "source", "sha256", "provider",
                "model", "createdAt", "createdBy", "unit", "explanation", "catalogueId", "reviewStatus")


class _RowStore:
    """Stateful fake session/transaction: ``rows`` by (project, dataPropertyIri), ``entries`` by catalogueId."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}
        self.entries: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []
        self._names = {value: name for name, value in vars(store).items()
                       if name.endswith("_QUERY") and isinstance(value, str)}

    # session API
    def execute_write(self, fn, *args, **kwargs):
        return fn(self, *args, **kwargs)

    def run(self, query, **params):
        name = self._names.get(query)
        if name is None:
            pytest.fail(f"unknown statement reached the fake: {query[:80]}")
        self.calls.append((name, params))
        handler = getattr(self, "_do_" + name.lower(), None)
        if handler is None:
            pytest.fail(f"statement {name} has no fake handler")
        return _Result(handler(**params) or [])

    # helpers for tests
    def row(self, project=PROJECT, iri=IRI):
        return self.rows[(project, iri)]

    def names(self):
        return [n for n, _ in self.calls]

    def params_of(self, name):
        return [p for n, p in self.calls if n == name]

    def _row_for_write(self, project, iri):
        return self.rows.setdefault((project, iri), {"project": project, "dataPropertyIri": iri})

    # row statements
    def _do_load_query(self, project):
        out = [r for (p, _), r in sorted(self.rows.items()) if p == project and (r.get("status") or "active") == "active"]
        return [{k: r.get(k) for k in _LOAD_FIELDS} for r in out]

    def _do_save_state_query(self, project, dataPropertyIri):
        row = self._row_for_write(project, dataPropertyIri)
        row["reviewLock"] = row.get("reviewLock", 0) + 1
        return [{k: row.get(k) for k in _STATE_FIELDS}]

    def _do_save_query(self, project, dataPropertyIri, **fields):
        assert "rejectedSha256Json" not in fields, "a save must never write the rejected-hash list"
        assert set(fields) == set(_SAVE_FIELDS), set(fields) ^ set(_SAVE_FIELDS)
        row = self._row_for_write(project, dataPropertyIri)
        row.update(fields)
        return [{"dataPropertyIri": dataPropertyIri}]

    def _do_blocked_query(self, project):
        out = []
        for (p, _), r in sorted(self.rows.items()):
            hashes = r.get("rejectedSha256Json")
            if p == project and (r.get("status") in ("rejected", "retired") or hashes not in (None, "[]")):
                out.append({"dataPropertyIri": r["dataPropertyIri"], "status": r.get("status"),
                            "sha256": r.get("sha256"), "rejectedSha256Json": hashes,
                            "reviewReason": r.get("reviewReason"), "reviewedBy": r.get("reviewedBy"),
                            "regenerateRequested": r.get("regenerateRequested")})
        return out


def _entry(sha=SHA_A, iri=IRI, origin="generated", **extra):
    entry = {"dataPropertyIri": iri, "calculator": f"generated:{sha[:10]}" if origin == "generated" else "revit_x",
             "origin": origin, "params": {}, "provider": "fake", "model": "m1"}
    if origin == "generated":
        entry.update({"function": "calc_gen_abcdef0123", "source": f"source-{sha[:4]}", "sha256": sha})
    entry.update(extra)
    return entry


@pytest.fixture
def db():
    return _RowStore()


# ---------------------------------------------------------------------------------------------------- helpers


def test_catalogue_id_follows_the_stated_rule():
    import hashlib

    expected = "CC-" + hashlib.sha256(("ACME" + "\x1f" + "a" * 64).encode("utf-8")).hexdigest()[:16]
    assert store.catalogue_id("ACME", "a" * 64) == expected
    assert len(expected) == 19
    assert store.catalogue_id("ACME", "a" * 64) != store.catalogue_id("OTHER", "a" * 64)


def test_company_of_fails_closed(monkeypatch):
    import company

    monkeypatch.setattr(company, "company_for_project", lambda project: "ACME")
    assert store.company_of(PROJECT) == "ACME"

    def boom(project):
        raise OSError("store unreadable")

    monkeypatch.setattr(company, "company_for_project", boom)
    assert store.company_of(PROJECT) is None


@pytest.mark.parametrize("later, earlier, expected", [
    ("2026-10-21T12:00:01Z", "2026-10-21T12:00:00+00:00", True),
    ("2026-10-21T12:00:00Z", "2026-10-21T12:00:00+00:00", False),
    ("2026-10-21T12:00:00+02:00", "2026-10-21T11:00:00Z", False),   # 10:00Z is earlier
    ("2026-10-21T14:30:00+02:00", "2026-10-21T11:00:00Z", True),    # 12:30Z is later
    ("2026-10-21T12:00:00", "2026-10-21T11:59:59Z", True),           # naive means UTC
    (None, "2026-10-21T11:59:59Z", False),
    ("2026-10-21T12:00:00Z", None, False),
    ("garbage", "2026-10-21T11:59:59Z", False),
    ("2026-10-21T12:00:00Z", "", False),
])
def test_created_after_handles_zones_and_bad_values(later, earlier, expected):
    assert store.created_after(later, earlier) is expected


def test_is_blocked_and_rejected_source_helpers():
    assert store.is_blocked({"status": "rejected", "regenerate": False})
    assert store.is_blocked({"status": "retired"})
    assert not store.is_blocked({"status": "rejected", "regenerate": True})
    assert not store.is_blocked({"status": "active"})
    assert not store.is_blocked(None)
    blocked = {IRI: {"sha256s": [SHA_A]}}
    assert store.rejected_source(blocked, IRI, SHA_A)
    assert not store.rejected_source(blocked, IRI, SHA_B)
    assert not store.rejected_source(blocked, IRI2, SHA_A)
    assert not store.rejected_source(blocked, IRI, None)


def test_catalogue_graph_is_the_claim_untagged_shared_graph():
    import app as app_module

    assert store.CATALOGUE_GRAPH in app_module.CLAIM_UNTAGGED_SHARED_GRAPHS
    assert store.CATALOGUE_LABEL in app_module.LOCKED_NODE_LABELS


# ------------------------------------------------------------------------------------------------------ save


def test_save_new_generated_row_is_active_pending_and_keeps_unit_and_explanation(db):
    result = store.save(db, PROJECT, _entry(unit="mm", explanation="height of the box"), "alice")

    assert result == {"saved": True, "reason": None}
    row = db.row()
    assert (row["status"], row["reviewStatus"], row["regenerateRequested"]) == ("active", "pending", False)
    assert (row["unit"], row["explanation"], row["createdBy"]) == ("mm", "height of the box", "alice")
    assert row["catalogueId"] is None and row["createdAt"]


def test_save_catalogue_origin_has_no_review_status(db):
    store.save(db, PROJECT, _entry(origin="catalogue"), "alice")
    assert db.row()["reviewStatus"] is None and db.row()["status"] == "active"


def test_save_same_sha256_keeps_a_rejected_row_rejected(db):
    store.save(db, PROJECT, _entry(), "alice")
    db.row().update({"status": "rejected", "reviewStatus": "rejected", "regenerateRequested": True,
                     "createdAt": "2026-01-01T00:00:00+00:00", "catalogueId": "CC-0123456789abcdef"})

    result = store.save(db, PROJECT, _entry(), "bob")

    assert result["saved"] is True
    row = db.row()
    assert (row["status"], row["reviewStatus"], row["regenerateRequested"]) == ("rejected", "rejected", True)
    assert (row["createdAt"], row["createdBy"], row["catalogueId"]) == (
        "2026-01-01T00:00:00+00:00", "alice", "CC-0123456789abcdef")


def test_save_different_sha256_resets_review_state_and_keeps_the_rejection_list(db):
    store.save(db, PROJECT, _entry(SHA_A), "alice")
    db.row().update({"status": "rejected", "reviewStatus": "rejected", "regenerateRequested": True,
                     "rejectedSha256Json": json.dumps([SHA_A])})

    result = store.save(db, PROJECT, _entry(SHA_B), "bob")

    assert result == {"saved": True, "reason": None}
    row = db.row()
    assert (row["status"], row["reviewStatus"], row["regenerateRequested"]) == ("active", "pending", False)
    assert (row["sha256"], row["createdBy"], row["catalogueId"]) == (SHA_B, "bob", None)
    assert json.loads(row["rejectedSha256Json"]) == [SHA_A]  # save never writes the list


def test_save_refuses_a_generated_source_the_row_already_rejected(db):
    store.save(db, PROJECT, _entry(SHA_A), "alice")
    db.row()["rejectedSha256Json"] = json.dumps([SHA_A, SHA_B])
    before = dict(db.row())
    saves_before = db.names().count("SAVE_QUERY")

    result = store.save(db, PROJECT, _entry(SHA_B), "bob")

    assert result == {"saved": False, "reason": "rejected source"}
    assert db.names().count("SAVE_QUERY") == saves_before
    assert {k: v for k, v in db.row().items() if k != "reviewLock"} == {k: v for k, v in before.items() if k != "reviewLock"}


def test_save_never_passes_the_rejected_hash_list_to_a_statement(db):
    import inspect

    assert "rejectedSha256Json" not in store.SAVE_QUERY
    assert "rejectedSha256Json" in store.SAVE_STATE_QUERY and "rejectedSha256Json" in store.BLOCKED_QUERY
    store.save(db, PROJECT, _entry(), "alice")
    store.save(db, PROJECT, _entry(SHA_B), "alice")
    for name, params in db.calls:
        if name in ("SAVE_QUERY", "SAVE_STATE_QUERY"):
            assert "rejectedSha256Json" not in params
    assert "execute_write(_save_tx" in inspect.getsource(store.save).replace(" ", "")


def test_save_state_read_takes_the_row_lock(db):
    store.save(db, PROJECT, _entry(), "alice")
    store.save(db, PROJECT, _entry(), "alice")
    assert db.row()["reviewLock"] == 2
    assert db.names() == ["SAVE_STATE_QUERY", "SAVE_QUERY"] * 2


def test_load_active_reads_review_fields_and_defaults_generated_to_pending(db):
    store.save(db, PROJECT, _entry(unit="mm", explanation="e"), "alice")
    db.row()["reviewStatus"] = None  # a row written before 1303-16
    store.save(db, PROJECT, _entry(origin="catalogue", iri=IRI2), "alice")

    rows = store.load_active(db, PROJECT)

    assert rows[IRI]["reviewStatus"] == "pending" and rows[IRI]["unit"] == "mm" and rows[IRI]["explanation"] == "e"
    assert rows[IRI]["catalogueId"] is None and rows[IRI]["params"] == {}
    assert rows[IRI2]["reviewStatus"] is None


# --------------------------------------------------------------------------------------------- blocked read


def test_blocked_read_covers_rejected_retired_and_active_rows_with_history(db):
    for iri in (IRI, IRI2, "http://dg.example/onto#hasThird", "http://dg.example/onto#hasFourth"):
        store.save(db, PROJECT, _entry(SHA_B, iri=iri), "alice")
    db.row(iri=IRI).update({"status": "rejected", "reviewReason": "wrong", "reviewedBy": "carol",
                            "regenerateRequested": True, "rejectedSha256Json": json.dumps([SHA_A])})
    db.row(iri=IRI2).update({"status": "retired", "reviewReason": "retired from the company catalogue: x"})
    db.row(iri="http://dg.example/onto#hasThird")["rejectedSha256Json"] = json.dumps([SHA_A])
    # hasFourth stays active and never rejected

    blocked = store.load_blocked(db, PROJECT)

    assert set(blocked) == {IRI, IRI2, "http://dg.example/onto#hasThird"}
    assert blocked[IRI] == {"status": "rejected", "sha256": SHA_B, "sha256s": sorted([SHA_A, SHA_B]),
                            "reason": "wrong", "by": "carol", "regenerate": True}
    assert blocked[IRI2]["sha256s"] == [] and blocked[IRI2]["sha256"] == SHA_B  # paused, not rejected
    assert blocked["http://dg.example/onto#hasThird"]["sha256s"] == [SHA_A]
    assert not store.is_blocked(blocked["http://dg.example/onto#hasThird"])
    assert store.is_blocked(blocked[IRI2]) and not store.is_blocked(blocked[IRI])  # regenerate requested
    assert not store.rejected_source(blocked, IRI2, SHA_B)


def test_blocked_read_drops_rows_without_iri_and_active_rows_with_an_empty_list():
    class _Stale:
        def run(self, query, **params):
            assert query is store.BLOCKED_QUERY
            return _Result([
                {"dataPropertyIri": None, "status": "rejected", "sha256": SHA_A},
                {"dataPropertyIri": IRI, "status": "active", "sha256": SHA_A, "rejectedSha256Json": "[]"},
                {"dataPropertyIri": IRI2, "status": "active", "sha256": SHA_A, "rejectedSha256Json": "not json"},
            ])

    assert store.load_blocked(_Stale(), PROJECT) == {}


def test_blocked_read_is_empty_for_a_project_without_rejections(db):
    store.save(db, PROJECT, _entry(), "alice")
    assert store.load_blocked(db, PROJECT) == {}
    assert store.load_blocked(db, OTHER) == {}
