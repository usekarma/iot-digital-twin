# Prototype to production

| Stage | Work | Exit evidence |
| --- | --- | --- |
| Discover | Observe current process; define user, baseline, target, constraints | Brief and assumption log |
| Specify | Define contracts, invariants, failure expectations, test IDs | Reviewed spec and acceptance mapping |
| Prototype | Build smallest experiment with synthetic data | Demo and feedback in prototype review |
| Validate | Compare observed behavior to user need and baseline | Stakeholder decision: iterate, stop, or harden |
| Harden | Remove shortcuts; test boundaries, security, recovery, scale | Checks, threat model, load/recovery evidence |
| Verify | Reproduce result; independently review changed behavior | Verification record tied to commit |
| Release | Review readiness and rollout/rollback plan | Named human release decision |
| Operate | Monitor outcome, SLO, cost, and incidents | Owned runbook and feedback into specs |

Shortcuts require an owner, reason, risk, removal trigger, and expiry. Do not carry fake auth, in-memory durability assumptions, unbounded concurrency, or mocked dependency success into production unnoticed.

Before promotion, document timeout budgets, retry limits, idempotency keys, partial failure semantics, data retention, least privilege, alert ownership, restore/replay, rollback compatibility, and expected workload where applicable. If a concern is inapplicable, explain why in evidence instead of silently omitting it.

Release decisions must identify the source commit, checks, open risks, approver, rollout observation window, and rollback trigger. No automatic deployment is included.
