# Phase 8 Transfer Debt Time-Course Trace

## Date

2026-03-16

## Timestamp

2026-03-16T12:13:13.5518444-07:00

## Model

GPT-5 Codex

## Prompt

Add a time-course view of debt and credit during transfer so we can see not just where `Task B -> Task A` ends, but how long it stays metabolically stuck on the way there.

## Inputs Reviewed

- `Phase 8/docs/trails/20260316_phase8_asymmetry_metabolic_cost_trace.md`
- `Phase 8/compare_task_transfer.py`
- `Phase 8/evaluate_transfer_asymmetry.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/slow_layer/20260316_H_c_consolidation_transfer_matrix.md`
- `Phase 8/slow_layer/20260316_H_c_consolidation_task_b_diagnostics.md`

## Work Completed

- Added `Phase 8/analyze_transfer_timecourse.py`.
- The new evaluator:
  - trains on `Task A` or `Task B`,
  - loads warm-full carryover into the transfer task,
  - runs the transfer cycle by cycle,
  - records per-cycle:
    - `branch_context_credit_total`
    - `branch_context_debt_total`
    - `context_branch_transform_credit_total`
    - `context_branch_transform_debt_total`
    - `wrong_transform_family`
    - `stale_context_support_suspicions`
    - cumulative exact matches
    - cumulative mean bit accuracy
    - `context_1` bit accuracy
  - and computes:
    - peak debt
    - debt area under curve
    - half-relief cycle after the debt peak
    - final residual debt and credit
- Ran the analysis across 12 seeds:
  - `5, 13, 17, 23, 29, 37, 43, 51, 61, 79, 87, 97`

## Main Findings

### 1. `Task B -> Task A` carries a larger contradiction burden across transfer

Warm-full averages:

- `Task A -> Task B`
  - `avg_peak_branch_context_debt_total`: `0.93916`
  - `avg_branch_context_debt_auc`: `9.59475`
  - `avg_peak_context_branch_transform_debt_total`: `0.89377`
  - `avg_context_branch_transform_debt_auc`: `9.33833`
  - `avg_final_branch_context_debt_total`: `0.43189`
  - `avg_final_context_branch_transform_debt_total`: `0.40428`

- `Task B -> Task A`
  - `avg_peak_branch_context_debt_total`: `1.37661`
  - `avg_branch_context_debt_auc`: `15.39974`
  - `avg_peak_context_branch_transform_debt_total`: `1.24128`
  - `avg_context_branch_transform_debt_auc`: `14.18084`
  - `avg_final_branch_context_debt_total`: `0.67558`
  - `avg_final_context_branch_transform_debt_total`: `0.61720`

Interpretation:

- `Task B -> Task A` does not just end with more residual contradiction burden.
- It accumulates a substantially larger debt load over the whole transfer process.
- This strongly supports the idea that Task B leaves a stickier maintained state.

### 2. The “resists relaxation” story is only partly true

Warm-full half-relief timing:

- `Task A -> Task B`
  - `avg_branch_context_half_relief_cycle`: `17.75`
  - `avg_context_branch_transform_half_relief_cycle`: `17.5`

- `Task B -> Task A`
  - `avg_branch_context_half_relief_cycle`: `15.83333`
  - `avg_context_branch_transform_half_relief_cycle`: `17.16667`

Interpretation:

- `Task B -> Task A` does **not** appear to relax more slowly after peak debt in a simple monotonic sense.
- Its branch-context debt peak is larger and later, but once the system has clearly recognized the contradiction, it can reduce that debt at roughly similar speed, and in one measure slightly faster.
- So the better interpretation is:
  - `Task B -> Task A` is harder because it reaches a larger contradiction peak and carries more debt mass overall,
  - not because its debt necessarily decays more slowly after the peak.

### 3. The larger debt burden coincides with weaker transfer performance

Warm-full final task performance:

- `Task A -> Task B`
  - `avg_final_mean_bit_accuracy`: `0.62730`
  - `avg_final_exact_matches`: `8.91667`

- `Task B -> Task A`
  - `avg_final_mean_bit_accuracy`: `0.61804`
  - `avg_final_exact_matches`: `7.50000`

Interpretation:

- The transfer direction with the larger contradiction burden is also the one with worse final task performance.
- That makes the contradiction load look causally relevant rather than merely epiphenomenal.

### 4. Early-cycle dynamics already separate the two directions

In the first eight warm-full transfer cycles:

- `Task A -> Task B` starts with stronger positive credit buildup and much lower early contradiction debt.
- `Task B -> Task A` develops branch-context debt more quickly by cycles `4-7`, even while cumulative `context_1` accuracy initially looks healthy.

Interpretation:

- The system can look superficially competent early in `Task B -> Task A` while already accumulating a heavier contradiction burden underneath.
- This fits the idea that Task B’s carryover is not merely “wrong,” but structurally sticky.

## Conclusion

The time-course analysis strengthens the structural-asymmetry interpretation:

- `Task B -> Task A` carries a higher contradiction burden over transfer, with larger peaks, larger debt area-under-curve, and larger final residual debt.
- But the phrase “resists relaxation” needs precision.
- The system is not obviously slower to relax **after** it peaks. Instead, it reaches a deeper contradiction state and therefore has more to unwind.

That means the best current interpretation is:

- Task B creates a more metabolically difficult and contradiction-heavy maintained state.
- Reverse transfer out of that state is harder because the system falls into a deeper local conflict basin, not simply because its demotion dynamics are too slow.

## Validation

- `python -m py_compile analyze_transfer_timecourse.py`
- Inline 12-seed aggregate run via `python -`

## Next Steps

- Add a combined “credit minus debt” time-course signal so we can measure when each transfer direction crosses from contradiction-dominated to scaffold-dominated dynamics.
- Use that crossing point as a sharper transfer-readiness marker than final-state debt alone.
