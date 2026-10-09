# AWS sandbox planning prototype

This directory contains a non-mutating Terraform structure for the AWS sandbox design for the single-device digital-twin prototype.

## Design intent

- one device
- one Thing
- one certificate attached outside Terraform state
- one narrow MQTT topic
- one ingestion Lambda
- one DynamoDB latest-state table
- one minimal TwinMaker workspace and entity model
- one connector-backed read path to TwinMaker

## Safety guardrails

- no private key generation in Terraform
- no certificate material in the repository
- no `terraform apply`
- no live AWS mutation from this repository
- no resource creation without explicit human approval after reviewing the plan

## Expected flow

1. define the Thing, policy, Lambda, and state store in Terraform for review
2. validate the configuration locally
3. generate a plan for review only
4. stop before apply
5. require human approval for any real AWS change
