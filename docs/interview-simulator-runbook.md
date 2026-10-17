# Offline interview simulator rehearsal

Owner: Ted / repository maintainer. Synthetic local demonstration only.
Prerequisite: Python 3.12 and the existing repository verification environment;
there are no new runtime dependencies. Start from an isolated checkout to avoid
scanning unrelated ignored firmware/vendor artifacts in the existing workspace.

```bash
PYTHONPATH=src python -m business_app.simulate_grid --seed 17 --assets 5 --ticks 3 --reset-after 2
```

Read JSON lines in order: baseline totals (3 healthy, 1 warning, 1 critical),
asset-001 worsening because its preceding neighbor was critical, another tick,
then a local reset receipt with `applied: true`, `duplicate_applied: false`,
and the new epoch's baseline. The remaining tick reproduces the first progression.
These fields prove a local consumer reset, not cloud/device authorization or ACK.
The whole command exits without sleeping; 60 simulated seconds per tick is an
accelerated clock, not measured wall-clock latency or an interview timing claim.

Run twice with the same options and compare stdout byte-for-byte. Omit
`--reset-after` for a healthy normal progression without an explicit reset.
Use `--assets 50` only for local exploration; no capacity/cost benchmark is claimed.
CLI limits: 3–50 assets, 1–100 ticks, reset-after 1–ticks, seed 0–2**32-1.
Invalid options exit 2 before any state output. Domain runs stop at 1000 ticks;
reset starts a fresh generation. No automatic retries or retained history.

Recovery: run the command again from the documented seed/configuration; no durable
state exists to repair. Local reset clears counters/faults to the defined interview
baseline while preserving a monotonically advancing epoch during that process.
Do not feed this output into a live adapter. No AWS cost, rollout, teardown,
flash, UART or MQTT operation is part of this rehearsal.

Verification:

```bash
PYTHONPATH=src python -m pytest tests/test_grid_simulator.py
PYTHONPATH=src python scripts/check.py
```

The normal CI workflow already runs the complete gate and retains its reports.
Actual branch protection and completed CD are not established by this slice.

Next slices: review the narrative with Ted, add the opt-in debugging exercise using
this same consumer boundary, then design a dashboard and separately approved cloud
and physical-button application-ACK path. Physical LED validation remains pending.
