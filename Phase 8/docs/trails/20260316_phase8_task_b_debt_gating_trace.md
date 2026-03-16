# Phase 8 Task B Debt Gating Trace

## Date

2026-03-16

## Timestamp

2026-03-16T10:56:48-07:00

## Model

GPT-5 Codex

## Prompt

Go ahead

## Intent

Narrow contradiction-debt accumulation so it only activates when there is already meaningful local evidence of a stale transform habit, instead of penalizing every mismatch equally.

## Files Touched

- `Phase 8/phase8/environment.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- debt accumulation in returning task feedback is now gated on prior local commitment:
  - prior generic transform credit
  - prior context-transform credit
  - existing generic debt
  - existing context debt
- low-match feedback without strong prior commitment now mostly relaxes old debt rather than creating new debt
- added a regression confirming that ordinary low-match feedback without prior commitment does not build large debt

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\environment.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\\compare_task_transfer.py"`

All commands passed.

## Result

This narrowed debt trigger recovered some of the aggregate damage from the previous debt pass.

Across 5 seeds:

- cold Task B exact matches averaged `3.2`
- warm full Task B exact matches averaged `4.0`
- warm substrate-only Task B exact matches averaged `5.0`

- cold Task B mean bit accuracy averaged `0.4111`
- warm full Task B mean bit accuracy averaged `0.4222`
- warm substrate-only Task B mean bit accuracy averaged `0.4611`

So warm full is again slightly ahead of cold on the aggregate core metrics.

But the branch-specific diagnostics still show the remaining weakness:

- cold `context_1` mean bit accuracy averaged `0.3000`
- warm full `context_1` mean bit accuracy averaged `0.2500`
- warm substrate-only `context_1` mean bit accuracy averaged `0.4750`

For seed `51`, the narrowed debt gate did not preserve the earlier dramatic warm-full gain:

- cold Task B: `0` exact matches, `0.2222` mean bit accuracy
- warm full Task B: `1` exact match, `0.1944` mean bit accuracy
- warm substrate-only Task B: `2` exact matches, `0.3333` mean bit accuracy

## Interpretation

This is a better global tradeoff than the broad debt pass, but it is still not the final answer.

The architecture now has a more reasonable contradiction response:

- it no longer suppresses adaptation as broadly across seeds
- it restores a modest warm-full aggregate advantage over cold start

But it still does not fix the core branch-specific problem. The changed odd-context branch (`context_1`) remains the weak point for full carryover, and substrate-only carryover still adapts there more cleanly.

## Immediate Next Step

- keep the narrowed debt trigger in place
- make the next retune target `context_1` more selectively, likely by combining contradiction gating with branch- or transform-family-specific evidence rather than broader transform-level debt alone
- treat improvement as real only if warm full beats cold on both:
  - overall mean bit accuracy
  - `context_1` mean bit accuracy
