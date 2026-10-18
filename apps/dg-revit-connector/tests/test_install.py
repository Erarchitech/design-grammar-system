# -*- coding: utf-8 -*-
"""The installer: a dry-run plan, a real copy and the backup of a live install.

Everything happens in a throw-away folder under the system temp directory; the
real ``%APPDATA%\\pyRevit\\Extensions`` is never touched by a test.

Note on the temp folder: ``tempfile.mkdtemp`` creates a ``0o700`` directory,
whose Windows ACL cannot be written into from this sandbox, so the temp folder
is created with ``os.mkdir`` (no mode) below ``tempfile.gettempdir()``.
"""

import datetime
import io
import os
import shutil
import sys
import tempfile
import uuid

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)

if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

import install as installer  # noqa: E402

NOW = datetime.datetime(2026, 10, 18, 12, 0, 0)
STAMP = "20261018T120000Z"

EXTENSION_FILES = (
    "extension.json",
    "startup.py",
    "dg_transport.py",
    "DG_SharedParameters.txt",
    os.path.join("dg_revit_mcp", "utils.py"),
    os.path.join("dg_revit_mcp", "dg_connector_routes.py"),
    os.path.join("lib", "dg_connector", "revit_io.py"),
    os.path.join("lib", "dg_connector", "runner.py"),
    os.path.join("lib", "dg_connector", "signin.xaml"),
    os.path.join("DG.tab", "Connector.panel", "SignIn.pushbutton", "script.py"),
    os.path.join("DG.tab", "Connector.panel", "SignIn.pushbutton", "bundle.yaml"),
)

NEVER_COPIED = ("tests", "tools", "main.py", "install.py", "README.md", "uv.lock")


def make_temp_dir():
    """A writable folder under the system temp folder (see the module docstring)."""
    path = os.path.join(tempfile.gettempdir(), "dg-install-" + uuid.uuid4().hex[:12])
    os.mkdir(path)
    return path


@pytest.fixture()
def workspace():
    root = make_temp_dir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def target_of(workspace, name=installer.EXTENSION_NAME):
    return os.path.join(workspace, name)


def all_files(root):
    found = []
    for directory, _subdirectories, names in os.walk(root):
        for name in names:
            found.append(os.path.join(directory, name))
    return found


# --- the plan ---------------------------------------------------------------------

def test_dry_run_prints_the_plan_and_writes_nothing(workspace):
    target = target_of(workspace)
    stream = io.StringIO()
    plan = installer.install(APP_ROOT, target, dry_run=True, now=NOW, stream=stream)

    assert plan["installed"] is False
    assert not os.path.exists(target)
    assert plan["target"] == os.path.abspath(target)
    assert plan["exists"] is False
    assert plan["backup"] is None

    output = stream.getvalue()
    assert "dry run" in output
    assert "extension.json" in output
    assert plan["source"] == os.path.abspath(APP_ROOT)
    assert len(plan["files"]) > 30
    assert any(relative.endswith("DG_SharedParameters.txt")
               for relative, _absolute in plan["files"])


def previous_installation(target, marker_name="old.txt", text="previous install"):
    """An earlier connector installation: its extension.json plus a marker file."""
    os.makedirs(target)
    with open(os.path.join(target, "extension.json"), "w", encoding="utf-8") as handle:
        handle.write("{}")
    marker = os.path.join(target, marker_name)
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(text)
    return marker


def test_dry_run_shows_the_backup_path_of_an_existing_installation(workspace):
    target = target_of(workspace)
    previous_installation(target)
    backups = os.path.join(workspace, "backups")
    stream = io.StringIO()

    plan = installer.install(APP_ROOT, target, backup_root=backups, dry_run=True,
                             now=NOW, stream=stream)
    assert plan["exists"] is True
    assert plan["backup"] == os.path.join(backups, STAMP)
    assert "backup" in stream.getvalue()
    assert STAMP in stream.getvalue()
    # a dry run moves and writes nothing
    assert os.path.isfile(os.path.join(target, "old.txt"))
    assert not os.path.exists(backups)


# --- a real copy --------------------------------------------------------------------

def test_install_copies_the_extension_into_a_temp_target(workspace):
    target = target_of(workspace)
    stream = io.StringIO()
    plan = installer.install(APP_ROOT, target, now=NOW, stream=stream)

    assert plan["installed"] is True
    assert plan["copied"] == len(plan["files"])
    assert "copied {} files".format(plan["copied"]) in stream.getvalue()

    for relative in EXTENSION_FILES:
        assert os.path.isfile(os.path.join(target, relative)), relative
    for name in NEVER_COPIED:
        assert not os.path.exists(os.path.join(target, name)), name


def test_install_skips_pycache_and_pyc(workspace):
    source = os.path.join(workspace, "src")
    os.makedirs(os.path.join(source, "dg_revit_mcp", "__pycache__"))
    os.makedirs(os.path.join(source, "lib", "dg_connector"))
    os.makedirs(os.path.join(source, "DG.tab"))
    for relative in ("extension.json", "startup.py", "dg_transport.py",
                     "DG_SharedParameters.txt",
                     os.path.join("dg_revit_mcp", "keep.py"),
                     os.path.join("dg_revit_mcp", "__pycache__", "keep.cpython-314.pyc"),
                     os.path.join("lib", "dg_connector", "__init__.py"),
                     os.path.join("DG.tab", "bundle.yaml")):
        path = os.path.join(source, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")

    target = target_of(workspace)
    plan = installer.install(source, target, now=NOW, stream=io.StringIO())

    copied = [path.replace(target + os.sep, "") for path in all_files(target)]
    assert os.path.join("dg_revit_mcp", "keep.py") in copied
    assert not any("__pycache__" in path for path in copied)
    assert not any(path.endswith(".pyc") for path in copied)
    assert len(plan["files"]) == len(copied)


def test_install_replaces_an_existing_installation_after_a_backup(workspace):
    target = target_of(workspace)
    marker = previous_installation(target, "previous-marker.txt", "the previous connector")
    backups = os.path.join(workspace, "backups")
    stream = io.StringIO()

    plan = installer.install(APP_ROOT, target, backup_root=backups, now=NOW, stream=stream)

    assert plan["installed"] is True
    assert plan["backup"] == os.path.join(backups, STAMP)
    assert plan["backup_path"] == os.path.join(backups, STAMP)
    moved = os.path.join(plan["backup_path"], os.path.basename(target),
                         "previous-marker.txt")
    assert os.path.isfile(moved)
    with open(moved, encoding="utf-8") as handle:
        assert handle.read() == "the previous connector"
    assert not os.path.exists(marker)  # the old folder was moved, not merged
    assert os.path.isfile(os.path.join(target, "extension.json"))
    assert "moved the previous installation" in stream.getvalue()


def test_a_backup_never_overwrites_an_earlier_one(workspace):
    target = target_of(workspace)
    backups = os.path.join(workspace, "backups")
    os.makedirs(os.path.join(backups, STAMP))

    os.makedirs(target)
    plan = installer.install(APP_ROOT, target, backup_root=backups, now=NOW,
                             stream=io.StringIO())
    assert plan["backup_path"] == os.path.join(backups, STAMP + "-2")
    assert os.path.isdir(os.path.join(backups, STAMP))  # the first backup survives


# --- guards against moving the wrong folder -------------------------------------------

def test_a_foreign_folder_is_never_moved(workspace):
    """An existing non-empty target without extension.json is not an installation."""
    target = os.path.join(workspace, "Documents")
    os.makedirs(target)
    keep = os.path.join(target, "thesis.docx")
    with open(keep, "w", encoding="utf-8") as handle:
        handle.write("not a connector")
    backups = os.path.join(workspace, "backups")
    for dry_run in (True, False):
        with pytest.raises(installer.InstallError) as info:
            installer.install(APP_ROOT, target, backup_root=backups, dry_run=dry_run,
                              now=NOW, stream=io.StringIO())
        assert "not an earlier connector installation" in str(info.value)
    assert os.path.isfile(keep)
    assert not os.path.exists(backups)


def test_an_existing_empty_folder_is_a_valid_target(workspace):
    target = os.path.join(workspace, "empty-target")
    os.makedirs(target)
    plan = installer.install(APP_ROOT, target, backup_root=os.path.join(workspace, "b"),
                             dry_run=True, now=NOW, stream=io.StringIO())
    assert plan["exists"] is True and plan["installed"] is False


@pytest.mark.parametrize("relative", [".", "lib", ".."])
def test_a_target_overlapping_the_source_is_refused(workspace, relative):
    """The source itself, a folder inside it or a folder holding it would be carried away."""
    target = os.path.normpath(os.path.join(APP_ROOT, relative))
    with pytest.raises(installer.InstallError) as info:
        installer.install(APP_ROOT, target, backup_root=os.path.join(workspace, "b"),
                          dry_run=True, now=NOW, stream=io.StringIO())
    assert "overlaps the source folder" in str(info.value)


def test_a_backup_root_inside_the_target_is_refused(workspace):
    target = target_of(workspace)
    previous_installation(target)
    with pytest.raises(installer.InstallError) as info:
        installer.install(APP_ROOT, target, backup_root=os.path.join(target, "backups"),
                          now=NOW, stream=io.StringIO())
    assert "must not lie inside the target" in str(info.value)
    assert os.path.isfile(os.path.join(target, "old.txt"))


# --- refusals -------------------------------------------------------------------------

def test_the_upstream_extension_is_refused(workspace):
    target = target_of(workspace, installer.UPSTREAM_EXTENSION_NAME)
    with pytest.raises(installer.InstallError) as info:
        installer.install(APP_ROOT, target, now=NOW, stream=io.StringIO())
    assert installer.UPSTREAM_EXTENSION_NAME in str(info.value)
    assert not os.path.exists(target)


def test_the_upstream_extension_is_refused_in_a_dry_run_too(workspace):
    target = target_of(workspace, installer.UPSTREAM_EXTENSION_NAME)
    stream = io.StringIO()
    with pytest.raises(installer.InstallError):
        installer.install(APP_ROOT, target, dry_run=True, now=NOW, stream=stream)
    assert stream.getvalue() == ""


def test_a_missing_source_entry_is_reported(workspace):
    source = os.path.join(workspace, "empty")
    os.makedirs(source)
    with pytest.raises(installer.InstallError) as info:
        installer.install(source, target_of(workspace), now=NOW, stream=io.StringIO())
    assert "missing in the source folder" in str(info.value)


# --- paths and the command line ---------------------------------------------------------

def test_default_paths_follow_the_windows_folders(monkeypatch):
    monkeypatch.setenv("APPDATA", "C:\\Users\\x\\AppData\\Roaming")
    monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\x\\AppData\\Local")
    assert installer.default_target() == os.path.join(
        "C:\\Users\\x\\AppData\\Roaming", "pyRevit", "Extensions",
        "dg-revit-connector.extension")
    assert installer.default_backup_root() == os.path.join(
        "C:\\Users\\x\\AppData\\Local", "DG", "revit-connector-backups")


def test_cli_dry_run(workspace, capsys):
    target = target_of(workspace)
    assert installer.main(["--dry-run", "--target", target, "--source", APP_ROOT]) == 0
    output = capsys.readouterr().out
    assert "dry run" in output
    assert target in output
    assert not os.path.exists(target)


def test_cli_refuses_the_upstream_target(workspace, capsys):
    target = target_of(workspace, installer.UPSTREAM_EXTENSION_NAME)
    assert installer.main(["--dry-run", "--target", target, "--source", APP_ROOT]) == 2
    captured = capsys.readouterr()
    assert "refusing" in captured.err.lower()
    assert not os.path.exists(target)
