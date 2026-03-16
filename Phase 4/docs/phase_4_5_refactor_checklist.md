# Phase 4.5 - Concrete Refactor Checklist

**Date:** 2026-03-15
**Status:** Planning checklist

This note translates the Phase 4.5 memory revision proposal into concrete changes against the current Phase 4 codebase.

## Refactor objective

Update Phase 4 so that memory is no longer modeled only as episodic history plus pruning. The generalized engine should instead treat memory as:

- episodic trace
- consolidated pattern memory
- maintained slow-layer substrate

The implementation goal is to preserve the existing domain-agnostic architecture while revising its memory model to match the stronger Phase 7 account of memory as maintained constraint.

## Non-goals

Do not do these in the first refactor pass:

- do not replace the six coherence dimensions
- do not rewrite the CFAR selector from scratch
- do not make domains share one concrete observation model
- do not require all domains to use rich substrate effects immediately
- do not break current Phase 4 experiments during the transition

## Recommended rollout strategy

Use a compatibility-first rollout.

1. Add new memory-aware abstractions without removing current ones.
2. Keep current `RealCoreEngine` behavior working with neutral defaults.
3. Port one domain first.
4. Expand tests.
5. Only then deprecate or narrow old interfaces.

## Target architecture after refactor

### Engine-owned state

The engine should own:

- `episodic_memory`
- `substrate`
- `consolidation_pipeline`
- `memory_binding`
- `session_state`

### Domain-owned responsibilities

Each domain should continue to own:

- raw observation generation
- domain action execution
- coherence scoring
- mapping substrate state onto domain-specific epistemic effects

## File-by-file plan

### `Phase 4/real_core/types.py`

Current role:

- `ActionOutcome`
- `CycleEntry`
- dimension and status types

Planned changes:

- add `SubstrateSnapshot` dataclass
- add `SessionCarryover` dataclass
- add `MemoryActionSpec` dataclass if action/cost estimation needs a typed bridge
- extend `CycleEntry` only if needed for memory-side observability

Guideline:

- avoid stuffing all substrate state into `CycleEntry` unless it is needed for learning or debugging
- keep `CycleEntry` domain-facing and add separate typed snapshots for substrate/session persistence

### `Phase 4/real_core/interfaces.py`

Current role:

- base protocols for observation, action, coherence, selector, consolidator, mesh

Planned changes:

- keep all existing protocols
- add `MemorySubstrateProtocol`
- add `ConsolidationPipeline`
- add `DomainMemoryBinding`

Suggested responsibilities for `DomainMemoryBinding`:

- `modulate_observation(raw_obs, substrate, cycle)`
- `extra_actions(substrate, history)`
- `estimate_memory_action_cost(action, substrate)`
- `execute_memory_action(action, substrate)`
- `substrate_health_signal(substrate, state_after, history)`

Guideline:

- this is the main bridge that keeps the core memory model domain-agnostic while allowing domains to decide what substrate support actually changes

### `Phase 4/real_core/memory.py`

Current role:

- `EpisodicMemory`

Planned changes:

Option A, preferred:

- keep this file temporarily as a compatibility shim
- move `EpisodicMemory` implementation to `real_core/episodic.py`
- re-export `EpisodicMemory` from `memory.py`

Option B:

- leave `memory.py` in place for now, then split later

Recommendation:

- use Option A to keep imports stable while making the architecture clearer

### `Phase 4/real_core/episodic.py`

New file.

Responsibilities:

- move current `EpisodicMemory` here
- keep existing trail statistics and `consolidate_three_tier()` initially
- keep behavior unchanged in the first pass

This creates a clean place to say: episodic memory is only one layer of the memory stack.

### `Phase 4/real_core/substrate.py`

New file.

Source prototype:

- `Phase 2/Phase 7/memory_substrate/substrate.py`

Responsibilities in Phase 4.5:

- hold fast and slow layers
- support bistability, decay, maintenance age, velocity
- compute write and maintenance cost
- store constraint patterns or delegate them to `patterns.py`
- expose save/load state
- default keyspace is coherence-dimension aligned

Initial simplification allowed:

- keep dimension-aligned keys only in the first Phase 4 port
- postpone hierarchical or action-specific keys

### `Phase 4/real_core/patterns.py`

New file.

Source prototype:

- `ConstraintPattern` logic from `Phase 2/Phase 7/memory_substrate/substrate.py`

Responsibilities:

- pattern data structure
- similarity and matching
- diversity management
- merge/prune logic
- pattern-derived modulation output

Reason for split:

- keeps substrate mechanics separate from pattern recognition policy
- makes later experiments easier without destabilizing the slow-layer core

### `Phase 4/real_core/consolidation.py`

New file.

Responsibilities:

- run episodic three-tier retention
- extract candidate attractor/trough signatures
- promote selected patterns into `H_c`
- update the substrate when promotion criteria are met
- create the cross-session carryover package

Guideline:

- first pass can wrap the current three-tier logic and add pattern extraction as an additional step
- avoid overfitting promotion rules before data exists in multiple domains

### `Phase 4/real_core/session.py`

Current role:

- session summaries persisted across runs

Planned changes:

- keep `SessionHistory` for developmental summaries
- do not overload it with full substrate persistence
- add a separate `session_state.py` for warm-start memory transfer

Reason:

- session summaries and cross-session learning state are not the same artifact

### `Phase 4/real_core/session_state.py`

New file.

Responsibilities:

- save/load `SessionCarryover`
- persist substrate state
- persist consolidated episodic survivors
- persist dimension context and prior coherence
- support warm starts in a domain-independent format

### `Phase 4/real_core/engine.py`

Current role:

- simple generalized REAL cycle over observer/actions/coherence/selector/mesh/memory

Planned changes:

1. Update constructor to accept optional:
- `substrate`
- `consolidation_pipeline`
- `memory_binding`
- `session_state_store` or carryover payload
- `session_budget`

2. Update cycle execution:
- raw observe from domain observer
- modulate via `memory_binding` if substrate enabled
- combine domain actions with memory actions
- filter by affordability if budget enabled
- select action
- route memory actions to substrate or domain actions to backend
- rescore with optional substrate health contribution
- update episodic memory
- update substrate context and decay

3. Update session execution:
- support promotion triggers, not just episodic prune-on-rest
- optionally emit carryover package at end of session

Compatibility target:

- engine should behave almost exactly like current Phase 4 when no substrate or binding is supplied

### `Phase 4/real_core/__init__.py`

Planned changes:

- export new substrate and consolidation types
- keep existing public imports stable where possible
- re-export `EpisodicMemory` even if moved to `episodic.py`

### `Phase 4/domains/registry.py`

Current role:

- build `(observer, actions, coherence)` bundles

Planned changes:

- return a richer domain bundle with optional `memory_binding`
- keep legacy defaults for domains that have not yet been migrated

Suggested bundle shape:

- `observer`
- `actions`
- `coherence`
- `memory_binding`
- optionally `domain_defaults` for cost/budget/substrate tuning

### `Phase 4/domains/hardware/adapter.py`

First-pass migration target:

- low-complexity substrate effect
- map dimension support to observation clarity or noise reduction
- expose no extra memory actions at first, or only `invest_*` / `maintain_substrate`

Why this domain is a good early candidate:

- observation and action space are simple
- easier to validate parity against current scaffold behavior

### `Phase 4/domains/repo_health/adapter.py`

Strong candidate for first substantive migration.

Planned binding ideas:

- continuity support sharpens long-horizon trend estimates
- accountability support reduces noise around TODO/test/documentation interpretation
- reflexivity support improves detection of action-response recovery patterns

Why this is attractive:

- the domain has real structure but not too much runtime complexity
- effects are intuitive and inspectable

### `Phase 4/domains/llm_api/adapter.py`

High-value but later migration target.

Planned binding ideas:

- reflexivity support improves observability of failure/retry trajectories
- accountability support sharpens trace completeness / causal attribution
- contextual fit support alters confidence in tool-usage or quality interpretation

Why this should probably be second or third:

- more moving parts
- replay and capture paths already introduce extra complexity

### `Phase 4/tests/test_contracts.py`

Current role:

- verifies basic engine/domain/config behavior

Planned additions:

- engine still works with no substrate attached
- substrate-enabled engine records cycles correctly
- carryover can be saved and loaded
- pattern extraction does not break session execution
- domain bundle can expose a neutral `memory_binding`
- budget filtering works when memory actions are present

Important compatibility test:

- current Phase 4 example configs should continue to pass with substrate disabled or neutral

### `Phase 4/experiments/*.toml`

Planned changes:

- add optional `[memory_substrate]` section
- add optional `[carryover]` section
- add optional budget settings

Guideline:

- defaults should keep current experiments working without edits

### `Phase 4/run_experiment.py`

Planned changes:

- parse new memory-related config blocks
- build engine with substrate components when enabled
- preserve current config behavior when those sections are absent

## Recommended implementation order

### Milestone 1: Introduce types and interfaces

Checklist:

- add new protocols to `interfaces.py`
- add substrate/session carryover types to `types.py`
- keep old imports working

Exit condition:

- no behavior change yet
- current tests still pass

### Milestone 2: Split episodic memory from generalized memory

Checklist:

- add `episodic.py`
- re-export from `memory.py`
- add placeholder `substrate.py` and `patterns.py`

Exit condition:

- architecture is clearer
- current engine still unchanged in behavior

### Milestone 3: Add substrate-capable engine path

Checklist:

- update `engine.py` to accept neutral substrate and binding
- support optional budget filtering
- support memory actions
- keep no-substrate path as default behavior

Exit condition:

- old domains still run
- substrate can be attached without breaking the loop

### Milestone 4: Add consolidation pipeline and carryover

Checklist:

- add `consolidation.py`
- add `session_state.py`
- let engine save/load warm-start state

Exit condition:

- cross-session memory becomes a first-class Phase 4 capability

### Milestone 5: Port one domain end-to-end

Recommendation:

- start with `repo_health`

Checklist:

- implement a real `DomainMemoryBinding`
- confirm parity when substrate effects are neutral
- confirm changed behavior when substrate is active

Exit condition:

- one real Phase 4 domain demonstrates memory as maintained constraint

### Milestone 6: Expand to remaining domains

Checklist:

- port `hardware`
- port `llm_api`
- document domain-specific substrate mappings

Exit condition:

- Phase 4 is genuinely memory-aware across domains, not only in one experiment branch

## Risks to watch

### Risk 1: Overcoupling substrate to one domain's semantics

Mitigation:

- keep substrate keys dimension-aligned in the core
- push domain-specific effects into `DomainMemoryBinding`

### Risk 2: Breaking current Phase 4 simplicity

Mitigation:

- neutral defaults
- compatibility shims
- milestone-based rollout

### Risk 3: Treating cross-session history and learning state as the same thing

Mitigation:

- keep `SessionHistory` summaries separate from `SessionCarryover`

### Risk 4: Reintroducing hardcoded maintenance policy

Mitigation:

- allow memory actions and substrate effects first
- keep selector mostly unchanged initially
- use trail learning before engineered selector logic

## Suggested first coding slice

If work starts immediately, the smallest high-value slice is:

1. add `real_core/episodic.py`
2. add `real_core/substrate.py` with a trimmed Phase 7 substrate
3. add `DomainMemoryBinding` to `interfaces.py`
4. update `RealCoreEngine` so it can run with a neutral substrate path
5. add tests proving old Phase 4 behavior still works

That is enough to begin the merge of Phase 7's memory model into the generalized architecture without forcing a full domain migration on day one.
