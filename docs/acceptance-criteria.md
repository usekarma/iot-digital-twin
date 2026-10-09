# Acceptance and quality criteria

This project is a prototype for validating a physical M5Stack Core2 for AWS asset and its cloud digital-twin state. The acceptance criteria below focus on the security, data validity, and observability required to justify continuing beyond the first experiment.

## Project acceptance IDs

- AC-101: The physical device publishes a valid IMU telemetry event over authenticated MQTT/TLS to AWS IoT Core.
- AC-102: Malformed or out-of-range telemetry is rejected before it mutates the digital-twin state.
- AC-103: A valid update reaches the TwinMaker-visible asset state within 10 seconds under normal development conditions.
- AC-104: A physical motion event changes the derived operating condition and the TwinMaker-visible condition value.
- AC-105: No device credentials, private keys, or AWS secrets are present in the repository or Git history.

## Objective evidence for each criterion

- AC-101 is supported by a device-side test contract and a review of the certificate-policy path.
- AC-102 is validated by strict schema and range checks in the telemetry contract tests.
- AC-103 is validated by measuring the latency between message publish and cloud-visible state update in a controlled demo.
- AC-104 requires a real device movement exercise with a captured before/after value in the TwinMaker state.
- AC-105 is enforced by the repository secret scan and a human review of the Git history for credentials.

## Engineering gate expectations

This project follows the repository engineering gates: format, lint, strict types, behavior tests, and secret scanning. Production readiness is intentionally separate and cannot be claimed from this architecture pass alone.

## Non-goals for this prototype

- Fleet-scale analytics and management
- Advanced predictive maintenance
- A production-ready industrial scene
- Automatic remediation or broad operational rollout

These items remain future work after the first end-to-end proof is demonstrated to a stakeholder.
