# Phase 4.5 - Memory Revision Proposal

**Date:** 2026-03-15
**Status:** Proposal

## Why this update is needed

Phase 4 correctly generalized the REAL loop, but it carried forward an early and overly thin model of memory. In the current generalized core, memory is primarily episodic history plus consolidation. Phase 7 develops a stronger claim: memory is not just retained record, but maintained constraint.

If REAL is meant to become a domain-agnostic allostatic learning algorithm, then memory cannot remain an optional archive-like subsystem. It must become a structural part of how the engine perceives, spends, stabilizes, and changes.

This proposal updates the Phase 4 generalization work so that it remains aligned with the project's philosophy:

- intelligence is endogenous rather than externally imposed
- adaptation is metabolically constrained
- memory is part of what the system becomes, not only what it stores
- the algorithm remains domain-agnostic while each domain supplies its own substrate bindings

## Core revision

### Phase 4 memory model

Current implicit model:

- `H`: episodic history
- `Gamma`: consolidation of history

This is useful, but incomplete. It treats memory as a retained log.

### Revised memory model

The generalized system should treat memory as three coupled layers:

1. **Episodic trace (`H_e`)**
   What happened. Raw cycle history and short-horizon trail data.

2. **Consolidated pattern memory (`H_c`)**
   What recurs or matters. Attractors, surprises, boundaries, and promoted multi-dimensional signatures.

3. **Maintained substrate (`M_s`)**
   What now shapes perception, transition cost, and reachable state. Slow-layer infrastructure that must be actively maintained under metabolic constraint.

Consolidation (`Gamma`) is no longer just pruning. It becomes a promotion process that determines how episodic structure becomes durable constraint.

## Revised generalized tuple

The generalized REAL tuple should be updated from:

- `S`: state space
- `A`: action vocabulary
- `c`: cost model
- `O`: observation function
- `Phi`: coherence function
- `H`: episodic history
- `Psi`: selector
- `Gamma`: consolidation
- `Omega`: regulatory mesh

To:

- `S`: state space
- `A`: action vocabulary
- `M_s`: maintained substrate
- `c(a, M_s)`: cost model with memory maintenance and infrastructure costs
- `O(S, M_s)`: observation function modulated by substrate state
- `Phi(S, H_e, M_s)`: coherence function with second-order substrate health
- `H_e`: episodic history
- `H_c`: consolidated pattern memory
- `Psi(H_e, H_c, M_s)`: selector operating in a memory-shaped action landscape
- `Gamma(H_e -> H_c -> M_s)`: consolidation and promotion pipeline
- `Omega`: regulatory mesh

The practical meaning is simple: the agent does not merely consult memory. It acts inside a world that its maintained history has already made more or less legible.

## Design principles for the generalized memory architecture

### 1. Memory must stay domain-agnostic in representation

The slow layer should not encode hardware sensors, repo files, or tool names directly in core memory structures. The core representation should remain portable.

The Phase 7 choice to key the substrate around coherence dimensions is a strong default:

- continuity support
- vitality support
- contextual fit support
- differentiation support
- accountability support
- reflexivity support

Constraint patterns should also be defined in terms of dimension configurations and trends, not domain objects.

Domains then translate substrate state into local effects.

### 2. Domain specificity should live at the binding layer

The core should define memory mechanics. Domains should define how memory changes access.

Examples:

- hardware domain: maintained accountability support might sharpen causal observability of system actions
- repo-health domain: maintained continuity support might reduce noise in long-horizon project trend estimates
- LLM trace domain: maintained reflexivity support might improve observability of recent failure signatures or uncertainty trajectories

The substrate remains general; the consequences of support are domain-specific.

### 3. Memory must be metabolically real

If memory infrastructure is free, it becomes an annotation layer rather than an allostatic one.

The generalized engine should preserve:

- costly investment
- cheaper but nonzero maintenance
- decay when neglected
- path dependence in write cost
- a real competition between action and infrastructure

### 4. Consolidation must become transformative, not archival

`Gamma` should do more than retain entries. It should:

- keep useful episodic traces for selector learning
- extract recurring patterns from history
- promote patterns or dimension support into slow-layer infrastructure
- support cross-session continuity

This is the bridge from "what happened" to "what now constrains what can happen."

## Proposed Phase 4.5 core components

### 1. `real_core/episodic.py`

Move the current `EpisodicMemory` here with minimal changes.

Responsibilities:

- record `CycleEntry`
- retain bounded history
- provide trail statistics for the selector
- support three-tier consolidation over episodic traces

### 2. `real_core/substrate.py`

Generalized slow-layer memory substrate, extracted and cleaned up from Phase 7.

Responsibilities:

- maintain fast and slow memory layers
- support bistable thresholds and decay
- track maintenance age and velocity
- compute history-dependent write and maintenance costs
- store constraint patterns
- support persistence across sessions

Default keyspace:

- one slow-layer support entry per coherence dimension

Designed extensibility:

- later support for action-specific, context-specific, or hierarchical entries

### 3. `real_core/patterns.py`

Constraint pattern primitives promoted from consolidation.

Responsibilities:

- represent attractor and trough signatures
- match current dimension state against stored patterns
- compute pattern-derived modulation signals
- manage diversity, merge thresholds, and redundancy pruning

### 4. `real_core/consolidation.py`

A true consolidation pipeline rather than only an episodic prune pass.

Responsibilities:

- run episodic three-tier retention
- extract consolidated signatures
- decide which patterns become `H_c`
- promote selected structure into `M_s`
- prepare cross-session carryover package

### 5. `real_core/session_state.py`

A single cross-session persistence model.

Responsibilities:

- save and restore episodic survivors
- save and restore substrate state
- save and restore dimension context and prior coherence
- provide domain-independent warm starts

## Proposed engine changes

### Current engine shape

`RealCoreEngine` currently assumes a simple loop:

1. observe
2. select
3. execute
4. observe again
5. score
6. record
7. occasionally consolidate

### Revised engine shape

`RealCoreEngine` should be revised so memory is active throughout the loop:

1. substrate-informed observe
2. enumerate domain actions plus memory actions
3. filter by metabolic affordability
4. select using episodic, consolidated, and substrate-informed context
5. execute domain or substrate action
6. observe again through substrate-modulated access
7. score coherence including substrate health
8. record episodic entry
9. update dimension context and substrate dynamics
10. run consolidation and promotion when triggered

This does not require abandoning the current loop. It requires making memory present at more than one step in it.

## Proposed interfaces and contracts

The goal is to keep Phase 4 domain-agnostic while allowing memory to be structural.

### Keep existing protocols

These still make sense:

- `ObservationAdapter`
- `ActionBackend`
- `CoherenceModel`
- `Selector`
- `RegulatoryMesh`

### Add memory-aware core contracts

#### `MemorySubstrate`

Core object owned by the engine.

Responsibilities:

- slow-layer state
- maintenance and write mechanics
- pattern state
- persistence

#### `ConsolidationPipeline`

Replaces the idea of consolidation as only list-pruning.

Methods should cover:

- episodic retention
- pattern extraction
- substrate promotion
- export/import of cross-session carryover

#### `DomainMemoryBinding`

This is the crucial domain-agnostic bridge.

The core memory system remains general, but each domain must define how substrate state affects local observability and affordance.

Possible responsibilities:

- `modulate_observation(raw_obs, substrate) -> obs`
- `extra_actions(substrate, history) -> list[str]`
- `estimate_memory_action_cost(action, substrate) -> float | None`
- `execute_memory_action(action, substrate) -> ActionOutcome | None`
- `substrate_health_signal(substrate, state_after, history) -> dict[str, float]`

This keeps the substrate general while letting each domain bind it to its own epistemic consequences.

## Recommended file-level refactor in Phase 4

### Existing files to revise

- `real_core/engine.py`
  - add first-class substrate support
  - add budget-aware action filtering
  - add session save/load hooks

- `real_core/memory.py`
  - either narrow this file to episodic memory only or replace it with a package split across episodic/consolidation/substrate

- `real_core/types.py`
  - add types for substrate snapshots and cross-session state

- `real_core/interfaces.py`
  - add `ConsolidationPipeline` and `DomainMemoryBinding`

### New files recommended

- `real_core/episodic.py`
- `real_core/substrate.py`
- `real_core/patterns.py`
- `real_core/consolidation.py`
- `real_core/session_state.py`
- optionally `real_core/memory_stack.py`

## Migration path

### Step 1: Extract the substrate into Phase 4 core

Source prototype:

- `Phase 2/Phase 7/memory_substrate/substrate.py`

Goal:

- create a clean, domain-agnostic `real_core/substrate.py`
- keep the initial keyspace dimension-aligned
- preserve decay, bistability, maintenance, pattern persistence

### Step 2: Replace "memory = episodic log" in the engine

Update the engine so `EpisodicMemory` is no longer the only memory primitive. The engine should own:

- episodic trace
- consolidation pipeline
- substrate state

### Step 3: Introduce memory bindings per domain

Each Phase 4 domain should define how substrate support changes local observation and cost.

This can begin minimally:

- hardware: observation noise modulation only
- repo-health: trend clarity modulation only
- LLM API: uncertainty/failure-pattern observability only

### Step 4: Add cross-session warm start as core behavior

Cross-session carryover should stop being experiment-specific logic. It should become a standard engine capability.

### Step 5: Upgrade selector use of memory

Initially, the existing CFAR selector can remain mostly unchanged. It can operate over expanded action vocabularies and trail data as in Phase 7.

Later, the selector can explicitly use:

- substrate weakness signals
- active pattern matches
- budget-wall awareness
- infrastructure maturity

## What should remain unchanged

This revision should deepen the generalized architecture, not replace its identity.

These parts should remain stable:

- the six coherence dimensions
- the perceive -> select -> execute -> re-perceive -> score -> record rhythm
- the CFAR family as the selector basis
- bounded regulatory coupling via the mesh
- domain adapters as the mechanism for swapping concrete substrates

## Philosophical alignment

This revision is not feature growth for its own sake. It restores alignment between the generalized architecture and the project's central claim.

A domain-agnostic allostatic learner should not have:

- rich coherence scoring
- bounded action selection
- consolidation
- real metabolic tradeoffs

while still treating memory as passive storage.

If the system's history is supposed to become part of its ongoing organization, then Phase 4 must be updated so that memory is structurally active.

Phase 4 generalized the scaffold.
Phase 7 clarifies what memory in that scaffold actually needs to be.
Phase 4.5 should unify them.

## Immediate implementation target

The smallest coherent implementation target is:

1. extract Phase 7 substrate and pattern primitives into `Phase 4/real_core`
2. modify `RealCoreEngine` to own `episodic_memory`, `substrate`, and `consolidation_pipeline`
3. add a lightweight `DomainMemoryBinding` protocol
4. port one existing Phase 4 domain through the new memory-aware engine
5. confirm parity with current Phase 4 behavior when substrate effects are effectively neutral

That would create a genuine domain-agnostic memory architecture instead of leaving Phase 7 as a side branch.


