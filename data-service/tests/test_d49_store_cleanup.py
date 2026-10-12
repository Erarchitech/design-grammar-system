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
