"""Bounded synthetic MQTT experiment; transport and pacing are injected."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict

from business_app.grid_simulator import GridSimulator, SimulatorConfig

TOPIC = "adage/iot-digital-twin/operational-demo/asset-000/telemetry"


def envelopes(run_id: str, start_seconds: int) -> list[dict[str, object]]:
    """Build exactly twenty immutable-model observations using real time metadata."""
    if re.fullmatch(r"[0-9a-f]{32}", run_id) is None:
        raise ValueError("invalid run ID")
    if isinstance(start_seconds, bool) or not isinstance(start_seconds, int) or start_seconds < 0:
        raise ValueError("invalid start time")
    simulator = GridSimulator(SimulatorConfig())
    result: list[dict[str, object]] = []
    for index in range(20):
        event = simulator.step()[0]
        observation = asdict(event)
        result.append(
            observation
            | {
                "schema_version": 1,
                "synthetic": True,
                "run_id": run_id,
                "event_time_seconds": start_seconds + index,
                "event_time_nanos": 0,
                "observation": observation,
            }
        )
    return result


def publish_run(
    packets: list[dict[str, object]],
    publish: Callable[[str, bytes], None],
    sleep: Callable[[float], None],
) -> None:
    """Publish fixed packets once; stop on failure rather than hiding lost points."""
    if len(packets) != 20:
        raise ValueError("exactly twenty packets required")
    first = packets[0]
    run_id, start = first.get("run_id"), first.get("event_time_seconds")
    if not isinstance(run_id, str) or type(start) is not int:
        raise ValueError("invalid envelope metadata")
    for packet in packets:
        if any(
            type(packet.get(k)) is not int
            for k in (
                "epoch",
                "sequence",
                "tick",
                "severity",
                "event_time_seconds",
                "event_time_nanos",
                "schema_version",
            )
        ):
            raise ValueError("integer fields must not be booleans")
    if packets != envelopes(run_id, start):
        raise ValueError("invalid or modified observation run")
    for index, packet in enumerate(packets):
        if index:
            sleep(1.0)
        publish(TOPIC, json.dumps(packet, sort_keys=True, separators=(",", ":")).encode())
