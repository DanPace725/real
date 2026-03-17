# Episodic Trace ($H_e$) - Richer Source Sequence Adapter

**Author:** GPT-5 Codex  
**Timestamp:** 2026-03-16T21:48:00-07:00  
**Context:** Implemented a richer source-local sequence adapter for latent-context runs, following the latent diagnostics pass.

## Goal

Replace the earlier source parity cue with a richer source-local sequence sketch that:
- helps early transform commitment under hidden context,
- stays local to the source,
- does not directly become `effective_context`,
- does not loosen context-shaped memory promotion.

## What Changed

- Extended the latent task state with source-sequence sketch fields:
  - previous input bits
  - previous parity
  - input delta bits
  - change ratio
  - repeat flag
- Exposed new source-only observation features:
  - `source_sequence_available`
  - `source_sequence_prev_parity`
  - `source_prev_bit_*`
  - `source_delta_bit_*`
  - `source_sequence_change_ratio`
  - `source_sequence_repeat_input`
  - `source_sequence_transform_hint_*`
- Changed the selector to use these as soft transform hints under hidden context, instead of turning the source sequence cue into `effective_context`.
- Left the latent context promotion gate unchanged.

## Verification

- `python -m unittest tests.test_phase8 -q` -> `Ran 79 tests ... OK`
- `python compare_latent_ablations.py`
- `python -c "from compare_latent_context import evaluate_latent_context ..."`

## Benchmark Snapshot

Default latent-context aggregate after the richer adapter:

- `Task A` latent: exact `3.2`, bit accuracy `0.4778`
- `Task B` latent: exact `3.4`, bit accuracy `0.4722`
- `Task A -> Task B` latent transfer: exact `7.4`, bit accuracy `0.6222`

## Ablation Read

Comparing no source sequence vs richer source sequence:

- `Task A`:
  - no source sequence: `3.6` / `0.4889`
  - with source sequence: `3.2` / `0.4778`
- `Task B`:
  - no source sequence: `3.2` / `0.4722`
  - with source sequence: `3.4` / `0.4722`
- transfer:
  - no source sequence: `6.0` / `0.5333`
  - with source sequence: `7.4` / `0.6222`

## Interpretation

The richer adapter helped warm latent transfer significantly and produced a small improvement on cold hidden `Task B`, but it still does not solve cold hidden `Task A`. The key improvement over the earlier parity-only version is architectural cleanliness: the source sequence sketch now informs transform choice without silently becoming a promoted context estimate.

The main remaining issue is still cold-task instability under hidden context, especially for `Task A`.
