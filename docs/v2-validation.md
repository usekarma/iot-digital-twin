# v2 template validation

## Evidence

Validated on Python 3.12.14 with dependencies installed from the hash lock. `./scripts/check.sh` exited 0: spec traceability and credential patterns passed; Ruff format/lint passed; strict mypy passed for six source files; 22 pytest cases passed; application branch coverage was 100% against a 90% gate; Bandit had no findings; pip-audit reported no known vulnerabilities in the locked dependencies. The live audit was performed on October 7, 2026 UTC.

The production command exited 1 with `Production blocked: stage is not production`, confirming the deliberate default block. Regression tests cover missing test mappings, duplicate IDs, path escape, credential detection without value disclosure, missing owners, placeholder evidence, and prototype promotion. GitHub Action commit pins were checked against official repository tags.

## Limitations

These results validate the starter and its gates, not a deployed business service. No stakeholder business validation, load test, rollback drill, recovery drill, or production release approval has occurred. Security pattern matching and static analysis are incomplete by design. The vulnerability database can change. Evidence documents require human review; the readiness validator only enforces structure. GitHub branch rulesets are a separate project configuration.
