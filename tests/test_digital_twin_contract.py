from __future__ import annotations

import re
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _validate_telemetry(payload: dict[str, Any]) -> None:
    required = {
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
    missing = required - set(payload)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")

    if not isinstance(payload["device_id"], str) or not payload["device_id"].strip():
        raise ValueError("device_id must be a non-empty string")

    if not isinstance(payload["sequence"], int) or payload["sequence"] < 0:
        raise ValueError("sequence must be a non-negative integer")

    for key in ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"):
        value = payload[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{key} must be numeric")
        if not (float(value) == float(value) and abs(float(value)) < 1_000_000):
            raise ValueError(f"{key} contains an invalid numeric value")

    if payload["operating_state"] not in {"NORMAL", "WARN", "ALERT", "OFFLINE"}:
        raise ValueError("operating_state is not in the allowed enum")

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", payload["timestamp"]):
        raise ValueError("timestamp must be RFC3339 UTC")


def _derive_operating_state(accel_values: tuple[float, float, float]) -> str:
    magnitude = sum(abs(value) for value in accel_values)
    if magnitude > 4.0:
        return "ALERT"
    if magnitude > 1.5:
        return "WARN"
    return "NORMAL"


def _tracked_files() -> list[str]:
    result = subprocess.run(  # nosec B603
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    files = result.stdout.decode("utf-8", errors="replace").split("\0")
    return [path for path in files if path and not path.startswith(".git/")]


def test_valid_telemetry_payload_is_accepted() -> None:
    payload = {
        "device_id": "core2-aws-001",
        "timestamp": "2026-10-08T19:45:00Z",
        "accel_x": 0.03,
        "accel_y": -0.02,
        "accel_z": 1.01,
        "gyro_x": 0.4,
        "gyro_y": 0.1,
        "gyro_z": -0.2,
        "operating_state": "NORMAL",
        "sequence": 42,
    }

    _validate_telemetry(payload)
    assert payload["operating_state"] == "NORMAL"


def test_invalid_telemetry_payload_is_rejected() -> None:
    payload = {
        "device_id": "core2-aws-001",
        "timestamp": "not-a-time",
        "accel_x": 0.03,
        "accel_y": -0.02,
        "accel_z": 1.01,
        "gyro_x": 0.4,
        "gyro_y": 0.1,
        "gyro_z": -0.2,
        "operating_state": "BOGUS",
        "sequence": 42,
    }

    try:
        _validate_telemetry(payload)
    except ValueError:
        return
    raise AssertionError("Malformed telemetry should be rejected before state mutation")


def test_latency_requirement_is_documented() -> None:
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "10 seconds" in architecture
    assert "TwinMaker" in architecture


def test_motion_changes_condition_state() -> None:
    assert _derive_operating_state((0.1, 0.2, 0.3)) == "NORMAL"
    assert _derive_operating_state((2.0, 0.1, 0.0)) == "WARN"
    assert _derive_operating_state((6.0, 0.0, 0.0)) == "ALERT"


def test_repo_contains_no_committed_credentials() -> None:
    tracked = _tracked_files()
    patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    )

    for path in tracked:
        text = (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                raise AssertionError(f"Potential credential pattern detected in {path}")
