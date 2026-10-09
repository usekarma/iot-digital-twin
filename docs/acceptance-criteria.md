# Acceptance and quality criteria

Business acceptance lives in `specs/*.md` and `specs/acceptance.json`. The included five IDs are worked examples; replace them with real project behavior. The gate requires unique IDs, existing specs containing each ID, and collected tests for every mapping. Pytest must then pass.

Engineering gates: format, lint, strict types, behavior tests, minimum 90% branch coverage of application code, secret scan, Bandit, and live dependency audit. The secret scanner detects selected credential patterns; it is not a complete data-loss prevention system.

Production acceptance is separate: `docs/readiness.json` must reference substantive repository evidence and named owners. Human review must establish that the evidence is true, current, and sufficient. Automated checks cannot certify a release.
