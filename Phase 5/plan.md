# Phase 5 Architecture Plan

**Date:** March 11, 2026
**Status:** Planning

---

## Research Question

Does inference friction — the metabolic cost of resolving competing optimization constraints during LLM generation — have a measurable signature in logit and activation topology? And can a coherence-maintenance algorithm (REAL) identify and respond to that signature as an endogenous slow-layer regulatory substrate?

---

## Architecture

### System Tuple (Phase 4 notation, re-operationalized)

| Symbol | Phase 5 Meaning |
|---|---|
| **S** | Internal activation state during inference: token-level logit entropy, hidden state trajectory variance, attention pattern distribution |
| **A** | Inference interventions: `adjust_temperature`, `inject_prefix`, `scale_attention`, `rest` (no-op cycle) |
| **c** | Wall-clock cost of each intervention (additional forward passes, prefix token overhead) |
| **O** | Partial observation via TransformerLens hooks: not full hidden state, but computed statistics over it |
| **Φ** | Coherence function mapping activation statistics → six dimensions (see below) |
| **H** | Episodic log of (state_before, intervention, state_after, coherence, delta) across generation steps |
| **Ψ** | CFAR selector (Phase 4 `real_core/selector.py`, reused unchanged) |
| **Γ** | Three-tier consolidation (Phase 4 `real_core/memory.py`, reused unchanged) |
| **Ω** | Regulatory mesh (Phase 4 `real_core/mesh.py`, reused unchanged) |

### Embedding Condition Verification

| Condition | Phase 5 Satisfaction |
|---|---|
| **Epistemic asymmetry** | REAL observes activation statistics, not full hidden state; cannot directly set token probabilities |
| **Metabolic reality** | Each intervention costs real compute time (additional forward passes, prefix overhead) |
| **Temporal persistence** | Context window accumulates; previous interventions shape future attention patterns |

### Coherence Function Φ — Mapping Activations to Six Dimensions

| Dimension | Primitive | Operationalization |
|---|---|---|
| **Continuity** | P1 Ontological | Low variance in hidden state trajectories across recent generation steps. High trajectory variance = identity instability. |
| **Vitality** | P2 Dynamical | Per-token compute in the productive range: inverted parabola over mean logit entropy. Both near-zero entropy (total certainty, no process) and maximum entropy (uniform confusion) are low vitality. |
| **Contextual Fit** | P3 Geometric/Causal | Alignment between attention pattern topology and input structure. Does attention actually concentrate on contextually relevant tokens, or diffuse randomly? |
| **Differentiation** | P4 Constraint | Is the model distinguishing relevant from irrelevant context? Measured as attention head specialization (low cross-head entropy = heads doing distinct work). |
| **Accountability** | P5 Epistemic | Is generation traceable through layers? Measured as logit lens coherence — do intermediate layer predictions converge toward the final token, or jump unpredictably? |
| **Reflexivity** | P6 Meta | Same as Phase 2: after a coherence dip, does the next intervention differ, and does it produce recovery? Measured from episodic log. |

**Critical design note:** No external quality judgment is used. Φ reads only observable structural properties of the inference process itself. "Quality" of the output is not an input to the coherence function.

### Action Vocabulary

| Action | Type | Mechanism |
|---|---|---|
| `adjust_temperature_down` | Tilt | Reduce sampling temperature → sharpen distribution |
| `adjust_temperature_up` | Tilt | Increase sampling temperature → flatten distribution |
| `inject_prefix` | Tilt | Prepend a short structuring prefix to the next generation step |
| `scale_attention` | Tilt | Boost attention weights on specific token positions (via hook) |
| `observe` | Reflex | No-op; read state without intervening |
| `rest` | Reflex | Skip a cycle; allow context to accumulate |

All actions are **tilt coupling**: they shift which states the fast layer prefers without restructuring its scoring function. This respects the parametric wall.

---

## Milestones

### M0 — Observational Experiment (First step, no REAL loop yet)

**Goal:** Confirm the core prediction before building the full architecture.

**What it is:** Run a small open-weight model on two prompt classes:
1. *Non-competing* prompts: single clear objective ("Summarize this paragraph")
2. *Competing* prompts: simultaneous contradictory objectives ("Explain both why X is good and why X is fundamentally flawed, resolving the tension in your answer")

**What to measure:** Per-token logit entropy at each layer (Entropy-Lens-style), hidden state trajectory variance, attention pattern distribution.

**Prediction:** Competing prompts will show measurably higher and more volatile entropy in logit distributions, consistent with TCL's prediction of oscillation under competing constraints without a slow-layer regulator.

**Success criterion:** Statistically distinguishable entropy profiles between prompt classes. If this doesn't hold, reassess the theoretical basis before building the full loop.

**Tools:** TransformerLens, Google Colab (free tier), model: TinyLlama 1.1B or Qwen 3 0.6B
**Deliverable:** `notebooks/01_entropy_observation.ipynb`

---

### M1 — Observation Adapter

Build the `real_inference/` domain adapter:
- `hooks.py`: TransformerLens hook registration, activation collection, statistic computation
- `adapter.py`: `ObservationAdapter` and `ActionBackend` implementing Phase 4 interfaces
- `coherence.py`: `CoherenceModel` mapping activation statistics → six-dimensional scores

**Acceptance criterion:** Can run `RealCoreEngine(observer, actions, coherence).run_session(cycles=20)` against a loaded model without engine changes.

---

### M2 — Minimal REAL Loop

Connect the adapter to the Phase 4 engine. Run one session:
- Model generates tokens in response to a competing-pressure prompt
- REAL observes entropy/activation state between generation steps
- REAL selects an intervention (initially likely `observe` or `adjust_temperature`)
- Engine records cycle entry, accumulates episodic log
- Session summary produced

**Deliverable:** `notebooks/02_real_loop_minimal.ipynb`
**Success criterion:** Session runs without errors; GCO status varies (not stuck at DEGRADED every cycle, which would indicate a calibration problem like the `repo_health` domain issues in Phase 4)

---

### M3 — Coherence Calibration

The coherence function will need calibration against observed baseline behavior. Following the Phase 2 pattern: run multiple sessions on non-competing prompts to establish baseline dimension scores, then on competing prompts to confirm the predicted delta.

This is also where the founding biases (weight profiles) get set for the inference domain. Expected initial profile: **vitality and accountability** weighted higher in early sessions (same rationale as Phase 2's `early_cycles` profile).

---

### M4 — Intervention Efficacy

Do the tilt actions actually change generation behavior in ways that improve coherence? This requires:
- Running REAL in active intervention mode (not just `observe`)
- Comparing coherence trajectories across sessions with and without active interventions
- Verifying reflexivity: does the agent switch interventions after coherence dips and recover?

**Success criterion:** Same behavioral arc as Phase 2 — early sessions volatile, later sessions more stable; reflexivity rises from baseline.

---

### M5 — The GCO Closing Test

The document's proposed final experiment: "If a REAL-modulated model can then generate improved versions of REAL's own coherence function, that's the GCO closing on its own construction."

Concretely: run REAL modulation during a session where the model is asked to reason about the REAL coherence function. Measure whether modulation-on vs. modulation-off produces a measurable difference in the quality of the model's output about its own evaluation architecture.

This is speculative at M5 — it depends on what's learned in M0–M4. Include it as a goal to aim toward, not a deliverable to plan against.

---

## Open Design Questions

1. **Timescale of REAL cycles.** In Phase 2, one cycle = one agent action over ~1 second of real time. In Phase 5, one cycle might map to: one token? one sentence? one full generation? The right granularity depends on what "step" gives enough state variation to be informative. This is the most important architectural question to resolve early.

2. **Attention topology metric.** "Contextual fit" requires measuring attention alignment with input structure. What's the right metric? Options: attention entropy per head, KL divergence between attention distributions across layers, or a simpler proxy like top-k token concentration in attention weights.

3. **Parametric wall in practice.** Temperature adjustment changes the *shape* of the sampling distribution, which could be classified as reshape coupling rather than tilt coupling. Need to carefully bound how much temperature can shift per cycle (analogous to δ_max in Phase 2) to stay within the parametric wall constraint.

4. **Model selection.** TinyLlama 1.1B runs full precision on Colab free tier; Qwen 3 0.6B is even smaller for fast iteration. Llama 3.1 8B (4-bit) is more representative but slower. Start with the smallest that shows the predicted entropy pattern in M0.

---

## Prior Work to Cite / Differentiate From

| Work | What it does | How Phase 5 differs |
|---|---|---|
| Entropy-Lens (arXiv 2024–2025) | Measures layer-wise logit entropy to interpret model behavior | Phase 5 uses entropy as *live state input* to a regulatory loop, not post-hoc interpretation |
| Logit Lens | Projects residual stream to vocabulary at each layer | Phase 5 uses this as one input to Accountability (P5) scoring |
| Representation Engineering (Anthropic) | Steers activations toward externally-defined target directions | Phase 5 uses REAL (no external target) to determine *when* and *how much* to tilt |
| RLHF / reward modeling | External slow layer via human preference labels | Phase 5 is endogenous — no external evaluator |
