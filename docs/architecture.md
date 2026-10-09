# Architecture

## Decision summary

The current architecture hypothesis is valid as an end-state for a richer industrial digital-twin program, but it is not the smallest credible path for the first proof-of-value experiment.

The project should challenge the direct `IoT Core -> SiteWise -> TwinMaker` path before cloud resources are added. SiteWise is useful as an asset/time-series model for historical analytics, but for a single-device prototype it adds modeling overhead, IAM complexity, and recurring costs before the core question has been answered: can a real M5Stack Core2 for AWS publish authenticated telemetry that becomes visible as the state of a digital twin?

The proposed prototype should therefore optimize for the smallest end-to-end proof, not for a production-ready industrial stack. The recommended first slice is:

```text
M5Stack Core2 for AWS
        |
        | MQTT over TLS + X.509 device identity
        v
AWS IoT Core
        |
        | topic rule / validation
        v
AWS Lambda (validator and state normalizer)
        |
        | latest-state write
        v
TwinMaker entity property / simple asset state
```

SiteWise should be introduced only if the team decides that TwinMaker needs a supported SiteWise-backed asset property model or that historical time-series is essential for the stakeholder demo. Until that requirement is proven, the architecture should stay lean.

## Why the current proposal is too broad for phase 1

The architecture as written does not yet justify the extra layers:

- `SiteWise` adds asset-model creation, property mapping, and time-series semantics before the telemetry path itself is demonstrated.
- `TwinMaker` requires an explicit model, component binding, and scene representation; that is valuable later, but it is not the smallest path to proving real-device telemetry reaches cloud state.
- The current brief already constrains the project to one low-rate physical device and a prototype target of 10-second observability. Those constraints argue against fleet infrastructure, an always-on data lake, or a large industrial scene.
- The experiment is not trying to optimize for long-term analytics or alarm quality; it is trying to demonstrate secure telemetry ingestion and observable digital-twin state changes.

The architecture review therefore recommends a deliberate deferral of `SiteWise` and any 3D scene complexity until after a live demo proves real-condition updates.

## Smallest credible vertical slice

### Component responsibilities

- M5Stack Core2 for AWS: capture IMU values, apply local time stamping, and publish a low-rate telemetry event at a bounded cadence (target <= 1 message/sec).
- AWS IoT Core: device authentication, encrypted transport, topic authorization, and ingestion of validated MQTT messages.
- AWS Lambda: validate JSON, enforce schema and range checks, deduplicate stale/replayed messages, and normalize the event to a small asset condition state.
- DynamoDB or equivalent latest-state store: hold the latest observed conditions for the asset. This is the simplest reliable snapshot for the first demo and keeps the prototype small.
- TwinMaker: expose the asset as a single entity with a current-condition property (for example, `condition`, `motion_state`, or `imu_status`) for user-visible state.

### Out-of-scope for the first slice

- Greengrass or local edge orchestration
- Device Defender / compliance policy beyond least-privilege certificate and topic permissions
- Kinesis / Kafka / broad event streaming
- SiteWise historical modeling unless required by the demonstrated use case
- polished 3D scene or dashboard design
- predictive analytics, alert routing, or fleet management

### Why this slice is enough

This slice still covers the full business path being evaluated:

1. a real device emits telemetry;
2. AWS authenticates and ingests it;
3. cloud validation rejects malformed input;
4. the latest state is readable from a TwinMaker-backed asset representation;
5. a human can observe the physical state as a digital-twin condition.

It remains small, reviewable, and reversible, which is the right tradeoff for a prototype that has not yet proven the product value.

## Telemetry contract

The device contract should be documented as a strict JSON schema. The first prototype uses a single IMU payload at a low rate.

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

Required rules:

- `device_id`: non-empty string; must match the device certificate identity or a trusted device registry mapping.
- `timestamp`: RFC3339 UTC timestamp; `now` must be within a bounded skew window (for example ±10s) or the message is rejected.
- `accel_*` and `gyro_*`: finite floating-point numbers and must fit the sensor range for the M5Stack Core2 AWS IMU; the prototype rejects NaN and infinity values.
- `operating_state`: enum of `NORMAL`, `WARN`, `ALERT`, `OFFLINE` and must be derived by deterministic domain logic rather than accepted as arbitrary free-form text.
- `sequence`: strictly increasing per device; duplicates or replayed values are rejected or treated as idempotent updates based on the dedupe policy.

The payload size should be deliberately bounded (for example < 1 KB) to safeguard the prototype and reduce surprise cost.

## Trust and failure boundaries

### Trust boundaries

- Device identity boundary: certs and private keys remain in the device or secure provisioning store; no credentials in Git or repository artifacts.
- AWS IoT boundary: MQTT topic, policy, and certificate authorization define which device can publish to which topic.
- Cloud validation boundary: Lambda or equivalent service validates payload structure, ranges, and timestamps before state mutation.
- TwinMaker visibility boundary: only the accepted, normalized state should propagate to the digital-twin asset view.

### Failure boundaries

- Invalid payloads are rejected before any state mutation occurs.
- Duplicate or replayed messages are identified by `sequence` and timestamp and are not treated as independent state changes.
- Offline or network-failure scenarios do not mutate the last-known-good state; they should record a local retry count and the last successful state.
- Cloud-side processing errors should emit structured logs and metrics, and the system should keep the last known valid state rather than writing a partial or corrupt value.
- Failed authorization attempts are not retried by expanding permissions; the permission set remains least privilege and reviewable.

### Operational assumptions

- One physical device, one asset model, low-rate telemetry.
- Practical latency target: observable cloud state within 10 seconds under normal development conditions.
- No production-grade fleet or device-OTA lifecycle is required for this prototype.
- Cloud cost should stay within a small sandbox budget and be documented before any non-trial deployment.

## Architectural tradeoffs

### Why not keep SiteWise in the initial path?

Because the prototype is intentionally validating the data path, not historical time-series analytics. SiteWise introduces operational and modeling cost without increasing confidence that the device-to-cloud path is valid. The architecture should defer SiteWise until a stakeholder asks for historical state or source-of-truth asset semantics.

### Why not add a complex IoT edge stack?

Because the use case does not require device shadowing, fleet management, local orchestration, or edge analytics. Adding those layers would obscure the failure mode we need to test: does a real device send valid telemetry to the cloud and can TwinMaker reflect it?

### Why keep TwinMaker in scope?

Because the project's primary objective is to show the working digital-twin representation, not just publish telemetry to AWS. A single entity and a single condition property is enough to satisfy that business goal while keeping the rest of the stack minimal.

## Acceptance criteria mapped to this architecture

- AC-101: the physical M5Stack Core2 publishes a valid, signed MQTT payload over TLS to AWS IoT Core.
- AC-102: malformed or out-of-range telemetry is rejected before it mutates the asset state.
- AC-103: the cloud path updates the latest asset state and makes it observable in TwinMaker within 10 seconds under normal development conditions.
- AC-104: a physical motion event changes the derived operating condition and the TwinMaker-visible value.
- AC-105: no AWS keys, private certificates, or device credentials are committed to the repository.

## Open assumptions

- The exact Core2 firmware/toolchain is still to be confirmed by the technical owner.
- The asset model and TwinMaker property names need confirmation before production-style implementation.
- The exact device certificate policy and command topic are part of the reviewed sandbox deployment, not part of the repository.
- Historical analytics, alerting, and shared scenes remain explicit future work.

These assumptions should be closed before any AWS deployment activity is approved by a human reviewer.
