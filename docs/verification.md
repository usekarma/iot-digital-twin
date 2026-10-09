# Verification evidence

For each change record source commit, environment/tool versions, exact commands and exit codes, acceptance IDs and observed behavior, negative cases, findings, reviewer, and residual limitations. Attach non-sensitive artifacts or repository paths. Never substitute generated prose for executed checks.

`scripts/check.py` writes JUnit, coverage, static security, and dependency audit reports to ignored `artifacts/`. CI preserves them for 14 days, including on gate failure. Review before sharing reports because future project errors can contain sensitive data.

Spec mappings verify that test IDs exist; behavioral assertions and independent review determine whether they prove the requirement. Coverage is a guardrail, not correctness proof. A successful prototype demo is not a production readiness decision.

## Independent verifier report

Reviewer: Verifier pass on the current `main` branch and a fresh branch created for evidence review (`verifier/telemetry-slice-review`).

### 1. Deterministic gate evidence

Executed command:

```bash
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python scripts/check.py
```

Observed result:

- exit status: 0
- `pytest`: 41 passed in 0.14s
- coverage: 100.00% total, above the 90.00% threshold
- `ruff`: all checks passed
- `mypy`: Success: no issues found in 7 source files
- `bandit`: no findings produced for the scoped source tree
- `pip_audit`: No known vulnerabilities found

This is strong local validation evidence for the repository itself. It proves the codebase is internally consistent and contains no committed credential patterns, but it does not prove the AWS IoT + Lambda + TwinMaker path is working end-to-end.

### 2. Contract-enforcement evidence

The architecture and work request require a bounded clock-skew window and strictly increasing `sequence` values for a given device before a payload is accepted. The actual implementation in `src/business_app/telemetry.py` does not enforce those checks.

Executed probe:

```bash
cd /home/ted/dev/iot-digital-twin && . .venv/bin/activate && python - <<'PY'
from datetime import datetime, timedelta, timezone
from business_app.telemetry import validate_telemetry

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
print('valid_result', validate_telemetry(valid))

stale = dict(valid)
stale['timestamp'] = (now - timedelta(seconds=45)).strftime('%Y-%m-%dT%H:%M:%SZ')
stale['sequence'] = 43
try:
    validate_telemetry(stale)
    print('stale_timestamp_ACCEPTED')
except Exception as exc:
    print('stale_timestamp_REJECTED', type(exc).__name__, exc)

dupe = dict(valid)
dupe['sequence'] = 42
try:
    validate_telemetry(dupe)
    print('duplicate_sequence_ACCEPTED')
except Exception as exc:
    print('duplicate_sequence_REJECTED', type(exc).__name__, exc)
PY
```

Observed result:

- `valid_result Telemetry(...)`
- `stale_timestamp_ACCEPTED`
- `duplicate_sequence_ACCEPTED`

This demonstrates a real specification gap: the code accepts stale timestamps and duplicate/replayed sequence numbers even though the architecture and work request require those conditions to be rejected or ignored.

### 3. Acceptance criteria status

| Acceptance ID | Status | Evidence and limits |
| --- | --- | --- |
| AC-101 | Not proven in live execution | No physical M5Stack Core2, TLS certificate flow, or AWS IoT Core publish was observed. The repository contains only local validation logic and documentation. |
| AC-102 | Partially proven locally | Malformed sensor values and invalid enums are rejected in local tests, but stale timestamps and replayed `sequence` values are accepted by the implementation, so the full contract is not enforced. |
| AC-103 | Not proven in live execution | No real AWS Lambda or TwinMaker update was observed, and no latency measurement under normal development conditions exists. |
| AC-104 | Partially proven in local logic | `derive_operating_state` is deterministic and unit-tested, but no physical motion event was captured from a real device or a live TwinMaker-visible state update. |
| AC-105 | Proven locally | `scripts/check.py` passed the repository credential scan and no secret patterns were detected in tracked files. |

### 4. Findings

1. The repository passes deterministic engineering gates, but the code does not yet satisfy the stricter runtime contract described in the architecture and work request.
2. The critical gap is in validation policy: bounded clock skew and replay protection are described as required behavior but are not currently implemented in `validate_telemetry`.
3. The acceptance-test layer is too shallow to prove the end-to-end architecture; it validates document structure and simple field formatting, not real MQTT/TLS or cloud state propagation.
4. The current prototype remains a local business-logic slice, not a demonstrated AWS digital-twin data path.

### 5. Residual risk and next required evidence

Before claiming the prototype is valid for the architecture proposal, the team still needs:

- one live MQTT publish from the Core2 device over authenticated TLS;
- one AWS IoT Core authorization and topic validation path observed in logs;
- one Lambda validation path that rejects stale timestamps and replayed sequences;
- one confirmed TwinMaker-visible asset update within the 10-second target;
- one real motion event that changes the derived operating state in the cloud-visible value.

Until that evidence exists, the safest statement is: the local repo is consistent and the domain logic is implemented, but the end-to-end physical and cloud path is unverified.

### 6. Verdict

The current implementation is a credible local prototype for telemetry validation and state derivation, but it is not yet a validated implementation of the architecture’s strict runtime contract. The repository is green, yet the business requirement remains partially unproven.
