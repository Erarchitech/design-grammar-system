# Research: Phase 6 - End-to-End Hardening and Verification

## Goal

Close integration gaps and establish objective release readiness for v2.0.

## Findings

- E2E checks must include both state-present and state-absent flows.
- Error handling quality should be verified at plugin and viewer surfaces.
- Requirement closure evidence should be mapped directly to INTG-01..03.

## Suggested Verification Matrix

- Capture and serialize state
- Persist run with state
- Retrieve by rule and by state
- Reinstate selected state
- Validate legacy run without state
- Validate expected error messages for malformed/missing state

## Risks

- Cross-component contract drift can pass unit tests but fail E2E.
- Missing evidence mapping delays milestone audit closure.
