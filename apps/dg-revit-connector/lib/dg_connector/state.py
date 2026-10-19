# -*- coding: utf-8 -*-
"""Connector state store shared by every pyRevit script engine (D-47).

The ribbon buttons, the poll thread and the startup engine are separate
IronPython script engines: module globals are *not* shared between them. Inside
Revit the state therefore lives in a .NET ``Dictionary[str, str]`` attached to
``System.AppDomain.CurrentDomain`` under :data:`STATE_KEY`, so every engine
sees the same values. Outside Revit (CPython tests) a module-level dict is used
instead, with the same API.

Only the ``dgk_`` token, never the password, is ever stored here; the password
exists only for the duration of the sign-in call. ``snapshot()`` never returns
the token, and ``__repr__`` never prints it, so a state dump cannot leak it.

Keys used by the connector:

``url``           DG data-service base URL
``token``         connector session token (``dgk_...``), never shown
``project``       DG project the token is bound to
``user``          account name of the signed-in user
``sessionId``     open mapping session (``ms-...``)
``documentKey``   key of the open Revit document (see :mod:`dg_connector.docs`)
``documentPath``  full path of that document
``creationGuid``  ``Document.CreationGUID`` of that document
``viewId``        view the colours were written in
``message``       last status message for the ribbon / MCP status route
``lastDigest``    digest of the states the view was last painted with

Standard library only; Python 2.7 / 3 syntax (pyRevit's IronPython 2.7 under Revit).
"""
from __future__ import unicode_literals

#: ``AppDomain`` data key holding the shared dictionary.
STATE_KEY = "DG.RevitConnector.State"

#: Every key the connector uses (``token`` is the only secret).
FIELDS = (
    "url",
    "token",
    "project",
    "user",
    "sessionId",
    "documentKey",
    "documentPath",
    "creationGuid",
    "viewId",
    "message",
    "lastDigest",
    "batchDeliveries",
)

#: Fields of one open mapping session: cleared by :meth:`ConnectorState.clear_session`.
SESSION_FIELDS = (
    "sessionId",
    "documentKey",
    "documentPath",
    "creationGuid",
    "viewId",
    "message",
    "lastDigest",
    "batchDeliveries",
)

#: Fields cleared by :meth:`ConnectorState.sign_out` (the DG URL stays).
SIGN_OUT_FIELDS = ("token", "user", "project") + SESSION_FIELDS


def _text(value):
    """Preserve a Python-2 Unicode project/user value in AppDomain state."""
    if value is None:
        return u""
    try:
        if isinstance(value, unicode):
            return value
        if isinstance(value, str):
            return value.decode("utf-8", "replace")
    except NameError:
        if isinstance(value, str):
            return value
    try:
        return unicode(value)
    except NameError:
        return str(value)


# --- backends -----------------------------------------------------------------

class _MemoryBackend(object):
    """Module-level dict backend (CPython tests, anything without .NET)."""

    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value

    def remove(self, key):
        self._data.pop(key, None)

    def clear(self):
        self._data.clear()

    def keys(self):
        return sorted(self._data.keys())


class _AppDomainBackend(object):
    """``System.Collections.Generic.Dictionary[str, str]`` held in AppDomain data."""

    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, key):
        try:
            return self._mapping[key]
        except Exception:
            return None

    def set(self, key, value):
        self._mapping[key] = value

    def remove(self, key):
        try:
            if self._mapping.ContainsKey(key):
                self._mapping.Remove(key)
        except Exception:
            pass

    def clear(self):
        try:
            self._mapping.Clear()
        except Exception:
            pass

    def keys(self):
        try:
            return sorted(_text(key) for key in self._mapping.Keys)
        except Exception:
            return []


_MEMORY_BACKEND = _MemoryBackend()

#: Lazily resolved backend, kept as a one-item list so it is probed once per
#: process and the same store is shared by every engine.
_BACKEND = []


def _appdomain_backend():
    """The AppDomain dictionary backend, or None when System/clr is unavailable."""
    try:
        import clr  # noqa: F401 - only exists under IronPython
    except Exception:
        return None
    try:
        from System import AppDomain
        from System.Collections.Generic import Dictionary
    except Exception:
        return None
    try:
        mapping = AppDomain.CurrentDomain.GetData(STATE_KEY)
        if mapping is None:
            mapping = Dictionary[str, str]()
            AppDomain.CurrentDomain.SetData(STATE_KEY, mapping)
        if not hasattr(mapping, "ContainsKey"):
            return None
        return _AppDomainBackend(mapping)
    except Exception:
        return None


def backend():
    """The active backend: AppDomain dictionary inside Revit, a dict elsewhere."""
    if not _BACKEND:
        found = _appdomain_backend()
        _BACKEND.append(found if found is not None else _MEMORY_BACKEND)
    return _BACKEND[0]


def backend_name():
    """``"appdomain"`` or ``"memory"``: which backend the state lives in."""
    return "memory" if backend() is _MEMORY_BACKEND else "appdomain"


def _key(key):
    name = _text(key).strip()
    if not name:
        raise ValueError("a connector state key must not be empty")
    return name


# --- the store ----------------------------------------------------------------

class ConnectorState(object):
    """The connector's state. Every instance is a view on the same store.

    The store is process-wide on purpose: a ribbon button and the startup
    engine must see the same token and session, so two ``ConnectorState()``
    objects never hold independent copies.
    """

    def get(self, key, default=None):
        """Value stored under ``key``, or ``default``."""
        value = backend().get(_key(key))
        return default if value is None else value

    def set(self, key, value):
        """Store ``value`` under ``key``; ``None`` removes the key."""
        name = _key(key)
        if value is None:
            backend().remove(name)
            return None
        stored = _text(value)
        backend().set(name, stored)
        return stored

    def clear_session(self):
        """Forget the open mapping session, keep the sign-in and the DG URL."""
        for name in SESSION_FIELDS:
            backend().remove(name)

    def sign_out(self):
        """Forget token, user, project and the open session; keep the DG URL."""
        for name in SIGN_OUT_FIELDS:
            backend().remove(name)

    def clear(self):
        """Forget everything, including the DG URL."""
        backend().clear()

    def is_signed_in(self):
        """True when a connector token is stored."""
        return bool(_text(backend().get("token")).strip())

    def snapshot(self):
        """Dict of every stored value except the token, plus ``signedIn``."""
        values = {"signedIn": self.is_signed_in()}
        store = backend()
        for name in store.keys():
            if name == "token":
                continue
            value = store.get(name)
            if value is not None:
                values[name] = value
        return values

    def __repr__(self):
        return "<ConnectorState url={!r} project={!r} user={!r} signedIn={!r}>".format(
            backend().get("url"), backend().get("project"), backend().get("user"),
            self.is_signed_in())


#: Convenience instance for the Revit side (module-level store, no copying).
state = ConnectorState()
