# -*- coding: utf-8 -*-
"""Design Grammars Revit connector — pure connector library.

This package is the Revit-independent half of the DG Revit connector. Every
module here is plain Python 3.4 syntax and standard library only, so it runs
inside Revit under IronPython 3.4 (pyRevit puts ``<extension>/lib`` on
``sys.path``) and under a normal CPython for the offline tests.

The Revit API never appears in this package: the Revit side (``revit_io.py``,
``runner.py``) reads elements into plain dicts and calls these modules, and the
modules return plain dicts, so everything here is testable without Revit.

Modules:

``descriptors``
    Revit element rows -> mapping ``ElementDescriptor`` dicts (API contract
    section 1 and section 8.1), a faithful port of ``tools/mapping/revit_read.py``
    plus the adaptive placement-point count.
``docs``
    Document key of a Revit/Grasshopper file name and the session label.
``palette``
    Mapping state -> RGB colour, the same palette as the Grasshopper connector.
``dg_client``
    DG data-service client: sign in as the ``revit`` connector, create, read
    and apply mapping sessions, sign out.
``loop``
    Pure poll decision function of the apply loop (recolour, grace, apply,
    done, idle) plus the per-element lookups the Revit writer needs.
``state``
    The connector's in-memory session state, shared between pyRevit script
    engines through ``AppDomain`` data and a plain dict outside Revit.

Nothing here imports a third-party package, touches the network at import
time, or stores a password.
"""

__all__ = [
    "descriptors",
    "docs",
    "palette",
    "dg_client",
    "loop",
    "state",
]
