"""AWS integration boundaries for the prototype digital twin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from business_app.telemetry import Telemetry


@dataclass(frozen=True)
class AssetState:
    """Latest normalized state that is safe to surface in a TwinMaker asset view."""

    device_id: str
    operating_state: str
    sequence: int
    timestamp: str


@runtime_checkable
class IoTCoreAdapter(Protocol):
    """Boundary for the device ingress point into AWS IoT Core."""

    def publish(self, telemetry: Telemetry) -> None:
        """Accept a validated device payload for MQTT/topic routing."""


@runtime_checkable
class LatestStateStore(Protocol):
    """Latest-state persistence boundary used by the Lambda normalization step."""

    def upsert(self, state: AssetState) -> None:
        """Write the newest observed state for a device."""


@runtime_checkable
class TwinMakerAdapter(Protocol):
    """Boundary for projecting the accepted state into the digital twin view."""

    def sync_state(self, state: AssetState) -> None:
        """Publish the normalized asset state to the TwinMaker entity."""


def latest_state_from_telemetry(telemetry: Telemetry) -> AssetState:
    """Convert a validated telemetry event into the latest asset state for cloud adapters."""
    return AssetState(
        device_id=telemetry.device_id,
        operating_state=telemetry.operating_state,
        sequence=telemetry.sequence,
        timestamp=telemetry.timestamp,
    )
