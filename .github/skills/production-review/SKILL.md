---
name: production-review
description: Verify security, failure behavior, and operational evidence before promotion.
---

Read `AGENTS.md`, specs, threat model, runbook, and readiness evidence. Review timeout/retry bounds, duplicate effects, partial writes, concurrency, resource limits, permissions, sensitive logs, rollback, restore/replay, SLOs, owners, and cost. Require executable checks for material risks. Run quality and production gates. Report gaps and exact evidence; a green gate is not human release approval.
