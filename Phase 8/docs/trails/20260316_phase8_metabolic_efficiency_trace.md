# Phase 8 Metabolic Efficiency Trace - 2026-03-16

## Intent

Make the learned source-boundary admission substrate care about metabolic efficiency, not just whether traffic eventually succeeds.

## Hypotheses

1. Admission support should weaken when the source spends ATP without getting local metabolic return.
Result: the admission substrate now explicitly scores source action cost against returned feedback energy, and tests confirm support drops after unreciprocated source spending.

2. Efficiency-gated admission should preserve the zero-drop robustness from the earlier queue-management slice.
Result: across the stress suite, delivery, drops, and overload all stayed flat at `16.0`, `0.0`, and `0.0` overall.

3. Efficiency gating should keep admission support from saturating to `1.0` too easily.
Result: this improved. Overall cold admission support now averages about `0.7016` instead of saturating near `1.0`, while warm starts rise to about `0.7703` full and `0.7696` substrate-only.

## Implementation Notes

- extended `AdmissionSubstrate.update()` to incorporate:
  - source action cost
  - returned feedback energy
  - net local energy balance
- added per-cycle source efficiency tracking in the routing environment
- surfaced `mean_source_efficiency` and `last_source_efficiency` in summaries and demos
- added a regression test that admission support decreases after a source packet is sent but not yet rewarded

## Comparison Results

Across the `5`-seed multi-scenario comparison:

- overall delivered packets remained `16.0`
- overall dropped packets remained `0.0`
- overall overload events remained `0.0`
- overall route cost still improved on warm starts:
  - `0.04760` cold
  - `0.04426` warm-full
  - `0.04083` warm-substrate

New efficiency observations:

- overall mean source efficiency is now visible at about `0.5876`
- `branch_pressure` shows mean source efficiency around `0.55`
- `detour_resilience` shows mean source efficiency around `0.3545`
- the sustained-pressure demo for seed `51` shows mean source efficiency `0.8583`, cold admission support `0.7945`, and warm admission support `0.8823`

## Consequence

This step made the learned boundary policy more metabolically honest. The next useful refinement is to teach the admission substrate to trade off latency against efficiency, because the current rule now avoids blind saturation but still accepts the higher latency imposed by strong ingress pacing.
