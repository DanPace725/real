from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .adapter import InferenceRuntimeState


def load_m0_observations(metrics_path: str | Path) -> list[dict[str, float]]:
    """Load M0 metrics_raw.jsonl rows into M1 observation dicts."""
    path = Path(metrics_path)
    observations: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            observations.append(
                {
                    "token_entropy_mean": float(row.get("final_layer_token_entropy_mean", 0.0)),
                    "token_entropy_std": float(row.get("token_entropy_volatility_std", 0.0)),
                    "attention_entropy_mean": float(row.get("per_head_attention_entropy_mean", 0.0)),
                    "hidden_delta_norm_mean": float(row.get("hidden_state_delta_norm_mean", 0.0)),
                    "tokens_generated": float(row.get("num_generated_tokens", 0.0)),
                }
            )
    if not observations:
        raise ValueError(f"No observations found in {path}")
    return observations


class OfflineReplayObservationAdapter:
    """
    ObservationAdapter that replays saved M0 observations as before/after pairs.

    For each cycle:
    - first observe(cycle) returns observation[i] (before)
    - second observe(cycle) returns observation[i+1] (after), then advances i
    """

    def __init__(
        self,
        observations: Iterable[dict[str, float]],
        runtime_state: InferenceRuntimeState,
    ) -> None:
        self._observations = [dict(o) for o in observations]
        if not self._observations:
            raise ValueError("OfflineReplayObservationAdapter requires at least one observation")
        self._state = runtime_state
        self._index = 0
        self._before_phase = True

    @property
    def max_cycles(self) -> int:
        return max(1, len(self._observations) - 1)

    def observe(self, cycle: int) -> dict[str, float]:
        if self._before_phase:
            idx = min(self._index, len(self._observations) - 1)
            out = dict(self._observations[idx])
            self._before_phase = False
        else:
            idx = min(self._index + 1, len(self._observations) - 1)
            out = dict(self._observations[idx])
            self._index = min(self._index + 1, len(self._observations) - 1)
            self._before_phase = True

        out["cycle"] = float(cycle)
        out["temperature"] = float(self._state.current_temperature)
        self._state.ingest_observation(out)
        return out
