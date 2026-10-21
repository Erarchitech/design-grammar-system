# -*- coding: UTF-8 -*-
"""«Вход» - sign in to the Design Grammars data service (D-47).

The dialog asks for the DG URL, the user, the password and the project. The
password is handed to :func:`dg_connector.dg_client.sign_in`; it is never kept in
the connector state, never written to a log and never shown in a message. Only
the returned ``dgk_`` token is kept, in the shared connector state.

Owner request 2026-10-21 (amends D-47): the last URL, user and project are
remembered across Revit sessions in ``%APPDATA%/DG/revit-connector.json``, and the
password too when «Запомнить пароль» is ticked - only DPAPI-encrypted for the
current Windows user (:mod:`dg_connector.remember`).
"""

import os
import sys

from pyrevit import forms

#: DG data service of the local Docker stack.
DEFAULT_URL = "http://localhost:8000"

#: Project the mapping demo works in.
DEFAULT_PROJECT = "v12-hexagonal-facade-01"

#: The dialog of ``lib/dg_connector``.
XAML_NAME = "signin.xaml"

#: ``<extension>/lib``: filled by :func:`ensure_lib`.
LIB_DIR = ""


def extension_dir():
    """``<extension>`` folder of this push button (``DG.tab/Connector.panel/X.pushbutton``)."""
    here = os.path.dirname(os.path.abspath(__file__))
    pushbutton = os.path.dirname(here)
    panel = os.path.dirname(pushbutton)
    tab = os.path.dirname(panel)
    return tab


def ensure_lib():
    """Put ``<extension>/lib`` first on sys.path and return it."""
    lib = os.path.join(extension_dir(), "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    return lib


class SignInWindow(forms.WPFWindow):
    """The sign-in dialog: URL, user, password, project, OK / Cancel."""

    def __init__(self, xaml, store, remembered=None):
        forms.WPFWindow.__init__(self, xaml)
        remembered = remembered or {}
        self.accepted = False
        self.password = None
        self.remember_password = bool(remembered.get("rememberPassword"))
        self.url = store.get("url") or remembered.get("url") or DEFAULT_URL
        self.user = store.get("user") or remembered.get("user") or ""
        self.project = store.get("project") or remembered.get("project") or DEFAULT_PROJECT
        self.urlBox.Text = self.url
        self.userBox.Text = self.user
        self.projectBox.Text = self.project
        try:
            self.rememberBox.IsChecked = self.remember_password
            if remembered.get("password"):
                self.passwordBox.Password = remembered["password"]
                self.okButton.Focus()
            else:
                self.passwordBox.Focus()
        except Exception:
            pass

    def ok_click(self, sender, args):
        self.url = (self.urlBox.Text or "").strip()
        self.user = (self.userBox.Text or "").strip()
        self.project = (self.projectBox.Text or "").strip()
        self.password = self.passwordBox.Password
        try:
            self.remember_password = bool(self.rememberBox.IsChecked)
        except Exception:
            self.remember_password = False
        try:
            self.passwordBox.Clear()  # the dialog keeps no copy of the password
        except Exception:
            pass
        self.accepted = True
        self.Close()

    def cancel_click(self, sender, args):
        self.password = None
        self.accepted = False
        self.Close()


def sign_in(window, store, client, remember=None):
    """Sign in with what the dialog holds, store the token, remember the last entries, drop the password."""
    url = window.url or DEFAULT_URL
    project = window.project or DEFAULT_PROJECT
    user = window.user
    password = window.password
    window.password = None
    try:
        result = client.sign_in(url, user, password, project)
    except client.DgClientError as error:
        forms.alert("DG sign-in failed: {}\n{}".format(error.code, error.message),
                    title="DG")
        return False
    except Exception as error:
        forms.alert("DG sign-in failed: {}".format(error), title="DG")
        return False
    if remember is not None:
        try:  # only after a successful sign-in, so a wrong password is never remembered
            remember.save(url, user, result.get("project") or project, password=password,
                          remember_password=getattr(window, "remember_password", False))
        except Exception:
            pass
    password = None
    window.password = None
    signed_in_project = result.get("project") or project
    store.set("url", url)
    store.set("token", result.get("token"))
    store.set("user", user)
    store.set("project", signed_in_project)
    store.set("message", u"Signed in to DG as {}".format(user or u"the connector"))
    forms.alert(u"Signed in to DG as {} (project {}).".format(
        user or u"the connector", signed_in_project), title="DG")
    return True


def main():
    global LIB_DIR
    LIB_DIR = ensure_lib()
    try:
        from dg_connector import dg_client
        from dg_connector import remember
        from dg_connector import state as connector_state
    except Exception as error:
        forms.alert("DG connector library failed to load:\n{}".format(error), title="DG")
        return
    store = connector_state.state
    try:
        remembered = remember.load()
    except Exception:
        remembered = {}
    window = SignInWindow(os.path.join(LIB_DIR, "dg_connector", XAML_NAME), store, remembered)
    remembered = None
    window.ShowDialog()
    if not window.accepted:
        return
    sign_in(window, store, dg_client, remember)


main()
