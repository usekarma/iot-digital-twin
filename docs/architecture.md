# Architecture

The starter has a pure `WorkRequest` domain boundary and `calculate_result` service, with no external I/O. Bounded input and immutable request state make the example easy to reason about.

Repository quality infrastructure is separate: specifications map acceptance IDs to pytest node IDs; a gate validates that mapping and performs a narrow secret scan; the check runner invokes formatting, lint, types, behavioral tests, security checks, and vulnerability audit. Production readiness checks evidence documents separately.

For your project, document neighboring systems, component responsibilities, data flow, state ownership, trust boundaries, timeout budgets, retry/idempotency semantics, partial failure recovery, resource limits, observability, cost, and deployment/rollback constraints. Start with the simplest deployable boundary and justify distribution.
