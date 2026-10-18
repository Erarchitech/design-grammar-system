from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
SPEC_PATH = REPO_ROOT / "spec" / "REPRODUCIBILITY.md"
START_MARKER = "<!-- reproducibility:llm-call-sites:start -->"
END_MARKER = "<!-- reproducibility:llm-call-sites:end -->"
# A call site is a ``.generate`` call or, since Phase 1301-08, a ``.stream_chat``
# call on an adapter-named receiver (the streaming DeGram relay).
GENERATIVE_ATTRS = ("generate", "stream_chat")


def load_fenced_call_sites() -> dict[str, str]:
    text = SPEC_PATH.read_text(encoding="utf-8")
    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    body = text[start + len(START_MARKER):end]
    result = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        file_part, _, rest = line.rpartition("|")
        # rest is "function|scope_class"; but we split on LAST "|" for scope_class,
        # so re-split file_part on first remaining "|" for function.
        # Simpler: split on "|" fully (exactly 3 parts expected).
        parts = line.split("|")
        if len(parts) != 3:
            continue
        file_name, function_name, scope_class = parts
        result[f"{file_name}|{function_name}"] = scope_class
    return result


class _EnclosingFunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.call_sites: set[str] = set()
        self._stack: list[str] = []

    def visit_FunctionDef(self, node):
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in GENERATIVE_ATTRS
            and isinstance(func.value, ast.Name)
            and "adapter" in func.value.id
        ):
            if self._stack:
                self.call_sites.add(self._stack[-1])
        self.generic_visit(node)


def scan_call_sites() -> set[str]:
    found: set[str] = set()
    for py_file in sorted(DATA_SERVICE_DIR.glob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        visitor = _EnclosingFunctionVisitor()
        visitor.visit(tree)
        for func_name in visitor.call_sites:
            found.add(f"{py_file.name}|{func_name}")
    return found


def report_mismatch(documented: set[str], scanned: set[str]) -> tuple[set[str], set[str]]:
    return (documented - scanned, scanned - documented)


class TestReproducibilityScopeDrift:
    def test_call_sites_match_in_both_directions(self):
        documented = set(load_fenced_call_sites())
        scanned = scan_call_sites()
        documented_only, code_only = report_mismatch(documented, scanned)
        assert documented_only == set(), f"documented but not in code: {documented_only}"
        assert code_only == set(), f"in code but not documented: {code_only}"

    def test_scope_class_vocabulary_is_restricted(self):
        allowed = {"measured", "model-dependent-unmeasured"}
        for key, scope_class in load_fenced_call_sites().items():
            assert scope_class in allowed, f"{key} has disallowed scope-class {scope_class!r}"
            assert scope_class != "deterministic-measured"

    def test_checker_reports_induced_extra_entry(self):
        documented = set(load_fenced_call_sites()) | {"app.py|fake_function"}
        scanned = scan_call_sites()
        documented_only, code_only = report_mismatch(documented, scanned)
        assert "app.py|fake_function" in documented_only

    def test_checker_reports_induced_missing_entry(self):
        documented = set(load_fenced_call_sites())
        scanned = scan_call_sites() - {"cg_recognition.py|recognize_structure"}
        documented_only, code_only = report_mismatch(documented, scanned)
        assert "cg_recognition.py|recognize_structure" in documented_only


class TestStreamingRelayCallSite:
    """Phase 1301-08: the scan rule also matches ``stream_chat`` on an
    adapter-named receiver, so the DeGram relay (a live LLM call site) is
    governed by this contract like the ``generate`` call sites."""

    RELAY_KEY = "degram_relay.py|relay_chat_completions"

    def test_scan_finds_the_relay_call_site(self):
        assert self.RELAY_KEY in scan_call_sites()

    def test_spec_block_lists_the_relay_with_a_live_generation_scope_class(self):
        documented = load_fenced_call_sites()
        assert documented[self.RELAY_KEY] == documented["app.py|llm_generate"]
        assert documented[self.RELAY_KEY] == "model-dependent-unmeasured"

    def test_scan_rule_matches_stream_chat_on_adapter_named_receivers_only(self):
        source = (
            "async def hit(adapter):\n"
            "    adapter.stream_chat([])\n"
            "async def other(client):\n"
            "    client.stream_chat([])\n"
            "def define():\n"
            "    def stream_chat(): pass\n"
        )
        visitor = _EnclosingFunctionVisitor()
        visitor.visit(ast.parse(source))
        assert visitor.call_sites == {"hit"}

    def test_spec_prose_states_the_stream_chat_rule_and_the_row_count(self):
        text = SPEC_PATH.read_text(encoding="utf-8")
        assert "`stream_chat`" in text
        assert "exactly nine lines" in text
        assert len(load_fenced_call_sites()) == 9
