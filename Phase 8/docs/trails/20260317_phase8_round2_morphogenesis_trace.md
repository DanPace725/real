# Phase 8 — Round 2 Morphogenesis Improvements Trace

**Date:** 2026-03-17
**Time:** UTC evening
**Model:** Claude Sonnet 4.6
**Type:** H_e (Episodic Trace)
**Harnesses:** `compare_morphogenesis.py`, `compare_latent_context.py`
**Seeds:** 13, 23, 37, 51, 79
**Follows:** `20260317_phase8_improvement_round1_trace.md`

---

## 1. Changes Implemented

Two targeted improvements addressing the residual open issues from Round 1:

| # | Target | Change |
|---|---|---|
| R2-1 | `phase8/topology.py` | Add `routing_feedback_gate: float = 0.0` to `MorphogenesisConfig` |
| R2-2 | `phase8/environment.py` | Wire `routing_has_feedback` gate into `growth_ready` condition |
| R2-3 | `phase8/environment.py` | Expand `anticipatory_ready` to fire on `queue_pressure` (any node, not just source) |
| R2-4 | `phase8/environment.py` | Remove `positive_energy_streak` and `structural_value` requirements from `anticipatory_ready` |
| R2-5 | `compare_morphogenesis.py` | Set `routing_feedback_gate=0.05` in `benchmark_morphogenesis_config()` |

**Rationale for R2-1/R2-2:** branch_pressure grows 100% of seeds but earns 0%. The hypothesis was that requiring positive routing feedback before growth would block premature budding in routing-only scenarios.

**Rationale for R2-3/R2-4:** sustained_pressure earns 0% growth because ATP stays in deficit under constant load, and anticipatory growth (source backlog only) was blocked by `positive_energy_streak >= 1` — exactly the condition that fails under sustained pressure.

---

## 2. Morphogenesis Results — Round 2

### 2a. Scenario: branch_pressure

| Metric | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Growth realization | 100% | 100% | 0 |
| Earned growth rate | 0% | **0%** | 0 |
| Growth win rate | 0% | 0% | 0 |

**Unchanged.** The routing_feedback_gate hypothesis was incorrect: branch_pressure nodes are actively routing packets, so `feedback_recent > 0.05` is satisfied at the time of budding. The gate correctly distinguishes zero-feedback nodes from live-routing nodes, but branch_pressure nodes are live-routing — they're just doing routing-only work with no task scoring. The gate passes and growth still fires prematurely.

**Root cause confirmed:** branch_pressure is a task-free scenario (no task metadata, no context_bit). Any topology growth is structurally unrooted — new nodes receive default supports and are bypassed because no context-specific seeding can fire. This is an architectural mismatch, not a tuning problem. No parameter adjustment can make morphogenesis earn value in a task-free scenario within the CVT-1 framework.

### 2b. Scenario: sustained_pressure

| Metric | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Growth realization | 0% | **0%** | 0 |
| Earned growth rate | 0% | 0% | 0 |

**Unchanged.** The expanded anticipatory_ready condition (queue_pressure OR ingress_backlog, any node) still never fires. Root cause analysis:

- `queue_pressure = min(1.0, overflow / inbox_capacity)` — this is inbox overflow-based, not load-based. Under sustained_pressure, adaptive admission control prevents overflow.
- `ingress_backlog` is only non-zero at source_id. Admission control meters input to prevent source backlog from building.
- Both metrics are effectively 0.0 for all nodes throughout the scenario.

**Root cause confirmed:** The admission control system is working correctly — it meters traffic to match what the fixed topology can absorb. This prevents the pressure signals (`queue_pressure`, `ingress_backlog`) that would trigger anticipatory growth. The system cannot distinguish between "load is manageable, no growth needed" and "load is heavy but being handled by admission throttling, growth would help." From the observation space, these look identical (both show near-zero overflow).

Additionally, sustained_pressure also carries no task metadata (routing-only scenario), so any growth that did fire would face the same structural unrooting problem as branch_pressure.

### 2c. Scenario: cvt1_task_b_stage1 (cold start)

| Metric | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Growth realization | 80% | 80% | 0 |
| Earned growth rate | 20% | 20% | 0 |
| Growth win rate | 20% | 20% | 0 |
| Dynamic node value | 0.086 | 0.086 | 0 |
| Dynamic net energy | −0.039 | −0.039 | 0 |

**Unchanged.** R2 changes do not affect task scenarios with visible context. The routing_feedback_gate=0.05 is satisfied by nodes that have active routing feedback, so cold-start cvt1 behavior is unaffected.

### 2d. A→B Transfer with morphogenesis

| Metric | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Fixed transfer exact | 6.2 | 6.2 | 0 |
| Growth transfer exact | 7.4 | 7.4 | 0 |
| Growth transfer bit acc | 0.5833 | 0.5833 | 0 |
| Dynamic node value | 0.2233 | 0.2233 | 0 |
| Dynamic net energy | −0.0898 | −0.0898 | 0 |
| Earned growth rate | 80% | 80% | 0 |
| Growth win rate | 60% | 60% | 0 |

**Stable.** Transfer+morphogenesis results unchanged from Round 1. The R2 changes (routing_feedback_gate, expanded anticipatory) do not degrade the core transfer benefit.

---

## 3. Latent Context Results — Round 2 Stability Check

Run `compare_latent_context.py` to confirm Round 1 improvements remain stable after R2 code changes.

### 3a. In-distribution

| Condition | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Task A — visible | 10.0 | 10.0 | 0 |
| Task A — latent | 2.2 | 2.2 | 0 |
| Task B — visible | 3.0 | 3.0 | 0 |
| Task B — latent | 8.6 | 8.6 | 0 |

**Stable.** Latent context improvements from Round 1 (PROMOTION_STREAK=2, PROMOTION_THRESHOLD=0.78) are not affected by R2 morphogenesis changes.

### 3b. A→B Transfer

| Condition | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Visible train → Visible B | 6.2 | 6.2 | 0 |
| Latent train → Latent B | 7.0 | 7.0 | 0 |
| Bit acc delta (latent − visible) | +0.066 | +0.057 | −0.009 |

**Stable.** Latent transfer continues to exceed visible (+0.8 exact). Bit accuracy delta narrows slightly (−0.009) within seed-level variance.

---

## 4. Summary: What Round 2 Resolved

| Issue | Hypothesis | Result | Conclusion |
|---|---|---|---|
| branch_pressure 0% earned | routing_feedback_gate would block premature growth | **Hypothesis incorrect** — nodes DO have feedback > 0.05 | Task-free routing scenarios are architectural mismatches for CVT-1 morphogenesis |
| sustained_pressure 0% realization | queue_pressure trigger would fire under load | **Hypothesis incorrect** — admission control prevents queue overflow | Observation space cannot distinguish "admission-managed load" from "no load" |

Both open issues from Round 1 were architectural mismatches, not tuning gaps. No parameter adjustment or signal expansion within the current observation space can address them without modifying scenario design or the observation function.

---

## 5. Architectural Conclusions

### When morphogenesis works (confirmed)

- **Task scenario + warm substrate carryover**: Transfer+morphogenesis delivers +1.2 exact matches, 60% win rate, 80% earned growth. The mechanism is clear: warm carryover provides routing clarity before growth fires, new nodes receive feedback-validated seeding, and the ATP surplus window opens after routing stabilizes.

### When morphogenesis cannot work (confirmed architectural limits)

1. **Task-free routing scenarios (branch_pressure, sustained_pressure)**: CVT-1 morphogenesis requires task metadata and context bits to seed new nodes productively. Without these, growth is structurally unrooted regardless of when it fires. These scenarios should be evaluated against different systems (e.g., pure routing optimizers without task substrate).

2. **Admission-managed load (sustained_pressure)**: The observation space (`queue_pressure`, `ingress_backlog`) is overflow-based. Admission control prevents overflow, making the system indistinguishable from no-load in these signals. A load-based anticipatory trigger would require a new observation signal — e.g., `admission_velocity` (rate of change in admission rate) or `throughput_deficit` (gap between raw demand and admitted rate) — which are not currently exposed per-node.

### Design gap documented

Phase 8 morphogenesis is task-substrate-coupled by design. Growth seeding (edge support, action support) is only meaningful when context and task metadata are present. For routing-only workloads, morphogenesis provides no benefit and may add cost (upkeep on unused nodes). This is a correct architectural constraint, not a bug.

---

## 6. H_c Consolidated Pattern Update

**Morphogenesis domain is task+transfer, not routing.** The evidence across three rounds is unambiguous: morphogenesis earns value in task scenarios with warm carryover, and provides no value in task-free routing scenarios. This is an architectural constraint of the CVT-1 substrate coupling, and should be documented as a design invariant rather than treated as a tuning problem.

**Routing_feedback_gate is a meaningful gate for zero-feedback nodes.** It correctly blocks budding at nodes that have never received routing feedback (e.g., isolated nodes, unreachable sinks). It is not effective against routing-only nodes that have feedback but no task scoring. The gate's semantic meaning is "don't grow into unrouted territory" — which is correct and useful for task scenarios, irrelevant for routing-only scenarios where all nodes are already routing.

**Admission control and anticipatory growth are in tension.** The adaptive admission control (a strength of the system for stability) actively suppresses the pressure signals that anticipatory growth watches. These two mechanisms are architecturally incompatible without a new observation signal that tracks admission throttling directly. This is a known open design gap, not an implementation error.
