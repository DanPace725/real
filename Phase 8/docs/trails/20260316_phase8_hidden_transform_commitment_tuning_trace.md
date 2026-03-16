# Episodic Trace ($H_e$) - Hidden Transform Commitment Tuning

**Author:** GPT-5 Codex  
**Timestamp:** 2026-03-16T21:05:00-07:00  
**Context:** Follow-up tuning pass on the latent-context bridge, focused specifically on earlier transform commitment under hidden context without loosening the promotion gate for context-shaped memory.

## Goal

Reduce `identity` fallback and get earlier non-identity transform commitment when `task_id` is visible but `context_bit` is hidden, while keeping context-memory promotion conservative.

## What Was Tried

1. Added task-compatible transform affinities to local observation.
   - Hidden-context routing now knows which transform families are admissible for the visible `task_id`.

2. Added a hidden-task selector bias.
   - Under hidden context and weak effective-context evidence, valid task transforms receive a local score bonus.
   - `identity` receives a penalty so the selector does not coast on partial-credit fallback.

3. Added a source-local sequence cue.
   - The source node now tracks the previous packet's input parity per task and exposes it as a local latent context estimate for the next packet.
   - This sequence-derived cue is only used at the source, where packet order is trustworthy.

4. Kept promotion conservative.
   - Sequence/task cues affect routing choice and effective context for scoring the selector.
   - Context-shaped substrate promotion still requires the existing stable/high-confidence gate.

## Key Finding

The first aggressive task-compatibility bias helped hidden `Task B` and warm transfer a lot, but it overcommitted hidden `Task A`.

Narrowing the sequence cue to the source and softening the task-compatibility bias produced a better middle point:

- Hidden `Task A`: still weak
- Hidden `Task B`: significantly better
- Hidden `Task A -> Task B` transfer: substantially better

## Verification

- `python -m unittest tests.test_phase8 -q` -> `Ran 78 tests ... OK`

## Benchmark Snapshot

Aggregate latent metrics after this tuning pass:

- `Task A` latent: exact matches `3.0`, bit accuracy `0.4611`
- `Task B` latent: exact matches `4.6`, bit accuracy `0.5333`
- `Task A -> Task B` latent transfer: exact matches `7.6`, bit accuracy `0.6000`

Compared with the earlier latent bridge baseline:

- `Task A` got worse.
- `Task B` improved strongly.
- transfer improved very strongly.

## Interpretation

This confirms that earlier transform commitment is real and reachable without loosening the context-promotion gate. But task-only commitment is not enough for `Task A`: it needs better disambiguation between its two valid transform families. The next likely fix is richer source-local sequence features or a more explicit sequence-state adapter, rather than stronger generic anti-identity pressure.
