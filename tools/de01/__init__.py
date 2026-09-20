"""DE-01: the standalone cross-service runner (spec/EVIDENCE-CONTRACT.md section 8).

Drives fixtures/golden/fixture.json through all four legs (data-service, dg-reasoner,
the C# evaluator via DG.De01Harness, and the persisted-replay leg), compares canonical
statuses per (rule, object) pair, and emits a structured JSON report plus a
human-readable Markdown report. See tools/de01/README.md for invocation.
"""
