# IoT Digital Twin

An AI-first AWS IoT digital-twin prototype built around a physical **M5Stack Core2 for AWS** device.

The project is designed to prove a narrow end-to-end idea:

```text
Physical M5Stack Core2
        |
        | IMU telemetry over MQTT/TLS
        v
AWS IoT Core
        |
        | validation / normalization
        v
AWS application boundary
        |
        v
AWS IoT TwinMaker
        |
        v
Human-visible digital-twin state
```

The immediate goal is not to build a production IoT platform. It is to demonstrate that movement of a real physical device can securely produce telemetry, pass deterministic validation, and become observable as digital-twin state.

## Project status

The repository is currently in the prototype-validation stage.

```text
Project brief         complete
Architecture          complete
Domain implementation complete
Local verification    complete / being refined
Security review       pending
Operations review     pending
AWS sandbox deploy    not yet approved
Physical device demo  not yet completed
Production readiness  no
```

No live AWS deployment or production-readiness claim should be inferred from passing repository tests.

## Acceptance criteria

The project tracks five primary acceptance criteria:

| ID | Requirement | Current status |
| --- | --- | --- |
| AC-101 | Physical Core2 publishes authenticated MQTT/TLS telemetry to AWS IoT Core | Pending live device/AWS evidence |
| AC-102 | Invalid, stale, or replayed telemetry cannot mutate digital-twin state | Locally testable |
| AC-103 | Valid telemetry becomes TwinMaker-visible within 10 seconds | Pending live AWS evidence |
| AC-104 | Physical motion causes an observable digital-twin condition change | Local logic implemented; live demo pending |
| AC-105 | No device credentials, certificates, or AWS secrets are committed | Repository controls in place |

See `specs/work-request.md`, `specs/acceptance.json`, and `docs/verification.md` for the detailed evidence contract.

## Architecture

The original hypothesis was:

```text
IoT Core -> IoT SiteWise -> TwinMaker
```

The Architect review deliberately reduced the first experiment.

For a single low-rate physical device, SiteWise and a polished 3D scene were judged unnecessary for the first proof. The current prototype favors the smallest credible vertical slice:

```text
M5Stack Core2
      |
      | MQTT/TLS + X.509
      v
AWS IoT Core
      |
      v
validation / state normalization
      |
      v
latest accepted asset state
      |
      v
TwinMaker-visible entity
```

AWS IoT SiteWise remains a possible later addition if historical time-series or richer asset-model semantics become important.

See `docs/architecture.md` and `docs/decision-log.md`.

## Telemetry model

The prototype uses a bounded IMU telemetry event similar to:

```json
{
  "device_id": "core2-aws-001",
  "timestamp": "2026-10-08T19:45:00Z",
  "accel_x": 0.03,
  "accel_y": -0.02,
  "accel_z": 1.01,
  "gyro_x": 0.4,
  "gyro_y": 0.1,
  "gyro_z": -0.2,
  "operating_state": "NORMAL",
  "sequence": 42
}
```

The domain layer validates telemetry before external state may be changed.

Current validation includes:

- required fields
- numeric validity
- deterministic operating-state derivation
- timestamp bounds
- monotonic sequence / replay protection
- normalized asset-state generation

The core domain logic is kept independent of AWS I/O so it can be tested deterministically.

## AI-first engineering workflow

This repository was created from `agent-business-solution-template` and is also an experiment in using specialized AI engineering roles with explicit human control.

The project has progressed through:

```text
PROJECT_BRIEF
      |
      v
Architect
      |
      v
acceptance contract + architecture
      |
      v
Builder
      |
      v
implementation + tests
      |
      v
Verifier
      |
      v
Reviewer / Security / Operations
      |
      v
human deployment decision
```

Agent definitions live under:

```text
.github/agents/
├── architect.agent.md
├── builder.agent.md
├── verifier.agent.md
├── reviewer.agent.md
├── security.agent.md
└── operations.agent.md
```

`AGENTS.md` defines the authority model shared by those roles.

Agents may inspect, propose, implement, test, and produce evidence.

They do **not** gain authority to deploy cloud infrastructure, broaden permissions, expose credentials, or make consequential production changes merely because a test or review passes.

## Human control boundary

The project intentionally separates engineering evidence from deployment authority.

Before live AWS resources are created, a human must review:

- AWS account and region
- resources to be created
- IAM permissions
- device certificate and IoT policy scope
- recurring cost
- data-retention implications
- rollback / deletion behavior
- expected blast radius

A passing agent review is evidence for a decision. It is not the decision itself.

## Repository map

```text
PROJECT_BRIEF.md
    Business problem, scope, constraints, and target outcome

AGENTS.md
    Agent authority and engineering rules

.github/agents/
    Specialized Architect, Builder, Verifier, Reviewer,
    Security, and Operations roles

docs/architecture.md
    Current system design and component responsibilities

docs/decision-log.md
    Architectural decisions and tradeoffs

docs/verification.md
    Executed verification evidence and remaining gaps

docs/prototype-review.md
    Prototype hypothesis, findings, and stakeholder evidence

specs/work-request.md
    Human-readable behavioral contract

specs/acceptance.json
    Acceptance IDs mapped to executable evidence

src/business_app/
    Pure application/domain logic and AWS adapter boundaries

tests/
    Behavioral and contract tests

infra/
    Infrastructure-related project assets

scripts/
    Deterministic repository quality and readiness gates
```

## Local development

Python 3.12 is used for the repository tooling and prototype domain layer.

Bootstrap:

```bash
./scripts/bootstrap.sh
```

Run the full engineering gate:

```bash
make check
```

Run behavioral tests:

```bash
make test
```

Production-readiness checks are intentionally separate:

```bash
make production
```

Passing `make check` does **not** mean the physical device or AWS digital-twin path has been demonstrated.

## Evidence over confidence

The core engineering principle of this repository is:

> AI can propose and implement quickly, but deterministic checks and observed system behavior establish evidence.

That distinction matters especially for this project because several requirements cannot be proven locally.

A complete prototype requires observed evidence from:

```text
physical M5Stack
      ↓
authenticated AWS IoT connection
      ↓
accepted telemetry
      ↓
cloud processing
      ↓
TwinMaker-visible state
```

Until that path has actually been exercised, it remains an architectural hypothesis backed by local software evidence rather than a demonstrated digital twin.

## What is deliberately out of scope

The first prototype does not attempt to provide:

- fleet-scale device management
- predictive maintenance or ML
- Kafka/Kinesis streaming architecture
- polished industrial 3D scenes
- production alerting or on-call operations
- OTA firmware management
- automatic remediation
- production availability guarantees

Those capabilities should only be introduced when evidence from the first experiment justifies the additional complexity.

## Next milestone

The next major milestone is the first controlled sandbox demonstration:

```text
move the physical M5Stack
        ↓
IMU telemetry changes
        ↓
AWS receives authenticated telemetry
        ↓
validation accepts the event
        ↓
digital-twin state changes
        ↓
human observes the change
```

That experiment will provide the first real system-level evidence for AC-101, AC-103, and AC-104.
