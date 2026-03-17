# 2026-03-16 - GPT-5 Codex - Phase 8 Latent Timecourse Trace

## Intent

Adapt the existing timecourse analysis so hidden-context runs can be inspected cycle by cycle, with special attention to cold latent `Task A` and source-local sequence behavior.

## Files Updated

- `Phase 8/analyze_transfer_timecourse.py`
- `Phase 8/tests/test_phase8.py`

## What Changed

- Extended `analyze_transfer_timecourse.py` with a latent-context timecourse path:
  - cold visible runs,
  - cold latent runs without the source-sequence adapter,
  - cold latent runs with the source-sequence adapter.
- Added source-local cycle capture without mutating runtime state:
  - source ATP and ATP ratio,
  - latent context availability/confidence,
  - effective context confidence,
  - source-sequence confidence,
  - context-promotion readiness,
  - per-cycle diagnostic deltas for:
    - `wrong_transform_family`
    - `route_wrong_transform_potentially_right`
    - `route_right_transform_wrong`
    - `transform_unstable_across_inferred_context_boundary`
    - `delayed_correction`
    - `stale_context_support_suspicions`
- Added latent timecourse summaries and selector-window aggregates for:
  - low-confidence cycles,
  - pre-effective-context cycles,
  - instability cycles.
- Added unit tests for the latent timecourse summary and aggregate behavior.

## Validation

- `python -m unittest tests.test_phase8 -q`
- `python -m py_compile analyze_transfer_timecourse.py`
- inline `analyze_latent_context_timecourse(...)` runs over seeds:
  - `13, 23, 37, 51, 79`

## Main Findings

### 1. Cold hidden `Task A` is not failing because latent context never forms

Across the five-seed aggregate:

- without source sequence:
  - `avg_first_effective_context_cycle`: `1.0`
  - `avg_final_effective_context_confidence`: `0.86355`
  - `avg_final_mean_bit_accuracy`: `0.4889`
  - `avg_final_exact_matches`: `3.6`

- with source sequence:
  - `avg_first_effective_context_cycle`: `1.0`
  - `avg_final_effective_context_confidence`: `0.37388`
  - `avg_final_mean_bit_accuracy`: `0.47778`
  - `avg_final_exact_matches`: `3.2`

Interpretation:

- The system already forms an effective latent context very early on cold hidden `Task A`.
- The problem is not delayed context availability.
- The problem is that the source-sequence adapter appears to make the eventual effective context less stable and less trustworthy, even though it helps early ambiguity.

### 2. The source-sequence adapter strongly reduces early instability on cold hidden `Task A`

For cold hidden `Task A`:

- without source sequence:
  - `avg_pre_effective_instability_events`: `6.2`

- with source sequence:
  - `avg_pre_effective_instability_events`: `1.2`

Interpretation:

- The richer source-local adapter is doing real work.
- It suppresses much of the early transform instability before the latent state is effectively settled.
- That confirms the adapter is not useless; it is solving one part of the problem.

### 3. The benefit is being paid for with much lower early routing activity

For cold hidden `Task A`, pre-effective-context selector windows:

- without source sequence:
  - `total_route_actions`: `69`
  - `total_rest_actions`: `45`
  - `total_invest_actions`: `24`
  - route transform share:
    - `rotate_left_1`: `0.6087`
    - `xor_mask_1010`: `0.36232`

- with source sequence:
  - `total_route_actions`: `18`
  - `total_rest_actions`: `70`
  - `total_invest_actions`: `50`
  - route transform share:
    - `rotate_left_1`: `0.38889`
    - `xor_mask_1010`: `0.44444`
    - `xor_mask_0101`: `0.16667`

Interpretation:

- The source-sequence adapter is not simply “committing earlier.”
- It is shifting the system into a much more conservative early regime:
  - far fewer route actions,
  - much more resting,
  - much more investment.
- That likely explains why early instability drops while final cold-task performance still gets worse.

### 4. The same pattern is milder on cold hidden `Task B`

For cold hidden `Task B`:

- source sequence reduced `avg_pre_effective_instability_events` from `6.4` to `4.8`
- reduced `avg_low_confidence_cycle_count` from `4.2` to `3.2`
- improved `avg_final_exact_matches` from `3.2` to `3.4`
- kept `avg_final_mean_bit_accuracy` flat at `0.47222`

Interpretation:

- The source-sequence adapter is directionally helpful on cold hidden `Task B`.
- The cold hidden `Task A` failure looks more specific than a general latent-context collapse.

## Conclusion

The new timecourse analysis surfaces a sharper diagnosis for cold hidden `Task A`:

- The source-sequence adapter helps with the **early instability** problem.
- But it also appears to induce an **over-conservative pre-effective regime** that reduces routing throughput and leaves final latent/effective context confidence worse.
- So the next tuning target should not be “make context form earlier.”
- It should be “preserve the early-stability benefit while restoring healthy early route exploration/commitment.”

## Suggested Next Step

- Retune hidden-context source behavior so source-sequence evidence biases transform choice without suppressing early route volume as strongly.
- The most direct path is probably a lighter pre-effective penalty on routing/rest balance at the source, rather than another increase in transform commitment strength.
