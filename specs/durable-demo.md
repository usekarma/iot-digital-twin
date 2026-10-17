# Durable AWS demonstration behavior — Issue #17 Phase 2

Status: planning baseline and executable local reference tests; not deployed.
Stakeholder/owner: Ted and repository maintainer. Acceptance goal: one live 60-second
AWS simulator -> dashboard -> authenticated ATOM reset -> application ACK demonstration.
Local reference tests are not evidence that DynamoDB or AWS IoT executed correctly.
Existing Core2, simulator, trace and dashboard acceptance/evidence remain separate.

## Ownership and scope

`iot-digital-twin` owns this contract, simulator/traces, firmware and acceptance tests.
`aws-lambda` implements SDK/runtime adapters and immutable packaging of a pinned model
revision; `aws-config` owns non-secret desired state/artifact bindings; `aws-iac` owns
Terraform/IAM/wiring/deployment. Do not copy the model into a second rule engine.
This slice supplies no SDK adapter, Terraform resource, credential/policy mutation,
MQTT publisher or firmware change. Runtime implementation is the next scoped handoff.

## Proposed DynamoDB contract

One on-demand table with string PK/SK, no GSI or stream. A trusted operator starts one
session with a fresh 128-bit ID, exact ATOM certificate principal binding and a fixed
absolute server-clock deadline (180 seconds); neither device nor browser chooses it.
PK = SESSION#<session_id>. SK = STATE for state, CMD#<command_id> for reset receipts.
The operator/read handlers select the active session from reviewed run configuration.
No automatic session rollover; stale sessions cannot become active through commands.

STATE contains schema_version=1, model artifact version, seed=17, asset_count=5,
epoch, tick, revision, accepted_command_count, next_tick_at, run_deadline, runner owner, lease_until,
fencing counter, current synthetic observations/latest trace and at most 12 recent
snapshots. Store JSON/numeric data only: no pickle, credentials or serialized RNG.
Maximum STATE item 64 KiB; command item 2 KiB; reject oversized items before writing.
Replay at most six progression ticks per epoch from the pinned Python 3.12/model
version, then hold state while waiting for reset or deadline. Each tick is three wall
seconds apart (60 simulated seconds). Fault/model/observation semantics are unchanged.
Replay reconstructs state after process loss without consuming an extra committed tick;
the adapter relabels replayed observations/traces with the durable epoch consistently.
Incompatible model/schema versions fail closed, not silently restart.

Read STATE with ConsistentRead=true; return a single coherent bounded snapshot.
Dashboard polling is read-only, at most once/second; it never drives simulator ticks.
Expose synthetic state and run status only, not certificate principal or runner lease.

## Runner and conditional writes

Acquire/renew a lease via conditional UpdateItem. One runner owns a lease of 10 seconds,
renewed before expiry. Acquire after expiry increments the fencing counter and revision.
Absolute run_deadline never extends on acquisition, restart or reset. Worker invocation
has a local monotonic budget <=180 seconds, stops with Lambda timeout margin, and uses
server UTC for durable lease/deadline decisions. Lease safety assumes bounded host-clock
skew; provision/test margin and fail closed when time is unavailable or inconsistent.

Tick update condition: session/model match AND epoch/tick/revision/fence/owner equal
read snapshot AND lease_until > now AND run_deadline > now AND next_tick_at <= now.
Result advances tick and per-asset sequences together once, increments revision,
updates trace/history and schedules the next tick. Failed conditions discard calculated
output, reread and decide anew; no blind write or permission expansion. After six ticks,
runner renews boundedly while waiting for reset; no unbounded fault/history growth.

If reset commits first, the pending old-epoch tick fails. If tick commits first, reset
rereads revision and retries its transaction with the same command identity. Expired
workers cannot commit after a new lease/fence is acquired. Lost update responses are
resolved by consistent reread of revision/epoch/tick, never blindly advancing again.
No automatic new runner is promised: supervised restart within the existing deadline
recovers the cursor; after deadline, start a separately authorized new session.

SDK connect/read timeouts 2/3 seconds; max_attempts=2. At most two application conflict
retries per command, with injected bounded backoff within the invocation deadline.
Validation/stale-session failures never retry. Alarm/report exhaustion rather than loop.

## Reset transaction and application ACK

IoT rule explicitly projects command fields and injects principal()/topic(); no SELECT *.
Only the reviewed rule/account can invoke reset processing. Payload device_id is data,
not authority. Command: session_id, command_id (1–64 ASCII letters/digits/_/-),
expected_epoch. Authenticate exact principal/topic against current session bindings.
A maximum of three distinct accepted commands is allowed per session.

Check active session/deadline/identity before processing even a duplicate. A receipt
with the same ID and identical command fields returns its original committed ACK;
a reused ID with different fields is a conflict. New command with old/future epoch
rejects without state mutation. Receipt lookup uses consistent reads.

TransactWriteItems performs BOTH: (1) conditional STATE reset to known baseline,
epoch+1, tick/sequence=0, history baseline, revision+1, accepted_command_count+1
(conditioned on count < 3), next_tick_at=now+3; preserve
runner fence/lease and absolute deadline; (2) conditional Put CMD receipt if absent,
including command fingerprint, committed new epoch and ACK status pending. One STATE
Update carries its own conditions; do not ConditionCheck the same item separately.
Any failure leaves neither change committed. If response is lost, reread the receipt.
DynamoDB client-token idempotency alone is insufficient: its window is only ten minutes.
[Transaction semantics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html).

ACK payload: version=1, session_id, command_id, expected_epoch, committed_epoch,
status=reset_committed. ACK proves committed baseline, not screen rendering, device
receipt, or that the baseline has remained unchanged since subsequent ticks.
Publish only after a committed receipt exists to exact
`devices/atom-lite-001/demo/reset/ack`. Device request topic:
`devices/atom-lite-001/demo/reset/request`; require separately reviewed policy change.
Never send completion ACK for validation failure, failed/unknown commit or stale session.

Receipt is the durable outbox. Atomic claim of pending ACK increments attempt count;
max three publish attempts, claim timeout five seconds. Publish timeout/error/crash
leaves it retryable; successful publish marks sent but does not establish device receipt.
Runner scans only the bounded three known command slots and can retry pending ACKs;
no DynamoDB Scan, streams or new queue. The concrete adapter must define Query on this
partition/command prefix and atomic claim/lease conditions. Duplicate delivery may
republish the original ACK within the shared three-attempt bound, without another reset.
A publish-success/mark-sent crash can yield duplicate ACKs; device deduplicates them.
After attempt exhaustion/deadline, record ACK_UNKNOWN; operator investigates. Do not
show success or reset again to compensate. Receipts persist until approved teardown;
TTL must not delete replay protection while the session can accept commands.

ATOM subscribes and confirms SUBACK before request, stays connected up to ten seconds,
and indicates success only for matching session/command/committed epoch on its ACK
subscription. PUBACK remains pending feedback. Ignore duplicate/retained/stale/wrong ACKs;
no automatic reconnect or request retry. Lost ACK produces timeout/unknown, even if reset
committed. Safe operator-supervised receipt redelivery uses the SAME command identity;
firmware subscription/request changes and hardware proof are later approved work.

## Acceptance and remaining evidence

- AC-212: conditional tick/reset interleavings and fences reject obsolete writes.
- AC-213: restart deterministically reconstructs observations/trace; bounds/deadline hold.
- AC-214: duplicate reset, conflicting ID, stale session/epoch and expiry fail safely.
- AC-215: committed receipt precedes ACK, lost publish retry/deduplication is bounded.

Test-only reference models emulate persistent storage across worker instances and
controlled interleavings. They cannot certify actual DynamoDB atomicity, SDK timeout,
clock skew, IAM or MQTT behavior. aws-lambda must run the same scenarios against its
adapter; aws-iac validates Terraform/IAM; approved live evidence must correlate press,
principal, command, epoch change, dashboard read and device application ACK. Until
that observed 60-second run, INT-03/04/05 live completion remains PENDING.
