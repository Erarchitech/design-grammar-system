# -*- coding: utf-8 -*-
"""Remembered sign-in of the DG Revit connector (owner request 2026-10-21, amends D-47).

The connector state lives only in Revit's AppDomain, so every Revit start asked for the DG URL, user, password and
project again. This module keeps the last values in ``%APPDATA%\\DG\\revit-connector.json``:

* ``url``, ``user``, ``project`` as plain text (not secrets);
* the password only when the user ticks «Запомнить пароль», and only encrypted with Windows DPAPI for the current
  Windows user (``ProtectedData``, ``DataProtectionScope.CurrentUser``, with a connector-specific entropy). Another
  Windows account or another computer cannot decrypt it; it is never written in clear text and never logged.

Unticking the box or signing out removes the stored password. The protector is injected so CPython tests run without
.NET. Standard library only; Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""
from __future__ import unicode_literals

import base64
import io
import json
import os

FILE_NAME = "revit-connector.json"
PLAIN_FIELDS = ("url", "user", "project")
ENTROPY = b"DG.RevitConnector.Password.v1"


def default_path():
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(root, "DG", FILE_NAME)


class DpapiProtector(object):
    """Windows DPAPI for the current user (only inside Revit / .NET)."""

    def __init__(self):
        import clr  # noqa: F401  (IronPython / pythonnet)

        clr.AddReference("System.Security")
        from System.Security.Cryptography import DataProtectionScope, ProtectedData

        self._data = ProtectedData
        self._scope = DataProtectionScope.CurrentUser

    def protect(self, text):
        from System import Array, Byte
        from System.Text import Encoding

        raw = Encoding.UTF8.GetBytes(text)
        entropy = Array[Byte](bytearray(ENTROPY))
        sealed = self._data.Protect(raw, entropy, self._scope)
        return base64.b64encode(bytes(bytearray(sealed))).decode("ascii")

    def unprotect(self, blob):
        from System import Array, Byte
        from System.Text import Encoding

        sealed = Array[Byte](bytearray(base64.b64decode(blob)))
        entropy = Array[Byte](bytearray(ENTROPY))
        return Encoding.UTF8.GetString(self._data.Unprotect(sealed, entropy, self._scope))


def _protector():
    try:
        return DpapiProtector()
    except Exception:
        return None  # outside Windows/.NET: the password is simply not remembered


def load(path=None, protector=None):
    """``{url, user, project, password, rememberPassword}``; missing or unreadable parts are empty."""
    path = path or default_path()
    out = {"url": "", "user": "", "project": "", "password": "", "rememberPassword": False}
    try:
        with io.open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return out
    if not isinstance(data, dict):
        return out
    for key in PLAIN_FIELDS:
        value = data.get(key)
        if isinstance(value, (type(u""), str)):
            out[key] = value
    blob = data.get("passwordDpapi")
    if blob:
        out["rememberPassword"] = True
        protector = protector or _protector()
        if protector is not None:
            try:
                out["password"] = protector.unprotect(blob)
            except Exception:
                out["password"] = ""  # another Windows user or a damaged blob: ask again
    return out


def save(url, user, project, password=None, remember_password=False, path=None, protector=None):
    """Store the last sign-in. The password is stored only when ``remember_password`` and DPAPI is available;
    otherwise any stored password is removed."""
    path = path or default_path()
    data = {"url": url or "", "user": user or "", "project": project or ""}
    if remember_password and password:
        protector = protector or _protector()
        if protector is not None:
            data["passwordDpapi"] = protector.protect(password)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, sort_keys=True))
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)
    return data


def forget_password(path=None):
    """Drop the stored password, keep URL / user / project (used by «Выход»)."""
    current = load(path=path, protector=_NoProtector())
    save(current["url"], current["user"], current["project"], path=path)


class _NoProtector(object):
    def unprotect(self, blob):
        return ""
