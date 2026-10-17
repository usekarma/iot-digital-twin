"""Bounded offline terminal rehearsal: python -m business_app.simulate_grid."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from business_app.grid_simulator import GridSimulator, GridStateView, SimulatorConfig


def _show(view: GridStateView) -> None:
    events = view.snapshot()
    print(
        json.dumps(
            {
                "source": "synthetic-local",
                "kind": "state",
                "epoch": events[0].epoch,
                "tick": events[0].tick,
                "simulated_seconds": events[0].simulated_seconds,
                "totals": {
                    condition: sum(e.condition == condition for e in events)
                    for condition in ("HEALTHY", "WARNING", "CRITICAL")
                },
                "assets": [asdict(event) | {"condition": event.condition} for event in events],
            },
            sort_keys=True,
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Emit a finite synthetic history and optionally demonstrate a duplicate reset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--assets", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--reset-after", type=int, help="Reset after this many emitted ticks")
    parser.add_argument("--trace", action="store_true", help="Include synthetic rule evidence")
    args = parser.parse_args(argv)
    try:
        config = SimulatorConfig(seed=args.seed, asset_count=args.assets)
        if not 1 <= args.ticks <= 100:
            raise ValueError("ticks must be in [1, 100]")
        if args.reset_after is not None and not 1 <= args.reset_after <= args.ticks:
            raise ValueError("reset-after must be in [1, ticks]")
    except ValueError as exc:
        parser.error(str(exc))
    simulator = GridSimulator(config)
    view = GridStateView(config)
    for event in simulator.snapshot():
        view.apply(event)
    _show(view)
    for index in range(1, args.ticks + 1):
        trace = simulator.step_traced() if args.trace else None
        events = trace.observations if trace is not None else simulator.step()
        for event in events:
            view.apply(event)
        _show(view)
        if trace is not None:
            print(
                json.dumps(
                    {
                        "source": "synthetic-local",
                        "kind": "trace",
                        "trace": asdict(trace),
                        "explanation": trace.explain("asset-001"),
                    },
                    sort_keys=True,
                )
            )
        if index == args.reset_after:
            receipt = simulator.reset("local-demo-reset", expected_epoch=simulator.epoch)
            applied = view.reset(receipt)
            duplicate = simulator.reset(receipt.command_id, expected_epoch=receipt.previous_epoch)
            print(
                json.dumps(
                    {
                        "source": "synthetic-local",
                        "kind": "reset",
                        "receipt": asdict(receipt),
                        "applied": applied,
                        "duplicate_applied": view.reset(duplicate),
                    },
                    sort_keys=True,
                )
            )
            _show(view)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
