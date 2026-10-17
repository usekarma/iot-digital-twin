# Acceptance and quality criteria

This project is a prototype for validating a physical M5Stack Core2 for AWS asset and its cloud digital-twin state. The acceptance criteria below focus on the security, data validity, and observability required to justify continuing beyond the first experiment.

## Project acceptance IDs

- AC-101: The physical device publishes a valid IMU telemetry event over authenticated MQTT/TLS to AWS IoT Core.
- AC-102: Malformed or out-of-range telemetry is rejected before it mutates the digital-twin state.
- AC-103: A valid update reaches the TwinMaker-visible asset state within 10 seconds under normal development conditions.
- AC-104: A physical motion event changes the derived operating condition and the TwinMaker-visible condition value.
- AC-105: No device credentials, private keys, or AWS secrets are present in the repository or Git history.

## Objective evidence for each criterion

- AC-101 is supported only by a reviewed device-side certificate policy and a real device/AWS observation; local contract tests do not count as live evidence.
- AC-102 is validated by strict schema and range checks in the telemetry contract tests.
- AC-103 is validated only by measuring the latency between message publish and cloud-visible state update in a controlled live demo; a documented latency requirement is not sufficient proof.
- AC-104 requires a real device movement exercise with a captured before/after value in the TwinMaker state; local motion-state derivation is not cloud evidence.
- AC-105 is enforced by the repository secret scan and a human review of the Git history for credentials.

## Engineering gate expectations

This project follows the repository engineering gates: format, lint, strict types, behavior tests, and secret scanning. Production readiness is intentionally separate and cannot be claimed from this architecture pass alone.

## Non-goals for this prototype

- Fleet-scale analytics and management
- Advanced predictive maintenance
- A production-ready industrial scene
- Automatic remediation or broad operational rollout

These items remain future work after the first end-to-end proof is demonstrated to a stakeholder.

## Offline interview simulator — separate local criteria

See `specs/interview-simulator.md` for contracts and `specs/acceptance.json` for tests.

- AC-201 (INT-01): repeatable seeded history and replay after reset.
- AC-202 (INT-02): persistent accumulating faults and reproducible neighbor effects.
- AC-203 (local part of INT-03): idempotent reset to baseline, epoch isolation, bounded state.
- AC-204 (foundation for INT-09): per-asset sequence tracking and invalid-state rejection.
- AC-205: finite offline terminal rehearsal with explicit synthetic/local labels.

These criteria do not close Issue #17 or replace AC-101–AC-105. Cloud-authorized reset,
physical application ACK, dashboard, debugging exercise and measured rehearsal remain future work.

## Synthetic transition trace experiment

AC-206–AC-208 cover recorded arithmetic/predecessor agreement, deterministic execution
including reset and exhaustion, and accurate opt-in explanations without changing
ordinary observations. See `specs/karma-transition-trace.md` and its additive mappings.
These criteria establish synthetic rule execution only, not real-world inference.
