# Phase 8 Carryover Trace - 2026-03-15

## Intent

Take the first routing scaffold and make it remember across sessions in a way that matches Phase 4.5:

- useful route histories should promote into maintained substrate
- node state should support warm starts instead of blank restarts

## Hypotheses tested

1. A Phase 8-specific consolidation pipeline can live on top of the Phase 4.5 `BasicConsolidationPipeline`.
Result: accepted. The new pipeline retains the same episodic pruning behavior and adds promotion into edge support and edge patterns when the substrate is a Phase 8 connection substrate.

2. Route history is enough to derive useful promotion targets even without a global reward or explicit path planner.
Result: accepted for the current slice. Positive `route:*` histories are sufficient to seed edge support and create route attractor patterns.

3. Cross-session carryover should be stored per node rather than as one global monolith.
Result: accepted. Each node now exports its own Phase 4.5 carryover package, while the system manifest stores environment runtime state and cycle position.

## Frictions encountered

- Windows temp directories were outside the writable workspace sandbox here, so persistence tests had to be moved into a repo-local temp folder.
- `RealCoreEngine` supports carryover cleanly, but in-session consolidation still needed an explicit trigger inside the Phase 8 node wrapper because the global system is stepped cycle-by-cycle rather than via `run_session()`.

## Decisions reinforced

- Promotion remains local: route history only changes the node that lived that history.
- Warm starts restore node episodic survivors, substrate state, and local runtime environment, not a hidden global planner.
- Phase 8 continues to extend `real_core` rather than diverging from it.
