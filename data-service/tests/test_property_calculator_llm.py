"""Contract checks for LLM-generated property calculators (Phase 1303-15)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import property_calculator_llm as pcl  # noqa: E402

GOOD = (
    "def calc_gen(ctx, box, params):\n"
    "    return len(ctx.intersecting(box, ['OST_StructuralFraming']))\n"
)


def test_good_function_is_accepted_and_named_by_content():
    name, source = pcl.finalize(GOOD)
    assert name.startswith("calc_gen_") and source.startswith(f"def {name}(ctx, box, params):")
    assert pcl.finalize(GOOD) == (name, source)


@pytest.mark.parametrize("source, reason", [
    ("import os\ndef calc_gen(ctx, box, params):\n    return 0\n", "exactly one function"),
    ("def calc_gen(ctx, box, params):\n    import os\n    return 0\n", "Import"),
    ("def calc_gen(ctx, box, params):\n    box.Delete()\n    return 0\n", "Delete"),
    ("def calc_gen(ctx, box, params):\n    t = DB.Transaction(ctx.doc, 'x')\n    return 0\n", "Transaction"),
    ("def calc_gen(ctx, box, params):\n    return box.__class__\n", "__class__"),
    ("def calc_gen(ctx, box, params):\n    return eval('1')\n", "eval"),
    ("def calc_gen(ctx, box, params):\n    open('x')\n    return 0\n", "open"),
    ("def calc_gen(ctx, box, params):\n    p = box.LookupParameter('x')\n    p.Set(1)\n    return 0\n", "Set"),
    ("def calc_gen(ctx, box):\n    return 0\n", "exactly (ctx, box, params)"),
    ("def calc_gen(ctx, box, params):\n    with ctx.doc as d:\n        return 0\n", "With"),
])
def test_forbidden_constructs_are_rejected(source, reason):
    with pytest.raises(pcl.GeneratedCalculatorError) as err:
        pcl.validate_function(source)
    assert reason in str(err.value)


def test_generate_calculator_parses_json_answer_and_validates():
    def complete(prompt, system):
        assert "hasOpeningHeightMm" in prompt and "calc_gen" in system
        return ('```json\n{"function": "def calc_gen(ctx, box, params):\\n    return 1.0\\n", "unit": "mm"}\n```',
                "fake", "m1")

    out = pcl.generate_calculator({"label": "hasOpeningHeightMm", "iri": "dg:hasOpeningHeightMm"},
                                  [{"ruleId": "R1", "text": "t", "swrl": "s"}], "OpeningBox", complete=complete)
    assert out["status"] == "ok" and out["unit"] == "mm" and out["function"].startswith("calc_gen_")


def test_generate_calculator_rejects_unsafe_answer_and_survives_provider_errors():
    bad = pcl.generate_calculator({"label": "x"}, [], "Box", complete=lambda p, s: (
        '{"function": "def calc_gen(ctx, box, params):\\n    box.Delete()\\n    return 0\\n"}', "fake", "m"))
    assert bad["status"] == "invalid" and "Delete" in bad["error"]

    def boom(prompt, system):
        raise RuntimeError("provider down")

    assert pcl.generate_calculator({"label": "x"}, [], "Box", complete=boom)["status"] == "unavailable"
