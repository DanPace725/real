from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - optional at import time
    torch = None

try:
    from transformer_lens import HookedTransformer
except Exception:  # pragma: no cover - optional at import time
    HookedTransformer = None

# Make Phase 4 real_core importable when this package is imported directly.
_THIS_FILE = Path(__file__).resolve()
_PHASE2_DIR = _THIS_FILE.parents[2]
_PHASE4_DIR = _PHASE2_DIR / "Phase 4"
if str(_PHASE4_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE4_DIR))

from .adapter import InferenceRuntimeState
from .hooks import build_snapshot


def _require_live_deps() -> None:
    if torch is None:
        raise RuntimeError("torch is required for live inference mode")
    if HookedTransformer is None:
        raise RuntimeError("transformer_lens is required for live inference mode")


def _entropy(prob_tensor):
    p = prob_tensor.clamp_min(1e-12)
    return -(p * torch.log(p)).sum(dim=-1)


@dataclass
class LiveLoopConfig:
    """Configuration for online M1/M2 generation segments."""

    segment_tokens: int = 20
    max_total_new_tokens: int = 240
    temperature: float = 0.8
    sample_multinomial: bool = True


class LiveSegmentObservationAdapter:
    """
    Observation adapter that generates live TransformerLens segments online.

    Observe pattern per cycle:
    - First observe(cycle): returns latest known observation (before action)
    - Second observe(cycle): generates next segment with current runtime state
      (after action), extracts aggregate metrics, updates runtime state.

    This lets RealCoreEngine run a live M1/M2 loop without engine changes.
    """

    def __init__(
        self,
        *,
        model: Any,
        runtime_state: InferenceRuntimeState,
        prompt: str,
        config: LiveLoopConfig | None = None,
    ) -> None:
        _require_live_deps()
        self.model = model
        self.state = runtime_state
        self.prompt = prompt
        self.config = config or LiveLoopConfig()

        self._tokens = self.model.to_tokens(prompt, prepend_bos=True)
        if hasattr(self._tokens, "to"):
            self._tokens = self._tokens.to(self._resolve_device())

        self._generated_ids: list[int] = []
        self._final_layer = int(self.model.cfg.n_layers - 1)
        self._before_phase = True
        self._stopped = False
        self._prev_resid = None

        self.latest_observation: dict[str, float] = {
            "cycle": 0.0,
            "token_entropy_mean": 0.0,
            "token_entropy_std": 0.0,
            "attention_entropy_mean": 0.0,
            "hidden_delta_norm_mean": 0.0,
            "tokens_generated": 0.0,
            "generation_complete": 0.0,
            "temperature": float(self.state.current_temperature),
            "prefix_applied": 0.0,
        }
        self.segment_trace: list[dict[str, Any]] = []

        # Keep runtime state synchronized with config defaults at start.
        self.state.current_temperature = float(self.config.temperature)
        self.state.ingest_observation(self.latest_observation)

    @property
    def max_cycles_estimate(self) -> int:
        return max(1, math.ceil(self.config.max_total_new_tokens / max(1, self.config.segment_tokens)))

    @property
    def generation_complete(self) -> bool:
        return self._stopped

    def generated_text(self) -> str:
        if not self._generated_ids:
            return ""
        return self.model.to_string(self._generated_ids)

    def observe(self, cycle: int) -> dict[str, float]:
        if self._before_phase:
            out = dict(self.latest_observation)
            out["cycle"] = float(cycle)
            out["temperature"] = float(self.state.current_temperature)
            self._before_phase = False
            self.state.ingest_observation(out)
            return out

        metrics, trace = self._generate_segment()
        snapshot = build_snapshot(
            token_entropies=trace["token_entropies"],
            attention_entropies=trace["attention_entropies"],
            hidden_delta_norms=trace["hidden_delta_norms"],
            tokens_generated=trace["tokens_generated"],
        )

        out = snapshot.to_observation(cycle)
        out["temperature"] = float(self.state.current_temperature)
        out["generation_complete"] = 1.0 if self._stopped else 0.0
        out["tokens_generated_total"] = float(len(self._generated_ids))
        out["prefix_applied"] = 1.0 if trace.get("prefix_applied") else 0.0

        self.latest_observation = dict(out)
        self.segment_trace.append(
            {
                "cycle": int(cycle),
                "temperature": float(self.state.current_temperature),
                **metrics,
                "prefix_applied": bool(trace.get("prefix_applied")),
                "prefix_text": trace.get("prefix_text", ""),
            }
        )

        self._before_phase = True
        self.state.ingest_observation(out)
        return out

    def _resolve_device(self):
        cfg_device = getattr(getattr(self.model, "cfg", None), "device", None)
        if cfg_device is not None:
            return cfg_device
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _apply_pending_prefix(self) -> tuple[bool, str]:
        prefix = (self.state.pending_prefix or "").strip()
        if not prefix:
            return False, ""

        prefix_text = " " + prefix
        prefix_tokens = self.model.to_tokens(prefix_text, prepend_bos=False)
        if hasattr(prefix_tokens, "to"):
            prefix_tokens = prefix_tokens.to(self._tokens.device)
        self._tokens = torch.cat([self._tokens, prefix_tokens], dim=1)
        self.state.pending_prefix = ""
        return True, prefix

    def _generate_segment(self) -> tuple[dict[str, float], dict[str, Any]]:
        if self._stopped:
            empty_trace = {
                "token_entropies": [],
                "attention_entropies": [],
                "hidden_delta_norms": [],
                "tokens_generated": 0,
                "prefix_applied": False,
                "prefix_text": "",
            }
            metrics = {
                "segment_token_entropy_mean": 0.0,
                "segment_attention_entropy_mean": 0.0,
                "segment_hidden_delta_norm_mean": 0.0,
                "segment_tokens_generated": 0.0,
                "generation_complete": 1.0,
            }
            return metrics, empty_trace

        prefix_applied, prefix_text = self._apply_pending_prefix()

        token_entropies: list[float] = []
        attention_entropies: list[float] = []
        hidden_delta_norms: list[float] = []
        segment_ids: list[int] = []

        for _ in range(self.config.segment_tokens):
            if len(self._generated_ids) >= self.config.max_total_new_tokens:
                self._stopped = True
                break

            logits, cache = self.model.run_with_cache(self._tokens, remove_batch_dim=False)
            last_logits = logits[:, -1, :].float()
            scaled_logits = last_logits / max(self.state.current_temperature, 1e-6)
            probs = torch.softmax(scaled_logits, dim=-1)

            token_entropies.append(float(_entropy(probs).item()))

            pattern = cache["pattern", self._final_layer][0, :, -1, :]
            attention_entropies.append(float(_entropy(pattern.float()).mean().item()))

            resid = cache["resid_post", self._final_layer][0, -1, :].float().detach().cpu()
            if self._prev_resid is not None:
                hidden_delta_norms.append(float(torch.norm(resid - self._prev_resid, p=2).item()))
            self._prev_resid = resid

            if self.config.sample_multinomial:
                next_token = torch.multinomial(probs, num_samples=1)
                next_token_id = int(next_token.item())
            else:
                next_token_id = int(torch.argmax(probs, dim=-1).item())
                next_token = torch.tensor([[next_token_id]], device=self._tokens.device, dtype=self._tokens.dtype)

            segment_ids.append(next_token_id)
            self._generated_ids.append(next_token_id)
            self._tokens = torch.cat([self._tokens, next_token.to(self._tokens.device)], dim=1)

            eos_id = self.model.tokenizer.eos_token_id
            if eos_id is not None and next_token_id == eos_id:
                self._stopped = True
                break

        metrics = {
            "segment_token_entropy_mean": float(sum(token_entropies) / len(token_entropies)) if token_entropies else 0.0,
            "segment_attention_entropy_mean": float(sum(attention_entropies) / len(attention_entropies)) if attention_entropies else 0.0,
            "segment_hidden_delta_norm_mean": float(sum(hidden_delta_norms) / len(hidden_delta_norms)) if hidden_delta_norms else 0.0,
            "segment_tokens_generated": float(len(segment_ids)),
            "generation_complete": 1.0 if self._stopped else 0.0,
        }

        trace = {
            "token_entropies": token_entropies,
            "attention_entropies": attention_entropies,
            "hidden_delta_norms": hidden_delta_norms,
            "tokens_generated": len(segment_ids),
            "generated_text_segment": self.model.to_string(segment_ids) if segment_ids else "",
            "prefix_applied": prefix_applied,
            "prefix_text": prefix_text,
        }
        return metrics, trace
