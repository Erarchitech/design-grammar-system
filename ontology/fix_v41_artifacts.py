"""
One-shot cleanup of artifacts introduced by:
  - apply_v41_simplification.py — left orphaned closing tags after deleting
    DesignStateKindValue and VariableKindValue (their owl:equivalentClass
    blocks contained nested <owl:Class> elements; the non-greedy regex
    matched the inner closing tag, leaving the outer tags dangling).
  - add_layer_hubs.py (v3.3) — inserted <rdfs:subClassOf .../> inside
    enum classes' nested <owl:oneOf> blocks rather than at the outer
    class level. The XML was still well-formed but semantically wrong.

This script:
  1. Removes the two orphan closing-tag groups left from v4.1 deletion.
  2. Moves four misplaced <rdfs:subClassOf rdf:resource="..."/> lines from
     inside <owl:oneOf> blocks to the correct outer-class position.

Idempotent: re-running detects clean state and exits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# ============================================================
# Fix 1: Remove orphaned closing-tag groups from v4.1 deletion
# ============================================================

# Pattern: comment header followed by orphaned closing tags (from VariableKindValue / DesignStateKindValue deletion)
ORPHAN_PATTERNS = [
    # After METAGRAPH ENUMERATIONS — VariableKind, VariableScope comment
    (
        "         METAGRAPH ENUMERATIONS — VariableKind, VariableScope\n"
        "         ************************************************************ -->\n"
        "\n"
        "        </owl:equivalentClass>\n"
        "        <dg:graph rdf:resource=\"&dgm;Metagraph\"/>\n"
        "    </owl:Class>\n"
        "\n",
        "         METAGRAPH ENUMERATIONS — VariableScope\n"
        "         ************************************************************ -->\n"
        "\n",
    ),
    # After VALIDATION ENUMERATIONS — DesignStateKind comment
    (
        "         VALIDATION ENUMERATIONS — DesignStateKind\n"
        "         ************************************************************ -->\n"
        "\n"
        "        </owl:equivalentClass>\n"
        "        <dg:graph rdf:resource=\"&dgv;ValidationGraph\"/>\n"
        "    </owl:Class>\n"
        "\n",
        # Remove entire comment block + orphan tags since DesignStateKind enum is gone
        "",
    ),
]


def fix_orphan_closing_tags(content: str) -> tuple[str, int]:
    fixed = 0
    for old, new in ORPHAN_PATTERNS:
        if old in content:
            content = content.replace(old, new, 1)
            fixed += 1
    return content, fixed


# ============================================================
# Fix 2: Move misplaced <rdfs:subClassOf> from inside <owl:oneOf> blocks
# ============================================================

# Each fix targets an enum class. The misplaced line is INSIDE the equivalentClass
# block (between </owl:oneOf> and </owl:Class>); it must move to AFTER </owl:equivalentClass>
# and BEFORE <dg:graph>. The pattern is consistent across all four affected enum classes.

MISPLACED_FIXES = [
    # Each tuple: (old_block, new_block) — replaces both the misplaced and the empty target spot
    (
        # VariableScopeValue
        '''                </owl:oneOf>
        <rdfs:subClassOf rdf:resource="&dgm;Metagraph"/>
            </owl:Class>
        </owl:equivalentClass>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>''',
        '''                </owl:oneOf>
            </owl:Class>
        </owl:equivalentClass>
        <rdfs:subClassOf rdf:resource="&dgm;Metagraph"/>
        <dg:graph rdf:resource="&dgm;Metagraph"/>
    </owl:Class>''',
    ),
    (
        # DesignStateParameterTypeValue
        '''                </owl:oneOf>
        <rdfs:subClassOf rdf:resource="&dgv;ValidationGraph"/>
            </owl:Class>
        </owl:equivalentClass>
        <dg:graph rdf:resource="&dgv;ValidationGraph"/>
    </owl:Class>''',
        '''                </owl:oneOf>
            </owl:Class>
        </owl:equivalentClass>
        <rdfs:subClassOf rdf:resource="&dgv;ValidationGraph"/>
        <dg:graph rdf:resource="&dgv;ValidationGraph"/>
    </owl:Class>''',
    ),
]


def fix_misplaced_subclassof(content: str) -> tuple[str, int]:
    """The same old/new pattern appears for DesignStateParameterTypeValue,
    ReinstatementStatusValue, and ValidationStatusValue. Replace ALL
    occurrences (replace_all=True semantics)."""
    fixed = 0
    for old, new in MISPLACED_FIXES:
        # Use replace WITHOUT count to catch all occurrences with the same indentation pattern
        n = content.count(old)
        if n > 0:
            content = content.replace(old, new)
            fixed += n
    return content, fixed


# ============================================================
# Main
# ============================================================

def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    owl = repo / "ontology" / "DesignGrammar.owl"
    content = owl.read_text(encoding="utf-8")

    print("Fixing v4.1 artifacts")
    print("-" * 60)

    content, n_orphans = fix_orphan_closing_tags(content)
    print(f"  Orphan closing-tag groups removed:  {n_orphans}")

    content, n_misplaced = fix_misplaced_subclassof(content)
    print(f"  Misplaced subClassOf lines fixed:   {n_misplaced}")

    owl.write_text(content, encoding="utf-8")
    print("-" * 60)

    # Validate well-formed XML
    import xml.etree.ElementTree as ET
    try:
        t = ET.parse(owl)
        elems = list(t.iter())
        print(f"XML parse OK: {len(elems)} elements")
        return 0
    except ET.ParseError as e:
        print(f"XML PARSE ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
