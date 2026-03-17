# 2026-03-16 - GPT-5 Codex - Phase 8 Source Pre-Effective Route Drive Trace

## Intent

Follow the latent timecourse diagnosis by tuning the hidden-context source selector so source-sequence guidance preserves early stability without falling back toward identity or wrong-family transforms.

## Files Updated

- `Phase 8/phase8/selector.py`
- `Phase 8/tests/test_phase8.py`

## What Changed

- Added a source-only pre-effective route drive in `Phase8Selector._score_route(...)`:
  - active only when:
    - context is hidden,
    - effective context is not yet available,
    - source-sequence guidance is available,
    - and the acting node is the source.
- Increased positive score for task-compatible transforms under that regime.
- Added stronger penalties for:
  - identity routing at the source during the same regime,
  - wrong-family transforms under the same regime.
- Added a focused regression test confirming that source-sequence parity cues can drive the selector toward the expected Task A transform family in a hidden-context source-only setup.

## Validation

- `python -m unittest tests.test_phase8 -q`
- `python compare_latent_context.py`
- inline `analyze_latent_context_timecourse(...)` on:
  - `cvt1_task_a_stage1`
  - `cvt1_task_b_stage1`
  - seeds `13, 23, 37, 51, 79`

## Main Findings

### 1. The selector behavior is cleaner and the regression is real

- The new focused test passes and confirms the source selector now chooses the expected Task A transform family from source-sequence parity in the hidden-context source-only case.
- Full Phase 8 tests remain green.

### 2. Cold hidden `Task A` did not materially improve at the aggregate level

Aggregate latent benchmark with source-sequence enabled remained:

- `Task A`
  - latent exact matches: `3.2`
  - latent bit accuracy: `0.4778`

This is effectively unchanged from the prior richer-source-adapter state.

### 3. The earlier timecourse diagnosis still stands

The latent timecourse aggregate for cold hidden `Task A` still shows:

- strong reduction in pre-effective instability with source-sequence guidance,
- but weaker final effective-context confidence than the no-source-sequence latent run.

Key numbers stayed:

- without source sequence:
  - `avg_final_effective_context_confidence`: `0.86355`
  - `avg_final_mean_bit_accuracy`: `0.4889`

- with source sequence:
  - `avg_final_effective_context_confidence`: `0.37388`
  - `avg_final_mean_bit_accuracy`: `0.47778`

## Conclusion

This pass improved the **source-side transform-choice policy** and removed an undesirable identity/wrong-family weakness, but it did **not** solve the cold hidden `Task A` aggregate failure.

That suggests the dominant remaining bottleneck is not simply:

- source transform-family choice,
- or source route willingness.

The stronger remaining hypothesis is:

- latent confidence is being destabilized later in the run by downstream or cross-cycle evidence mixing,
- even after the source begins with a cleaner transform commitment.

## Suggested Next Step

- Add source-versus-downstream latent evidence diagnostics so we can see whether confidence collapse in cold hidden `Task A` is being caused by:
  - source route evidence,
  - downstream route evidence,
  - or downstream feedback pulses overriding an initially cleaner source hypothesis.
