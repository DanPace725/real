# ATP Budget Report: The Metabolic Wall

**Date:** 2026-03-15
**Data sources:** Budget sweep (10 levels × 3 seeds × 10 sessions), A/B comparisons at 2.0, 3.5, and unlimited ATP (5 seeds × 15 sessions per condition)

---

## Summary

Adding an explicit per-session ATP budget to the integrated REAL + substrate engine reveals a phase transition: there exists a minimum metabolic budget (~2.5–3.0 ATP) below which the two-layer memory architecture is a net cost, and above which it is a net benefit. This is the TCL parametric wall realized computationally — the system cannot sustain its own complexity without sufficient metabolic resources.

---

## The Budget Mechanism

Every action now has an ATP cost drawn from the same pool:

| Action | ATP Cost | Category |
|---|---|---|
| rest | 0.00 | Domain |
| scan | 0.03 | Domain |
| introspect | 0.06 | Domain |
| invest_* | 0.06–0.15 (varies by neighbors) | Substrate |
| maintain_substrate | 0.01–0.03 per active dim | Substrate |

The engine filters available actions to only those the agent can afford. When the budget depletes, only rest remains. The baseline engine uses the same cost table, so both conditions face identical metabolic rules.

Natural ATP consumption at saturation is ~3.3 ATP/session. The baseline naturally spends ~1.5 ATP/session (only domain actions).

---

## Budget Sweep Results

| Budget | Coherence | Active Dims | Coupling | STABLE | Invest | Maintain | Domain | Rest |
|--------|-----------|-------------|----------|--------|--------|----------|--------|------|
| 0.5 | 0.563 | 0.0 | 0.000 | 10% | 5% | 3% | 91% | 89% |
| 1.0 | 0.602 | 0.0 | 0.000 | 20% | 11% | 8% | 81% | 77% |
| 1.5 | 0.627 | 0.0 | 0.000 | 28% | 18% | 11% | 72% | 68% |
| 2.0 | 0.660 | 0.0 | 0.000 | 37% | 24% | 14% | 62% | 59% |
| 2.5 | 0.710 | 0.1 | 0.009 | 49% | 30% | 18% | 52% | 46% |
| **3.0** | **0.755** | **0.5** | **0.076** | **60%** | **38%** | **21%** | **41%** | **35%** |
| 5.0 | 0.799 | 4.1 | 0.263 | 76% | 37% | 33% | 31% | 7% |
| inf | 0.803 | 4.3 | 0.318 | 75% | 37% | 34% | 30% | 11% |

The transition from 0 to 4+ active dimensions happens almost entirely between 2.5 and 5.0 ATP. Below 2.5, no slow-layer infrastructure can be established regardless of the agent's strategy. Above 5.0, the budget is non-binding. The **wall** sits at roughly 3.0 ATP.

---

## A/B Comparison Across the Wall

Three conditions, same domain, same seeds:

### Above the wall (3.5 ATP)

|  | Baseline | Substrate | Delta |
|---|---|---|---|
| Coherence | 0.727 | 0.801 | **+10.2%** |
| STABLE | 72.6% | 75.7% | +3.1pp |
| accountability | 0.530 | 0.778 | +0.248 |
| differentiation | 0.714 | 0.913 | +0.200 |

The substrate agent allocates 67% of its actions to infrastructure (33% maintain, 34% invest) and still outperforms the baseline by 10%. The infrastructure investment pays off through better epistemic access and traceable action-outcome links.

### Below the wall (2.0 ATP)

|  | Baseline | Substrate | Delta |
|---|---|---|---|
| Coherence | 0.726 | 0.658 | **-9.4%** |
| STABLE | 71.3% | 35.8% | -35.5pp |
| DEGRADED | 6.8% | 36.5% | +29.7pp |
| reflexivity | 0.684 | 0.475 | -0.208 |

The substrate agent is worse across nearly every dimension. It burns ATP on investment that never crosses the bistable threshold, then rests for 59% of cycles because the budget is exhausted. The observation noise penalty (from having no slow-layer support) compounds the damage.

### The crossover

| Budget | Substrate Coherence | Baseline Coherence | Substrate Advantage |
|--------|--------------------|--------------------|---------------------|
| 2.0 | 0.658 | 0.726 | **-9.4%** |
| 2.5 | 0.710 | ~0.727 | ~-2.3% |
| 3.0 | 0.755 | ~0.727 | ~+3.9% |
| 3.5 | 0.801 | 0.727 | **+10.2%** |
| inf | 0.803 | 0.727 | **+10.4%** |

The crossover is between 2.5 and 3.0 ATP. Below it, the substrate is a liability. Above it, it's an asset.

---

## What This Means

### The parametric wall is real

TCL predicts that systems under metabolic constraints develop bistable complexity thresholds — a minimum energy expenditure below which organized structure cannot be maintained. The budget sweep confirms this: the slow layer requires ~3.0 ATP/session to bootstrap. Below that, the agent is better off without it.

This is not a soft degradation. Active dimensions go from 0 (at 2.5) to 4.1 (at 5.0) over a narrow range. The transition is sharp because of the bistable dynamics: partial investment that doesn't cross the threshold is wasted, and wasted investment leaves the agent worse off than if it had never tried.

### Below the wall, the substrate is toxic

At 2.0 ATP, the substrate agent is 9.4% worse than baseline. The mechanism:

1. The selector still tries to invest (24% of actions) because it's designed to build infrastructure
2. None of those investments cross the bistable threshold (0 active dims)
3. The ATP spent on failed investment means fewer domain actions
4. The observation noise penalty (no slow-layer support = max noise) degrades all observation-dependent dimensions
5. Rest rate hits 59% — the agent is metabolically starved

The agent is paying the cost of complexity without getting the benefit. This is the regime where simpler organisms outcompete complex ones.

### Above the wall, the advantage is robust

At 3.5 ATP, the substrate agent faces real metabolic pressure (natural consumption is ~3.3 ATP) yet still achieves +10.2% coherence. The budget forces harder tradeoffs than the unbounded case, but the tradeoffs are productive — the agent invests selectively and maintains what matters.

The fact that 3.5 ATP and unlimited produce nearly identical results (0.801 vs 0.803) means the system self-limits its own complexity. It doesn't expand infrastructure indefinitely; it builds ~4 active dimensions and stops. The extra budget goes unused.

### The baseline is budget-insensitive

The baseline spends ~1.5 ATP/session regardless of the budget. At 3.5 ATP, it has 2.0 ATP of unused capacity. It can't use extra metabolic resources because its behavioral vocabulary (3 domain actions) doesn't include infrastructure investment. This is the cost of simplicity: robust under scarcity, unable to benefit from abundance.

---

## Implications for System Design

1. **Budget should be a first-class parameter.** The default should sit above the wall (>3.0 ATP) but not so high that it's non-binding. 3.5–4.0 ATP forces productive tradeoffs while allowing infrastructure.

2. **The selector needs budget awareness below the wall.** Currently, the selector tries to invest even when the budget can't support it. A budget-aware selector would recognize when investment is futile and fall back to domain-only behavior — essentially becoming the baseline when resources are too scarce. This would eliminate the toxicity below the wall.

3. **The wall height is a system property.** It depends on: write_base_cost, maintain_base_cost, bistable_threshold, decay rate, and the number of dimensions. Changing any of these shifts the wall. A system that can lower its infrastructure costs (through neighbor discounts, through consolidation) effectively lowers its own metabolic floor.

4. **Cross-session carryover lowers effective cost.** A well-established slow layer from prior sessions requires only maintenance (cheap) rather than investment (expensive). This means mature agents operate below the per-session wall that new agents face — their history subsidizes their current budget. The wall is highest for fresh agents.

---

*Built on: budget_sweep.py (10-level sweep), ab_comparison.py (budgeted A/B). All data in experiment_data/budget_sweep_v2/, ab_budget_3.5/, ab_budget_2.0/.*
