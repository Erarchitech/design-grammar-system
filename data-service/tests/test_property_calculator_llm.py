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


# --- Phase 1303-16: integrity of stored code, rename-aware validation, prompt and log line -----------------------

import hashlib  # noqa: E402
import importlib  # noqa: E402
import logging  # noqa: E402

# sha256 and length of build_prompt({'label': 'hasHeightMm', 'iri': 'dg:hasHeightMm'},
# [{'ruleId': 'R1', 'text': 't', 'swrl': 's'}], 'Beam') taken BEFORE 1303-16 changed build_prompt; re-pinned by
# 1303-24 (D-66), which added two sentences to CONTEXT_API (return None for "nothing found", counts return 0) and
# changed nothing else (was length 1419, sha256 0c22e77a...).
PROMPT_BEFORE_SHA256 = "61afb4e26eefbc91e6d0feec5ccf563088bd19ae8c09f06e88cc6b51cf72762e"
PROMPT_BEFORE_LENGTH = 1746
# (1303-24, second re-pin after two live generations answered with `from ... import`: one more CONTEXT_API line;
# the first 1303-24 pin was length 1627, sha256 6dad6ef0...)

GEN_LOGGER = "dg.property_calculator_generation"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_rename_validate_function_accepts_the_stored_content_derived_name():
    name, source = pcl.finalize(GOOD)
    assert pcl.validate_function(source, name=name) == source
    with pytest.raises(pcl.GeneratedCalculatorError) as err:
        pcl.validate_function(source)  # default name stays calc_gen
    assert "calc_gen" in str(err.value)
    with pytest.raises(pcl.GeneratedCalculatorError) as err:
        pcl.validate_function(GOOD, name=name)
    assert name in str(err.value)  # the error text names the expected name


def test_integrity_finalize_output_verifies():
    name, source = pcl.finalize(GOOD)
    assert pcl.verify_stored_source(source, name, _sha(source)) is None


def test_integrity_changed_byte_wrong_hash_and_wrong_name_are_reported():
    name, source = pcl.finalize(GOOD)
    tampered = source.replace("StructuralFraming", "StructuralFramingX")
    assert "sha256" in pcl.verify_stored_source(tampered, name, _sha(source))
    assert "sha256" in pcl.verify_stored_source(source, name, "0" * 64)
    assert pcl.verify_stored_source(source, "calc_gen", _sha(source))  # not calc_gen_<10 hex>
    assert pcl.verify_stored_source(source, "calc_gen_XYZ", _sha(source))
    assert pcl.verify_stored_source(None, name, _sha(source))
    assert pcl.verify_stored_source(source, name, None)


def test_integrity_name_that_does_not_match_the_source_digest_is_reported():
    name, source = pcl.finalize(GOOD)
    forged = source.replace(name, "calc_gen_0000000000")
    assert name != "calc_gen_0000000000"
    reason = pcl.verify_stored_source(forged, "calc_gen_0000000000", _sha(forged))
    assert reason and "digest" in reason


def test_integrity_source_that_is_not_a_fixed_point_is_reported():
    source = "def calc_gen_abcdef0123(ctx, box, params):\n    return  1\n"
    reason = pcl.verify_stored_source(source, "calc_gen_abcdef0123", _sha(source))
    assert reason and "normalized" in reason


def test_integrity_forbidden_construct_is_reported():
    source = "def calc_gen_abcdef0123(ctx, box, params):\n    box.Delete()\n    return 0\n"
    reason = pcl.verify_stored_source(source, "calc_gen_abcdef0123", _sha(source))
    assert reason and "Delete" in reason


def test_prompt_without_rejected_reason_is_unchanged_and_with_it_names_the_reason():
    data_property = {"label": "hasHeightMm", "iri": "dg:hasHeightMm"}
    rules = [{"ruleId": "R1", "text": "t", "swrl": "s"}]
    plain = pcl.build_prompt(data_property, rules, "Beam")
    assert len(plain) == PROMPT_BEFORE_LENGTH and _sha(plain) == PROMPT_BEFORE_SHA256
    assert pcl.build_prompt({**data_property, "rejectedReason": ""}, rules, "Beam") == plain

    with_reason = pcl.build_prompt({**data_property, "rejectedReason": "counts only the nearest wall"}, rules, "Beam")
    assert with_reason.startswith(plain)
    assert "counts only the nearest wall" in with_reason and "different calculator" in with_reason


def _generation_records(caplog):
    return [r for r in caplog.records if r.name == GEN_LOGGER]


def test_generation_logs_one_line_per_call_without_prompt_or_source(caplog):
    answer = '{"function": "def calc_gen(ctx, box, params):\n    return 1.0\n", "unit": "mm"}'
    with caplog.at_level(logging.INFO, logger=GEN_LOGGER):
        for _ in range(2):
            pcl.generate_calculator({"label": "x", "iri": "dg:hasHeightMm"}, [{"ruleId": "R1", "text": "SECRETRULE"}],
                                    "Beam", complete=lambda p, s: (answer, "fake", "m"))
        pcl.generate_calculator({"label": "x", "iri": "dg:hasHeightMm"}, [], "Beam",
                                complete=lambda p, s: (_ for _ in ()).throw(RuntimeError("down")))
    records = _generation_records(caplog)
    assert len(records) == 3  # one per call, also for a provider error
    for record in records:
        message = record.getMessage()
        assert message == "property calculator LLM generation requested: dg:hasHeightMm"
        assert "SECRETRULE" not in message and "calc_gen" not in message and "return 1.0" not in message
        assert record.levelno == logging.INFO


def test_generation_logger_has_exactly_one_own_stderr_handler_even_after_reload():
    importlib.reload(pcl)
    importlib.reload(pcl)
    logger = logging.getLogger(GEN_LOGGER)
    own = [h for h in logger.handlers if getattr(h, "_dg_generation", False)]
    assert len(own) == 1 and isinstance(own[0], logging.StreamHandler)  # stderr stream as captured at import
    assert logger.level == logging.INFO


# ---------------------------------------------------------------------------------------------------------------
# Phase 1303-22 (D-62): the generation prompt names the participants of the rules
# ---------------------------------------------------------------------------------------------------------------

PARTICIPANTS = [
    {"label": "Slab", "relation": "hostedBy", "relatedTo": "Opening", "revitCategories": ["OST_Floors"]},
    {"label": "Column", "relation": "projectsOnto", "relatedTo": "Slab",
     "revitCategories": ["OST_Columns", "OST_StructuralColumns"]},
]


def test_prompt_without_participants_stays_byte_identical_to_the_1303_16_pin():
    data_property = {"label": "hasHeightMm", "iri": "dg:hasHeightMm"}
    rules = [{"ruleId": "R1", "text": "t", "swrl": "s"}]
    for participants in (None, []):
        plain = pcl.build_prompt(data_property, rules, "Beam", participants)
        assert len(plain) == PROMPT_BEFORE_LENGTH and _sha(plain) == PROMPT_BEFORE_SHA256
    assert "Participants" not in pcl.build_prompt(data_property, rules, "Beam")


def test_prompt_with_participants_adds_one_block_and_leaves_the_context_api_alone():
    data_property = {"label": "hasMinProjectionClearanceMm", "iri": "dg:hasMinProjectionClearanceMm"}
    rules = [{"ruleId": "R1", "text": "t", "swrl": "s"}]
    plain = pcl.build_prompt(data_property, rules, "Opening")
    prompt = pcl.build_prompt(data_property, rules, "Opening", PARTICIPANTS)
    block = ("Participants:\n"
             "- Slab: hostedBy Opening; Revit categories: OST_Floors\n"
             "- Column: projectsOnto Slab; Revit categories: OST_Columns, OST_StructuralColumns")
    assert block in prompt and pcl.CONTEXT_API in prompt
    assert prompt.index("Rules that test it:") < prompt.index("Participants:") < prompt.index(pcl.CONTEXT_API)
    assert prompt.replace(block + "\n\n", "") == plain


def test_a_participant_without_a_relation_or_categories_is_still_named():
    block = pcl.participants_block([{"label": "Wall", "relation": None, "relatedTo": None, "revitCategories": []}])
    assert block == "Participants:\n- Wall: Revit categories: none known"


def test_participants_come_from_the_request_and_the_rejection_reason_still_follows_them():
    seen = []
    answer = '{"function": "def calc_gen(ctx, box, params):\n    return 1.0\n", "unit": "mm"}'

    def complete(prompt, system):
        seen.append(prompt)
        return answer, "fake", "m"

    base = {"label": "x", "iri": "dg:hasX", "participants": PARTICIPANTS, "rejectedReason": "wrong slab"}
    pcl.generate_calculator(base, [{"ruleId": "R1"}], "Opening", complete=complete)
    pcl.generate_calculator({"label": "x", "iri": "dg:hasX"}, [{"ruleId": "R1"}], "Opening", complete=complete)
    assert "Participants:\n- Slab: hostedBy Opening" in seen[0]
    assert seen[0].index("Participants:") < seen[0].index("wrong slab")
    assert "Participants" not in seen[1]


# --- Phase 1303-24 (D-66): "nothing found" is no data, never 0 --------------------------------------------------

NOT_FOUND_ZERO = (
    "def calc_gen(ctx, box, params):\n"
    "    min_clear = None\n"
    "    for e in ctx.intersecting(box, ['OST_Walls']):\n"
    "        min_clear = 1.0\n"
    "    if min_clear is None:\n"
    "        return {zero}\n"
    "    return min_clear\n"
)


@pytest.mark.parametrize("zero", ["0.0", "0", "-0.0"])
def test_a_zero_returned_from_the_nothing_found_branch_is_refused(zero):
    with pytest.raises(pcl.GeneratedCalculatorError) as err:
        pcl.validate_function(NOT_FOUND_ZERO.format(zero=zero))
    assert "return None" in str(err.value)


def test_a_zero_in_a_nested_statement_of_the_nothing_found_branch_is_refused():
    source = (
        "def calc_gen(ctx, box, params):\n"
        "    best = None\n"
        "    if best is None:\n"
        "        if params:\n"
        "            return 1.0\n"
        "        for e in ctx.intersecting(box, ['OST_Walls']):\n"
        "            return 0.0\n"
        "    return best\n"
    )
    with pytest.raises(pcl.GeneratedCalculatorError):
        pcl.validate_function(source)


def test_none_for_nothing_found_is_accepted():
    name, source = pcl.finalize(NOT_FOUND_ZERO.format(zero="None"))
    assert "return None" in source and pcl.verify_stored_source(source, name, hashlib.sha256(source.encode()).hexdigest()) is None


def test_counts_may_return_zero_when_nothing_is_found():
    count = (
        "def calc_gen(ctx, box, params):\n"
        "    hits = ctx.intersecting(box, ['OST_StructuralFraming'])\n"
        "    if not hits:\n"
        "        return 0\n"
        "    if len(hits) == 0:\n"
        "        return 0\n"
        "    return len(hits)\n"
    )
    other = (
        "def calc_gen(ctx, box, params):\n"
        "    x = ctx.wall_frame(box)\n"
        "    if x is not None:\n"
        "        return 0.0\n"
        "    return None\n"
    )
    assert pcl.validate_function(count) and pcl.validate_function(other)


def test_a_stored_source_with_the_zero_fallback_fails_verification_with_a_reason():
    # the source the 2026-10-25 live run stored: valid before D-66, so it is rebuilt the way finalize used to
    old = NOT_FOUND_ZERO.format(zero="0.0")
    import ast
    function = "calc_gen_" + hashlib.sha256(ast.unparse(ast.parse(old).body[0]).strip().replace(
        "def calc_gen(", "def calc_gen(").encode()).hexdigest()[:10]
    stored = ast.unparse(ast.parse(old).body[0]).replace("def calc_gen(", f"def {function}(", 1) + "\n"
    problem = pcl.verify_stored_source(stored, function, hashlib.sha256(stored.encode()).hexdigest())
    assert problem and "source fails the contract" in problem and "return None" in problem


def test_the_contract_text_tells_the_model_to_return_none_for_nothing_found():
    assert "return None" in pcl.SYSTEM + pcl.CONTEXT_API
    assert "never return 0" in pcl.CONTEXT_API.lower() or "never 0" in pcl.CONTEXT_API.lower()
    assert "count" in pcl.CONTEXT_API.lower()


def test_the_contract_text_forbids_imports_and_names_what_is_already_available():
    # live 2026-10-25: two generations in a row answered with `from ... import`, which validate_function refuses
    text = pcl.CONTEXT_API.lower()
    assert "no import" in text and "already available" in text
    assert "math" in pcl.CONTEXT_API and "DB" in pcl.CONTEXT_API
