# Phase 8 Latent-Context Follow-up Trace (Context-Bit Removal Focus)

## Date

2026-03-16

## Timestamp

2026-03-16T23:02:58+00:00

## Model

GPT-5.2-Codex

## Prompt

Review recent traces and implementation changes, then provide a new evaluation focused on following up the prior recommendation to remove the explicit context bit, including the discovered difficulty and practical ways to move forward.

## Inputs Reviewed

- `Phase 8/AGENTS.md`
- `Phase 8/vision.md`
- `Phase 8/first_computational_experiment_spec.md`
- `Phase 8/README.md`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/scenarios.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/docs/trails/20260316_phase8_cvt1_spec_trace.md`
- `Phase 8/docs/trails/20260316_phase8_cvt1_task_tuning_trace.md`
- `Phase 8/docs/trails/20260316_phase8_cvt1_context_credit_trace.md`
- `Phase 8/docs/trails/20260316_phase8_carryover_maintenance_trace.md`
- `Phase 8/docs/trails/20260316_phase8_task_b_transfer_retuning_trace.md`
- `Phase 8/docs/trails_gpt52/20260316_phase8_code_alignment_trace.md`
- `Phase 8/docs/trails_gpt52/20260316_phase8_progress_review_and_next_steps_trace.md`

---

## Executive Take

The project has made meaningful progress on Stage 1 (explicit context): local transform learning, context-conditioned supports, and transfer retuning now produce non-trivial behavior.

But the exact place where difficulty appears is also clear:

- many of the strongest learning signals are currently coupled to `context_bit` visibility,
- and the same mechanisms that improve Stage 1 can become unstable or blind when that explicit context channel is removed.

This does **not** mean Stage 2 is failing in principle. It means Stage 2 is a different problem class: from context-conditioned control to local sequence inference under energy constraints.

---

## What Changed That Matters for This Question

Recent updates concentrated on improving context-sensitive behavior under explicit context:

- context-shaped action support and maintenance,
- context-specific returned credit handling,
- selector pressure that can prefer context-matched transform evidence,
- transfer retuning to weaken stale context-transform carryover.

These are valid and useful. They also increase dependence on context-indexed structures, which raises the migration cost to latent-context operation.

---

## Why “Drop the Context Bit” Became Harder Than It Sounds

### 1) Observability cliff

With explicit context removed, nodes lose a direct disambiguator for two different transform regimes that can share similar local route pressures.

In Stage 1, context-conditioned lookup can be learned quickly.
In Stage 2, the system must infer hidden state from history traces and delayed outcomes.

### 2) Credit assignment delay compounds ambiguity

Feedback is sequential and local (good for architecture), but this increases temporal distance between a hidden-context decision and corrective credit.

Without explicit context, that delay makes transform attribution noisier and easier to overwrite by route-economy effects.

### 3) Existing memory schema is context-key friendly, not latent-state native

Current support structures naturally attach to explicit context tags when present.
When context is hidden, there is no built-in compact latent state representation that all nodes can reference locally.

### 4) Transfer tuning currently fights stale explicit-context priors

Recent retuning logic addresses contradictory context-bound supports. That helps Stage 1 transfer. But it also indicates the model can strongly commit to context-indexed priors that are hard to reinterpret when context becomes implicit.

---

## Discovered Difficulty (Current State)

Based on the traces and code shape, the discovered difficulty can be summarized as:

> The system is now good enough at using explicit context that removing it reveals a second-order bottleneck: latent context inference is under-instrumented relative to context-conditioned execution.

In other words, this is less “the architecture can’t do Stage 2” and more “Stage 2 needs dedicated scaffolding and diagnostics, not just Stage 1 knobs with context hidden.”

---

## Practical Forward Path (Recommended)

### Step A — Add a “Contextless Stage 1.5” mode before full Stage 2

Run the same task mapping, but remove only node-visible `context_bit` while keeping environment-side target logic unchanged.

Purpose:
- isolate inference difficulty from task-definition changes,
- keep comparability with existing Stage 1 metrics,
- avoid conflating multiple deltas in one jump.

### Step B — Introduce local latent-context surrogates (without global leakage)

Allow nodes to perceive strictly local sequence traces that do not reveal target or global labels, e.g.:

- previous head payload bits seen at that node,
- short rolling transform/outcome sketches (local only),
- low-bandwidth “recent mismatch trend” scalar.

This keeps locality intact while giving the selector a workable hidden-state proxy.

### Step C — Split diagnostics by failure class

Add reporting that partitions misses into:

1. route wrong / transform potentially right,
2. route right / transform wrong,
3. transform unstable across inferred context boundary,
4. delayed correction (credit arrives but selector inertia persists).

Without this split, latent-context tuning will be guesswork.

### Step D — Rebalance selector trust hierarchy under hidden context

When no explicit context is present:

- reduce trust in long-lived context-bound action priors,
- increase weight on very recent local return quality and contradiction evidence,
- decay transform certainty faster after low-match pulses.

This should reduce stale-policy lock-in during hidden-state ambiguity.

### Step E — Gate claims on two robustness checks

Before claiming Stage 2 progress, require:

1. warm full beats cold on **both** exact matches and mean bit accuracy across fixed seeds,
2. performance remains stable when schedule order is perturbed (to test true sequence inference vs accidental ordering dependence).

---

## Concrete Near-Term Experiments

1. **Ablation 1 (context hidden, no new features):** establish a baseline drop from current Stage 1.
2. **Ablation 2 (add previous-payload local feature only):** measure recovery.
3. **Ablation 3 (add mismatch-trend scalar only):** test if tiny feedback memory is enough.
4. **Ablation 4 (both together):** check interaction and overfitting risk.
5. **Transfer replay (Task A→B) in contextless mode:** compare full/substrate/cold deltas.

Keep each ablation small, with fixed seeds and a frozen summary schema.

---

## Risks to Watch

- **Hidden leakage risk:** latent surrogates accidentally encoding target information.
- **Metric illusion:** exact-match gains with stagnant mean bit accuracy (already seen pattern).
- **Overfitted sequence artifacts:** success tied to one schedule ordering.
- **Selector churn:** too-fast decay causing instability and lost carryover value.

---

## Final Evaluation

Dropping the context bit remains the right direction and still aligns with the CVT-1 spec. The current difficulty is expected: explicit-context mechanisms matured faster than latent-state inference support.

The best move now is a staged migration with strong attribution diagnostics, not a hard switch. If done this way, Stage 2 can become a genuine proof of sequence-sensitive local learning rather than a regression surprise.
