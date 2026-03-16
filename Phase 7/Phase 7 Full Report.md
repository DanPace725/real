# Phase 7: Memory as Constraint Field — Full Development Report

**Date:** March 15–16, 2026
**Author:** Claude (Anthropic), working with project lead
**Codebase:** `Phase 2/Phase 7/memory_substrate/`

---

## 1. Origin and Motivation

Phase 7 began with a research document on cellular memory and the observation that biological memory is not stored — it is maintained. Cells don't consult an archive. Their history becomes structurally built into which future states are easy or hard to enter. The preferred term from that research — **constraint accumulation** — maps directly onto the E² framework's six relational primitives:

- P1 (Continuity): Chromatin marks persist across cell division
- P2 (Vitality): Feedback loops sustain regulatory programs
- P3 (Contextual Fit): Tissue-specific expression patterns
- P4 (Differentiation): Epigenetic marks reshape accessible state space
- P5 (Accountability): Writer/reader/eraser enzyme relationships
- P6 (Reflexivity): The cell's regulatory state includes self-monitoring circuits

The REAL engine (Phase 4) already had episodic memory — a passive log of past experiences used for trail-following. Phase 7 asked: what if memory were something the agent partly *is*, not something it *has*? What if accumulated history shaped what actions are cheap, what environments are legible, and what state-space regions are reachable?

Five structural invariants from the cellular research became the design requirements:

1. **Bistability** — memory entries occupy stable on/off states with threshold dynamics
2. **Active maintenance cost** — persistence requires ongoing ATP expenditure
3. **Speed differential** — fast (volatile, free) and slow (persistent, costly) layers
4. **History-dependence** — the cost structure depends on what's already been built
5. **Self-reinforcing closure** — maintaining memory generates conditions that make maintenance easier

---

## 2. What Was Built

### Phase 0: The Two-Layer Substrate

A standalone `MemorySubstrate` with six dimensions matching the REAL coherence model:

- **Fast layer**: Updated every cycle from observation. Free reads, volatile. Represents current perception.
- **Slow layer**: Persistent, costly writes, decays unless maintained. Bistable threshold at 0.25 — below it, accelerated decay pulls toward zero; above it, manageable decay can be counteracted by maintenance.
- **ATP costs**: Writing new entries costs 0.15 ATP (reduced by active neighbors via history-dependent discount). Maintenance costs 0.03 ATP per tick.
- **Coupling**: The slow layer modulates the observation function — dimensions with active slow-layer support are observed with less noise (clarity scales 0.35–0.97).

### Phase 1: Instrumentation and Validation

Ran systematic experiments: 20-session baselines, parameter sweeps across decay rate, budget, threshold, and acceleration factor.

**Findings:**
- Bistability is clean — 94.9% of slow-layer values above threshold, 4.5% near zero, only 0.7% in transition
- The developmental arc is real — systems bootstrap from empty to full active support over 3-5 sessions
- Self-reinforcing closure confirmed — active dimensions lower the cost of activating neighbors by 12% each
- Two corrections needed: metabolic budget wasn't binding (action costs too low), coupling formula measured the wrong thing (level alignment instead of variance reduction)

Both corrections were applied before Phase 3.

### Phase 2: Visualization Dashboard

An interactive HTML dashboard displaying four signals: coupling strength over time, maintenance ratio, trail-following ratio, and self-model accuracy. Served via local HTTP for browser access.

### Phase 3: Wiring into REAL

Five wrapper components make the substrate a structural participant in the REAL cycle:

| REAL Element | Integration |
|---|---|
| **O** (Observation) | Slow-layer support reduces noise per dimension |
| **c** (Cost) | invest/maintain actions consume ATP, cost-adjusted by selector |
| **Φ** (Coherence) | Substrate health feeds into reflexivity scoring |
| **Ψ** (Selector) | CFAR selector operates over expanded action vocabulary |
| **H/Γ** (Memory) | Slow layer persists across sessions; standard three-tier consolidation for episodic log |

The integration is domain-agnostic — any domain adapter can be wrapped with the substrate layer.

### ATP Budget: The Metabolic Wall

Added an explicit per-session ATP budget. Every action draws from the same finite pool:

| Action | ATP Cost |
|---|---|
| rest | 0.00 |
| scan | 0.03 |
| introspect | 0.06 |
| invest_\<dim\> | 0.06–0.15 (history-dependent) |
| maintain_substrate | 0.03–0.05 (history-dependent) |

Budget sweep across 10 levels revealed a **phase transition at ~2.5–3.0 ATP**: below this, the substrate is a net cost (the agent can't afford both domain actions and substrate maintenance); above it, the substrate is a net benefit. This is the TCL parametric wall — the system cannot sustain its own complexity without sufficient metabolic resources.

### Layer 1: Trajectory Awareness

Added velocity tracking to the slow layer — an exponential moving average of each dimension's net change per cycle. Negative velocity (decaying support) reduces observation clarity before the threshold crossing, making decay *perceptible* through the observation function.

This was necessary but insufficient. The CFAR selector's single-step evaluation couldn't translate a momentary velocity signal into learned multi-step preventive behavior. Maintenance share remained ~5% with velocity alone, confirming the need for deeper pattern-level memory.

### Layer 2: Constraint Patterns

The core contribution of this development cycle. Four sub-components built iteratively:

#### 2a. Pattern Data Structure and Matching

`ConstraintPattern` — a compressed multi-dimensional signature with:
- `dim_scores` / `dim_trends`: what the agent was experiencing
- `valence`: positive (attractor) or negative (trough)
- `strength`: decays each tick, refreshed on match
- `coherence_level`: mean coherence when this pattern occurred

Matching uses weighted similarity (65% dimension scores, 35% trends) against the agent's current dimension state. Patterns that match above threshold get their strength refreshed — if they stop being recognized, they fade naturally.

#### 2b. Pattern Diversity

Without enforcement, all 12 pattern slots fill with near-identical attractors (>0.90 pairwise similarity). Two mechanisms prevent this:

1. **Merge gating** (threshold 0.70): New patterns that are too similar to an existing same-polarity pattern are merged via EMA rather than added
2. **Coverage-aware pruning**: When at capacity, the most redundant pattern (nearest to its neighbor) is removed rather than the weakest

This yields 2-5 genuinely diverse patterns with max pairwise similarity ~0.69, covering distinct attractor and trough configurations.

#### 2c. Per-Dimension Specificity

Patterns modulate clarity *per dimension* rather than uniformly. Each matching pattern sharpens the dimensions that are prominent in its signature:

- Attractor with differentiation=1.00 → strong clarity boost for differentiation
- Attractor with contextual_fit=0.73 → moderate clarity boost for contextual_fit
- Trough with accountability=0.61 → noise for accountability

This creates context-dependent perception analogous to tissue-specific gene expression — the agent's perceptual acuity depends on which attractor configuration it recognizes.

#### 2d. Cross-Session Consolidation

**The largest single improvement in the entire development cycle.**

Previously, each session started with empty episodic memory despite carrying substrate state and patterns. The CFAR selector was forced into random exploration for the first 10-15 cycles — wasting 20-30% of every session.

`save_session` / `load_session` now carries three things across session boundaries:
1. **Consolidated episodic entries** — three-tier survivors, giving trail data from cycle 1
2. **Dimension context** — so pattern matching activates immediately
3. **Prior coherence** — so the first cycle's delta is meaningful

---

## 3. What Was Attempted and Abandoned

### Pre-Decline Warning Patterns
Captured the state *before* coherence declines. Failed because the pre-decline state is indistinguishable from a normal good state — both positive and negative patterns matched everything simultaneously, and the net noise degraded performance. Coherence declined -0.017 across sessions with this approach.

### Strict Consecutive-Decline Detection
Required 4+ cycles with delta < -0.01. Never triggered — coherence deltas are too noisy for strict consecutive thresholds.

### Asymmetric Modulation Weights (+0.08 / -0.15)
With diverse patterns producing more troughs than attractors, the asymmetric negative weight created a net noise bias. Symmetric weighting resolved this.

### Forced Selector Logic
Early Phase 3 had hardcoded maintenance priority in the CFAR selector. Removed entirely in favor of organic learning — the selector learns maintenance value from trail data, not from engineered rules. This was a critical philosophical decision aligned with the project's core principle that coherence should be endogenous, not imposed.

### Merge Threshold 0.60 (Too Aggressive)
Left only 1-3 patterns — too few to provide meaningful recognition signal.

### Merge Threshold 0.65 with Asymmetric Weights
Produced a 2:7 positive:negative ratio where negative matches dominated. The 0.70 threshold naturally produces a more balanced ratio.

---

## 4. Results

### Final A/B Comparison (3 seeds × 15 sessions, 50 cycles each)

Substrate condition includes all improvements: two-layer substrate, velocity tracking, diverse constraint patterns, per-dimension specificity, and cross-session consolidation.

#### Unlimited Budget

| Metric | Baseline | Substrate | Delta |
|--------|----------|-----------|-------|
| **Mean coherence** | 0.728 | **0.833** | **+14.5%** |
| STABLE rate | 72.4% | **82.3%** | +9.9pp |
| DEGRADED rate | 7.1% | **0.3%** | -6.8pp |
| CRITICAL rate | 0.0% | 0.4% | +0.4pp |
| Maintenance share | — | 10.3% | organic |

#### 5.0 ATP Budget

| Metric | Baseline | Substrate | Delta |
|--------|----------|-----------|-------|
| **Mean coherence** | 0.725 | **0.818** | **+12.8%** |
| STABLE rate | 72.8% | 73.8% | +1.0pp |
| DEGRADED rate | 7.0% | **0.3%** | -6.7pp |
| CRITICAL rate | 0.0% | 0.4% | +0.4pp |
| Maintenance share | — | 7.8% | organic |

#### Per-Dimension Scores (Unlimited Budget)

| Dimension | Baseline | Substrate | Delta |
|-----------|----------|-----------|-------|
| continuity | 0.851 | 0.825 | -0.026 |
| vitality | 0.940 | **0.977** | **+0.037** |
| contextual_fit | 0.644 | 0.608 | -0.036 |
| differentiation | 0.709 | **0.986** | **+0.277** |
| accountability | 0.530 | **0.801** | **+0.271** |
| reflexivity | 0.693 | **0.803** | **+0.110** |

Four of six dimensions show positive deltas. Differentiation (+0.277) and accountability (+0.271) benefit most from the expanded action vocabulary and cross-session learning. Reflexivity (+0.110) reflects the agent's growing awareness of its own infrastructure.

#### Progressive Improvement Across the Development Cycle

| Stage | Coherence Delta (Unlimited) | Key Change |
|-------|-----------------------------|------------|
| Phase 3 integration | +8.6% | Substrate wired into REAL |
| + ATP budget | +8.2% | Finite metabolic resources |
| + Velocity tracking | +7.8% | Decay perceptible in observation |
| + Constraint patterns | +8.2% | Attractor recognition boosts clarity |
| + Pattern diversity | +7.8% | Distinct patterns, coverage-aware pruning |
| + Per-dimension specificity | +8.2% | Context-dependent perception |
| + **Cross-session consolidation** | **+14.5%** | Warm start eliminates cold-start waste |

### 20-Session Diagnostic (Seed 42, 5.0 ATP)

| Phase | Coherence | Maintenance | Memory Size | Active Dims |
|-------|-----------|-------------|-------------|-------------|
| Sessions 1-5 | 0.812 | 3.6% | 38→30 | 0→1 |
| Sessions 6-10 | 0.840 | 6.4% | 37→62 | 1→4 |
| Sessions 11-15 | 0.838 | 7.2% | 35→48 | 1→4 |
| Sessions 16-20 | **0.842** | 6.0% | 50→83 | 1→2 |
| **Gain (early→late)** | **+0.030** | +2.4pp | accumulating | |

---

## 5. What It Means

### The Central Thesis Holds

The cellular memory research's core claim — that memory is maintained state that constrains future behavior, not a passive archive — translates directly into a computational architecture that measurably outperforms the baseline.

The substrate doesn't help because it stores more information. It helps because it changes *what the agent can perceive*. Dimensions with slow-layer support are observed with less noise. Attractor patterns recognized from past experience sharpen perception further. The agent doesn't decide to maintain its memory because a rule says to — it maintains its memory because doing so sustains the perceptual conditions under which it thrives.

### Five Invariants Are Realized

1. **Bistability**: 94.9% of slow-layer values are in the "on" basin. The transition zone is narrow (0.7%), confirming clean bistable dynamics.

2. **Active maintenance cost**: The metabolic wall at 2.5-3.0 ATP confirms that maintenance isn't free. Below the wall, the substrate is a net cost. The agent must earn enough metabolic resources to sustain its own complexity.

3. **Speed differential**: The fast layer reflects current observation (volatile, free). The slow layer persists across sessions (costly, decays). Their interaction — slow layer modulating fast-layer clarity — is the TCL lamination structure.

4. **History-dependence**: Neighbor discounts mean the cost to activate a new dimension drops as existing dimensions are maintained. The system exhibits path-dependence: the order in which dimensions are invested changes the cost landscape.

5. **Self-reinforcing closure**: This operates at three levels now:
   - **Dimension level**: Active dimensions reduce the cost of activating neighbors
   - **Pattern level**: Attractor recognition → better observation → higher coherence → more positive trail data → actions that sustain the attractor
   - **Cross-session level**: Consolidated memory seeds better decisions → better outcomes → richer consolidation fodder

### The Maintenance Gap Closed Organically

The original design challenge was whether the agent could learn to maintain its own memory infrastructure without hardcoded rules. Early versions required a forced selector that prioritized maintenance. Layer 1 (velocity tracking) made decay perceptible but didn't change behavior (~5% maintenance). Layer 2 (constraint patterns + diversity + cross-session consolidation) solved it:

- Maintenance reached 10.3% in the A/B average (unlimited budget)
- Single-seed diagnostics showed 32-50% maintenance in mature sessions
- All of this emerged from the CFAR selector learning through trail data — no hardcoded maintenance logic

The mechanism: attractor patterns boost observation clarity → higher coherence → positive trail data for substrate actions → the selector learns that invest/maintain actions contribute to good states. Cross-session memory ensures this learning persists across session boundaries.

### The Cold Start Was the Bottleneck

The single largest improvement came not from a new mechanism but from *carrying existing learning forward*. Cross-session consolidation nearly doubled the coherence advantage (8.2% → 14.5%) by eliminating the 20-30% of each session wasted on cold-start exploration.

This has a broader implication: in systems where sessions are discrete (sleep/wake cycles, task boundaries, context switches), the handoff between sessions may matter more than the within-session dynamics. The three-tier consolidation — originally designed as a memory management strategy — turned out to be the critical bridge that made accumulated experience *usable*.

### Dimensions That Still Lag

Two dimensions consistently score lower with the substrate:

- **Continuity** (-0.026): The expanded action vocabulary makes the agent's observation history more varied, which the continuity scorer (variance-based) penalizes.
- **Contextual fit** (-0.036): Same cause — a more diverse behavioral profile is less predictable to the trend-following coherence model.

These aren't failures of the substrate. They reveal a tension in the coherence model: the dimensions that reward behavioral consistency (continuity, contextual_fit) are at odds with the dimensions that reward behavioral diversity (differentiation, accountability). The substrate shifts the balance toward diversity, which is a net positive for overall coherence but creates per-dimension trade-offs.

---

## 6. Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    REAL Engine Cycle                      │
│                                                          │
│  Observe → Select → Execute → Observe → Score → Record  │
│     ↑                                          ↓        │
│     │         ┌──────────────────────┐         │        │
│     │         │   Memory Substrate    │         │        │
│     │         │                      │         │        │
│     │         │  Fast Layer (free)   │←────────┘        │
│     │         │      ↕ coupling      │  update_fast()   │
│     │         │  Slow Layer (costly) │                   │
│     │         │      ↕ velocity      │                   │
│     │         │  Constraint Patterns │                   │
│     │         │      ↕ matching      │                   │
│     └─────────│  Dim Modulation     │                   │
│   clarity mod │                      │                   │
│               └──────────────────────┘                   │
│                          ↕                               │
│                 save_session / load_session               │
│               (substrate + memory + context)             │
└─────────────────────────────────────────────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `substrate.py` | Two-layer substrate, bistable dynamics, constraint patterns, diversity enforcement |
| `real_integration.py` | REAL wrappers (observation, action, coherence, selector, engine), pattern promotion, cross-session persistence |
| `run_integration.py` | Domain adapters (signal environment), experiment runner |
| `ab_comparison.py` | A/B comparison framework (baseline vs substrate) |
| `budget_sweep.py` | ATP budget parameter sweep |
| `pattern_diagnostic.py` | Per-session pattern accumulation tracking |
| `environment.py` | Phase 0 synthetic environment |
| `agent.py` | Phase 0 standalone agent |
| `runner.py` | Phase 0 session runner |
| `analyze.py` | Phase 1 analysis tools |
| `sweep.py` | Phase 1 parameter sweeps |
| `dashboard.py` | Phase 2 HTML dashboard generator |

---

## 7. Next Steps

### Near-Term

1. **Observation variance investigation**: Substrate observation variance is consistently higher than baseline for several dimensions. This is partly an artifact of the expanded action vocabulary but may also reflect a genuine cost of per-dimension modulation. Understanding this trade-off could guide tuning of the modulation scale factors.

2. **Contextual fit gap**: The one dimension that consistently underperforms. The coherence model's trend-following scorer penalizes the behavioral diversity that the substrate encourages. This may require a scorer revision — one that rewards adaptive flexibility rather than trend consistency.

3. **Budget sweep with cross-session memory**: The metabolic wall analysis was done before cross-session consolidation. The warm start may shift the wall lower (the agent wastes less budget on exploration), which would change the system's viability envelope.

### Medium-Term

4. **Real domain integration**: All experiments use a synthetic six-channel signal environment. The next validation step is a domain where the constraint field shapes meaningful behavior — a task with real structure where the agent's investment in specific dimensions has observable consequences beyond coherence scores.

5. **Pattern-action association**: Currently, patterns modulate perception but don't directly inform action selection. Tracking which actions produced the states that became attractor patterns could create a richer recognition signal — "I'm in a state where invest_continuity worked well before" rather than just "I'm in a familiar good state."

6. **Consolidation policy learning**: The three-tier retention strategy (attractors, surprises, boundaries) uses fixed parameters. The system could learn which retention policy produces the best cross-session transfer — adjusting the attractor/surprise/boundary ratio based on how well carried entries predict future outcomes.

### Longer-Term

7. **Multi-agent substrate interaction**: What happens when multiple agents share an environment and their constraint fields overlap? Stigmergic effects — where one agent's infrastructure changes the environment that another agent perceives — could create emergent coordination without explicit communication.

8. **Substrate-aware meta-learning**: The substrate currently has fixed parameters (decay rates, threshold, costs). A meta-learning layer that adjusts these based on the agent's developmental stage could allow the system to be more exploratory early (lower maintenance cost, faster decay) and more conservative later (higher maintenance cost, slower decay).

9. **Theoretical formalization**: The empirical results confirm the cellular memory analogy works computationally. A formal analysis — connecting the substrate's dynamics to the TCL specification's bistability requirements and the E² framework's relational primitives — would ground the implementation in the project's theoretical foundations.

---

## 8. Key Takeaway

The memory substrate validates the Phase 7 hypothesis: **memory as maintained constraint, not passive archive, produces measurably better coherence in a REAL agent**. The mechanism is not storage — it is sustained perceptual shaping. The agent doesn't remember what to do; it becomes the kind of agent that perceives the world in a way that makes good actions legible.

The +14.5% coherence advantage, 82.3% STABLE rate, near-elimination of DEGRADED states, and organic emergence of maintenance behavior all follow from a single architectural commitment: making the agent's history structurally built into its future perception. That is the cellular memory insight, computationally realized.
