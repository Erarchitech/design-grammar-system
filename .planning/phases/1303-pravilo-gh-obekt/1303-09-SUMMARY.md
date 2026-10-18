---
phase: 1303-pravilo-gh-obekt
plan: "09"
status: complete
completed: 2026-10-18
requirements: [DGMAP-01, DGMAP-02, DGMAP-03, DGMAP-04, DGMAP-05]
executor: "controller (Claude, inline); no DSH worker"
commits: [5d723de, 4a131a6, 5ae3972, b6bfd20, 761da66, ab04bb3]
---

# 1303-09 Summary — DG roles on the canvas, LLM proposal, automatic placement up to VALIDATOR

## What was built

- **Engine** (`data-service/mapping_engine.py`), commit `5d723de`:
  - sliders → `dg:Parameter` (`batch-parameters`);
  - calculation outputs → datatype properties (`map_measures`: value agreement with the plugin's own geometry features, acronym, words, canvas text, LLM, measure profiles; `batch-measures` / `map-measure`);
  - an output votes for its stream's class through the classes whose rules use its property;
  - `rule_bindings`: rule → class → property → output → stream; when streams tie, the rule's class picks the stream.
- **LLM proposal** (`mapping_llm.py`, `llm_gateway.py`, `mapping_store.py`):
  - one call per session, only when questions remain; temperature 0, MAX_TOKENS 24000, timeout 420 s (`GenerationOptions.timeout_s`);
  - runs in the background (`LLM_ASYNC`): the session is saved with `llm.status = pending`, and a daemon thread recomputes it with the proposal and the answers given meanwhile;
  - the proposal is validated against the digest and reused for every recompute; the digest uses short aliases s1 / m1 / p1 (`b6bfd20`);
  - call site `mapping_llm.py|propose_mapping` in `spec/REPRODUCIBILITY.md`.
- **DG.gha** (`4a131a6`, `5ae3972`):
  - `MappingMeasureMatcher`: branch keys and agreement; a single value counts as weak;
  - `MappingStreamDedupe`: duplicate streams and unions of other streams are dropped by element bounding boxes;
  - `MappingPlacementPlan` and `MappingPlacer`: after apply, on a canvas without DG states, one group «DG · автоматический меппинг (CONNECTOR)». It holds GRAPH DECONSTRUCT → METAGRAPH, one OBJECT STATE per class and measured stream (`Object = class:<IRI>`), RULE BY ID + PROPERTY STATE per rule binding, PARAMETER STATE, DESIGN STATE and VALIDATOR (`SendValid = false`);
  - new `RuleByIdComponent` (picks a rule by Rule_Id); `ObjectStateComponent` accepts `class:<IRI>` text. No List Item index is placed.
- **Web UI** (`MappingPanel.jsx`, `screens.js`): question labels for the new types, tables «Параметры DG» and «Расчётные выходы», evidence kinds `llm` and `measure`, an LLM status line, a 5 s re-read while the proposal is pending.
- **Rehearsal fix** (`ab04bb3`, 2026-10-18 ~12:05):
  - the mapping-or-design question names the evidence behind the conflicting class and says what each button does, quoting the Web UI labels;
  - an answer that gives a retired profile again switches it back on (`state = active`). Without this, profiles retired for a cold restart would stay off after the same answer, and the next variant would be asked again.

## Verification

- Automated, end of 2026-10-18 morning (before `ab04bb3`; session note): data-service 5771 passed (known environment failures only), DG.Tests 770 passed with 5 known environment failures, ui-v2 322/322, `dotnet build` of DG.Grasshopper Release passed.
- `ab04bb3`: mapping tests 44/44 (`test_mapping_engine.py`, `test_mapping_routes.py`, `test_mapping_llm.py`); the full data-service run is recorded in `1303-UAT.md`.
- Deployment: data-service image built `--no-cache` from `git archive ab04bb3` (`sha256:a360504a…`), container recreated 2026-10-18 11:09 UTC. The served `/app/mapping_engine.py` contains the new code; `POST /mapping/sessions` without credentials → 401 on :8000 and :8080. Rollback tag `design-grammar-system-data-service:pre-ab04bb3` (= `b6bfd20`). UI image unchanged (`5ae3972`).

## Live run (Task 5)

**Checked live on 2026-10-18 (first run, `ms-98a39fa841bc`):**
- canvas reading of the clean copy: 7 streams, 18 outputs, 14 sliders;
- 13 questions without the LLM; the background LLM proposal (`mimo-v2.5-pro`) arrived after 2 min 17 s, then 6 questions;
- dry-run placement on the open copy without saving: 5 OBJECT STATE, 11 RULE BY ID + PROPERTY STATE, DESIGN STATE with 376 objects and 976 values.

**Owner answers in that session:**
- Panels A (120) → BottomTriangularPanel (as the guide says);
- Panels C (123) → «GlassPanel — нарушения правил — ошибки проекта». The guide expected BottomTriangularPanel or «Ни один».

The recorded LLM proposal explains the question. It put GlassPanel on Panels A and Panels C (both triangular) and the panel outputs AR / W / PD / B Panel Ratio on Panels A. Value agreement moved AR, W and PD back to Panels B; B Panel Ratio has no agreement, so it kept the LLM's stream. The old question text did not say why GlassPanel was proposed or what each button does; fixed in `ab04bb3`.

**Owner decision (~12:10):** retire the two profiles from these answers and start again. `P-07e78a4b6bf6` (Panels C → GlassPanel, accepts R_GLASS_ASPECTRATIO_MIN_1.3_V) and `P-7a2d45d381f1` (Panels A → BottomTriangularPanel) are set to `state = retired` with `retiredAt` / `retiredReason`. A read-only recompute of the session data with the new engine and these profiles gives 6 questions again.

**Checked live on 2026-10-18, run 2 (`ms-56907a90d11f`, after plan 1303-10 was deployed):**
- 13 → 6 questions; the owner answered in DeGram, including one undo;
- applied at 13:35:24Z, 502 elements;
- placement «placed 5 OBJECT STATE, 11 PROPERTY STATE (+RULE BY ID), 13 parameters, DESIGN STATE, VALIDATOR»; the OBJECT STATE streams equal the V1 gold set (376);
- VALIDATOR (auto) reported all 11 rules PASS on V1. From that we infer that METAGRAPH delivered the rules after sign-in and every `R <Rule_Id>` resolved; the R components' own messages were not read.

Details in `test/v12-hexagonal-facade-01/mapping-demo/PROTOCOL.md` and `1303-UAT.md`.

**Not yet checked live:** variants V2/V3 (UAT test 11).

## Observations not fixed

- «B Panel Ratio» (a Number parameter in the old «VALIDATION VALUES» group) is listed on stream Panels A: this is the LLM's stream; the output's values match AR but in another branch order (agreement 0.136 on Panels B). The rule bindings still take AR on Panels B for GlassPanel, so placement is not affected. It adds a weak «расчётный выход» vote for GlassPanel on Panels A.
