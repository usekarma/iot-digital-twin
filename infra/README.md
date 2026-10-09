# Infrastructure planning

This directory is reserved for the non-mutating sandbox design and the implementation plan for the first AWS prototype. It does not authorize resource creation, certificate generation, or Terraform apply operations.

## Current design decision

The first sandbox should use:

```text
M5Stack Core2
    |
    | MQTT/TLS + X.509
    v
AWS IoT Core
    |
    | narrow topic rule
    v
Lambda ingestion / validation
    |
    v
DynamoDB latest-state table
    |
    v
TwinMaker connector-backed read path
    |
    v
TwinMaker-visible device state
```

The first implementation does not start with SiteWise. A SiteWise-backed path is valid later, but it is broader than the minimal prototype and adds historical time-series complexity before the live device path is proven.

## Why not direct Lambda writes to TwinMaker?

The current AWS IoT TwinMaker pattern is connector-based. The safer and more durable design is:

- IoT Core receives authenticated telemetry;
- Lambda validates and normalizes it;
- Lambda writes the accepted latest state to DynamoDB;
- a TwinMaker connector or connector-compatible Lambda reads the latest state and exposes it in the TwinMaker entity.

This keeps the architecture consistent with the current AWS service model while preserving a narrow, reviewable prototype.

## Required sandbox resources

The sandbox should include, at minimum:

- IoT Thing for the prototype device
- IoT certificate attachment to the Thing, created outside Terraform state if private-key material must be protected
- narrow IoT policy scoped to the device identity and its own topic
- IoT topic rule that routes accepted telemetry to ingestion Lambda
- ingestion Lambda with validation and sequence checks
- DynamoDB latest-state table
- TwinMaker workspace, entity, component type, and a connector-backed property model
- least-privilege IAM roles for Lambda, DynamoDB, and TwinMaker access
- CloudWatch logs and minimal metrics

## Certificate and key handling

The device certificate and private key must not be created in Terraform state or committed to Git.

Preferred approach:

1. generate the keypair and CSR outside the repository and outside Terraform state management;
2. attach the certificate to the Thing in a human-controlled provisioning flow;
3. download the certificate to the device only through a secure provisioning path;
4. never store the private key in Terraform state, CI logs, or repository artifacts.

A Terraform certificate resource is not the default design because it may expose or persist the private key in state, which violates the project’s security model.

## Terraform structure

The repository keeps the IaC structure small and reviewable:

```text
infra/
  README.md
  sandbox/
    README.md
    versions.tf
    providers.tf
    variables.tf
    locals.tf
    main.tf
    iot.tf
    lambda.tf
    dynamodb.tf
    iam.tf
    twinmaker.tf
    outputs.tf
```

This is for planning and review only. It is not an execution path and it is not a deployment pipeline.

## Non-mutating workflow

The intended workflow is:

```text
code/spec
   ↓
terraform fmt
   ↓
terraform validate
   ↓
static/security checks
   ↓
terraform plan
   ↓
human review
   ↓
STOP
```

The project must not do any of the following from this repository:

- `terraform apply`
- create live AWS resources
- generate device certificates or private keys
- place secret material in Terraform state
- claim live AWS/device acceptance criteria as passed

## Human approval gates before any AWS mutation

Before a human authorizes real AWS changes, they must review:

- the exact device identity model
- the IoT policy scope
- the IAM role boundaries
- the sandbox cost
- the cleanup plan
- the certificate revocation path
- the final evidence collection plan for AC-101, AC-103, and AC-104

This directory is deliberately a planning layer, not a deployment authority.
