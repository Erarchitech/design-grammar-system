"""GHIN-04 / D-22 structural assertion (Phase 38 Plan 04).

The generation modules (`cg_input_generation`, `cg_input_sampler`,
`cg_input_bindings`) must never reach the Grasshopper canvas bridge
(`gh_bridge`) and must never import the accept-time persistence module
plan 38-05 creates (`cg_paramstate_store`) -- the whole point of splitting
"generate a candidate" from "apply an accepted candidate" into separate
plans. This file turns that separation into an executable assertion,
walking the TRANSITIVE first-party import closure of the three modules via
`ast` -- never by importing them and inspecting the interpreter's already-
loaded module registry, which would pass vacuously by picking up whatever
the test session already loaded regardless of what these modules actually
import.

A failure here means the generation/application separation has been
breached, not that a lint rule is unhappy.
"""

from __future__ import annotations

import ast
import os

_DATA_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..")

_ENTRY_MODULES = ("cg_input_generation", "cg_input_sampler", "cg_input_bindings")

_FORBIDDEN_BRIDGE_IMPORT = "gh_bridge"
_FORBIDDEN_PERSISTENCE_IMPORT = "cg_paramstate_store"

_WRITE_TOKENS = ("MERGE", "CREATE (", "SET ")


def _module_path(name: str) -> "str | None":
    path = os.path.join(_DATA_SERVICE_DIR, f"{name}.py")
    return path if os.path.isfile(path) else None


def _imported_names(path: str) -> set[str]:
    """Top-level module names this file imports, parsed via `ast` -- never
    by importing the module and inspecting the interpreter's module registry."""
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _transitive_closure(entry_modules) -> set[str]:
    """Every first-party module name reachable from `entry_modules` via
    imports, followed recursively. A name with no corresponding `.py` file
    in `data-service/` (stdlib or third-party) terminates that branch
    without recursing further."""
    seen: set[str] = set()
    frontier = list(entry_modules)
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        path = _module_path(name)
        if path is None:
            continue
        for imported in _imported_names(path):
            if imported not in seen:
                frontier.append(imported)
    return seen


def test_entry_modules_exist():
    for name in _ENTRY_MODULES:
        assert _module_path(name) is not None, f"{name}.py not found under data-service/"


def test_gh_bridge_not_in_transitive_import_closure():
    closure = _transitive_closure(_ENTRY_MODULES)
    assert _FORBIDDEN_BRIDGE_IMPORT not in closure, (
        f"{_FORBIDDEN_BRIDGE_IMPORT!r} appeared in the transitive import closure of "
        f"{_ENTRY_MODULES} -- GHIN-04/D-22 violated: the generation path must never reach the "
        f"Grasshopper canvas bridge. Closure was: {sorted(closure)}"
    )


def test_cg_paramstate_store_not_imported_by_generation():
    path = _module_path("cg_input_generation")
    assert path is not None
    assert _FORBIDDEN_PERSISTENCE_IMPORT not in _imported_names(path), (
        f"cg_input_generation.py imports {_FORBIDDEN_PERSISTENCE_IMPORT!r} -- the generation "
        f"and application (accept) paths must stay separate (D-22). This assertion is written "
        f"BEFORE plan 38-05 creates that module specifically so the moment they are wired "
        f"together, this test fails."
    )


def test_no_write_tokens_in_generation_module_sources():
    for name in _ENTRY_MODULES:
        path = _module_path(name)
        assert path is not None
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        for token in _WRITE_TOKENS:
            assert token not in text, (
                f"{name}.py contains the write token {token!r} -- the generation path must "
                f"perform zero graph writes (T-38-13)."
            )
