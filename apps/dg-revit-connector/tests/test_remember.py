# -*- coding: utf-8 -*-
"""Remembered sign-in (owner request 2026-10-21, amends D-47)."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

from dg_connector import remember  # noqa: E402


class FakeProtector(object):
    """Stands in for DPAPI: reversible, and the stored text never equals the password."""

    def protect(self, text):
        return "sealed:" + text[::-1]

    def unprotect(self, blob):
        assert blob.startswith("sealed:")
        return blob[len("sealed:"):][::-1]


def test_url_user_project_are_remembered_and_the_password_is_not_by_default(tmp_path):
    path = str(tmp_path / "revit-connector.json")
    remember.save("http://localhost:8000", "ermolenko", "str-openings-01", password="s3cret", path=path,
                  protector=FakeProtector())
    stored = json.load(open(path, encoding="utf-8"))
    assert stored == {"url": "http://localhost:8000", "user": "ermolenko", "project": "str-openings-01"}
    loaded = remember.load(path=path, protector=FakeProtector())
    assert loaded["user"] == "ermolenko" and loaded["password"] == "" and loaded["rememberPassword"] is False


def test_password_is_stored_only_encrypted_when_asked(tmp_path):
    path = str(tmp_path / "revit-connector.json")
    remember.save("u", "me", "p", password="s3cret", remember_password=True, path=path, protector=FakeProtector())
    text = open(path, encoding="utf-8").read()
    assert "s3cret" not in text and "passwordDpapi" in text
    loaded = remember.load(path=path, protector=FakeProtector())
    assert loaded["password"] == "s3cret" and loaded["rememberPassword"] is True


def test_forget_password_keeps_the_other_fields(tmp_path):
    path = str(tmp_path / "revit-connector.json")
    remember.save("u", "me", "p", password="s3cret", remember_password=True, path=path, protector=FakeProtector())
    remember.forget_password(path=path)
    stored = json.load(open(path, encoding="utf-8"))
    assert stored == {"url": "u", "user": "me", "project": "p"}


def test_unreadable_password_or_file_falls_back_to_asking(tmp_path):
    path = str(tmp_path / "revit-connector.json")
    open(path, "w").write(json.dumps({"url": "u", "user": "me", "project": "p", "passwordDpapi": "garbage"}))

    class Failing(object):
        def unprotect(self, blob):
            raise ValueError("another Windows user")

    loaded = remember.load(path=path, protector=Failing())
    assert loaded["user"] == "me" and loaded["password"] == ""
    assert remember.load(path=str(tmp_path / "missing.json"))["user"] == ""
