# -*- coding: UTF-8 -*-
"""«Вход» - sign in to the Design Grammars data service (D-47).

The dialog asks for the DG URL, the user, the password and the project. The
password is handed to :func:`dg_connector.dg_client.sign_in` and then dropped:
it is never stored in the connector state, never written to a log and never
shown in a message. Only the returned ``dgk_`` token is kept, in the shared
connector state (AppDomain-backed, so the other pyRevit engines see it).
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
    return os.path.dirname(tab)


def ensure_lib():
    """Put ``<extension>/lib`` first on sys.path and return it."""
    lib = os.path.join(extension_dir(), "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    return lib


class SignInWindow(forms.WPFWindow):
    """The sign-in dialog: URL, user, password, project, OK / Cancel."""

    def __init__(self, xaml, store):
        forms.WPFWindow.__init__(self, xaml)
        self.accepted = False
        self.password = None
        self.url = store.get("url") or DEFAULT_URL
        self.user = store.get("user") or ""
        self.project = store.get("project") or DEFAULT_PROJECT
        self.urlBox.Text = self.url
        self.userBox.Text = self.user
        self.projectBox.Text = self.project
        try:
            self.passwordBox.Focus()
        except Exception:
            pass

    def ok_click(self, sender, args):
        self.url = (self.urlBox.Text or "").strip()
        self.user = (self.userBox.Text or "").strip()
        self.project = (self.projectBox.Text or "").strip()
        self.password = self.passwordBox.Password
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


def sign_in(window, store, client):
    """Sign in with what the dialog holds, store the token, drop the password."""
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
    finally:
        password = None
        window.password = None
    signed_in_project = result.get("project") or project
    store.set("url", url)
    store.set("token", result.get("token"))
    store.set("user", user)
    store.set("project", signed_in_project)
    store.set("message", "Signed in to DG as {}".format(user or "the connector"))
    forms.alert("Signed in to DG as {} (project {}).".format(
        user or "the connector", signed_in_project), title="DG")
    return True


def main():
    global LIB_DIR
    LIB_DIR = ensure_lib()
    try:
        from dg_connector import dg_client
        from dg_connector import state as connector_state
    except Exception as error:
        forms.alert("DG connector library failed to load:\n{}".format(error), title="DG")
        return
    store = connector_state.state
    window = SignInWindow(os.path.join(LIB_DIR, "dg_connector", XAML_NAME), store)
    window.ShowDialog()
    if not window.accepted:
        return
    sign_in(window, store, dg_client)


main()
