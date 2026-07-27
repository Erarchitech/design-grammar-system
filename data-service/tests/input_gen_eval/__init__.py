"""SC1 measurement harness for AI-generated Grasshopper script inputs
(Phase 38 plan 07: GHIN-01/02/03).

Mirrors `data-service/tests/recognition_eval/`'s package shape (Phase
35-11/35-13 precedent): pure scoring functions in `scoring.py`, a
cassette-backed pytest module (`../test_input_gen_eval.py`) that asserts the
five SC1 thresholds fixed in `spec/API.md`'s SC1 acceptance-thresholds table.

Test-only, like `recognition_eval/` -- this package is never imported from
production code (`data-service/cg_input_generation.py`,
`cg_input_sampler.py`, `cg_input_bindings.py` do not import it, and never
should).
"""
