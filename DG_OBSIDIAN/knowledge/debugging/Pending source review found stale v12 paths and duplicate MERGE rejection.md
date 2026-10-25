---
tags: [debugging, pending-review, cypher, evidence, reproducibility]
date: 2026-10-25
status: open
---

# Pending source review found stale v12 paths and duplicate MERGE rejection

Independent read-only review of old uncommitted source/test/spec changes, performed against the main-root dirty files on 2026-10-25. These changes were NOT accepted, committed or deployed by this review. Line numbers below are checkpoint-local and should be reverified before editing.

## Reproduced issues

### Stale v12 report paths

`data-service/tests/recognition_eval/test_repeat_sweep.py:422–424` reads the old `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/llm-evidence/llm-repeatability-report.json` path. Tests starting near 434 and 463 share this helper. Executing the current AST-extracted helper reproduced FileNotFoundError. The phase has moved under `.planning/milestones/v12.0-phases/`; verify the exact report there before changing the reference. No Neo4j or Docker dependency caused this error.

`spec/SWRL-SUBSET.md:240` likewise references old `1201-06-SUMMARY.md` under active phases. These paths belong to pending local edits; the review does not authorize broader spec admission.

### Repeated idempotent MERGE falsely rejected

`data-service/cypher_allowlist.py:601,1459–1477`: write_edges records syntactic occurrences; structural gate counts them as graph cardinality. Appending either an identical `MERGE (a2)-[:REFERS_TO]->(up)` or `MERGE (a2)-[:ARG {pos:1}]->(v0)` to the new test's valid a1_cypher fixture passes write allowlisting but triggers “expected exactly one REFERS_TO” / invalid or duplicated ARG positions. Identical MERGE is idempotent, not a second stored edge.

Candidate direction, NOT implemented: normalize identical MERGE facts while preserving rejection of genuinely distinct/ambiguous edges, CREATE duplicates, and invalid argument positions. Add red/green tests before modifying the gate. Gate is producer-local, not a complete stored graph validator; no full HAS_BODY/HAS_HEAD, incoming-edge or pre-existing database-state proof is implied.

### Evidence/source drift

Three UI JSON reports are historical offline/synthetic reports, not current live acceptance. Current source SHA comparisons, both raw and CRLF-normalized:
- `ui-v2/tests/evidence/degram-verified.json`: 45 mismatches of 83;
- `degram-commit-preflight.json`: 45 of 79;
- `degram-latest.json`: 32 of 103.

Reports themselves disclose synthetic matched API responses/no live service and bundler-input rather than executed-module coverage. Keep historical labeling; mismatches do not prove fabrication or invalidate the historical run, but cannot support current UI/installed Desktop/live stack acceptance.

### Contradictory harness warning

`DG/tools/DG.De01Harness/Program.cs:251–257` now comments that ObjectPropertyAtom exclusion is synthetic, but warning at 364–371 still claims ResolveAtomType lacks its branch. Hard-coded OBJ_GOLD_FAIL is not generic evaluator conformance evidence. Status preservation change is sensible but does not establish independent object-property evaluation.

## Provenance and verification limits

`.planning/phases/1308-dg-web-ui/1308-ROLLOUT.md:29–44` lists eight modified/four untracked files as OLD UNCOMMITTED work excluded from the 13 October clean-HEAD rollout. This demonstrates prior existence of the named set, not author identity or today's exact bytes. Spec addenda, C# harness/CLI tests and untracked RuleEvaluatorBuiltinBoundaryTests.cs are not covered by that list. Do not use the rollout's in-container results to validate excluded edits.

Reviewer checks: 12 Python AST parses; direct structural-gate probes; retained helper FileNotFoundError; synthetic Markdown renderer; three JSON source-hash comparisons; whitespace and selected BOM/EOL checks. Full pytest/.NET/browser suites were not run. C# boundary tests appeared consistent by source review only; CLI tests require a rebuilt Release DLL, stale binaries are not proof.

Retained replay in report.py uses private CassetteAdapter._load and caller historical metadata; replay/scoring determinism is not provider attestation/Cypher correctness. Immutability tests model limited Cypher with a fake state machine, not real transaction/concurrency behavior. test_rule_conflict.py covers fake-query endpoint scenarios, not real Cypher/atomic supersede.

## Separate packer result

Independent review of `a22f6b7` found the narrow runtime catalogue/template inclusion sound: direct-child matching excludes nested secret-shaped paths, all five current catalogue templates covered, existing path/symlink/hash guards retained. Optional paths do not enforce dependency completeness. Controller's server-kit suite: 23/23. This is not full release/native recovery acceptance.

Next: owner decides old-cluster admission; fixes and focused verification then occur in an explicitly scoped change. See [[sessions/2026-10-25 Stand update and milestone13 consolidation]], [[knowledge/decisions/Milestone13 cleanup preserves pending source changes and excludes generated evidence]].
