# Offline interview simulator — Issue #17, first slice

Status: local prototype proposal; independent of the Core2 AC-101–AC-105 experiment.
Stakeholder: Ted, preparing a reliable one-minute interview demonstration.
Baseline: no reproducible fleet simulation. Target: a deterministic terminal rehearsal
that shows accumulating faults, a neighbor consequence, and a verified local reset.

## Contract and deliberate shortcuts

Python 3.12, standard library, in-memory state, no network, MQTT, credentials or device I/O.
Default interview preset: 5 assets in a directed ring, seed 17; configurable 3–50 assets.
Asset IDs are `asset-000` onward. Severity 0/1/2 means HEALTHY/WARNING/CRITICAL.
The baseline has asset-000 CRITICAL, the middle asset WARNING, and the rest HEALTHY.
Reset restores this intelligible baseline, not an all-healthy fleet.
This is a fictional electrical-asset degradation model, not power-flow engineering.

Each explicit tick represents 60 simulated seconds and emits one immutable synthetic
event per asset. A seeded pseudorandom selection worsens one asset by one severity
level. Each asset that was CRITICAL before the tick worsens its right neighbor by one
level. Both contributions are computed from the pre-tick snapshot, added, and capped
at CRITICAL: no order-dependent same-tick cascade. Faults never heal except on reset.
For the same seed/configuration and Python 3.12 runtime, histories are identical.
No wall clock, sleep, background workers or unbounded history retention is used.

Events contain asset_id, epoch, per-asset sequence, tick, and severity. Epoch starts
at 1; tick and sequences start at 0. Sequence advances once per emitted asset event.
Configuration bounds: seed 0–2**32-1, ticks/sequences 0–1000, epochs 1–1,000,000.
Reject bools masquerading as integers. Reaching a bound fails before state mutation.

A separate current-state consumer is the future ingestion/query boundary. It rejects
unknown assets and invalid event fields. Duplicate/replayed sequences, old/future
epochs, backward ticks and healing transitions cannot mutate current state. Sequence
tracking is per asset in the active epoch; independent interleaved assets must advance.
This is a single-threaded local consumer, not durable or authenticated cloud ingestion.

Reset takes a bounded command ID and expected epoch. A successful reset increments
epoch, clears tick/sequences, reseeds randomness, and restores the baseline. Retain
only the most recent reset receipt: its duplicate returns the same receipt without
resetting new progress. Older requests and wrong epochs are rejected without mutation.
Command IDs are 1–64 ASCII letters/digits/underscore/hyphen; key is (expected_epoch, ID).
A consumer applies that receipt once, clearing old state and loading the new baseline.
A duplicate receipt must not clear progress; delayed old-epoch events remain rejected.
Idempotency lasts for this process only. Restart starts a new isolated rehearsal;
no live adapter may reuse these local epochs as authenticated session identifiers.

## Acceptance mapping

- AC-201 / INT-01: identical seeded event/state replay, including after reset.
- AC-202 / INT-02: persistent accumulating faults, bounded transitions, visible neighbor effect.
- AC-203 / local part of INT-03: complete reset, duplicate idempotency, old-epoch isolation.
- AC-204 / foundation for INT-09: independent per-asset ingestion, replay rejection,
  invalid-state rejection with unchanged query state.
- AC-205: bounded offline terminal rehearsal clearly labels synthetic data and local reset.

The existing gate accepts AC-nnn IDs; these additive IDs map the issue's INT IDs
without changing the gate or the original acceptance criteria. Full INT-03 cloud
handling, INT-04 physical/application ACK, dashboard, AWS integration, intentional
INT-08–INT-11 debugging exercise, recording, and measured rehearsal time are deferred.

## Open decisions and evaluation

Technical owner: repository maintainer. Ted evaluates whether the terminal progression
is understandable before a dashboard is added. Seeded hazard and ring topology are
reversible prototype choices. Actual asset topology, cloud stack, authenticated reset
sessions, persistence/concurrency, 50/500-asset throughput/cost and physical LED behavior
remain unresolved and unverified. No production or live-device evidence is implied.
