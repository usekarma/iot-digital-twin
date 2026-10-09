# Decision Log

Record decisions that future engineers or agents should not have to rediscover.

## ADR-001: Use a single-device, low-rate telemetry prototype

**Status:** accepted

**Context:**

The project must demonstrate a real physical M5Stack Core2 for AWS connected to a digital-twin representation without spending on infrastructure that is not required to answer the first decision: is the path credible enough to continue?

**Decision:**

The prototype will use exactly one device, one asset model, and one low-rate telemetry path. The recommended first slice is MQTT/TLS to AWS IoT Core with a minimal validation stage and a TwinMaker-visible asset state. SiteWise is deferred unless a later requirement clearly calls for historical property modeling.

**Alternatives considered:**

- Keep the full `IoT Core -> SiteWise -> TwinMaker` path from day one.
- Add edge orchestration, telemetry streaming, or full scene automation before the live experiment.
- Build a fleet-scale architecture without proof that the single-device path works.

**Consequences:**

This keeps the experiment small, lower-cost, easier to review, and faster to validate from a real device. The tradeoff is that it does not yet provide rich retrospective analytics or a production industrial model.

## ADR-002: Defer SiteWise unless the TwinMaker proof requires it

**Status:** accepted

**Context:**

The proposal assumes SiteWise is the preferred data source for TwinMaker. For the first proof, that assumption is not yet justified by the business need or the single-device scale.

**Decision:**

The architecture does not require SiteWise for the initial demonstration. If a later requirement demonstrates the need for historical time-series or asset-property semantics, SiteWise can be added as a second step without changing the core device-to-cloud path.

**Alternatives considered:**

- Add SiteWise immediately to satisfy the architecture hypothesis.
- Skip TwinMaker and only validate AWS IoT Core telemetry ingestion.
- Use a custom Lambda/DynamoDB-only path without any TwinMaker representation.

**Consequences:**

This preserves the smallest credible end-to-end slice while leaving a clean upgrade path to a richer industrial setup. The tradeoff is that the first demo will not yet exercise the full SiteWise workflow.

## ADR-003: Evidence-driven AI workflow

Status: accepted for template v2.

Use AI for ambiguity reduction, experiments, implementation, and review. Require executable behavior contracts and deterministic engineering gates. Keep production promotion separate and fail closed until a real project supplies owned evidence. Keep external advisory audits live; record their temporal and network limitations.
