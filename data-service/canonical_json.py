"""Canonical-JSON serialization and hashing helpers (spec/EVIDENCE-CONTRACT.md section 6).

Cross-language parity contract
-------------------------------
This module is byte-identical in behavior to ``DG.Core.Contracts.CanonicalJsonWriter``
(the C# mirror implemented in plan 1200-04). Any change to the normalization rules
implemented here breaks cross-platform evidence-hash parity between Python
(data-service, dg-reasoner) and C# (DG.Core). The shared golden vectors in
``fixtures/golden/canonical-vectors.json`` are what guard this parity -- every vector
in that file must reproduce byte-exactly (the canonical string itself) and
digest-exactly (its SHA-256 uppercase hex) from both language implementations.

Two hashing conventions
------------------------
1. **Scalar-tuple hashing** (``hash_scalar_tuple``) -- for a fixed, ordered list of
   scalar strings (e.g. minting a ``dgId``). This is the shipped precedent already in
   production: ``data-service/dg_identity.py``'s ``compute_dg_id`` and
   ``DG.Core.Models.Identity.DgIdMintingService.Mint`` pipe-join their parts, SHA-256
   the UTF-8 bytes, and render the digest as uppercase hex. No canonical-JSON step is
   needed for this class of hash -- the ordered pipe-join already is the canonical
   form.
2. **Nested-payload canonicalization** (``canonicalize`` / ``hash_canonical``) -- for a
   hash input that is a nested JSON payload (arrays, objects), implementing the six
   normalization rules from spec/EVIDENCE-CONTRACT.md section 6: key ordering, number
   formatting, whitespace, Unicode NFC form, escaping, and the NaN/Infinity
   prohibition. Hand-rolled by explicit recursive walk rather than delegated to the
   standard library's generic serializer, per RESEARCH.md's finding that no verified
   jointly-tested cross-language canonical-JSON package pair exists -- the escaping
   and number rules must stay under this module's control so they are exactly
   mirror-able in C#.

Changing any of the six canonicalization rules requires bumping
``CANONICALIZATION_VERSION``, because a recorded hash in already-committed evidence
becomes meaningless if the rules that produced it change silently underneath it.
"""

from __future__ import annotations

import hashlib
import math
import unicodedata
from decimal import Decimal
from typing import Any

CANONICALIZATION_VERSION = 1

# JSON-mandated escape characters (rule 5): quote, backslash, and control chars < 0x20.
_ESCAPE_MAP = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def hash_scalar_tuple(*parts: str) -> str:
    """Pipe-join scalar string parts, SHA-256 the UTF-8 bytes, return uppercase hex.

    Mirrors ``dg_identity.compute_dg_id`` / ``DgIdMintingService.Mint`` byte-for-byte:
    ``"|".join(parts)`` encoded UTF-8, SHA-256, ``.hexdigest().upper()``. Returns the
    full 64-character digest (callers wanting the 16-char dgId form slice it
    themselves, as ``compute_dg_id`` already does).

    Raises ``ValueError`` naming the offending position for any non-string or
    empty-after-strip part, following ``DgIdMintingService``'s argument-guard style.
    """
    if not parts:
        raise ValueError("hash_scalar_tuple requires at least one part")
    for i, part in enumerate(parts):
        if not isinstance(part, str):
            raise ValueError(f"hash_scalar_tuple part at position {i} must be a string, got {type(part).__name__}")
        if part.strip() == "":
            raise ValueError(f"hash_scalar_tuple part at position {i} must not be empty or whitespace-only")
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest().upper()


def _canonicalize_string(s: str) -> str:
    """NFC-normalize (rule 4) and JSON-escape only the mandatory characters (rule 5)."""
    normalized = unicodedata.normalize("NFC", s)
    out = []
    for ch in normalized:
        if ch in _ESCAPE_MAP:
            out.append(_ESCAPE_MAP[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            # Non-ASCII characters are left unescaped (rule 5) -- deliberate choice,
            # this internal evidence JSON is never rendered into HTML.
            out.append(ch)
    return '"' + "".join(out) + '"'


def _canonicalize_number(value: Any, field: str = "<value>") -> str:
    """Render integers with no decimal point; Decimal as fixed-point; reject float."""
    if isinstance(value, bool):
        # bool is a subclass of int in Python -- must not fall through to int handling.
        raise TypeError(f"canonicalize: field {field!r} is a bool, not a JSON boolean-compatible number path")
    if isinstance(value, float):
        raise TypeError(
            f"canonicalize: field {field!r} is a float ({value!r}); IEEE-754 formatting diverges "
            "across languages. Use decimal.Decimal for non-integer numbers, or represent a "
            "non-finite/indeterminate result via the 'indeterminate'/'error' canonical status instead."
        )
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(
                f"canonicalize: field {field!r} is a non-finite Decimal ({value!r}); NaN and Infinity "
                "are forbidden in canonical form (rule 6). Represent this as the 'indeterminate' or "
                "'error' canonical status instead."
            )
        # Fixed-point string, never scientific notation.
        return format(value, "f")
    raise TypeError(f"canonicalize: field {field!r} has unsupported numeric type {type(value).__name__}")


def _walk(value: Any, field: str = "<root>") -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(
                f"canonicalize: field {field!r} is NaN or Infinity; forbidden in canonical form (rule 6). "
                "Represent this as the 'indeterminate' or 'error' canonical status instead."
            )
        raise TypeError(
            f"canonicalize: field {field!r} is a float ({value!r}); IEEE-754 formatting diverges "
            "across languages. Use decimal.Decimal for non-integer numbers."
        )
    if isinstance(value, (int, Decimal)):
        return _canonicalize_number(value, field)
    if isinstance(value, str):
        return _canonicalize_string(value)
    if isinstance(value, (list, tuple)):
        items = [_walk(item, f"{field}[{i}]") for i, item in enumerate(value)]
        return "[" + ",".join(items) + "]"
    if isinstance(value, dict):
        # Rule 1: sort keys ascending by Unicode code point (ordinal). Also NFC-
        # normalize keys before sorting/emitting, per rule 4 ("every string value
        # and every object key").
        normalized_items = [
            (unicodedata.normalize("NFC", str(k)), v) for k, v in value.items()
        ]
        normalized_items.sort(key=lambda kv: kv[0])
        parts = []
        for k, v in normalized_items:
            key_str = _canonicalize_string(k)
            val_str = _walk(v, f"{field}.{k}")
            parts.append(f"{key_str}:{val_str}")
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"canonicalize: field {field!r} has unsupported type {type(value).__name__}")


def canonicalize(value: Any) -> str:
    """Produce the canonical serialization of ``value``, implementing all six rules.

    1. Object keys sorted ascending by Unicode code point.
    2. Integers rendered with no decimal point/leading zeros; non-integers only from
       ``decimal.Decimal`` as fixed-point strings; ``float`` raises ``TypeError``.
    3. No insignificant whitespace (minimal separators ``,`` and ``:``).
    4. Every string value and object key normalized to Unicode NFC.
    5. Only ``"``, ``\\``, and control characters below 0x20 are escaped; non-ASCII is
       left unescaped.
    6. NaN and Infinity raise -- never representable in canonical form.

    Implemented as an explicit recursive walk (never delegates to the standard
    library's generic serializer) so the escaping and number rules stay under this
    module's control and are exactly mirror-able in C#.
    """
    return _walk(value)


def hash_canonical(value: Any) -> str:
    """Canonicalize ``value``, SHA-256 the UTF-8 bytes, return uppercase hex."""
    canonical = canonicalize(value)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
