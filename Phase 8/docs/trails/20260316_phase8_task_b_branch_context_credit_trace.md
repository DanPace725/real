# Phase 8 Task B Branch Context Credit Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:21:02-07:00

## Model

GPT-5 Codex

## Prompt

Ok, lets add the positive branch context evidence

## Intent

Add a positive branch-context signal so Task B transfer can preserve branch-context pairs that are locally working, instead of learning only by building contradiction debt against stale branch reuse.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added `branch_context_credit` to local runtime state
- contextual feedback now updates both:
  - negative branch-context evidence through `branch_context_debt`
  - positive branch-context evidence through `branch_context_credit`
- local observation now exposes `branch_context_feedback_credit_{neighbor}`
- selector scoring now uses positive branch-context evidence to:
  - increase context evidence for a branch
  - reduce branch-context pressure when a branch still has good local evidence
  - positively bias route choice toward branches that have worked in this context before
- maintenance now also uses branch-context credit, so scarce ATP can preserve context-reliable branches instead of only avoiding contradiction-heavy ones
- added regressions for:
  - maintenance preference toward high branch-context credit
  - good contextual feedback building branch-context credit while reducing debt
  - selector preference for the credited branch even when transform-level evidence is otherwise similar

## Validation

Executed:

- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\selector.py" "Phase 8\phase8\substrate.py" "Phase 8\phase8\models.py" "Phase 8\phase8\adapters.py" "Phase 8\tests\test_phase8.py"`
- `python "Phase 8\compare_task_transfer.py"`

All commands passed.

## Result

This was a strong step for Task B transfer.

Across 5 seeds:

- cold Task B exact matches averaged `2.2`
- warm full Task B exact matches averaged `5.2`
- warm substrate-only Task B exact matches averaged `4.2`

- cold Task B mean bit accuracy averaged `0.3722`
- warm full Task B mean bit accuracy averaged `0.4722`
- warm substrate-only Task B mean bit accuracy averaged `0.4778`

- cold `context_1` mean bit accuracy averaged `0.2250`
- warm full `context_1` mean bit accuracy averaged `0.3500`
- warm substrate-only `context_1` mean bit accuracy averaged `0.3375`

- cold wrong-transform-family counts averaged `12.2`
- warm full wrong-transform-family counts averaged `11.4`
- warm substrate-only wrong-transform-family counts averaged `9.6`

## Interpretation

Positive branch-context evidence gives the mechanism a healthier shape.

Full carryover is no longer improving mainly by backing away from stale branches. It now has an explicit local signal for branch-context pairings that are worth preserving, and that shows up in the numbers:

- warm full clearly beats cold on both Task B aggregate metrics
- warm full now edges substrate-only on exact matches
- warm full now also edges substrate-only on the changed `context_1` branch

The remaining weakness is precision and stability rather than raw transfer anymore. Warm full still trails substrate-only slightly on overall mean bit accuracy, and stale-support suspicion remains elevated compared with substrate-only.

## Immediate Next Step

- keep the positive branch-context evidence path
- couple branch-context credit more tightly to the correct transform family, so the preferred branch is also more likely to choose the right transform on Task B
- use that to reduce warm-full stale-support suspicion without giving back the new exact-match gains
