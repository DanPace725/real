# Phase 8 Task B Branch Debt Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:02:08-07:00

## Model

GPT-5 Codex

## Prompt

Go ahead and give that a try

## Intent

Retune Task B transfer more selectively by penalizing stale branch-specific transform habits, instead of damping an entire transform family whenever contradictory feedback appears.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added branch-specific contradiction memory to node runtime state:
  - `branch_transform_debt`
  - `context_branch_transform_debt`
- returning task feedback now tracks contradiction at the level of:
  - neighbor branch
  - transform
  - explicit context
- branch debt only accumulates under the same narrowed gating rule already used for generic debt:
  - prior transform commitment
  - prior context-transform commitment
  - existing contradiction debt
- local observation now exposes branch-specific debt signals to the selector
- route scoring now penalizes branch-specific contradiction debt, with the strongest penalty applied to context-matched branch debt
- added regressions for:
  - branch debt buildup under stale committed behavior
  - no branch debt buildup without prior commitment
  - selector avoidance of a branch carrying high context-branch debt

## Validation

Executed:

- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\selector.py" "Phase 8\phase8\models.py" "Phase 8\tests\test_phase8.py"`
- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python "Phase 8\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\compare_task_transfer.py"`

All commands passed.

## Result

This selective branch-debt pass improved the aggregate Task B transfer story instead of just moving failure around.

Across 5 seeds:

- cold Task B exact matches averaged `3.8`
- warm full Task B exact matches averaged `5.0`
- warm substrate-only Task B exact matches averaged `6.6`

- cold Task B mean bit accuracy averaged `0.4333`
- warm full Task B mean bit accuracy averaged `0.4944`
- warm substrate-only Task B mean bit accuracy averaged `0.5556`

- cold `context_1` mean bit accuracy averaged `0.3375`
- warm full `context_1` mean bit accuracy averaged `0.3500`
- warm substrate-only `context_1` mean bit accuracy averaged `0.4500`

- cold wrong-transform-family counts averaged `11.2`
- warm full wrong-transform-family counts averaged `10.2`
- warm substrate-only wrong-transform-family counts averaged `8.6`

For seed `51`:

- cold Task B: `0` exact matches, `0.2222` mean bit accuracy
- warm full Task B: `4` exact matches, `0.4722` mean bit accuracy
- warm substrate-only Task B: `4` exact matches, `0.4444` mean bit accuracy

## Interpretation

This is the first Task B retune in this sequence that clearly improved both:

- the 5-seed warm-full aggregate
- the specific `context_1` branch that had been lagging cold start

The benefit appears to come from making contradiction memory more local and more precise. The system is no longer penalizing a whole transform family just because one branch-context pairing has gone stale.

The remaining limitation is also clear. Warm full is now ahead of cold, but substrate-only is still the more plastic transfer path on Task B. That suggests full carryover still preserves too much Task A-specific odd-branch structure, even though the new branch-level debt can now push back against it.

## Immediate Next Step

- keep the narrowed generic contradiction gate and the new branch-specific debt path
- target repeated wrong-transform-family reuse on `context_1` more directly, using the new branch debt and mismatch diagnostics rather than broader suppression
- treat the next Task B pass as successful only if warm full narrows the remaining gap to substrate-only while preserving its aggregate advantage over cold
