# Context: Phase 3 - Validation Runs Retrieval Component

## Locked Decisions

- VALIDATION RUNS supports optional Rule and optional State filters.
- Component outputs must include Runs, Results, States.
- Output schema must remain deterministic for downstream consumers.

## Inputs

- .planning/milestones/v2.0-REQUIREMENTS.md
- .planning/phases/02-classificator-state-input-and-run-persistence/02-01-PLAN.md
- .planning/phases/03-validation-runs-retrieval-component/03-01-PLAN.md

## Downstream Consumers

- Phase 4 REINSTATE input
- Phase 5 grouped Model Viewer strip
- Phase 6 E2E coverage

## Open Questions

- Default sort order for runs when no filter is provided.
- Pagination behavior for large run history.
