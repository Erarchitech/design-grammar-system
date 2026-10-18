#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install the DG Revit connector as a pyRevit extension (CPython 3.11+).

Copies the pyRevit half of this folder to
``%APPDATA%\\pyRevit\\Extensions\\dg-revit-connector.extension``:

* ``extension.json``, ``startup.py``, ``dg_transport.py``
* ``dg_revit_mcp/`` (the route modules)
* ``lib/`` (the DG connector library)
* ``DG.tab/`` (the «DG» ribbon panel)
* ``DG_SharedParameters.txt``

``tests/``, ``tools/``, ``main.py`` and every ``__pycache__`` stay behind: the
MCP server is run from the repository path by the MCP client (DeGram's
``DEGRAM_REVIT_MCP_DIR``), only the extension has to live in pyRevit's
extension folder.

An existing installation is first moved to
``%LOCALAPPDATA%\\DG\\revit-connector-backups\\<UTC yyyymmddTHHMMSSZ>``, so a
rollback is one folder move. ``revit-mcp.extension`` (the upstream project) is
never touched or replaced: the script refuses that target name. It also
refuses a target that overlaps the source folder and an existing non-empty
target without ``extension.json`` (see :func:`check_target`).

Usage::

    python install.py                       # install into %APPDATA%
    python install.py --dry-run             # print the plan, write nothing
    python install.py --target D:\\x.extension --backup-root D:\\backups
    python install.py --dry-run --target <temp dir>

Exit codes: 0 success, 2 refused or missing source.
"""

import argparse
import datetime
import os
import shutil
import sys

#: Name of the installed extension folder.
EXTENSION_NAME = "dg-revit-connector.extension"

#: The upstream extension this script refuses to touch.
UPSTREAM_EXTENSION_NAME = "revit-mcp.extension"

#: What the extension needs at runtime, in copy order.
COPY_ENTRIES = (
    "extension.json",
    "startup.py",
    "dg_transport.py",
    "dg_revit_mcp",
    "lib",
    "DG.tab",
    "DG_SharedParameters.txt",
)

#: Copy filters: nothing generated belongs in an installed extension.
SKIP_DIRECTORIES = frozenset(["__pycache__", ".git", ".pytest_cache"])
SKIP_SUFFIXES = (".pyc", ".pyo")

#: Folder of this script: the extension source.
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


class InstallError(Exception):
    """The install cannot proceed (refused target, missing source entry)."""


# --- paths --------------------------------------------------------------------

def default_extensions_dir():
    """``%APPDATA%\\pyRevit\\Extensions`` (the pyRevit extension folder)."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "pyRevit", "Extensions")


def default_target(extensions_dir=None):
    """``<extensions dir>\\dg-revit-connector.extension``."""
    root = extensions_dir or default_extensions_dir()
    return os.path.join(root, EXTENSION_NAME)


def default_backup_root():
    """``%LOCALAPPDATA%\\DG\\revit-connector-backups``."""
    localappdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(localappdata, "DG", "revit-connector-backups")


def utc_stamp(now=None):
    """``yyyymmddTHHMMSSZ`` for a moment (UTC by default)."""
    moment = now
    if moment is None:
        moment = datetime.datetime.now(datetime.timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def is_upstream_target(target):
    """True when ``target`` names the upstream ``revit-mcp.extension``."""
    name = os.path.basename(os.path.normpath(os.path.abspath(target)))
    return name.lower() == UPSTREAM_EXTENSION_NAME.lower()


def _comparable(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _contains(outer, inner):
    """True when ``inner`` is ``outer`` or lies below it."""
    outer, inner = _comparable(outer), _comparable(inner)
    try:
        return os.path.commonpath([outer, inner]) == outer
    except ValueError:  # different drives
        return False


def check_target(source_dir, target, backup_root=None):
    """Refuse a target the installer must never move or overwrite.

    * ``revit-mcp.extension`` (the upstream extension stays untouched);
    * the source folder itself, a folder inside it or a folder holding it (the
      backup move would carry the repository away);
    * an existing file, or an existing non-empty folder without
      ``extension.json`` (not an earlier installation, so not ours to move);
    * a backup root inside the target.
    """
    if is_upstream_target(target):
        raise InstallError(
            "refusing to install into {}: that is the upstream extension, which is "
            "left untouched (use the dg-revit-connector.extension target)".format(
                os.path.abspath(target)))
    if _contains(source_dir, target) or _contains(target, source_dir):
        raise InstallError(
            "refusing to install into {}: it overlaps the source folder {}".format(
                os.path.abspath(target), os.path.abspath(source_dir)))
    if os.path.exists(target):
        if not os.path.isdir(target):
            raise InstallError("the target exists and is not a folder: {}".format(
                os.path.abspath(target)))
        if os.listdir(target) and not os.path.isfile(os.path.join(target, "extension.json")):
            raise InstallError(
                "refusing to move {}: it is not empty and holds no extension.json, so it "
                "is not an earlier connector installation".format(os.path.abspath(target)))
    if backup_root and _contains(target, backup_root):
        raise InstallError("the backup root {} must not lie inside the target".format(
            os.path.abspath(backup_root)))


# --- the copy plan ------------------------------------------------------------

def source_files(source_dir=SOURCE_DIR):
    """``[(relative path, absolute path)]`` of every file to install, sorted."""
    found = []
    for entry in COPY_ENTRIES:
        absolute = os.path.join(source_dir, entry)
        if not os.path.exists(absolute):
            raise InstallError("missing in the source folder: {}".format(entry))
        if os.path.isdir(absolute):
            for directory, subdirectories, names in os.walk(absolute):
                subdirectories[:] = sorted(name for name in subdirectories
                                           if name not in SKIP_DIRECTORIES)
                for name in sorted(names):
                    if name.endswith(SKIP_SUFFIXES):
                        continue
                    path = os.path.join(directory, name)
                    found.append((os.path.relpath(path, source_dir), path))
        else:
            found.append((entry, absolute))
    found.sort()
    return found


def plan(source_dir=SOURCE_DIR, target=None, backup_root=None, now=None):
    """What an install would do -> dict with target, backup path and files."""
    target = os.path.abspath(target or default_target())
    files = source_files(source_dir)
    backup = None
    if os.path.exists(target):
        root = os.path.abspath(backup_root or default_backup_root())
        backup = os.path.join(root, utc_stamp(now))
    return {
        "source": os.path.abspath(source_dir),
        "target": target,
        "backup": backup,
        "files": files,
        "exists": os.path.exists(target),
    }


def _print_plan(install_plan, dry_run, stream):
    lines = []
    lines.append("DG Revit connector install{}".format(" (dry run)" if dry_run else ""))
    lines.append("  source : {}".format(install_plan["source"]))
    lines.append("  target : {}".format(install_plan["target"]))
    if install_plan["backup"]:
        lines.append("  backup : {}  (the existing installation is moved here)".format(
            install_plan["backup"]))
    else:
        lines.append("  backup : none (no existing installation)")
    lines.append("  files  : {}".format(len(install_plan["files"])))
    for relative, _absolute in install_plan["files"]:
        lines.append("    {}".format(relative.replace("\\", "/")))
    stream.write("\n".join(lines) + "\n")


def _unique_directory(path):
    """``path``, or ``path-2``, ``path-3``... when it already exists."""
    candidate = path
    counter = 2
    while os.path.exists(candidate):
        candidate = "{}-{}".format(path, counter)
        counter += 1
    return candidate


def install(source_dir=SOURCE_DIR, target=None, backup_root=None, dry_run=False,
            now=None, stream=None):
    """Copy the extension into place -> the plan dict (with ``installed``)."""
    stream = stream if stream is not None else sys.stdout
    check_target(source_dir, target or default_target(), backup_root or default_backup_root())
    install_plan = plan(source_dir, target, backup_root, now)
    _print_plan(install_plan, dry_run, stream)
    install_plan["installed"] = False
    if dry_run:
        stream.write("dry run: nothing was written\n")
        return install_plan

    backup_path = None
    if install_plan["exists"]:
        if not os.path.isdir(install_plan["target"]):
            raise InstallError("the target exists and is not a folder: {}".format(
                install_plan["target"]))
        backup_path = _unique_directory(install_plan["backup"])
        os.makedirs(backup_path)
        shutil.move(install_plan["target"],
                    os.path.join(backup_path, os.path.basename(install_plan["target"])))
    os.makedirs(install_plan["target"], exist_ok=True)
    copied = 0
    for relative, absolute in install_plan["files"]:
        destination = os.path.join(install_plan["target"], relative)
        parent = os.path.dirname(destination)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(absolute, destination)
        copied += 1
    install_plan["installed"] = True
    install_plan["copied"] = copied
    install_plan["backup_path"] = backup_path
    if backup_path:
        stream.write("moved the previous installation to {}\n".format(backup_path))
    stream.write("copied {} files to {}\n".format(copied, install_plan["target"]))
    stream.write("reload pyRevit (pyRevit tab -> Reload) or restart Revit to load the connector\n")
    return install_plan


# --- command line -------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Install the Design Grammars Revit connector as a pyRevit extension.")
    parser.add_argument("--target", default=None,
                        help="extension folder to install into "
                             "(default: %%APPDATA%%\\pyRevit\\Extensions\\{})".format(
                                 EXTENSION_NAME))
    parser.add_argument("--backup-root", default=None,
                        help="where an existing installation is moved to "
                             "(default: %%LOCALAPPDATA%%\\DG\\revit-connector-backups)")
    parser.add_argument("--source", default=SOURCE_DIR,
                        help="folder holding the extension sources (default: this folder)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and write nothing")
    arguments = parser.parse_args(argv)
    try:
        install(arguments.source, arguments.target, arguments.backup_root,
                dry_run=arguments.dry_run)
    except InstallError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
