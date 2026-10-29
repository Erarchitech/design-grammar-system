# F27 — generated Atom schema admission

Status: source fix tested; final independent review PASS; two modules deployed and read-back verified; A1 repaired transactionally and persisted read-back verified; live GH/publication/Model Viewer pending.

## Root cause and observed evidence

A1 SWRL text was preserved by Ingest, but Neo4j contains five atoms with obsolete `Builtin_iri = swrlb:...`, no type/iri/REFERS_TO. This is invalid structural encoding, not a legitimate Unsupported outcome. The owner's RULE DECONSTRUCT screenshot corroborates failure to classify ?m/?v1/?v2. The doubled ? is message formatting and was not changed in this work.

Live workflow `a1b2c3d4-e5f6-7890-abcd-ef1234567890` is active and uses `/context/generate-cypher` (no legacy workflow bypass found). Source validation enforced allowed grammar/project ownership but lacked atom completeness/type/reference checks. No claim is made about the exact original provider response: a current workflow export and persisted malformed graph were inspected; retained n8n execution history does not contain this latest run.

## Change

- Reuse lexer/parser write-node, property and directed-edge metadata; quoted strings cannot forge links.
- Add `check_ingest_atom_structure` to production project-aware `validate_cypher` for rule_ingest/rule_edit.
- Require known Atom.type, nonempty Atom.iri, exactly one matching typed REFERS_TO, argument links with distinct contiguous positions and matching Var/Literal targets. Reject obsolete Builtin_iri and non-builtin swrlb prefixes.
- Preserve variable builtin arity and all existing catalog shapes (recognition != evaluator support); no new vocabulary or schema.
- Reject and feed corrections into existing bounded generate/retry loop; do not silently repair model output.

## Verification

- RED: exact F27-shaped output previously admitted (`valid=True`); regression failed with expected assertion.
- GREEN: regression plus A1 valid encoding, missing/wrong reference, fake links in string, wrong predicate/type, ARG loss/duplicates, incoming-direction reference, inline Atom props, and generate retry tests pass.
- Relevant suites: **828 passed / 16 skipped** (`test_ingest_atom_structure`, `test_dg_context`, `test_cypher_allowlist`); one preexisting Starlette/httpx deprecation warning.
- Complete review diff includes both tracked files and new test file; git apply --numstat checked. SHA256 `06930c72b5001eda7a0a7bcd2851774a527b6a11f8f84c475081a8f3e6f4f1f9`.

## Remaining authorized work

### Deployment and A1 repair completed

Third review PASS; parent verified current code/test diff SHA256 exactly matches `0f350b252f050948661f18d6b8cdb484fd2ff01152ac31e2eded5e2c19614ce0`. Relevant suites 848 pass/16 skip. Backed up `/app/cypher_allowlist.py` and `/app/dg_context.py` under `/app/F27-backup`, deployed ONLY those files and restarted data-service. SHA256 source/container match; actual `/app` production validate rejects malformed fixture and accepts typed A1; `/auth/options` HTTP 200. This is a container hotfix, not a rebuilt Docker image; recreation from the old image will lose it until the authorized image rebuild.

`9-repair-A1.py` repaired exactly A1 in one transaction, retaining Rule properties/SWRL and ARG/composition edges. Created missing Class FacadeModule/PatternNode and ObjectProperty hasUpperVertex/hasLowerVertex, assigned the five correct Atom types/iris, removed obsolete Builtin_iri and linked REFERS_TO. Commit followed by exact persisted read-back verification. Other 11 full rule subgraphs unchanged: SHA256 `947aa43987732813daab2aa04099411fce1f22fe545d97f5f50ca9fb4bdf56d2`. Evidence: `9-A1-repair-evidence.json`, `9-A1-before-repair.json`, `9-A1-after-repair.json`.

The subsequent RhinoCode repository read produced no result and Rhino UI became blocked again (no GH solution running). Cause not proven; do not assert a modal exists. One Cordyceps output read timed out. CAD requests stopped. No publication attempted. Owner needs to restore responsive UI/reload, then refresh METAGRAPH; do not re-ingest A1. The synchronous Neo4j repository read probe is suspect and must not be rerun unchanged; use async read/task or isolated metadata read instead.

### Review correction checkpoint

First reviewer reproduced negative ARG positions, undirected extra ARG/REFERS_TO, DataProperty literal subject, and duplicate Atom_Id declarations under different variables. New regressions first failed on all five cases (two undirected variants). Corrections retain numeric signs, record/reject undirected Atom edges, validate DataProperty subject as Var, and reject duplicate persisted Atom identities. Additional tests cover noncanonical positions, later null overrides and chained incoming/outgoing links. Current relevant suites: **840 passed / 16 skipped**, same preexisting deprecation warning. Second complete review diff SHA256 `c864a74027159ed6331af372c8c35c79db0b51230ba57c8df46ca8365980af82`, validated by git apply --numstat. No deploy/graph mutation before review acceptance.

1. Apply any review corrections; run broader suites; deploy only the corrected modules, preserving unrelated service/source changes.
2. Snapshot A1 plus other 11 rule subgraphs, repair exactly the five A1 atoms and four missing vocabulary nodes/links in one transaction, retain Rule_Id and exact SWRL, verify other rule snapshots unchanged. No delete/re-ingest that could blend rules or change shared Vars.
3. Read the repaired rule with actual GH repository/components, verify A1 Unsupported rather than malformed/no_population, publish only A1 and read back exact Run evidence. Inspect Model Viewer; retain human_needed when UI cannot be reached.

Second review FAILED on identity aliases/renames: final per-variable metadata could lose declaration-time identity, and SET could erase Atom_Id. Eight new regressions first failed. Corrected by retaining declaration metadata, rejecting identity mutations (including temporary change/restore), checking nonempty final Atom_Id and detecting duplicates by declaration-time IDs. Current relevant suites: **848 passed / 16 skipped**. Third/final bounded review pending, diff SHA256 `0f350b252f050948661f18d6b8cdb484fd2ff01152ac31e2eded5e2c19614ce0`. No graph repair, deployment or publication has occurred as of this checkpoint. If another blocking review issue remains, stop the fix loop and discuss scope with owner.
