# Karma deterministic transition trace — separate follow-up experiment

Status: offline experiment for human review; no real-world causal inference.
Stakeholder: Ted, evaluating whether Karma can explain consequences in a modeled system.
Baseline: PR #19 emits observations without their disturbance/propagation inputs.
Target: explain one asset's progression from the exact rules and inputs used at execution.
Existing AC-201–AC-205 and simulator observation fields remain unchanged.

## Contract

`step()` keeps returning the original observations. `step_traced()` advances exactly
one tick and returns an immutable `TickTrace`; both use the same calculation and one
seeded random selection. `--trace` adds JSON trace records to the CLI; without that flag
its output is unchanged. No extra draws, reconstructed rules or AI explanations.

A tick trace contains the complete immutable pre-tick observations, one disturbance
(epoch, source tick, selected asset, +1), propagated effects (exact predecessor
observation, target asset, +1), per-asset transitions (before/after observations,
disturbance/propagated contributions, uncapped severity), and resulting observations.
Propagation reads source tick t; output belongs to tick t+1. A newly critical asset
cannot propagate within its own transition tick. Severity remains min(2, prior +
disturbance + propagated). Unchanged and capped transitions are included. These records
are producer-created execution evidence, not an authenticated external input schema.

`explain(asset_id)` uses a fixed template of recorded causes and arithmetic; unknown
assets raise ValueError. It reports all contributions, including clipping, without
claiming that either cause was uniquely necessary. Complete pre-tick state explains
why a predecessor did not activate. Disturbance selection explains which assets did
not receive that contribution. No counterfactual inference is performed.

The simulator retains no trace/history. Each returned trace is O(asset_count), bounded
by 50 assets. CLI remains capped at 100 ticks; domain at 1000 per epoch. A caller that
retains history owns that additional memory. At tick exhaustion, traced advancement
fails before state or randomness changes. Reset uses the existing receipt contract,
advances epoch and reseeds; subsequent traces reproduce the same progression in the
new epoch. Previously returned immutable traces remain historical records.

## Acceptance

- AC-206: trace contributions and pre-tick predecessors agree with transition arithmetic,
  including combined effects, saturation and no same-tick cascade.
- AC-207: traced and untraced runs agree; replay, one draw per tick, reset and exhaustion
  preserve the existing simulator behavior.
- AC-208: fixed-template explanations agree with records; CLI tracing is opt-in and
  ordinary output remains byte-identical.

No dependencies, cloud adapters, device I/O, inference framework or reusable engine
is introduced. Ring topology and severity remain the original fictional domain model.
Independent review is needed before claiming the experiment is accepted.
