"""Phase 1308 plan 08 (WEBUI-11, D-47, D-49, D-33): the one-off store cleanup script.

Every test redirects each store to ``tmp_path`` (the ``auth`` file constants,
``connectors.CREDENTIALS_FILE`` and ``DG_DATA_DIR`` for the policy store) --
the live ``data-service/data`` directory is never read or written, and every
token hash below is an obviously fake value.
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
import d49_store_cleanup as d49  # noqa: E402

NOW = 1_800_000_000
FAKE_HASH_A = "a" * 64
FAKE_HASH_B = "b" * 64
FAKE_HASH_C = "c" * 64


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setenv("DG_DATA_DIR", str(tmp_path))


def _write(path, key, rows):
    path.write_text(json.dumps({key: rows}, indent=2), encoding="utf-8")


def _credential(cid, *, revoked=False, extra=None):
    row = {
        "credential_id": cid,
        "connector_id": "grasshopper",
        "label": "",
        "project": "default-project",
        "token_hash": FAKE_HASH_A,
        "created_at": "2026-01-01T00:00:00+00:00",
        "revoked": revoked,
        "last_connection": None,
    }
    row.update(extra or {})
    return row


def _credentials_fixture(tmp_path):
    rows = [
        _credential("c1"),
        _credential("c2", revoked=True),
        _credential("c3", extra={"label": "kept-label"}),
    ]
    _write(tmp_path / "connector-credentials.json", "credentials", rows)
    return rows


def _read_credentials(tmp_path):
    return json.loads((tmp_path / "connector-credentials.json").read_text(encoding="utf-8"))[
        "credentials"
    ]


class TestCredentialRetirement:
    def test_dry_run_reports_counts_and_writes_nothing(self, tmp_path):
        _credentials_fixture(tmp_path)
        before = (tmp_path / "connector-credentials.json").read_bytes()

        code, status, counts = d49.run(now=NOW)

        assert (code, status) == (0, d49.STATUS_DRY_RUN_OK) == (0, "dry-run-ok")
        assert counts["credentials_to_retire"] == 2
        assert counts["credentials_already_revoked"] == 1
        assert (tmp_path / "connector-credentials.json").read_bytes() == before

    def test_apply_retires_only_active_credentials(self, tmp_path):
        original = _credentials_fixture(tmp_path)

        code, status, counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (0, d49.STATUS_APPLIED) == (0, "applied")
        assert counts["credentials_to_retire"] == 2
        rows = _read_credentials(tmp_path)
        assert [r["credential_id"] for r in rows] == ["c1", "c2", "c3"]  # ordering
        for index in (0, 2):
            assert rows[index]["revoked"] is True
            assert rows[index]["retired"] == "D-49" == d49.RETIRED_MARKER
            assert rows[index]["revoked_at"].startswith("2027-01-15T")
            # every other field survives
            for field, value in original[index].items():
                if field != "revoked":
                    assert rows[index][field] == value
        # EDGE adjacency: the already-revoked credential is untouched
        assert rows[1] == original[1]
        assert "retired" not in rows[1] and "revoked_at" not in rows[1]

    def test_second_apply_is_nothing_to_do_and_changes_no_file(self, tmp_path):
        _credentials_fixture(tmp_path)
        d49.run(apply=True, now=NOW)
        after_first = (tmp_path / "connector-credentials.json").read_bytes()

        code, status, counts = d49.run(apply=True, now=NOW + 60)

        assert (code, status) == (0, d49.STATUS_NOTHING) == (0, "nothing-to-do")
        assert counts["credentials_to_retire"] == 0
        assert counts["credentials_already_revoked"] == 3
        assert (tmp_path / "connector-credentials.json").read_bytes() == after_first

    def test_dry_run_with_nothing_to_do_reports_it(self, tmp_path):
        code, status, _counts = d49.run(now=NOW)
        assert (code, status) == (0, "nothing-to-do")

    def test_missing_credential_store_counts_as_empty_and_stays_missing(self, tmp_path):
        code, status, counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (0, "nothing-to-do")
        assert counts["credentials_to_retire"] == 0
        assert not (tmp_path / "connector-credentials.json").exists()

    @pytest.mark.parametrize("apply", [False, True])
    def test_malformed_credential_store_aborts_with_exit_3(self, tmp_path, apply):
        path = tmp_path / "connector-credentials.json"
        path.write_text("{not json", encoding="utf-8")
        before = path.read_bytes()

        code, status, _counts = d49.run(apply=apply, now=NOW)

        assert (code, status) == (3, d49.STATUS_UNREADABLE) == (3, "store-unreadable")
        assert path.read_bytes() == before

    def test_credentials_list_of_wrong_type_is_unreadable(self, tmp_path):
        path = tmp_path / "connector-credentials.json"
        path.write_text(json.dumps({"credentials": "oops"}), encoding="utf-8")
        code, status, _counts = d49.run(apply=True, now=NOW)
        assert (code, status) == (3, "store-unreadable")


class TestCommandLine:
    def test_help_lists_apply_and_no_target_override(self, capsys):
        with pytest.raises(SystemExit) as exc:
            d49.main(["--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "--apply" in out
        for forbidden in ("--user", "--username", "--project", "--target", "--settings"):
            assert forbidden not in out

    def test_unknown_flag_is_rejected(self):
        with pytest.raises(SystemExit) as exc:
            d49.main(["--username", "someone@dg.local"])
        assert exc.value.code == 2

    def test_main_defaults_to_dry_run(self, tmp_path, capsys):
        _credentials_fixture(tmp_path)
        before = (tmp_path / "connector-credentials.json").read_bytes()

        assert d49.main([]) == 0

        out = capsys.readouterr().out
        assert out.strip().splitlines()[-1] == "dry-run-ok"
        assert (tmp_path / "connector-credentials.json").read_bytes() == before

    def test_main_apply_prints_counts_and_status_only(self, tmp_path, capsys):
        _credentials_fixture(tmp_path)

        assert d49.main(["--apply"]) == 0

        out = capsys.readouterr().out
        assert out.strip().splitlines()[-1] == "applied"
        assert not re.search(r"[0-9a-f]{64}", out)
        assert FAKE_HASH_A not in out
        assert "dgc_" not in out

    def test_main_exit_code_for_unreadable_store(self, tmp_path, capsys):
        (tmp_path / "connector-credentials.json").write_text("[]", encoding="utf-8")
        assert d49.main(["--apply"]) == 3
        assert capsys.readouterr().out.strip().splitlines()[-1] == "store-unreadable"

    def test_module_does_not_import_neo4j(self):
        source = open(d49.__file__, encoding="utf-8").read()
        assert "neo4j" not in source.lower()


# ---------------------------------------------------------------------------
# Task 2: the UAT account and project across every auth store
# ---------------------------------------------------------------------------

UAT = d49.UAT_USERNAME
UAT_PROJ = d49.UAT_PROJECT
OTHER_USER = "other@dg.local"
OTHER_PROJ = "other-project"

# store file name -> (JSON key, count key). connector-access holds two keys.
STORES = {
    "auth-users.json": ("users", "users"),
    "auth-sessions.json": ("sessions", "sessions"),
    "auth-memberships.json": ("memberships", "memberships"),
    "auth-invites.json": ("invites", "invites"),
    "auth-delegated-tokens.json": ("tokens", "delegated_tokens"),
    "auth-connector-sessions.json": ("sessions", "connector_sessions"),
    "degram-grants.json": ("grants", "degram_grants"),
    "degram-grant-requests.json": ("requests", "degram_grant_requests"),
    "degram-pairings.json": ("pairings", "pairings"),
    "auth-project-companies.json": ("companies", "project_companies"),
    "degram-policy.json": ("policies", "export_policies"),
}


def _user_row(name):
    return {"username": name, "password_hash": "scrypt$fake", "is_admin": False, "created_at": 1}


def _seed_rows():
    """Per store: (rows to be removed, rows that must stay)."""
    keep_a, keep_b = FAKE_HASH_B, FAKE_HASH_C
    return {
        "auth-users.json": (
            [_user_row(UAT)],
            [_user_row(OTHER_USER), _user_row("third@dg.local")],
        ),
        "auth-sessions.json": (
            [{"token_hash": FAKE_HASH_A, "username": UAT, "expires_at": NOW, "revoked": False}],
            [{"token_hash": keep_a, "username": OTHER_USER, "expires_at": NOW, "revoked": False}],
        ),
        "auth-memberships.json": (
            [{"username": UAT, "project": UAT_PROJ, "role": "owner", "granted_at": 1}],
            [{"username": OTHER_USER, "project": OTHER_PROJ, "role": "owner", "granted_at": 1}],
        ),
        "auth-invites.json": (
            [
                {"code_hash": FAKE_HASH_A, "username": UAT, "project": OTHER_PROJ, "role": "viewer",
                 "created_by": OTHER_USER, "used": False},
                {"code_hash": FAKE_HASH_B, "username": OTHER_USER, "project": OTHER_PROJ, "role": "viewer",
                 "created_by": UAT, "used": False},
            ],
            [{"code_hash": keep_b, "username": "x@dg.local", "project": OTHER_PROJ, "role": "viewer",
              "created_by": OTHER_USER, "used": False}],
        ),
        "auth-delegated-tokens.json": (
            [{"token_hash": FAKE_HASH_A, "username": UAT, "project": UAT_PROJ, "revoked": False}],
            [{"token_hash": keep_a, "username": OTHER_USER, "project": OTHER_PROJ, "revoked": False}],
        ),
        "auth-connector-sessions.json": (
            [{"token_hash": FAKE_HASH_A, "username": UAT, "project": UAT_PROJ, "revoked": False}],
            [{"token_hash": keep_a, "username": OTHER_USER, "project": OTHER_PROJ, "revoked": False}],
        ),
        "degram-grants.json": (
            [{"grant_id": "g1", "username": UAT, "project": UAT_PROJ, "revoked": False}],
            [{"grant_id": "g2", "username": OTHER_USER, "project": OTHER_PROJ, "revoked": False}],
        ),
        "degram-grant-requests.json": (
            [{"request_id": "r1", "username": UAT, "project": UAT_PROJ, "status": "pending"}],
            [{"request_id": "r2", "username": OTHER_USER, "project": OTHER_PROJ, "status": "pending"}],
        ),
        "degram-pairings.json": (
            [{"pairing_id": "p1", "username": UAT, "revoked": False}],
            [{"pairing_id": "p2", "username": OTHER_USER, "revoked": False}],
        ),
        "auth-project-companies.json": (
            [{"project": UAT_PROJ, "company": "UAT Co", "updated_at": 1}],
            [{"project": OTHER_PROJ, "company": "Real Co", "updated_at": 1}],
        ),
        "degram-policy.json": (
            [{"project": UAT_PROJ, "providerExportAllowed": False, "wholeDefinitionAllowed": False}],
            [{"project": OTHER_PROJ, "providerExportAllowed": True, "wholeDefinitionAllowed": False}],
        ),
    }


def _interleave(drop, keep):
    """keep[0], drop..., keep[1:] so removal has to preserve the order around it."""
    return [keep[0], *drop, *keep[1:]]


def _seed_all(tmp_path, *, with_access=True):
    seeded = _seed_rows()
    for name, (key, _count) in STORES.items():
        drop, keep = seeded[name]
        _write(tmp_path / name, key, _interleave(drop, keep))
    if with_access:
        grants = (
            [{"access_id": "a1", "username": UAT, "project": UAT_PROJ, "connector_id": "revit", "revoked": False}],
            [{"access_id": "a2", "username": OTHER_USER, "project": OTHER_PROJ, "connector_id": "revit", "revoked": False}],
        )
        requests = (
            [{"request_id": "q1", "username": UAT, "project": UAT_PROJ, "connector_id": "revit", "status": "pending"}],
            [{"request_id": "q2", "username": OTHER_USER, "project": OTHER_PROJ, "connector_id": "revit", "status": "pending"}],
        )
        (tmp_path / "connector-access.json").write_text(
            json.dumps(
                {
                    "grants": _interleave(*grants),
                    "requests": _interleave(*requests),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        seeded["connector-access.json"] = (grants, requests)
    _credentials_fixture(tmp_path)
    return seeded


def _snapshot(tmp_path):
    return {p.name: p.read_bytes() for p in sorted(tmp_path.iterdir()) if p.is_file()}


def _rows(tmp_path, name, key):
    return json.loads((tmp_path / name).read_text(encoding="utf-8"))[key]


class TestUatAccountRemoval:
    def test_dry_run_reports_counts_per_store_and_writes_nothing(self, tmp_path):
        _seed_all(tmp_path)
        before = _snapshot(tmp_path)

        code, status, counts = d49.run(now=NOW)

        assert (code, status) == (0, "dry-run-ok")
        assert counts["credentials_to_retire"] == 2
        assert counts["credentials_already_revoked"] == 1
        for _name, (_key, count_key) in STORES.items():
            expected = 2 if count_key == "invites" else 1
            assert counts[count_key] == expected, count_key
        assert counts["connector_access_grants"] == 1
        assert counts["connector_access_requests"] == 1
        assert _snapshot(tmp_path) == before

    @pytest.mark.parametrize("name", sorted(STORES))
    def test_apply_removes_only_uat_rows_and_keeps_order(self, tmp_path, name):
        seeded = _seed_all(tmp_path)
        key, _count = STORES[name]

        code, status, _counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (0, "applied")
        assert _rows(tmp_path, name, key) == seeded[name][1]

    def test_apply_removes_connector_access_grants_and_requests(self, tmp_path):
        seeded = _seed_all(tmp_path)

        d49.run(apply=True, now=NOW)

        payload = json.loads((tmp_path / "connector-access.json").read_text(encoding="utf-8"))
        assert payload["grants"] == seeded["connector-access.json"][0][1]
        assert payload["requests"] == seeded["connector-access.json"][1][1]

    def test_apply_still_retires_credentials_in_the_same_run(self, tmp_path):
        _seed_all(tmp_path)

        d49.run(apply=True, now=NOW)

        rows = _read_credentials(tmp_path)
        assert [r["revoked"] for r in rows] == [True, True, True]
        assert [r.get("retired") for r in rows] == ["D-49", None, "D-49"]

    def test_second_apply_is_nothing_to_do_and_changes_no_file(self, tmp_path):
        _seed_all(tmp_path)
        d49.run(apply=True, now=NOW)
        after_first = _snapshot(tmp_path)

        code, status, counts = d49.run(apply=True, now=NOW + 5)

        assert (code, status) == (0, "nothing-to-do")
        assert all(counts[k] == 0 for k in counts if k != "credentials_already_revoked")
        assert _snapshot(tmp_path) == after_first

    def test_project_rows_of_other_users_are_removed_with_the_project(self, tmp_path):
        """A grant row that names the UAT project belongs to the removed project."""
        _write(
            tmp_path / "degram-grants.json",
            "grants",
            [
                {"grant_id": "g1", "username": OTHER_USER, "project": UAT_PROJ, "revoked": False},
                {"grant_id": "g2", "username": OTHER_USER, "project": OTHER_PROJ, "revoked": False},
            ],
        )
        _write(tmp_path / "auth-users.json", "users", [_user_row(UAT)])

        code, _status, counts = d49.run(apply=True, now=NOW)

        assert code == 0 and counts["degram_grants"] == 1
        assert [r["grant_id"] for r in _rows(tmp_path, "degram-grants.json", "grants")] == ["g2"]

    def test_username_match_is_normalized(self, tmp_path):
        _write(tmp_path / "auth-users.json", "users", [_user_row(OTHER_USER), _user_row(UAT)])
        _write(
            tmp_path / "auth-sessions.json",
            "sessions",
            [{"token_hash": FAKE_HASH_A, "username": f"  {UAT.upper()} ", "expires_at": NOW}],
        )
        d49.run(apply=True, now=NOW)
        assert _rows(tmp_path, "auth-sessions.json", "sessions") == []
        assert [r["username"] for r in _rows(tmp_path, "auth-users.json", "users")] == [OTHER_USER]

    def test_missing_stores_stay_missing(self, tmp_path):
        _write(tmp_path / "auth-users.json", "users", [_user_row(UAT)])
        _write(
            tmp_path / "auth-memberships.json",
            "memberships",
            [{"username": UAT, "project": UAT_PROJ, "role": "owner", "granted_at": 1}],
        )

        code, status, _counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (0, "applied")
        present = {p.name for p in tmp_path.iterdir()}
        assert present == {"auth-users.json", "auth-memberships.json"}

    def test_connector_access_file_absent_is_empty_and_not_created(self, tmp_path):
        _seed_all(tmp_path, with_access=False)

        code, _status, counts = d49.run(apply=True, now=NOW)

        assert code == 0
        assert counts["connector_access_grants"] == 0
        assert counts["connector_access_requests"] == 0
        assert not (tmp_path / "connector-access.json").exists()

    def test_connector_access_untouched_when_it_holds_no_uat_rows(self, tmp_path):
        _seed_all(tmp_path)
        grants = [{"access_id": "a2", "username": OTHER_USER, "project": OTHER_PROJ, "revoked": False}]
        (tmp_path / "connector-access.json").write_text(
            json.dumps({"grants": grants, "requests": []}, indent=2), encoding="utf-8"
        )
        before = (tmp_path / "connector-access.json").read_bytes()

        d49.run(apply=True, now=NOW)

        assert (tmp_path / "connector-access.json").read_bytes() == before


class TestRefusals:
    def test_other_member_in_the_uat_project_refuses_with_exit_2(self, tmp_path):
        _seed_all(tmp_path)
        memberships = _rows(tmp_path, "auth-memberships.json", "memberships")
        memberships.append(
            {"username": OTHER_USER, "project": UAT_PROJ, "role": "editor", "granted_at": 2}
        )
        _write(tmp_path / "auth-memberships.json", "memberships", memberships)
        before = _snapshot(tmp_path)

        code, status, _counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (2, d49.STATUS_OTHER_MEMBERS) == (2, "project-has-other-members")
        assert _snapshot(tmp_path) == before

    def test_refusal_applies_to_dry_run_too(self, tmp_path):
        _write(
            tmp_path / "auth-memberships.json",
            "memberships",
            [{"username": OTHER_USER, "project": UAT_PROJ, "role": "owner", "granted_at": 2}],
        )
        assert d49.run(now=NOW)[:2] == (2, "project-has-other-members")

    def test_main_prints_the_refusal_word_and_exits_2(self, tmp_path, capsys):
        _write(
            tmp_path / "auth-memberships.json",
            "memberships",
            [{"username": OTHER_USER, "project": UAT_PROJ, "role": "owner", "granted_at": 2}],
        )
        assert d49.main(["--apply"]) == 2
        assert capsys.readouterr().out.strip().splitlines()[-1] == "project-has-other-members"

    @pytest.mark.parametrize(
        "name",
        sorted(STORES) + ["connector-access.json", "connector-credentials.json"],
    )
    def test_any_malformed_store_aborts_with_exit_3_and_no_writes(self, tmp_path, name):
        _seed_all(tmp_path)
        (tmp_path / name).write_text("{ truncated", encoding="utf-8")
        before = _snapshot(tmp_path)

        code, status, _counts = d49.run(apply=True, now=NOW)

        assert (code, status) == (3, "store-unreadable")
        assert _snapshot(tmp_path) == before

    def test_policy_store_with_wrong_shape_is_unreadable(self, tmp_path):
        (tmp_path / "degram-policy.json").write_text(
            json.dumps({"policies": "nope"}), encoding="utf-8"
        )
        assert d49.run(apply=True, now=NOW)[:2] == (3, "store-unreadable")


class TestOutputHygiene:
    def test_stdout_has_counts_and_status_but_no_secrets(self, tmp_path, capsys):
        _seed_all(tmp_path)

        assert d49.main(["--apply"]) == 0

        out = capsys.readouterr().out
        assert not re.search(r"[0-9a-fA-F]{64}", out)
        assert not re.search(r"\b(dgc|dgs|dgd|dgi|dgp|dgk)_", out)
        assert "scrypt" not in out
        assert UAT not in out and UAT_PROJ not in out
        lines = out.strip().splitlines()
        assert lines[-1] == "applied"
        assert "users: 1" in lines

    def test_dry_run_stdout_ends_with_the_status_word(self, tmp_path, capsys):
        _seed_all(tmp_path)
        assert d49.main([]) == 0
        assert capsys.readouterr().out.strip().splitlines()[-1] == "dry-run-ok"
