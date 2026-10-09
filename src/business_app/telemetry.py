"""Telemetry validation and digital-twin state logic for the M5Stack prototype."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

DEVICE_OPERATIONAL_STATES = {"NORMAL", "WARN", "ALERT"}
SERVER_CONNECTIVITY_STATES = {"ONLINE", "OFFLINE"}
VALID_OPERATIONAL_STATES = DEVICE_OPERATIONAL_STATES
MAX_CLOCK_SKEW_SECONDS = 10
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

    def to_asset_state(self) -> dict[str, str | int]:
        """Return the normalized state that an adapter may persist or display."""
        return {
            "device_id": self.device_id,
            "operating_state": self.operating_state,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }


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


def _validate_timestamp(value: object, *, now: datetime | None = None) -> str:
    if not isinstance(value, str):
        raise TypeError("timestamp must be a UTC timestamp string")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be RFC3339 UTC") from exc

    if now is None:
        current_time = datetime.now(UTC)
    elif isinstance(now, datetime):
        current_time = now
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        else:
            current_time = current_time.astimezone(UTC)
    else:
        raise TypeError("now must be None or a datetime")

    message_time = parsed.replace(tzinfo=UTC)
    skew_seconds = abs((message_time - current_time).total_seconds())
    if skew_seconds > MAX_CLOCK_SKEW_SECONDS:
        raise ValueError("timestamp is outside the permitted clock-skew window")

    return value


def validate_telemetry(
    payload: Mapping[str, object],
    *,
    last_sequence: int | None = None,
    now: datetime | None = None,
    authenticated_device_id: str | None = None,
) -> Telemetry:
    """Validate a telemetry payload before the digital twin may ingest it.

    The payload `device_id` is treated as telemetry data. The authoritative device
    identity comes from the authenticated certificate / Thing / registry context,
    which is passed in via `authenticated_device_id` when available.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    missing = REQUIRED_FIELDS - set(payload)
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ValueError(f"Missing required fields: {missing_fields}")

    if "connectivity_state" in payload:
        raise ValueError(
            "connectivity_state is server-derived and cannot be supplied by device telemetry"
        )

    device_id = payload["device_id"]
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be a non-empty string")

    if authenticated_device_id is not None:
        if not isinstance(authenticated_device_id, str) or not authenticated_device_id.strip():
            raise ValueError("authenticated_device_id must be a non-empty string")
        if device_id != authenticated_device_id:
            raise ValueError("device_id does not match the authenticated device identity")

    sequence = payload["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    if last_sequence is not None:
        if (
            isinstance(last_sequence, bool)
            or not isinstance(last_sequence, int)
            or last_sequence < 0
        ):
            raise ValueError("last_sequence must be a non-negative integer")
        if sequence <= last_sequence:
            raise ValueError("sequence is not greater than the last accepted value")

    accel_x = _as_float(payload["accel_x"], "accel_x")
    accel_y = _as_float(payload["accel_y"], "accel_y")
    accel_z = _as_float(payload["accel_z"], "accel_z")
    gyro_x = _as_float(payload["gyro_x"], "gyro_x")
    gyro_y = _as_float(payload["gyro_y"], "gyro_y")
    gyro_z = _as_float(payload["gyro_z"], "gyro_z")

    operating_state = payload["operating_state"]
    if operating_state == "OFFLINE":
        raise ValueError("OFFLINE is server-derived and cannot be self-reported by the device")
    if not isinstance(operating_state, str) or operating_state not in VALID_OPERATIONAL_STATES:
        raise ValueError("operating_state is not in the allowed device enum")

    timestamp = _validate_timestamp(payload["timestamp"], now=now)
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
