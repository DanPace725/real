# Phase 8 CVT-1 Task Tuning Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:03:01-07:00

## Model

GPT-5 Codex

## Prompt

After aligning with the slow-layer guidance, begin working on task-sensitive selection, differentiation, and diagnostics for CVT-1.

## Files Touched

- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/consolidation.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/models.py`
- `Phase 8/phase8/__init__.py`
- `Phase 8/run_phase8_demo.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- transform choices now have their own local slow-memory supports in `ConnectionSubstrate`
- route-transform actions now receive transform-specific cost discounts instead of sharing only edge-level route memory
- the selector now scores route-transform actions with:
  - transform-specific slow support
  - transform-specific velocity
  - context-conditioned recent history when a context bit is available
- the consolidation pipeline now promotes successful route-transform history into transform-specific supports
- summaries now report:
  - `context_breakdown`
  - `final_transform_counts`
  - `action_supports`

## Why This Change Was Needed

The first CVT-1 comparison exposed that Phase 8 was learning route economy more strongly than transform correctness. Warm starts got cheaper routes, but not better task performance.

This tuning pass makes transform choice part of the maintained substrate rather than treating all transforms on a given edge as the same action family.

## Validation

Executed:

- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python -m py_compile "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\adapters.py" "Phase 8\\phase8\\selector.py" "Phase 8\\phase8\\consolidation.py" "Phase 8\\phase8\\environment.py" "Phase 8\\run_phase8_demo.py" "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## Result

This removed the worst version of the warm-start regression, but it did not fully flip the aggregate result yet.

For seed `51` on `cvt1_task_a_stage1`:

- cold exact matches: `7`
- warm full exact matches: `8`
- warm substrate exact matches: `1`

Across 5 seeds on the same scenario:

- cold exact matches averaged `4.6`
- warm full exact matches averaged `4.2`
- warm substrate exact matches averaged `4.4`
- cold mean bit accuracy averaged `0.6167`
- warm full mean bit accuracy averaged `0.6000`
- warm substrate mean bit accuracy averaged `0.6111`

Warm full now sometimes beats cold and no longer collapses as badly, but the average still trails slightly.

## Interpretation

This is progress, but not closure.

- route-cost carryover is still stronger than task-correct carryover
- full carryover is now close enough to cold that the next tuning loop should focus on binding feedback quality to the exact transform choices that produced it
- the new diagnostics make it clear that identity transforms still dominate too much of the task flow

## Immediate Next Step

The next loop should strengthen how sink feedback quality feeds back into transform-specific memory and selector pressure, especially under explicit context, before moving on to Task B transfer or latent-context Stage 2.
