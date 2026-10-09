# Prototype review

Status: architecture review complete; prototype implementation not yet approved.

This document records the architectural review outcome and the design questions that still require a live device demonstration. It does not claim stakeholder approval for any AWS deployment or live cloud implementation.

## Hypothesis

If a real M5Stack Core2 for AWS can publish authenticated telemetry to AWS IoT Core and the resulting state is visible in a minimal TwinMaker asset view, then the architecture is credible enough to continue into a real prototype and future industrial monitoring work.

## Baseline and target

- Baseline: no physical-device-to-cloud digital-twin path exists.
- Target: a live device publishes valid telemetry; cloud state becomes visible within 10 seconds under normal development conditions.

## Architectural findings

- The proposed `IoT Core -> SiteWise -> TwinMaker` path is a valid long-term industrial architecture, but it is broader than needed for the initial proof.
- The smallest credible slice is `M5Stack -> IoT Core -> validation -> latest-state store -> TwinMaker` with SiteWise deferred unless a stakeholder requirement justifies it.
- A real device demo is required to validate the IMU contract, TLS identities, and state-change timing.

## Open questions

- Which exact firmware/toolchain will be used to read the Core2 IMU and publish MQTT telemetry?
- What exact `topic`, property names, and asset model should TwinMaker expose for the first demo?
- Is historical SiteWise analytics essential before the business owner will fund a second iteration?

## Decision

Decision: iterate on the minimal TwinMaker-backed prototype first; add SiteWise only when the stakeholder identifies a need for historical time-series or asset-model semantics.

## Evidence requirement before implementation proceeds

A human must review the actual device certificate policy, the telemetry contract, and the proof-of-life device output before any AWS deployment is approved.
