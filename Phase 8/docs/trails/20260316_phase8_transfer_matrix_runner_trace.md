# Phase 8 Transfer Matrix Runner Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:42:00-07:00

## Model

GPT-5 Codex

## Prompt

Go ahead and the matrix and nearby variant

## Intent

Add a nearby Stage 1 transfer variant and turn the ad hoc transfer checks into a reusable small transfer matrix across multiple tasks.

## Files Touched

- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/scenarios.py`
- `Phase 8/compare_transfer_matrix.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added `task_c` target logic:
  - `context_0 -> xor_mask_1010`
  - `context_1 -> xor_mask_0101`
- added `cvt1_task_c_stage1` to the scenario catalog
- added sink-scoring and scenario-availability regressions for `task_c`
- added `compare_transfer_matrix.py`, which runs ordered pairwise transfer checks across:
  - `cvt1_task_a_stage1`
  - `cvt1_task_b_stage1`
  - `cvt1_task_c_stage1`

## Validation

Executed:

- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\scenarios.py" "Phase 8\compare_transfer_matrix.py" "Phase 8\tests\test_phase8.py"`
- `python "Phase 8\compare_transfer_matrix.py"`

All commands passed.

## Result

Using seeds `13, 23, 37, 51, 79`, the matrix aggregates were:

### `Task A -> Task B`

- cold exact `3.0`, warm full exact `8.8`
- cold bit accuracy `0.4445`, warm full `0.6333`
- warm full beat cold on both metrics in `5 / 5` seeds

### `Task A -> Task C`

- cold exact `4.8`, warm full exact `8.2`
- cold bit accuracy `0.4333`, warm full `0.5500`
- warm full beat cold on bit accuracy in `5 / 5` seeds and on both metrics in `4 / 5`

### `Task B -> Task A`

- cold exact `9.4`, warm full exact `9.0`
- cold bit accuracy `0.7000`, warm full `0.6722`
- this direction remained mixed and slightly negative overall

### `Task B -> Task C`

- cold exact `4.8`, warm full exact `5.8`
- cold bit accuracy `0.4333`, warm full `0.4722`
- mildly positive, but weaker than `A -> B`

### `Task C -> Task A`

- cold exact `9.4`, warm full exact `10.0`
- cold bit accuracy `0.7000`, warm full `0.6944`
- near parity overall

### `Task C -> Task B`

- cold exact `3.0`, warm full exact `5.6`
- cold bit accuracy `0.4445`, warm full `0.4778`
- modestly positive, but less stable than `A -> B`

## Interpretation

The transfer mechanism is now clearly stronger than it was, but the matrix shows it is not symmetric.

The system transfers especially well out of `Task A`, and much less reliably when adapting from `Task B` back toward `Task A`. So the current maintained substrate is not just “good at transfer” in the abstract; it is better described as direction-sensitive and attractor-dependent.

That is useful scientifically because it gives a much sharper next question:

- what substrate properties make one task a good launch point for transfer and another a sticky trap?

## Immediate Next Step

- use the matrix runner as the default transfer evaluation surface
- compare the per-pair diagnostics rather than optimizing only `A -> B`
- avoid claiming general transfer symmetry until `B -> A` and `C -> A` are stronger
