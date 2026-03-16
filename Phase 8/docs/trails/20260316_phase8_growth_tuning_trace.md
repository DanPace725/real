# 2026-03-16 - GPT-5 - Phase 8 Growth Tuning Trace

## Intent

Tune Level 2 morphogenesis so structural growth happens early enough to matter, new structure is selectable after it appears, and benchmark "wins" reflect useful adaptation rather than topology size alone.

## Initial Symptoms

- Growth in `cvt1_task_b_stage1` often arrived too late to receive any feedback.
- Transfer runs could bud multiple nodes, but some of those structures remained unused because the route scorer still favored entrenched edges.
- The first morphogenesis benchmark could count lower-cost but worse-output runs as wins.

## Tuning Changes

- Allowed growth actions to appear under low local pressure instead of only when a node inbox is completely empty.
- Let the selector interrupt routing for growth only when:
  - local queue is within the morphogenesis tolerance,
  - urgency is still low,
  - ATP is healthy,
  - contradiction or overload is structurally high,
  - and the node has enough recent experience to justify interruption.
- Added a success brake so nodes do not interrupt a route that is already matching well unless contradiction is significantly elevated.
- Seeded new growth paths with the parent's strongest generic and context-specific transform biases so fresh edges/nodes can actually get tried.
- Added local observation fields for dynamic/probationary neighbors plus frontier-target progress values to improve local scoring without exposing global topology.
- Tightened benchmark semantics so `growth_win` now requires earned growth and either task improvement or efficiency improvement without meaningful task regression.

## Measurement Snapshot

- `cvt1_task_b_stage1` aggregate moved from a clear regression to near-neutral task performance:
  - fixed exact matches: `3.0`
  - growth exact matches: `3.0`
  - fixed bit accuracy: `0.4389`
  - growth bit accuracy: `0.4333`
  - earned growth rate: `0.4`
  - growth win rate: `0.2`
- `Task A -> Task B` transfer now shows meaningful structural adaptation:
  - fixed exact matches: `7.6`
  - growth exact matches: `9.0`
  - fixed bit accuracy: `0.5833`
  - growth bit accuracy: `0.6444`
  - earned growth transfer rate: `0.8`
  - growth transfer win rate: `0.6`

## Remaining Frictions

- `branch_pressure` and `sustained_pressure` still rarely convert buds into utilized structure.
- Some transfer seeds still overgrow in ways that do not improve task quality (`seed 79` remained earned but not a win).
- The next tuning pass should probably focus on overload-specific growth scoring and dynamic-edge pruning after low-value transfer buds.
