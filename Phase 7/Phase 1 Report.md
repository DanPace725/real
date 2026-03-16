# Phase 1 Report: Instrumentation and Findings

**Date:** 2026-03-15
**Data sources:** 20-session baseline (run_001), parameter sweeps (decay, budget, threshold, acceleration), self-reinforcing closure test

---

## Summary

The two-layer memory substrate from Phase 0 produces genuine bistable dynamics with a clear developmental arc. All five structural invariants are observable. However, two issues emerged that need correction before Phase 2: the metabolic budget is not binding (action costs are too low to create real tradeoffs), and the coupling score formula doesn't capture the actual mechanism (variance reduction, not level alignment).

---

## Finding 1: Bistability Is Clean and Very Stable

The slow-layer value distribution is strongly bimodal:

- **4.5%** near zero (< 0.05)
- **0.7%** in transition (0.05–0.25)
- **94.9%** above threshold (≥ 0.25)
- **116** upward threshold crossings, **1** downward crossing

Once an entry is established above threshold, it essentially never falls back under current parameters. The transition zone is nearly empty — entries are either off or on. This is clean bistability.

**Implication:** The bistable dynamics are working, but may be too sticky. Entries should be able to collapse if the agent genuinely stops maintaining them. The current decay rate (0.02/cycle) is slow enough that even infrequent maintenance prevents collapse. Consider 0.03 for sharper dynamics.

---

## Finding 2: Self-Reinforcing Closure Works

When 3 of 6 slow-layer dimensions were zeroed after a full build-up:

- **2/3 recovered in 1 session**, all 3 recovered in 2 sessions
- Post-recovery coherence matched pre-perturbation levels (0.785 vs 0.781)
- The neighbor discount mechanism enabled cheaper rebuilding

The pattern rebuilds itself when partially damaged, as predicted by the cellular memory research. Active neighbors reduce write costs for decayed entries, creating a pull toward the prior configuration.

---

## Finding 3: The Budget Constraint Is Not Binding

The budget sweep produced **identical results** across all levels (2.0, 3.5, 5.0, 7.0 ATP). The agent never exhausts its budget at any level. This means metabolic reality (invariant #2) is not producing meaningful tradeoffs.

**Root cause:** Action costs are too low. With observe at 0.005, invest at ~0.05, and maintain at ~0.01 per entry, a typical session consumes ~1.5 ATP regardless of budget. The costs need to scale up, or the budget needs to come down significantly, to create genuine scarcity.

**Fix needed for Phase 2:** Either increase action costs by ~3x or set the budget to ~1.5 so the constraint binds. The interesting dynamics (choosing what to maintain vs. what to let decay) only emerge under genuine scarcity.

---

## Finding 4: Decay Rate Sweet Spot Is 0.02–0.03

| Decay | Coherence | STABLE | Active | Coupling |
|-------|-----------|--------|--------|----------|
| 0.01 | 0.748 | 46% | 5.8 | 0.274 |
| 0.02 | 0.789 | 55% | 5.7 | 0.234 |
| 0.03 | 0.795 | 54% | 5.0 | 0.195 |
| 0.05 | 0.769 | 36% | 2.3 | 0.223 |

- **0.01** is too slow: entries accumulate easily, no maintenance pressure, lower coherence.
- **0.02** (current): good balance, most entries survive.
- **0.03**: slightly higher coherence, forces more selective maintenance, 5 active dims instead of 5.7.
- **0.05**: too fast, only 2.3 active dims, agent can't build enough infrastructure.

**Recommendation:** Move to 0.03. The slight increase forces the agent to be more selective about what it maintains, which is closer to the "can't maintain everything" dynamic we want.

---

## Finding 5: Higher Bistable Threshold Increases Coupling Quality

| Threshold | Coherence | STABLE | Active | Coupling |
|-----------|-----------|--------|--------|----------|
| 0.15 | 0.789 | 53% | 5.9 | 0.242 |
| 0.25 | 0.789 | 55% | 5.7 | 0.234 |
| 0.35 | 0.779 | 50% | 4.7 | 0.219 |
| 0.45 | 0.746 | 42% | 4.3 | 0.295 |

At 0.45, coupling score jumps to 0.295 — the highest in any sweep — despite lower coherence and fewer active dimensions. When the threshold is high, maintaining entries is harder, so the entries that survive are more meaningfully tied to behavior. Fewer but more meaningful constraints.

**Recommendation:** Keep at 0.25 for now but explore 0.30–0.35 once the budget constraint is binding. The combination of higher threshold + real scarcity should produce the most interesting dynamics.

---

## Finding 6: Coupling Score Formula Needs Revision

The current formula (slow_val × fast_stability × fast_mean) doesn't capture the real mechanism. The per-dimension coupling breakdown shows that variance reduction is the actual signal:

| Dimension | Var (active) | Var (inactive) | Reduction |
|-----------|-------------|----------------|-----------|
| continuity | 0.0853 | 0.1944 | 56% |
| differentiation | 0.0146 | 0.0521 | 72% |
| contextual_fit | 0.0292 | 0.0465 | 37% |
| reflexivity | 0.0379 | 0.0738 | 49% |
| accountability | 0.0815 | 0.1136 | 28% |
| vitality | 0.0885 | 0.1339 | 34% |

Every dimension shows lower fast-layer variance when the slow layer is active. This confirms the mechanism: the slow layer is reducing observation noise, which is what it should do. The coupling formula should be revised to weight variance reduction directly.

**Proposed formula:**

```
coupling(dim) = slow_val * (1 - var_active / var_baseline)
```

Where `var_baseline` is the expected variance without slow-layer support.

---

## Finding 7: Predictive Power Is Modest but Real

- Active count → future coherence: r = 0.161 (weak positive)
- Best per-dimension predictor: contextual_fit (r = 0.203)
- When contextual_fit dimension scores > 0.65, mean slow-layer value is 0.706; when < 0.50, it's 0.605

The slow layer helps, but it's not the dominant factor in coherence. This makes sense: the coherence model scores several things (action diversity, reflexivity, accountability) that aren't directly about observation quality. The slow layer improves observation, which improves some dimensions but not all.

---

## Finding 8: The Developmental Arc Is Clear

Session-by-session trajectory with slow-layer carryover:

- **Sessions 1–3**: Investment phase. 3→5 active dimensions. Heavy invest actions.
- **Session 4**: Inflection. All 6 active. 72% STABLE. Behavioral shift.
- **Sessions 5–20**: Mature phase. All 6 maintained. 54–72% STABLE. Observe-dominant.
- **Coherence trend**: r = 0.534 (moderate positive). +0.034 gain early→late.

The agent spontaneously develops a two-phase behavioral pattern: build infrastructure, then use it. This mirrors the TCL prediction that systems under metabolic constraints develop fast/slow layer differentiation.

---

## Consolidation Strategy Implications

The data suggests that consolidation for the slow layer is structurally different from episodic log consolidation.

**The episodic log problem:** Too many entries → cull the least useful ones (attractors, surprises, boundaries).

**The slow-layer problem:** Once established, entries self-maintain. The real decision is not what to keep but **what to invest in next**. The consolidation question becomes: given limited ATP, which dimensions should the agent prioritize building or strengthening?

**Derived strategy:**

1. **Investment priority ordering.** When the budget is scarce (which it currently isn't but should be), the agent should invest in dimensions where the slow-layer value is just below the bistable threshold — the transition zone where a small investment has the highest leverage.

2. **Selective maintenance under scarcity.** When the budget can't cover maintaining all active entries, the agent should maintain dimensions where the observation quality improvement is largest (highest variance reduction). Let less impactful dimensions decay.

3. **No consolidation needed for stable entries.** Active entries above ~0.35 don't need consolidation logic — they self-maintain at low cost. The decay mechanism handles pruning naturally: anything not maintained eventually collapses.

4. **Cross-session consolidation is promotion.** The three-tier episodic consolidation (attractors, surprises, boundaries) identifies what was important. Those insights should inform slow-layer investment: if a particular dimension consistently appears in attractor or surprise entries, that dimension deserves slow-layer investment.

---

## Adjustments for Phase 2

Before building the visualization layer, two changes are needed:

1. **Make the budget bind.** Increase action costs or lower budget so the agent must choose between maintaining, investing, and acting. Target: agent exhausts 80–90% of budget per session.

2. **Revise coupling formula.** Switch from level-alignment to variance-reduction. This makes the coupling score actually measure what we care about.

These should be implemented as Phase 1.5 corrections before proceeding.

---

*Based on: 20-session baseline run, 16-configuration parameter sweep, 1 perturbation/recovery test, 1000 total sessions of logged data.*
