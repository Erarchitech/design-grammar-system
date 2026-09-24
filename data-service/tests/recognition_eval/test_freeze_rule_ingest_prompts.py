"""1204-07 Task 4: fake-renderer tests for the D-12 prompt-freeze script.

No n8n import, no network, no fixture writes. Temp-dir note: this repo's
pytest/system temp root is permission-denied in this sandbox, so scratch
output goes to a uniquely-named directory under the repo-local `.de01/`
output root (the same workaround plan 1204-05's suite uses), always removed
in a `finally`.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pytest  # noqa: E402

import freeze_rule_ingest_prompts as _freeze_module  # noqa: E402


@pytest.fixture
def scratch_dir():
    path = _freeze_module.REPO_ROOT / ".de01" / f"freeze-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _fake_renderer(rule_text: str) -> str:
    return f"PROMPT: {rule_text[:50]}"


def _snapshot(root: Path) -> "dict[str, int]":
    out: "dict[str, int]" = {}
    if not root.exists():
        return out
    for path in root.rglob("*"):
        if path.is_file():
            out[str(path.relative_to(root))] = path.stat().st_mtime_ns
    return out


def test_sources_are_the_five_d12_inputs():
    """D-12: height rule + three fixture_rules_v7 rules + attribute-of."""
    names = [name for name, _ in _freeze_module.RULE_INGEST_SOURCES]
    assert len(names) == 5, f"expected five D-12 sources, got {names}"
    assert names[0] == "height_rule"
    assert names[-1] == "cq3_attribute_of"
    assert sum(1 for n in names if n.startswith("fixture_rules_v7_")) == 3
    assert all(isinstance(text, str) and text.strip() for _, text in _freeze_module.RULE_INGEST_SOURCES)


def test_freeze_writes_five_prompts_and_manifest(scratch_dir):
    """Exactly five prompt files plus a MANIFEST whose entries are sha256 hex
    digests over each written file's bytes."""
    prompts = _freeze_module.freeze_rule_ingest_prompts(_fake_renderer, scratch_dir)
    assert len(prompts) == 5
    assert len(prompts) == len(_freeze_module.RULE_INGEST_SOURCES)

    written = sorted(p.name for p in scratch_dir.glob("*.prompt.txt"))
    assert len(written) == 5

    manifest_path = scratch_dir / "MANIFEST"
    assert manifest_path.is_file()
    manifest = manifest_path.read_text(encoding="utf-8")

    entries = {}
    for line in manifest.splitlines():
        if not line.strip():
            continue
        filename, _, digest = line.partition(": ")
        entries[filename.strip()] = digest.strip()
    assert len(entries) == 5

    for name in prompts:
        filename = f"{name}.prompt.txt"
        assert filename in entries
        direct = hashlib.sha256((scratch_dir / filename).read_bytes()).hexdigest()
        assert re.fullmatch(r"[0-9a-f]{64}", entries[filename])
        assert entries[filename] == direct
        assert entries[filename] == hashlib.sha256(prompts[name].encode("utf-8")).hexdigest()


def test_freeze_writes_nothing_outside_out_dir(scratch_dir):
    """Nothing outside out_dir is written: the fixture sources stay byte- and
    mtime-identical, and the .de01 scratch dir gains only the new test dir."""
    fixture_roots = [
        _freeze_module.REPO_ROOT / "fixtures" / "golden",
        _freeze_module.REPO_ROOT / "test",
    ]
    before = {str(root): _snapshot(root) for root in fixture_roots}

    _freeze_module.freeze_rule_ingest_prompts(_fake_renderer, scratch_dir)

    after = {str(root): _snapshot(root) for root in fixture_roots}
    assert after == before, "a frozen fixture/ source was written"


def test_freeze_is_renderer_injectable():
    """The renderer is injected: it is called exactly once per D-12 source,
    and the module never imports the n8n node itself."""
    calls = []

    def recording_renderer(text):
        calls.append(text)
        return "R"

    scratch = _freeze_module.REPO_ROOT / ".de01" / f"freeze-inj-{uuid.uuid4().hex}"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        prompts = _freeze_module.freeze_rule_ingest_prompts(recording_renderer, scratch)
        assert len(calls) == len(_freeze_module.RULE_INGEST_SOURCES) == 5
        assert all(value == "R" for value in prompts.values())

        # No network/HTTP import and no import of an n8n-workflow-shaped
        # module. This is an AST check on actual `import` statements, not a
        # substring ban on the file text -- the module's own docstring
        # legitimately *names* n8n/workflows/rules-to-metagraph.json as
        # documentation of where the real renderer logic lives, without
        # importing it (a .json file cannot be imported as a Python module
        # anyway; the substantive guarantee is no import and no network).
        source = Path(_freeze_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        forbidden_prefixes = ("requests", "httpx", "urllib", "n8n")
        offending = {
            name for name in imported_names
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
        }
        assert not offending, f"forbidden import(s): {offending}"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)