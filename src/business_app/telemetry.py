"""Telemetry validation and digital-twin state logic for the M5Stack prototype."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

VALID_OPERATIONAL_STATES = {"NORMAL", "WARN", "ALERT", "OFFLINE"}
REQUIRED_FIELDS = {
    "device_id",
    "timestamp",
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "operating_state",
    "sequence",
}


@dataclass(frozen=True)
class Telemetry:
    """Validated device telemetry for a single digital-twin asset."""

    device_id: str
    timestamp: str
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    operating_state: str
    sequence: int


def derive_operating_state(accel_values: tuple[float, float, float]) -> str:
    """Map acceleration magnitude to a small deterministic operating state."""
    magnitude = sum(abs(float(value)) for value in accel_values)
    if magnitude > 4.0:
        return "ALERT"
    if magnitude > 1.5:
        return "WARN"
    return "NORMAL"


def _as_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    numeric_value = float(value)
    if numeric_value != numeric_value or abs(numeric_value) >= 1_000_000:
        raise ValueError(f"{name} contains an invalid numeric value")
    return numeric_value


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("timestamp must be a UTC timestamp string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be RFC3339 UTC") from exc
    return value


def validate_telemetry(payload: Mapping[str, object]) -> Telemetry:
    """Validate a telemetry payload before the digital twin may ingest it."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    missing = REQUIRED_FIELDS - set(payload)
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ValueError(f"Missing required fields: {missing_fields}")

    device_id = payload["device_id"]
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be a non-empty string")

    sequence = payload["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")

    accel_x = _as_float(payload["accel_x"], "accel_x")
    accel_y = _as_float(payload["accel_y"], "accel_y")
    accel_z = _as_float(payload["accel_z"], "accel_z")
    gyro_x = _as_float(payload["gyro_x"], "gyro_x")
    gyro_y = _as_float(payload["gyro_y"], "gyro_y")
    gyro_z = _as_float(payload["gyro_z"], "gyro_z")

    operating_state = payload["operating_state"]
    if not isinstance(operating_state, str) or operating_state not in VALID_OPERATIONAL_STATES:
        raise ValueError("operating_state is not in the allowed enum")

    timestamp = _validate_timestamp(payload["timestamp"])
    derived_state = derive_operating_state((accel_x, accel_y, accel_z))
    if operating_state != derived_state:
        raise ValueError("operating_state does not match derived motion state")

    return Telemetry(
        device_id=device_id,
        timestamp=timestamp,
        accel_x=accel_x,
        accel_y=accel_y,
        accel_z=accel_z,
        gyro_x=gyro_x,
        gyro_y=gyro_y,
        gyro_z=gyro_z,
        operating_state=operating_state,
        sequence=sequence,
    )
