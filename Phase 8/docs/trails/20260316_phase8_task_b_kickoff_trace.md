# Phase 8 Task B Kickoff Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:49:38-07:00

## Model

GPT-5 Codex

## Prompt

Take a look at the new slow layer file, make sure it aligns with your understanding of things overall, and then let's start working towards Task B work.

## Alignment Check

The new slow-layer note aligned closely with the current code state.

- it correctly identified the route-economy vs task-correctness tension
- it correctly called the context-specific substrate work the current breakthrough
- its directive to begin Task B transfer now matched the current Task A stability level after the recent carryover passes

## Files Touched

- `Phase 8/phase8/scenarios.py`
- `Phase 8/compare_task_transfer.py`
- `Phase 8/run_phase8_demo.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added a real Stage 1 Task B scenario:
  - `cvt1_task_b_stage1`
- generalized the CVT Stage 1 signal generator so Task A and Task B share the same input/context stream while differing only in the odd-context target transform
- added the first Task A -> Task B transfer runner in `compare_task_transfer.py`
- added a `transfer` mode to `run_phase8_demo.py`
- added tests for:
  - Task B exact sink scoring
  - Task B scenario availability
  - transfer-metric window reporting

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\scenarios.py" "Phase 8\\compare_task_transfer.py" "Phase 8\\run_phase8_demo.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\\compare_task_transfer.py"`

All commands passed.

## Result

The first Task B transfer result is mixed and useful.

For seed `51`:

- cold Task B: `3` exact matches, `0.4444` mean bit accuracy
- warm full Task B: `1` exact match, `0.2778` mean bit accuracy
- warm substrate-only Task B: `6` exact matches, `0.5833` mean bit accuracy

Across 5 seeds:

- cold Task B exact matches averaged `5.2`
- warm full Task B exact matches averaged `3.4`
- warm substrate-only Task B exact matches averaged `5.2`

- cold Task B mean bit accuracy averaged `0.5389`
- warm full Task B mean bit accuracy averaged `0.4056`
- warm substrate-only Task B mean bit accuracy averaged `0.5222`

So the first transfer loop says:

- full carryover currently overfits the old Task A odd-context branch and hurts direct Task B adaptation
- substrate-only carryover is much less damaging and is roughly at cold-start parity overall

## Interpretation

This is an honest but productive first transfer result.

The architecture is now testing the right thing. The current maintained substrate preserves useful computational structure, but the full carryover path still carries too much task-specific commitment into the changed branch. That is exactly the kind of failure mode the transfer harness is supposed to reveal.

## Immediate Next Step

- tune the full-carryover path so context-bound odd-branch memory can relax faster when Task B contradicts Task A
- preserve the stable even-context branch while reducing stale odd-context lock-in
- compare whether this makes full carryover beat both cold Task B and substrate-only Task B
