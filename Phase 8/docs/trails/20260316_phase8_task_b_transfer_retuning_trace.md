# Phase 8 Task B Transfer Retuning Trace

## Date

2026-03-16

## Timestamp

2026-03-16T10:05:27-07:00

## Model

GPT-5 Codex

## Prompt

Ok, let's see how that works

## Intent

Retune Task B adaptation so full carryover can relax stale Task A context-transform bias more quickly without discarding the useful route and substrate scaffold built during Task A.

## Files Touched

- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- strengthened mismatch demotion inside the local connection substrate so contradictory context feedback reduces promoted context-action support more aggressively and clears the local promotion accumulator faster
- retuned returning task feedback so low-match context feedback relaxes generic and context-specific transform credit instead of continuing to reinforce stale Task A behavior
- gated selector trust in episodic route history using maintained context evidence:
  - old history is now trusted much more when the current context-specific substrate and returned credit still support it
  - old history is trusted much less when current maintained context evidence is weak
- added regressions for:
  - low-match context feedback demoting local context action support
  - low-match feedback relaxing stale transform and context credit on the returning node

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\environment.py" "Phase 8\\phase8\\selector.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode transfer --seed 51`
- `python "Phase 8\\compare_task_transfer.py"`

All commands passed.

## Result

Task B transfer is now less stuck than the initial kickoff pass, but the result is still mixed.

For seed `51`:

- cold Task B: `0` exact matches, `0.2222` mean bit accuracy
- warm full Task B: `1` exact match, `0.2778` mean bit accuracy
- warm substrate-only Task B: `5` exact matches, `0.5278` mean bit accuracy

Across 5 seeds:

- cold Task B exact matches averaged `2.2`
- warm full Task B exact matches averaged `3.0`
- warm substrate-only Task B exact matches averaged `2.4`

- cold Task B mean bit accuracy averaged `0.3778`
- warm full Task B mean bit accuracy averaged `0.3722`
- warm substrate-only Task B mean bit accuracy averaged `0.4056`

So after the retuning:

- full carryover now beats cold on Task B exact matches in aggregate
- full carryover still does not beat cold on mean bit accuracy
- substrate-only carryover remains more behaviorally plastic and now beats cold on mean bit accuracy

## Interpretation

This suggests the core failure mode has shifted.

The system is no longer simply replaying the old Task A odd-context branch blindly. Full carryover can now adapt enough to recover more exact Task B hits. But the remaining error pattern looks like partial-match drift: useful route and transform scaffold is present, yet transform precision under the changed odd-context rule is still not stable enough.

The selector-gating pass also reinforces a Phase 7-style lesson: episodic history should not dominate when maintained substrate no longer endorses it. That principle now has a real local implementation in the Phase 8 fast loop.

## Immediate Next Step

- improve Task B mean bit accuracy by penalizing partial-match persistence more directly than exact-match failure alone
- add clearer per-context transfer diagnostics so we can see whether remaining error is coming from wrong branch choice, wrong transform reuse, or excessive identity/partial-match fallback
- keep full carryover aligned with maintained substrate rather than letting episodic survivors act like a passive archive
