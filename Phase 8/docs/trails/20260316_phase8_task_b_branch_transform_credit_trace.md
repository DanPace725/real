# Phase 8 Task B Branch Transform Credit Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:28:38-07:00

## Model

GPT-5 Codex

## Prompt

Interesting. Go ahead and keep working this out

## Intent

Build on the positive branch-context evidence path by adding positive branch-plus-transform credit, so full carryover can not only prefer the right branch in Task B transfer, but also choose the right transform family on that branch more reliably.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added two new local positive-memory channels:
  - `branch_transform_credit`
  - `context_branch_transform_credit`
- returning feedback now reinforces:
  - generic transform credit
  - context-transform credit
  - branch-context credit
  - branch-plus-transform credit
  - branch-plus-transform-plus-context credit
- local observation now exposes:
  - `branch_feedback_credit_{neighbor}_{transform}`
  - `context_branch_feedback_credit_{neighbor}_{transform}`
- selector scoring now uses these positive branch-transform signals to strengthen transform choice on a promising branch, instead of only steering branch choice
- maintenance now also prioritizes action supports with strong branch-transform-context credit under ATP scarcity
- added regressions for:
  - maintenance preferring the credited transform on the same branch/context
  - successful feedback creating branch-transform and context-branch-transform credit
  - selector preference for the credited transform when branch support is otherwise equal

## Validation

Executed:

- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\selector.py" "Phase 8\phase8\substrate.py" "Phase 8\phase8\models.py" "Phase 8\phase8\adapters.py" "Phase 8\tests\test_phase8.py"`
- `python "Phase 8\compare_task_transfer.py"`

All commands passed.

## Result

This was the strongest Task B carryover improvement so far.

Across 5 seeds:

- cold Task B exact matches averaged `3.0`
- warm full Task B exact matches averaged `8.8`
- warm substrate-only Task B exact matches averaged `6.6`

- cold Task B mean bit accuracy averaged `0.4445`
- warm full Task B mean bit accuracy averaged `0.6333`
- warm substrate-only Task B mean bit accuracy averaged `0.5555`

- cold `context_1` mean bit accuracy averaged `0.3375`
- warm full `context_1` mean bit accuracy averaged `0.5500`
- warm substrate-only `context_1` mean bit accuracy averaged `0.4500`

- cold wrong-transform-family counts averaged `10.2`
- warm full wrong-transform-family counts averaged `9.2`
- warm substrate-only wrong-transform-family counts averaged `7.2`

- cold stale-support suspicions averaged `5.6`
- warm full stale-support suspicions averaged `4.2`
- warm substrate-only stale-support suspicions averaged `1.6`

## Interpretation

This is a real change in the quality of full carryover.

The system now has a positive local mechanism for preserving not just:

- which context a branch belongs to
- but which transform family tends to work on that branch in that context

That appears to be exactly what full carryover was missing. Warm full is now ahead of both cold and substrate-only on the core Task B transfer metrics in this 5-seed run, and it is no longer paying for that advantage with worse stale-support suspicion than cold start.

## Immediate Next Step

- keep the new branch-transform credit mechanism
- test whether this stronger warm-full advantage holds across a broader seed set and nearby transfer-task variants
- if it does, the project is much closer to being ready for the next transfer benchmark rather than more local retuning first
