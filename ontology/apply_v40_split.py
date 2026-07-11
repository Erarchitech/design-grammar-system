"""
Phase 2: v3.4 → v4.0 — Option B file split.

Splits DesignGrammar.owl (which currently contains both DG content AND
cross-vocabulary alignments) into two files:

  1. DesignGrammar.owl (v4.0 core)
     - DG content only (42 DG classes + properties + instances + DG-internal axioms)
     - No owl:imports
     - No cross-vocabulary alignment axioms
     - No external annotation enrichments
     - Clean Protégé view by default

  2. DesignGrammar-aligned.owl (v4.0 facade)
     - Imports DesignGrammar.owl + 7 external vocabularies
     - Contains all 49 cross-vocabulary alignment axioms (moved from core)
     - Contains all 17 external annotation enrichments (moved from core)
     - Used when full cross-vocab reasoning / interop is needed

This is the standard W3C "core + extension" layering pattern (e.g. SOSA core +
SSN extension).

Idempotent: re-running detects v4.0 state and exits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# External namespaces — any axiom referencing these IRIs goes to the facade
EXTERNAL_ENTITY_PREFIXES = ["swrl", "prov", "sosa", "sh", "skos", "dcterms", "geo"]

# Hard-coded set of properties that may carry external-IRI references
# Matched as: <PROPERTY rdf:resource="&PREFIX;..."/> on a single line
ALIGNMENT_PROPERTIES = [
    "rdfs:subClassOf",
    "rdfs:subPropertyOf",
    "owl:equivalentClass",
    "owl:equivalentProperty",
]


# ============================================================
# Aligned-file header
# ============================================================

ALIGNED_HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE rdf:RDF [
    <!ENTITY owl     "http://www.w3.org/2002/07/owl#">
    <!ENTITY rdf     "http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <!ENTITY rdfs    "http://www.w3.org/2000/01/rdf-schema#">
    <!ENTITY xsd     "http://www.w3.org/2001/XMLSchema#">
    <!ENTITY dg      "http://example.org/design-grammar#">
    <!ENTITY dgm     "http://example.org/design-grammar/metagraph#">
    <!ENTITY dgv     "http://example.org/design-grammar/validation#">
    <!ENTITY dgk     "http://example.org/design-grammar/knowledge#">
    <!ENTITY swrl    "http://www.w3.org/2003/11/swrl#">
    <!ENTITY prov    "http://www.w3.org/ns/prov#">
    <!ENTITY sosa    "http://www.w3.org/ns/sosa/">
    <!ENTITY sh      "http://www.w3.org/ns/shacl#">
    <!ENTITY skos    "http://www.w3.org/2004/02/skos/core#">
    <!ENTITY dcterms "http://purl.org/dc/terms/">
    <!ENTITY geo     "http://www.opengis.net/ont/geosparql#">
]>

<rdf:RDF
    xmlns:rdf="&rdf;"
    xmlns:rdfs="&rdfs;"
    xmlns:owl="&owl;"
    xmlns:xsd="&xsd;"
    xmlns:dg="&dg;"
    xmlns:dgm="&dgm;"
    xmlns:dgv="&dgv;"
    xmlns:dgk="&dgk;"
    xmlns:swrl="&swrl;"
    xmlns:prov="&prov;"
    xmlns:sosa="&sosa;"
    xmlns:sh="&sh;"
    xmlns:skos="&skos;"
    xmlns:dcterms="&dcterms;"
    xmlns:geo="&geo;"
    xml:base="http://example.org/design-grammar/aligned">

    <!-- ============================================================
         DESIGN GRAMMAR — ALIGNED FACADE (v4.0)

         This facade ontology imports the core DG ontology AND the seven
         external vocabularies DG aligns with, then declares the
         cross-vocabulary alignment axioms and annotation enrichments.

         Use this file when you need:
           - HermiT reasoning over DG + external vocabs together
           - Cross-vocab queries (e.g. "all prov:Activity instances in DG")
           - Tools that consume PROV-O / SOSA / SHACL / etc. natively

         For DG-only work (lean Protégé view, schema editing, fast load),
         open DesignGrammar.owl directly.

         Pattern: standard W3C "core + extension" layering, same as
         SOSA core + SSN extension.
         ============================================================ -->

    <owl:Ontology rdf:about="http://example.org/design-grammar/aligned">
        <rdfs:label xml:lang="en">Design Grammar (aligned facade)</rdfs:label>
        <rdfs:comment xml:lang="en">Cross-vocabulary alignment facade for the Design Grammar System ontology. Imports the DG core ontology and seven established W3C/OGC vocabularies (SWRL, PROV-O, SOSA, SHACL, SKOS, DCTerms, GeoSPARQL) and declares the alignment axioms that bridge them. See ONTOLOGY-ALIGNMENT.md for rationale (R1-R7).</rdfs:comment>
        <owl:versionInfo>4.0</owl:versionInfo>
        <owl:imports rdf:resource="http://example.org/design-grammar"/>
        <owl:imports rdf:resource="http://www.w3.org/2003/11/swrl"/>
        <owl:imports rdf:resource="http://www.w3.org/ns/prov-o#"/>
        <owl:imports rdf:resource="http://www.w3.org/ns/sosa/"/>
        <owl:imports rdf:resource="http://www.w3.org/ns/shacl#"/>
        <owl:imports rdf:resource="http://www.w3.org/2004/02/skos/core"/>
        <owl:imports rdf:resource="http://purl.org/dc/terms/"/>
        <owl:imports rdf:resource="http://www.opengis.net/ont/geosparql"/>
    </owl:Ontology>

'''

ALIGNED_FOOTER = '\n</rdf:RDF>\n'


# ============================================================
# Extraction logic
# ============================================================

def is_external_ref_line(line: str) -> bool:
    """Return True if this line is an inline alignment axiom referencing an
    external vocabulary (one of EXTERNAL_ENTITY_PREFIXES)."""
    for prop in ALIGNMENT_PROPERTIES:
        for prefix in EXTERNAL_ENTITY_PREFIXES:
            pattern = f'<{prop} rdf:resource="&{prefix};'
            if pattern in line:
                return True
    return False


def extract_inline_alignments(content: str) -> tuple[str, list[tuple[str, str]]]:
    """Walk through every <owl:Class> and <owl:ObjectProperty> /
    <owl:DatatypeProperty> declaration; remove inline alignment axioms
    that reference external IRIs. Return (cleaned_content, list of
    (subject_iri, axiom_line) pairs that were extracted)."""

    extracted: list[tuple[str, str]] = []

    # Match a complete entity declaration block:
    # <owl:Class rdf:about="..."> ... </owl:Class>
    # <owl:ObjectProperty rdf:about="..."> ... </owl:ObjectProperty>
    # <owl:DatatypeProperty rdf:about="..."> ... </owl:DatatypeProperty>
    decl_pattern = re.compile(
        r'(<owl:(?:Class|ObjectProperty|DatatypeProperty) rdf:about="([^"]+)">)(.*?)(</owl:(?:Class|ObjectProperty|DatatypeProperty)>)',
        re.DOTALL,
    )

    def process_block(m: re.Match) -> str:
        opening, subject_iri, body, closing = m.group(1), m.group(2), m.group(3), m.group(4)
        # Skip if subject itself is external (we don't strip enrichment blocks here — those are <rdf:Description>)
        # Only keep alignments from internal DG classes/properties
        if any(subject_iri.startswith(f"&{p};") or f"//{p}" in subject_iri for p in EXTERNAL_ENTITY_PREFIXES):
            return m.group(0)

        # Split body by lines, filter out external-ref lines
        new_lines = []
        for line in body.split("\n"):
            if is_external_ref_line(line):
                extracted.append((subject_iri, line.strip()))
            else:
                new_lines.append(line)
        return opening + "\n".join(new_lines) + closing

    new_content = decl_pattern.sub(process_block, content)
    return new_content, extracted


def extract_external_descriptions(content: str) -> tuple[str, list[str]]:
    """Remove <rdf:Description rdf:about="&PREFIX;..."> ... </rdf:Description>
    blocks where the subject is an external IRI. Return cleaned content and
    list of removed blocks."""

    removed: list[str] = []

    # Build pattern for any external Description block
    prefixes_alt = "|".join(EXTERNAL_ENTITY_PREFIXES)
    pattern = re.compile(
        rf'(    <rdf:Description rdf:about="&(?:{prefixes_alt});[^"]+">.*?</rdf:Description>\s*\n)',
        re.DOTALL,
    )

    def capture(m: re.Match) -> str:
        removed.append(m.group(1))
        return ""

    new_content = pattern.sub(capture, content)
    return new_content, removed


def remove_imports(content: str) -> tuple[str, list[str]]:
    """Remove <owl:imports rdf:resource="..."/> declarations from the
    ontology header. Return cleaned content and list of removed import IRIs."""
    removed: list[str] = []
    pattern = re.compile(
        r'\s*<owl:imports rdf:resource="([^"]+)"/>\n'
    )

    def capture(m: re.Match) -> str:
        removed.append(m.group(1))
        return ""

    new_content = pattern.sub(capture, content)
    return new_content, removed


def remove_enrichment_comment_block(content: str) -> str:
    """Remove the v3.4 'EXTERNAL CLASS ANNOTATION ENRICHMENT' comment block
    from the core file (the actual <rdf:Description> blocks are removed by
    extract_external_descriptions; this just removes the leftover header)."""
    pattern = re.compile(
        r'\s*<!-- ============================================================\s*'
        r'\s*EXTERNAL CLASS ANNOTATION ENRICHMENT \(v3\.4 Fix 2\).*?'
        r'============================================================ -->\s*\n',
        re.DOTALL,
    )
    return pattern.sub("\n", content, count=1)


def strip_external_entity_decls(content: str) -> str:
    """Remove the <!ENTITY swrl ...>, <!ENTITY prov ...> etc declarations
    plus xmlns:swrl etc bindings from the core file, since core no longer
    references external IRIs."""
    for prefix in EXTERNAL_ENTITY_PREFIXES:
        # Remove <!ENTITY prefix "url"> line
        content = re.sub(
            rf'    <!ENTITY {prefix}\s+"[^"]+">\n',
            "",
            content,
        )
        # Remove xmlns:prefix="&prefix;" attribute
        content = re.sub(
            rf'    xmlns:{prefix}="&{prefix};"\n',
            "",
            content,
        )
    return content


def update_core_version_and_seealso(content: str) -> str:
    """Bump version 3.4 → 4.0 and update seeAlso to note the split."""
    content = content.replace(
        "<owl:versionInfo>3.4</owl:versionInfo>",
        "<owl:versionInfo>4.0</owl:versionInfo>",
        1,
    )
    addendum = (
        " v4.0 splits cross-vocabulary alignments into a separate facade ontology "
        "(DesignGrammar-aligned.owl) per Option B in HIERARCHY-OPTIMIZATION.md — "
        "this core file now contains only DG content with no external imports."
    )
    # Append to existing seeAlso (find the closing </rdfs:seeAlso> after the v3.4 text)
    marker = "annotation enrichment for 17 external superclasses."
    if marker in content:
        content = content.replace(marker, marker + addendum, 1)
    return content


# ============================================================
# Aligned file construction
# ============================================================

def build_aligned_file(extracted_axioms: list[tuple[str, str]],
                       extracted_descriptions: list[str]) -> str:
    """Construct the content of DesignGrammar-aligned.owl from the extracted
    alignment axioms and annotation enrichment blocks."""

    # Group axioms by subject IRI so each subject gets one declaration block
    from collections import defaultdict
    by_subject: dict[str, list[str]] = defaultdict(list)
    for subject, axiom in extracted_axioms:
        by_subject[subject].append(axiom)

    body_parts: list[str] = []

    body_parts.append("    <!-- ============================================================\n"
                      "         CROSS-VOCABULARY ALIGNMENT AXIOMS\n"
                      "\n"
                      "         These axioms relate DG classes and properties to their\n"
                      "         counterparts in the imported W3C/OGC vocabularies. Each\n"
                      "         axiom block re-opens an existing DG class declaration (from\n"
                      "         the core DesignGrammar.owl, imported above) and asserts\n"
                      "         additional subClassOf / equivalentClass / equivalentProperty\n"
                      "         / subPropertyOf relations.\n"
                      "         ============================================================ -->\n")

    for subject in sorted(by_subject.keys()):
        axioms = by_subject[subject]
        # Determine the declaration type (Class / ObjectProperty / DatatypeProperty)
        # Use a heuristic: check whether axioms include equivalentProperty/subPropertyOf
        # vs equivalentClass/subClassOf
        prop_axioms = any("Property" in a for a in axioms)
        cls_axioms = any("Class" in a for a in axioms)
        # If both or only class, use owl:Class; if only property, use owl:ObjectProperty
        # The aligned-file declaration just re-opens the same IRI — type doesn't redefine.
        if cls_axioms and not prop_axioms:
            decl_type = "owl:Class"
        elif prop_axioms and not cls_axioms:
            # Need to know if it's ObjectProperty or DatatypeProperty
            # Heuristic from axiom: subPropertyOf with subj IRI we can't determine without reading core
            # Safe approach: use owl:AnnotationProperty? No. Use rdf:Description
            decl_type = None  # will use rdf:Description instead
        else:
            decl_type = "owl:Class"

        body_parts.append("")
        if decl_type:
            body_parts.append(f'    <{decl_type} rdf:about="{subject}">')
            for axiom in axioms:
                body_parts.append(f'        {axiom}')
            body_parts.append(f'    </{decl_type}>')
        else:
            # Use rdf:Description for properties to avoid having to know if it's ObjectProperty or Datatype
            body_parts.append(f'    <rdf:Description rdf:about="{subject}">')
            for axiom in axioms:
                body_parts.append(f'        {axiom}')
            body_parts.append(f'    </rdf:Description>')

    body_parts.append("")
    body_parts.append("    <!-- ============================================================\n"
                      "         EXTERNAL CLASS ANNOTATION ENRICHMENT\n"
                      "\n"
                      "         DG-perspective rdfs:label, rdfs:comment, rdfs:isDefinedBy,\n"
                      "         and rdfs:seeAlso for the 17 external classes DG aligns with.\n"
                      "         Purely additive — does NOT change external-class semantics.\n"
                      "         ============================================================ -->\n")

    for block in extracted_descriptions:
        body_parts.append(block.rstrip("\n"))

    return ALIGNED_HEADER + "\n".join(body_parts) + ALIGNED_FOOTER


# ============================================================
# Main
# ============================================================

def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    core_owl = repo / "ontology" / "DesignGrammar.owl"
    aligned_owl = repo / "ontology" / "DesignGrammar-aligned.owl"

    content = core_owl.read_text(encoding="utf-8")

    # Idempotency check
    if "<owl:versionInfo>4.0</owl:versionInfo>" in content and aligned_owl.exists():
        print("Already at v4.0 (split applied) — no changes.")
        return 0

    if "<owl:versionInfo>3.4</owl:versionInfo>" not in content:
        print("ERROR: expected v3.4 source — run apply_v34_consistency.py first.", file=sys.stderr)
        return 1

    print("Phase 2: splitting v3.4 → v4.0 (Option B)")
    print("-" * 60)

    # Step 1: extract owl:imports
    content, removed_imports = remove_imports(content)
    print(f"  Step 1 (remove owl:imports from core):       {len(removed_imports)} removed")

    # Step 2: extract inline alignment axioms
    content, extracted_axioms = extract_inline_alignments(content)
    print(f"  Step 2 (extract inline alignment axioms):    {len(extracted_axioms)} extracted")

    # Step 3: extract external annotation enrichments
    content, extracted_descriptions = extract_external_descriptions(content)
    print(f"  Step 3 (extract enrichment Descriptions):    {len(extracted_descriptions)} extracted")

    # Step 4: remove the enrichment-block comment leftover
    content = remove_enrichment_comment_block(content)
    print("  Step 4 (remove enrichment comment block):    done")

    # Step 5: strip external ENTITY decls and xmlns bindings (core no longer needs them)
    content = strip_external_entity_decls(content)
    print("  Step 5 (strip external ENTITY/xmlns):        done")

    # Step 6: bump version
    content = update_core_version_and_seealso(content)
    print("  Step 6 (core version bump 3.4 → 4.0):       done")

    core_owl.write_text(content, encoding="utf-8")
    print(f"\n  Wrote core file:    {core_owl} ({core_owl.stat().st_size:,} bytes)")

    # Step 7: build and write the aligned facade
    aligned_content = build_aligned_file(extracted_axioms, extracted_descriptions)
    aligned_owl.write_text(aligned_content, encoding="utf-8")
    print(f"  Wrote facade file:  {aligned_owl} ({aligned_owl.stat().st_size:,} bytes)")

    print("-" * 60)
    print("Phase 2 complete. Two-file structure in place.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
