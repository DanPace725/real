# Phase 8 Comparison Trace - 2026-03-15

## Intent

Measure whether the new carryover paths actually help routing under a denser branching workload, then use the result to redesign the demo around a more meaningful test.

## Workload

- topology: branch-pressure graph with 6 active nodes plus sink
- session length: 18 cycles
- packet load: 6 initial packets, then +2 at cycles 4, 8, and 12
- seeds tested: 13, 23, 37, 51, 79

## Findings

1. Full carryover is mixed and currently regresses on average.
Result: average delivered packets fell from 7.0 on cold start to 5.6 on full warm start, while average route cost improved from 0.04737 to 0.04305.

2. The main failure mode appears to be stale episodic exploitation.
Result: full carryover often spends ATP following prior trails more cheaply, but not always more adaptively. Throughput and latency regress in most seeds even though route cost drops.

3. Substrate-only carryover is gentler than full carryover but still not a net win yet.
Result: average delivered packets fell from 7.0 on cold start to 6.2 on substrate-only warm start. It did lower average route cost further to 0.04105 and slightly increased remaining ATP, but it did not improve throughput overall.

## Consequence

The demo should no longer be a simple smoke run. It now needs to show:

- a training session
- a cold evaluation session
- a full warm-start evaluation
- a substrate-only warm-start evaluation

That comparison is the current best diagnostic for Phase 8 behavior.
