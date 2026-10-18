# -*- coding: UTF-8 -*-
"""«Выход» - sign out of DG and forget the connector session (D-47).

Deletes the connector session in DG (best effort: a failure is reported, not
raised) and clears the local token, user, project and open session. The DG URL
stays, so the next sign-in prefills it.
"""

import os
import sys

from pyrevit import forms


def ensure_lib():
    """Put ``<extension>/lib`` first on sys.path and return it."""
    here = os.path.dirname(os.path.abspath(__file__))
    pushbutton = os.path.dirname(here)
    panel = os.path.dirname(pushbutton)
    tab = os.path.dirname(panel)
    extension = os.path.dirname(tab)
    lib = os.path.join(extension, "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    return lib


def main():
    ensure_lib()
    try:
        from dg_connector import dg_client
        from dg_connector import state as connector_state
    except Exception as error:
        forms.alert("DG connector library failed to load:\n{}".format(error), title="DG")
        return
    store = connector_state.state
    url = store.get("url") or dg_client.DEFAULT_BASE_URL
    token = store.get("token") or ""
    confirmed = False
    if token:
        try:
            confirmed = dg_client.sign_out(url, token)
        except Exception:
            confirmed = False
    store.sign_out()
    store.set("message", "Signed out of DG")
    if confirmed:
        forms.alert("Signed out of DG.", title="DG")
    else:
        forms.alert("Signed out locally; DG did not confirm the sign-out.", title="DG")


main()
