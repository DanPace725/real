"""Synthetic test environment for Phase 0 substrate validation.

Six signal channels with different temporal patterns. The agent observes
through the substrate: slow-layer support improves observation quality
(lower noise), mirroring chromatin accessibility — same environment,
different epistemic access.
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any

from .substrate import DIMENSIONS, MemorySubstrate

BASE_OBSERVATION_QUALITY = 0.30
SLOW_LAYER_BONUS = 0.60
NOISE_SCALE = 0.35

GCO_THRESHOLDS = {"STABLE": 0.72, "PARTIAL": 0.58, "DEGRADED": 0.40}
GCO_DIM_FLOOR = 0.50


class SignalEnvironment:
    """Six-channel signal environment with patterns at different timescales."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.cycle = 0
        self.signals: dict[str, float] = {d: 0.5 for d in DIMENSIONS}

        self._context_value = 0.5
        self._context_next_shift = self.rng.randint(15, 25)
        self._walk_value = 0.5
        self._ramp_phase = 0

    def tick(self):
        self.cycle += 1
        c = self.cycle

        self.signals["continuity"] = 0.5 + 0.4 * math.sin(
            2 * math.pi * c / 40
        )

        phase = (c % 30) / 30
        self.signals["vitality"] = 1.0 - abs(2 * phase - 1)

        if c >= self._context_next_shift:
            self._context_value = self.rng.uniform(0.2, 0.8)
            self._context_next_shift = c + self.rng.randint(15, 25)
        self.signals["contextual_fit"] = self._context_value

        base = 0.6
        pert = self.rng.gauss(0, 0.2) if self.rng.random() < 0.08 else 0.0
        self.signals["differentiation"] = max(0.0, min(1.0, base + pert))

        self._ramp_phase = (self._ramp_phase + 1) % 20
        self.signals["accountability"] = self._ramp_phase / 20

        step = self.rng.gauss(0, 0.05)
        self._walk_value = max(0.15, min(0.85, self._walk_value + step))
        self.signals["reflexivity"] = self._walk_value

    def observe(self, substrate: MemorySubstrate) -> dict[str, float]:
        """Partial, noisy observation. Quality improves with slow-layer support."""
        obs = {}
        for dim in DIMENSIONS:
            true_val = self.signals[dim]
            slow_support = (
                substrate.slow.get(dim, 0.0)
                if substrate.is_active(dim)
                else 0.0
            )
            quality = BASE_OBSERVATION_QUALITY + SLOW_LAYER_BONUS * slow_support
            quality = min(quality, 0.95)
            noise_std = NOISE_SCALE * (1.0 - quality)
            noise = self.rng.gauss(0, noise_std)
            obs[dim] = max(0.0, min(1.0, true_val + noise))
        return obs


class TestCoherenceModel:
    """Coherence model for the synthetic test environment.

    Computable entirely from the agent's observation history — no access
    to true signals. Naturally rewards slow-layer investment because
    better observation quality produces smoother, more consistent readings.
    """

    dimension_names = DIMENSIONS

    def score(
        self,
        observation: dict[str, float],
        history: list[dict[str, Any]],
        action: str,
        action_history: list[str],
    ) -> dict[str, float]:
        recent_obs = (
            [h["observation"] for h in history[-10:]] if history else []
        )
        dims: dict[str, float] = {}

        dims["continuity"] = self._score_continuity(recent_obs)
        dims["vitality"] = self._score_vitality(action_history)
        dims["contextual_fit"] = self._score_contextual_fit(
            observation, recent_obs
        )
        dims["differentiation"] = self._score_differentiation(action_history)
        dims["accountability"] = self._score_accountability(history)
        dims["reflexivity"] = self._score_reflexivity(history)

        return dims

    def composite(self, dimensions: dict[str, float]) -> float:
        if not dimensions:
            return 0.0
        return sum(dimensions.values()) / len(dimensions)

    def gco_status(
        self, dimensions: dict[str, float], coherence: float
    ) -> str:
        if coherence < GCO_THRESHOLDS["DEGRADED"]:
            return "CRITICAL"
        if coherence < GCO_THRESHOLDS["PARTIAL"]:
            return "DEGRADED"
        if coherence >= GCO_THRESHOLDS["STABLE"] and all(
            v >= GCO_DIM_FLOOR for v in dimensions.values()
        ):
            return "STABLE"
        return "PARTIAL"

    # ------------------------------------------------------------------
    # Per-dimension scoring
    # ------------------------------------------------------------------

    def _score_continuity(self, recent_obs: list[dict]) -> float:
        """Low variance in recent observations = stable identity."""
        if len(recent_obs) < 3:
            return 0.40
        dim_vars = []
        for dim in DIMENSIONS:
            vals = [o[dim] for o in recent_obs]
            dim_vars.append(statistics.variance(vals))
        mean_var = statistics.mean(dim_vars)
        return max(0.0, min(1.0, 1.0 - mean_var * 5))

    def _score_vitality(self, action_history: list[str]) -> float:
        """Balanced action profile — neither monotonous nor chaotic."""
        if len(action_history) < 3:
            return 0.40
        window = action_history[-12:]
        unique_ratio = len(set(window)) / len(window)
        return max(0.0, min(1.0, 4 * unique_ratio * (1 - unique_ratio) + 0.2))

    def _score_contextual_fit(
        self, observation: dict, recent_obs: list[dict]
    ) -> float:
        """Current observation consistent with recent trend."""
        if len(recent_obs) < 3:
            return 0.40
        scores = []
        for dim in DIMENSIONS:
            recent_vals = [o[dim] for o in recent_obs[-5:]]
            trend_mean = statistics.mean(recent_vals)
            deviation = abs(observation[dim] - trend_mean)
            scores.append(max(0.0, 1.0 - deviation * 3))
        return statistics.mean(scores)

    def _score_differentiation(self, action_history: list[str]) -> float:
        """Agent behavior distinguishable from random: using vocabulary breadth."""
        if len(action_history) < 5:
            return 0.40
        window = action_history[-15:]
        unique = len(set(window))
        return min(1.0, unique / max(len(window) * 0.4, 1))

    def _score_accountability(self, history: list[dict]) -> float:
        """Invest actions connected to observable improvement in that dimension."""
        if len(history) < 5:
            return 0.40
        traceable = 0
        checked = 0
        for i in range(max(0, len(history) - 12), len(history)):
            h = history[i]
            if not h["action"].startswith("invest_"):
                continue
            target = h["action"].replace("invest_", "")
            if target not in DIMENSIONS:
                continue
            before_vals = [
                history[j]["observation"].get(target, 0.5)
                for j in range(max(0, i - 2), i)
            ]
            after_vals = [
                history[j]["observation"].get(target, 0.5)
                for j in range(i + 1, min(i + 3, len(history)))
            ]
            if before_vals and after_vals:
                improvement = statistics.mean(after_vals) - statistics.mean(
                    before_vals
                )
                traceable += 1 if improvement > -0.05 else 0
                checked += 1
        if checked == 0:
            return 0.40
        return min(1.0, 0.30 + 0.70 * (traceable / checked))

    def _score_reflexivity(self, history: list[dict]) -> float:
        """Behavior change following coherence dips."""
        if len(history) < 5:
            return 0.40
        dips = 0
        switches = 0
        for i in range(1, min(len(history), 12)):
            idx = len(history) - i
            if history[idx].get("delta", 0) < -0.03:
                dips += 1
                if idx + 1 < len(history):
                    if history[idx + 1]["action"] != history[idx]["action"]:
                        switches += 1
        if dips == 0:
            return 0.50
        return min(1.0, 0.30 + 0.70 * (switches / dips))
