---
tags: [debugging, spike, reasoner, HermiT]
date: 2026-07-11
---

# HermiT crashes on SWRL builtin atoms — strip before Owlready2 sync_reasoner()

**Symptom:** `run_hybrid.py` crashed with `java.lang.IllegalArgumentException: A SWRL rule uses a built-in atom, but built-in atoms are not supported yet.` when calling `owlready2.sync_reasoner()`.

**Root cause:** `run_hybrid.py` was missing the `strip_hermit_unsupported(g: Graph) -> int` call that `run_naive.py` correctly had. The hybrid export (`hybrid_export.ttl`) contains SWRL builtin atoms from the live Metagraph (5 builtin-using rules in `v8-ui-smoke`). HermiT's underlying OWL API refuses to translate rules with builtin atoms and throws an exception — the bundled HermiT JAR does not support `swrlb:` builtins.

**Context:** This occurred during Phase 820's spike after the original executor agent hit a session limit mid-Task 3. When resuming execution manually, the continuation fixed the missing import and stripping call that the original executor had already included in `run_naive.py` but hadn't yet replicated in `run_hybrid.py`.

**Fix applied (commit `99cf3a5`):**
1. Added `from export import strip_hermit_unsupported` to `run_hybrid.py`
2. Added inline `stripped = strip_hermit_unsupported(g)` call before serialization to NTriples
3. Added the builtin-strip count to the output evidence text

**Lesson:** Both run scripts must strip builtin atoms from HermiT input. The `export.py` module already exports `strip_hermit_unsupported()` — both consumers must call it. Documented in `spec/LPG-OWL-MAPPING.md` (HermiT Builtin-Exclusion Limitation section).

**Also updated:** `spike/README.md` to reflect that Debian trixie ships OpenJDK 21, not 17 (the original instructions referenced `openjdk-17-jre-headless` which no longer exists in the `python:3.11-slim` image base).
