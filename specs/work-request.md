# Work request contract (worked example)

Status: example, not a production business spec.
Owner: template maintainer. Stakeholder: engineer checking the starter.

## Outcome

Demonstrate a pure domain boundary whose accepted input produces twice its value without external side effects. The measurable template outcome is repeatable checks and rejected invalid inputs.

## Contract

`WorkRequest(request_id: str, value: int)` accepts a nonblank string identifier of at most 128 characters and an integer from 0 through 1,000,000. Boolean values are rejected even though Python treats bool as an int. Invalid types raise TypeError; invalid bounds raise ValueError. `calculate_result` returns exactly `value * 2` and does not mutate input or perform I/O.

## Acceptance IDs

- AC-001: accepted input returns the exact doubled value, including boundary values.
- AC-002: blank or oversized identifiers are rejected.
- AC-003: negative or oversized values are rejected.
- AC-004: invalid types, including boolean values, are rejected.
- AC-005: repeated computation is deterministic and leaves input unchanged.

Map each ID to executable pytest node IDs in `acceptance.json`. Passing mappings prove test execution, not that assertions are sufficient; review remains required.

## Failure and security boundaries

No network, persistence, authentication, retries, or distributed side effects exist in this example. Do not infer distributed idempotency from deterministic pure computation. Add explicit contracts and integration tests when those boundaries are introduced.

## Non-goals

A production application, API, deployment, or business-specific ROI claim.
