"""Deterministic synthetic degradation and an offline current-state consumer."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from business_app.transition_trace import (
    Disturbance,
    PropagatedEffect,
    StateTransition,
    TickTrace,
)

MAX_TICKS = 1000
MAX_EPOCH = 1_000_000
TICK_SECONDS = 60


def _integer(value: object, name: str, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")


@dataclass(frozen=True)
class SimulatorConfig:
    """Small, bounded interview preset; no live asset or credential configuration."""

    seed: int = 17
    asset_count: int = 5

    def __post_init__(self) -> None:
        _integer(self.seed, "seed", 0, 2**32 - 1)
        _integer(self.asset_count, "asset_count", 3, 50)

    @property
    def asset_ids(self) -> tuple[str, ...]:
        """Return stable ring order."""
        return tuple(f"asset-{index:03d}" for index in range(self.asset_count))


@dataclass(frozen=True)
class AssetEvent:
    """Validated synthetic event, never evidence of physical equipment behavior."""

    asset_id: str
    epoch: int
    sequence: int
    tick: int
    severity: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.asset_id, str)
            or re.fullmatch(r"asset-[0-9]{3}", self.asset_id) is None
        ):
            raise ValueError("asset_id must have the form asset-000")
        _integer(self.epoch, "epoch", 1, MAX_EPOCH)
        _integer(self.sequence, "sequence", 0, MAX_TICKS)
        _integer(self.tick, "tick", 0, MAX_TICKS)
        _integer(self.severity, "severity", 0, 2)

    @property
    def condition(self) -> str:
        """Return the presentation label for a validated severity."""
        return ("HEALTHY", "WARNING", "CRITICAL")[self.severity]

    @property
    def simulated_seconds(self) -> int:
        """Return accelerated elapsed time, independent of the wall clock."""
        return self.tick * TICK_SECONDS


@dataclass(frozen=True)
class ResetReceipt:
    """Local application result, not a device or cloud acknowledgment."""

    command_id: str
    previous_epoch: int
    epoch: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.command_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.command_id) is None
        ):
            raise ValueError("command_id must contain 1–64 ASCII letters/digits/underscore/hyphen")
        _integer(self.previous_epoch, "previous_epoch", 1, MAX_EPOCH - 1)
        _integer(self.epoch, "epoch", 2, MAX_EPOCH)
        if self.epoch != self.previous_epoch + 1:
            raise ValueError("reset epoch must advance exactly once")


def _baseline(config: SimulatorConfig) -> list[int]:
    values = [0] * config.asset_count
    values[0] = 2
    values[config.asset_count // 2] = 1
    return values


class GridSimulator:
    """Single-threaded, process-local simulation with bounded reset deduplication."""

    def __init__(self, config: SimulatorConfig) -> None:
        self._config = config
        self._epoch = 1
        self._tick = 0
        self._severity = _baseline(config)
        # Reproducible synthetic hazards only, never security tokens or live identities.
        self._random = random.Random(config.seed)  # nosec B311
        self._last_reset: ResetReceipt | None = None

    @property
    def config(self) -> SimulatorConfig:
        """Expose immutable configuration."""
        return self._config

    @property
    def epoch(self) -> int:
        """Return the active local rehearsal generation."""
        return self._epoch

    def snapshot(self) -> tuple[AssetEvent, ...]:
        """Read current state without advancing ticks, sequences or randomness."""
        return tuple(
            AssetEvent(asset_id, self._epoch, self._tick, self._tick, severity)
            for asset_id, severity in zip(self.config.asset_ids, self._severity, strict=True)
        )

    def step(self) -> tuple[AssetEvent, ...]:
        """Advance normally without allocating trace records."""
        return self._advance(tracing=False)[0]

    def step_traced(self) -> TickTrace:
        """Advance once and return immutable evidence of that calculation."""
        _, trace = self._advance(tracing=True)
        if trace is None:
            raise RuntimeError("traced advancement did not return execution evidence")
        return trace

    def _advance(self, *, tracing: bool) -> tuple[tuple[AssetEvent, ...], TickTrace | None]:
        if self._tick == MAX_TICKS:
            raise ValueError("tick limit reached; reset to start a new bounded run")
        before = self.snapshot() if tracing else ()
        selected = self._random.randrange(self.config.asset_count)
        increments = [0] * self.config.asset_count
        increments[selected] += 1
        effects = []
        for index, severity in enumerate(self._severity):
            if severity == 2:
                target = (index + 1) % self.config.asset_count
                increments[target] += 1
                if tracing:
                    effects.append(
                        PropagatedEffect(before[index], self.config.asset_ids[target], 1)
                    )
        self._severity = [
            min(2, severity + increment)
            for severity, increment in zip(self._severity, increments, strict=True)
        ]
        self._tick += 1
        observations = self.snapshot()
        if not tracing:
            return observations, None
        disturbance = Disturbance(self._epoch, self._tick - 1, self.config.asset_ids[selected], 1)
        transitions = tuple(
            StateTransition(
                old,
                new,
                int(index == selected),
                increments[index] - int(index == selected),
                old.severity + increments[index],
            )
            for index, (old, new) in enumerate(zip(before, observations, strict=True))
        )
        return observations, TickTrace(
            before, disturbance, tuple(effects), transitions, observations
        )

    def reset(self, command_id: str, *, expected_epoch: int) -> ResetReceipt:
        """Restore baseline once; stale commands never reset newer progress."""
        _integer(expected_epoch, "expected_epoch", 1, MAX_EPOCH - 1)
        candidate = ResetReceipt(command_id, expected_epoch, expected_epoch + 1)
        if candidate == self._last_reset:
            return candidate
        if expected_epoch != self._epoch:
            raise ValueError("reset expected_epoch does not match active epoch")
        self._epoch = candidate.epoch
        self._tick = 0
        self._severity = _baseline(self.config)
        self._random.seed(self.config.seed)
        self._last_reset = candidate
        return candidate


class GridStateView:
    """In-memory ingestion/query boundary; not durable, concurrent or authenticated."""

    def __init__(self, config: SimulatorConfig) -> None:
        self._asset_ids = config.asset_ids
        self._epoch = 1
        self._states: dict[str, AssetEvent] = {}
        self._last_reset: ResetReceipt | None = None

    def apply(self, event: AssetEvent) -> bool:
        """Accept per-tick observations; reject invalid ordering without mutation."""
        if event.asset_id not in self._asset_ids:
            raise ValueError("unknown asset_id")
        if event.epoch != self._epoch or event.sequence != event.tick:
            return False
        previous = self._states.get(event.asset_id)
        if previous is not None and (
            event.sequence <= previous.sequence
            or event.tick < previous.tick
            or event.severity < previous.severity
        ):
            return False
        self._states[event.asset_id] = event
        return True

    def snapshot(self) -> tuple[AssetEvent, ...]:
        """Return immutable latest events in configured asset order."""
        return tuple(self._states[key] for key in self._asset_ids if key in self._states)

    def reset(self, receipt: ResetReceipt) -> bool:
        """Apply a local reset receipt once and load its known baseline atomically."""
        if receipt == self._last_reset:
            return False
        if receipt.previous_epoch != self._epoch:
            raise ValueError("reset receipt does not match active epoch")
        baseline = _baseline(SimulatorConfig(asset_count=len(self._asset_ids)))
        states = {
            key: AssetEvent(key, receipt.epoch, 0, 0, severity)
            for key, severity in zip(self._asset_ids, baseline, strict=True)
        }
        self._states = states
        self._epoch = receipt.epoch
        self._last_reset = receipt
        return True
