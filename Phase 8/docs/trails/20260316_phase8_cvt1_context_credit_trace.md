# Phase 8 CVT-1 Context Credit Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:13:22-07:00

## Model

GPT-5 Codex

## Prompt

Continue tuning task-sensitive selection and feedback binding so computational success shapes behavior more strongly than route-cost reduction alone.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/consolidation.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- `FeedbackPulse` now carries transform-path and match-quality information
- `NodeRuntimeState` now stores:
  - `last_feedback_amount`
  - `last_match_ratio`
  - per-transform returned `transform_credit`
- when a graded sink pulse returns upstream, each node now receives local credit tied to the transform it used on that packet
- local observation exposes:
  - `feedback_credit_<transform>`
  - `last_feedback_amount`
  - `last_match_ratio`
- transform memory can now be context-sensitive for explicit-context Stage 1 tasks
- selector scoring now uses:
  - returned transform credit
  - explicit-context transform bias
  - a penalty against low-evidence identity transforms when the packet is a context-bearing task packet

## Validation

Executed:

- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python -m py_compile "Phase 8\\phase8\\models.py" "Phase 8\\phase8\\environment.py" "Phase 8\\phase8\\adapters.py" "Phase 8\\phase8\\selector.py" "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\consolidation.py" "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## Result

This pass produced the first aggregate sign that full warm carryover is starting to help the computational task instead of only the route economy.

For seed `51` on `cvt1_task_a_stage1`:

- cold exact matches: `9`
- warm full exact matches: `3`
- warm substrate-only exact matches: `12`

This seed remains mixed, but the 5-seed aggregate improved:

- cold exact matches averaged `9.2`
- warm full exact matches averaged `9.6`
- warm substrate exact matches averaged `7.2`

At the same time:

- cold mean bit accuracy averaged `0.7333`
- warm full mean bit accuracy averaged `0.6889`
- warm substrate mean bit accuracy averaged `0.6222`

So warm full is now slightly ahead on exact matches, but task quality is still less stable than desired.

## Interpretation

The system has crossed an important threshold:

- full carryover is no longer only helping route cost
- full carryover can now improve exact computational success in aggregate on Task A

But the quality of that success is still uneven. The current selector and feedback binding appear strong enough to find more exact-match trajectories, but not yet strong enough to make those trajectories consistently cleaner across the whole packet stream.

## Immediate Next Step

The next loop should focus on stability rather than just breakthrough:

- improve mean bit accuracy under warm full carryover
- inspect context-specific failures more directly
- then move to Task B transfer once Task A warm starts are clearly better on both exact matches and overall accuracy
