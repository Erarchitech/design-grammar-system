"""Tests for canonical_json.py (Phase 1200 Plan 03, ALGN12-01/spec/EVIDENCE-CONTRACT.md section 6)."""
import hashlib
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from canonical_json import CANONICALIZATION_VERSION, canonicalize, hash_canonical, hash_scalar_tuple


def _repo_root() -> Path:
    """Resolve the repo root, tolerating both host layout and /mnt/repo container mount."""
    mnt = Path("/mnt/repo")
    if mnt.exists():
        return mnt
    # data-service/tests/test_canonical_json.py -> data-service -> repo root
    return Path(__file__).resolve().parent.parent.parent


def _load_golden_vectors() -> list[dict]:
    """Load the shared golden vectors, decoding JSON non-integer numbers as
    ``decimal.Decimal`` (``parse_float=Decimal``) rather than native ``float`` --
    ``canonicalize`` requires ``Decimal`` for non-integer numbers (rule 2), so any
    real producer parsing numeric evidence-envelope fields destined for
    canonicalization must load them the same way, never through native float.
    """
    fixture_path = _repo_root() / "fixtures" / "golden" / "canonical-vectors.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f, parse_float=Decimal)
    return data["vectors"]


def test_canonicalization_version_is_1():
    assert CANONICALIZATION_VERSION == 1


def test_scalar_tuple_hash_is_deterministic_and_matches_shipped_dgid_vector():
    digest = hash_scalar_tuple("p1", "frame.gh", "cg:1:proc:11_Proc")
    assert digest[:16] == "BC8E62EE137E2B56"
    # Determinism: recomputing yields the identical digest.
    assert hash_scalar_tuple("p1", "frame.gh", "cg:1:proc:11_Proc") == digest


def test_scalar_tuple_hash_changes_when_any_part_changes():
    base = hash_scalar_tuple("p1", "frame.gh", "cg:1:proc:11_Proc")
    changed = hash_scalar_tuple("p2", "frame.gh", "cg:1:proc:11_Proc")
    assert base != changed


def test_scalar_tuple_hash_rejects_non_string_part():
    with pytest.raises(ValueError):
        hash_scalar_tuple("p1", 42, "cg:1:proc:11_Proc")  # type: ignore[arg-type]


def test_scalar_tuple_hash_rejects_empty_part():
    with pytest.raises(ValueError):
        hash_scalar_tuple("p1", "", "cg:1:proc:11_Proc")
    with pytest.raises(ValueError):
        hash_scalar_tuple("p1", "   ", "cg:1:proc:11_Proc")


def test_canonicalize_sorts_object_keys_by_unicode_code_point():
    assert canonicalize({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonicalize_nfc_normalizes_decomposed_unicode():
    # "e" + combining acute accent (U+0301) -- decomposed NFD form.
    decomposed = "Café"
    result = canonicalize(decomposed)
    assert result == '"Café"'


def test_canonicalize_leaves_non_ascii_unescaped():
    result = canonicalize("Café")
    assert "\\u" not in result
    assert result == '"Café"'


def test_canonicalize_decimal_and_integer_formatting():
    # Decimal renders as a fixed-point string, preserving exactness (no rounding/
    # trailing-zero stripping -- format(Decimal, "f") is exact, never scientific).
    assert canonicalize(Decimal("2.50")) == "2.50"
    assert canonicalize(2) == "2"


def test_canonicalize_rejects_float():
    with pytest.raises(TypeError):
        canonicalize(2.5)


def test_canonicalize_rejects_nan_and_infinity():
    with pytest.raises(ValueError):
        canonicalize(float("nan"))
    with pytest.raises(ValueError):
        canonicalize(float("inf"))


def test_canonicalize_no_insignificant_whitespace():
    result = canonicalize({"a": [1, 2], "b": "x"})
    assert " " not in result
    assert result == '{"a":[1,2],"b":"x"}'


def test_canonicalize_escapes_only_mandatory_characters():
    result = canonicalize('a"b\\c\td')
    assert result == '"a\\"b\\\\c\\td"'


def test_golden_vectors_file_is_non_empty():
    vectors = _load_golden_vectors()
    assert len(vectors) > 0


def test_golden_vectors_scalar_tuple_round_trip():
    vectors = [v for v in _load_golden_vectors() if v["kind"] == "scalarTuple"]
    assert len(vectors) > 0
    for vector in vectors:
        digest = hash_scalar_tuple(*vector["parts"])
        assert digest == vector["sha256Upper"], f"digest mismatch for {vector['description']}"
        assert "|".join(vector["parts"]) == vector["joined"]


def test_golden_vectors_canonical_json_round_trip():
    vectors = [v for v in _load_golden_vectors() if v["kind"] == "canonicalJson"]
    assert len(vectors) > 0
    for vector in vectors:
        canonical = canonicalize(vector["value"])
        assert canonical == vector["canonical"], f"canonical string mismatch for {vector['description']}"
        digest = hash_canonical(vector["value"])
        assert digest == vector["sha256Upper"], f"digest mismatch for {vector['description']}"


def test_canonicalize_preserves_trailing_zero_decimal_scale():
    # CR-01 direct reproduction: a decimal's stored scale (including trailing zeros) is part
    # of its canonical form, exactly mirroring format(Decimal, "f").
    value = {"amount": Decimal("100.00"), "ratio": Decimal("2.50")}
    assert canonicalize(value) == '{"amount":100.00,"ratio":2.50}'


def test_golden_vectors_include_a_trailing_zero_decimal():
    # Guards against silently reopening the CR-01 coverage gap: if the trailing-zero vector is
    # ever removed from canonical-vectors.json, this fails instead of the gap going unnoticed.
    vectors = [v for v in _load_golden_vectors() if v["kind"] == "canonicalJson"]
    trailing_zero_hits = [
        v for v in vectors if re.search(r":-?\d+\.\d*0[,}]", v["canonical"])
    ]
    assert trailing_zero_hits, "no canonicalJson golden vector carries a trailing-zero decimal"


def test_canonicalize_preserves_negative_zero_sign():
    # WR-01 reference behavior: format(Decimal, "f") keeps negative zero's sign. This is the
    # normative side of the parity contract -- the C# leg's WriteNumberDecimal was the one that
    # dropped it (decimal.ToString("F2") renders -0.00m as "0.00"), and was fixed to match this.
    assert canonicalize(Decimal("-0.00")) == "-0.00"
    assert canonicalize(Decimal("-0")) == "-0"
    assert canonicalize({"margin": Decimal("-0.00")}) == '{"margin":-0.00}'
    # Positive zero is unaffected.
    assert canonicalize(Decimal("0.00")) == "0.00"


def test_canonicalize_renders_ordinary_negative_decimal_with_single_sign():
    # IN-01: no pre-1200-09 vector exercised any negative value, so a plain sign regression
    # (or a double-prepended sign on the C# leg) would have gone uncaught on both legs.
    value = {"delta": Decimal("-12.50"), "offset": Decimal("-0.5"), "count": -7}
    canonical = canonicalize(value)
    assert canonical == '{"count":-7,"delta":-12.50,"offset":-0.5}'
    assert "--" not in canonical


def test_golden_vectors_include_negative_zero_and_ordinary_negative():
    # Guards against silently reopening the WR-01/IN-01 coverage gap: if either vector is removed
    # from canonical-vectors.json, this fails instead of the gap going unnoticed.
    vectors = [v for v in _load_golden_vectors() if v["kind"] == "canonicalJson"]
    negative_zero_hits = [v for v in vectors if re.search(r":-0(\.0+)?[,}]", v["canonical"])]
    ordinary_negative_hits = [
        v for v in vectors if re.search(r":-(?!0(\.0+)?[,}])\d", v["canonical"])
    ]
    assert negative_zero_hits, "no canonicalJson golden vector carries a negative-zero decimal"
    assert ordinary_negative_hits, "no canonicalJson golden vector carries an ordinary negative value"


def test_golden_vector_negative_digests_are_independently_reproducible():
    # Recompute each negative-carrying vector's digest from the canonical string rather than
    # trusting the recorded literal -- the same double-check the fixture's own _comment requires.
    vectors = [
        v
        for v in _load_golden_vectors()
        if v["kind"] == "canonicalJson" and re.search(r":-\d", v["canonical"])
    ]
    assert len(vectors) >= 2, "expected at least the WR-01 and IN-01 negative vectors"
    for vector in vectors:
        canonical = canonicalize(vector["value"])
        assert canonical == vector["canonical"], f"canonical mismatch for {vector['description']}"
        recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
        assert recomputed == vector["sha256Upper"], f"digest mismatch for {vector['description']}"
        assert hash_canonical(vector["value"]) == recomputed


def test_serializer_does_not_delegate_to_json_dumps():
    """The serializer is explicit, not delegated -- grep-verifiable acceptance criterion."""
    module_path = Path(__file__).resolve().parent.parent / "canonical_json.py"
    source = module_path.read_text(encoding="utf-8")
    assert "json.dumps" not in source
