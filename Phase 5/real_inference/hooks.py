from __future__ import annotations

from dataclasses import dataclass

try:
    import torch
except Exception:  # pragma: no cover - optional at import time
    torch = None


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return float((sum((v - m) ** 2 for v in values) / len(values)) ** 0.5)


@dataclass
class InferenceSnapshot:
    """Compact, lossy observation over an inference step/window."""

    token_entropy_mean: float
    token_entropy_std: float
    attention_entropy_mean: float
    hidden_delta_norm_mean: float
    tokens_generated: int

    def to_observation(self, cycle: int) -> dict[str, float]:
        return {
            "cycle": float(cycle),
            "token_entropy_mean": float(self.token_entropy_mean),
            "token_entropy_std": float(self.token_entropy_std),
            "attention_entropy_mean": float(self.attention_entropy_mean),
            "hidden_delta_norm_mean": float(self.hidden_delta_norm_mean),
            "tokens_generated": float(self.tokens_generated),
        }


def _entropy(prob_tensor):
    if torch is None:
        raise RuntimeError("torch is required for entropy calculations in real_inference.hooks")
    p = prob_tensor.clamp_min(1e-12)
    return -(p * torch.log(p)).sum(dim=-1)


def build_snapshot(
    *,
    token_entropies: list[float],
    attention_entropies: list[float],
    hidden_delta_norms: list[float],
    tokens_generated: int,
) -> InferenceSnapshot:
    """
    Build an M1-ready observation from M0-style traces.

    This keeps the observation partial and aggregate by design.
    """

    return InferenceSnapshot(
        token_entropy_mean=_mean(token_entropies),
        token_entropy_std=_std(token_entropies),
        attention_entropy_mean=_mean(attention_entropies),
        hidden_delta_norm_mean=_mean(hidden_delta_norms),
        tokens_generated=int(tokens_generated),
    )


def build_snapshot_from_tlens_step(
    *,
    logits_last_step,
    attention_pattern,
    hidden_delta_norm: float,
    temperature: float,
) -> InferenceSnapshot:
    """
    Convenience helper for direct TransformerLens integration.

    Parameters:
    - logits_last_step: shape [1, vocab]
    - attention_pattern: shape [heads, key_positions]
    """

    if torch is None:
        raise RuntimeError("torch is required for TransformerLens snapshot extraction")

    scaled = logits_last_step.float() / max(temperature, 1e-6)
    probs = torch.softmax(scaled, dim=-1)
    token_entropy = float(_entropy(probs).item())

    head_entropy = _entropy(attention_pattern.float())
    attn_entropy = float(head_entropy.mean().item())

    return InferenceSnapshot(
        token_entropy_mean=token_entropy,
        token_entropy_std=0.0,
        attention_entropy_mean=attn_entropy,
        hidden_delta_norm_mean=float(hidden_delta_norm),
        tokens_generated=1,
    )
