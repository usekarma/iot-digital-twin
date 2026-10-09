from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from business_app.adapters import AssetState, latest_state_from_telemetry
from business_app.telemetry import (
    MAX_CLOCK_SKEW_SECONDS,
    VALID_OPERATIONAL_STATES,
    Telemetry,
    derive_operating_state,
    validate_telemetry,
)

ROOT = Path(__file__).resolve().parents[1]
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


def test_valid_telemetry_payload_is_accepted() -> None:
    telemetry = validate_telemetry(VALID_PAYLOAD)

    assert isinstance(telemetry, Telemetry)
    assert telemetry.device_id == "core2-aws-001"
    assert telemetry.operating_state in VALID_OPERATIONAL_STATES
    assert telemetry.to_asset_state()["operating_state"] == "NORMAL"


def test_invalid_telemetry_payload_is_rejected() -> None:
    with pytest.raises((TypeError, ValueError), match="timestamp"):
        validate_telemetry({**VALID_PAYLOAD, "timestamp": "not-a-time"})

    with pytest.raises((TypeError, ValueError), match="sequence"):
        validate_telemetry({**VALID_PAYLOAD, "sequence": 41}, last_sequence=42)


def test_latency_requirement_is_documented() -> None:
    assert MAX_CLOCK_SKEW_SECONDS == 10
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "10 seconds" in architecture
    assert "TwinMaker" in architecture


def test_motion_changes_condition_state() -> None:
    assert derive_operating_state((0.1, 0.2, 0.3)) == "NORMAL"
    assert derive_operating_state((2.0, 0.1, 0.0)) == "WARN"
    assert derive_operating_state((6.0, 0.0, 0.0)) == "ALERT"

    state = latest_state_from_telemetry(
        validate_telemetry({**VALID_PAYLOAD, "accel_x": 6.0, "operating_state": "ALERT"})
    )
    assert isinstance(state, AssetState)
    assert state.operating_state == "ALERT"


def test_repo_contains_no_committed_credentials() -> None:
    patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    )

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                raise AssertionError(f"Potential credential pattern detected in {path}")
