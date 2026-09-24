# REPRODUCIBILITY.md — the determinism boundary for the data-grammar system

This document is the normative determinism boundary for the data-grammar system. It defines
what may be claimed as reproducibility, for which path, and on what evidence, covering the
DE-01 determinism legs (ALGN12-15) and the LLM/canvas reproducibility benchmark surfaces
(ALGN12-16). It exists so that "deterministic", "reproducible" and "verified" are never used
loosely: every claim in this repository must trace to exactly one class defined here.

The divided ownership split (D-25) is: **phase 1204 owns the definition** recorded in this
document, and **v11.0 SPEC-04 owns the propagation** of that definition into the surrounding
spec corpus, checklists and propagation tables. 1204 defines; SPEC-04 propagates. Changes to
the definitions here are the 1204 contract; changes to how other documents cite them are the
SPEC-04 contract.

## Determinism Classes

Exactly three determinism classes exist. Nothing in this repository may be described by a
class outside this list.

| class | one-line semantics |
| --- | --- |
| `deterministic-measured` | Repeat output was **measured identical across fresh process lifetimes on a fixed fixture** — the DE-01 legs. |
| `model-dependent` | Output depends on a **live model**. Determinism is not claimed and is not measurable by fixture replay alone. |
| `unmeasured` | **No measurement exists.** No determinism claim is permitted, in either direction, for this path. |

`deterministic-measured` is an empirically earned label, not a design intention: it requires a
recorded cross-process repeat measurement on a frozen fixture. `model-dependent` is a property
of the dependency, not a statement about observed variance. `unmeasured` is the default for
every path that has not been measured; absence of evidence is not evidence of determinism.

## Scope Table

One row per governed path. `evidence` names the artifact or procedure that supports the class;
`note` records the qualification that limits the claim.

| path | class | evidence | note |
| --- | --- | --- | --- |
| DE-01 leg: csharp evaluator | `deterministic-measured` | DE-01 leg repeat runs, fresh process lifetimes, fixed fixture | validator determinism, measured |
| DE-01 leg: dg-reasoner evaluator | `deterministic-measured` | DE-01 leg repeat runs, fresh process lifetimes, fixed fixture | validator determinism, measured |
| DE-01 leg: data-service replay relay | `deterministic-measured` | DE-01 leg repeat runs, fresh process lifetimes, fixed fixture | relay, not validator determinism |
| DE-01 leg: data-service live relay | `deterministic-measured` | DE-01 leg repeat runs, fresh process lifetimes, fixed fixture | relay, not validator determinism |
| recognition (`cg_recognition.py|recognize_structure`) | `model-dependent` | measured in this phase | measured; still model-dependent |
| rule-ingest (`dg_context.py|generate_validated_cypher`) | `model-dependent` | measured in this phase | measured; still model-dependent |
| consult (`dg_context.py|consult_computgraph`) | `model-dependent` | none — not measured | unmeasured (D-11) |
| input generation (`cg_input_generation.py|generate_inputs`) | `model-dependent` | none — not measured | unmeasured (D-11) |
| `cg_structure_checks` (the seven structural checks) | `unmeasured` | none | D-03 |
| HermiT OWL consistency | `unmeasured` | none | D-03 |
| Tier-0 recognition + Tier-0 input generation | `unmeasured` | none | D-03 |
| SHACL on non-golden data | `unmeasured` | none | D-03 |
| live Grasshopper solver / canvas | `unmeasured` | none | D-03 |

The four DE-01 legs share one measurement basis — repeat runs across fresh process lifetimes
on a fixed fixture (D-01). The two relay rows are labelled **relay, not validator
determinism**: they assert that the relay faithfully carried a stable payload, which is not a
statement that any validator decided the payload identically for the same reasons.

The five D-03 rows are `unmeasured` because no measurement exists for them. They are not
claimed to be nondeterministic either; the correct statement is that no claim is made. The
live Grasshopper solver/canvas row is `unmeasured` by construction, because canvas state is
live and no fixture capture of it has been taken.

## Projection and Exclusion List

Each DE-01 leg hash is a SHA-256 over the canonical JSON (nested-payload,
canonicalizationVersion 1) of the leg envelope **minus exactly** the exclusion fields. This
document restates the D-04 constants; it does not redefine them, and
`tools/de01/projection_hash.py` remains their single source of truth:

- `EXCLUSION_FIELDS == frozenset({"emittedAt", "generatedAt", "definitionId"})`
- `PROJECTION_VERSION == 1`

The three exclusions and their reasons:

1. `emittedAt` — wall-clock emission timestamp. It changes between two otherwise identical
   runs, so including it would make every projection hash unique and the measurement vacuous.
2. `generatedAt` — report wall-clock timestamp. Same reasoning as `emittedAt`; it records when
   the report was written, not what was measured.
3. `definitionId` — carries the run id. It identifies a particular execution rather than the
   projected content, so it must not participate in the content hash.

Everything else in the envelope is included — `ruleId`, `objectId`, `canonicalStatus`,
`warnings`, `detail`, the envelope's `canonicalStatus`, `serviceName`, `serviceVersion`,
`stage`, and producer hashes as-is. **Rows are normatively sorted**; the ordering is part of
the projection, not incidental to it, so a projection whose rows are permuted is a different
projection and must not be reported as identical.

`hash_scalar_tuple` / `HashScalarTuple` **must never be used** (Correction 10). It is not a
projection of the envelope and cannot be substituted for the D-04 projection under any
circumstances.

**Version-bump rule:** any addition to the exclusion list requires (a) a recorded reason in
this section, and (b) a `PROJECTION_VERSION` bump in `tools/de01/projection_hash.py`. An
exclusion added without both is a defect: it silently changes the meaning of every previously
recorded hash while leaving the version stamp claiming comparability.

## Provenance Fields

The D-19 required provenance block. **A sample missing any required field is void** and must
not be reported as evidence. Provider identity is **host + model**, never the adapter name —
the adapter is an implementation detail of how the call was made, not what answered it.

- adapter name, plus **endpoint host** — never a secret or an auth-bearing URL
- requested model id, served model id, response id, system fingerprint
- Ollama weights digest
- prompt path, prompt sha256, `prompt_version`
- rendered-request sha256
- sampling params as-sent (the literal string `"not sent"` is legal and preferred over silence)
- negotiated structured-output mode
- gateway/service commit
- input sha256
- sample index
- timestamps, usage, `finish_reason`

"Requested model id" and "served model id" are recorded separately and both are required: for
provider-managed endpoints the two routinely differ, and the served id is the only honest
record of what actually answered. Record the endpoint host, never a credentialed URL that
embeds a key; a key must never appear in a provenance record, which is why this document
itself carries no example credentials.

## Reproducibility Classes

The D-22 classes, reproduced verbatim with their reasons:

| class | definition | reason |
| --- | --- | --- |
| `replayable` | Committed cassettes; analysis reproduces exactly, model is not re-run. | The model call is frozen into a committed artifact, so repeating the analysis re-reads the same recorded response. |
| `re-executable-pinned-weights` | Local Ollama with a recorded digest. | Weights are pinned and the digest is recorded, but output is still **not guaranteed bitwise-identical** because of batching and kernel nondeterminism. |
| `not-reproducible-provider-managed` | Cloud provider-managed endpoint. | The cloud model id is an **alias** that can be repointed, there is no seed control, and temperature 0 is only near-deterministic. |

**A bitwise re-execution claim is available only in `replayable`.** The other two classes
support "the analysis can be run again and compared", never "the bytes will match".
`re-executable-pinned-weights` narrows the unknowns (the weights are known) without removing
them (the kernels are not). `not-reproducible-provider-managed` offers the weakest guarantee
of the three, because neither the weights nor the sampling is under local control.

## Non-Claims

Each of these is an explicit refusal to claim, and each is a claim that reviewers and later
phases may rely on being absent:

1. **No claim of determinism holds universally across live LLM output or live canvas state.**
   Nothing in this document asserts that any live-model or live-canvas path behaves the same
   way twice. Claims are per-path and evidence-bound, never global.
2. **Temperature 0 is not determinism.** A temperature-0 setting is only near-deterministic on
   provider-managed endpoints, and it does not survive batching and kernel effects even
   locally. It is a request parameter, not a guarantee.
3. **Cassette replay is not model repeatability.** Replaying a committed cassette reproduces
   the analysis, not the model. It says nothing about what a fresh call would have returned.
4. **Relay legs are not validator determinism.** The DE-01 relay legs measure that a stable
   payload was carried stably. They are not evidence that any validator produced the same
   decision for the same reasons.
5. **The Ollama fallback is not output equivalence.** Falling back to a local Ollama model
   changes the answering model. A fallback run is not interchangeable with, and is not
   evidence about, the provider-managed run it replaced.

## Machine-Checked Scope

The fenced block below is the machine-checked scope for LLM call sites. It is read verbatim by
`tools/de01/tests/test_reproducibility_scope_drift.py`, which asserts that the block and the
set of generative call sites found by static AST scan of `data-service/*.py` agree **in both
directions**. One line per **generative** call site, formatted
`file|function|scope-class`, exactly seven lines:

<!-- reproducibility:llm-call-sites:start -->
```
app.py|llm_generate|model-dependent-unmeasured
app.py|test_llm_settings|model-dependent-unmeasured
cg_recognition.py|recognize_structure|measured
cg_input_generation.py|generate_inputs|model-dependent-unmeasured
dg_context.py|generate_validated_cypher|measured
dg_context.py|consult_computgraph|model-dependent-unmeasured
dg_context.py|select_rules_for_deletion|model-dependent-unmeasured
```
<!-- reproducibility:llm-call-sites:end -->

Excluded as non-generative: `llm_gateway.py|list_models_for_provider` is excluded as
non-generative — it calls `get_adapter` only and never calls `.generate`, so it lists models
and produces no model output. It is recorded here as an exclusion note and must never appear
as a scope-class row in the fenced block.

Scope-class reconciliation against the three determinism classes above: scope-class `measured`
= **model-dependent AND measured by this phase**; scope-class `model-dependent-unmeasured` =
**model-dependent AND not measured by this phase**. `deterministic-measured` **never appears**
in this block, because every LLM call site is model-dependent by definition — reaching a live
model is exactly what makes it a call site.

The scan rule is static and hermetic: for each top-level `data-service/*.py` file, an
`ast.Call` counts only when its function is an `ast.Attribute` named `generate` whose value is
an `ast.Name` whose id contains `adapter`. Callers that only retrieve an adapter (for example
`get_adapter` for model listing) are therefore not matched, and definitions and imports cannot
inflate the count. No data-service module is imported by the checker; only file text is read.

## Enforcement and Ownership

**Machine-checked:** the fenced block in the previous section, via
`tools/de01/tests/test_reproducibility_scope_drift.py`. That test suite is the enforcing
artifact and covers four properties: the documented and scanned call-site sets agree in both
directions (a documented site absent from code fails, and a code site absent from the block
fails); every scope-class is drawn from `{measured, model-dependent-unmeasured}` and none is
`deterministic-measured`; and the checker itself is proven to report a synthetic extra entry
and a synthetic missing entry, so a silent no-op checker cannot pass. The
`list_models_for_provider` exclusion is enforced by the scan rule rather than asserted in the
block.

**Documentation discipline:** everything else here — the determinism classes, the scope-table
class and evidence assignments, the projection and exclusion reasons, the provenance field
list, the reproducibility classes, and the five non-claims. These are normative, and reviewers
are expected to hold authors to them, but they are not grep-enforced. The DE-01 leg
measurements are evidence artifacts; their existence is checked by the DE-01 leg tests, not by
this document's checker.

**Ownership (D-25):** phase **1204 owns the definition** recorded in this file. **v11.0
SPEC-04 owns the propagation** of that definition into other specs, checklists and propagation
tables. Editing the definitions here is a 1204 change; editing how other documents cite them
is a SPEC-04 change. A propagated copy that drifts from this file is a SPEC-04 defect, not
permission to change the definition here.

