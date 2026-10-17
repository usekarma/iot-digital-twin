import pytest
from durable_demo_reference import Command, Store, Worker


def test_tick_reset_race_both_orders_and_expired_worker():
    store = Store()
    assert store.acquire("worker-a", 0)
    pending = store.state
    store.reset(Command("session-a", "reset", 1), 1)
    assert not store.tick(pending, 2)
    assert store.state.epoch == 2 and store.state.tick == 0
    assert store.tick(store.state, 4)
    with pytest.raises(RuntimeError, match="conflict"):
        store.reset(Command("session-a", "reset-2", 2), 5, expected_revision=pending.revision)
    store.reset(Command("session-a", "reset-2", 2), 5, expected_revision=store.state.revision)
    assert store.state.epoch == 3 and store.state.tick == 0
    old = store.state
    assert store.acquire("worker-b", 11)
    assert not store.tick(old, 12)
    assert store.state.fence > old.fence


def test_restart_replay_bounds_and_lost_tick_response():
    store = Store()
    assert store.acquire("a", 0)
    before = store.state
    assert store.tick(before, 0)
    assert not store.tick(before, 1)  # Commit response lost; no second advancement.
    assert Worker(store).recover() == Worker(store).recover()
    assert not store.tick(store.state, 1)  # Not yet due.
    for now in (3, 6, 9, 12, 15):
        if now >= store.state.lease_until:
            assert store.acquire("replacement", now)
        assert store.tick(store.state, now)
    assert store.state.tick == 6
    assert not store.tick(store.state, 18)
    assert not store.acquire("late", 180)
    store.reset(Command("session-a", "reset", 1), 17)
    assert store.state.deadline == 180
    events, trace = Worker(store).recover()
    assert trace is None and all(e.epoch == 2 and e.sequence == 0 for e in events)


def test_reset_deduplication_stale_sessions_and_conflicts():
    store = Store()
    command = Command("session-a", "reset", 1)
    ack = store.reset(command, 0)
    state = store.state
    assert store.reset(command, 1) == ack and store.state == state
    for invalid in (
        Command("session-a", "reset", 2),
        Command("old-session", "reset", 1),
        Command("session-a", "new-id", 1),
        Command("session-a", "reset", 1, "forged"),
    ):
        with pytest.raises(ValueError):
            store.reset(invalid, 1)
        assert store.state == state
    with pytest.raises(ValueError):
        store.reset(command, 180)
    for epoch in (2, 3):
        store.reset(Command("session-a", f"reset-{epoch}", epoch), 2)
    with pytest.raises(ValueError):
        store.reset(Command("session-a", "fourth", 4), 3)


def test_ack_after_commit_lost_ack_and_bounded_retry():
    store = Store()
    command = Command("session-a", "reset", 1)
    with pytest.raises(RuntimeError):
        store.reset(command, 0, fail_transaction=True)
    assert store.state.epoch == 1 and not store.receipts
    assert store.publish("reset", 0, True) is None
    ack = store.reset(command, 0)
    assert store.state.epoch == ack.committed_epoch == 2
    assert store.publish("reset", 1, False) is None
    restarted = Worker(store)
    assert restarted.store.publish("reset", 2, True) == ack
    assert store.reset(command, 3) == ack
    assert store.publish("reset", 3, True) == ack  # Duplicate ACK, not another reset.
    assert store.publish("reset", 4, True) is None
    assert store.state.epoch == 2 and store.attempts["reset"] == 3


def test_recovery_trace_uses_durable_epoch_and_device_correlation():
    from dataclasses import replace

    from business_app.grid_simulator import GridSimulator, SimulatorConfig

    store = Store()
    assert store.acquire("a", 0)
    command = Command("session-a", "reset", 1)
    ack = store.reset(command, 0)
    assert store.tick(store.state, 3)
    events, trace = Worker(store).recover()
    assert trace.observations == events
    assert all(e.epoch == 2 for e in trace.before + trace.observations)
    assert all(e.predecessor.epoch == 2 for e in trace.effects)
    assert all(t.before.epoch == t.after.epoch == 2 for t in trace.transitions)
    initial = GridSimulator(SimulatorConfig()).step_traced()
    assert [e.severity for e in events] == [e.severity for e in initial.observations]
    assert trace.disturbance == replace(initial.disturbance, epoch=2)
    assert ack.command == command and ack.committed_epoch == command.expected_epoch + 1
    assert ack.command != replace(command, session="old-session")
    assert ack.command != replace(command, command_id="wrong-id")
