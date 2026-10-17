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

## ADR-004: Align sandbox ownership with the sibling repositories

**Status:** proposed for review; no deployment authorization.

**Context:**

The documentation omitted Lambda runtime ownership, assumed a production environment binding, and conflated local configuration preparation with AWS mutation. The existing sandbox desired state uses `iac/dev/iot-digital-twin/core2-aws-001/config.json`.

**Decision:**

- `aws-lambda` owns Lambda application code, testing, and packaging.
- `aws-config` owns non-secret desired-state configuration and environment bindings.
- `aws-iac` owns Terraform/Terragrunt resources, IAM, and integration wiring.
- `iot-digital-twin` owns the product contract, trust boundaries, and behavioral acceptance evidence.

Use the existing `dev` desired-state path. The deployment binding remains unresolved pending human confirmation. Creating or editing non-secret configuration locally does not require deployment approval; publishing it to SSM or modifying AWS resources requires explicit human approval for the concrete operation and target.

**Consequences:**

Local documentation and configuration preparation remain reviewable without authorizing cloud mutation. Runtime packaging and infrastructure wiring have explicit owners. This decision adds no live device/AWS evidence and changes no telemetry acceptance criteria.

## ADR-005: Begin the interview milestone with a bounded offline simulator

**Status:** prototype proposal for review.

**Context:** Issue #17 needs a reliable one-minute narrative before cloud and hardware
integration. The Core2 contract remains a separate experiment.

**Decision:** Use standard-library Python with a fixed-seed five-asset directed ring,
monotonic severity and simultaneous pre-tick neighbor propagation. Restore the seeded
interview baseline on reset, advance epoch and reset per-asset counters. A separate
in-memory consumer enforces per-asset replay and epoch rejection. Retain only the last
reset receipt; older duplicates fail closed rather than requiring unbounded history.
Use additive AC-201–AC-205 mappings to the issue's INT criteria, preserving the existing
AC-only traceability gate. No new dependencies, cloud services or security gate changes.

**Consequences:** The terminal progression can be rehearsed offline. Ring hazards are
a fictional teaching model and saturate at CRITICAL; this is not a validated grid
model. Idempotency and epochs are process-local; durable multi-producer state, cloud
authorization and device application ACK need separately reviewed contracts.

### ADR-005 clarification: sequence equals tick for this producer

PR #19 review identified that the consumer admitted independently advancing sequences
and ticks even though the producer emits exactly one observation per asset per tick.
Enforce `sequence == tick` within the active epoch at the consumer boundary, rejecting
mismatches without mutation. Retain per-asset ordering and permit skipped observations;
asset interleaving does not require independent sequence and tick counters. Multiple
observations per tick would require a future explicit contract revision. This narrows
the consumer to the current offline model without changing generated observations.
