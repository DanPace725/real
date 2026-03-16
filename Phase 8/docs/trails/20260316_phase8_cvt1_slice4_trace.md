# Phase 8 CVT-1 Slice 4 Trace

## Date

2026-03-16

## Timestamp

Not recorded in the original trace pass.

## Model

GPT-5 Codex

## Prompt

Continue into CVT-1 Slice 4 by adding a runnable Task A scenario and comparison harness.

## Slice Implemented

CVT-1 Slice 4: Stage 1 scenario definition plus comparison and demo support.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/scenarios.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/__init__.py`
- `Phase 8/compare_cold_warm.py`
- `Phase 8/run_phase8_demo.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added `SignalSpec` as a scenario-level signal description type
- `NativeSubstrateSystem` can now inject explicit signal specs and run workloads from signal-spec schedules
- added `cvt1_task_a_stage1` to the scenario catalog
- comparison and demo runners now support signal-spec workloads, not just count-based packet schedules
- summaries and aggregates now include task-facing metrics:
  - `exact_matches`
  - `partial_matches`
  - `mean_bit_accuracy`
  - `mean_feedback_award`

## Validation Run

Executed:

- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python -m py_compile "Phase 8\\phase8\\models.py" "Phase 8\\phase8\\environment.py" "Phase 8\\phase8\\scenarios.py" "Phase 8\\compare_cold_warm.py" "Phase 8\\run_phase8_demo.py" "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## First Result

The first computational scenario is now runnable and measurable.

For seed `51` on `cvt1_task_a_stage1`:

- cold start: `6` exact matches, `0.6667` mean bit accuracy
- warm full: `1` exact match, `0.5278` mean bit accuracy
- warm substrate-only: `1` exact match, `0.5278` mean bit accuracy

Across 5 seeds on the same scenario:

- cold exact matches averaged `4.6`
- warm full exact matches averaged `3.2`
- warm substrate exact matches averaged `2.8`
- cold mean bit accuracy averaged `0.6056`
- warm full mean bit accuracy averaged `0.5278`
- warm substrate mean bit accuracy averaged `0.5667`

Warm starts still reduce route cost, but they are not yet improving computational performance on Task A.

## Interpretation

This is the first honest signal that the current carryover mechanisms are still biased toward routing economy more than task-correct transformation.

That means the computational scenario is doing its job: it is exposing the difference between "the substrate got cheaper" and "the substrate got smarter at the actual task."

## Immediate Next Step

The next development loop should tune task-sensitive selection or coherence so exact and partial computational success shape behavior more strongly than route-cost reduction alone.
