from __future__ import annotations

from dataclasses import replace

import pytest

from business_app.grid_simulator import AssetEvent, GridSimulator, GridStateView, SimulatorConfig


def consume(view: GridStateView, events: tuple[AssetEvent, ...]) -> None:
    for event in events:
        assert view.apply(event)


def test_seeded_replay_and_reset_replay() -> None:
    first = GridSimulator(SimulatorConfig(seed=17, asset_count=5))
    second = GridSimulator(SimulatorConfig(seed=17, asset_count=5))
    history = [first.step() for _ in range(12)]
    assert history == [second.step() for _ in range(12)]
    first.reset("replay", expected_epoch=1)
    replay = [first.step() for _ in range(12)]
    assert history == [tuple(replace(e, epoch=1) for e in batch) for batch in replay]
    assert GridSimulator(SimulatorConfig(seed=18)).step() != history[0]


def test_faults_persist_accumulate_and_affect_neighbor() -> None:
    simulator = GridSimulator(SimulatorConfig())
    baseline = simulator.snapshot()
    assert [e.severity for e in baseline].count(2) == 1
    assert [e.severity for e in baseline].count(1) == 1
    first = simulator.step()
    assert first[1].severity > baseline[1].severity  # Critical asset-000 affects its neighbor.
    assert sum(e.severity > 0 for e in first) > sum(e.severity > 0 for e in baseline)
    previous = first
    for _ in range(20):
        current = simulator.step()
        assert all(
            0 <= old.severity <= new.severity <= 2
            for old, new in zip(previous, current, strict=True)
        )
        assert all(
            new.sequence == old.sequence + 1 for old, new in zip(previous, current, strict=True)
        )
        previous = current
    assert all(e.severity == 2 for e in previous)


def test_neighbor_effect_uses_pre_tick_state() -> None:
    simulator = GridSimulator(SimulatorConfig(asset_count=5, seed=17))
    baseline = simulator.snapshot()
    first = simulator.step()
    # Seed 17 selects asset-004; no new critical asset propagates within this tick.
    assert [e.severity for e in baseline] == [2, 0, 1, 0, 0]
    assert [e.severity for e in first] == [2, 1, 1, 0, 1]


def test_reset_is_complete_and_duplicate_does_not_erase_progress() -> None:
    simulator = GridSimulator(SimulatorConfig())
    baseline = simulator.snapshot()
    view = GridStateView(simulator.config)
    consume(view, baseline)
    old = simulator.step()
    consume(view, old)
    receipt = simulator.reset("button-1", expected_epoch=1)
    assert receipt.previous_epoch == 1 and receipt.epoch == 2
    assert all(e.tick == 0 and e.sequence == 0 and e.epoch == 2 for e in simulator.snapshot())
    assert [e.severity for e in simulator.snapshot()] == [e.severity for e in baseline]
    assert view.reset(receipt)
    assert view.snapshot() == simulator.snapshot()
    consume(view, simulator.step())
    before = view.snapshot()
    assert simulator.reset("button-1", expected_epoch=1) == receipt
    assert not view.reset(receipt)
    assert view.snapshot() == before
    assert not view.apply(replace(old[0], sequence=999, tick=999))
    second = simulator.reset("button-2", expected_epoch=2)
    assert second.epoch == 3
    stable = simulator.snapshot()
    with pytest.raises(ValueError, match="epoch"):
        simulator.reset("button-1", expected_epoch=1)
    assert simulator.snapshot() == stable


def test_interleaved_assets_replay_and_epoch_isolation() -> None:
    simulator = GridSimulator(SimulatorConfig())
    view = GridStateView(simulator.config)
    events = simulator.step()
    assert view.apply(replace(events[0], sequence=10, tick=10))
    assert view.apply(events[1])  # A global sequence tracker would wrongly reject this.
    before = view.snapshot()
    assert not view.apply(events[0])
    assert not view.apply(events[1])
    assert not view.apply(replace(events[1], epoch=2, sequence=2, tick=2))
    assert not view.apply(replace(events[1], sequence=2, tick=0))
    assert not view.apply(replace(events[0], sequence=11, tick=11, severity=0))
    with pytest.raises(ValueError, match="asset"):
        view.apply(replace(events[0], asset_id="asset-999"))
    assert view.snapshot() == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("seed", -1),
        ("seed", 2**32),
        ("asset_count", 2),
        ("asset_count", 51),
        ("asset_count", 3.5),
    ],
)
def test_config_bounds(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        SimulatorConfig(**{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("epoch", 0),
        ("sequence", True),
        ("tick", -1),
        ("severity", 3),
        ("severity", float("nan")),
        ("asset_id", ""),
        ("asset_id", "../asset-000"),
    ],
)
def test_event_validation(field: str, value: object) -> None:
    event = GridSimulator(SimulatorConfig()).snapshot()[0]
    with pytest.raises(ValueError):
        replace(event, **{field: value})


@pytest.mark.parametrize("command", ["", "x" * 65, "spaces forbidden", "é"])
def test_invalid_reset_never_mutates(command: str) -> None:
    simulator = GridSimulator(SimulatorConfig())
    before = simulator.step()
    with pytest.raises(ValueError):
        simulator.reset(command, expected_epoch=1)
    assert simulator.snapshot() == before


def test_wrong_reset_epoch_and_tick_limit_fail_without_mutation() -> None:
    simulator = GridSimulator(SimulatorConfig())
    with pytest.raises(ValueError, match="epoch"):
        simulator.reset("bad", expected_epoch=True)
    for _ in range(1000):
        simulator.step()
    before = simulator.snapshot()
    with pytest.raises(ValueError, match="tick"):
        simulator.step()
    assert simulator.snapshot() == before


def test_offline_terminal_rehearsal(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    from business_app.simulate_grid import main

    assert main(["--ticks", "3", "--reset-after", "2"]) == 0
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(r["source"] == "synthetic-local" for r in records)
    assert [r["epoch"] for r in records if r["kind"] == "state"] == [1, 1, 1, 2, 2]
    reset = next(r for r in records if r["kind"] == "reset")
    assert reset["applied"] and not reset["duplicate_applied"]
    assert records[0]["totals"] == {"HEALTHY": 3, "WARNING": 1, "CRITICAL": 1}
    assert records[1]["assets"][1]["condition"] == "WARNING"
    assert records[-1]["tick"] == 1


@pytest.mark.parametrize(
    "arguments", [["--assets", "51"], ["--ticks", "0"], ["--ticks", "101"], ["--reset-after", "4"]]
)
def test_invalid_cli_has_no_partial_output(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    from business_app.simulate_grid import main

    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    assert capsys.readouterr().out == ""


def test_snapshot_is_immutable_and_reset_receipt_validation() -> None:
    from dataclasses import FrozenInstanceError

    from business_app.grid_simulator import ResetReceipt

    simulator = GridSimulator(SimulatorConfig())
    event = simulator.snapshot()[0]
    with pytest.raises(FrozenInstanceError):
        event.severity = 0
    with pytest.raises(ValueError):
        ResetReceipt("bad", 1, 3)
    view = GridStateView(simulator.config)
    with pytest.raises(ValueError, match="epoch"):
        view.reset(ResetReceipt("future", 2, 3))
    assert view.snapshot() == ()


@pytest.mark.parametrize("count", [3, 50])
def test_supported_fleet_sizes_replay_and_reset(count: int) -> None:
    config = SimulatorConfig(asset_count=count)
    source = GridSimulator(config)
    view = GridStateView(config)
    consume(view, source.snapshot())
    for _ in range(3):
        consume(view, source.step())
    first = source.reset("first", expected_epoch=1)
    assert view.reset(first)
    second = source.reset("second", expected_epoch=2)
    assert view.reset(second)
    assert view.snapshot() == source.snapshot()
    before = view.snapshot()
    with pytest.raises(ValueError, match="epoch"):
        view.reset(first)
    assert view.snapshot() == before
    assert len(before) == count


def test_combined_faults_cap_at_critical() -> None:
    # Seed 1 selects the healthy neighbor of the initial critical asset.
    source = GridSimulator(SimulatorConfig(seed=1))
    assert source.step()[1].severity == 2


@pytest.mark.parametrize("sequence,tick", [(2, 1), (1, 2), (0, 1), (1, 0)])
def test_consumer_rejects_sequence_tick_mismatch_without_mutation(sequence: int, tick: int) -> None:
    source = GridSimulator(SimulatorConfig())
    view = GridStateView(source.config)
    event = source.snapshot()[1]
    invalid = replace(event, sequence=sequence, tick=tick)
    # Enforce the contract even before this asset has a previous observation.
    assert not view.apply(invalid)
    assert view.snapshot() == ()
    consume(view, source.snapshot())
    before = view.snapshot()
    assert not view.apply(invalid)
    assert view.snapshot() == before


def test_consumer_accepts_skipped_ticks_and_independent_assets() -> None:
    source = GridSimulator(SimulatorConfig())
    view = GridStateView(source.config)
    consume(view, source.snapshot())
    first = source.step()
    source.step()
    third = source.step()
    assert view.apply(third[0])
    assert view.apply(first[1])
    assert not view.apply(first[0])
    assert view.apply(third[1])
    assert all(e.sequence == e.tick for e in view.snapshot())
