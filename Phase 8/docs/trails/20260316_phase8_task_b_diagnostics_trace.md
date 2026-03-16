# Phase 8 Task B Diagnostics Trace

## Date

2026-03-16

## Timestamp

2026-03-16T10:40:51-07:00

## Model

GPT-5 Codex

## Prompt

Ok, go ahead

## Intent

Add a causal diagnostics layer for Task B transfer so future tuning can distinguish branch-choice behavior, transform-family errors, partial-match drift, and stale-support carryover instead of relying only on aggregate exact-match and bit-accuracy scores.

## Files Touched

- `Phase 8/phase8/environment.py`
- `Phase 8/compare_task_transfer.py`
- `Phase 8/run_phase8_demo.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- extended `NativeSubstrateSystem.summarize()` with `task_diagnostics`:
  - per-context counts
  - expected transform per context
  - final transform counts
  - mismatch transform counts
  - first-hop branch counts
  - mismatch branch counts
  - identity fallback counts
  - wrong-transform-family counts
  - heuristic stale-context-support suspicion counts
  - compact admission-side masking metrics
- exposed those diagnostics directly in the Task B transfer demo
- extended the transfer aggregate summary with:
  - context-1 bit accuracy
  - wrong-transform counts
  - identity fallbacks
  - stale-support suspicion totals
- added tests for:
  - transform-mismatch diagnostic reporting in system summaries
  - transfer aggregate reporting of the new diagnostic fields

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\environment.py" "Phase 8\\compare_task_transfer.py" "Phase 8\\run_phase8_demo.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\\compare_task_transfer.py"`

All commands passed.

## Result

The new diagnostics make the current Task B transfer failure mode much more concrete.

For seed `51`:

- cold Task B:
  - `context_1` mean bit accuracy: `0.0`
  - wrong-transform-family count: `15`
  - stale-support suspicions: `13`
- warm full Task B:
  - `context_1` mean bit accuracy: `0.0`
  - wrong-transform-family count: `17`
  - stale-support suspicions: `17`
- warm substrate-only Task B:
  - `context_1` mean bit accuracy: `0.5625`
  - wrong-transform-family count: `8`
  - stale-support suspicions: `2`

Across 5 seeds:

- cold Task B `context_1` mean bit accuracy averaged `0.2125`
- warm full Task B `context_1` mean bit accuracy averaged `0.0875`
- warm substrate-only Task B `context_1` mean bit accuracy averaged `0.3125`

- cold wrong-transform-family count averaged `12.8`
- warm full wrong-transform-family count averaged `15.0`
- warm substrate-only wrong-transform-family count averaged `10.8`

- cold stale-support suspicion count averaged `5.4`
- warm full stale-support suspicion count averaged `13.6`
- warm substrate-only stale-support suspicion count averaged `2.0`

## Interpretation

The main remaining Task B problem is now sharply localized:

- warm full carryover is still overcommitted on the changed odd-context branch
- this is showing up more as wrong-transform persistence than as admission masking
- substrate-only carryover remains more plastic because it preserves useful scaffold without dragging as much stale context-specific commitment behind it

This means the next tuning pass should focus less on generic transfer improvement and more on reducing context-1 transform lock-in under full carryover.

## Immediate Next Step

- penalize partial-match persistence more directly on the changed odd-context branch
- weaken or decay context-specific transform bias faster when repeated contradictory feedback accumulates for the same context
- keep the new diagnostics in the loop and only count a tuning pass as successful if warm full improves both overall mean bit accuracy and `context_1` accuracy against cold start
