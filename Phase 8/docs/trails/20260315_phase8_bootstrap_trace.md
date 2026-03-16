# Phase 8 Bootstrap Trace - 2026-03-15

## Intent

Start Phase 8 with the smallest implementation that still respects the new architecture:

- each node must be a REAL agent
- memory must sit on maintained local structure
- ATP feedback must move upstream locally
- no global optimizer should appear anywhere in the loop

## Hypotheses tested during design

1. Reuse `Phase 4/real_core/RealCoreEngine` directly rather than building a second agent loop.
Result: accepted. The existing engine already has the right hooks through `MemorySubstrateProtocol` and `DomainMemoryBinding`.

2. Put slow memory on edges instead of only on abstract dimensions.
Result: accepted. This is the clearest way to make routing cheaper after successful histories without introducing global state.

3. Use the Phase 7 substrate wholesale.
Result: partially rejected for the first slice. Phase 7 has useful mechanics, but its implementation is broader than needed for the first local-routing scaffold. The new Phase 8 substrate borrows the maintenance and decay logic while staying tightly scoped to neighbor edges.

4. Enforce ATP walls through `RealCoreEngine.session_budget`.
Result: rejected for now. Node ATP needs to both decrease and refill from upstream feedback during a session, so the environment tracks ATP locally and only exposes affordable actions to the engine.

5. Implement the first environment as a trivial routing graph.
Result: accepted. The initial environment now consists of local inboxes, edge routing, inhibition, and hop-by-hop feedback pulses from sink to source.

## Frictions encountered

- `Phase 4` assumes dimension-keyed substrate state, while Phase 8 needs connection-keyed state.
- `session_budget` is one-way depletion, but Phase 8 needs local ATP replenishment.
- The repo root in this workspace is not a git root, so validation and diffing need to be done directly by file path and test commands.

## Decisions promoted to maintained substrate

- Phase 8 node agents should continue to instantiate `RealCoreEngine`.
- Node observations should remain strictly local: node state plus direct neighbors only.
- Successful delivery should create sequential upstream ATP pulses, never a global reward write.
- Tests should encode these constraints early so later refactors cannot quietly reintroduce global control.
