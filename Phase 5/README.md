# Phase 5 — REAL as Endogenous Slow Layer for LLM Inference

## What This Phase Is

Phase 5 applies REAL not as an external monitor of an LLM agent, but as an **endogenous slow layer operating inside the inference process itself**.

Phases 1–3 demonstrated the algorithm on real hardware (CPU/memory/thermal signals as state space).
Phase 4 generalized the algorithm into a domain-agnostic core and built three substrate adapters.
Phase 5 asks: **can REAL function as the regulatory substrate that language models structurally lack?**

## The Core Research Question

Language models during inference bear real metabolic cost — computational work, attention overhead, the resolution of competing optimization pressures into a single token stream. This cost contains information about difficulty, uncertainty, and internal tension. After inference, it is lost. What survives is the output text: a flat symbolic artifact stripped of the thermodynamic trace of its own production.

The hypothesis: **inference friction has a measurable signature in the logit and activation topology, and a coherence-maintenance algorithm (REAL) can identify and respond to that signature without requiring an external reward signal.**

## Relationship to Prior Phases

| Phase | Substrate | REAL's role |
|---|---|---|
| 1–3 | Real hardware (psutil) | Observer + actor in a real physical environment |
| 4 | Hardware / repo / LLM API surface | Observer + actor in generalized substrates |
| **5** | **LLM hidden states during inference** | **Endogenous slow-layer regulatory substrate** |

The Phase 4 `real_core/` engine is reused unchanged. Phase 5 adds a new domain adapter that hooks into a transformer's internal activations.

## Why This Is a Phase Change and Not Phase 4 Extended

Phase 4 generalized *where* REAL runs. Phase 5 changes *what it's embedded in*. In Phases 1–4, REAL observes something external to itself. In Phase 5, the substrate is the generative mechanism. The agent being evaluated and the evaluation architecture become the same system. This satisfies the TCL requirement for a genuine speed differential: the slow layer (REAL, operating across generation steps) modulates the fast layer (token-by-token attention) without operating at the same timescale.

## TCL Framing

A transformer during inference is all fast layer. Attention mechanisms operate at the same timescale as output generation; there is no slow regulatory substrate. Without a genuine speed differential, the system either locks into a single attractor (mode collapse, repetition) or oscillates too fast to consolidate (incoherent reasoning chains, hallucination).

REAL provides the missing slow layer:
- **Fast layer**: token-by-token inference (milliseconds)
- **Slow layer**: REAL coherence evaluation across generation steps (seconds to minutes)
- **Coupling mechanism**: tilt actions (temperature modulation, prompt prefix injection) that push the fast layer toward coherent operating states without dictating content

## Relationship to Existing Literature

The closest existing work is **Entropy-Lens** (arXiv 2024–2025), which uses Shannon entropy of layer-wise decoded logits to create interpretable entropy profiles per token. Key findings from that work:
- Entropy profiles are predictive of prompt type and task format
- They correlate with output correctness
- They reveal family-specific expansion/pruning strategies across layers

Phase 5 is **not** doing interpretability analysis. The distinction:
- Entropy-Lens: *observe and describe* entropy topology
- Phase 5: *observe, evaluate endogenously, and tilt* based on coherence state

The novel contribution is the regulatory loop, not the measurement.

## Folder Structure (Planned)

```
Phase 5/
├── README.md                    (this file)
├── plan.md                      (architecture + milestones)
├── notebooks/
│   └── 01_entropy_observation.ipynb    (M0: observational experiment)
├── real_inference/              (domain adapter for transformer internals)
│   ├── adapter.py               (ObservationAdapter + ActionBackend)
│   ├── coherence.py             (CoherenceModel mapping activations → P1–P6)
│   └── hooks.py                 (TransformerLens hook management)
└── experiments/
    └── phase5_baseline.toml     (experiment config)
```

The Phase 4 `real_core/` engine is imported directly; no modifications needed.
