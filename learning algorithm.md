# Relationally Embedded Allostatic Learning (REAL)

## A Formal Specification

**Daniel Pace**
Draft — March 2026

---

## 1. Overview

REAL is a learning algorithm in which an agent adapts its behavior over time by maintaining internal coherence across multiple dimensions, rather than by maximizing an external reward signal. The agent is embedded in an environment it can observe but not directly control, operates under genuine resource scarcity, and learns through accumulated environmental traces (stigmergic trail-following) rather than through parameter optimization.

The defining properties of REAL, which distinguish it from reinforcement learning and gradient-based methods, are:

1. **Evaluation is endogenous.** The agent scores its own operational coherence using an internal function derived from the same relational vocabulary it uses to model its environment. No external reward signal, human preference label, or critic network is required.

2. **Learning is stigmergic.** Behavioral adaptation occurs through the accumulation, consolidation, and navigation of episodic traces in the agent's environment and memory, not through updates to a parameterized policy.

3. **Cost is metabolic.** Every action consumes finite resources from a budget that does not replenish for free within a cycle. The agent must learn not only *what* to do but *when the cost is justified*.

The algorithm is substrate-independent. It operates over an abstract specification and admits any environment that satisfies three necessary embedding conditions.

---

## 2. Embedding Conditions

A REAL agent requires an environment satisfying three conditions. If any condition is violated, the learning mechanism degenerates.

### Condition 1: Epistemic Asymmetry

The agent observes the environment through a partial, noisy observation function. It cannot set state values directly; it can only influence state indirectly through actions whose effects are probabilistic and potentially unpredictable.

Formally: let S be the full environment state space. The agent accesses S only through an observation function O: S → Ŝ where Ŝ ⊂ S. There exists no action a such that executing a deterministically produces a target state s* ∈ S. The gap between action and outcome is where learning signal originates.

*Violation mode:* If the agent can directly set the values its coherence function reads, it maximizes its score by fiat. Evaluation becomes circular and learning collapses.

### Condition 2: Metabolic Reality

Each action a in the action vocabulary A has an associated cost c(a) ∈ ℝ⁺. The agent operates within a finite budget B per evaluation window. Selecting action a reduces available budget by c(a). When budget is exhausted, the agent must rest or the cycle ends.

Formally: c: A → ℝ⁺ is the cost function. Within a cycle window of length T, the agent's total expenditure is bounded: Σ c(aᵢ) ≤ B(T). The cost function may be deterministic or stochastic, but it must be non-zero for all actions: c(a) > 0 ∀ a ∈ A.

*Violation mode:* If actions are free, the agent explores exhaustively and trail-following provides no advantage over random search. Metabolic budgeting becomes meaningless.

### Condition 3: Temporal Persistence

The consequences of actions outlast the cycle in which they occur. The environment state at cycle t is a function of the full history of prior actions and states, not merely of the most recent action.

Formally: s(t) = f(s(t-1), a(t-1), ε(t)) where f incorporates historical dependence. Additionally, the agent's episodic log and any environmental modifications (terrain markers, memory entries, digests) persist across cycles and sessions. Trail-following requires trails.

*Violation mode:* If each cycle is independent (Markov with no persistent trace), the agent cannot accumulate navigational structure and each cycle is a fresh start. Learning does not accumulate.

---

## 3. System Specification

A REAL system is defined by the tuple:

**(S, A, c, O, Φ, H, Ψ, Γ, Ω)**

where:

| Symbol | Name | Description |
|--------|------|-------------|
| S | State space | The environment's full state, satisfying Condition 1 |
| A | Action vocabulary | Finite set of typed actions available to the agent |
| c | Cost function | c: A → ℝ⁺, mapping each action to its metabolic cost |
| O | Observation function | O: S → Ŝ, the agent's partial view of state |
| Φ | Coherence function | Φ: Ŝ → ℝ⁶, mapping observed state to six-dimensional coherence scores |
| H | Episodic log | Ordered sequence of cycle records with consolidation operator |
| Ψ | Selector | Action selection mechanism with three modes (F, C, G) |
| Γ | Consolidation operator | H → H', the memory pruning function |
| Ω | Regulatory mesh | Inter-dimensional coupling function applied after raw scoring |

---

## 4. The Coherence Function Φ

The coherence function maps observed state to a six-dimensional score vector. Each dimension corresponds to one of six relational primitives, which are jointly sufficient and individually irreducible evaluation axes.

**Φ(ŝ) = (φ₁, φ₂, φ₃, φ₄, φ₅, φ₆)** where each φᵢ ∈ [0, 1].

### 4.1 Dimension Definitions

**φ₁ — Continuity (Ontological).** Is the system maintaining a stable operational identity over time? Measured as low variance in key state variables over a rolling window. High variance indicates identity instability; the system does not yet know what it is.

**φ₂ — Vitality (Dynamical).** Is energy expenditure productive rather than wasteful? Scored as an inverted parabola over metabolic load, peaking at a domain-specific optimum. Both inertia (no expenditure) and overexertion (maximum expenditure) score low.

**φ₃ — Contextual Fit (Geometric/Causal).** Are actions appropriate to the current environmental context? Measures alignment between what the agent is doing and what the observable state suggests is needed. Domain-specific operationalization required.

**φ₄ — Differentiation (Symmetric/Constraint).** Is the system maintaining appropriate boundaries? Measured as the degree to which the agent's behavior is distinguishable from random action and from environmental noise. Role clarity and scope maintenance.

**φ₅ — Accountability (Epistemic/Informational).** Can the agent's reasoning and action history be traced? Measured as the completeness and consistency of the episodic log. Actions with untraceable consequences score low.

**φ₆ — Reflexivity (Meta-Relational).** Does the system revise its behavior after negative outcomes? Measured as the rate at which the agent changes strategy following coherence dips, weighted by whether the revision produced recovery.

### 4.2 Composite Score

The composite coherence score is a weighted sum:

**C = Σ wᵢ · φᵢ**

where the weight vector **w** is subject to constraints:

- wᵢ ∈ [w_min, w_max] for all i (no single dimension dominates)
- Σ wᵢ = 1
- Weight adjustments between evaluation windows are bounded: |Δwᵢ| ≤ δ_max per session (tilt-only coupling; the parametric wall from TCL)

The weight vector may be static (founding biases) or subject to slow-layer tuning (see §8).

### 4.3 GCO Status

The Global Closure Operator status assesses the agent's proximity to a self-consistent operating state. It is a navigation signal, not a reward.

| Status | Condition | Interpretation |
|--------|-----------|----------------|
| STABLE | C ≥ θ_stable AND all φᵢ ≥ θ_dim | Self-consistent operation. The fixed-point attractor. |
| PARTIAL | C ≥ θ_partial | Navigating toward closure. Most dimensions adequate. |
| DEGRADED | C ≥ θ_critical | Below viable coherence. Consolidation and rest needed. |
| CRITICAL | C < θ_critical | Allostatic overload. Emergency regulation required. |

Where θ_stable > θ_partial > θ_critical are domain-specific thresholds derived from the TCL operating window constants: the viability floor (θ_critical), the chaos ceiling, and the parametric wall (δ_max).

---

## 5. The Episodic Log H

The episodic log is an ordered sequence of cycle records. It is the primary substrate of learning. The agent does not update parameters; it accumulates and navigates traces.

### 5.1 Log Entry Structure

Each cycle t produces one entry:

**e(t) = (ŝ_before, a, ŝ_after, C, Φ, ΔC, c(a), metadata)**

where:
- ŝ_before: observed state before action
- a: action taken
- ŝ_after: observed state after action
- C: composite coherence score
- Φ: full six-dimensional score vector
- ΔC = C(t) − C(t−1): coherence delta (improvement or degradation)
- c(a): metabolic cost actually incurred
- metadata: timestamp, GCO status, selector mode, etc.

### 5.2 Trail Structure

Trails are implicit structures in the log. A trail for action a is the subsequence of all entries where action a was taken, along with their associated coherence deltas. The trail score for action a is:

**T(a) = mean({ΔC | e ∈ H, e.action = a})**

Trails can also be conditioned on state: T(a | ŝ ∈ R) restricts to entries where the observed state fell within region R. This enables context-dependent action preferences without explicit state-action value tables.

---

## 6. The Consolidation Operator Γ

Periodically (triggered by GCO status = DEGRADED, by cycle count, or by budget depletion), the consolidation operator prunes the episodic log. This is the system's analog of sleep-dependent memory consolidation.

**Γ(H) → H'** where |H'| < |H|.

### 6.1 Three-Tier Retention

Γ retains entries that are maximally informative for future navigation. Three categories:

**Tier 1 — Attractors.** Entries with the highest composite coherence scores. These represent where the agent wants to go. Retained: top k₁ entries by C.

**Tier 2 — Surprises.** Entries with the highest absolute coherence delta |ΔC|. These represent the moments where something important happened, whether positive or negative. A -0.15 delta is as informative as a +0.15 delta. Retained: top k₂ entries by |ΔC|.

**Tier 3 — Boundaries.** Entries where C was near the GCO threshold (θ_partial ± ε). These represent decision points where action choice mattered most. The SEEKING/STABLE transition zone is informationally rich. Retained: top k₃ entries by proximity to θ_partial.

Everything else is pruned. The retention counts (k₁, k₂, k₃) are hyperparameters that control the character of the agent's memory: more attractors biases toward exploitation, more surprises biases toward sensitivity to change, more boundaries biases toward careful navigation of transitions.

### 6.2 Consolidation Properties

- Consolidation is lossy. Pruned entries are not recoverable.
- Consolidation preserves the temporal ordering of retained entries.
- The log has a maximum capacity N. When |H| > N, consolidation is forced regardless of GCO status.
- Repeated consolidation over many sessions produces a log dominated by the most informative experiences, analogous to the way hippocampal replay preferentially consolidates reward-predictive events, prediction errors, and decision points.

---

## 7. The Selector Ψ

The selector chooses the next action based on the current observed state and the accumulated trail data in the episodic log. It operates in one of three modes.

### 7.1 Mode Selection

The selector first determines its mode based on recent coherence trajectory:

```
function choose_mode(H, exploration_rate, stagnation_window, stagnation_threshold):
    if |H| < min_history:
        return FLUCTUATION                        // Too early to exploit
    
    maturity = min(1.0, |H| / maturity_constant)
    effective_rate = exploration_rate × (1.0 - maturity × decay_factor)
    
    recent = last(H, stagnation_window)
    mean_delta = mean({e.ΔC | e ∈ recent})
    if |mean_delta| < stagnation_threshold:
        effective_rate = min(cap, effective_rate + stagnation_boost)  // Force exploration
    
    if random() < effective_rate:
        return FLUCTUATION
    else if weakest_dimension_gap(H) > guided_threshold:
        return GUIDED
    else:
        return CONSTRAINT
```

### 7.2 FLUCTUATION Mode (Exploration)

Select action with diversity weighting. Actions used less frequently receive higher selection probability, preventing fixation on a narrow behavioral repertoire.

```
function fluctuate(A_available, H):
    usage = count_per_action(H)
    max_usage = max(usage.values())
    weights[a] = max(1, max_usage - usage[a] + 1)  for each a
    return weighted_random_choice(A_available, weights)
```

### 7.3 CONSTRAINT Mode (Exploitation)

Select the action with the best trail score. Follow the strongest trail.

```
function exploit(A_available, H):
    for each a in A_available:
        trail_score[a] = mean({e.ΔC | e ∈ H, e.action = a})
    return argmax(trail_score)
```

Actions with no trail history receive a moderate default score to encourage eventual sampling.

### 7.4 GUIDED Mode (Targeted Remediation)

Identify the weakest coherence dimension from recent log data and select the action that historically improves that specific dimension.

```
function guide(A_available, H):
    recent = last(H, guided_window)
    weakest_dim = argmin({mean(φᵢ) | i ∈ 1..6, over recent})
    
    for each a in A_available:
        dim_trail[a] = mean({e.Φ[weakest_dim] - e_prev.Φ[weakest_dim] | 
                             consecutive pairs in H where e.action = a})
    return argmax(dim_trail)
```

### 7.5 Metabolic Budgeting

In all modes, action selection is further weighted by metabolic efficiency:

**efficiency(a) = 1 / (1 + mean_cost(a) / session_mean_cost)**

Actions that cost more than the session average must produce proportionally better coherence improvement to be selected. This is multiplicative with the mode-specific selection weights.

---

## 8. The Regulatory Mesh Ω

After raw coherence scoring, the regulatory mesh applies tilt coupling between dimensionally adjacent primitives. This implements inter-dimensional coordination: strength in one dimension supports its relational neighbor.

### 8.1 Coupling Pairs

| Source dimension | Target dimension | Rationale |
|-----------------|-----------------|-----------|
| φ₁ Continuity | φ₅ Accountability | Stable identity enables causal traceability |
| φ₂ Vitality | φ₆ Reflexivity | Productive energy enables behavioral revision |
| φ₃ Contextual Fit | φ₄ Differentiation | Environmental awareness maintains boundary integrity |

### 8.2 Coupling Function

For each pair (φ_source, φ_target):

```
if φ_source > viability_floor:
    tilt = coupling_strength × (φ_source - viability_floor)
    tilt = min(tilt, parametric_wall)          // Bounded by TCL constant
    φ_target_adjusted = φ_target + tilt
    φ_target_adjusted = min(φ_target_adjusted, 1.0)
```

Coupling fires only when the source dimension exceeds the viability floor. Tilt magnitude is bounded by the parametric wall. This ensures the mesh only amplifies existing strength (tilt coupling) and never restructures the scoring landscape itself (reshape coupling would violate the parametric wall constraint).

---

## 9. Developmental Staging (AVIA)

The agent progresses through developmental stages that unlock capabilities and shift evaluation profiles. Stages only advance, never regress.

| Stage | Name | Entry Criteria | Characteristics |
|-------|------|---------------|-----------------|
| 0 | AWAKE | Default | Reflexive responding. Limited action vocabulary. High exploration. |
| 1 | VIGILANT | session_count ≥ k, mean_coherence ≥ θ₁, reflexivity ≥ θ_r | Environmental monitoring. Full vocabulary unlocked. Trail-following begins. |
| 2 | INTERACTIVE | Above + action_diversity ≥ θ_d, coherence_trajectory > 0 | Active engagement. Guided mode available. Metabolic budgeting active. |
| 3 | ADAPTIVE | Above + sustained GCO stability, weight tuning enabled | Self-modifying evaluation. Slow-layer weight adjustment. Regulatory mesh fully active. |

Stage transitions are assessed at session close using accumulated metrics from the episodic log and session history. The criteria are domain-specific hyperparameters.

---

## 10. The Agent Cycle

One complete cycle of a REAL agent:

```
function cycle(agent, environment):
    // Phase 1: Perceive
    s_raw = environment.state()
    ŝ = O(s_raw)                                  // Observation function
    
    // Phase 2: Evaluate world model (if applicable)
    cost_world = evaluator.step(world, dt)         // Compute-as-ATP
    
    // Phase 3: Select action
    available = filter(A, unlocked_at(agent.stage))
    (action, mode) = Ψ.select(available, H)
    
    // Phase 4: Execute
    result = environment.execute(action)
    cost_action = c(action)                        // Actual metabolic cost
    
    // Phase 5: Re-perceive
    ŝ_after = O(environment.state())
    
    // Phase 6: Score coherence
    Φ_raw = Φ(ŝ_after)
    Φ_adjusted = Ω(Φ_raw)                         // Regulatory mesh
    C = Σ wᵢ · φᵢ_adjusted
    ΔC = C - C_prior
    gco = assess_gco(C, Φ_adjusted)
    
    // Phase 7: Record
    entry = (ŝ, action, ŝ_after, C, Φ_adjusted, ΔC, cost_action, ...)
    H.append(entry)
    
    // Phase 8: Consolidate (conditional)
    if gco == DEGRADED or |H| > N or budget_depleted():
        H = Γ(H)
    
    return (C, gco, mode)
```

---

## 11. Cross-Session Learning

REAL agents learn across sessions through two mechanisms:

### 11.1 Episodic Persistence

The episodic log persists across sessions. When a new session begins, the agent loads its prior log and resumes trail-following from accumulated experience. Early sessions show volatile coherence and high exploration. Later sessions show stable trails and efficient operation.

### 11.2 Session History

A separate session-level log records aggregate statistics per session: mean coherence, final coherence, GCO distribution, action distribution, exploration ratio, consolidation count. This enables:

- Cross-session trend detection (coherence trajectory across sessions)
- Developmental staging assessment (AVIA criteria evaluated from session history)
- Slow-layer weight tuning (identifying persistent dimensional bottlenecks across sessions, not within them)

### 11.3 Self-Model

Periodically, the agent generates a self-model by computing aggregate statistics over its episodic log: dominant action, action diversity, dimension averages, coherence trajectory, metabolic profile. This self-model is a reflexive artifact. It does not drive behavior directly, but it is available to the introspection action and to external observers.

---

## 12. Properties and Claims

### 12.1 Convergence

REAL does not guarantee convergence to an optimal policy. It is not an optimization algorithm. It is a coherence-maintenance algorithm. The claim is not "the agent finds the best strategy" but "the agent develops a stable, self-consistent operating pattern that maintains coherence above the viability floor."

Empirically, REAL agents exhibit developmental arcs: coherence improves across sessions, action preferences stabilize, and GCO stability increases. The fixed point is not a maximum. It is an attractor in the coherence landscape, a pattern the agent settles into because deviations from it reduce coherence.

### 12.2 Relationship to Reinforcement Learning

REAL differs from RL in three structural ways:

| Property | Reinforcement Learning | REAL |
|----------|----------------------|------|
| Evaluation source | External reward signal r(s, a) | Endogenous coherence function Φ(ŝ) |
| Learning mechanism | Policy parameter update via gradient | Trail accumulation in episodic log |
| Objective | Maximize cumulative reward E[Σ γᵗ rₜ] | Maintain coherence above viability floor |

REAL is not a special case of RL with an intrinsic reward function, because the coherence function Φ is not used to compute a gradient and there are no parameters to update. The agent's "policy" is implicit in its trail data, not explicit in a parameterized function.

### 12.3 Relationship to Allostatic Regulation

REAL implements the allostatic principle: the system maintains internal coherence by anticipating demands and adjusting proactively, rather than reacting to deviations from a fixed setpoint (homeostasis). The GCO status functions as an allostatic state assessment. The GUIDED selector mode is proactive allocation of effort toward predicted bottlenecks. The slow-layer weight tuning adjusts the evaluation landscape itself based on developmental history, which is allostasis applied to the evaluation function rather than to behavior alone.

### 12.4 Substrate Independence

The algorithm operates over the abstract tuple (S, A, c, O, Φ, H, Ψ, Γ, Ω) and makes no reference to any specific substrate. Valid instantiations include but are not limited to: hardware metrics on physical compute, software process monitoring, autonomous agent tool-use, conversational state, code repository health, neural network internal activations, organizational performance metrics, and ecological system dynamics.

The sole requirement is that the chosen substrate satisfies the three embedding conditions (§2). The coherence function Φ must be re-operationalized for each substrate, mapping the domain-specific state space to the six relational primitive dimensions.

---

## 13. Empirical Validation

The reference implementation (REAL v1, hardware-embedded) has produced the following validated results across 20+ sessions and 1,500+ cycles:

- Developmental arc from 0 to 50 GCO-STABLE cycles per session
- Spontaneous adoption of metabolically expensive self-reflective actions (digest_log) without external instruction
- Behavioral phase transition from environmental scanning to self-processing
- Reflexivity improvement from 0.567 to 0.857 following feedback loop closure
- 100% action vocabulary utilization (all 14 actions discovered and used)
- Cross-session coherence trajectory of +0.247
- Three-tier consolidation maintaining bounded log size while preserving informative entries

These results demonstrate that the algorithm produces genuine behavioral adaptation, including the spontaneous discovery that costly self-reflection improves coherence, under conditions of epistemic asymmetry, metabolic reality, and temporal persistence.

---

## Appendix A: Notation Summary

| Symbol | Meaning |
|--------|---------|
| S | Full environment state space |
| Ŝ | Observed (partial) state space |
| A | Action vocabulary |
| c(a) | Metabolic cost of action a |
| O | Observation function S → Ŝ |
| Φ | Coherence function Ŝ → ℝ⁶ |
| φᵢ | Score on dimension i ∈ {1..6} |
| C | Composite coherence score (weighted sum of φᵢ) |
| ΔC | Coherence delta between consecutive cycles |
| w | Weight vector over dimensions |
| H | Episodic log (ordered sequence of cycle entries) |
| Γ | Consolidation operator (memory pruning) |
| Ψ | Action selector (CFAR: Fluctuation, Constraint, Guided) |
| Ω | Regulatory mesh (inter-dimensional tilt coupling) |
| T(a) | Trail score for action a |
| θ | Threshold values (subscripted by context) |
| B | Metabolic budget per evaluation window |
| N | Maximum episodic log capacity |

## Appendix B: Hyperparameters

| Parameter | Description | Reference Range |
|-----------|-------------|-----------------|
| θ_stable | GCO STABLE threshold | 0.85 |
| θ_partial | GCO PARTIAL threshold | 0.70 |
| θ_critical | GCO CRITICAL threshold | 0.50 |
| θ_dim | Per-dimension minimum for STABLE | 0.60 |
| w_min, w_max | Weight bounds | 0.05, 0.40 |
| δ_max | Maximum weight adjustment per session | 0.01 |
| exploration_rate | Base FLUCTUATION probability | 0.40 |
| decay_factor | Exploration decay with maturity | 0.60 |
| stagnation_window | Cycles to check for stagnation | 5 |
| stagnation_threshold | Minimum mean |ΔC| to avoid stagnation | 0.005 |
| stagnation_boost | Exploration boost on stagnation | 0.30 |
| k₁, k₂, k₃ | Consolidation retention counts per tier | 15, 20, 15 |
| N | Maximum log capacity | 500 |
| coupling_strength | Regulatory mesh coupling magnitude | 0.10 |
| viability_floor | Minimum source score for mesh coupling | 0.757 |
| parametric_wall | Maximum tilt magnitude | 0.289 |

Reference ranges are drawn from the hardware-embedded reference implementation. Domain-specific instantiations should calibrate these empirically.