---
tags: [debugging, security, grasshopper, connector, phase-1303]
date: 2026-10-18
status: open — owner to remove the password Panel before the demo
---

# Facade .gh copies sign in to CONNECTOR on open from Panels

**Symptom.** Each Rhino restart or reopen of `v12-hexagonal-facade-01-auto-mapping.gh` created a new mapping session in the project graph, with one LLM call each. About 10 unapplied sessions piled up on 2026-10-18, although nobody had signed in.

**Cause.** CONNECTOR's Username and Password inputs are non-persistent by design: they are not saved in the .gh. In both facade copies (`…-mapping.gh` and its clean copy `…-auto-mapping.gh`), however, they are fed from two `GH_Panel` objects, and the `Connect` toggle is saved as True. The Panel text is serialized in the .gh. So the password sits in those files in plain text, and opening a copy signs in and starts automatic mapping.

The panel values were not read. The source types were checked with a read-only RhinoCode script.

**Mitigation.**
- Both copies are git-ignored (`*.gh`) and are not in the repository. Do not share them.
- Before the demo, delete the Password Panel and type the password into the CONNECTOR input itself, which is non-persistent, or save the copies with Connect = False.
- The leftover sessions are harmless: they are unapplied, and the Mapping panel follows the newest. Nothing was deleted.

**Lesson for agents.** Reopening these copies is a real sign-in and a real session plus an LLM call. Do it only on purpose.

Related: [[sessions/2026-10-18 Phase 1303 automatic mapping in CONNECTOR with LLM proposal and placement up to VALIDATOR|session]], `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs`.
