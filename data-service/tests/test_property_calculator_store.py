"""Store-level checks of the calculator review lifecycle (Phase 1303-16, DGOPN-05; D-54, D-56, D-58..D-60).

Everything runs without Neo4j against ``_RowStore``, a stateful fake that dispatches on the identity of the store's
query constants and applies each statement's effect like its WHERE/SET clauses. A statement it does not know fails
the test, so a new query cannot slip past the fake.
"""

from __future__ import annotations

import copy
import hashlib
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


_LOCK_FIELDS = ("dataPropertyIri", "origin", "status", "reviewStatus", "catalogueId", "sha256", "function", "source",
                "unit", "provider", "model", "createdAt", "createdBy", "reviewedBy", "reviewedAt", "reviewReason",
                "regenerateRequested", "rejectedSha256Json")
_CANDIDATE_FIELDS = ("dataPropertyIri", "function", "source", "sha256", "unit", "explanation", "provider", "model",
                     "createdAt", "createdBy", "catalogueId", "sourceRunId")
_CATALOGUE_FIELDS = ("catalogueId", "propertyKey", "propertyName", "sha256", "source", "function", "unit", "meaning",
                     "readCategories", "contractVersion", "provider", "model", "status")
_ENTRY_FIELDS = ("catalogueId", "propertyKey", "propertyName", "dataPropertyIri", "function", "sha256", "unit",
                 "meaning", "readCategories", "contractVersion", "provider", "model", "sourceProject", "sourceRunId",
                 "confirmedBy", "confirmedAt", "status")
# every property of the DATABASE.md CatalogueCalculator block that confirm sets on create (never `project`)
_CREATE_FIELDS = ("propertyKey", "propertyName", "dataPropertyIri", "function", "source", "sha256", "unit", "meaning",
                  "readCategories", "contractVersion", "provider", "model", "sourceProject", "sourceRunId",
                  "sourceRunCreatedAt", "confirmedBy", "confirmedAt", "historyJson")


class _RowStore:
    """Stateful fake session/transaction: ``rows`` by (project, dataPropertyIri), ``entries`` by catalogueId."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}
        self.entries: dict[str, dict] = {}
        self.verdicts: list[dict] = []
        self.calls: list[tuple[str, dict]] = []
        self.queries: list[str] = []
        self._names = {value: name for name, value in vars(store).items()
                       if name.endswith("_QUERY") and isinstance(value, str)}

    # session API
    def execute_write(self, fn, *args, **kwargs):
        # a managed transaction rolls back when its function raises
        snapshot = copy.deepcopy((self.rows, self.entries))
        try:
            return fn(self, *args, **kwargs)
        except Exception:
            self.rows, self.entries = snapshot
            raise

    def run(self, query, **params):
        name = self._names.get(query)
        if name is None:
            pytest.fail(f"unknown statement reached the fake: {query[:80]}")
        self.calls.append((name, params))
        self.queries.append(query)
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

    def _do_review_lock_query(self, project, dataPropertyIri):
        row = self.rows.get((project, dataPropertyIri))
        if row is None:  # MATCH, never create
            return []
        row["reviewLock"] = row.get("reviewLock", 0) + 1
        return [{k: row.get(k) for k in _LOCK_FIELDS}]

    def _do_confirm_row_query(self, project, dataPropertyIri, catalogueId, by, at, runId):
        self.rows[(project, dataPropertyIri)].update(
            status="active", reviewStatus="confirmed", catalogueId=catalogueId, reviewedBy=by, reviewedAt=at,
            sourceRunId=runId, regenerateRequested=False, reviewReason=None)
        return [{"dataPropertyIri": dataPropertyIri}]

    def _do_reject_row_query(self, project, dataPropertyIri, by, at, reason, regenerate, rejectedSha256Json):
        self.rows[(project, dataPropertyIri)].update(
            status="rejected", reviewStatus="rejected", reviewedBy=by, reviewedAt=at, reviewReason=reason,
            regenerateRequested=regenerate, rejectedSha256Json=rejectedSha256Json)
        return [{"dataPropertyIri": dataPropertyIri}]

    def _do_retire_copies_query(self, catalogueId, reason):
        hit = [r for r in self.rows.values() if r.get("catalogueId") == catalogueId and r.get("status") == "active"]
        for r in hit:
            r.update(status="retired", reviewReason=reason)
        return [{"retiredCopies": len(hit)}]

    def _do_reactivate_copies_query(self, catalogueId, sha256):
        hit = [r for r in self.rows.values()
               if r.get("catalogueId") == catalogueId and r.get("status") == "retired" and r.get("sha256") == sha256]
        for r in hit:
            r.update(status="active", reviewStatus="confirmed", reviewReason=None)
        return [{"reactivatedCopies": len(hit)}]

    def _do_candidates_query(self, project):
        out = []
        for (p, _), r in sorted(self.rows.items()):
            status = r.get("status") or "active"
            pending = status == "active" and not r.get("catalogueId") and (r.get("reviewStatus") or "pending") == "pending"
            retired = status == "retired" and r.get("catalogueId")
            if p == project and r.get("origin") == "generated" and (pending or retired):
                out.append({k: r.get(k) for k in _CANDIDATE_FIELDS} | {"status": status})
        return out

    def _do_verdict_counts_query(self, project, runId, ruleIds):
        counts: dict[tuple, int] = {}
        for v in self.verdicts:
            if v["project"] == project and v["runId"] == runId and v["ruleId"] in ruleIds:
                counts[(v["ruleId"], v["status"])] = counts.get((v["ruleId"], v["status"]), 0) + 1
        return [{"ruleId": r, "status": s, "count": n} for (r, s), n in sorted(counts.items())]

    # catalogue statements: every one is filtered by company, like the Cypher
    def _company_entries(self, company, active_only=True):
        return sorted((e for e in self.entries.values()
                       if e.get("company") == company and (not active_only or e.get("status") == "active")),
                      key=lambda e: (e.get("propertyKey") or "", e.get("sha256") or ""))

    def _do_catalogue_query(self, company):
        return [{k: e.get(k) for k in _CATALOGUE_FIELDS} for e in self._company_entries(company)]

    def _do_vocabulary_query(self, company):
        return [{k: e.get(k) for k in ("propertyKey", "propertyName", "meaning", "unit", "status")}
                for e in self._company_entries(company)]

    def _do_catalogue_entries_query(self, company):
        return [{k: e.get(k) for k in _ENTRY_FIELDS} for e in self._company_entries(company)]

    def _do_catalogue_key_query(self, company, propertyKey):
        return [{"catalogueId": e["catalogueId"], "sha256": e["sha256"]}
                for e in self._company_entries(company) if e.get("propertyKey") == propertyKey]

    def _do_catalogue_by_id_query(self, company, catalogueId):
        e = self.entries.get(catalogueId)
        return [{"entry": dict(e)}] if e and e.get("company") == company else []

    def _do_catalogue_create_query(self, company, catalogueId, **f):
        assert "project" not in f and "project" not in _CREATE_FIELDS
        assert set(f) == set(_CREATE_FIELDS), set(f) ^ set(_CREATE_FIELDS)
        entry = self.entries.get(catalogueId)
        if entry is None:  # MERGE .. ON CREATE SET
            entry = {"graph": "CalculatorCatalogue", "company": company, "catalogueId": catalogueId,
                     "status": "active", **f}
            self.entries[catalogueId] = entry
        return [{"entry": dict(entry)}]

    def _do_retire_entry_query(self, company, catalogueId, by, at, reason, historyJson):
        self.entries[catalogueId].update(status="retired", retiredBy=by, retiredAt=at, retiredReason=reason,
                                         historyJson=historyJson)
        return [{"catalogueId": catalogueId}]

    def _do_reactivate_entry_query(self, company, catalogueId, by, at, runId, meaning, unit, historyJson):
        self.entries[catalogueId].update(status="active", reconfirmedBy=by, reconfirmedAt=at, reconfirmedRunId=runId,
                                         meaning=meaning, unit=unit, historyJson=historyJson)
        return [{"entry": dict(self.entries[catalogueId])}]


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


# ======================================================================================================
# Task 3: company catalogue reads and the locked confirm / reject / retire transactions
# ======================================================================================================

COMPANY = "ACME"
GOOD_SOURCE = "def calc_gen(ctx, box, params):\n    return len(ctx.intersecting(box, ['OST_StructuralFraming']))\n"
FUNCTION, SOURCE = pcl.finalize(GOOD_SOURCE)
GOOD_SHA = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
# a second, different calculator (another DataProperty with its own code)
FUNCTION_B, SOURCE_B = pcl.finalize(
    "def calc_gen(ctx, box, params):\n    return len(ctx.intersecting(box, ['OST_StructuralColumns']))\n")
SHA_B2 = hashlib.sha256(SOURCE_B.encode("utf-8")).hexdigest()
OWN_CODE = {"function": FUNCTION_B, "source": SOURCE_B, "sha256": SHA_B2}
CALCULATOR_TIME = "2026-10-20T10:00:00+00:00"
RUN = {"runId": "run-1", "createdAt": "2026-10-21T10:00:00+00:00"}
READ_ONLY = {"REVIEW_LOCK_QUERY", "CATALOGUE_KEY_QUERY", "CATALOGUE_BY_ID_QUERY"}


def _generated(db, project=PROJECT, iri=IRI, **extra):
    """A stored, finalized generated calculator waiting for review (what property_scripts.generate leaves)."""
    entry = {"dataPropertyIri": iri, "calculator": f"generated:{GOOD_SHA[:10]}", "origin": "generated", "params": {},
             "function": FUNCTION, "source": SOURCE, "sha256": GOOD_SHA, "provider": "fake", "model": "m1",
             "unit": "mm", "explanation": "LLM sentence, never vocabulary"}
    entry.update(extra)
    store.save(db, project, entry, "alice")
    db.row(project, iri)["createdAt"] = CALCULATOR_TIME
    return db.row(project, iri)


def _confirm(db, **over):
    kwargs = dict(project=PROJECT, company=COMPANY, data_property_iri=IRI, sha256=GOOD_SHA, run=dict(RUN),
                  actor="alice", meaning="Height of the opening box in millimetres", unit=None, contract_version=3)
    kwargs.update(over)
    return store.confirm(db, **kwargs)


def _state(db):
    return copy.deepcopy((db.rows, db.entries))


def _refused(db, code, status, call):
    """The call raises CalculatorReviewError(code, status) and leaves rows and entries exactly as they were."""
    before = _state(db)
    calls_before = len(db.calls)
    with pytest.raises(store.CalculatorReviewError) as err:
        call()
    assert (err.value.code, err.value.status) == (code, status)
    assert _state(db) == before
    assert {n for n, _ in db.calls[calls_before:]} <= READ_ONLY
    return err.value


def _confirmed_in_two_projects(db):
    """P1 confirms; P2 holds a shared copy of the entry (as a shared binding would save it)."""
    _generated(db)
    result = _confirm(db)
    cid = result["catalogueId"]
    store.save(db, OTHER, {"dataPropertyIri": IRI, "calculator": f"generated:{GOOD_SHA[:10]}", "origin": "generated",
                           "params": {}, "function": FUNCTION, "source": SOURCE, "sha256": GOOD_SHA,
                           "catalogueId": cid, "reviewStatus": "confirmed"}, "bob")
    db.row(OTHER)["createdAt"] = CALCULATOR_TIME
    return cid


# ------------------------------------------------------------------------------------------------ confirm


def test_confirm_creates_one_company_entry_with_provenance_and_no_project(db):
    _generated(db)

    result = _confirm(db)

    cid = store.catalogue_id(COMPANY, GOOD_SHA)
    assert set(result) == {"catalogueId", "entry", "alreadyConfirmed", "reconfirmed", "reactivatedCopies"}
    assert (result["catalogueId"], result["alreadyConfirmed"], result["reconfirmed"]) == (cid, False, False)
    assert result["reactivatedCopies"] == 0
    entry = db.entries[cid]
    assert result["entry"] == entry and "project" not in entry
    assert entry["graph"] == "CalculatorCatalogue" and entry["company"] == COMPANY and entry["status"] == "active"
    assert (entry["propertyKey"], entry["propertyName"]) == ("hasopeningheightmm", "hasOpeningHeightMm")
    assert (entry["function"], entry["source"], entry["sha256"]) == (FUNCTION, SOURCE, GOOD_SHA)
    assert (entry["unit"], entry["meaning"]) == ("mm", "Height of the opening box in millimetres")
    assert entry["readCategories"] == ["OST_StructuralFraming"] and entry["contractVersion"] == 3
    assert (entry["provider"], entry["model"], entry["dataPropertyIri"]) == ("fake", "m1", IRI)
    assert (entry["sourceProject"], entry["sourceRunId"], entry["sourceRunCreatedAt"]) == (
        PROJECT, "run-1", RUN["createdAt"])
    assert entry["confirmedBy"] == "alice" and entry["confirmedAt"]
    history = json.loads(entry["historyJson"])
    assert [e["event"] for e in history] == ["confirmed"] and history[0]["by"] == "alice"
    assert history[0]["project"] == PROJECT and history[0]["runId"] == "run-1"
    assert "explanation" not in entry
    (create_params,) = db.params_of("CATALOGUE_CREATE_QUERY")
    assert "project" not in create_params
    row = db.row()
    assert (row["status"], row["reviewStatus"], row["catalogueId"], row["sourceRunId"]) == (
        "active", "confirmed", cid, "run-1")


def test_confirm_request_unit_overrides_the_stored_unit(db):
    _generated(db, unit="m")
    _confirm(db, unit="mm")
    assert next(iter(db.entries.values()))["unit"] == "mm"


def test_confirm_without_any_unit_stores_none(db):
    _generated(db, unit=None)
    _confirm(db)
    assert next(iter(db.entries.values()))["unit"] is None


def test_confirm_repeat_of_the_same_sha256_is_already_confirmed_and_creates_nothing(db):
    _generated(db)
    first = _confirm(db)

    second = _confirm(db, actor="bob")

    assert second["alreadyConfirmed"] is True and second["catalogueId"] == first["catalogueId"]
    assert second["reconfirmed"] is False and len(db.entries) == 1
    assert db.names().count("CATALOGUE_CREATE_QUERY") == 1
    assert db.row()["reviewStatus"] == "confirmed" and db.row()["catalogueId"] == first["catalogueId"]


def test_confirm_two_sequential_actors_in_two_projects_give_one_entry(db):
    _generated(db)
    _generated(db, project=OTHER)

    first = _confirm(db, actor="alice")
    second = _confirm(db, project=OTHER, actor="bob")

    assert first["catalogueId"] == second["catalogueId"] and len(db.entries) == 1
    assert (first["alreadyConfirmed"], second["alreadyConfirmed"]) == (False, True)
    assert db.row(OTHER)["catalogueId"] == first["catalogueId"] and db.row(OTHER)["reviewStatus"] == "confirmed"
    assert json.loads(next(iter(db.entries.values()))["historyJson"])[0]["by"] == "alice"


def test_confirm_entry_of_one_company_is_not_the_entry_of_another(db):
    _generated(db)
    _generated(db, project=OTHER)
    first = _confirm(db)
    other = _confirm(db, project=OTHER, company="GLOBEX")
    assert first["catalogueId"] != other["catalogueId"] and len(db.entries) == 2
    assert {e["company"] for e in db.entries.values()} == {COMPANY, "GLOBEX"}


@pytest.mark.parametrize("setup", ["missing", "catalogue_origin"])
def test_confirm_not_found_for_missing_or_non_generated_row(db, setup):
    if setup == "catalogue_origin":
        store.save(db, PROJECT, _entry(origin="catalogue"), "alice")
    _refused(db, "CALCULATOR_NOT_FOUND", 404, lambda: _confirm(db))


@pytest.mark.parametrize("mutation", [
    {"status": "rejected"},
    {"reviewStatus": "rejected"},
    {"status": "retired", "catalogueId": "CC-0000000000000000"},
    {"status": "retired", "catalogueId": None},
    {"catalogueId": "CC-0000000000000000"},  # confirmed under another key or company
])
def test_confirm_not_pending_for_rejected_or_foreign_rows(db, mutation):
    _generated(db).update(mutation)
    _refused(db, "CALCULATOR_NOT_PENDING", 409, lambda: _confirm(db))


def test_confirm_refuses_a_calculator_that_changed_since_it_was_shown(db):
    _generated(db)
    _refused(db, "CALCULATOR_CHANGED", 409, lambda: _confirm(db, sha256="f" * 64))


def test_confirm_integrity_failure_refuses_a_tampered_source(db):
    row = _generated(db)
    row["source"] = SOURCE.replace("StructuralFraming", "StructuralColumns")  # sha256 field still the old one
    error = _refused(db, "CALCULATOR_INTEGRITY", 409, lambda: _confirm(db))
    assert "sha256" in error.detail


def test_confirm_integrity_failure_refuses_a_forbidden_construct(db):
    forged = "def calc_gen_abcdef0123(ctx, box, params):\n    box.Delete()\n    return 0\n"
    sha = hashlib.sha256(forged.encode("utf-8")).hexdigest()
    _generated(db, function="calc_gen_abcdef0123", source=forged, sha256=sha)
    _refused(db, "CALCULATOR_INTEGRITY", 409, lambda: _confirm(db, sha256=sha))


@pytest.mark.parametrize("run_time", [
    "2026-10-20T10:00:00Z",       # equal to the calculator
    "2026-10-19T10:00:00+00:00",  # older
    "not a time", "", None,
])
def test_confirm_run_must_be_newer_than_the_calculator(db, run_time):
    _generated(db)
    _refused(db, "CALCULATOR_RUN_INVALID", 422, lambda: _confirm(db, run={"runId": "r", "createdAt": run_time}))


def test_confirm_property_taken_when_another_entry_holds_the_key(db):
    _generated(db)
    db.entries["CC-other"] = {"graph": "CalculatorCatalogue", "company": COMPANY, "catalogueId": "CC-other",
                              "propertyKey": "hasopeningheightmm", "sha256": "e" * 64, "status": "active"}
    _refused(db, "CATALOGUE_PROPERTY_TAKEN", 409, lambda: _confirm(db))
    assert db.names().count("CATALOGUE_CREATE_QUERY") == 0


def test_confirm_refuses_a_source_already_confirmed_for_another_property(db):
    _generated(db)
    _confirm(db)
    _generated(db, iri=IRI2)  # identical source under another DataProperty
    error = _refused(db, "CATALOGUE_PROPERTY_TAKEN", 409, lambda: _confirm(db, data_property_iri=IRI2))
    assert "another property" in error.detail


def test_confirm_needs_a_company_and_runs_no_statement_without_one(db):
    _generated(db)
    calls_before = len(db.calls)
    with pytest.raises(store.CalculatorReviewError) as err:
        _confirm(db, company=None)
    assert err.value.code == "CATALOGUE_COMPANY_REQUIRED" and len(db.calls) == calls_before


def test_confirm_first_of_a_pending_row_needs_no_owner_flag(db):
    _generated(db)
    assert _confirm(db)["alreadyConfirmed"] is False  # allow_reconfirm stays at its default False


# ------------------------------------------------------------------------------------------------ reject


def test_reject_requires_the_shown_sha256(db):
    _generated(db)
    _refused(db, "CALCULATOR_CHANGED", 409, lambda: store.reject(
        db, project=PROJECT, data_property_iri=IRI, sha256="f" * 64, actor="carol", reason="r", regenerate=False))


def test_reject_not_found(db):
    _refused(db, "CALCULATOR_NOT_FOUND", 404, lambda: store.reject(
        db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="carol", reason="r", regenerate=False))


def test_reject_records_the_hash_and_the_decision_and_runs_no_catalogue_statement(db):
    _generated(db).update(rejectedSha256Json=json.dumps(["9" * 64, "1" * 64]))

    result = store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="carol",
                          reason="counts too much", regenerate=True)

    row = db.row()
    assert json.loads(row["rejectedSha256Json"]) == sorted(["1" * 64, "9" * 64, GOOD_SHA])
    assert (row["status"], row["reviewStatus"], row["reviewedBy"], row["reviewReason"], row["regenerateRequested"]) == (
        "rejected", "rejected", "carol", "counts too much", True)
    assert row["reviewedAt"]
    assert result == {"alreadyRejected": False, "regenerate": True, "rejectedSha256s": json.loads(row["rejectedSha256Json"])}
    assert not [n for n in db.names() if n.startswith("CATALOGUE_") or n.endswith("_ENTRY_QUERY")]


def test_reject_twice_is_already_rejected_and_updates_only_regenerate_and_reason(db):
    _generated(db)
    store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="carol", reason="first",
                 regenerate=False)
    first = dict(db.row())

    again = store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="dave", reason="second",
                         regenerate=True)

    assert again["alreadyRejected"] is True
    row = db.row()
    assert (row["reviewReason"], row["regenerateRequested"]) == ("second", True)
    assert (row["reviewedBy"], row["reviewedAt"], row["rejectedSha256Json"]) == (
        first["reviewedBy"], first["reviewedAt"], first["rejectedSha256Json"])


@pytest.mark.parametrize("regenerate", [False, True])
def test_reject_refuses_a_confirmed_copy_with_or_without_regenerate(db, regenerate):
    _generated(db)
    _confirm(db)
    _refused(db, "CALCULATOR_IN_CATALOGUE", 409, lambda: store.reject(
        db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="carol", reason="r",
        regenerate=regenerate))
    assert db.row()["status"] == "active" and "rejectedSha256Json" not in db.row()


def test_reject_retired_copy_refused_with_or_without_regenerate(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="owner", reason="wrong")
    assert db.row()["status"] == "retired"

    for regenerate in (False, True):
        _refused(db, "CALCULATOR_IN_CATALOGUE", 409, lambda: store.reject(
            db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="carol", reason="r",
            regenerate=regenerate))

    blocked = store.load_blocked(db, PROJECT)[IRI]
    assert blocked["status"] == "retired" and blocked["sha256"] == GOOD_SHA
    assert GOOD_SHA not in blocked["sha256s"]  # paused, not rejected
    assert "rejectedSha256Json" not in db.row()


# ----------------------------------------------------------------------------------- reject / regenerate cycle


def test_reject_regenerate_reject_cycle_never_revives_a_rejected_source(db):
    store.save(db, PROJECT, _entry(SHA_A), "alice")
    store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=SHA_A, actor="carol", reason="no",
                 regenerate=True)
    assert store.save(db, PROJECT, _entry(SHA_B), "alice") == {"saved": True, "reason": None}  # the regenerate
    store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=SHA_B, actor="carol", reason="still no",
                 regenerate=False)

    blocked = store.load_blocked(db, PROJECT)

    assert blocked[IRI]["sha256s"] == sorted([SHA_A, SHA_B]) and blocked[IRI]["status"] == "rejected"
    assert store.rejected_source(blocked, IRI, SHA_A) and store.rejected_source(blocked, IRI, SHA_B)
    assert store.save(db, PROJECT, _entry(SHA_A), "alice") == {"saved": False, "reason": "rejected source"}
    assert db.row()["sha256"] == SHA_B and db.row()["status"] == "rejected"


def test_active_row_with_earlier_rejection_still_refuses_that_source(db):
    store.save(db, PROJECT, _entry(SHA_A), "alice")
    store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=SHA_A, actor="carol", reason="no",
                 regenerate=True)
    store.save(db, PROJECT, _entry(SHA_B), "alice")  # B is active and pending

    blocked = store.load_blocked(db, PROJECT)

    assert db.row()["status"] == "active" and db.row()["sha256"] == SHA_B
    assert store.rejected_source(blocked, IRI, SHA_A) and not store.rejected_source(blocked, IRI, SHA_B)
    assert not store.is_blocked(blocked[IRI])
    assert store.save(db, PROJECT, _entry(SHA_A), "alice") == {"saved": False, "reason": "rejected source"}
    assert db.row()["sha256"] == SHA_B


# ------------------------------------------------------------------------------------------------- retire


def test_retire_unknown_or_foreign_id_is_the_same_not_found(db):
    cid = _confirmed_in_two_projects(db)
    unknown = _refused(db, "CATALOGUE_ENTRY_NOT_FOUND", 404, lambda: store.retire(
        db, project=PROJECT, company=COMPANY, catalogue_id="CC-unknown", actor="o", reason="r"))
    foreign = _refused(db, "CATALOGUE_ENTRY_NOT_FOUND", 404, lambda: store.retire(
        db, project=PROJECT, company="GLOBEX", catalogue_id=cid, actor="o", reason="r"))
    assert (unknown.code, unknown.status, unknown.detail) == (foreign.code, foreign.status, foreign.detail)
    assert db.entries[cid]["status"] == "active"


def test_retire_without_a_company_runs_no_statement(db):
    calls_before = len(db.calls)
    with pytest.raises(store.CalculatorReviewError) as err:
        store.retire(db, project=PROJECT, company=None, catalogue_id="CC-x", actor="o", reason="r")
    assert err.value.code == "CATALOGUE_ENTRY_NOT_FOUND" and len(db.calls) == calls_before


def test_retire_from_another_project_of_the_company_retires_entry_and_copies_and_deletes_nothing(db):
    cid = _confirmed_in_two_projects(db)

    result = store.retire(db, project=OTHER, company=COMPANY, catalogue_id=cid, actor="bob", reason="unsafe")

    assert result == {"catalogueId": cid, "retiredCopies": 2, "alreadyRetired": False}
    entry = db.entries[cid]
    assert (entry["status"], entry["retiredBy"], entry["retiredReason"]) == ("retired", "bob", "unsafe")
    assert entry["retiredAt"]
    events = json.loads(entry["historyJson"])
    assert [e["event"] for e in events] == ["confirmed", "retired"]
    assert events[1]["by"] == "bob" and events[1]["project"] == OTHER and events[1]["reason"] == "unsafe"
    for project in (PROJECT, OTHER):
        assert db.row(project)["status"] == "retired"
        assert db.row(project)["reviewReason"] == "retired from the company catalogue: unsafe"
    assert not any("DELETE" in q.upper() for q in db.queries)
    # gone from every read, listed as retired (paused, not rejected) in the blocked read
    assert store.load_catalogue(db, COMPANY) == {} and store.vocabulary_rows(db, COMPANY) == []
    assert store.load_catalogue_entries(db, COMPANY) == []
    for project in (PROJECT, OTHER):
        blocked = store.load_blocked(db, project)[IRI]
        assert blocked["status"] == "retired" and GOOD_SHA not in blocked["sha256s"] and store.is_blocked(blocked)


def test_retire_already_retired_entry_reports_it_and_changes_nothing(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="o", reason="first")
    before = _state(db)

    again = store.retire(db, project=OTHER, company=COMPANY, catalogue_id=cid, actor="p", reason="second")

    assert again == {"catalogueId": cid, "retiredCopies": 0, "alreadyRetired": True}
    assert _state(db) == before


# --------------------------------------------------------------------------- confirming a retired entry again


def test_retired_entry_confirmed_again_reactivates_entry_and_copies(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=OTHER, company=COMPANY, catalogue_id=cid, actor="bob", reason="wrong")
    assert store.load_catalogue(db, COMPANY) == {}

    result = _confirm(db, actor="owner", run={"runId": "run-2", "createdAt": "2026-10-22T09:00:00Z"},
                      meaning="Opening height (reviewed)", unit="mm", allow_reconfirm=True)

    assert result["catalogueId"] == cid and result["reconfirmed"] is True and result["alreadyConfirmed"] is False
    assert result["reactivatedCopies"] == 2
    entry = db.entries[cid]
    assert entry["status"] == "active" and result["entry"] == entry
    assert (entry["reconfirmedBy"], entry["reconfirmedRunId"], entry["meaning"]) == (
        "owner", "run-2", "Opening height (reviewed)")
    assert entry["reconfirmedAt"] and (entry["retiredBy"], entry["retiredReason"]) == ("bob", "wrong")
    assert (entry["confirmedBy"], entry["sourceProject"], entry["sourceRunId"]) == ("alice", PROJECT, "run-1")
    assert [e["event"] for e in json.loads(entry["historyJson"])] == ["confirmed", "retired", "reconfirmed"]
    assert json.loads(entry["historyJson"])[2]["runId"] == "run-2"
    for project in (PROJECT, OTHER):
        assert (db.row(project)["status"], db.row(project)["reviewStatus"]) == ("active", "confirmed")
        assert db.row(project)["reviewReason"] is None
        assert store.load_blocked(db, project) == {}
    assert list(store.load_catalogue(db, COMPANY)) == ["hasopeningheightmm"]
    assert [r["property"] for r in store.vocabulary_rows(db, COMPANY)] == ["hasOpeningHeightMm"]
    assert len(db.entries) == 1  # the same entry, no second node


def test_confirm_again_refused_while_another_entry_holds_the_key(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="o", reason="wrong")
    db.entries["CC-rival"] = {"graph": "CalculatorCatalogue", "company": COMPANY, "catalogueId": "CC-rival",
                              "propertyKey": "hasopeningheightmm", "sha256": "e" * 64, "status": "active"}

    _refused(db, "CATALOGUE_PROPERTY_TAKEN", 409, lambda: _confirm(
        db, run={"runId": "run-2", "createdAt": "2026-10-22T09:00:00Z"}, allow_reconfirm=True))

    assert db.entries[cid]["status"] == "retired" and db.row()["status"] == "retired"
    assert db.names().count("REACTIVATE_ENTRY_QUERY") == 0


def test_reconfirm_retired_copy_refused_without_owner_flag(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=OTHER, company=COMPANY, catalogue_id=cid, actor="bob", reason="wrong")
    history_before = db.entries[cid]["historyJson"]

    run = {"runId": "run-2", "createdAt": "2026-10-22T09:00:00Z"}
    _refused(db, "CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403, lambda: _confirm(db, run=run))
    _refused(db, "CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403, lambda: _confirm(db, run=run, allow_reconfirm=False))
    _refused(db, "CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403, lambda: _confirm(db, run=run, allow_reconfirm="yes"))
    # the owner gate comes right after eligibility, before the sha256 comparison
    _refused(db, "CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403, lambda: _confirm(db, run=run, sha256="f" * 64))

    assert db.entries[cid]["status"] == "retired" and db.entries[cid]["historyJson"] == history_before
    assert db.row(PROJECT)["status"] == "retired" and db.row(OTHER)["status"] == "retired"
    # a first confirm of a pending row with the default flag still works
    _generated(db, iri=IRI2, unit="count", **OWN_CODE)
    assert _confirm(db, data_property_iri=IRI2, sha256=SHA_B2)["alreadyConfirmed"] is False


def test_a_fresh_pending_copy_of_a_retired_source_also_needs_the_owner_flag(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="o", reason="wrong")
    _generated(db, project="str-openings-03")  # another project generates the very same source

    _refused(db, "CATALOGUE_RECONFIRM_OWNER_REQUIRED", 403, lambda: _confirm(
        db, project="str-openings-03", run={"runId": "run-2", "createdAt": "2026-10-22T09:00:00Z"}))
    assert db.entries[cid]["status"] == "retired"


# ---------------------------------------------------------------------------------------------------- reads


def test_catalogue_reads_return_nothing_and_run_no_statement_for_a_falsy_company(db):
    _generated(db)
    _confirm(db)
    calls_before = len(db.calls)
    for company in (None, ""):
        assert store.load_catalogue(db, company) == {}
        assert store.vocabulary_rows(db, company) == []
        assert store.load_catalogue_entries(db, company) == []
    assert len(db.calls) == calls_before


def test_catalogue_reads_see_only_the_entries_of_the_given_company(db):
    _generated(db)
    _confirm(db)
    assert list(store.load_catalogue(db, COMPANY)) == ["hasopeningheightmm"]
    assert store.load_catalogue(db, "GLOBEX") == {}
    assert store.vocabulary_rows(db, "GLOBEX") == [] and store.load_catalogue_entries(db, "GLOBEX") == []
    for name in ("CATALOGUE_QUERY", "VOCABULARY_QUERY", "CATALOGUE_ENTRIES_QUERY", "CATALOGUE_KEY_QUERY",
                 "CATALOGUE_BY_ID_QUERY", "CATALOGUE_CREATE_QUERY", "RETIRE_ENTRY_QUERY", "REACTIVATE_ENTRY_QUERY"):
        text = getattr(store, name)
        assert "$company" in text and "CatalogueCalculator" in text, name
        assert "reviewLock" not in text and "rejectedSha256Json" not in text, name


def test_catalogue_read_drops_retired_rows_and_keeps_the_first_of_a_duplicate_key(db):
    base = {"graph": "CalculatorCatalogue", "company": COMPANY, "propertyKey": "k", "propertyName": "hasK",
            "source": "s", "function": "f", "meaning": "m"}
    db.entries["CC-1"] = {**base, "catalogueId": "CC-1", "sha256": "1" * 64, "status": "active"}
    db.entries["CC-2"] = {**base, "catalogueId": "CC-2", "sha256": "2" * 64, "status": "active"}
    db.entries["CC-3"] = {**base, "catalogueId": "CC-3", "propertyKey": "j", "sha256": "3" * 64, "status": "retired"}

    rows = store.load_catalogue(db, COMPANY)

    assert list(rows) == ["k"] and rows["k"]["catalogueId"] == "CC-1"

    class _Stale:
        def run(self, query, **params):  # a stale row that slipped past the WHERE clause
            return _Result([{**base, "catalogueId": "CC-9", "sha256": "9" * 64, "status": "retired"}])

    assert store.load_catalogue(_Stale(), COMPANY) == {}


def test_vocabulary_rows_carry_meaning_and_unit_never_the_explanation(db):
    _generated(db, explanation="LLM wrote this, never vocabulary")
    _confirm(db, meaning="Opening height", unit=None)
    db.entries[next(iter(db.entries))]["unit"] = None

    rows = store.vocabulary_rows(db, COMPANY)

    assert rows == [{"property": "hasOpeningHeightMm", "meaning": "Opening height", "unit": ""}]
    assert "explanation" not in store.VOCABULARY_QUERY


def test_vocabulary_rows_are_empty_on_any_failure_and_skip_incomplete_rows():
    class _Boom:
        def run(self, query, **params):
            raise RuntimeError("neo4j down")

    assert store.vocabulary_rows(_Boom(), COMPANY) == []

    class _Partial:
        def run(self, query, **params):
            return _Result([
                {"propertyKey": "a", "propertyName": "hasA", "meaning": "A", "unit": "mm", "status": "active"},
                {"propertyKey": "b", "propertyName": "hasB", "meaning": None, "unit": "mm", "status": "active"},
                {"propertyKey": None, "propertyName": "hasC", "meaning": "C", "unit": "", "status": "active"},
            ])

    assert store.vocabulary_rows(_Partial(), COMPANY) == [{"property": "hasA", "meaning": "A", "unit": "mm"}]


def test_catalogue_entries_are_ordered_with_their_provenance(db):
    _generated(db)
    _confirm(db)
    _generated(db, iri=IRI2, **OWN_CODE)
    _confirm(db, data_property_iri=IRI2, sha256=SHA_B2)

    entries = store.load_catalogue_entries(db, COMPANY)

    assert [e["propertyKey"] for e in entries] == ["hascolumnintersectioncount", "hasopeningheightmm"]
    assert entries[1]["sourceProject"] == PROJECT and entries[1]["confirmedBy"] == "alice"
    assert entries[1]["sourceRunId"] == "run-1" and "source" not in entries[1]


def test_candidates_list_pending_rows_and_retired_copies_flagged(db):
    _generated(db, iri=IRI2)                      # pending
    cid = _confirmed_in_two_projects(db)          # confirmed in P1 and P2
    assert [c["dataPropertyIri"] for c in store.load_candidates(db, PROJECT)] == [IRI2]
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="o", reason="r")

    rows = store.load_candidates(db, PROJECT)

    assert [(c["dataPropertyIri"], c["retired"]) for c in rows] == [(IRI2, False), (IRI, True)]
    retired = rows[1]
    assert retired["source"] == SOURCE and retired["function"] == FUNCTION and retired["sha256"] == GOOD_SHA
    assert retired["unit"] == "mm" and retired["catalogueId"] == cid and retired["explanation"]
    assert {"provider", "model", "createdAt", "createdBy", "sourceRunId"} <= set(retired)
    assert [c["dataPropertyIri"] for c in store.load_candidates(db, "str-openings-99")] == []


def test_candidates_exclude_rejected_rows(db):
    _generated(db)
    store.reject(db, project=PROJECT, data_property_iri=IRI, sha256=GOOD_SHA, actor="c", reason="r", regenerate=False)
    assert store.load_candidates(db, PROJECT) == []


def test_verdict_counts_group_by_rule_and_status_and_skip_an_empty_request(db):
    db.verdicts = (
        [{"project": PROJECT, "runId": "run-1", "ruleId": "R1", "status": "violated"}] * 2
        + [{"project": PROJECT, "runId": "run-1", "ruleId": "R1", "status": "satisfied"}]
        + [{"project": PROJECT, "runId": "run-1", "ruleId": "R2", "status": "satisfied"}]
        + [{"project": PROJECT, "runId": "run-2", "ruleId": "R1", "status": "satisfied"}]
        + [{"project": OTHER, "runId": "run-1", "ruleId": "R1", "status": "satisfied"}]
    )

    rows = store.load_verdict_counts(db, PROJECT, "run-1", ["R1"])

    assert rows == [{"ruleId": "R1", "status": "satisfied", "count": 1}, {"ruleId": "R1", "status": "violated", "count": 2}]
    assert len(store.load_verdict_counts(db, PROJECT, "run-1", ["R1", "R2"])) == 3
    calls_before = len(db.calls)
    assert store.load_verdict_counts(db, PROJECT, "run-1", []) == []
    assert store.load_verdict_counts(db, PROJECT, "", ["R1"]) == []
    assert len(db.calls) == calls_before
    assert "ValidationEntity" in store.VERDICT_COUNTS_QUERY and "ValidGraph" in store.VERDICT_COUNTS_QUERY


# ------------------------------------------------------------------------------------- invariants of the module


def test_no_store_statement_deletes_a_calculator_or_catalogue_node(db):
    cid = _confirmed_in_two_projects(db)
    store.retire(db, project=PROJECT, company=COMPANY, catalogue_id=cid, actor="o", reason="r")
    _confirm(db, run={"runId": "run-2", "createdAt": "2026-10-22T09:00:00Z"}, allow_reconfirm=True)
    _generated(db, iri=IRI2)
    store.reject(db, project=PROJECT, data_property_iri=IRI2, sha256=GOOD_SHA, actor="c", reason="r", regenerate=False)

    assert not any("DELETE" in q.upper() for q in db.queries)
    for name in ("REVIEW_LOCK_QUERY", "CONFIRM_ROW_QUERY", "REJECT_ROW_QUERY", "RETIRE_COPIES_QUERY",
                 "REACTIVATE_COPIES_QUERY", "RETIRE_ENTRY_QUERY", "REACTIVATE_ENTRY_QUERY", "CATALOGUE_CREATE_QUERY"):
        assert "DELETE" not in getattr(store, name).upper(), name


def test_every_query_constant_is_known_to_the_fake_and_the_marker_contract_holds():
    queries = {n: v for n, v in vars(store).items() if n.endswith("_QUERY") and isinstance(v, str)}
    assert {n for n, v in queries.items() if "reviewLock" in v} == {"SAVE_STATE_QUERY", "REVIEW_LOCK_QUERY"}
    for name in ("LOAD_QUERY", "SAVE_QUERY", "BLOCKED_QUERY", "CANDIDATES_QUERY"):
        assert "reviewLock" not in queries[name]
    reachable = {"LOAD_QUERY", "SAVE_STATE_QUERY", "SAVE_QUERY", "BLOCKED_QUERY"}
    assert {n for n in reachable if "rejectedSha256Json" in queries[n]} == {"SAVE_STATE_QUERY", "BLOCKED_QUERY"}
    for name, text in queries.items():
        if "CatalogueCalculator" in text:
            assert "reviewLock" not in text and "rejectedSha256Json" not in text, name
    assert queries["SAVE_QUERY"].startswith("MERGE (pc:PropertyCalculator")
    fake = _RowStore()
    for name in queries:
        if name in ("CONTEXT_CLASS_QUERY", "PARTICIPANT_CLASS_QUERY", "CLASS_CATEGORIES_QUERY", "UNLINK_QUERY",
                    "PRUNE_QUERY"):
            continue  # class linking is covered by test_property_scripts
        assert hasattr(fake, "_do_" + name.lower()), name


def test_confirm_and_retire_hold_the_catalogue_lock(monkeypatch):
    seen = []

    class _Lock:
        def __enter__(self):
            seen.append("enter")

        def __exit__(self, *exc):
            seen.append("exit")

    class _Session:
        def execute_write(self, fn, *a, **k):
            seen.append("write")
            return {}

    monkeypatch.setattr(store, "_CATALOGUE_LOCK", _Lock())
    store.confirm(_Session(), project=PROJECT, company=COMPANY, data_property_iri=IRI, sha256="s", run={},
                  actor="a", meaning="m", unit=None, contract_version=1)
    store.retire(_Session(), project=PROJECT, company=COMPANY, catalogue_id="CC-x", actor="a", reason="r")
    assert seen == ["enter", "write", "exit", "enter", "write", "exit"]


# ---------------------------------------------------------------------------------------------------------------
# Phase 1303-22 (D-62): READS_CLASS edges carry the relation of a participant
# ---------------------------------------------------------------------------------------------------------------


class _ClassSession:
    """Records the class-linking statements of save_context_classes; ``existing`` are the project's class labels."""

    def __init__(self, existing=(), categories=()):
        self.existing = list(existing)
        self.categories = list(categories)
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if "revitCategories AS revitCategories" in query:
            return _Result(self.categories)
        if "coalesce(k.label, k.iri) AS label" in query:
            return _Result([{"label": label} for label in self.existing])
        return _Result([])

    def links(self):
        return [(q, p) for q, p in self.calls if "MERGE (k:Class" in q]


def _slab(**extra):
    return {"label": "Slab", "iri": "ex:Slab", "revitCategories": ["OST_Floors"], **extra}


def test_a_participant_writes_its_relation_and_related_to_on_the_edge():
    db = _ClassSession()
    store.save_context_classes(db, PROJECT, IRI, [_slab(relation="hostedBy", relatedTo="Opening")])
    (query, params), = db.links()
    assert "r.relation = $relation" in query and "r.relatedTo = $relatedTo" in query
    assert (params["relation"], params["relatedTo"], params["label"]) == ("hostedBy", "Opening", "Slab")
    assert params["categories"] == ["OST_Floors"] and params["project"] == PROJECT


def test_a_class_without_a_relation_is_linked_exactly_as_before():
    db = _ClassSession()
    store.save_context_classes(db, PROJECT, IRI, [_slab()])
    (query, params), = db.links()
    assert query.startswith(store.CONTEXT_CLASS_QUERY[:40]) and "$relation" not in query
    assert "relation" not in params and "relatedTo" not in params


def test_a_participant_of_a_concept_the_project_has_is_folded_onto_that_class_and_relatedto_follows():
    """No second class for one concept: Slab is Floor, and the relation that points at Slab points at Floor."""
    db = _ClassSession(existing=["Column", "Floor", "Opening"])
    store.save_context_classes(db, PROJECT, IRI, [
        _slab(relation="hostedBy", relatedTo="Opening"),
        {"label": "Column", "iri": "ex:Column", "revitCategories": ["OST_Columns"], "relation": "projectsOnto",
         "relatedTo": "Slab"}])
    labels = [(p["label"], p["relatedTo"]) for _q, p in db.links()]
    assert labels == [("Floor", "Opening"), ("Column", "Floor")]


def test_a_class_that_already_has_the_exact_label_is_never_folded_onto_another_one():
    db = _ClassSession(existing=["Floor", "Slab"])
    store.save_context_classes(db, PROJECT, IRI, [_slab()])
    assert [p["label"] for _q, p in db.links()] == ["Slab"]


def test_the_project_classes_are_read_with_their_stored_revit_categories():
    db = _ClassSession(categories=[{"label": "Floor", "revitCategories": ["OST_Floors"]},
                                   {"label": "Wall", "revitCategories": None}])
    assert store.load_class_categories(db, PROJECT) == {"Floor": ["OST_Floors"], "Wall": []}
    query, params = db.calls[0]
    assert params == {"project": PROJECT} and "$project" in query
