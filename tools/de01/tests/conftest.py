"""Shared pytest configuration for tools/de01/tests/.

Registers the `live` marker (mirroring data-service/tests/conftest.py's own `live`
marker precedent) so pytest does not warn about an unregistered marker. Unlike that
conftest, this one does NOT auto-deselect `live`-marked items -- this plan's own
<verify> block explicitly selects with `-k "not live"` rather than relying on
auto-deselection, and the wrapper test's own name already contains "against_golden_fixture"
so a keyword filter works with or without the marker.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: drives the real DE-01 runner against the dev stack (data-service, "
        "dg-reasoner, dotnet, Neo4j). Deselect with `-k \"not live\"` when the stack is down.",
    )
