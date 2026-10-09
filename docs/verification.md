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

4. The adapter boundaries are sensible, but they are still abstract contracts rather than live integration proof
   - [src/business_app/adapters.py](src/business_app/adapters.py) defines clean protocols for `IoTCoreAdapter`, `LatestStateStore`, and `TwinMakerAdapter`; this is a good separation of concerns for a prototype.
   - However, the project currently contains no implementation of those adapters against real AWS services, so the boundaries are architectural guidance, not evidence of a working integration.
   - Recommendation: keep the boundary design, but explicitly label the adapter layer as a future implementation target until the relevant AWS path has been demoed and recorded.

5. Maintainability is acceptable, but several tests are stronger as local guards than as proof of the production claim
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
