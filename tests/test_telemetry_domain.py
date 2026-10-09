from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from business_app.telemetry import Telemetry, derive_operating_state, validate_telemetry

CURRENT_TIME = datetime.now(UTC)

VALID_PAYLOAD = {
    "device_id": "core2-aws-001",
    "timestamp": CURRENT_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "accel_x": 0.03,
    "accel_y": -0.02,
    "accel_z": 1.01,
    "gyro_x": 0.4,
    "gyro_y": 0.1,
    "gyro_z": -0.2,
    "operating_state": "NORMAL",
    "sequence": 42,
}


def test_validate_telemetry_accepts_valid_payload() -> None:
    telemetry = validate_telemetry(VALID_PAYLOAD)
    assert isinstance(telemetry, Telemetry)
    assert telemetry.device_id == "core2-aws-001"
    assert telemetry.operating_state == "NORMAL"
    assert telemetry.sequence == 42


def test_validate_telemetry_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        validate_telemetry({**VALID_PAYLOAD, "timestamp": "not-a-time"})


def test_validate_telemetry_rejects_timestamp_outside_skew_window() -> None:
    current_time = datetime.now(UTC)
    stale_payload = {
        **VALID_PAYLOAD,
        "timestamp": (current_time - timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    future_payload = {
        **VALID_PAYLOAD,
        "timestamp": (current_time + timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with pytest.raises(ValueError, match="clock-skew"):
        validate_telemetry(stale_payload, now=current_time)

    with pytest.raises(ValueError, match="clock-skew"):
        validate_telemetry(future_payload, now=current_time)


def test_validate_telemetry_rejects_non_monotonic_sequence() -> None:
    payload = {**VALID_PAYLOAD, "sequence": 41}

    with pytest.raises(ValueError, match="sequence"):
        validate_telemetry(payload, last_sequence=41)

    with pytest.raises(ValueError, match="sequence"):
        validate_telemetry(payload, last_sequence=42)


@pytest.mark.parametrize(
    ("payload", "error_message"),
    [
        ({"device_id": "x"}, "Missing required fields"),
        ({**VALID_PAYLOAD, "sequence": -1}, "sequence"),
        ({**VALID_PAYLOAD, "operating_state": "BOGUS"}, "operating_state"),
        ({**VALID_PAYLOAD, "timestamp": 123}, "timestamp"),
        ({**VALID_PAYLOAD, "accel_x": float("nan")}, "invalid numeric value"),
        ({**VALID_PAYLOAD, "accel_x": True}, "numeric"),
        ({**VALID_PAYLOAD, "operating_state": "WARN"}, "does not match derived"),
    ],
)
def test_validate_telemetry_rejects_invalid_domain_values(
    payload: dict[str, object], error_message: str
) -> None:
    with pytest.raises((TypeError, ValueError), match=error_message):
        validate_telemetry(payload)


@pytest.mark.parametrize(
    ("payload", "error_message"),
    [
        ([], "payload must be a mapping"),
        ({**VALID_PAYLOAD, "device_id": ""}, "device_id"),
    ],
)
def test_validate_telemetry_rejects_invalid_shapes(payload: object, error_message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=error_message):
        validate_telemetry(payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("accel_values", "expected"),
    [((0.1, 0.2, 0.3), "NORMAL"), ((2.0, 0.1, 0.0), "WARN"), ((6.0, 0.0, 0.0), "ALERT")],
)
def test_derive_operating_state(accel_values: tuple[float, float, float], expected: str) -> None:
    assert derive_operating_state(accel_values) == expected
