# 2026-03-16 - GPT-5 - Phase 8 Morphogenesis Benchmark Trace

## Intent

Move Phase 8 Level 2 from "topology mutation exists" toward "topology mutation can be measured against fixed-topology baselines."

## Findings

- The first Level 2 scaffold was structurally complete, but enabled morphogenesis could still prune static scaffold edges and often never selected budding actions during workloads.
- Existing comparison scripts (`compare_cold_warm.py`, `compare_task_transfer.py`, `evaluate_transfer_asymmetry.py`) already provided the reporting pattern needed for a dedicated morphogenesis benchmark.
- Under a calibrated evaluation config (`enabled=True`, checkpoint interval `6`, max dynamic nodes `4`, contradiction threshold `0.2`, overload threshold `0.2`, ATP surplus threshold `0.4`), `cvt1_task_b_stage1` and `Task A -> Task B` transfer runs can now produce actual bud events, while the fixed scaffold remains intact.

## Changes

- Updated selector priority so locally justified growth actions can beat maintenance instead of waiting indefinitely behind it.
- Restricted prune proposals and auto-prune to dynamic edges so Level 2 does not cannibalize the initial scaffold before new structure proves useful.
- Added `compare_morphogenesis.py` to compare fixed versus morphogenesis-enabled runs across workload and transfer scenarios, including "earned growth" and "growth win" diagnostics.
- Added tests covering:
  - static scaffold preservation under enabled morphogenesis,
  - structural benchmark reporting,
  - "earned growth" versus mere topology expansion.

## Validation

- Targeted morphogenesis comparison tests passed.
- Full Phase 8 regression suite was rerun after these changes.

## Open Edges

- Branch-pressure and sustained-pressure workloads still do not reliably trigger budding under the calibrated benchmark config.
- The benchmark can now show when growth occurs, but it does not yet prove aggregate performance wins; transfer currently shows earned growth more readily than workload-level wins.
