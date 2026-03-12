from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

# Make Phase 4 real_core importable when this package is imported directly.
_THIS_FILE = Path(__file__).resolve()
_PHASE2_DIR = _THIS_FILE.parents[2]
_PHASE4_DIR = _PHASE2_DIR / "Phase 4"
if str(_PHASE4_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE4_DIR))

from real_core.types import CycleEntry, DimensionScores, GCOStatus


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class InferenceCoherenceModel:
    """
    M1 coherence mapping for inference-internal observations.

    Input state fields are expected from `InferenceSnapshot.to_observation()`.
    """

    dimension_names: tuple[str, ...] = (
        "continuity",
        "vitality",
        "contextual_fit",
        "differentiation",
        "accountability",
        "reflexivity",
    )

    def score(self, state_after: dict[str, float], history: list[CycleEntry]) -> DimensionScores:
        entropy_mean = float(state_after.get("token_entropy_mean", 0.0))
        entropy_std = float(state_after.get("token_entropy_std", 0.0))
        attention_entropy = float(state_after.get("attention_entropy_mean", 0.0))
        hidden_delta = float(state_after.get("hidden_delta_norm_mean", 0.0))

        # Continuity: lower volatility in entropy and hidden trajectory.
        continuity = _clip01(1.0 - 0.45 * entropy_std - 0.002 * hidden_delta)

        # Vitality: productive entropy band with inverted-parabola shape.
        vitality = _clip01(1.0 - ((entropy_mean - 1.4) ** 2) / 1.4)

        # Contextual fit: lower attention entropy implies stronger concentration.
        contextual_fit = _clip01(1.0 - 0.18 * attention_entropy)

        # Differentiation: reward moderate entropy variability, penalize extremes.
        differentiation = _clip01(1.0 - abs(entropy_std - 0.65) / 0.9)

        # Accountability: coherence between trajectory smoothness and attention structure.
        accountability = _clip01(1.0 - 0.10 * attention_entropy - 0.0015 * hidden_delta)

        # Reflexivity: did a recent negative delta trigger a mode/action change and recovery.
        reflexivity = 0.30
        recent = history[-12:]
        if len(recent) >= 4:
            dips = 0
            switches = 0
            recoveries = 0
            for i in range(1, len(recent)):
                prev = recent[i - 1]
                cur = recent[i]
                if prev.delta < -0.015:
                    dips += 1
                    if cur.action != prev.action:
                        switches += 1
                        if cur.delta > 0:
                            recoveries += 1
            switch_rate = switches / max(1, dips)
            recovery_rate = recoveries / max(1, switches)
            reflexivity = _clip01(0.45 * switch_rate + 0.55 * recovery_rate)

        return {
            "continuity": continuity,
            "vitality": vitality,
            "contextual_fit": contextual_fit,
            "differentiation": differentiation,
            "accountability": accountability,
            "reflexivity": reflexivity,
        }

    def composite(self, dimensions: DimensionScores) -> float:
        return sum(dimensions.values()) / max(1, len(dimensions))

    def gco_status(self, dimensions: DimensionScores, coherence: float) -> GCOStatus:
        if coherence < 0.40:
            return GCOStatus.CRITICAL
        if coherence < 0.65:
            return GCOStatus.DEGRADED
        if all(v >= 0.65 for v in dimensions.values()):
            return GCOStatus.STABLE
        return GCOStatus.PARTIAL
