# Phase 8 CVT-1 Slice 3 Trace

## Date

2026-03-16

## Timestamp

Not recorded in the original trace pass.

## Model

GPT-5 Codex

## Prompt

Continue into CVT-1 Slice 3 and add sink-side scoring with graded sequential feedback.

## Slice Implemented

CVT-1 Slice 3: sink-side target computation, exact and partial scoring, and graded feedback.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- `SignalPacket` now records `bit_match_ratio` and `feedback_award`
- the environment can now compute Stage 1 targets for:
  - `task_a`
  - `task_b`
- when a task packet reaches the sink:
  - target bits are computed from `input_bits`, `context_bit`, and `task_id`
  - exact-match status is stored in `matched_target`
  - bit overlap is recorded in `bit_match_ratio`
  - upstream feedback amount is scaled by match quality
- routing-only packets keep the legacy full feedback behavior so earlier routing experiments are preserved
- environment snapshots and summaries now report exact matches, partial matches, mean bit accuracy, and mean feedback award

## Why This Slice Matters

This is the first point where local transforms can become learnable for a computational task.

Before this slice, nodes could mutate packet content, but the environment had no way to tell whether those mutations were useful. Now the sink can judge them and return a graded metabolic consequence without introducing any global training shortcut.

## Tests Added

- exact-match task packet gets full feedback
- partial-match task packet gets smaller positive feedback
- zero-match task packet gets no feedback

## Validation

- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python -m py_compile "Phase 8\\phase8\\models.py" "Phase 8\\phase8\\environment.py" "Phase 8\\tests\\test_phase8.py"`

Both passed.

## Immediate Next Step

CVT-1 Slice 4 should add a first runnable Task A scenario and comparison harness so we can observe whether the substrate actually learns from the new graded computational feedback.
