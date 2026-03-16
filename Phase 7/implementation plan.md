# Phase 7: Memory Substrate Implementation Plan

**Date:** 2026-03-15
**Status:** Active

---

## Design Target

Replace REAL's passive episodic archive with a two-layer memory substrate where accumulated history shapes what actions are cheap, what environments are legible, and what state-space regions are reachable. Memory becomes something the agent partly *is*, not something it *has*.

The cellular memory research provides the frame: memory is maintained, not stored. Five structural invariants provide the requirements. Phase 4's `real_core/` provides the integration surface.

---

## Five Structural Invariants

### 1. Bistability

The slow layer uses threshold dynamics. Each entry has a maintenance threshold θ_b. Below it, the entry decays toward zero (the "off" basin). Above it, an active maintenance loop can hold it (the "on" basin). Crossing from below requires deliberate ATP expenditure; once above, maintenance is cheaper than the initial investment but never free.

### 2. Active Maintenance Cost

Every tick, each slow-layer entry loses `slow_decay` units unless the agent spends ATP to maintain it. Writing new entries costs more than maintaining existing ones. Maintenance cost scales with the number of active entries. The agent can't accumulate everything; it must choose what to maintain.

### 3. Speed Differential

The fast layer updates every cycle (free reads, volatile, reflects current observation). The slow layer persists across sessions, updates only through costly writes, and decays slowly. Slow-layer state modulates the observation function O, changing what the fast layer can see. This is the TCL lamination structure.

### 4. History-Dependence in Transitions

Past slow-layer writes change which future writes are cheaper or more expensive. Strong existing infrastructure on a dimension makes related writes cheaper. Building from nothing costs more than extending what exists. History reshapes the transition cost landscape, not just preferences.

### 5. Self-Reinforcing Closure

A well-maintained slow-layer pattern can partially rebuild itself after perturbation. Surviving entries lower the write cost for decayed neighbors. The pattern tends to restore itself — the difference between a database entry and a regulatory loop.

---

## Build Phases

### Phase 0: Minimum Viable Substrate

Build the two-layer substrate in isolation. No connection to existing REAL code yet.

**Data structures:**

```python
@dataclass
class MemorySubstrate:
    fast: dict[str, float]       # current cycle observation, free reads
    slow: dict[str, float]       # persistent, costly writes, decays
    slow_age: dict[str, int]     # cycles since last maintenance per entry
    slow_decay: float = 0.02    # decay per cycle if unmaintained
    bistable_threshold: float = 0.3
    write_base_cost: float = 0.05
    maintain_base_cost: float = 0.01
```

**Key methods:**

- `tick()` — decay all slow entries; update fast from environment
- `write_slow(key, value, atp_budget)` — attempt costly write; returns ATP consumed or False
- `maintain_slow(key, atp_budget)` — prevent decay for this cycle; cheaper than writing
- `coupling_score()` — correlation between slow-layer state and recent fast-layer behavior
- `write_cost(key)` — base cost modified by existing slow-layer neighborhood
- `is_bistable_active(key)` — whether entry is above threshold

**Test environment:**

A minimal synthetic domain where:

- The state space has recurring patterns across a longer timescale than a single cycle
- The agent has basic actions (observe, explore, rest, consolidate)
- Coherence rewards pattern recognition that requires cross-cycle memory
- The agent can survive without the slow layer but can't sustain STABLE without it
- Slow layer costs real ATP that competes with action budget

**Exit criteria:**

- Bistability is observable (entries either decay to zero or hold above threshold)
- Coupling score is measurable and varies with agent behavior
- Maintenance cost tradeoff is real (choices have consequences)
- All five invariants are observable in logged data

### Phase 1: Instrument and Observe

Do not design consolidation for the new substrate. Run it and watch.

**Protocol:**

- Run 10+ sessions with the Phase 0 test environment
- Log every cycle: full slow-layer state, fast-layer state, ATP spent on memory, coupling score, coherence
- Log every session: slow-layer topology (which entries survived, decayed, or were actively maintained)

**Analysis targets:**

- Which slow-layer configurations at cycle N predicted high coherence at cycle N+k?
- Which maintenance patterns (always maintain, intermittent, burst) produced the best coupling scores?
- Did bistability emerge cleanly from threshold dynamics?
- What decay rate keeps the system adaptable without losing useful structure?
- Does self-reinforcing closure happen naturally?

**Exit criteria:**

- Enough data to derive a consolidation strategy from observation
- Clear answer on whether bistability is emergent or needs reinforcement
- Calibrated decay rate and maintenance cost that produce interesting dynamics

### Phase 2: Visualization Layer

Build the four-signal dashboard before adding complexity.

**Four signals:**

1. **Coupling strength** — predictive power of slow-layer state on fast-layer behavior over a rolling window
2. **Maintenance ratio** — fraction of slow-layer entries actively maintained vs. decaying
3. **Trail-following ratio** — fraction of actions following established trails vs. exploring
4. **Self-model accuracy** — divergence between slow-layer-implied behavior and actual behavior over last N cycles

**Periodic graph snapshots:**

Every N cycles, render slow-layer state as a weighted graph. Nodes are entries. Edge weights are coupling strengths between co-maintained entries. Track topology evolution across sessions.

**Exit criteria:**

- Dashboard is live and human-legible during runs
- Coupling strength responds visibly to agent behavior
- Graph snapshots show recognizable topology changes across sessions

### Phase 3: Wire Into REAL

Connect the substrate to the REAL tuple.

**Integration points:**

1. **Observation function O** — slow-layer state modulates observation resolution per dimension. Well-maintained entry = finer-grained observation. This mirrors chromatin accessibility: same environment, different epistemic access.

2. **Cost function c** — slow-layer maintenance is part of the metabolic budget. The agent allocates ATP between acting and maintaining memory infrastructure.

3. **Coherence function Φ** — new second-order signal: coherence of the memory substrate itself (organization, degradation, rigidity, coverage gaps). Feeds into φ₆ Reflexivity.

4. **Consolidation Γ** — existing three-tier consolidation continues for the episodic log. The slow layer gets its own consolidation logic derived from Phase 1 data. Episodic consolidation survivors are candidates for slow-layer promotion.

5. **Selector Ψ** — GUIDED mode becomes sensitive to slow-layer state. Weak slow-layer infrastructure on a dimension prioritizes actions that build that infrastructure, not just actions that improve the immediate score.

**Exit criteria:**

- Observation resolution demonstrably changes based on slow-layer state
- Memory maintenance competes with action budget non-trivially
- Coupling score correlates with coherence trajectory across sessions
- An agent with developed slow layer outperforms one without in the same environment

---

## Design Decisions

1. **Slow-layer keys:** Start dimension-aligned (one entry per coherence dimension). Design for extensibility to action-specific and context-specific entries.

2. **Codebase location:** New module at `real_core/substrate.py`. Existing `EpisodicMemory` stays as H. The substrate sits between H and the rest of the tuple.

3. **Python first, JS later.** Phase 4's `real_core/` is the integration target. Phase 6's JS port gets the substrate after it's proven in Python.

4. **Test environment is throwaway.** Exists only to validate the substrate. Minimal and diagnostic, not interesting.

5. **Consolidation is data-driven.** Do not design slow-layer consolidation before Phase 1 data. Resist the temptation.

---

## What This Solves

| Problem | How the substrate addresses it |
|---------|-------------------------------|
| Memory as library vs. constraint field | Slow layer shapes observation and transition costs, not just trail recommendations |
| Timescale flatness | Fast and slow layers with explicit coupling; TCL speed differential is structural |
| No second-order signal | Coherence of the memory substrate itself becomes observable |
| Phase 6 accountability bottleneck | Slow layer provides mechanism for actions to leave durable, legible traces |

---

*Status: working plan. Phase 0 is the immediate build target.*
