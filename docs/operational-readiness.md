# Operational readiness

`docs/readiness.json` is deliberately pending. For each check, supply `status: "passed"`, a named owner, and a repository-relative Markdown evidence path. Each evidence document must contain `## Evidence` and `## Limitations` with substantive content. Do not use the template examples as proof.

- Stakeholder validation: observed business benefit and actual stakeholder decision.
- Security review: assets, boundaries, findings, mitigations, and accepted residual risk.
- SLO and alerts: workload, availability/latency/error objectives, thresholds, routing, and escalation owner.
- Rollback drill: version/config/schema compatibility, observed rollback, and triggers.
- Recovery drill: restore/replay evidence, duplicate handling, RPO/RTO, and partial failure repair.
- Capacity and cost: measured workload, limits, backpressure, and spend guardrails.
- Release approval: source commit, evidence reviewed, approver, rollout observation, and decision.

For inapplicable concerns, record an explicit rationale and have it reviewed. The gate checks document structure; a human checks truth and adequacy. Production deployment is not authorized by a passing JSON file.
