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
