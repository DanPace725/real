# Phase 8 Transfer Matrix Evaluation Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:37:03-07:00

## Model

GPT-5 Codex

## Prompt

Ok, let's try that and see what the results are

## Intent

Stress-test the new Task B carryover gains with broader evaluation instead of more local tuning, using:

- a larger-seed `Task A -> Task B` sweep
- a nearby reverse-direction `Task B -> Task A` transfer check

## Files Touched

- `Phase 8/docs/trails/20260316_phase8_transfer_matrix_eval_trace.md`

## Validation

Executed:

- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\selector.py" "Phase 8\phase8\substrate.py" "Phase 8\phase8\models.py" "Phase 8\phase8\adapters.py" "Phase 8\tests\test_phase8.py"`
- expanded transfer-matrix evaluation via inline Python using the existing `compare_task_transfer` and `compare_cold_warm` helpers

All commands passed.

## Result

### Expanded `Task A -> Task B` check

Across 12 seeds (`7, 11, 13, 17, 23, 29, 31, 37, 43, 51, 67, 79`):

- cold Task B exact matches averaged `3.9167`
- warm full Task B exact matches averaged `10.5833`
- warm substrate-only Task B exact matches averaged `7.3333`

- cold Task B mean bit accuracy averaged `0.4769`
- warm full Task B mean bit accuracy averaged `0.7037`
- warm substrate-only Task B mean bit accuracy averaged `0.5857`

- cold `context_1` mean bit accuracy averaged `0.4062`
- warm full `context_1` mean bit accuracy averaged `0.5833`
- warm substrate-only `context_1` mean bit accuracy averaged `0.4688`

- cold wrong-transform-family counts averaged `9.75`
- warm full wrong-transform-family counts averaged `6.75`
- warm substrate-only wrong-transform-family counts averaged `7.5833`

- cold stale-support suspicions averaged `6.0`
- warm full stale-support suspicions averaged `2.75`
- warm substrate-only stale-support suspicions averaged `2.0833`

Warm full beat cold on:

- exact matches in `11 / 12` seeds
- mean bit accuracy in `10 / 12` seeds
- both together in `10 / 12` seeds

### Reverse `Task B -> Task A` check

Across 5 seeds (`13, 23, 37, 51, 79`):

- cold exact matches averaged `9.4`
- warm full exact matches averaged `9.0`
- warm substrate-only exact matches averaged `9.0`

- cold mean bit accuracy averaged `0.7000`
- warm full mean bit accuracy averaged `0.6722`
- warm substrate-only mean bit accuracy averaged `0.6611`

- cold `context_1` mean bit accuracy averaged `0.8625`
- warm full `context_1` mean bit accuracy averaged `0.7375`
- warm substrate-only `context_1` mean bit accuracy averaged `0.7000`

This reverse-direction result was mixed and seed-sensitive rather than consistently positive.

## Interpretation

The new carryover mechanism appears to be genuinely strong for the harder `Task A -> Task B` transfer direction we have been shaping toward.

But it is not yet symmetric. The reverse `Task B -> Task A` check suggests the current substrate is better at adapting from the earlier Task A attractor into the revised Task B rule than it is at relaxing back in the other direction.

That means the project is in a better place than before, but not yet at “general transfer substrate” confidence.

## Immediate Next Step

- treat the current `Task A -> Task B` result as a strong positive milestone
- do not yet assume transfer symmetry
- add one more nearby transfer variant or a small transfer matrix runner so this asymmetry can be studied systematically rather than inferred from ad hoc reverse checks
