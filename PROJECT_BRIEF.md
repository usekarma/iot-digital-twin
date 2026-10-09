# Project Brief

## Business problem

Describe the real business problem in plain language.

> Example: Operations staff manually reconcile failed transactions across two systems. The process takes 2-4 hours per day and failures are difficult to trace.

## Desired outcome

Describe what should be measurably better when the project succeeds.

## Users / stakeholders

- Primary user:
- Business owner:
- Technical owner:
- Downstream consumers:

## Current process

Describe what happens today, including manual steps and failure handling.

## Constraints

- Security/compliance:
- Cost:
- Latency/SLA:
- Data volume:
- Deployment environment:
- Existing systems that cannot change:

## Inputs

List important events, APIs, files, messages, database records, or user input.

## Outputs

List observable business outputs, state changes, reports, events, or API responses.

## Failure expectations

What must happen when dependencies fail, requests are duplicated, or processing partially succeeds?

## Out of scope

Explicitly list what this project will not solve.

## Success metrics

Define measurable success, for example:

- manual effort reduced from X to Y
- 99% of requests complete within N seconds
- reconciliation mismatch rate below X%
- zero duplicate side effects under retry

## Discovery and experiment

- Hypothesis and smallest stakeholder demo:
- Current baseline and measurable target:
- Assumptions with validation owner and deadline:
- Prototype decision: iterate / stop / harden:
- Data classification and permitted synthetic fixtures:
- Production owner and release decision maker:

Use `specs/` for detailed contracts and `docs/prototype-review.md` for observed feedback.
