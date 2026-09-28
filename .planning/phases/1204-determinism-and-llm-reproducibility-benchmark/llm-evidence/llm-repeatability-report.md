# LLM Repeatability Report

**Label:** scoring-pipeline determinism
**Subject:** rule_ingest
**Samples per item:** 10 (min-sample floor: 5)
**Generated:** 2026-09-28T00:00:00Z

> This report measures **scoring-pipeline determinism** (byte-identical
> regeneration from committed cassettes) and **sample-to-sample output
> stability** for a live model. It is NOT a claim of universal LLM
> determinism, NOT model correctness, and NOT pooled across providers
> or across items (D-13/D-24). Temperature 0 is not determinism;
> cassette replay is not model repeatability. See Limitations below.

## Per-(provider, item) strata

| Provider | Item | n | Level-1 distinct | Level-2 distinct | Modal agreement | Wilson 95% CI |
|---|---|---|---|---|---|---|
| openai | cq3_attribute_of | 10 | 9 | 9 | 0.200 | [0.05668094798069328, 0.5098431532792767] |
| openai | fixture_rules_v7_1_maximum_height_of_buildings_is_75_meters | 10 | 5 | 5 | 0.600 | [0.3126695474501863, 0.8318224187964901] |
| openai | fixture_rules_v7_2_minimum_area_of_living_units_is_28_squar | 10 | 8 | 8 | 0.200 | [0.05668094798069328, 0.5098431532792767] |
| openai | fixture_rules_v7_3_all_residential_buildings_must_be_at_lea | 10 | 9 | 9 | 0.200 | [0.05668094798069328, 0.5098431532792767] |
| openai | height_rule | 10 | 10 | 10 | 0.100 | [0.01787574951572113, 0.4041563854975721] |

## Outcome tallies per item

- **cq3_attribute_of** (openai): {'valid': 8, 'truncated': 2}
- **fixture_rules_v7_1_maximum_height_of_buildings_is_75_meters** (openai): {'valid': 9, 'truncated': 1}
- **fixture_rules_v7_2_minimum_area_of_living_units_is_28_squar** (openai): {'valid': 10}
- **fixture_rules_v7_3_all_residential_buildings_must_be_at_lea** (openai): {'truncated': 4, 'valid': 6}
- **height_rule** (openai): {'truncated': 3, 'valid': 7}

## D-22 reproducibility class

`not-reproducible-provider-managed` — cloud model id is an alias, no seed control, temperature is provider-default (not sent). A bitwise re-execution claim is available only in the `replayable` class (committed cassettes; this report's own D-21 replay-byte-identity check demonstrates that class, for the *scoring pipeline*, not the model).

## Limitations

- No claim of determinism holds universally across live LLM or canvas state.
- Temperature is provider-default (not sent) for rule-ingest — this is not the same as temperature 0, and neither would guarantee determinism.
- Cassette replay demonstrates scoring-pipeline determinism, never model repeatability.
- This report is never pooled with the 1204-08 deterministic-half report (D-24) — separate files, separate schemas, no shared score field.
- No live structural validity oracle was wired for this benchmark's outcome classification (D-18 oracle-free scope); outcome tallies reflect provider-level signals (truncation/refusal/provider_error) only, not Cypher correctness.
- Only one provider (openai-compatible, via a custom router) was reachable this run; Anthropic and local Ollama were out of scope for this capture (owner decision).
