# Phase 8 Carryover Maintenance Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:35:36-07:00

## Model

GPT-5 Codex

## Prompt

Keep working on developing the carryover.

## Files Touched

- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/run_phase8_demo.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- edge-local substrate can now explicitly maintain active transform and context-specific action supports, not just edge supports
- substrate now exposes maintenance diagnostics that distinguish recently maintained support from support that is only persisting by decay timing
- `route_transform:*` execution now spends the correct context-shaped cost instead of ignoring context-specific action support at execution time
- selector maintenance pressure now considers active action-support erosion in addition to edge erosion
- summaries now expose:
  - `substrate_maintenance`
  - `context_action_supports`
- the demo now prints context-specific transform supports and substrate maintenance diagnostics during comparison and detailed runs

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\adapters.py" "Phase 8\\phase8\\selector.py" "Phase 8\\phase8\\environment.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## Result

This pass strengthened carryover in two ways:

- the slow layer is more structurally real because action support now has an explicit maintenance path
- the task-specific carryover is applied more faithfully because context-shaped transform costs are now used at execution time, not only during action availability checks

On `cvt1_task_a_stage1`, seed `51` moved from:

- cold exact matches: `9`
- warm full exact matches: `12`
- cold mean bit accuracy: `0.75`
- warm full mean bit accuracy: `0.8056`

In the 5-seed aggregate for `cvt1_task_a_stage1`, warm full improved to:

- exact matches: `8.8` cold -> `11.4` warm full
- mean bit accuracy: `0.7222` cold -> `0.7834` warm full
- mean route cost: `0.04872` cold -> `0.04462` warm full

## Interpretation

This is a more convincing carryover step than the previous one.

- warm full now helps both exact task success and mean task accuracy in the Stage 1 computational workload
- the substrate is beginning to look less like passive residue and more like an actively maintained local bias field

The remaining limitation is that this improvement is still concentrated in Task A. The next meaningful pressure is making sure context-specific transform support remains visible and stable enough to support transfer rather than just replaying a single learned tendency.

## Immediate Next Step

- inspect the new context-specific maintenance diagnostics during warm runs
- strengthen promotion and maintenance of context-specific transform support where it is active but under-maintained
- then start the first Task B transfer loop once Task A warm gains remain stable across repeated comparisons
