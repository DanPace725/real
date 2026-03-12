# Phase 5 Design Question Responses

**Date:** March 11, 2026
**Context:** These responses address the open design questions in the Phase 5 Architecture Plan, grounded in the TCL (Temporal Constraint Lamination) research, the E² relational ontology framework, and prior REAL implementation experience across Phases 2-4. They are intended to be read alongside the Phase 5 plan and used to guide implementation decisions.

---

## Question 1: Timescale of REAL Cycles

**Question from plan:** In Phase 2, one cycle = one agent action over ~1 second of real time. In Phase 5, one cycle might map to: one token? one sentence? one full generation?

**Answer: One REAL cycle per generation segment (roughly 15-40 tokens, approximately one sentence or coherent clause).**

### Rationale from TCL

The TCL research establishes that adaptive cycling requires a genuine speed differential between the slow layer and the fast layer. The slow layer's influence must integrate over multiple fast-layer transitions. If REAL cycles at the same rate as token generation (one cycle per token), there is no speed differential. REAL becomes another fast-layer process, not a regulatory substrate. It cannot regulate what it cannot observe from a different timescale.

The three natural timescales in this domain are:

1. **Token level (~1 per forward pass):** State variation at this level is dominated by local syntax and vocabulary effects. The entropy bounces between high (content word selection, branching decisions) and low (function words, deterministic completions) based on linguistic structure rather than semantic tension. Too noisy for coherence evaluation.

2. **Segment level (~15-40 tokens, one clause or sentence):** This is where semantic decisions happen. The model commits to a line of reasoning, shifts between conceptual frames, or navigates the tension between competing objectives. The competing-pressure entropy signatures identified in the conversation synthesis should be most legible at this scale, because this is where contradictory optimization targets create sustained distributional tension rather than token-by-token noise.

3. **Full generation level (hundreds of tokens):** By this point, the generation is complete. The trajectory information has already collapsed into a finished output. REAL can't modulate what's already happened.

The segment level provides the right speed differential. REAL operates at roughly 1/20th the speed of token generation (if segment length averages ~20 tokens). This is analogous to the slow-layer/fast-layer ratio in the TCL mathematical model, where the slow layer operates at a fraction of the fast layer's speed but is coupled strongly enough to influence state transitions.

### Practical Implementation

- REAL's observation function accumulates activation statistics (entropy, attention distributions, hidden state variance) over a sliding window of N tokens.
- At the end of each window, the accumulated statistics are passed to the coherence function.
- REAL scores coherence, selects an intervention, and that intervention applies to the next generation window.
- Window size N is a tunable parameter. Start with N=20. If M0 shows that entropy patterns need more tokens to stabilize, increase. If they're legible at shorter windows, decrease.

### Note on Delay

TCL proved that moderate delay is *constructive* for tilt-coupled systems, lowering the coupling threshold by approximately 14%. The mechanism: when the fast layer has settled into a state, the delayed signal from the slow layer's observation of the *previous* state provides a well-timed push that assists the next transition. In Phase 5 terms: if there is a lag of a few tokens between REAL observing state and the intervention taking effect, this is not a problem. It may actively help. Do not over-engineer to minimize latency.

---

## Question 2: Attention Topology Metric for Contextual Fit

**Question from plan:** "Contextual fit" requires measuring attention alignment with input structure. What's the right metric?

**Answer: Use a composite metric measuring the fraction of attention mass on structurally relevant tokens, not just attention regularity in isolation. For M0, attention entropy per head is an acceptable starting proxy.**

### Rationale from E² Framework

Contextual Fit maps to P3 (Geometric/Causal): the system's relationship to its environment is appropriate to the environment's actual structure. This is not about whether attention is focused or diffuse in general. It is about whether the attention topology *matches* the task demands.

Consider the failure modes:

- Diffuse attention on a simple, focused prompt = low contextual fit (the model is not engaging the structure of the input)
- Focused attention on contextually irrelevant tokens = low contextual fit (engagement is present but misaligned)
- Focused attention on structurally relevant tokens = high contextual fit (the model's processing topology matches the input topology)

Attention entropy per head captures the first failure mode but not the second. KL divergence across layers captures consistency of attention through the model's depth but not contextual relevance. Top-k concentration captures sharpness but not alignment.

### Recommended Metric

**Structural Attention Alignment (SAA):** For each attention head in the final few layers, compute the fraction of attention mass falling on tokens that are structurally relevant to the current generation position. "Structurally relevant" tokens include:

- Prompt instruction tokens (the task specification)
- Recent context tokens (the last N tokens of generated output, where N ~ segment length)
- Key reference tokens (tokens the model has already committed to that constrain the current generation, such as names, numbers, or logical connectors)

SAA = mean across heads of (attention mass on relevant tokens / total attention mass).

High SAA with low variance across heads = high contextual fit. Low SAA or high variance = low contextual fit.

### Phased Implementation

- **M0 (observational):** Use attention entropy per head as a simple proxy. It's fast to compute and will show whether competing-pressure prompts produce different attention patterns at all.
- **M1-M2 (minimal loop):** Implement SAA with a simple relevance heuristic (prompt tokens + last-N-generated tokens count as relevant). This doesn't require semantic parsing, just positional tracking.
- **M3+ (calibration):** Refine the relevance heuristic based on observed patterns. If the model consistently attends to specific structural positions during high-coherence segments, those positions can be incorporated into the relevance mask.

---

## Question 3: Parametric Wall and Temperature as Tilt vs. Reshape

**Question from plan:** Temperature adjustment changes the shape of the sampling distribution, which could be classified as reshape coupling rather than tilt coupling. Need to carefully bound how much temperature can shift per cycle.

**Answer: Temperature adjustment is tilt-like within bounded ranges but becomes effectively reshape at extremes. Bound temperature delta to +/-0.1 per REAL cycle, with absolute bounds of [0.4, 1.2].**

### The TCL Distinction

- **Tilt coupling:** The slow layer pushes the fast layer toward a particular state without changing where the attractor basins are. Tilt is robust to delay, noise, and bandwidth limitations. It is durable but not maximally adaptive.
- **Reshape coupling:** The slow layer changes the geometry of the fast layer's available options, altering what states are even reachable. Reshape is highly adaptive but fragile: sensitive to delays and bandwidth limitations. The parametric wall (sigma_p < 0.289) is the hard ceiling on reshape coupling.

### Temperature Analysis

Temperature does not change the logits (the model's "opinion" about what comes next). It changes how sharply that opinion gets expressed during sampling. This is closer to tilt than reshape because the landscape (logit distribution) remains unchanged; only the traversal dynamics change (how the system navigates between options).

However, extreme temperature shifts function as reshape in effect:

- Temperature near 0: Collapses the distribution to top-1. All paths except one are eliminated. This is landscape reshaping regardless of mechanism.
- Temperature very high (>2.0): Flattens the distribution to near-uniform. All paths become equally likely. The landscape's peaks and valleys become irrelevant.

Both extremes change what states are *effectively reachable*, which is the definition of reshape coupling.

### Recommended Bounds

Following the TCL parametric wall constraint (sigma_p < 0.289), temperature interventions should be bounded to stay firmly in tilt territory:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Delta per cycle | +/-0.1 | Analogous to delta_max = 0.01 for weight tuning in Phase 2, scaled to temperature's effective range |
| Absolute minimum | 0.4 | Below this, the distribution is effectively collapsed; fewer than ~3 tokens carry meaningful probability mass |
| Absolute maximum | 1.2 | Above this, the distribution is too flat for coherent generation; sampling becomes noise |
| Cooldown | 3 cycles | Prevent oscillation between temperature extremes (same rationale as retune cooldown in Phase 4c) |

### Classification of Other Actions

- **inject_prefix:** Clearly tilt. Biases what the model attends to without changing the model's computations. Analogous to tilting a table so the ball rolls toward a particular valley.
- **scale_attention:** Clearly tilt. Boosts attention weights at specific positions, encouraging the model to weight certain context more heavily. Does not alter the attention mechanism itself.
- **observe / rest:** No coupling. These are the agent's equivalent of the breathing/recovery cycles that TCL proved are mandatory under metabolic cost.

---

## Question 4: Model Selection

**Question from plan:** TinyLlama 1.1B runs full precision on Colab free tier; Qwen 3 0.6B is even smaller for fast iteration. Llama 3.1 8B (4-bit) is more representative but slower.

**Answer: Qwen 3 0.6B for M0, TinyLlama 1.1B for M1-M4. Scale to Llama 3.1 8B only if results warrant it and compute budget allows.**

### M0: Qwen 3 0.6B

M0 is purely observational: testing whether competing-pressure prompts produce distinguishable entropy profiles. The priority is fast iteration so you can run many prompts and build statistical confidence. 0.6B runs fast enough on a T4 to iterate rapidly. If the entropy signal is architectural (as predicted), it should appear even at this scale.

### M1-M4: TinyLlama 1.1B

The REAL loop requires a model with enough internal structure for the coherence dimensions to have real variance:

- 22 layers: Enough depth for logit lens to show meaningful convergence patterns (Accountability/P5)
- 32 attention heads: Enough heads for attention specialization to be measurable (Differentiation/P4)
- 1.1B parameters at full precision on T4: No quantization artifacts affecting activation statistics

This is the sweet spot between structural complexity and iteration speed within Colab session limits (90 minutes idle, 12 hours active).

### Scale-Dependence as a Finding

If the entropy signal does not appear at 0.6B or 1.1B, that is an important result. It would indicate the phenomenon is scale-dependent rather than architectural, which narrows the theoretical claims and redirects the research toward understanding what scale threshold is required. The TCL framework predicts the signal should be present at any scale where the attention mechanism handles competing objectives, but empirical falsification at small scale would be genuinely informative.

If the signal *does* appear at small scale but REAL's interventions fail to modulate it, that's a different finding: the regulatory mechanism may require more coupling strength than small models provide, analogous to a slow layer that's too weakly coupled to push the fast layer over its transition barriers (below the viability floor).

---

## Additional Recommendations

### On M5 (GCO Closing Test)

The plan correctly marks M5 as speculative. Strengthen this framing: M5 is a **horizon marker**, not a deliverable. Its function is to orient the developmental arc. If M0-M4 produce predicted results, M5 becomes a natural next step. If they don't, M5 transforms into "what did we learn about why the GCO can't close here?" Either outcome has value.

The risk is treating M5 as a success criterion for the project as a whole. The project succeeds at M2 if the REAL loop runs against inference internals and produces variable GCO states. Everything after M2 is elaboration on a proof that the basic mechanism works.

### On the Prior Work Differentiation Table

The table in the plan is good. Add one row:

| Work | What it does | How Phase 5 differs |
|------|-------------|---------------------|
| Activation Steering / RepE | Steers activations toward externally-defined target vectors | Phase 5 uses endogenous coherence evaluation (no external target); interventions are selected by CFAR dynamics, not by a predetermined direction |

This distinction is important because activation steering is the closest existing work to what Phase 5 proposes, and the key difference (endogenous vs. exogenous evaluation) is the entire theoretical contribution.

### On the Coherence Function's No-External-Quality Constraint

The plan's critical design note ("No external quality judgment is used. Phi reads only observable structural properties of the inference process itself") is exactly right and should be treated as a hard constraint, not a preference. The moment external quality judgment enters the coherence function, REAL degenerates into a variant of RLHF with extra steps. The entire theoretical claim depends on endogenous evaluation. This is the equivalent of Phase 2's "no RLHF" design decision and should carry the same weight.

### On Embedding Condition Verification

The plan's verification is correct but worth expanding on one point. **Epistemic asymmetry** in Phase 5 is actually stronger than in Phase 2. In Phase 2, the agent could read system state fairly completely via psutil. In Phase 5, REAL observes *computed statistics over* hidden states, not the full hidden state vectors themselves. The observation function is lossy by design: it computes entropy, variance, and attention mass fractions from activation tensors that may have thousands of dimensions per token per layer. This lossiness is a feature, not a limitation. It ensures that REAL cannot "game" its own coherence function by directly manipulating the values it reads, which was identified as the degeneration mode for Condition 1 in the formal specification (Section 2).

---

*These responses are derived from the TCL mathematical research (three constants, tilt/reshape distinction, metabolic cost findings), the E² relational primitive definitions (P1-P6), and implementation experience from REAL Phases 2-4. They should be read as design guidance, not implementation specifications. The coding agent should treat the specific numbers (window size 20, temperature bounds 0.4-1.2, etc.) as starting points subject to empirical calibration in M0 and M1.*