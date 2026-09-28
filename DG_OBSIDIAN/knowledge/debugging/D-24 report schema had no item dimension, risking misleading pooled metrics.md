---
tags: [debugging, schema, v12.0, phase-1204]
date: 2026-09-28
---

# D-24 report schema had no item dimension, risking misleading pooled metrics

**Symptom:** Schema validation of the live LLM-repeatability report (`llm-repeatability-report.json` against `report_schema_llm.json`) initially failed with a field-name mismatch (`providerStrata` required, `strata` supplied). After fixing the field name, the schema's `providerStrata` shape allowed only ONE stratum object per provider — no way to represent per-item breakdown, even though the actual sampling covered 5 different rule-ingest prompts against one provider.

**Root cause:** `report_schema_llm.json` (shipped by an earlier plan, 1204-07) was authored against a single-item mental model, even though the module that actually produces the metrics (`repeat_sweep.compute_item_metrics`/`run_repeat_sweep`) is explicitly multi-item-shaped (`{item_id: {..., strata: {provider: {...}}}}`). This was invisible in 1204-07's own tests because they only ever exercised crafted single-item metrics dicts — nothing forced a real multi-item validation end-to-end until the live capture actually sampled 5 different prompts.

**Why pooling would have been actively misleading, not just non-conformant:** the schema's `providerStrata` cell computes one "modal agreement" figure per provider by finding the single most common raw output across all samples in that cell. If forced to pool 5 different rule-ingest prompts' 50 samples into one cell, the "modal output" would be whichever single Cypher statement happened to repeat most across five *different questions* — near-1/50, reading as near-total instability, regardless of how stable any individual prompt's own 10 samples actually were. A technically schema-valid but substantively false headline number.

**Fix:** Minimal additive schema change — added a required `item` field to each `providerStrata` array entry, so the array now genuinely holds one row per `(provider, item)` pair (a single-item run still validates fine; it just has one entry). Verified the fix doesn't break the shipping plan's own tests (`test_llm_report_schema_has_no_shared_or_accuracy_fields`, full 14-test `test_repeat_sweep.py` suite).

**Lesson:** A report schema authored against synthetic single-case test fixtures can silently omit a dimension the real data generator always produces. When a schema and its producer disagree on shape, trust the producer's actual multi-instance behavior over the schema's narrower assumption — and never force data into a schema's shape by pooling/aggregating away a dimension that changes what the resulting number actually means.

**Related:** [[knowledge/decisions/1204-09 scoped to rule-ingest only, recognition prompt construction deferred]]
