# -*- coding: utf-8 -*-
"""IronPython 3.4 syntax guard for everything the connector loads in Revit.

CPython happily parses syntax that IronPython 3.4 rejects, so a green CPython
test run does not prove the connector loads inside Revit. This test parses the
files pyRevit really imports and fails on anything newer than Python 3.4:

* f-strings (``JoinedStr``);
* variable annotations (``AnnAssign``);
* the walrus operator (``NamedExpr``);
* ``async`` functions and ``await`` / ``async for`` / ``async with``;
* parameter annotations and return annotations.

It scans every ``.py`` under ``lib/`` and, when they exist, ``startup.py``,
``dg_transport.py``, ``dg_revit_mcp/dg_connector_routes.py`` and every
``DG.tab/**/script.py`` ribbon script.
"""

import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
LIB_DIR = os.path.join(APP_ROOT, "lib")

#: Top-level files of the extension that pyRevit loads directly.
REQUIRED_SCRIPTS = ("startup.py", "dg_transport.py")

#: Files of the DG connector that may exist only after a later plan.
OPTIONAL_SCRIPTS = (os.path.join("dg_revit_mcp", "dg_connector_routes.py"),)

#: The library modules this plan creates.
EXPECTED_LIB_MODULES = (
    "__init__.py",
    "descriptors.py",
    "docs.py",
    "palette.py",
    "dg_client.py",
    "loop.py",
    "state.py",
)

_FORBIDDEN_NODE_NAMES = (
    "JoinedStr",         # f-string
    "AnnAssign",         # x: int = 1
    "NamedExpr",         # (x := 1)
    "AsyncFunctionDef",  # async def
    "Await",             # await
    "AsyncFor",          # async for
    "AsyncWith",         # async with
)

_FORBIDDEN_NODES = tuple(
    node_type for node_type in (getattr(ast, name, None) for name in _FORBIDDEN_NODE_NAMES)
    if node_type is not None)


def python_files(root):
    """Every ``.py`` file under ``root``, skipping ``__pycache__`` and hidden dirs."""
    found = []
    for directory, subdirectories, names in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories
                                   if not name.startswith(".") and name != "__pycache__")
        for name in sorted(names):
            if name.endswith(".py"):
                found.append(os.path.join(directory, name))
    return found


def scanned_files():
    """Every file the guard checks: what exists of the extension's Python code."""
    files = python_files(LIB_DIR)
    for relative in REQUIRED_SCRIPTS + OPTIONAL_SCRIPTS:
        path = os.path.join(APP_ROOT, relative)
        if os.path.isfile(path):
            files.append(path)
    tab_dir = os.path.join(APP_ROOT, "DG.tab")
    if os.path.isdir(tab_dir):
        files.extend(path for path in python_files(tab_dir)
                     if os.path.basename(path) == "script.py")
    return sorted(set(files))


def syntax_problems(source, display_name="<string>"):
    """Every Python-3.5+ construct of ``source`` as ``display_name:line: reason``."""
    tree = ast.parse(source, filename=display_name)
    problems = []
    for node in ast.walk(tree):
        node_type = type(node)
        if node_type in _FORBIDDEN_NODES:
            problems.append("{}:{}: {} is not Python 3.4 syntax".format(
                display_name, getattr(node, "lineno", 0), node_type.__name__))
        if isinstance(node, ast.arg) and getattr(node, "annotation", None) is not None:
            problems.append("{}:{}: parameter {!r} has a type annotation".format(
                display_name, getattr(node, "lineno", 0), getattr(node, "arg", "?")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and getattr(node, "returns", None) is not None:
            problems.append("{}:{}: function {!r} has a return annotation".format(
                display_name, getattr(node, "lineno", 0), getattr(node, "name", "?")))
    return problems


def test_connector_python_is_python34_syntax():
    files = scanned_files()
    assert files, "the IronPython syntax guard scanned no file"
    problems = []
    for path in files:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        problems.extend(syntax_problems(source, path))
    assert problems == [], "Python-3.5+ syntax found:\n" + "\n".join(problems)


def test_the_guard_covers_the_extension_files():
    found = set(os.path.basename(path) for path in scanned_files())
    for module in EXPECTED_LIB_MODULES:
        assert module in found, "lib/dg_connector/{} is missing".format(module)
    assert "startup.py" in found
    assert "dg_transport.py" in found

    lib_files = python_files(LIB_DIR)
    assert len(lib_files) >= len(EXPECTED_LIB_MODULES)
    for path in lib_files:
        assert path.startswith(LIB_DIR), path


def test_the_guard_rejects_a_f_string():
    problems = syntax_problems('name = "x"\nprint(f"{name}")\n', "fstring.py")
    assert problems and "JoinedStr" in problems[0]


def test_the_guard_rejects_a_variable_annotation():
    problems = syntax_problems("count: int = 1\n", "annotated.py")
    assert problems and "AnnAssign" in problems[0]


def test_the_guard_rejects_annotated_arguments_and_returns():
    problems = syntax_problems("def f(a, b: int) -> int:\n    return a + b\n", "signature.py")
    reasons = "\n".join(problems)
    assert "type annotation" in reasons
    assert "return annotation" in reasons


def test_the_guard_rejects_async_syntax():
    problems = syntax_problems(
        "async def f():\n    await g()\n    async with h():\n        pass\n    async for x in y:\n        pass\n",
        "async.py")
    reasons = " ".join(problems)
    for name in ("AsyncFunctionDef", "Await", "AsyncWith", "AsyncFor"):
        assert name in reasons


def test_the_guard_rejects_the_walrus_operator():
    if getattr(ast, "NamedExpr", None) is None:  # the interpreter predates it
        return
    problems = syntax_problems("if (value := 1):\n    pass\n", "walrus.py")
    assert problems and "NamedExpr" in problems[0]
