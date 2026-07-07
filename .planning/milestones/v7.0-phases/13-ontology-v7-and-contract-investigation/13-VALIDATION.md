---
phase: 13
slug: ontology-v7-and-contract-investigation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-03
approved: 2026-07-03
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> This is an ontology/documentation phase — deliverables are OWL files, Python transform scripts, and markdown artifacts. Validation is through self-checking scripts and behavioral spot-checks, not traditional unit tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3.x inline self-checks (no external test runner) |
| **Config file** | none — scripts use `if __name__ == "__main__"` entrypoints |
| **Quick run command** | `python ontology/apply_v7_rename.py` |
| **Full suite command** | `python ontology/apply_v7_rename.py && python ontology/apply_v7_extensions.py && cd ontology && python make_export_v7.py && python make_docs_v7.py` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run the affected script's self-check (`python ontology/<script>.py`)
- **After every plan wave:** Run all affected scripts in dependency order
- **Before `/gsd-verify-work`:** Full suite must be green (all scripts exit 0, all XML parses)
- **Max feedback latency:** 3 seconds (scripts are fast, linear transformations)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | ONTO-04 | — | Conflict (a): ValidStatus resolution documented | manual | `grep -c "ValidStatus.*Boolean" ontology/V7-INVESTIGATION.md` | ✅ | ✅ green |
| 13-01-02 | 01 | 1 | ONTO-04 | — | Complete V6→V7 rename table with all 14 rows | manual | `grep -c "→" ontology/V7-INVESTIGATION.md` | ✅ | ✅ green |
| 13-02-01 | 02 | 2 | ONTO-01 | — | Script reads V6, writes V7, prints OK | self-check | `python ontology/apply_v7_rename.py` | ✅ | ✅ green |
| 13-02-02 | 02 | 2 | ONTO-01, ONTO-02 | OWL-construct collision | DesignGrammar-V7.owl produced with all renames, zero banned tokens | self-check | `python ontology/apply_v7_rename.py` (asserts zero banned tokens, OWL construct parity) | ✅ | ✅ green |
| 13-02-03 | 02 | 2 | ONTO-02 | — | V6-to-V7-mapping.md emitted from script's RENAMES list | self-check | `python ontology/apply_v7_rename.py` (mapping writer is part of script) | ✅ | ✅ green |
| 13-03-01 | 03 | 3 | ONTO-06 | — | 14-component port map with 66 rows, zero unmapped output ports | manual | `grep -cP "^\|" ontology/port-iri-map-V7.md` | ✅ | ✅ green |
| 13-03-02 | 03 | 3 | ONTO-06 | — | All 25 ontology IRIs resolve in DesignGrammar-V7.owl | manual | `grep -c "resolved in DesignGrammar-V7.owl" ontology/port-iri-map-V7.md` | ✅ | ✅ green |
| 13-04-01 | 04 | 3 | ONTO-05 | — | Extension facades generated with V7 names | self-check | `python ontology/apply_v7_extensions.py` | ✅ | ✅ green |
| 13-04-02 | 04 | 3 | ONTO-05 | — | OASIS catalog maps all 4 DG IRIs to V7 files | manual | `grep -c "DesignGrammar-V7" ontology/catalog-v001-V7.xml` | ✅ | ✅ green |
| 13-04-03 | 04 | 3 | ONTO-05 | — | Markdown docs regenerated from V7 owl with zero V6 residue | self-check | `python ontology/make_export_v7.py && python ontology/make_docs_v7.py` | ✅ | ✅ green |
| 13-04-04 | 04 | 3 | ONTO-05 | — | All V7 owl + XML files parse as well-formed XML | manual | `python -c "import xml.dom.minidom; [xml.dom.minidom.parse(f) for f in ['DesignGrammar-V7.owl','DesignGrammar-BOT-extension-V7.owl','DesignGrammar-Topologic-extension-V7.owl','DesignGrammar-standards-extension-V7.owl','catalog-v001-V7.xml']]"` (from ontology/) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new dependencies or test frameworks needed:
- `ontology/apply_v7_rename.py` — self-checking V6→V7 transform (8 assertions)
- `ontology/apply_v7_extensions.py` — self-checking extension transform (1 assertion)
- `ontology/make_export_v7.py` + `ontology/make_docs_v7.py` — doc generation chain
- Behavioral spot-checks in `13-VERIFICATION.md` (8 checks, all PASS)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| V6 source files byte-for-byte unchanged | ONTO-01, ONTO-05 | Git checksum verification — no automated script for this in ontology pipeline | `git diff --stat ontology/DesignGrammar-V6.owl ontology/DesignGrammar-BOT-extension-V6.owl ontology/DesignGrammar-Topologic-extension-V6.owl ontology/DesignGrammar-standards-extension-V6.owl ontology/catalog-v001-V6.xml` — must be empty |
| Port map IRI resolution in V7 owl | ONTO-06 | Cross-referencing 25 distinct IRIs across two files — OWL-aware resolver needed; grep-based spot-check suffices | Read `ontology/port-iri-map-V7.md` Resolution check footer; verify "25 ontology IRIs referenced, all resolved" |
| OWL construct count parity (owl:ObjectProperty, owl:DatatypeProperty) | ONTO-01 | Exact count comparison between V6 and V7 requires context-aware counting (not substring matching) | `grep -c "owl:ObjectProperty" ontology/DesignGrammar-V6.owl` must equal `grep -c "owl:ObjectProperty" ontology/DesignGrammar-V7.owl` (87 vs 87) |
| Human-readable doc quality (V7 names, no stale V6 text) | ONTO-05 | Natural language prose review — cannot be fully automated | Read `ontology/DesignGrammar-V7.md` section headers; verify state trio (ObjState/ParamState/PropState), rule props (SWRL/RuleName/RuleDescription), no "ObjectState"/"DefState"/"ReinstatementStatus" in body text |

---

## Validation Sign-Off

- [x] All tasks have automated verification or documented manual checks
- [x] Sampling continuity: self-checks run per-plan, full suite at wave boundaries
- [x] Wave 0 covers all MISSING references (no missing references — 0 gaps)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-03
