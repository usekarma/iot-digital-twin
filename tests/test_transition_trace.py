from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock

import pytest

from business_app.grid_simulator import GridSimulator, SimulatorConfig


def test_trace_matches_untraced_replay_and_reset() -> None:
    normal = GridSimulator(SimulatorConfig())
    traced = GridSimulator(SimulatorConfig())
    replay = GridSimulator(SimulatorConfig())
    for _ in range(10):
        trace = traced.step_traced()
        assert trace == replay.step_traced()
        assert trace.observations == normal.step()
    receipt = traced.reset("reset", expected_epoch=1)
    normal.reset("reset", expected_epoch=1)
    replay.reset("reset", expected_epoch=1)
    first = traced.step_traced()
    assert first.observations == normal.step()
    assert first == replay.step_traced()
    assert traced.reset("reset", expected_epoch=1) == receipt
    assert traced.snapshot() == first.observations
    initial = GridSimulator(SimulatorConfig()).step_traced()
    assert first.disturbance == replace(initial.disturbance, epoch=2)
    assert first.before == tuple(replace(e, epoch=2) for e in initial.before)


def test_trace_arithmetic_predecessors_and_saturation() -> None:
    simulator = GridSimulator(SimulatorConfig(seed=1))
    combined = False
    saturated = False
    for _ in range(10):
        trace = simulator.step_traced()
        assert trace.disturbance.source_tick == trace.before[0].tick
        assert trace.disturbance.epoch == trace.before[0].epoch
        assert trace.disturbance.contribution == 1
        for index, transition in enumerate(trace.transitions):
            predecessor = trace.before[(index - 1) % len(trace.before)]
            assert transition.before == trace.before[index]
            assert transition.after == trace.observations[index]
            assert transition.disturbance == int(
                transition.before.asset_id == trace.disturbance.asset_id
            )
            assert transition.propagated == int(predecessor.severity == 2)
            assert (
                transition.uncapped_severity
                == transition.before.severity + transition.disturbance + transition.propagated
            )
            assert transition.after.severity == min(2, transition.uncapped_severity)
            effects = [e for e in trace.effects if e.target_asset_id == transition.before.asset_id]
            assert len(effects) == transition.propagated
            if effects:
                assert effects[0].predecessor == predecessor
                assert effects[0].contribution == 1
            combined |= bool(transition.disturbance and transition.propagated)
            if transition.uncapped_severity > 2:
                explanation = trace.explain(transition.before.asset_id)
                assert f"uncapped severity {transition.uncapped_severity}" in explanation
                assert (
                    f"min(2, {transition.before.severity} + {transition.disturbance} + "
                    f"{transition.propagated}) = 2" in explanation
                )
            saturated |= transition.uncapped_severity > 2
    assert combined and saturated


def test_explanation_matches_recorded_progression() -> None:
    simulator = GridSimulator(SimulatorConfig())
    first = simulator.step_traced()
    second = simulator.step_traced()
    assert first.explain("asset-001") == (
        "asset-001, epoch 1, tick 0 -> 1: HEALTHY -> WARNING. "
        "asset-000 was CRITICAL (severity 2) at tick 0 (+1). "
        "min(2, 0 + 0 + 1) = 1; uncapped severity 1."
    )
    assert "WARNING -> CRITICAL" in second.explain("asset-001")
    assert "at tick 1 (+1)" in second.explain("asset-001")
    assert "min(2, 1 + 0 + 1) = 2" in second.explain("asset-001")
    assert "no disturbance or propagated effect" in first.explain("asset-003")
    both = GridSimulator(SimulatorConfig(seed=1)).step_traced().explain("asset-001")
    assert "seeded disturbance selected asset-001 (+1)" in both
    assert "asset-000 was CRITICAL" in both
    assert "min(2, 0 + 1 + 1) = 2" in both
    with pytest.raises(ValueError):
        first.explain("asset-999")
    with pytest.raises(FrozenInstanceError):
        first.disturbance.contribution = 9


def test_one_random_draw_and_no_same_tick_cascade() -> None:
    simulator = GridSimulator(SimulatorConfig(seed=1))
    draw = Mock(wraps=simulator._random.randrange)
    simulator._random.randrange = draw
    trace = simulator.step_traced()
    draw.assert_called_once_with(5)
    assert trace.observations[1].severity == 2
    assert not any(e.predecessor.asset_id == "asset-001" for e in trace.effects)
    simulator.step()
    assert draw.call_count == 2


def test_cli_tracing_is_opt_in_and_preserves_state_output(capsys) -> None:
    import json

    from business_app.simulate_grid import main

    main(["--ticks", "3", "--reset-after", "2"])
    normal = capsys.readouterr().out.splitlines()
    main(["--ticks", "3", "--reset-after", "2", "--trace"])
    traced = capsys.readouterr().out.splitlines()
    assert [line for line in traced if json.loads(line)["kind"] != "trace"] == normal
    assert len([line for line in traced if json.loads(line)["kind"] == "trace"]) == 3


def test_traced_tick_limit_preserves_state_and_randomness() -> None:
    from business_app.grid_simulator import MAX_TICKS

    simulator = GridSimulator(SimulatorConfig())
    for _ in range(MAX_TICKS):
        simulator.step()
    before = simulator.snapshot()
    random_state = simulator._random.getstate()
    with pytest.raises(ValueError, match="tick"):
        simulator.step_traced()
    assert simulator.snapshot() == before
    assert simulator._random.getstate() == random_state
