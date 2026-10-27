#!/usr/bin/env python3
"""Stage the DG connector payloads a DeGram build bundles (quick 261027-sgc).

DeGram's Connectors tab installs two add-ins from its own bundle:

* ``resources/dg-grasshopper`` <- the DG Grasshopper plugin, the ``net48`` Release build of
  ``DG/src/DG.Grasshopper`` (Rhino 8 and Rhino.Inside.Revit 2024 both load it);
* ``resources/revit-mcp``      <- ``apps/dg-revit-connector`` (pyRevit extension + MCP server).

This script builds the plugin at the current framework commit and copies both payloads into one output
folder with ``connector-manifest.json`` (framework commit, dirty flag, SHA-256 of every file), so every
DeGram build carries a recorded, current pair instead of whatever an earlier copy left behind (see
DG_OBSIDIAN/knowledge/debugging/DeGram installers bundled a stale revit-mcp copy from the build folder.md).

Usage::

    python tools/degram/stage_connector_payloads.py --out D:\\dgb\\connector-payloads\\<commit>
    python tools/degram/stage_connector_payloads.py --out <dir> --no-build   # reuse the existing Release build

Then point the DeGram build at the staged folders (``D:\\dgb\\run-build.sh``)::

    export DEGRAM_DG_GRASSHOPPER_SOURCE='<out>\\dg-grasshopper'
    export DEGRAM_REVIT_MCP_SOURCE='<out>\\dg-revit-connector'

Exit codes: 0 staged, 2 refused (non-empty output, failed build, missing DG.gha or connector source).
"""

import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRASSHOPPER_PROJECT = Path("DG/src/DG.Grasshopper/DG.Grasshopper.csproj")
GRASSHOPPER_OUTPUT = Path("DG/src/DG.Grasshopper/bin/Release/net48")
REVIT_CONNECTOR = Path("apps/dg-revit-connector")

#: Only the plugin assemblies; symbols and build metadata stay behind (the bundle filter is `*.gha`, `*.dll`).
GRASSHOPPER_SUFFIXES = (".gha", ".dll")
#: Never part of the Revit payload (the same exclusions as the electron-builder filter).
REVIT_SKIP_DIRECTORIES = frozenset(["tests", ".git", ".github", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache"])
REVIT_SKIP_SUFFIXES = (".pyc", ".pyo")


class StageError(Exception):
    """The payloads cannot be staged."""


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def build_grasshopper(root, dotnet="dotnet", run=subprocess.run):
    """``dotnet build`` of the plugin, net48 Release; raises when it fails."""
    command = [dotnet, "build", str(root / GRASSHOPPER_PROJECT), "-c", "Release", "-f", "net48", "-nologo"]
    result = run(command, cwd=str(root), check=False)
    if result.returncode != 0:
        raise StageError("the DG Grasshopper build failed (exit {})".format(result.returncode))


def grasshopper_files(source):
    """``[(relative, path)]`` of the plugin payload; raises without ``DG.gha``."""
    if not (source / "DG.gha").is_file():
        raise StageError(
            "no DG.gha in {}: build DG with Rhino 8 installed (the GRASSHOPPER_SDK build), "
            "or run without --no-build".format(source))
    return sorted((p.name, p) for p in source.iterdir() if p.is_file() and p.suffix.lower() in GRASSHOPPER_SUFFIXES)


def revit_files(source):
    """``[(relative, path)]`` of the Revit connector payload; raises when the connector is incomplete."""
    for required in ("extension.json", "startup.py", "main.py", "DG.tab", "dg_revit_mcp"):
        if not (source / required).exists():
            raise StageError("the Revit connector at {} has no {}".format(source, required))
    found = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in REVIT_SKIP_DIRECTORIES for part in relative.parts):
            continue
        if path.is_file() and not path.name.endswith(REVIT_SKIP_SUFFIXES):
            found.append((relative.as_posix(), path))
    return found


def copy_files(files, target):
    manifest = {}
    for relative, path in files:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        manifest[relative] = sha256(destination)
    return manifest


def stage(root, out, build=True, dotnet="dotnet", run=subprocess.run, now=None):
    """Build (optionally) and stage both payloads into ``out``; returns the manifest dict."""
    root, out = Path(root), Path(out)
    if out.exists() and any(out.iterdir()):
        raise StageError("the output folder is not empty: {}".format(out))
    if build:
        build_grasshopper(root, dotnet, run)
    grasshopper = grasshopper_files(root / GRASSHOPPER_OUTPUT)
    revit = revit_files(root / REVIT_CONNECTOR)

    out.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.datetime.now(datetime.timezone.utc)
    manifest = {
        "frameworkCommit": git(root, "rev-parse", "HEAD") or None,
        # Uncommitted plugin (DG/src) or connector sources make the commit an incomplete record of what was staged.
        # Build output under bin/ and obj/ is tracked in places; it never makes the sources dirty.
        "dirty": bool(git(root, "status", "--porcelain", "--", "DG/src", REVIT_CONNECTOR.as_posix(),
                          ":(exclude,glob)DG/src/**/bin/**", ":(exclude,glob)DG/src/**/obj/**")),
        "stagedAt": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built": bool(build),
        "grasshopper": {"source": GRASSHOPPER_OUTPUT.as_posix(), "files": copy_files(grasshopper, out / "dg-grasshopper")},
        "revit": {"source": REVIT_CONNECTOR.as_posix(), "files": copy_files(revit, out / "dg-revit-connector")},
    }
    (out / "connector-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage the DG connector payloads for a DeGram build.")
    parser.add_argument("--out", required=True, help="an empty output folder")
    parser.add_argument("--no-build", action="store_true", help="reuse the existing net48 Release build")
    parser.add_argument("--dotnet", default="dotnet", help="the dotnet executable")
    arguments = parser.parse_args(argv)
    try:
        manifest = stage(ROOT, arguments.out, build=not arguments.no_build, dotnet=arguments.dotnet)
    except StageError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    out = Path(arguments.out).resolve()
    print("staged framework commit {}{}".format(manifest["frameworkCommit"], " (dirty)" if manifest["dirty"] else ""))
    print("  dg-grasshopper     : {} files".format(len(manifest["grasshopper"]["files"])))
    print("  dg-revit-connector : {} files".format(len(manifest["revit"]["files"])))
    print("add to the DeGram build driver:")
    print("  export DEGRAM_DG_GRASSHOPPER_SOURCE='{}'".format(out / "dg-grasshopper"))
    print("  export DEGRAM_REVIT_MCP_SOURCE='{}'".format(out / "dg-revit-connector"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
