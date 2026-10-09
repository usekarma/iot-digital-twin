# Verification evidence

For each change record source commit, environment/tool versions, exact commands and exit codes, acceptance IDs and observed behavior, negative cases, findings, reviewer, and residual limitations. Attach non-sensitive artifacts or repository paths. Never substitute generated prose for executed checks.

`scripts/check.py` writes JUnit, coverage, static security, and dependency audit reports to ignored `artifacts/`. CI preserves them for 14 days, including on gate failure. Review before sharing reports because future project errors can contain sensitive data.

Spec mappings verify that test IDs exist; behavioral assertions and independent review determine whether they prove the requirement. Coverage is a guardrail, not correctness proof. A successful prototype demo is not a production readiness decision.

## Corrected verifier review for current `main`

Reviewer: fresh verifier review created from the latest `origin/main`; only the evidence document was changed.

### 1. Current implementation inspected

The current implementation in [src/business_app/telemetry.py](src/business_app/telemetry.py) includes the following actual behavior:

- `MAX_CLOCK_SKEW_SECONDS = 10`
- `_validate_timestamp(value, *, now=None)` enforces the ±10s window using the supplied `now` parameter
- `validate_telemetry(..., last_sequence=<previous value>, now=<current time>)` rejects sequence values that are not greater than the previous accepted value
- `derive_operating_state` returns `NORMAL`, `WARN`, or `ALERT` from acceleration magnitude

### 2. Targeted probes against current `main`

Executed probe:

```bash
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python - <<'PY'
from datetime import datetime, timedelta, timezone
from business_app.telemetry import validate_telemetry, derive_operating_state

base_now = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
valid = {
    'device_id': 'core2-aws-001',
    'timestamp': base_now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'accel_x': 0.1,
    'accel_y': 0.2,
    'accel_z': 0.3,
    'gyro_x': 0.4,
    'gyro_y': 0.1,
    'gyro_z': -0.2,
    'operating_state': 'NORMAL',
    'sequence': 42,
}
print('VALID_PAYLOAD', validate_telemetry(valid, now=base_now))

stale = dict(valid)
stale['timestamp'] = (base_now - timedelta(seconds=11)).strftime('%Y-%m-%dT%H:%M:%SZ')
try:
    validate_telemetry(stale, now=base_now)
    print('STALE_TIMESTAMP_ACCEPTED')
except Exception as exc:
    print('STALE_TIMESTAMP_REJECTED', type(exc).__name__, exc)

ok_seq = dict(valid)
ok_seq['sequence'] = 43
try:
    validate_telemetry(ok_seq, last_sequence=42, now=base_now)
    print('INCREASING_SEQUENCE_ACCEPTED', ok_seq['sequence'])
except Exception as exc:
    print('INCREASING_SEQUENCE_REJECTED', type(exc).__name__, exc)

replay = dict(valid)
replay['sequence'] = 42
try:
    validate_telemetry(replay, last_sequence=42, now=base_now)
    print('DUPLICATE_OR_LOWER_SEQUENCE_ACCEPTED')
except Exception as exc:
    print('DUPLICATE_OR_LOWER_SEQUENCE_REJECTED', type(exc).__name__, exc)

lower = dict(valid)
lower['sequence'] = 41
try:
    validate_telemetry(lower, last_sequence=42, now=base_now)
    print('LOWER_SEQUENCE_ACCEPTED')
except Exception as exc:
    print('LOWER_SEQUENCE_REJECTED', type(exc).__name__, exc)

for bad in [dict(valid, gyro_x=float('nan')), dict(valid, accel_x=float('inf'))]:
    try:
        validate_telemetry(bad, now=base_now)
        print('NAN_OR_INF_ACCEPTED', bad)
    except Exception as exc:
        print('NAN_OR_INF_REJECTED', type(exc).__name__, exc)

bad_seq = dict(valid)
bad_seq['sequence'] = -1
try:
    validate_telemetry(bad_seq, now=base_now)
    print('NEGATIVE_SEQUENCE_ACCEPTED')
except Exception as exc:
    print('NEGATIVE_SEQUENCE_REJECTED', type(exc).__name__, exc)

print('NORMAL', derive_operating_state((0.1, 0.2, 0.3)))
print('WARN', derive_operating_state((2.0, 0.1, 0.0)))
print('ALERT', derive_operating_state((6.0, 0.0, 0.0)))
PY
```

Observed result:

- `VALID_PAYLOAD Telemetry(...)`
- `STALE_TIMESTAMP_REJECTED ValueError timestamp is outside the permitted clock-skew window`
- `INCREASING_SEQUENCE_ACCEPTED 43`
- `DUPLICATE_OR_LOWER_SEQUENCE_REJECTED ValueError sequence is not greater than the last accepted value`
- `LOWER_SEQUENCE_REJECTED ValueError sequence is not greater than the last accepted value`
- `NAN_OR_INF_REJECTED ValueError gyro_x contains an invalid numeric value`
- `NAN_OR_INF_REJECTED ValueError accel_x contains an invalid numeric value`
- `NEGATIVE_SEQUENCE_REJECTED ValueError sequence must be a non-negative integer`
- `NORMAL NORMAL`
- `WARN WARN`
- `ALERT ALERT`

### 3. Findings for current `main`

1. The current implementation does enforce a ±10 second clock-skew check when `now` is supplied correctly.
2. The current implementation does reject lower or duplicate sequence numbers when `last_sequence` is supplied as the prior accepted value.
3. The current implementation does reject NaN / infinity and negative sequence values before state mutation.
4. The operating-state derivation is correct for the current domain model: `NORMAL`, `WARN`, and `ALERT` match the expected thresholds.
5. There is still no live device or AWS observation proving AC-101, AC-103, or the live motion portion of AC-104.

### 4. Acceptance criteria assessment

| Acceptance ID | Status | Current observed evidence |
| --- | --- | --- |
| AC-101 | Not proven | No real M5Stack Core2 publish over authenticated MQTT/TLS to AWS IoT Core has been observed. |
| AC-102 | Proven locally | The current implementation rejects stale timestamps, lower/replayed sequences, NaN/inf values, and negative sequence numbers before state mutation. |
| AC-103 | Not proven | No live TwinMaker-visible update or 10-second latency measurement has been observed. |
| AC-104 | Partially proven locally | Correct `NORMAL`/`WARN`/`ALERT` derivation is observed locally, but no live device motion and no cloud-visible before/after state have been observed. |
| AC-105 | Proven locally | Repository credential scanning passes and no secret patterns were detected in tracked files. |

### 5. Residual risk and required evidence

Before claiming the digital-twin prototype is demonstrated end-to-end, the project still needs:

- a real device publish over authenticated TLS to AWS IoT Core;
- a live Lambda validation path that operates on the real device message flow;
- a live TwinMaker-visible state update with measured latency under 10 seconds;
- a real motion event that changes the observed operating state in the cloud-visible asset state.

No AWS resources were provisioned, and no live device or cloud evidence was fabricated.

### 6. Verdict

The current implementation on `main` does behave as the documented telemetry contract expects when tested with the actual API contract: `now` and `last_sequence` are enforced correctly, and the local validation logic rejects stale timestamps, replayed values, malformed numbers, and negative sequence numbers. However, AC-101, AC-103, and the live part of AC-104 remain unproven until the physical device and AWS path are exercised in a real environment.

## Independent verifier review for current `main`

Reviewer: fresh verifier review created from current `origin/main` and scoped to review-only evidence.

### 1. Branch and merge confirmation

Executed evidence:

```bash
cd /home/ted/dev/iot-digital-twin && git fetch --all --prune && git --no-pager log --oneline --decorate --graph --all --max-count=25
```

Observed result:

- `a6b884e` is the current `origin/main` tip.
- `a6b884e` is `Merge pull request #3 from usekarma/builder/telemetry-slice`.
- the merge includes `a246f92` (`Add telemetry validation slice`).

This confirms the current `main` contains the merged Builder changes from PR #3.

### 2. Deterministic gate evidence on current `main`

Executed command:

```bash
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python scripts/check.py
```

Observed result:

- exit status: 0
- `pytest`: 41 passed in 0.17s
- coverage: 100.00% total, above the required 90%
- `ruff`: all checks passed
- `mypy`: no issues found in 7 source files
- `bandit`: no findings
- `pip_audit`: no known vulnerabilities found

This is a green repository gate for the current implementation. It proves repository-level quality and credential scanning but not live AWS/device proof.

### 3. Targeted runtime probes against the current implementation

Executed probe:

```bash
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python - <<'PY'
from datetime import datetime, timedelta, timezone
from business_app.telemetry import validate_telemetry, derive_operating_state

now = datetime.now(timezone.utc)
valid = {
    'device_id': 'core2-aws-001',
    'timestamp': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'accel_x': 0.1,
    'accel_y': 0.2,
    'accel_z': 0.3,
    'gyro_x': 0.4,
    'gyro_y': 0.1,
    'gyro_z': -0.2,
    'operating_state': 'NORMAL',
    'sequence': 42,
}
print('VALID_PAYLOAD', validate_telemetry(valid))

stale = dict(valid)
stale['timestamp'] = (now - timedelta(seconds=45)).strftime('%Y-%m-%dT%H:%M:%SZ')
try:
    out = validate_telemetry(stale)
    print('STALE_TIMESTAMP_ACCEPTED', out)
except Exception as exc:
    print('STALE_TIMESTAMP_REJECTED', type(exc).__name__, exc)

replay = dict(valid)
replay['sequence'] = 42
try:
    out = validate_telemetry(replay)
    print('DUPLICATE_SEQUENCE_ACCEPTED', out)
except Exception as exc:
    print('DUPLICATE_SEQUENCE_REJECTED', type(exc).__name__, exc)

print('OPERATING_STATE_NORMAL', derive_operating_state((0.1, 0.2, 0.3)))
print('OPERATING_STATE_WARN', derive_operating_state((2.0, 0.1, 0.0)))
print('OPERATING_STATE_ALERT', derive_operating_state((6.0, 0.0, 0.0)))

bad = dict(valid)
bad['gyro_x'] = float('nan')
try:
    validate_telemetry(bad)
    print('NAN_ACCEPTED')
except Exception as exc:
    print('NAN_REJECTED', type(exc).__name__, exc)

bad2 = dict(valid)
bad2['accel_x'] = float('inf')
try:
    validate_telemetry(bad2)
    print('INF_ACCEPTED')
except Exception as exc:
    print('INF_REJECTED', type(exc).__name__, exc)

bad3 = dict(valid)
bad3['sequence'] = -1
try:
    validate_telemetry(bad3)
    print('NEGATIVE_SEQUENCE_ACCEPTED')
except Exception as exc:
    print('NEGATIVE_SEQUENCE_REJECTED', type(exc).__name__, exc)
PY
```

Observed result:

- `VALID_PAYLOAD Telemetry(...)`
- `STALE_TIMESTAMP_ACCEPTED Telemetry(...)`
- `DUPLICATE_SEQUENCE_ACCEPTED Telemetry(...)`

## Independent reviewer findings and recommendations

### Reviewer summary

The current `main` branch is green at the repository gate level, but it is not yet a demonstrated end-to-end prototype. The implementation is deterministic and well-structured for a local contract slice, while the real AWS/device evidence required by the architecture remains unobserved and should remain explicitly described as future work rather than treated as complete.

### Blocking findings

1. Contract mismatch for `OFFLINE` state
   - In [src/business_app/telemetry.py](src/business_app/telemetry.py), `VALID_OPERATIONAL_STATES` includes `OFFLINE`, but `derive_operating_state()` never returns it.
   - `validate_telemetry()` further enforces `operating_state == derive_operating_state(...)`, so an offline signal is impossible to represent under the current domain contract.
   - This is a concrete defect in the implementation-to-spec story: the allowed enum says `OFFLINE` is valid, but the deterministic derivation path rejects it.
   - Recommendation: either define a real `OFFLINE` derivation rule (for example, when the device misses a heartbeat or when the message is explicitly marked unavailable), or remove `OFFLINE` from the allowed enum until the contract is clarified.

2. Acceptance criteria are being used as if they were evidence
   - In [specs/acceptance.json](specs/acceptance.json), AC-101 maps to a local payload acceptance test, and AC-103 maps to a test that only asserts the latency requirement is documented in [docs/architecture.md](docs/architecture.md).
   - That is not live-device or live-AWS evidence; it is spec coverage, not proof of actual publish or TwinMaker observability.
   - Recommendation: keep the acceptance mapping, but mark the real cloud/device criteria as "pending live proof" unless a real device and AWS path have been exercised in a controlled demo.

3. No real device or AWS proof exists for the prototype outcome
   - The architecture in [docs/architecture.md](docs/architecture.md) is a reasonable minimal proposal, but the repository still does not contain observed evidence for: authenticated MQTT/TLS publish to AWS IoT Core, Lambda validation and normalization, or a TwinMaker-visible state change under 10 seconds.
   - The present code and tests do not replace those proofs.
   - Recommendation: before Security and Operations review, attach a human-reviewed demo record with the exact AWS account, region, resource list, device identity, and timing measurements; otherwise the prototype remains unsupported by real evidence.

### Important findings

1. The adapter boundaries are sensible, but they are still abstract contracts rather than live integration proof
   - [src/business_app/adapters.py](src/business_app/adapters.py) defines clean protocols for `IoTCoreAdapter`, `LatestStateStore`, and `TwinMakerAdapter`; this is a good separation of concerns for a prototype.
   - However, the project currently contains no implementation of those adapters against real AWS services, so the boundaries are architectural guidance, not evidence of a working integration.
   - Recommendation: keep the boundary design, but explicitly label the adapter layer as a future implementation target until the relevant AWS path has been demoed and recorded.

2. Maintainability is acceptable, but several tests are stronger as local guards than as proof of the production claim
   - [tests/test_digital_twin_contract.py](tests/test_digital_twin_contract.py) validates the domain contract well.
   - The repo still does not have a test that demonstrates live publish latency, real device motion, or AWS-visible state. That is a gap in the evidence story, not necessarily a code defect.
   - Recommendation: separate "local contract tests" from "live demo evidence" so the repo makes a clear distinction between deterministic local validation and actual cloud/device proof.

### Recommendation before Security and Operations review

- Clarify the intended meaning of `OFFLINE` in the telemetry contract before any wider approval.
- Keep SiteWise deferred until the minimal path is proven; the architecture decision in [docs/architecture.md](docs/architecture.md) remains sound.
- Preserve the local validation tests, but explicitly label them as local-only evidence and do not use them to claim AC-101 or AC-103.
- Require a recorded stakeholder demo with actual device and AWS timestamps before any release or operational approvals are considered.

### Reviewer verdict

This is a good local contract prototype with clean validation logic, but it is not yet a demonstrated IoT-to-digital-twin system. The code is reviewable and the engineering gates are green; the remaining work is evidence collection, contract clarification, and explicit separation of real proof from local assumptions.

No AWS resources were provisioned, no sensitive credentials were added, and no live AWS/device evidence was claimed beyond what is locally executable in the repository.

- `OPERATING_STATE_NORMAL NORMAL`
- `OPERATING_STATE_WARN WARN`
- `OPERATING_STATE_ALERT ALERT`
- `NAN_REJECTED ValueError gyro_x contains an invalid numeric value`
- `INF_REJECTED ValueError accel_x contains an invalid numeric value`
- `NEGATIVE_SEQUENCE_REJECTED ValueError sequence must be a non-negative integer`

### 4. Findings on current `main`

1. The current code accepts stale timestamps outside a ±10s skew window. This contradicts the contract in `specs/work-request.md` and the architecture assumptions in `docs/architecture.md`.
2. The current code accepts duplicate or replayed sequence values. This contradicts the documented requirement that per-device `sequence` values must be strictly increasing or the message is rejected or ignored.
3. The operating-state derivation logic itself is correct for the local domain model and matches the expected `NORMAL`/`WARN`/`ALERT` mapping.
4. Malformed numeric values and negative sequence numbers are rejected, which is good local validation. The gap is that the runtime policy does not enforce bounded timestamp skew or replay protection.
5. No live physical-device or AWS Cloud evidence exists for AC-101, AC-103, or AC-104.

### 5. Acceptance criteria assessment for current `main`

| Acceptance ID | Status | Current observed evidence |
| --- | --- | --- |
| AC-101 | Not proven | No physical M5Stack Core2 publish over authenticated MQTT/TLS to AWS IoT Core was observed. |
| AC-102 | Partially proven locally | Malformed numeric values and invalid negative sequence numbers are rejected, but stale timestamps and duplicate sequence values are accepted, so the full contract is not enforced. |
| AC-103 | Not proven | No live TwinMaker-visible state update or 10-second latency measurement was observed. |
| AC-104 | Partially proven locally | `derive_operating_state` behaves as expected in local logic tests, but there is no live motion event captured from a physical device and no cloud-visible before/after state. |
| AC-105 | Proven locally | The repository credential scan passes and no secret patterns were detected in tracked files. |

### 6. Residual risk and required evidence

Before claiming the prototype is demonstrated, the project still needs:

- a real device publish over authenticated TLS to AWS IoT Core;
- a live Lambda validation path that rejects stale timestamps and replayed sequence values;
- a live TwinMaker-visible asset update with a measured latency under 10 seconds;
- a real motion event that changes the derived operating parameter in the cloud-visible state.

No AWS resources were provisioned, and no live device or cloud evidence was fabricated.

### 7. Verdict

The current `main` branch is a green repository with a credible local domain model, but it does not yet satisfy the stricter end-to-end architecture requirements for a live digital-twin prototype. The local implementation is internally consistent, while the system-level acceptance criteria remain unproven without live device and AWS observations.

## Independent security review for current `main`

Reviewer: fresh security review of the current `origin/main` state. This review is limited to repository evidence and architecture intent; no AWS resources were provisioned and no live AWS/device evidence was claimed.

### Security scope and assessment basis

This project is a prototype, but the planned real path is still a security boundary: a physical device publishes telemetry through AWS IoT Core, a Lambda validates and normalizes it, a state store holds the latest accepted condition, and TwinMaker exposes that state to a user.

The repository verifies local contract logic and code quality, but it does not contain executed evidence for the live device-to-AWS path. Therefore, this review focuses on the trust boundaries that must hold before sandbox deployment and on whether the current architecture is safe enough to proceed with explicit human approval.

### Findings

#### 1. Device identity must be bound to the X.509 principal, not only to `device_id`

The domain contract in [src/business_app/telemetry.py](src/business_app/telemetry.py) relies on `device_id` as a payload field. That is useful for telemetry semantics, but it is not an identity control by itself.

For a real M5Stack device, the secure identity should be:

- the AWS IoT Thing (or equivalent certificate principal);
- the device certificate and private key kept on the device in a secure element, TPM-backed store, or equivalent locked provisioning path;
- the MQTT client identity and certificate identity bound to the same physical device identity;
- the payload `device_id` validated against the trusted device registry or Thing name rather than trusted solely because it appears in the message body.

If `device_id` is accepted as a free-form value from the device payload, a compromised or spoofed client can claim another device name and pollute state attribution. The architecture should treat `device_id` as a data attribute, not as the trust anchor.

Required control: keep payload `device_id` consistent with a trusted device registry or Thing principal and reject mismatches before state mutation.

#### 2. X.509 certificates and private keys should not live in the repository or application code

The repository correctly treats credentials as out of scope, and the secret scan is static evidence that tracked files do not contain obvious credential patterns. That is necessary but not sufficient.

For real deployment, private keys and device certificates must live:

- on the device secure storage or provisioning module;
- in an access-controlled secret manager or secure provisioning workflow only for the deployment pipeline;
- nowhere in Git, CI configuration, Terraform variables, environment files, or application package artifacts.

The project should explicitly document that certificate rotation, revocation, and renewal are required before any sandbox deployment and that no private key material is stored in the repository history or generated as part of build/test automation.

#### 3. AWS IoT Core policy scope must be tightly bounded

The architecture in [docs/architecture.md](docs/architecture.md) describes an IoT Core boundary but does not yet specify the actual IoT policy scope. That should be treated as a required design control before sandbox deployment.

The MQTT policy should be least privilege:

- allow only the specific device Thing or certificate to publish to the allowed topic(s);
- deny all other topics and actions by default;
- avoid wildcard topic subscriptions or broad publish permissions;
- constrain allowed actions to the minimum required for telemetry publishing;
- use device-specific principals and topic-level allowlists rather than a shared broad certificate policy.

A broad `iot:*` or topic wildcard policy would significantly increase the blast radius if a single device or certificate is compromised.

#### 4. Lambda and state-store permissions need explicit least-privilege boundaries

The architecture proposes a Lambda validation/normalization path and a latest-state store, but the repository does not define the resulting IAM policies. That is a security gap, not a repository defect, but it is a blocker to approval.

Required least-privilege design:

- Lambda should have permission only to the specific topic rule trigger or required input source, not broad IoT or AWS service access;
- Lambda logs should write only to a dedicated log group and never emit raw payloads at debug-level in production;
- the state store should allow only the specific table or key-space that holds latest asset state;
- TwinMaker access should be explicitly limited to the specific asset/entity or property path;
- no wildcard resource ARN patterns should be used unless there is a documented and reviewed need.

The implementation should also prevent a failure condition from broadening permissions via retries or automatic retries of a higher-privilege path. Retries should be bounded and idempotent; permission grants should remain static and reviewed.

#### 5. Replay and stale-message protection is necessary, but not sufficient without outbound trust checks

The local validation logic in [src/business_app/telemetry.py](src/business_app/telemetry.py) correctly rejects stale timestamps and lower/replayed sequences when those values are supplied appropriately. That is good hygiene.

However, the security review must also consider the live AWS path:

- the IoT rule or Lambda should reject messages that arrive with a timestamp too far in the future or too far in the past;
- the state store should be write-guarded against stale or replayed payloads by using monotonic per-device sequence checks and timestamp validation;
- it should not trust the payload `device_id` alone as proof of freshness or as the sole dedupe key;
- any replay protection should be enforced on the server side, not just in local tests.

This is good security control design and is consistent with the reviewer finding that the current repo proves local validation, not live cloud-side enforcement.

#### 6. The `OFFLINE` state is a contract and security concern, not just a domain issue

The reviewer finding remains valid: [docs/architecture.md](docs/architecture.md) and [specs/work-request.md](specs/work-request.md) allow `OFFLINE`, but [src/business_app/telemetry.py](src/business_app/telemetry.py) does not derive or accept it with the same deterministic logic as the other states.

Security concern: if `OFFLINE` becomes accepted as a client-authored state, a compromised device or malicious actor could falsely mark an asset as offline, suppress real motion state, or create confusion during incident triage.

Required control: define `OFFLINE` as a server-side derived state based on heartbeat timeout or missing telemetry, not as an arbitrary value that a device can self-select in a message payload. If `OFFLINE` is not yet implemented, remove it from the contract until the control is explicitly designed.

#### 7. Malformed payload handling must fail closed and avoid side effects

The local validation code handles malformed numeric values and negative or replayed sequences, which is good. For the live path, the same rule must hold at the Lambda or IoT rule boundary:

- invalid JSON must be rejected before state mutation;
- malformed fields must not be normalized into a state update;
- the system should retain the last known good state rather than writing partial or corrupt values;
- no action should be taken by failing open or by broadening the write path after validation errors.

The guardrail is right, but it must be repeated in the actual AWS processing layer, not only in the Python domain logic.

#### 8. Logging can leak sensitive operational data if payloads or device IDs are emitted verbatim

Telemetry payloads include device identifiers, timestamps, and motion values. That is not high-value personal data by itself, but it may still reveal operational state and physical movement patterns of equipment.

Required logging controls:

- log only redacted or normalized identifiers, not full payload bodies;
- avoid logging raw IMU values or certificate material;
- redact device IDs in debug logs unless they are actively needed for troubleshooting;
- include a consistent correlation ID rather than full payload content;
- define retention and access controls for log data because it could become operationally sensitive.

#### 9. Authentication and authorization failure behavior must not broaden the trust boundary

The architecture explicitly notes that failed authorization should not be retried by expanding permissions. This is the correct posture.

Operationally, the same rule should apply to:

- certificate rotation failures;
- IoT policy update attempts;
- Lambda execution failures that are retried with broader permissions or uncontrolled fallback paths;
- state-store write failures where a retry loop could produce duplicate or out-of-order writes.

Retries should be bounded, idempotent, and logged without revealing secrets or cert details. Azure-style or AWS-style fallback mechanisms must not silently widen the scope of access.

#### 10. The planned AWS architecture introduces a manageable but real attack surface

The main attack surfaces for the proposed prototype are:

- the device certificate and provisioning process;
- the AWS IoT Core policy and topic authorizations;
- the validation Lambda runtime and environment variables;
- the latest-state store and any linked indexes or keys;
- the TwinMaker asset representation and its access path.

This is still a small surface area, which is consistent with the project’s single-device prototype intent. However, the attack surface becomes materially larger if the project introduces wildcard topics, broad resource-level IAM, or any storage path that retains device data without a documented retention policy or access model.

### Additional controls required before sandbox deployment

The project should not advance to a sandbox deployment without the following controls being explicitly reviewed and recorded:

- device x.509 certificate issuance and rotation plan;
- device private key storage model and lifecycle;
- AWS IoT Core topic allowlist and Thing or certificate mapping;
- least-privilege IAM for Lambda, state store, and TwinMaker resource access;
- a documented secret management path with no repo or config secrets;
- stale timestamp and replay protection enforced in the live AWS pipeline;
- explicit log redaction and retention policy;
- a defined `OFFLINE` state model and/or removal of the unsupported enum value;
- a data-retention and deletion policy for recent state and any retained telemetry snapshots;
- a human review that confirms no permission broadening is implicit in retry or fallback logic.

### Residual risks and blockers

The main residual risks are not code quality issues; they are architecture and operational controls that remain unproven in the repo:

- the live certificate and identity binding model is not yet exercised;
- the real AWS IoT permission set is not yet reviewed;
- the Lambda/state-store/TwinMaker trust boundary is not yet designed in least privilege;
- no sandbox deployment has been performed, so no live device or AWS evidence exists;
- the `OFFLINE` state contract remains ambiguous and should be clarified before a wider review.

### Security verdict

The current repository is a clean local prototype with sensible validation logic and good discipline around secret scanning. The architecture is small and reviewable, and the proposed AWS path is a reasonable prototype boundary. However, the live security controls for device identity, certificate handling, AWS IoT authorization, and least-privilege IAM remain unproven and must be reviewed in a human-authored deployment design before the project proceeds to any sandbox environment.

This review does not claim live AWS/platform evidence. It does not authorize a sandbox deployment, and it does not broaden permissions or invent certificate material or AWS secrets.

## Independent operations review for current `main`

Reviewer: fresh operations review of the current `origin/main` branch. This review is limited to repository evidence, architecture intent, and the controls required for a sandbox deployment. No AWS resources were provisioned, no credentials were generated, and no live AWS/device evidence was claimed.

### Operations scope and assessment basis

The project is a single-device proof-of-value for an industrial digital twin: M5Stack Core2 for AWS publishes telemetry through AWS IoT Core, a Lambda validates and normalizes the message, a state store holds the latest accepted condition, and TwinMaker exposes it as the current entity state. The question for Operations is not whether the code is locally elegant; it is whether the planned path can be safely operated in a sandbox with controlled rollback, auditable evidence, and clear failure recovery.

The repository gives good evidence for the local validation contract, but it does not provide executed AWS/device evidence for the real path. Operations therefore treats the sandbox deployment as a gated, explicitly approved future step rather than as an already-proven operating system.

### 1. Safe sandbox operation posture

The prototype is not yet safe to operate in a sandbox because the deployment path is not fully specified and the required evidence set is still incomplete. The current code and docs support the following operating posture only in a review-only mode:

- sandbox-only deployments only, with explicit account and region controls;
- no production account or production data allowed;
- no default or wildcard permissions; all IAM must be least privilege and reviewable;
- no secret material in Git, build comments, config files, or runtime logs;
- a documented, reversible teardown path that stops all AWS resources if the demo is not validated;
- a review gate that requires human approval before any AWS mutation is performed.

Operational blocker: the repository does not yet provide a signed-off AWS deployment plan, access model, rollback plan, or live demo evidence for the actual sandbox path.

### 2. Deployment sequence and rollback

Recommended sequence for any first sandbox deployment:

1. Human confirms the AWS account, region, sandbox budget, and resource owner.
2. Human approves the exact set of AWS resources, IAM policies, certificate issuance flow, and retention policy.
3. Device identity and certificate principal are reviewed against the Thing or registry mapping.
4. IoT policy is reviewed for least privilege and topic scope.
5. A dry-run or plan-only review confirms the intended resources, their lifecycle, and their cost.
6. Only after approval is a sandbox deploy executed.
7. A short live telemetry demonstration validates the path end-to-end.
8. If the demo fails or the system does not meet the acceptance criteria, the operator immediately stops the demo flow and invokes teardown.

Rollback requirements:

- destroy all ephemeral AWS resources created for the sandbox demo;
- revoke or disable device credentials if they were created for the demo;
- remove any log retention artifacts or temporary state that are not part of the reviewed retention policy;
- restore the repo to the review-only state if the live demo does not prove the operational plan;
- keep the rollback log and decision record, with precise timestamps and human approval references.

A deployment is not considered safe if there is no documented rollback path that can remove the resources without manual guesswork.

### 3. Failure modes across device, IoT Core, Lambda, state storage, and TwinMaker

#### Device failure modes

- device disconnects or loses network connectivity;
- device sends stale timestamps or out-of-order sequence values;
- device presents a mismatched `device_id` or invalid certificate principal;
- device restarts and reuses a stale counter or clock without a verified reset path.

Required control: the real AWS path must reject device-originated state that is stale, replayed, or identity-mismatched. The payload `device_id` is not a trust anchor; the certificate or registry must be.

#### IoT Core failure modes

- auth failure; topic policy mismatch; certificate expiration or revocation;
- topic rules fail or route to the wrong path;
- message backlog or queue saturation during a device reconnect spike;
- duplicate delivery triggered by retry behavior.

Required control: narrow topic restrictions, explicit policy review, and bounded retries that preserve idempotency.

#### Lambda failure modes

- invalid JSON or schema mismatch;
- timeout while processing a message;
- partial write or write before validation is complete;
- poison message that keeps retrying without resolution.

Required control: fail closed, reject malformed messages before state mutation, and preserve the last known good state.

#### State-store failure modes

- write timeout or partial write;
- duplicate write after retry;
- stale rows overriding newer state; inconsistent last-write-wins behavior;
- table or index retention causing cost surprise.

Required control: use strictly monotonic per-device sequence checks, idempotent writes, and a clear last-known-good state model.

#### TwinMaker failure modes

- entity property write fails or times out;
- stale state from a prior device message overwrites a newer valid update;
- inability to render or observe the entity for troubleshooting.

Required control: keep synchronized state in a latest-state store and fail the visual update without corrupting the source-of-truth state.

### 4. Retries, idempotency, duplicate handling, and poison-message behavior

The repo’s local telemetry logic is right to reject staleness and replayed values. In a live AWS sandbox, the same logic must be enforced at the server boundary with explicit operational behavior:

- retries must be bounded and should not amplify the same message endlessly;
- duplicate messages must be detected by device identity + sequence + timestamp, not only by payload-only heuristics;
- stale messages must be discarded with a visible reason, not converted into a state mutation;
- poison messages must be quarantined or counted as rejected event traffic and not retried indefinitely;
- state writes must be idempotent for the same device and sequence number;
- if the device reconnects after network loss, sequence continuity must be preserved or the system must explicitly treat reconnects as a new window with a reset policy that is reviewed and documented.

Without these controls, the sandbox path is vulnerable to data drift, duplicate writes, and false operational status changes.

### 5. Observability: logs, metrics, alarms, and proof that the demo worked

Required observability before the first sandbox deployment:

- structured logs for message accepted/rejected, with reason codes rather than raw payload dumps;
- a per-device sequence counter and last accepted timestamp metric;
- stale/replay/rejected message counters by reason;
- Lambda duration, timeout, and error metrics;
- state-store write latency and write failures;
- TwinMaker sync success/failure counters;
- device connection/disconnection metrics;
- explicit alarm thresholds for repeated rejection spikes or sustained offline status.

What would prove the demo worked:

- the device successfully publishes a message over authenticated MQTT/TLS;
- IoT Core reports the message at the exact topic for that device;
- the Lambda logs a validation outcome with a single accepted event and no secret leakage;
- the latest-state store records the new asset state with the same sequence number;
- TwinMaker reflects the new asset condition within the agreed 10-second target;
- the event timestamp and sequence are captured in logs and can be matched to the device payload;
- a real motion event changes the observed state from `NORMAL` to `WARN` or `ALERT` and the before/after values are recorded.

This must be captured as evidence, not inferred from local code checks.

### 6. Stale/offline devices and device reconnect behavior

The semantics of `OFFLINE` must be clarified before any sandbox deployment. In the current repo, `OFFLINE` exists in the enum but is not derived by the domain logic. Operations requires the following definition:

- `OFFLINE` must be a server-side derived state based on heartbeat or missing-telemetry timeout, not a client-selected free-form payload value;
- if the device disconnects, the system should retain the last known good state and mark the device as stale or offline only after a defined timeout;
- reconnect behavior must be explicit: reconnect after a short outage should not be treated as a new state if the message sequence continues; reconnect after a longer outage should trigger a clear offline-status transition and a fresh sequence policy or explicit reset.

The project should not permit a device to self-report `OFFLINE` in the message payload unless that behavior is uniquely defined and server-side enforced. Otherwise it is a spoofing vector and a source of false alarm and false state.

### 7. Recovery after Lambda/state-store/TwinMaker failure

Recovery requirements:

- keep the last known good asset state as the source-of-truth and never overwrite it with a corrupt or stale message;
- if Lambda fails, preserve the event in a durable queue or log stream for replay after recovery;
- if the state store is unavailable, do not accept a new state mutation until the write is confirmed; prefer explicit rejection over silent cache-only state;
- if TwinMaker fails, continue to store the latest valid state and retry sync with backoff; do not delete the state on a failed visualization update;
- recover with a bounded retry loop and clear alerting; do not retry indefinitely without timeouts or rate limits.

The project should be able to recover cleanly after a single component outage without broad permission or data-loss assumptions.

### 8. Cost controls and cleanup requirements

The sandbox prototype must remain intentionally small. Required controls:

- select a low-cost AWS sandbox account and region;
- avoid always-on resources that are unnecessary to prove the demo;
- keep the device message rate low and bounded at or below the project target;
- disable or delete any nonessential data retention and observability resources when the demo is complete;
- document a cleanup task list and the expected cost ceiling before deployment;
- define a maximum sandbox lifetime and a mandatory teardown if the demo does not reach the agreed acceptance criteria.

No AWS resource should remain running without explicit human ownership and a documented expiry window.

### 9. Data retention and resource lifecycle

The prototype should define lifecycle rules for all data and resources:

- telemetry retention must be explicit and limited to the demo window unless human review approves a longer retention period;
- logs should be retained only as long as is required for troubleshooting and then expired or deleted;
- state-store keys should only retain the latest asset state required for the demo;
- any temporary device certificates or test identities must be destroyed after the demo or when the sandbox is closed;
- resource owners and cleanup owners must be recorded before the sandbox deployment begins.

The repository states that infrastructure should not add AWS services without a business requirement; this should apply to the sandbox as well. If a resource is unnecessary to prove the architecture, it should not be created.

### 10. Sandbox isolation from production

A sandbox must not share account or resource boundaries with production or long-lived business systems. Before deployment, the project should confirm:

- the AWS account is a dedicated sandbox or dev account;
- the region is explicitly designated for prototype use;
- resource names are unique and clearly tagged with the demo scope;
- production data and credentials are not used by the prototype;
- all IAM actions are isolated to the sandbox resource identifiers only.

Because this project is intentionally narrow, any production connection or shared resource should be treated as a blocker.

### 11. Runbook requirements

The sandbox runbook must include, at minimum:

- resource inventory and owners;
- account and region details;
- device certificate issuance and rotation procedure;
- IoT Core topic and policy review;
- Lambda validation logic and error codes;
- state-store failure and replay recovery steps;
- TwinMaker state visibility check;
- expected normal behavior and what constitutes a rejected message;
- alarm thresholds and escalation contacts;
- restart and reconnect procedures for the device;
- standard rollback and teardown steps.

Without a runbook, the system cannot be safely operated or recovered in a sandbox.

### 12. Evidence needed before and after deployment

Before any sandbox deployment, the project should have evidence for:

- authoritative device identity mapping from certificate principal to Thing or registry identity;
- least-privilege IoT policy and IAM definitions;
- exact AWS account, region, resources, and expected cost ceiling;
- human approval for the exact resource set and deletion plan;
- explicit `OFFLINE` semantics and the server-side replay/stale validation plan;
- log redaction and secret-handling policy.

After deployment, the project should capture evidence for:

- successful authenticated device publish;
- accepted/rejected message reason codes;
- message latency from device publish to accepted state write;
- transition from one operating state to another under controlled motion;
- reconnect/disconnect handling and recovery path;
- successful teardown and no resource left running after the demo.

The repository currently does not contain that live AWS/device evidence; therefore the sandbox remains a future approval decision, not a completed operational milestone.

### 13. Exact human approval points

The first sandbox deployment should require at least these human approvals before any AWS mutation is performed:

1. approval to create the sandbox account or use the designated dev/sandbox account;
2. approval of the exact AWS region, resource list, and resource owners;
3. approval of the Thing/device identity, certificate issuance path, and policy scope;
4. approval of IAM least-privilege policies for IoT, Lambda, state store, and TwinMaker;
5. approval of the cost ceiling and cleanup ownership model;
6. approval of the runbook and rollback plan;
7. approval to proceed only after at least one successful live demo proof or a documented exception.

These approvals must be explicit and recorded. A repository review or a passing check is not sufficient authorization.

### 14. Teardown procedure so no AWS resources are left running unintentionally

A sandbox teardown checklist must be executed immediately after every demo or any failed deployment attempt:

- disable or delete the device certificate or Thing if created for the demo;
- remove the IoT Core topic rule and policy entries tied to the sandbox demo;
- delete Lambda resources, log groups, and any temporary execution or event triggers;
- remove state-store entries or tables that were created for the prototype if they are not expressly required for an approved longer-lived sandbox;
- delete TwinMaker entity or asset resources created for the demo;
- remove any dashboards, alarm resources, or object storage artifacts created for the experiment;
- confirm no resources remain running in the sandbox account and record the final teardown status.

If any step cannot be executed, the deployment should be treated as incomplete and the remaining resources flagged for immediate human review. The project must never leave an AWS sandbox resource in an unowned or unreviewed state.

### Operations verdict

The current `main` branch is a solid local proof-of-contract and a credible starting point for a minimal digital-twin design. It is not yet a safe sandbox-operating system. The operational blockers are real and specific:

- authoritative device identity must come from the cert or registry context and not from unsafeguarded payload data;
- IoT policies must be narrow and least privilege;
- IAM must be least privilege end-to-end;
- replay and stale enforcement must be server-side and not just local Python logic;
- logs must not expose secrets or raw payloads;
- `OFFLINE` semantics must be clarified before the project claims it can model disconnected devices safely.

The correct operations decision is: do not approve a sandbox deployment yet. Continue only with a documented, human-reviewed runbook, explicit IAM and certificate design, measured live evidence, and a teardown procedure that can guarantee no AWS resources are left running unintentionally.

This review does not claim live AWS/device evidence. It does not authorize sandbox deployment or resource creation. It documents the exact conditions required for approval of the first sandbox demo.

## Verifier review of Builder remediation PR #11

Reviewer: fresh independent verifier review of Builder remediation PR #11 after it was merged onto `origin/main`.

### Exact commit reviewed

- Builder remediation commit: `6f459f9` (`Fix offline and identity trust contract`)
- Main merge commit containing PR #11: `2225f6b` (`Merge pull request #11 from usekarma/builder/remediation-pre-sandbox`)

This review verifies the repository state on `origin/main` after the PR merged, without claiming any live AWS or device observation.

### Exact checks run

Executed commands:

```bash
cd /home/ted/dev/iot-digital-twin && git pull --ff-only origin main
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python scripts/check.py
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python - <<'PY'
from datetime import UTC, datetime, timedelta
from business_app.telemetry import validate_telemetry

base_now = datetime(2026,10,8,12,0,0,tzinfo=UTC)
base = {
    'device_id':'core2-aws-001',
    'timestamp': base_now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'accel_x': 0.03,
    'accel_y': -0.02,
    'accel_z': 1.01,
    'gyro_x': 0.4,
    'gyro_y': 0.1,
    'gyro_z': -0.2,
    'operating_state':'NORMAL',
    'sequence':42,
}

for name, fn in [
    ('VALID_ACCEPTED', lambda: validate_telemetry(base, now=base_now)),
    ('OFFLINE_REJECTED', lambda: validate_telemetry({**base, 'operating_state':'OFFLINE'}, now=base_now)),
    ('MISMATCH_REJECTED', lambda: validate_telemetry(base, now=base_now, authenticated_device_id='core2-aws-999')),
    ('STALE_REJECTED', lambda: validate_telemetry({**base, 'timestamp': (base_now - timedelta(seconds=11)).strftime('%Y-%m-%dT%H:%M:%SZ')}, now=base_now)),
    ('REPLAY_REJECTED', lambda: validate_telemetry(base, now=base_now, last_sequence=42)),
    ('NEXT_ACCEPTED', lambda: validate_telemetry({**base, 'sequence':43}, now=base_now, last_sequence=42)),
]:
    try:
        result = fn()
        print(name, 'ACCEPTED', result)
    except Exception as exc:
        print(name, 'REJECTED', type(exc).__name__, exc)
PY
```

Observed results:

- `python scripts/check.py` exited successfully.
- 45 tests passed.
- coverage reached 93.85%.
- Ruff, mypy, Bandit, and pip-audit all passed.
- targeted runtime verification output included:
  - `VALID_ACCEPTED ACCEPTED Telemetry(...)`
  - `OFFLINE_REJECTED REJECTED ValueError OFFLINE is server-derived and cannot be self-reported by the device`
  - `MISMATCH_REJECTED REJECTED ValueError device_id does not match the authenticated device identity`
  - `STALE_REJECTED REJECTED ValueError timestamp is outside the permitted clock-skew window`
  - `REPLAY_REJECTED REJECTED ValueError sequence is not greater than the last accepted value`
  - `NEXT_ACCEPTED ACCEPTED Telemetry(...)`

### Observed behavior

The repository behavior on the merged `main` branch is consistent with the Builder remediation claims for the local contract layer:

- device-authored `OFFLINE` is rejected
- connectivity/offline status is documented and enforced as server-derived, not device-authored
- `device_id` in the payload is treated as data and not as a trust anchor when an authoritative identity is supplied
- a mismatch between payload `device_id` and the authenticated device identity is rejected
- stale timestamps remain rejected
- replayed or non-monotonic sequence values remain rejected
- valid telemetry still succeeds when the payload matches the authenticated device and the operating-state derivation remains consistent

This is local behavior only; it is not AWS/device proof. It does not establish a live sandbox deployment or a real TwinMaker update.

### Prior findings resolved by PR #11

The Builder remediation resolves the following specific issues from the earlier review cycle:

- Reviewer PR #8: `OFFLINE` contract mismatch is resolved by removing device-authored offline semantics from the valid device contract and documenting the server-derived status model.
- Reviewer PR #8: local evidence is no longer implied to be live AWS/device proof; the acceptance mapping explicitly distinguishes local evidence from live-demo-required evidence.
- Security PR #9: payload `device_id` is no longer treated as the trust anchor when an authoritative device identity is supplied; mismatch rejection is enforced.
- Security PR #9: the repo now clearly separates device operating condition from server-derived connectivity/offline semantics.
- Operations PR #10: stale/replay and offline semantics are explicitly documented as server-side controls, which matches the local validation and the operational review requirements.

### Acceptance criteria still dependent on live AWS/device evidence

The following acceptance criteria remain explicitly unproven and require a human-approved live AWS/device demonstration before any claim is made:

- AC-101: physical device publishes valid IMU telemetry over authenticated TLS to AWS IoT Core
- AC-103: valid telemetry reaches TwinMaker-visible state within 10 seconds under normal development conditions
- AC-104: a live physical motion event changes the cloud-visible asset condition; the local derivation logic is not enough to prove this

The remaining local-only evidence is:

- AC-102: malformed or out-of-range telemetry is rejected before state mutation in local contract validation
- AC-105: repository secret scanning and credential hygiene remain local repository evidence only

### Verdict

PR #11 resolves the local contract and evidence-contract issues it claimed to resolve. It does not prove a live device/AWS digital-twin path, and it should not be interpreted as deployment or sandbox approval. The repository is now consistent with the intended local contract boundaries, but live AWS/device observations remain required for the end-to-end prototype claims.
