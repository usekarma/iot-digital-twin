# Agent Business Solution Template v2

Turn an ambiguous business problem into a verified software solution using AI coding agents and human engineering judgment.

Inspired by business-facing engineering principles: clarify outcomes, prototype with stakeholders, anticipate edge cases, and own secure, operable delivery.

## Start here

1. Click **Use this template** on GitHub and create your project.
2. Fill in `PROJECT_BRIEF.md`: user, current process, measurable benefit, constraints, and assumptions.
3. Replace the worked example in `specs/work-request.md` and `specs/acceptance.json` with your behavior contract and test mappings.
4. Ask **Architect** to challenge assumptions and propose the smallest useful experiment.
5. Ask **Builder** for one vertical slice. Demo it to the stakeholder; record learning in `docs/prototype-review.md`.
6. Ask **Verifier**, **Reviewer**, **Security**, and **Operations** to evaluate the evidence in separate review passes.
7. Harden the validated idea using `docs/prototype-to-production.md`. Complete `docs/readiness.json` before claiming production readiness.

AI accelerates research, implementation, and review. Passing deterministic checks and observed behavior establish evidence; an agent's confidence does not.

## Setup and commands

Python 3.12, Git, and network access for bootstrap and vulnerability audit are required.

```bash
./scripts/bootstrap.sh
./scripts/check.sh
.venv/bin/python scripts/gates.py --production
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-dev.lock
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python scripts/check.py
.venv\Scripts\python scripts/gates.py --production
```

| Command | Evidence / gate |
| --- | --- |
| `make check` | Spec traceability, secret scan, format, lint, types, tests, coverage, Bandit, dependency audit |
| `make test` | Behavioral regression tests |
| `make production` | All checks plus owner, security, SLO, rollback, recovery, and stakeholder evidence |
| `make lock` | Deliberate dependency refresh; review and rerun gates |

CI runs the same `scripts/check.py` command on pushes and pull requests. Versions and dependency hashes are locked; GitHub Actions are pinned to immutable commits. The vulnerability advisory database is live and can change results or be unavailable: the audit fails closed. CI records reports in `artifacts/`.

**The template passes engineering checks but intentionally fails production readiness.** Replace the sample business logic and supply real evidence; do not mark the starter production-ready.

## Repository guide

- `AGENTS.md`: authority, workflow, and evidence requirements.
- `specs/`: human-readable contract and machine-readable acceptance/test traceability.
- `.github/agents/`: Architect, Builder, Verifier, Reviewer, Security, Operations.
- `.github/workflows/quality.yml`: repeatable checks; no deployment credentials.
- `docs/`: architecture, threat model, prototype feedback, verification, readiness, and recovery.
- `scripts/`: cross-platform checks and fail-closed readiness validation.
- `src/`, `tests/`: small pure-Python example and gate regression tests.

## Prototype to production

Discovery → experiment → stakeholder feedback → spec revision → hardening → verification → release decision. See `docs/prototype-to-production.md` for exit criteria and `docs/verification.md` for evidence requirements.

Prototype shortcuts must be recorded with owner, risk, and expiry. Use synthetic data. External side effects require bounded retries, timeouts, idempotency, and recovery tests where relevant. A human owns the business outcome and release decision.

## GitHub setup for projects created from this template

Keep `main` as default. Configure a branch ruleset requiring the **Quality gates** status check and review; workflow files alone do not enforce branch protection. Add a protected deployment environment with a human release approver when you introduce deployment. Never give untrusted pull requests production secrets. This template does not provision infrastructure or automatically deploy.

## Dependency maintenance

Edit `requirements-dev.in`, then run `make lock` in the development environment. Commit the generated hash lock with the change. Application runtime dependencies must also be added to `requirements-runtime.in`, reflected in `pyproject.toml`, locked, and audited. An empty runtime file is correct for this standard-library-only example.

## Upgrade notes

v2 adds executable specs, immutable tool inputs, evidence-oriented agents, CI, security gates, production readiness, and feedback-driven promotion. Existing domain code stays small. Hooks remain opt-in; see `.github/hooks/README.md`.
