# Phase 8 Substrate Promotion Trace

## Date

2026-03-16

## Timestamp

2026-03-16T09:49:38-07:00

## Model

GPT-5 Codex

## Prompt

Promote repeated context-bound credit into stronger durable context-specific action support so more of the stability lives in substrate-only carryover too.

## Files Touched

- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/node_agent.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- each connection substrate now keeps a local accumulator for repeated context-bound feedback keyed by:
  - neighbor
  - transform
  - context bit
- when repeated local credit crosses threshold, the substrate now:
  - promotes durable context-specific action support
  - reinforces the associated edge support so substrate-only carryover inherits a usable routing scaffold rather than isolated action memory
- `NativeSubstrateSystem` now routes delivered feedback events back into each node agent locally, and each node only updates its own substrate from its own returned feedback path
- substrate state persistence now carries the local context-credit accumulator along with the promoted supports

## Validation

Executed:

- `python -m py_compile "Phase 8\\phase8\\substrate.py" "Phase 8\\phase8\\node_agent.py" "Phase 8\\phase8\\environment.py" "Phase 8\\tests\\test_phase8.py"`
- `python -m unittest "Phase 8\\tests\\test_phase8.py"`
- `python "Phase 8\\run_phase8_demo.py" --mode comparison --scenario cvt1_task_a_stage1 --seed 51`
- `python "Phase 8\\compare_cold_warm.py"`

All commands passed.

## Result

This pass mainly improved substrate-only carryover.

For seed `51` on `cvt1_task_a_stage1`:

- cold exact matches: `8`
- warm full exact matches: `9`
- warm substrate-only exact matches: `9`
- cold mean bit accuracy: `0.6944`
- warm full mean bit accuracy: `0.7222`
- warm substrate-only mean bit accuracy: `0.7222`

In the 5-seed aggregate for `cvt1_task_a_stage1`:

- exact matches: `7.2` cold -> `8.2` warm full -> `7.4` warm substrate-only
- mean bit accuracy: `0.6278` cold -> `0.6722` warm full -> `0.6333` warm substrate-only
- mean route cost: `0.04266` cold -> `0.03882` warm full -> `0.03662` warm substrate-only

At the overall multi-scenario level:

- warm substrate-only exact matches improved from below cold to roughly at parity overall (`1.8` cold -> `1.85` warm substrate-only)
- warm substrate-only bit accuracy also moved back to slight overall advantage (`0.1569` cold -> `0.1583` warm substrate-only)

## Interpretation

The maintained substrate is now carrying more of the computational structure on its own.

- full carryover still performs best
- substrate-only carryover is no longer collapsing as sharply on CVT-1
- the remaining gap suggests episodic survivors still contribute useful disambiguation, but the substrate is starting to absorb a meaningful share of that role

## Immediate Next Step

- inspect which context-specific supports are still being promoted but not maintained strongly enough
- then begin the first Task B transfer loop with both full and substrate-only carryover paths, because the substrate-only path is now much closer to worth testing
