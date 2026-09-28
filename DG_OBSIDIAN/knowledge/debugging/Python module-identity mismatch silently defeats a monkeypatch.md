---
tags: [debugging, python, testing, v12.0, phase-1204]
date: 2026-09-28
---

# Python module-identity mismatch silently defeats a monkeypatch

**Symptom:** A live-run driver script patched `cassette_module._FIXTURES_ROOT` to redirect where `CassetteAdapter` writes recorded cassettes — away from the FROZEN `data-service/fixtures/recognition_eval/cassettes/` directory and into a scratch location. The patch appeared to succeed (no error), but the first 7 live-recorded cassettes landed in the frozen directory anyway.

**Root cause:** `repeat_sweep.py` (the module actually driving the recording) imports cassette as `from recognition_eval import cassette as cassette_module` — a package-qualified import. The driver script's own `import cassette as cassette_module` (with only `recognition_eval/`'s own directory, not its parent, on `sys.path`) resolved the *same physical file* but bound it under a *different key* in `sys.modules` (`"cassette"` vs. `"recognition_eval.cassette"`). Python caches modules by their full dotted import path, so these were two entirely separate module objects, each with its own `_FIXTURES_ROOT` global. Patching one never touched the other.

**Fix:** Never construct a fresh import path for a module a target library already imported internally. Instead, reach through the already-imported reference: `cassette_module = repeat_sweep.cassette_module` (reads the attribute `repeat_sweep.py`'s own `from ... import ... as cassette_module` statement bound on that module). This guarantees identity with whatever the target code actually calls into.

**Verification:** Before trusting a monkeypatch on a shared/global module attribute in a multi-import-path codebase, verify identity directly: `assert target_module.some_submodule is my_own_import` (or just always read the attribute off the already-imported parent, as above) rather than assuming `import x` and `from pkg import x` always give you the same object — they do NOT, unless the import paths resolve identically.

**Blast radius this time:** Caught immediately (checked `find /app/fixtures/recognition_eval/cassettes -newer ...` right after the first live run) and cleaned up before any commit. The container's filesystem is a build-time image snapshot, not bind-mounted to the host, so the host's git-tracked frozen cassettes were never actually at risk — but this could have been a real frozen-fixture violation in a bind-mounted setup, and is exactly the class of "silent wrong-target write" bug worth defending against systematically, not just catching by luck.

**Related:** [[Phase 35 latent parser bug — pattern host resolved by document order]] (a different flavor of "code silently does the wrong thing due to an ordering/identity assumption")
