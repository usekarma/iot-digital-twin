# AWS + ATOM demonstration deployment proposal

Planning only; no cloud/device execution authorized. Separate from Core2 resources.
Owner: Ted / repository maintainer. Region/account/profile/binding remain UNRESOLVED;
confirm a non-production target before deriving real ARNs, costs or a saved plan.
Runtime/test implementation belongs in aws-lambda; desired state in aws-config;
Terraform/IAM/resource lifecycle in aws-iac. iot-digital-twin supplies pinned model,
frontend/firmware and acceptance contracts. Phase 2 reference tests are not adapters.

## Exact proposed logical inventory

| Resource | Proposed name | Purpose |
| --- | --- | --- |
| DynamoDB on-demand table, PK/SK | iot-interview-demo-state | One session STATE plus <=3 receipts |
| Lambda, Python 3.12, 256 MB, timeout 210s | iot-interview-demo-runner | <=180s supervised simulation; reserved concurrency 1 |
| Lambda, Python 3.12, 256 MB, timeout 10s | iot-interview-demo-read | Bundled dashboard + strongly consistent state reads |
| Lambda, Python 3.12, 256 MB, timeout 10s | iot-interview-demo-reset | Trusted reset transaction and receipt ACK |
| Function URL | attached to read Lambda only | HTTPS assets/read state; public synthetic-read requires approval |
| IoT topic rule | iot_interview_demo_reset | Exact ATOM request topic, projected fields/principal/topic |
| IAM execution roles | <function-name>-role (three) | Separated read/write/publish permissions |
| CloudWatch log groups | /aws/lambda/<function-name> (three) | Sanitized outcome logs, 7-day retention |
| Budget notification | iot-interview-demo-budget | Proposed $5 experiment alert, not a hard limit |

Reuse existing ATOM Thing/certificate; do not generate keys or attach a replacement
identity. Request topic devices/atom-lite-001/demo/reset/request; ACK topic
 devices/atom-lite-001/demo/reset/ack. Exact principal/Thing/client association must
be independently verified. One approved amendment to the existing ATOM policy,
retaining its unrelated permissions and recording the previous version for rollback.
Existing versioned S3 artifact destination is a prerequisite, not an assumed deployment.
No queues, scheduler, streams, VPC/NAT, EC2, SiteWise, TwinMaker, Kinesis or Snowflake.
No custom domain or frontend redesign. Source/model artifact hash pinned in STATE.

## IAM proposal — resolve ARN templates only after target confirmation

- Runner: GetItem/UpdateItem on the table; Query for the session CMD prefix; required
  PutItem/UpdateItem permissions for ACK receipts; iot:Publish only to exact ACK topic;
  logs:CreateLogStream/PutLogEvents only its log group. No infrastructure management.
- Reset: GetItem, UpdateItem, PutItem on the table; these item-level permissions authorize
  the respective TransactWriteItems actions. Restrict partition access where supported.
  iot:Publish only exact ACK topic; its own log writes. No Scan or arbitrary Lambda invoke.
- Read: GetItem on the table only, plus its own log writes. Strip identity/lease metadata.
  No write or IoT permissions. Public Function URL policy applies only to read function;
  restrict invoke via URL and configure both InvokeFunctionUrl/InvokeFunction permissions.
- IoT rule: reset Lambda resource policy permits iot.amazonaws.com with exact SourceArn
  and SourceAccount. Explicit field projection injects principal()/topic(); never SELECT *.
- ATOM policy: iot:Connect on reviewed exact client ARN, Publish exact request topic,
  Subscribe exact ACK topicfilter, Receive exact ACK topic. Do not grant wildcards/fleet access.
- Deployment/operator role: existing reviewed artifact/SSM/plan workflow; separate
  authorization to create/start a session, invoke runner and execute saved plan.

## Pricing envelope (illustrative US pricing, no free-tier assumption)

Choose the final region and refresh prices in aws-config cost evidence before approval.
One three-minute rehearsal: runner compute 0.25GB * 180s = 45 GB-s; at the published
example rate $0.0000166667/GB-s, approximately $0.00075 plus request cost.
One browser polls <=180 times; runner ticks <=60 times (holds after six per epoch).
At most three resets and nine ACK publish attempts. DynamoDB transactions consume
extra write units; estimate with measured serialized STATE size, capped at 64 KiB,
not an invented 1-KiB item. Query/Get read units also depend on actual item size.

For 20 rehearsals, runner compute is approximately $0.015; total estimate is NOT
complete until Lambda read/reset duration, actual DynamoDB item sizes, IoT connection/
message/rule charges, logs, artifact storage and transfer are measured and priced.
Proposed experiment ceiling $5; budget alert does not enforce a hard cap. Limit
supervised starts, concurrency, requests and run deadline; deactivate public URL when
not rehearsing. Owner checks spend after each deployment session. No automatic restart.

Sources: [Lambda pricing](https://aws.amazon.com/lambda/pricing/),
[DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/),
[IoT Core pricing](https://aws.amazon.com/iot-core/pricing/).

## Safe implementation/release order

1. Human review durable contract/reference tests. aws-lambda implements repository and
   publisher adapters, deterministic replay from pinned artifact, atomic reset/outbox,
   clock/timeouts/leases and failure reporting. Run race, crash/restart, duplicate/stale
   and lost-ACK cases against adapters; then separately approved DynamoDB integration.
2. aws-config declares unresolved principal/artifact/account/region explicitly. aws-iac
   implements the named resources and policies, validates Terraform/schema/IAM locally,
   checks state ownership and prepares a saved plan. No placeholders masquerade as real
   principal, account, artifact version or successful cost/evidence gate.
3. Review source/artifact digests, cost estimate, exact target/IAM/plan and rollback.
   Human approval separately covers artifact publishing, SSM writes and infrastructure
   apply. Smoke test cloud runner/dashboard before any physical device execution.
4. Prepare firmware subscribe/SUBACK/request/ACK correlation and unknown/timeout LED
   tests without flashing. Preserve original image and exact policy version. Separately
   approve flash and bounded live publish. Match command/session, committed epoch,
   dashboard read and ATOM application ACK/LED in sanitized evidence.
5. Measure the 60-second run, retain recording/offline fallback, inspect cost and finish
   teardown. Current INT-03/04/05 live evidence remains pending until that observation.

## Recovery, rollback and teardown

Alarm/log Lambda errors/timeouts, lease conflicts, missed tick heartbeat and ACK_UNKNOWN;
operator owns response. No secret/principal/payload dumping. If a runner dies, supervised
replacement acquires a new fence within the unchanged deadline; otherwise stop and
retain failure evidence. Reset-commit/ACK loss never causes a compensating reset.

Rollback: stop the run, disable reset rule/public URL, retain committed receipts,
restore last reviewed function artifact and ATOM policy version only with approval.
Do not resume incompatible schema/model sessions; create a fresh approved session.
Firmware rollback uses the preserved image and separate human authorization.

Approved teardown order: disable IoT rule/public entry; wait out <=180s worker deadline;
verify no remaining invocations; export sanitized evidence; restore only demo policy
amendments; delete the three functions/roles/log groups and demo table through a reviewed
saved destroy plan; remove demo budget/SSM bindings as approved. Delete only experiment
artifact versions if explicitly included. Preserve shared artifact bucket, existing
ATOM Thing/certificate/Core2 resources and unrelated policies. Inventory exact resource
names/tags, confirm no leftovers and record final spend. Receipts must survive until
commands are disabled and retention deletion is separately approved.
