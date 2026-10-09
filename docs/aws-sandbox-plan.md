# AWS sandbox plan for the first live prototype

Status: planning only. No AWS resources have been created, no Terraform apply has been run, no device certificate or private key has been generated, and no live device evidence exists.

## Decision summary

The project should use the smallest architecture that still proves the business goal: one signed device publishes accepted telemetry, the cloud path rejects invalid or replayed payloads, and the latest device state becomes visible in a TwinMaker-backed view.

The chosen first sandbox architecture is:

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

This architecture intentionally does not begin with SiteWise. The first decision is whether the device-to-cloud path is valid and observable. SiteWise remains a later option when historical time-series or richer asset semantics are required.

## Why this is the correct first AWS pattern

Current AWS IoT TwinMaker guidance uses a connector-based model for external data sources. In that model, a Lambda-based connector or first-party connector is the way TwinMaker reads data from sources that are not automatically exposed by the native SiteWise integration.

For this prototype, a custom Lambda connector is the better fit because it keeps the path small and reviewable:

- one low-rate device
- one authoritative device identity
- one latest-state store
- one minimal TwinMaker entity and component model
- no historical SiteWise asset model before the core path is proven

The direct design pattern is not “Lambda writes to TwinMaker arbitrarily.” The safer and AWS-aligned pattern is: IoT Core -> Lambda validation -> latest-state store -> TwinMaker connector reads the latest state and exposes it as a TwinMaker property/value view.

This is the smallest architecture that satisfies the prototype acceptance criteria without adding historical analytics complexity before the business proof is complete.

## Required AWS resources

The sandbox resource inventory should include the following.

### 1. AWS IoT Thing
- Purpose: represent the physical device as an authoritative AWS device identity.
- Naming: `core2-aws-001` for the prototype device.
- Dependencies: IoT certificate attachment, IoT policy attachment, MQTT topic wildcard restrictions, and Thing registry binding.
- Terraform-managed: yes, if the device identity is created in a reviewed AWS account after human approval.
- Persistent state: yes, the Thing record persists until teardown.
- Teardown: delete the Thing after the demo or revoke the certificate and detach it before deleting the Thing.

### 2. IoT certificate attachment model
- Purpose: establish the certificate as the authoritative device identity on the AWS side.
- Naming: `core2-aws-001-cert` or equivalent human-managed certificate alias.
- Dependencies: Thing attachment + IoT policy permission.
- Terraform-managed: only the attachment metadata should be managed by Terraform if the certificate is created outside Terraform by a human-controlled process.
- Persistent state: yes, certificate metadata persists until revocation or deletion.
- Teardown: revoke and disable the certificate before deleting the Thing and policy association.

### 3. IoT policy
- Purpose: allow the device to connect and publish only to its own telemetry topic.
- Naming: `iot-digital-twin-core2-aws-001-device-policy`.
- Dependencies: Thing, certificate principal, telemetry topic.
- Terraform-managed: yes, after human approval.
- Persistent state: yes, until teardown.
- Teardown: detach certificate and delete the policy.

### 4. MQTT topic structure
- Purpose: ensure each device has a narrow, reviewable publish channel.
- Naming: `devices/core2-aws-001/telemetry`.
- Dependencies: IoT policy and the IoT topic rule.
- Terraform-managed: no separate resource; it is implied by the policy and the rule.
- Persistent state: no; it is routing metadata.
- Teardown: delete the topic rule and update policy to deny publication.

### 5. IoT topic rule
- Purpose: route accepted telemetry to the ingestion Lambda.
- Naming: `core2-aws-001-ingest-rule`.
- Dependencies: IoT topic, Lambda function permission, Lambda ARN.
- Terraform-managed: yes.
- Persistent state: yes, until cleanup.
- Teardown: delete the IoT topic rule.

### 6. Ingestion Lambda
- Purpose: validate the payload, reject replay/stale data, enforce authoritative identity checks, normalize state, and forward accepted state to the latest-state store.
- Naming: `iot-digital-twin-ingest`.
- Dependencies: IoT rule invocation, IAM role, DynamoDB write access, CloudWatch logs.
- Terraform-managed: yes.
- Persistent state: no, function code is stateless; logs and artifacts persist.
- Teardown: delete the Lambda function and clean up log groups.

### 7. Latest-state store
- Purpose: hold the most recent accepted device state and sequence value.
- Naming: `iot-digital-twin-latest-state`.
- Dependencies: ingestion Lambda IAM role, optional connector Lambda read access.
- Terraform-managed: yes.
- Persistent state: yes, until teardown.
- Teardown: delete the table or empty the demo data set as part of cleanup.

### 8. TwinMaker workspace
- Purpose: provide the digital-twin environment and the entity model for the demo.
- Naming: `iot-digital-twin-demo-workspace`.
- Dependencies: IAM roles, entity model, connector integration, entity data sources.
- Terraform-managed: yes, if the provider supports the current workspace resource model.
- Persistent state: yes.
- Teardown: delete workspace and all associated entities/components if no longer needed.

### 9. TwinMaker entity and component model
- Purpose: represent the device as a single TwinMaker asset with properties such as `device_id`, `last_sequence`, `last_timestamp`, `operating_state`, and `connectivity_state` if server-derived.
- Naming: `core2-aws-001-entity` and `core2-aws-001-component`.
- Dependencies: workspace, component type, connector configuration.
- Terraform-managed: yes, if the current API is available through the provider.
- Persistent state: yes.
- Teardown: delete entity/component references before removing the workspace.

### 10. TwinMaker Lambda data connector
- Purpose: expose the latest accepted state to TwinMaker in the connector model rather than writing state ad hoc outside the supported service pattern.
- Naming: `iot-digital-twin-twinmaker-connector`.
- Dependencies: workspace and latest-state table.
- Terraform-managed: yes, once the connector pattern and deployment model are approved.
- Persistent state: no, the function is stateless; the workspace metadata and entity model persist.
- Teardown: remove connector and workspace bindings before deleting the function.

### 11. IAM roles and policies
- Purpose: enforce least privilege at each boundary.
- Naming: `iot-digital-twin-ingest-role` and `iot-digital-twin-connector-role`.
- Dependencies: AWS services invoked by each component.
- Terraform-managed: yes.
- Persistent state: no; IAM roles are metadata objects.
- Teardown: delete or detach policies before deleting the role.

### 12. CloudWatch log groups
- Purpose: capture accepted and rejected telemetry reasoning without storing secrets or certificate material.
- Naming: `/aws/lambda/iot-digital-twin-ingest` and `/aws/lambda/iot-digital-twin-connector`.
- Dependencies: Lambda execution role and logging configuration.
- Terraform-managed: yes, via lambda logging configuration or log group resources.
- Persistent state: yes until retention/cleanup.
- Teardown: delete the log groups after demo validation or rely on retention policy.

### 13. Security/operational alarms and metrics
- Purpose: guard against rejections, callbacks, or state-write failures.
- Naming: alarm names keyed to `iot-digital-twin-*`.
- Dependencies: CloudWatch metrics from the Lambda and rule invocation path.
- Terraform-managed: yes, if justified.
- Persistent state: yes.
- Teardown: delete the alarms after approval or keep them within the sandbox only.

## Device identity and certificate model

The prototype must use exactly one certificate for the prototype device.

### Required model
- The device certificate is authoritative.
- The Thing identity is bound to the certificate principal.
- The payload `device_id` is never treated as the trust anchor.
- If a device publishes a payload where `device_id` differs from the authenticated Thing identity, the message is rejected before state mutation.
- The private key and certificate material are never committed to Git or stored in Terraform state.

### Provisioning model
The human-controlled path is:

1. create a sandbox IoT Thing in AWS;
2. create a certificate and private key outside Git and outside Terraform state management;
3. attach the cert to the Thing;
4. attach the least-privilege IoT policy to the cert;
5. transfer the private key to the M5Stack securely and never commit it to the repository;
6. retain the private key only in the device secure store or a controlled provisioning environment.

This is the correct pattern because Terraform certificate resources may place private key material in state or plan output, which conflicts with the repository’s no-secret policy and security review requirements.

### Revocation and cleanup
- disable or revoke the certificate before deleting the Thing;
- detach the policy before deleting the cert;
- remove the device from the device registry if the demo is being torn down;
- confirm no certificate or policy remains active after teardown.

## MQTT authorization design

Use a per-device namespace in the topic tree:

```text
devices/core2-aws-001/telemetry
```

### Desired policy semantics
- `iot:Connect` is allowed only for the specific client ID and device certificate principal.
- `iot:Publish` is allowed only to `devices/core2-aws-001/telemetry`.
- `iot:Subscribe` is not required for the device unless a feedback path is explicitly designed.
- No wildcard topic authorization is granted unless a documented need exists.
- No account-wide `Resource: "*"` is used for device publishing unless a tighter scoped ARN is unavailable and a human approves the exception.

### Example policy semantics

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": "arn:aws:iot:REGION:ACCOUNT:client/core2-aws-001"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/devices/core2-aws-001/telemetry"
    }
  ]
}
```

This is a human-reviewed policy sketch only; no real account identifiers are included in the repository.

## Lambda ingestion contract

The IoT topic rule invokes an ingestion Lambda that enforces the local contract and cloud-side rules.

### Lambda responsibilities
- read the authoritative device identity from the AWS IoT context or registry mapping, not from the payload
- validate JSON structure, required fields, and numeric sanity
- reject stale timestamps and future-skewed messages beyond the allowed window
- reject replayed or non-monotonic sequence values
- reject identity mismatches between the payload `device_id` and the trusted identity
- reject `OFFLINE` or any device-authored connectivity field
- determine server-side derived state using the validated acceleration summary
- write only accepted, normalized state to the latest-state store

### Retry and idempotency requirements
- no broad retry loops on validation failures
- validation failure is not retried automatically
- sequence/idempotency state must be enforced in the state store, not in memory
- Lambda invocation retries should be limited to transient, infrastructure-level errors only
- a duplicate or stale message must never overwrite the last known good state

### Sequence authority
The authoritative sequence tracking must live in the durable state store. The Lambda must compare the incoming `sequence` to the persisted latest value and use a conditional write or transaction-like compare-and-swap pattern to ensure only strictly newer messages advance the latest state.

## Latest-state persistence design

### Selected store: DynamoDB
DynamoDB is the smallest appropriate design for this prototype because it provides durable latest-state tracking and a simple conditional update pattern for sequence validation.

### Recommended table shape
- table name: `iot-digital-twin-latest-state`
- primary key: `device_id` (partition key)
- sort key: optional `asset_type` if needed, but not necessary for a single device
- attributes:
  - `device_id`
  - `last_sequence`
  - `last_timestamp`
  - `operating_state`
  - `accel_summary`
  - `connectivity_state` (server-derived; optional)
  - `updated_at`

### Conditional update behavior
- only accept a message when `sequence > last_sequence`
- reject stale or duplicate updates before writing
- retain the last known good state if a message is rejected
- use a condition expression or compare-and-swap logic to avoid race conditions and double-write behavior

### Security
- encryption at rest using AWS-managed KMS keys or a reviewed customer-managed key
- the ingestion Lambda should have write access only to the specific table and exact item paths required for the prototype
- no wildcard table access in the runtime policy

## TwinMaker integration design

### Decision
We will not start with a full SiteWise-backed TwinMaker architecture. Instead, we will use the current connector model: a Lambda-based data connector reads the latest accepted state from DynamoDB and exposes it to TwinMaker through a minimal entity and component model.

### Minimal TwinMaker design
- workspace: `iot-digital-twin-demo-workspace`
- entity: `core2-aws-001`
- component type: `deviceState` or `assetCondition`
- properties:
  - `device_id`
  - `last_timestamp`
  - `last_sequence`
  - `operating_state`
  - `connectivity_state` (server-derived if implemented)
  - `motion_summary` or acceleration summary

### Why not direct Lambda write to TwinMaker?
The supported model is connector-driven. A direct Lambda write path is not the correct assumption for the first sandbox design unless the current AWS API contract explicitly supports that direct write pattern and the required connector configuration is available. The narrower, safer path is a connector that reads from the latest-state store and exposes the data to TwinMaker.

### Resulting demo behavior
The TwinMaker view shows the final accepted condition and the motion summary after a valid message is accepted; a rejected message does not change the visible state.

## Least-privilege IAM design

### IoT Core
- `iot:Connect` scoped to the specific device client ID
- `iot:Publish` scoped to the exact telemetry topic
- no topic wildcards beyond a tightly justified device namespace
- no CloudTrail or broader IAM actions for the device principal

### Ingestion Lambda
- read the IoT topic message from the rule invocation
- write accepted state only to the exact DynamoDB table / item(s)
- write CloudWatch logs only
- no AWS management actions or broad resource wildcard access

### TwinMaker connector Lambda
- read from the specific DynamoDB table and item set
- read/write only the specific TwinMaker workspace and entity/component metadata required by the demo
- no broad wildcard access to other workspaces or accounts

### IAM rule
Use resource-scoped ARNs wherever supported. Avoid blanket `Resource: "*"` unless the AWS API genuinely requires broad scope and the requirement is explicitly justified in the human review.

## Observability and evidence plan

### Metrics and logs
Measure and retain the following:
- accepted telemetry count
- rejected telemetry count
- rejected reason and category
- Lambda input errors
- state-write failures
- connector failures
- last accepted timestamp and sequence
- end-to-end latency between publish and TwinMaker read

### Sanitization requirements
No logs should include:
- private keys
- certificates or PEM material
- AWS credentials
- session tokens
- raw security secrets

### Retention and cleanup
- CloudWatch log retention should be limited to the sandbox window
- logs older than the sandbox retention limit should be expired or deleted
- no long-lived demo resources should remain after teardown

## Acceptance evidence mapping

### AC-101
Physical M5Stack publishes authenticated MQTT/TLS telemetry to AWS IoT Core.

Required evidence:
- Thing/certificate identity binding
- device publish timestamp
- IoT rule invocation timestamp
- validated Lambda receipt
- sanitized logs showing successful, authenticated receipt and not a credential leak

### AC-103
Accepted telemetry becomes TwinMaker-visible state within the required latency.

Required evidence:
- device publish timestamp
- Lambda accepted-state timestamp
- DynamoDB write timestamp
- TwinMaker read timestamp
- latency calculation as `TwinMakerReadTime - DevicePublishTime`

### AC-104
Physical movement changes the derived condition and the TwinMaker-visible state.

Required repeatable flow:
1. record stationary baseline
2. confirm `NORMAL` in TwinMaker
3. physically move or shake the device
4. record the new device event sequence and timestamp
5. confirm the derived operating state and TwinMaker visible state changed as expected
6. capture before/after evidence and timestamps

No live AWS/device claims should be made before the demo is observed and recorded.

## Cost estimate

The sandbox should be intentionally small and inexpensive:

- one IoT Thing
- one certificate and policy pair
- one Lambda function
- one DynamoDB table
- one TwinMaker workspace/entity
- minimal CloudWatch logs

This should be serverless and pay-per-use, with the major recurring cost drivers being:
- Lambda invocations
- DynamoDB reads/writes
- TwinMaker workspace and metadata objects
- CloudWatch logs and metrics

The design should ensure the prototype remains within a small sandbox budget, with the resource set easy to delete after the demo.

## Teardown plan

The teardown sequence must be explicit and human reviewed.

1. disable and revoke the device certificate
2. detach the IoT policy from the certificate
3. delete the IoT Thing or detach the Thing from the cert before removal
4. delete the IoT topic rule
5. delete the backend Lambda function and any related alias/versioning objects not needed for evidence
6. delete the DynamoDB table used for latest state
7. remove the TwinMaker entity, component, and workspace if created under the demo
8. delete CloudWatch log groups created for the demo
9. verify no remaining resources are billable in the sandbox account

Any remaining data after teardown should be explicitly identified as intentionally retained or explicitly deleted; no “maybe” resources should be left running.

## Terraform structure and non-mutating workflow

The project should keep the Terraform structure intentionally small. The purpose is planning and review, not cloud mutation.

Suggested structure under `infra/`:

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
    iam.tf
    iot.tf
    dynamodb.tf
    lambda.tf
    twinmaker.tf
    outputs.tf
```

The workflow should be:

```text
code/spec
   ↓
terraform fmt
   ↓
terraform validate
   ↓
security/static checks
   ↓
terraform plan
   ↓
human review of:
  - resources
  - IAM
  - cost
  - credentials
  - teardown
   ↓
STOP
```

Important guardrails:
- no Terraform apply
- no private key generation in Terraform
- no certificate creation in Terraform state
- no live AWS resources created from this repository
- no AWS mutation without a human decision after reviewing the plan

## Assumptions still requiring live AWS validation

The following assumptions need human-reviewed live AWS validation before the system can be called ready for the first real demo:

- exact Core2 SDK / firmware and MQTT library behavior
- certificate issuance and rotation process on actual hardware
- exact topic names and the final Thing naming model
- final runtime IAM policy wording and any service-specific constraints
- exact TwinMaker connector model supported by the current AWS account and region
- CloudWatch retention / log-redaction decisions
- confirmation that the chosen bucket/state store and connector pattern are within the sandbox budget and do not create long-lived resources

## Current status

This document is a design artifact for sandbox planning. It is not a deployment approval, a live AWS proof, or a release claim. The next step is human-approved review of the plan followed by a controlled sandbox deployment only after the preceding requirements are satisfied.
