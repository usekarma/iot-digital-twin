# Digital twin telemetry contract

Status: architecture proposal for the first M5Stack Core2 AWS prototype. Not production-deployed.
Owner: technical owner. Stakeholder: engineering lead evaluating remote equipment condition.

## Outcome

Demonstrate that a real M5Stack Core2 for AWS can publish authenticated IMU telemetry to AWS IoT Core and that the latest asset condition is visible through a minimal digital-twin representation in a way that is measurable and reviewable.

## Contract

The device publishes a JSON telemetry payload on an authenticated MQTT topic. The payload must satisfy the following contract before any cloud-side state update occurs:

```json
{
  "device_id": "core2-aws-001",
  "timestamp": "2026-10-08T19:45:00Z",
  "accel_x": 0.03,
  "accel_y": -0.02,
  "accel_z": 1.01,
  "gyro_x": 0.4,
  "gyro_y": 0.1,
  "gyro_z": -0.2,
  "operating_state": "NORMAL",
  "sequence": 42
}
```

Rules:

- `device_id` is telemetry data only. The authoritative identity is the authenticated certificate principal, AWS IoT Thing identity, or a trusted registry mapping. A mismatch between the payload `device_id` and the authenticated identity is rejected before state mutation.
- `timestamp` must be RFC3339 UTC and within a bounded clock-skew window (target ±10s) at the point of validation.
- `accel_*` and `gyro_*` values must be finite numbers and within sensor-safe ranges for the M5Stack Core2 AWS IMU.
- `operating_state` must be one of `NORMAL`, `WARN`, or `ALERT` and is derived by deterministic motion logic. `OFFLINE` is not a device-authored state; it is server-derived from heartbeat timeout or missing telemetry and must not be self-reported.
- `sequence` must be strictly increasing for a given device, or the message is considered duplicate/replay and is rejected or ignored.
- `connectivity_state` is server-derived and is not accepted from a device telemetry payload.

The prototype does not permit arbitrary free-form telemetry; malformed event shapes are rejected before any state is written.

## Acceptance IDs

- AC-101: the physical device publishes a valid telemetry payload over authenticated TLS to AWS IoT Core.
- AC-102: malformed or out-of-range data is rejected before it mutates digital-twin state.
- AC-103: valid telemetry appears in the TwinMaker-visible asset state within 10 seconds under normal development conditions.
- AC-104: a physical motion event changes the derived operating condition and the TwinMaker-visible value.
- AC-105: no device credentials, private keys, or AWS secrets are stored in the repository.

## Failure and security boundaries

- Device auth and cloud auth remain separate trust boundaries enforced by certs and IoT policies.
- Malformed or unauthorized payloads do not mutate state.
- Replayed or duplicate telemetry is blocked by sequence/timestamp validation and never treated as independent state transitions.
- Offline network conditions do not overwrite the last known good state.
- Permission expansion is prohibited without a reviewed, explicit change to policy scope.

## Non-goals

- multi-device fleet management
- long-term predictive monitoring
- a production-ready 3D scene or full industrial asset model
- automated remediation or broad rollout
- reliance on SiteWise for the first proof unless a later requirement justifies it
