# Runbook

## Template example

This repository has no running service. Reproduce its behavior with `make check`. No cloud resources, persistence, on-call rotation, deployment, or rollback are configured.

## Before deploying a real project

Supply service purpose, business owner, technical owner, on-call contact, dependency map, dashboards, and source/deployment identifiers.

Define health checks that test readiness, workload and SLO signals, latency/error/backlog thresholds, alert routing, diagnosis commands, and escalation paths. Document restart behavior and in-flight work.

Provide tested procedures for dependency outage, retry exhaustion, duplicate work, partial writes, overload, authentication failure, and data repair where relevant. State safe preconditions and destructive steps requiring authorization.

Document rollback compatibility, trigger, procedure, validation, and observation window. Record restore/replay evidence, RPO/RTO, retention, and cost limits. Keep secrets and customer data out of runbook examples.
