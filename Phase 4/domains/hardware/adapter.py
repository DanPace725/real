from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

from real_core.types import ActionOutcome, DimensionScores, GCOStatus, CycleEntry


class HardwareObservationAdapter:
    """Simple hardware-like observation adapter for scaffold/demo use."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def observe(self, cycle: int) -> Dict[str, float]:
        # Placeholder signals; replace with psutil-backed adapter for parity.
        return {
            "cpu_load": self._rng.uniform(0.1, 0.9),
            "memory_pressure": self._rng.uniform(0.0, 0.4),
            "thermal_ratio": self._rng.uniform(0.0, 0.8),
            "process_count": self._rng.uniform(40, 140),
            "cycle": float(cycle),
        }


class HardwareActionBackend:
    """Action backend that simulates cost profiles by action class."""

    _ACTIONS = [
        "shallow_scan",
        "deep_scan",
        "rest",
        "introspect",
        "digest_log",
    ]

    def available_actions(self, history_size: int) -> List[str]:
        if history_size < 5:
            return ["shallow_scan", "rest", "deep_scan"]
        if history_size < 12:
            return ["shallow_scan", "rest", "deep_scan", "introspect"]
        return list(self._ACTIONS)

    def execute(self, action: str) -> ActionOutcome:
        t0 = time.perf_counter()
        if action == "digest_log":
            _ = sum(i * i for i in range(15000))
        elif action == "deep_scan":
            _ = sum(i for i in range(5000))
        elif action == "introspect":
            _ = sum(i for i in range(3000))
        elapsed = time.perf_counter() - t0
        return ActionOutcome(success=True, result={"action": action}, cost_secs=elapsed)


@dataclass
class HardwareCoherenceModel:
    dimension_names: Tuple[str, ...] = (
        "continuity",
        "vitality",
        "contextual_fit",
        "differentiation",
        "accountability",
        "reflexivity",
    )

    def score(self, state_after: Dict[str, float], history: List[CycleEntry]) -> DimensionScores:
        load = state_after.get("cpu_load", 0.5)
        mem = state_after.get("memory_pressure", 0.0)
        thermal = state_after.get("thermal_ratio", 0.0)

        continuity = max(0.0, min(1.0, 1.0 - abs(load - 0.5)))
        vitality = max(0.0, min(1.0, 1.0 - ((load - 0.4) ** 2) / 0.25 - 0.2 * mem))
        contextual_fit = max(0.0, min(1.0, 1.0 - thermal))
        differentiation = max(0.0, min(1.0, 1.0 - mem))
        accountability = max(0.2, min(1.0, len(history) / 20.0))

        recent = history[-10:]
        if len(recent) < 3:
            reflexivity = 0.3
        else:
            switches = 0
            recoveries = 0
            attempts = 0
            for i in range(1, len(recent)):
                if recent[i - 1].delta < -0.02:
                    attempts += 1
                    if recent[i].action != recent[i - 1].action:
                        switches += 1
                        if recent[i].delta > 0:
                            recoveries += 1
            switch_rate = switches / max(1, attempts)
            recovery_rate = recoveries / max(1, switches)
            reflexivity = 0.5 * switch_rate + 0.5 * recovery_rate

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
