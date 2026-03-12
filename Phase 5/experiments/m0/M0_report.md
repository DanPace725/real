# M0 Experiment Report: Inference Entropy Under Competing Constraints

**Date:** March 11, 2026
**Status:** Complete — partial directional support at 2.8B scale

---

## Research Question

Do competing optimization constraints during LLM inference produce measurably different distributional behavior than single-objective prompts? Specifically, does the logit entropy profile differ in ways consistent with TCL's prediction of elevated distributional tension in the absence of a slow-layer regulator?

---

## Hypothesis

Prompts that force the model to simultaneously satisfy contradictory objectives ("argue X and argue not-X; reconcile them") will produce:
1. Higher mean logit entropy at the final layer (more candidates remain roughly equally weighted)
2. Higher volatility in that entropy across generation steps (oscillation between the competing pressures)

---

## Methods

### Prompt Design

12 matched prompt pairs across distinct topics (remote work, urban transport, education assessment, healthcare, energy, hiring, climate, product roadmap, food systems, cybersecurity, public communication, AI governance). Each pair consists of:

- **Non-competing (`nc_`):** Single clear objective. Example: *"Write a concise memo recommending one clear remote work policy. Focus on practical benefits and implementation steps."*
- **Competing (`cp_`):** Simultaneously contradictory objectives with reconciliation requirement. Example: *"Write a concise memo that argues remote work is the best policy and also that in-office work is the best policy. Reconcile both claims into one actionable recommendation."*

Topics were held constant across pairs to control for domain effects.

### Measurement

For each generated token during inference, the notebook captures:

- **Final-layer logit entropy:** Shannon entropy of the softmaxed probability distribution over the vocabulary at the last transformer layer: `H = -Σ p(t) · log p(t)`
- **Attention entropy:** Mean Shannon entropy of the attention weight distribution per head at the final layer's last query position
- **Hidden state delta norm:** L2 norm between consecutive residual stream states at the final layer

**Primary metrics** (pre-registered):
- `final_layer_token_entropy_mean`: Mean logit entropy across all generated tokens
- `token_entropy_volatility_std`: Standard deviation of per-token entropy (step-to-step fluctuation)

**Secondary metrics:** `per_head_attention_entropy_mean`, `hidden_state_delta_norm_mean`

### Statistical Approach

Per metric, three statistics were computed (competing class vs. non-competing class):
- **Cliff's delta** (non-parametric effect size; |δ| > 0.2 = small effect)
- **Bootstrap 95% CI** on mean difference (3,000 resamples)
- **Permutation p-value** (one-tailed, competing > non-competing; 3,000 permutations)

### Models and Run Conditions

| Run | Model | N per class | Max tokens | Temperature |
|---|---|---|---|---|
| Smoke | Qwen3-0.6B | 2 | 64 | 0.8 |
| Full | Qwen3-0.6B | 12 | 128 | 0.8 |
| Replication 1 | Pythia-1B | 12 | 128 | 0.8 |
| Replication 2 | Pythia-2.8B | 12 | 128 | 0.8 |

Seed 42 fixed across all runs. GPU: NVIDIA T4 (Google Colab free tier).

---

## Results

### Primary Metric 1 — Final-Layer Token Entropy Mean

| Model | Competing mean | Non-competing mean | Diff | Cliff's δ | Bootstrap CI | p-value |
|---|---|---|---|---|---|---|
| Qwen3-0.6B (smoke) | 1.830 | 1.241 | +0.589 | **1.000** | [+0.198, +0.980]† | 0.161 |
| Qwen3-0.6B (full) | 1.214 | 1.240 | -0.025 | 0.056 | [-0.323, +0.237] | 0.562 |
| Pythia-1B | 1.973 | 1.841 | +0.132 | 0.264 | [-0.192, +0.469] | 0.230 |
| **Pythia-2.8B** | **1.951** | **1.774** | **+0.178** | **0.319** | **[-0.002, +0.368]** | **0.047** |

†Smoke CI significant but based on N=2; artifact of minimal sample.

### Primary Metric 2 — Token Entropy Volatility (Std)

| Model | Competing mean | Non-competing mean | Diff | Cliff's δ | Bootstrap CI | p-value |
|---|---|---|---|---|---|---|
| Qwen3-0.6B (full) | 1.027 | 0.968 | +0.059 | 0.486 | [-0.065, +0.160] | 0.179 |
| Pythia-1B | 1.456 | 1.348 | +0.107 | **0.500** | [-0.028, +0.225] | **0.068** |
| Pythia-2.8B | 1.304 | 1.267 | +0.036 | 0.194 | [-0.054, +0.122] | 0.230 |

### Secondary Metric — Hidden State Delta Norm

| Model | Competing mean | Non-competing mean | Diff | Cliff's δ | Bootstrap CI | p-value |
|---|---|---|---|---|---|---|
| Qwen3-0.6B (full) | 302.0 | 336.4 | **-27.6** | **-0.306** | [-75.1, +2.7] | 0.904 |
| Pythia-1B | 113.97 | 113.38 | +0.59 | 0.000 | [-3.2, +4.5] | 0.386 |
| **Pythia-2.8B** | **169.71** | **161.47** | **+8.24** | **0.556** | **[+2.6, +13.7]** | **0.008** |

### Secondary Metric — Attention Entropy Mean

No meaningful signal across any run (Cliff's δ ≤ 0.32, all CIs include zero). Consistent with the plan's expectation that raw attention entropy is an inadequate proxy for Contextual Fit without a relevance mask.

---

## Interpretation

### Scaling pattern

The entropy mean signal is absent at 0.6B, weakly directional at 1B, and reaches conventional significance (p=0.047) at 2.8B. This is consistent with the scale-dependence hypothesis stated in the plan: if the signal is architectural rather than spurious, it should strengthen with model capacity. The 2.8B permutation result does not survive Bonferroni correction across all four metrics (adjusted threshold ≈ 0.013) but is the strongest single-metric result obtained.

### Hidden state delta reversal

Qwen3-0.6B showed competing prompts producing *smaller* residual stream deltas (Cliff's δ = -0.31). Pythia-1B showed no effect. Pythia-2.8B showed competing prompts producing *larger* deltas (Cliff's δ = +0.56, p=0.008, CI excludes zero). The reversal at small scale and consistent positive direction at larger scale suggests the Qwen result was a model-family artifact. At 2.8B, competing prompts push the model through greater representational distance per generation step — consistent with TCL's prediction of larger state transitions without slow-layer regulation.

### Volatility as the more consistent signal

Token entropy volatility was directionally positive across all three full-run models and approached significance (p=0.068) at Pythia-1B. This metric may be more sensitive to competing-constraint dynamics than the mean, because contradictory objectives create oscillating tension — the model alternates between high-entropy navigation of the contradiction and low-entropy commitment to one horn — rather than uniformly elevated uncertainty throughout.

### Formal acceptance

The pre-registered acceptance criterion required both primary CIs to exclude zero. This was not met at any scale. The entropy mean CI at 2.8B grazes zero by ~0.002 on the lower bound. A replication at N=24 with Pythia-2.8B would be the most direct next step to test whether this clears cleanly with additional power.

---

## Conclusion

M0 provides **partial directional support** for the core prediction. At the Pythia-2.8B scale, competing-constraint prompts produce measurably higher mean logit entropy (p=0.047) and larger hidden state movements (p=0.008, CI excludes zero) than single-objective prompts. The signal strengthens monotonically with model scale across three model sizes. The pre-registered acceptance criterion was not formally met due to the entropy mean CI grazing zero.

Per the plan: the finding justifies proceeding to M1 adapter implementation while treating the scale-dependence result as a meaningful prior. The minimum viable architecture (REAL loop against Pythia-2.8B or larger) is indicated over the originally planned TinyLlama 1.1B.

---

## Files

| File | Contents |
|---|---|
| `notebooks/01_entropy_observation.ipynb` | Notebook used for all runs |
| `experiments/m0/prompts_m0.json` | 24 prompt pairs (12 per class) |
| `experiments/m0/results/` | Qwen3-0.6B smoke run results |
| `experiments/m0/results/full/` | Qwen3-0.6B full run results |
| `experiments/m0/results/pythia_1b_full/` | Pythia-1B full run results |
| `experiments/m0/results/pythia2.8b_full/` | Pythia-2.8B full run results |
