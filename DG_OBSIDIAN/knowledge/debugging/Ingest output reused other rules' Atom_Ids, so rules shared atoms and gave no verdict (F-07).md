---
tags: [debugging, ingest, cypher, metagraph, stand, phase-1303]
date: 2026-10-29
status: fixed (efa6621, b30d2ea; deployed to the stand)
---

# Ingest output reused other rules' Atom_Ids, so rules shared atoms and gave no verdict (F-07)

## Symptom

The Revit check of `isolation-check-a` on the stand gave verdicts for R1 and R5. R2–R4 gave `no_population`
(empty binding set). The Grasshopper path gives the same result: it uses the same DG.Core.

## Root cause

- Atoms are MERGEd on a literal `Atom_Id` in LLM-generated Cypher.
- The output for R3/R4 used `R_..._BEAM_..._V_A1` and `R_..._COLUMN_..._V_A1`, the Atom_Ids of R1 and R2. MERGE found
  those existing atoms. So the rules shared them, and every ARG MERGE added edges to the other rule's atom:
  - R2's `OpeningBox` atom ended up with two arguments (`?o`, `?b`);
  - R3/R4 had three `OpeningBox` atoms with five to seven arguments, and no order-1 atom.
- An atom with several arguments binds to no object, so the population was empty.
- The atom admission check F27 (`check_ingest_atom_structure`) existed only as an uncommitted container hotfix from
  the v12 facade test. The stand never had it, and localhost lost it when data-service was recreated from a commit.

## Fix

- `efa6621` commits F27: Atom.type/iri, one matching REFERS_TO, ARG positions 1..arity.
- `b30d2ea` adds atom ownership:
  - an atom linked by HAS_BODY/HAS_HEAD from more than one rule is rejected;
  - an Atom_Id that is not `<Rule_Id>_A<n>`/`_H<n>` of the linking rule is rejected.
- The violation goes back to the LLM through the bounded corrective retry loop.
- Deployed on the stand (`dg-data-service:f07-b30d2ea`). Checked in the running container: foreign atom rejected,
  F27 shape rejected, valid A1 accepted.

## Data repair

- Deleting only R3 would also have deleted the atoms it shared with R1/R2.
- All five rules were deleted after a JSON backup (`/root/dg-f07-b30d2ea/rules-backup-isolation-check-a.json`); the
  tester enters them again.
- The delete itself exposed a second bug: [[knowledge/debugging/Rule delete kept a rule whose arguments were all shared and still answered deleted]].

## How to spot it

```cypher
MATCH (r:Rule {project:$p})-[:HAS_BODY|HAS_HEAD]->(a:Atom)
WITH a, collect(DISTINCT r.Rule_Id) AS owners
WHERE size(owners) > 1
RETURN a.Atom_Id, owners
```
