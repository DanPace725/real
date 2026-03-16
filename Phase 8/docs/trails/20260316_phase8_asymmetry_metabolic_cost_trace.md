# Phase 8 Transfer Asymmetry + Metabolic Cost Trace

## Date

2026-03-16

## Timestamp

2026-03-16T12:07:17.7718491-07:00

## Model

GPT-5 Codex

## Prompt

Consider recent traces in the repo in `slow_layer` and from GPT-5.2, and evaluate whether the Task B asymmetry may be structural. Specifically: compare whether Task B leaves stronger branch-context debt that resists relaxation, and whether Task B costs more ATP to stabilize during initial training than Task A.

## Inputs Reviewed

- `Phase 8/slow_layer/20260316_H_c_consolidation_task_b_diagnostics.md`
- `Phase 8/slow_layer/20260316_H_c_consolidation_transfer_matrix.md`
- `Phase 8/slow_layer/20260316_H_c_consolidation_gpt52_evaluation.md`
- `Phase 8/docs/trails_gpt52/20260316_phase8_progress_review_and_next_steps_trace.md`
- `Phase 8/compare_cold_warm.py`
- `Phase 8/compare_task_transfer.py`
- `Phase 8/compare_transfer_matrix.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/models.py`

## Work Completed

- Added `Phase 8/evaluate_transfer_asymmetry.py` to measure:
  - initial-training criterion attainment and cost-to-criterion,
  - normalized metabolic cost during training,
  - residual branch-context and context-branch-transform debt/credit after training,
  - and warm-full residual commitment after `Task A -> Task B` and `Task B -> Task A`.
- Ran the evaluator across 12 seeds:
  - `5, 13, 17, 23, 29, 37, 43, 51, 61, 79, 87, 97`

## Main Findings

### 1. Task B is harder and less metabolically efficient to learn than Task A

Across 12 seeds:

- `Task A`
  - `criterion_hits`: `2/12`
  - `avg_cost_to_criterion`: `3.96085`
  - `avg_total_action_cost`: `5.57325`
  - `avg_action_cost_per_exact_match`: `1.04041`
  - `avg_action_cost_per_bit_accuracy`: `8.67216`
  - `avg_source_efficiency`: `0.51354`

- `Task B`
  - `criterion_hits`: `0/12`
  - `avg_total_action_cost`: `5.68611`
  - `avg_action_cost_per_exact_match`: `2.65135`
  - `avg_action_cost_per_bit_accuracy`: `13.25337`
  - `avg_source_efficiency`: `0.32951`

Interpretation:

- Task B consumes slightly more total action cost than Task A (`+0.11286`) while producing much worse task performance.
- Task B is substantially more expensive per successful outcome:
  - `+1.61094` more action cost per exact match
  - `+4.58121` more action cost per unit bit accuracy
- This supports the user hypothesis in a qualified way: Task B is metabolically costlier to stabilize than Task A, but the cost shows up as poorer efficiency and weaker coherence, not just larger total spend.

### 2. Task B training leaves slightly more branch-context debt, but not stronger positive commitment

After initial training:

- `Task A`
  - `avg_branch_context_credit_total`: `2.48055`
  - `avg_branch_context_debt_total`: `0.48815`
  - `avg_context_branch_transform_credit_total`: `2.97227`
  - `avg_context_branch_transform_debt_total`: `0.51542`

- `Task B`
  - `avg_branch_context_credit_total`: `1.48819`
  - `avg_branch_context_debt_total`: `0.52368`
  - `avg_context_branch_transform_credit_total`: `1.89403`
  - `avg_context_branch_transform_debt_total`: `0.48801`

Interpretation:

- Task B does leave slightly more residual `branch_context_debt` than Task A (`+0.03553`).
- But Task B leaves much less positive credit than Task A.
- So the current evidence does **not** support the strongest version of the story, namely: “Task B was learned more deeply because the system invested more in a strong positive scaffold.”
- Instead, it supports a weaker and more accurate account: Task B is a more metabolically difficult task that leaves a less coherent and less efficient maintained state.

### 3. Reverse transfer out of Task B retains more contradiction burden than reverse transfer out of Task A

Warm-full carryover after transfer:

- `Task A -> Task B`
  - `avg_warm_full_exact_matches`: `8.91667`
  - `avg_warm_full_mean_bit_accuracy`: `0.62730`
  - `avg_warm_full_branch_context_debt_total`: `0.43189`
  - `avg_warm_full_context_branch_transform_debt_total`: `0.40428`

- `Task B -> Task A`
  - `avg_warm_full_exact_matches`: `7.50000`
  - `avg_warm_full_mean_bit_accuracy`: `0.61804`
  - `avg_warm_full_branch_context_debt_total`: `0.67558`
  - `avg_warm_full_context_branch_transform_debt_total`: `0.61720`

Difference (`B -> A` minus `A -> B`):

- `avg_warm_full_branch_context_debt_total`: `+0.24369`
- `avg_warm_full_context_branch_transform_debt_total`: `+0.21292`

Interpretation:

- This is the cleanest support for the “sticky trap” hypothesis.
- When the system has to reverse out of Task B, it ends up carrying substantially more contradiction debt than when it reverses out of Task A.
- That makes the transfer asymmetry look structural rather than accidental.

## Conclusion

The current evidence supports the claim that the Task B asymmetry is structural, but with an important refinement:

- **Supported:** Task B is metabolically harder and less efficient to stabilize than Task A, and reverse transfer out of Task B leaves more residual contradiction debt.
- **Not fully supported:** the idea that Task B creates a stronger *positive* maintained scaffold because the system learned it “more deeply” in a straightforwardly successful sense.

The better reading is:

- Task B is a costlier and less coherent learning regime.
- That regime leaves the system with a stickier, more contradiction-laden maintained state.
- The difficulty reversing out of Task B is therefore not obviously a bug. It may be the system correctly reflecting that some learned structures are metabolically expensive and harder to unwind.

## Validation

- `python -m py_compile evaluate_transfer_asymmetry.py`
- `python evaluate_transfer_asymmetry.py`

## Next Steps

- Add one more asymmetry pass that compares positive scaffold retention and contradiction debt side by side during transfer, not only at the end of transfer.
- Use this evaluator as the default check before making new symmetry claims about `Task A`, `Task B`, or later Stage 2 latent-context tasks.
