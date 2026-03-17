# Episodic Trace ($H_e$) - Latent Diagnostics And Source Sequence Ablation

**Author:** GPT-5 Codex  
**Timestamp:** 2026-03-16T21:28:00-07:00  
**Context:** Implemented the next latent-context step suggested by the GPT-5.2 trail: add failure-class diagnostics and make the source-local sequence cue ablatable.

## What Was Added

- Added a latent failure taxonomy to `task_diagnostics`:
  - `route_wrong_transform_potentially_right`
  - `route_right_transform_wrong`
  - `transform_unstable_across_inferred_context_boundary`
  - `delayed_correction`
- Exposed `source_sequence_context_enabled` as a system/environment flag.
- Updated `compare_latent_context.py` to accept the source-sequence toggle.
- Added `compare_latent_ablations.py` to compare:
  - hidden context with no source sequence cue
  - hidden context with source-local sequence cue

## Verification

- `python -m unittest tests.test_phase8 -q` -> `Ran 79 tests ... OK`
- `python compare_latent_ablations.py`

## Main Readout

### Hidden `Task A`

- no source sequence: exact `3.6`, bit accuracy `0.4889`
- with source sequence: exact `3.0`, bit accuracy `0.4611`

### Hidden `Task B`

- no source sequence: exact `3.0`, bit accuracy `0.4611`
- with source sequence: exact `4.6`, bit accuracy `0.5333`

### Hidden `Task A -> Task B` transfer

- no source sequence: exact `5.6`, bit accuracy `0.5111`
- with source sequence: exact `7.6`, bit accuracy `0.6000`

## Diagnostic Interpretation

- `wrong_transform_family` stayed near `0.0` in these latent runs.
- The dominant latent failure signature is `transform_unstable_across_inferred_context_boundary`, especially on cold hidden-context runs.
- The source-local sequence cue helped most on:
  - `Task B`
  - warm transfer
- It did **not** solve cold hidden `Task A`, and slightly worsened it in aggregate.

## Conclusion

The new diagnostics suggest the main latent problem is not simple wrong-family routing. It is instability and correction timing under hidden-state ambiguity. The source-local sequence cue is useful, but mostly for transfer and for one side of the task family. Cold hidden `Task A` still needs a better disambiguation signal than the current source-parity cue.
