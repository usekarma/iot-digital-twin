"""Test-only executable contract; not a DynamoDB adapter or deployable runtime."""

from dataclasses import dataclass, replace

from business_app.grid_simulator import GridSimulator, SimulatorConfig


@dataclass(frozen=True)
class State:
    session: str = "session-a"
    epoch: int = 1
    tick: int = 0
    revision: int = 0
    deadline: int = 180
    owner: str = ""
    lease_until: int = 0
    fence: int = 0
    next_tick: int = 0


@dataclass(frozen=True)
class Command:
    session: str
    command_id: str
    expected_epoch: int
    principal: str = "trusted-fixture"


@dataclass(frozen=True)
class Ack:
    command: Command
    committed_epoch: int


class Store:
    """Shared fake storage survives Worker replacement, not process termination."""

    def __init__(self):
        self.state = State()
        self.receipts = {}
        self.attempts = {}

    def acquire(self, owner, now):
        s = self.state
        if now >= s.deadline or s.lease_until > now:
            return False
        self.state = replace(
            s,
            owner=owner,
            lease_until=min(now + 10, s.deadline),
            fence=s.fence + 1,
            revision=s.revision + 1,
        )
        return True

    def tick(self, snapshot, now):
        if (
            snapshot != self.state
            or now >= snapshot.lease_until
            or now >= snapshot.deadline
            or now < snapshot.next_tick
            or snapshot.tick >= 6
        ):
            return False
        self.state = replace(
            snapshot, tick=snapshot.tick + 1, revision=snapshot.revision + 1, next_tick=now + 3
        )
        return True

    def reset(self, command, now, fail_transaction=False, expected_revision=None):
        s = self.state
        if (
            command.session != s.session
            or command.principal != "trusted-fixture"
            or now >= s.deadline
        ):
            raise ValueError("inactive session/identity")
        existing = self.receipts.get(command.command_id)
        if existing:
            if existing.command != command:
                raise ValueError("conflicting command")
            return existing
        if command.expected_epoch != s.epoch or len(self.receipts) >= 3:
            raise ValueError("stale epoch/command limit")
        if expected_revision is not None and expected_revision != s.revision:
            raise RuntimeError("revision conflict")
        if fail_transaction:
            raise RuntimeError("transaction failed")
        ack = Ack(command, s.epoch + 1)
        updated = replace(s, epoch=s.epoch + 1, tick=0, revision=s.revision + 1, next_tick=now + 3)
        self.state, self.receipts = updated, self.receipts | {command.command_id: ack}
        self.attempts[command.command_id] = 0
        return ack

    def publish(self, command_id, now, delivered):
        if (
            now >= self.state.deadline
            or command_id not in self.receipts
            or self.attempts[command_id] >= 3
        ):
            return None
        self.attempts[command_id] += 1
        return self.receipts[command_id] if delivered else None


class Worker:
    def __init__(self, store):
        self.store = store

    def recover(self):
        simulator = GridSimulator(SimulatorConfig())
        trace = None
        for _ in range(self.store.state.tick):
            trace = simulator.step_traced()
        observations = tuple(replace(e, epoch=self.store.state.epoch) for e in simulator.snapshot())
        epoch = self.store.state.epoch
        if trace is not None:
            trace = replace(
                trace,
                before=tuple(replace(e, epoch=epoch) for e in trace.before),
                disturbance=replace(trace.disturbance, epoch=epoch),
                effects=tuple(
                    replace(e, predecessor=replace(e.predecessor, epoch=epoch))
                    for e in trace.effects
                ),
                transitions=tuple(
                    replace(
                        t,
                        before=replace(t.before, epoch=epoch),
                        after=replace(t.after, epoch=epoch),
                    )
                    for t in trace.transitions
                ),
                observations=observations,
            )
        return observations, trace
