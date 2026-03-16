# Phase 8 Task B Debt Retuning Trace

## Date

2026-03-16

## Timestamp

2026-03-16T10:51:50-07:00

## Model

GPT-5 Codex

## Prompt

ok, go ahead and work on the retune

## Intent

Retune Task B transfer so repeated contradictory feedback creates an explicit local negative memory, and make maintenance less likely to preserve context-action supports that are now carrying contradiction debt.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added local fast-layer transform debt to `NodeRuntimeState`:
  - `transform_debt`
  - `context_transform_debt`
- contradictory task feedback now increases debt on the node that used the transform, while successful feedback clears that debt
- local observation now exposes:
  - `feedback_debt_*`
  - `context_feedback_debt_*`
- selector scoring now subtracts debt-heavy transform options, especially in the active packet context
- maintenance now reduces priority for debt-heavy context-action supports when ATP is limited
- added regressions for:
  - low-match feedback building transform debt
  - successful feedback clearing transform debt
  - selector avoiding a debt-heavy context transform
  - maintenance preferring the lower-debt context support under a tight budget

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\models.py" "Phase 8\\phase8\\environment.py" "Phase 8\\phase8\\selector.py" "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\adapters.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\\compare_task_transfer.py"`

All commands passed.

## Result

This pass was mixed and important.

For seed `51`, the retune helped dramatically:

- cold Task B: `3` exact matches, `0.3611` mean bit accuracy
- warm full Task B: `8` exact matches, `0.5278` mean bit accuracy
- warm substrate-only Task B: `1` exact match, `0.3611` mean bit accuracy

The new diagnostics for that seed also improved in the expected direction for warm full:

- `context_1` mean bit accuracy rose to `0.3125`
- wrong-transform-family count fell to `9`
- stale-support suspicion fell to `5`

But across the 5-seed aggregate, the retune did **not** improve the overall transfer claim:

- cold Task B exact matches averaged `8.0`
- warm full Task B exact matches averaged `6.4`
- warm substrate-only Task B exact matches averaged `7.2`

- cold Task B mean bit accuracy averaged `0.5889`
- warm full Task B mean bit accuracy averaged `0.5111`
- warm substrate-only Task B mean bit accuracy averaged `0.5611`

So the debt mechanism appears to fix some formerly sticky warm-full cases, but it also over-generalizes enough to hurt the aggregate.

## Interpretation

The debt mechanism is directionally valid but not yet well scoped.

It seems to help when stale support is genuinely dominating the local decision loop, but it also suppresses useful adaptation pressure too broadly across other seeds. That likely means the system now needs a more selective contradiction response rather than a uniformly strong penalty.

The most likely next refinement is to make debt accumulation conditional on evidence of real stale domination, such as:

- strong pre-existing context support for the losing transform
- strong episodic-history endorsement for the losing transform
- repeated contradiction over multiple nearby packets in the same context

That would preserve the valuable “stop replaying the old answer” effect without degrading colder or more exploratory transfer runs.

## Immediate Next Step

- narrow contradiction-debt accumulation so it activates mainly when stale support is genuinely the source of the failure
- keep measuring success against both:
  - overall mean bit accuracy
  - `context_1` mean bit accuracy
- avoid any mode-specific special casing; keep the fix local and substrate-grounded
