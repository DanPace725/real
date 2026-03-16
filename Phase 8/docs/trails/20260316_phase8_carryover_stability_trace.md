# Phase 8 Carryover Stability Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:43:25-07:00

## Model

GPT-5 Codex

## Prompt

Work on tightening the stability.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- feedback pulses now carry packet `context_bit` so returned credit can stay local to the transform and the task context that produced it
- node runtime state now keeps:
  - generic `transform_credit`
  - context-bound `context_transform_credit`
- local observation now exposes `context_feedback_credit_<transform>` for the current head packet context
- selector scoring now weights context-matched returned credit more strongly than generic transform credit on explicit-context task packets
- substrate maintenance can now prioritize context-specific action support using context-bound returned credit
- tests now verify that returned transform credit is visible for the matching context and does not appear as context-specific credit for the wrong context

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\models.py" "Phase 8\\phase8\\environment.py" "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\adapters.py" "Phase 8\\phase8\\selector.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## Result

This pass improved Task A stability by reducing context bleed.

For seed `51` on `cvt1_task_a_stage1`:

- cold exact matches: `7`
- warm full exact matches: `10`
- cold mean bit accuracy: `0.6389`
- warm full mean bit accuracy: `0.75`

The transform mix also became more differentiated in training:

- final transforms: `rotate_left_1: 12`, `xor_mask_1010: 6`
- context breakdown shifted from a mostly single-transform warm solution to a more context-divided pattern

In the 5-seed aggregate for `cvt1_task_a_stage1`:

- exact matches: `8.0` cold -> `10.0` warm full
- mean bit accuracy: `0.6611` cold -> `0.7389` warm full
- mean route cost: `0.04638` cold -> `0.04313` warm full

## Interpretation

This is a stability gain rather than just a breakthrough gain.

- warm full still improves the computational task
- that improvement is now less dependent on generic transform reuse and more tied to explicit-context evidence

The remaining weakness is that substrate-only carryover is still unstable, which suggests episodic survivors and context-bound returned credit are still doing part of the work that the maintained substrate has not fully absorbed yet.

## Immediate Next Step

- strengthen promotion from repeated context-bound returned credit into durable context-specific action support
- add transfer evaluation on Task B once the full-carryover Task A margin remains stable across repeated comparison runs
