# Phase 8 Code Alignment Trace (Deep Evaluative Pass)

## Date

2026-03-16

## Timestamp

2026-03-16T17:22:16+00:00

## Model

GPT-5.2-Codex

## Prompt

Take a closer evaluative look at the Phase 8 code and implementation, starting from Phase 8 and referencing prior phases and vision documents. Identify alignment, inconsistencies, oversights, blindspots, and weak points. Do not alter code; save findings in trace-style docs.

## Inputs Reviewed

- `Phase 8/AGENTS.md`
- `Phase 8/vision.md`
- `Phase 8/first_computational_experiment_spec.md`
- `Phase 8/README.md`
- `Phase 8/phase8/node_agent.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/consolidation.py`
- `Phase 8/phase8/admission.py`
- `Phase 8/phase8/models.py`
- `Phase 8/phase8/scenarios.py`
- `Phase 8/tests/test_phase8.py`
- Context references: root `README.md`, `Phase 4/README.md`, `Phase 6/REAL_Integration_Summary.md`, `Phase 7/implementation plan.md`

---

## Executive Evaluation

Phase 8 implementation is broadly coherent with its declared constraints (local learning, ATP gating, sequential feedback, carryover mechanics) and represents a real bridge from theory to runnable substrate experiments.

However, the current implementation has several structural weakpoints that likely explain why transfer quality is mixed and why warm starts can still underperform on mean bit accuracy:

1. **The six-primitives scoring is partially underdetermined and can be gamed by local heuristics.**
2. **Consolidation and support maintenance are still mostly reward-adjacent, but not strongly tied to error-correction trajectories.**
3. **Task context handling remains Stage-1-explicit and may overfit to explicit `context_bit` rather than latent history.**
4. **Cross-layer governance is not yet explicit enough (e.g., no hard primitive-level invariants test suite).**
5. **A few implementation shortcuts (path injection, private engine calls) are practical but architectural debt if Phase 8 is to become a stable substrate platform.**

---

## Strong Alignment Signals (What is working)

### A) Locality + anti-global-gradient discipline is genuinely enforced

- Node agents only see local observations and neighbor-facing action vocab.
- Reward/feedback propagates edge-by-edge upstream (not broadcast globally).
- No code path found that computes a network-wide loss and updates all nodes together.

This is the core philosophical requirement from `AGENTS.md` and remains intact.

### B) ATP gating is not cosmetic

- Action execution, route costs, maintenance costs, and admission pacing all create explicit energetic tradeoffs.
- The source-admission substrate extends metabolic accounting to ingress itself.

This helps keep the substrate from becoming a hidden unconstrained optimizer.

### C) Carryover is materially represented, not just statistical

- The substrate explicitly stores and reloads support structures.
- Substrate-only carryover mode helps isolate “structural memory” from episodic memory.

This aligns with the memory-substrate goals inherited from Phase 7.

### D) CVT-1 path is directionally consistent with vision

- Packet content, transform actions, sink bit-level scoring, and transfer harnesses exist.
- The project has moved from “routing-only” toward computationally meaningful tasks.

---

## Weakpoints, Inconsistencies, and Blindspots

### 1) Primitive scoring semantics are partially conflated

The coherence model computes six dimensions, but some dimensions currently mix throughput, queue pressure, and post-hoc reward in ways that can blur causal interpretation:

- `vitality`, `contextual_fit`, and `reflexivity` all increase from immediate reward-side variables.
- `differentiation` uses route specialization frequency over recent actions; this can reward rigid routing habits even when task context shifts.

Risk: nodes may maximize local coherence proxies without robustly increasing task-correct transform behavior.

### 2) Consolidation trigger still uses engine private call path

`NodeAgent.step()` invokes `self.engine._run_consolidation()` directly after repeated rest behavior.

Risk: private call reliance can drift from upstream engine semantics and makes consolidation policy harder to evolve cleanly.

### 3) Stage 1 context affordance may leak shortcut behavior

Current CVT-1 Stage 1 includes explicit context flag support. This is intended by spec for bridge-stage engineering, but it creates a strategic blindspot:

- success may over-rely on explicit context tagging and under-develop latent sequence sensitivity.

Risk: apparent task improvement may not transfer to Stage 2 latent-context conditions.

### 4) Differentiation vs adaptability tension is unresolved

The system rewards specialization (differentiation proxy), but transfer tasks require controlled reconfiguration.

Risk: hard-won specialization may resist re-tuning under Task B shifts, producing exact-match gains but weaker average bit accuracy.

### 5) Maintenance policy may preserve stale supports too long

Maintenance and context-credit promotion are strong features, but current substrate behavior may still carry stale route/transform supports across task shifts if demotion pressure is insufficient or delayed.

Risk: substrate memory can become a source of transfer interference rather than transfer advantage.

### 6) Architecture debt: path injection + private surfaces

Multiple modules add Phase 4 root through `sys.path` mutation and rely on internal mechanics across layers.

Risk: reproducibility and packaging robustness may become friction points as Phase 8 grows.

---

## Oversight Check Against Vision + AGENTS constraints

### Non-negotiables mostly respected

- no global gradient update: respected
- no global planner that injects correct route: respected
- no target bits exposed to local observers: appears respected
- ATP scarcity and local constraints: respected

### Under-specified areas

- hard tests for “no non-local leakage” beyond current local-observation checks could be strengthened
- primitive-level invariants are not yet enforced as first-class contract tests
- evidence that substrate structures correspond to computationally causal subprograms remains mostly inferential

---

## Specific Hypotheses for Current Transfer Weakness

1. **Selector pressure overweights durable route economy relative to context-conditional transform correction.**
2. **Context-action support promotion threshold is reachable faster than contradiction resolution under task switch.**
3. **Reflexivity scoring is too short-horizon to detect slowly emerging mismatch on Task B.**
4. **Admission/queue dynamics can mask task-specific learning gains by dominating local ATP budgets during dense bursts.**

---

## Recommended Next Validation Loops (No code changes performed in this pass)

1. Add a primitive-contract test panel (continuity/vitality/contextual_fit/differentiation/accountability/reflexivity invariants under synthetic state perturbations).
2. Add explicit transfer-interference diagnostics that attribute Task B miss patterns to:
   - branch choice error,
   - wrong transform family,
   - stale context-bound support,
   - admission throttling side effects.
3. Add Stage-2 readiness checks that disable explicit context and verify latent-history dependence before claiming transfer stability.
4. Track maintenance “survival curves” for supports to separate useful durable attractors from inert substrate residue.

---

## Final Assessment

Phase 8 is architecturally serious and not merely rhetorical: it already enforces local adaptation mechanics and offers runnable comparative harnesses. The main gap is now less about adding features and more about **tightening causal validity** between primitive-level coherence, substrate promotion, and task-correct transfer behavior under context shift.

This is a healthy stage to be in: the framework has enough instrumentation to expose its own weaknesses, which is precisely what makes it scientifically usable.
