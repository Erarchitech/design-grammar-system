# Deferred Items - Phase 29

Items discovered during execution that are out of scope for the current task
(pre-existing failures/warnings unrelated to the files this plan touches).

## Plan 29-01

- **`tests/test_error_responses.py::test_publish_validation_missing_config`** --
  fails against the rebuilt `data-service` container (`assert 200 == 404`, expects
  a 404 when Speckle publish config is missing but gets 200). Unrelated to
  `dg_context.py` / `llm/cypher_catalog.json` (this plan's only files) --
  concerns `/validation/publish` Speckle config handling. Likely caused by env
  vars (`SPECKLE_WRITE_TOKEN`, `SPECKLE_PROJECT_ID`, etc.) being populated in
  this local `docker-compose.yml` environment where the test expects them
  unset. Not fixed here per the executor's scope boundary (out-of-scope for
  a Cypher-catalog-loader task). Flag for a future phase/plan that touches
  `speckle_validation.py` or the `/validation/publish` route.
  status: acknowledged
