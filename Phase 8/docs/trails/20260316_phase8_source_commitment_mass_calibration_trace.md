# 2026-03-16 - GPT-5 Codex - Phase 8 Source Commitment Mass Calibration Trace

## Intent

Continue the source-only latent commitment work by:

- letting source feedback reinforce source route commitment when they agree,
- allowing source feedback to rewrite weak source route commitment when they clearly disagree,
- and preventing the source from becoming maximally confident from only one or two route events by scaling confidence with total evidence mass.

## Files Updated

- `Phase 8/phase8/environment.py`
- `Phase 8/tests/test_phase8.py`

## What Changed

- Added source-only commitment alignment in `LatentContextTracker`:
  - source route and source feedback now reinforce one another when they support the same inferred context,
  - and strong source feedback can damp a weaker conflicting source-route hypothesis.
- Added evidence-mass calibration for latent confidence:
  - confidence is no longer only directional purity,
  - it is now `purity * evidence_scale`,
  - so thin evidence does not immediately appear fully trustworthy.
- Added tests covering:
  - source feedback reinforcing source route commitment,
  - backward-compatible latent tracker snapshots and timecourse summaries.

## Validation

- `python -m unittest tests.test_phase8 -q`
- `python -m py_compile phase8\\environment.py tests\\test_phase8.py`
- `python compare_latent_context.py`
- inline `analyze_latent_context_timecourse(...)` on cold hidden `cvt1_task_a_stage1`

## Main Findings

### 1. Cold hidden `Task A` improved meaningfully

Latent aggregate with source-sequence enabled:

- before this pass:
  - latent exact matches: `3.2`
  - latent bit accuracy: `0.4778`

- after this pass:
  - latent exact matches: `4.4`
  - latent bit accuracy: `0.5167`

Timecourse for cold hidden `Task A`:

- with source sequence:
  - `avg_final_latent_context_confidence`: `0.84795`
  - `avg_final_effective_context_confidence`: `0.79808`
  - `avg_final_source_route_context_confidence`: `0.96705`
  - `avg_final_source_feedback_context_confidence`: `0.82074`
  - `avg_final_mean_bit_accuracy`: `0.51668`
  - `avg_final_exact_matches`: `4.4`

### 2. Cold hidden `Task B` improved too

Latent aggregate with source-sequence enabled:

- latent exact matches: `4.4`
- latent bit accuracy: `0.5167`

This is better than the previous hidden-context source-sequence result.

### 3. The tradeoff is latent transfer regression

Latent `Task A -> Task B` transfer aggregate after this pass:

- visible exact matches: `6.2`
- latent exact matches: `5.8`
- visible bit accuracy: `0.5056`
- latent bit accuracy: `0.55`

Interpretation:

- cold hidden performance improved,
- but transfer no longer shows the strong latent carryover benefit seen in the earlier source-sequence tuning.
- The new source commitment is helping cold runs stabilize, but it also appears to make the source less adaptable during transfer.

## Conclusion

This was a productive step:

- the original cold hidden `Task A` bottleneck moved in the right direction,
- the source tracker is now better calibrated,
- and the system is less brittle to thin early evidence.

But the new balance introduces a real tradeoff:

- stronger source commitment improves cold hidden tasks,
- while latent transfer becomes less flexible.

## Suggested Next Step

- Keep this mass-calibrated source commitment foundation.
- Next tuning should be transfer-aware:
  - preserve source commitment on cold hidden runs,
  - but relax or reset source-side commitment faster when warm carryover enters a new task regime.
