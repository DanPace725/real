# Phase 8 Branch-Transform Competition Trace

## Date

2026-03-16

## Timestamp

2026-03-16T12:39:09.2445974-07:00

## Model

GPT-5 Codex

## Prompt

Move forward on the branch-transform competition mechanism by adding a selector-conditioned diagnostic and a local selector retune aimed at collapsing guided conflict under contradiction.

## Inputs Reviewed

- `Phase 8/phase8/selector.py`
- `Phase 8/analyze_transfer_timecourse.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/docs/trails/20260316_phase8_balance_conditioned_selector_trace.md`

## Work Completed

- Extended `analyze_transfer_timecourse.py` so negative-balance windows now capture:
  - branch shares
  - transform shares
  - mode shares
  - top branch-transform pair counts
  - mean route coherence
  - mean route delta
- Added a local selector competition pass in `phase8/selector.py`:
  - candidate evidence is compared across available route actions,
  - contradiction burden is computed locally from action/branch/context debt,
  - multi-candidate guided conflicts can now be penalized toward the dominant local branch-transform option.
- Added a regression in `tests/test_phase8.py`:
  - `test_selector_resolves_multi_candidate_conflict_toward_dominant_context_branch_evidence`

## Main Findings

### 1. The diagnostic is genuinely useful

Negative-balance selector summaries confirmed:

- `Task A -> Task B` remains dominated by `xor_mask_1010` during guided contradiction.
- `Task B -> Task A` stays spread across `rotate_left_1`, `xor_mask_0101`, and `xor_mask_1010`.
- Guided mode still dominates in both directions.

Interpretation:

- The transfer problem is a structured guided-competition problem, not a lack-of-exploration problem.

### 2. The first arbitration pass did not materially improve the hard direction

On the 5-seed transfer pair check:

- `Task A -> Task B`
  - warm full: `7.6` exact, `0.5833` bit accuracy
- `Task B -> Task A`
  - warm full: `9.0` exact, `0.6722` bit accuracy
  - cold: `10.0` exact, `0.7333` bit accuracy

Interpretation:

- `Task B -> Task A` is still negative relative to cold start.
- The selector competition rule is coherent and test-backed locally, but it did not change the aggregate reverse-transfer result.

### 3. The negative result is informative

The competition diagnostic stayed essentially unchanged after the retune. That suggests one of two things:

- the new arbitration rule rarely engages in the real transfer workload, or
- the key conflict is not simply “too many plausible candidates,” but a deeper issue in how local coherence/evidence remains good enough for several incompatible guided choices at once.

## Conclusion

This pass successfully strengthened the diagnostic surface and produced a clean local selector regression, but it did **not** solve the reverse-transfer asymmetry.

That is still useful progress:

- we now know the branch-transform competition hypothesis is real,
- and we also know a simple selector-side arbitration tweak is not sufficient to fix it in aggregate.

## Validation

- `python -m py_compile phase8\\selector.py analyze_transfer_timecourse.py tests\\test_phase8.py`
- `python -m unittest tests.test_phase8`
- inline 5-seed `A -> B` and `B -> A` pair evaluation via `compare_transfer_matrix`
- inline `analyze_transfer_timecourse` aggregate run

## Next Steps

- Make branch-transform competition observable in the runtime task diagnostics, not only the offline analyzer.
- Target the conflict one layer deeper than route ranking: either coherence shaping or feedback-binding so incompatible guided candidates stop remaining locally “good enough” at the same time.
