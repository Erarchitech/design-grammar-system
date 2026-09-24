"""D-12: freeze the five rule-ingest prompt inputs once via an injectable renderer.

1204-07 authors ONLY this freeze script and its fake-renderer unit test. The
frozen rendered prompts themselves land in
fixtures/llm_repeatability/rule_ingest_prompts/ when live plan 1204-09 invokes
this script -- this plan never writes into fixtures/.

The five D-12 rule-ingest inputs are:

1. the height rule from fixtures/golden/fixture.json               (read-only)
2-4. the three rules from test/fixture_rules_v7.txt                (read-only)
5. the single attribute-of source from fixtures/golden/cq3-attribute-of/
   (frozen, read-only)

The real renderer (1204-09) is the repo's n8n "Build LLM Prompt" node logic in
n8n/workflows/rules-to-metagraph.json, a read-only source. It is NOT imported
here: `render_rule_ingest_prompt` delegates to an injected callable, so this
module imports no n8n node and opens no network.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable

# data-service/tests/recognition_eval/freeze_rule_ingest_prompts.py
#   -> parents[0] = recognition_eval, [1] = tests, [2] = data-service,
#      [3] = repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Source of the three-rule fixture, split into one entry per rule below.
_FIXTURE_RULES_V7 = REPO_ROOT / "test" / "fixture_rules_v7.txt"


def _split_fixture_rules_v7(path: Path) -> "list[tuple[str, str]]":
    """Split `fixture_rules_v7.txt` into its three rule texts.

    The D-12 rule-ingest inputs are the three RULES, not the one file, so the
    freeze script must name them separately. The fixture's own header comment
    states its shape: a `#`/`//`-comment banner (dropped entirely -- it is
    file-level documentation, never a rule), followed by exactly one rule
    per non-blank line (the three rules are newline-separated, not
    blank-line-separated, so a blank-line block splitter would wrongly merge
    all three into a single block). Each surviving line is one rule.
    """
    raw = path.read_text(encoding="utf-8")
    rule_lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]

    named: "list[tuple[str, str]]" = []
    for index, rule_text in enumerate(rule_lines):
        slug = re.sub(r"[^0-9a-zA-Z]+", "_", rule_text).strip("_").lower()
        slug = slug[:40] or f"rule_{index + 1}"
        named.append((f"fixture_rules_v7_{index + 1}_{slug}", rule_text))
    return named


def _load_rule_ingest_sources() -> "list[tuple[str, str]]":
    """The five ordered D-12 rule-ingest inputs as (name, rule_text) pairs."""
    sources: "list[tuple[str, str]]" = []

    height_path = REPO_ROOT / "fixtures" / "golden" / "fixture.json"
    sources.append(("height_rule", height_path.read_text(encoding="utf-8")))

    sources.extend(_split_fixture_rules_v7(_FIXTURE_RULES_V7))

    cq3_seed = REPO_ROOT / "fixtures" / "golden" / "cq3-attribute-of" / "seed-cq3.cypher"
    sources.append(("cq3_attribute_of", cq3_seed.read_text(encoding="utf-8")))

    return sources


#: Ordered (name, rule_text). Exactly five entries per D-12.
RULE_INGEST_SOURCES: "list[tuple[str, str]]" = _load_rule_ingest_sources()


def render_rule_ingest_prompt(renderer: Callable[[str], str], rule_text: str) -> str:
    """Delegate rendering to an injectable callable. No default renderer, no
    n8n import, no network -- 1204-09 injects the real "Build LLM Prompt"
    node logic."""
    return renderer(rule_text)


def write_manifest(render_dir: Path, prompts: "dict[str, str]") -> Path:
    """Write `<name>.prompt.txt: <sha256 hex>` lines, sorted by name, to
    `<render_dir>/MANIFEST` and return the manifest path."""
    manifest_path = render_dir / "MANIFEST"
    lines = []
    for name in sorted(prompts):
        digest = hashlib.sha256(prompts[name].encode("utf-8")).hexdigest()
        lines.append(f"{name}.prompt.txt: {digest}")
    manifest_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return manifest_path


def freeze_rule_ingest_prompts(renderer: Callable[[str], str], out_dir: Path) -> "dict[str, str]":
    """Render all five D-12 rule-ingest inputs once, write each prompt to
    `<out_dir>/<name>.prompt.txt`, write the sha256 MANIFEST, and return the
    mapping of name -> rendered prompt.

    Writes only under `out_dir`. Never writes into fixtures/ -- 1204-09 must
    pass fixtures/llm_repeatability/rule_ingest_prompts/ explicitly.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts: "dict[str, str]" = {}
    for name, rule_text in RULE_INGEST_SOURCES:
        prompt = render_rule_ingest_prompt(renderer, rule_text)
        prompts[name] = prompt
        # write_bytes, never write_text: text-mode writes translate "\n" to
        # the platform line separator (CRLF on Windows), so the bytes on
        # disk would silently diverge from the string the manifest hashes.
        (out_dir / f"{name}.prompt.txt").write_bytes(prompt.encode("utf-8"))

    write_manifest(out_dir, prompts)
    return prompts