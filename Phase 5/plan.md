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
| **Epistemic asymmetry** | REAL observes *computed statistics over* hidden states — entropy, variance, attention mass fractions — not the full activation tensors. This lossiness is a feature: REAL cannot game its own coherence function by directly manipulating the values it reads (the degeneration mode for Condition 1 in the formal specification §2). Epistemic asymmetry is actually stronger here than in Phase 2, where psutil gave fairly complete system state. |
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

**Critical design note (hard constraint, not preference):** No external quality judgment is used. Φ reads only observable structural properties of the inference process itself. "Quality" of the output is not an input to the coherence function. The moment external quality judgment enters Φ, REAL degenerates into a variant of RLHF with extra steps. This is the Phase 5 equivalent of Phase 2's "no RLHF" design decision and carries the same weight.

### Action Vocabulary

| Action | Type | Mechanism |
|---|---|---|
| `adjust_temperature_down` | Tilt | Reduce sampling temperature → sharpen distribution |
| `adjust_temperature_up` | Tilt | Increase sampling temperature → flatten distribution |
| `inject_prefix` | Tilt | Prepend a short structuring prefix to the next generation step |
| `scale_attention` | Tilt | Boost attention weights on specific token positions (via hook) |
| `observe` | Reflex | No-op; read state without intervening |
| `rest` | Reflex | Skip a cycle; allow context to accumulate |

All actions are **tilt coupling**: they shift which states the fast layer prefers without restructuring its scoring function. This respects the parametric wall (σ_p < 0.289). Temperature adjustment is tilt-like within bounded ranges but becomes effectively reshape at extremes — see Design Decisions §3 below.

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

**Tools:** TransformerLens, Google Colab (free tier), model: **Qwen 3 0.6B** (fast iteration; if the entropy signal is architectural it should appear at this scale)
**Deliverable:** `notebooks/01_entropy_observation.ipynb`

**Note on scale-dependence:** If the entropy signal does not appear at 0.6B, that is an important finding — it suggests the phenomenon is scale-dependent rather than architectural, which narrows the theoretical claims and is itself a result worth reporting.

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
**Success criterion:** Session runs without errors; GCO status varies across cycles. The project succeeds at M2 if the REAL loop runs against inference internals and produces variable GCO states. Everything after M2 is elaboration on a proof that the basic mechanism works.

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

Concretely: run REAL modulation during a session where the model is asked to reason about the REAL coherence function. Measure whether modulation-on vs. modulation-off produces a measurable difference in the model's output about its own evaluation architecture.

M5 is a **horizon marker**, not a deliverable. Its function is to orient the developmental arc. If M0–M4 produce predicted results, M5 becomes a natural next step. If they don't, M5 transforms into "what did we learn about why the GCO can't close here?" Either outcome has value. Do not treat M5 as a success criterion for the project as a whole.

---

## Design Decisions

### 1. Timescale of REAL Cycles

**Decision: One REAL cycle per generation segment (~15–40 tokens, approximately one clause or sentence).**

The TCL research establishes that adaptive cycling requires a genuine speed differential between slow and fast layers. Three natural timescales exist:

- **Token level (~1 per forward pass):** Entropy bounces based on local syntax and vocabulary effects — too noisy for coherence evaluation.
- **Segment level (~15–40 tokens):** Semantic decisions happen here. The model commits to a reasoning line, shifts frames, or navigates tension between competing objectives. Competing-pressure entropy signatures should be most legible at this scale.
- **Full generation level:** The trajectory has already collapsed into a finished output — too late to intervene.

REAL's observation function accumulates activation statistics over a sliding window of N tokens (starting value: **N=20**). At window end, statistics are passed to the coherence function; the selected intervention applies to the next window. Note: TCL proved that moderate delay between observation and intervention is *constructive*, lowering the coupling threshold by ~14%. Do not over-engineer to minimize latency.

### 2. Attention Topology Metric for Contextual Fit

**Decision: Structural Attention Alignment (SAA), with attention entropy per head as a simpler proxy for M0.**

Contextual Fit (P3) is not about whether attention is focused or diffuse in general — it is about whether attention topology *matches* task demands. SAA measures the fraction of attention mass on structurally relevant tokens (prompt instruction tokens + recent context tokens + committed reference tokens), averaged across heads. High SAA with low cross-head variance = high contextual fit.

**Phased implementation:**
- **M0:** Attention entropy per head (fast to compute, sufficient for detecting whether competing prompts show different patterns)
- **M1–M2:** SAA with positional relevance heuristic (prompt tokens + last-N-generated count as relevant)
- **M3+:** Refine relevance mask from observed high-coherence patterns

### 3. Parametric Wall and Temperature as Tilt vs. Reshape

**Decision: Temperature is tilt-like within bounds; bound delta to ±0.1 per cycle, absolute range [0.4, 1.2].**

Temperature does not change the logits — it changes how sharply the model's opinion is expressed during sampling. This is tilt (traversal dynamics), not reshape (landscape geometry). However, extreme values become reshape in effect: temperature near 0 collapses to top-1, temperature > 2.0 flattens to near-uniform. Both eliminate effectively reachable states.

| Parameter | Value | Rationale |
|---|---|---|
| Δ per cycle | ±0.1 | Analogous to δ_max = 0.01 for weight tuning in Phase 2, scaled to temperature's effective range |
| Absolute minimum | 0.4 | Below this, fewer than ~3 tokens carry meaningful probability mass |
| Absolute maximum | 1.2 | Above this, sampling becomes noise |
| Cooldown | 3 cycles | Prevent oscillation between temperature extremes |

Other action classifications: `inject_prefix` and `scale_attention` are clearly tilt. `observe` and `rest` are no coupling — mandatory breathing cycles under metabolic cost (TCL requirement).

### 4. Model Selection

**Decision: Qwen 3 0.6B for M0; TinyLlama 1.1B for M1–M4; scale to Llama 3.1 8B only if results warrant it.**

- **M0 — Qwen 3 0.6B:** Fast iteration for the observational experiment. If the entropy signal is architectural (as predicted by TCL), it should appear even at this scale.
- **M1–M4 — TinyLlama 1.1B:** 22 layers provide enough depth for logit lens convergence patterns (Accountability/P5); 32 heads provide enough specialization for Differentiation/P4; full precision on T4 avoids quantization artifacts in activation statistics.
- If the signal does not appear at 0.6B or 1.1B, that is informative: it suggests the phenomenon is scale-dependent, narrowing the theoretical claim toward identifying what scale threshold is required.

---

## Prior Work to Cite / Differentiate From

| Work | What it does | How Phase 5 differs |
|---|---|---|
| Entropy-Lens (arXiv 2024–2025) | Measures layer-wise logit entropy to interpret model behavior | Phase 5 uses entropy as *live state input* to a regulatory loop, not post-hoc interpretation |
| Logit Lens | Projects residual stream to vocabulary at each layer | Phase 5 uses this as one input to Accountability (P5) scoring |
| Activation Steering / RepE | Steers activations toward externally-defined target vectors | Phase 5 uses endogenous coherence evaluation (no external target); interventions are selected by CFAR dynamics, not by a predetermined direction — this is the closest existing work to Phase 5 and the key distinction is the entire theoretical contribution |
| Representation Engineering (Anthropic) | Steers activations toward externally-defined target directions | Phase 5 uses REAL (no external target) to determine *when* and *how much* to tilt |
| RLHF / reward modeling | External slow layer via human preference labels | Phase 5 is endogenous — no external evaluator |
