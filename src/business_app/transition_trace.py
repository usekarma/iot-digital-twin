"""Immutable evidence of synthetic rule execution, not causal inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from business_app.grid_simulator import AssetEvent


@dataclass(frozen=True)
class Disturbance:
    """The single seeded selection at a source tick."""

    epoch: int
    source_tick: int
    asset_id: str
    contribution: int


@dataclass(frozen=True)
class PropagatedEffect:
    """A consequence of the exact predecessor observation read by the rule."""

    predecessor: AssetEvent
    target_asset_id: str
    contribution: int


@dataclass(frozen=True)
class StateTransition:
    """Inputs and capped result for one asset, including unchanged states."""

    before: AssetEvent
    after: AssetEvent
    disturbance: int
    propagated: int
    uncapped_severity: int


@dataclass(frozen=True)
class TickTrace:
    """One bounded tick; callers explicitly decide whether to retain history."""

    before: tuple[AssetEvent, ...]
    disturbance: Disturbance
    effects: tuple[PropagatedEffect, ...]
    transitions: tuple[StateTransition, ...]
    observations: tuple[AssetEvent, ...]

    def explain(self, asset_id: str) -> str:
        """Render recorded arithmetic and causes using a fixed template."""
        transition = next((t for t in self.transitions if t.before.asset_id == asset_id), None)
        if transition is None:
            raise ValueError("asset_id is absent from this trace")
        causes = []
        if transition.disturbance:
            causes.append(f"seeded disturbance selected {asset_id} (+1)")
        for effect in self.effects:
            if effect.target_asset_id == asset_id:
                predecessor = effect.predecessor
                causes.append(
                    f"{predecessor.asset_id} was {predecessor.condition} "
                    f"(severity {predecessor.severity}) at tick {predecessor.tick} (+1)"
                )
        cause_text = "; ".join(causes) if causes else "no disturbance or propagated effect"
        before, after = transition.before, transition.after
        return (
            f"{asset_id}, epoch {before.epoch}, tick {before.tick} -> {after.tick}: "
            f"{before.condition} -> {after.condition}. {cause_text}. "
            f"min(2, {before.severity} + {transition.disturbance} + "
            f"{transition.propagated}) = {after.severity}; "
            f"uncapped severity {transition.uncapped_severity}."
        )
