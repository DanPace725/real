# 2026-03-16 - GPT-5 - Phase 8 Energy-Governed Morphogenesis Trace

## Intent

Shift Level 2 morphogenesis away from mostly trigger-based growth/prune rules and toward local metabolic accounting: structure should grow when it can afford itself and survive when it remains net-positive.

## Structural Changes

- Added node-level energy ledgers to `TopologyState`:
  - route spend,
  - maintenance spend,
  - growth spend,
  - feedback income,
  - ATP/reward EMAs,
  - recent net energy,
  - recent structural value,
  - positive/negative energy streaks.
- Added edge-level energy ledgers:
  - traversal count,
  - route spend,
  - maintenance spend,
  - feedback income,
  - recent edge value,
  - negative-value streaks.
- Routed the runtime into those ledgers:
  - `route_signal()` records route spend on both node and edge,
  - `advance_feedback()` records feedback income on both node and edge,
  - maintenance actions record node/edge upkeep spend,
  - morphogenesis actions record growth spend.

## Policy Shift

- Growth is now gated by:
  - immediate ATP availability,
  - recent positive node energy,
  - positive recent structural value,
  - and contradiction/overload as motive rather than sole authority.
- Pruning now prefers edges that have stayed energetically net-negative, with idle time as a supporting signal.
- Apoptosis now requires sustained negative node value and structural isolation/dormancy pressure rather than only raw isolation.

## Diagnostics

- Added summary metrics for:
  - `mean_dynamic_node_value`
  - `mean_dynamic_net_energy`
  - `mean_dynamic_edge_value`
- Added corresponding morphogenesis benchmark aggregates.

## Validation Snapshot

- `cvt1_task_b_stage1` aggregate under morphogenesis:
  - fixed exact matches: `3.0`
  - growth exact matches: `3.2`
  - fixed bit accuracy: `0.4389`
  - growth bit accuracy: `0.4445`
  - earned growth rate: `0.2`
  - growth win rate: `0.2`
- `Task A -> Task B` transfer aggregate under morphogenesis:
  - fixed exact matches: `7.6`
  - growth exact matches: `8.0`
  - fixed bit accuracy: `0.5833`
  - growth bit accuracy: `0.6055`
  - earned growth transfer rate: `0.8`
  - growth transfer win rate: `0.6`

## Remaining Frictions

- Growth still realizes more often than it earns, especially on cold `Task B`.
- Overload-focused scenarios still need stronger energy-aware branch relief if we want `branch_pressure` and `sustained_pressure` to convert budding into useful structure.
