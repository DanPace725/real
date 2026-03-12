from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
import time

# Make Phase 4 real_core importable when this package is imported directly.
_THIS_FILE = Path(__file__).resolve()
_PHASE2_DIR = _THIS_FILE.parents[2]
_PHASE4_DIR = _PHASE2_DIR / "Phase 4"
if str(_PHASE4_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE4_DIR))

from real_core.types import ActionOutcome


@dataclass
class InferenceRuntimeState:
    """Mutable runtime container shared by observer and action backend."""

    latest_observation: dict[str, float] = field(default_factory=dict)
    current_temperature: float = 0.8
    min_temperature: float = 0.4
    max_temperature: float = 1.2
    temp_delta: float = 0.1
    temp_cooldown_steps: int = 3
    inject_prefix_text: str = "Keep the response coherent and explicitly structured."
    pending_prefix: str = ""
    enable_interventions: bool = True
    action_step: int = 0
    last_temp_adjust_step: int = -999999

    def ingest_observation(self, observation: dict[str, float]) -> None:
        self.latest_observation = dict(observation)


class InferenceObservationAdapter:
    """
    Phase 4 ObservationAdapter-compatible view into inference telemetry.

    In M1 this is intentionally thin: an external loop (e.g. notebook) feeds
    observations into `state.ingest_observation(...)`, and the adapter returns
    the latest snapshot to `RealCoreEngine`.
    """

    def __init__(self, state: InferenceRuntimeState) -> None:
        self.state = state

    def observe(self, cycle: int) -> dict[str, float]:
        baseline = {
            "cycle": float(cycle),
            "token_entropy_mean": 0.0,
            "token_entropy_std": 0.0,
            "attention_entropy_mean": 0.0,
            "hidden_delta_norm_mean": 0.0,
            "tokens_generated": 0.0,
            "temperature": float(self.state.current_temperature),
            "generation_complete": 0.0,
            "prefix_applied": 0.0,
        }
        baseline.update(self.state.latest_observation)
        baseline["cycle"] = float(cycle)
        baseline["temperature"] = float(self.state.current_temperature)
        return baseline


class InferenceActionBackend:
    """
    Phase 4 ActionBackend-compatible inference interventions.

    M2 keeps this intentionally lightweight:
    - bounded temperature up/down with cooldown
    - optional prefix injection
    - observe/rest no-op actions
    """

    _EARLY_ACTIONS = ["observe", "rest"]
    _FULL_ACTIONS = [
        "observe",
        "rest",
        "adjust_temperature_up",
        "adjust_temperature_down",
        "inject_prefix",
    ]

    def __init__(self, state: InferenceRuntimeState, enable_interventions: bool | None = None) -> None:
        self.state = state
        if enable_interventions is not None:
            self.state.enable_interventions = bool(enable_interventions)

    def available_actions(self, history_size: int) -> list[str]:
        if not self.state.enable_interventions:
            return self._EARLY_ACTIONS
        return self._EARLY_ACTIONS if history_size < 4 else self._FULL_ACTIONS

    def execute(self, action: str) -> ActionOutcome:
        t0 = time.perf_counter()
        self.state.action_step += 1

        if not self.state.enable_interventions and action not in {"observe", "rest"}:
            action = "observe"

        if action == "adjust_temperature_up":
            if self._in_temperature_cooldown():
                return self._cooldown_outcome(action, t0)
            self.state.current_temperature = min(
                self.state.max_temperature,
                self.state.current_temperature + self.state.temp_delta,
            )
            self.state.last_temp_adjust_step = self.state.action_step
        elif action == "adjust_temperature_down":
            if self._in_temperature_cooldown():
                return self._cooldown_outcome(action, t0)
            self.state.current_temperature = max(
                self.state.min_temperature,
                self.state.current_temperature - self.state.temp_delta,
            )
            self.state.last_temp_adjust_step = self.state.action_step
        elif action == "inject_prefix":
            self.state.pending_prefix = self.state.inject_prefix_text
        elif action not in {"observe", "rest"}:
            return ActionOutcome(
                success=False,
                result={"error": f"Unsupported action: {action}"},
                cost_secs=time.perf_counter() - t0,
            )

        return ActionOutcome(
            success=True,
            result={
                "action": action,
                "temperature": float(self.state.current_temperature),
                "pending_prefix": self.state.pending_prefix,
            },
            cost_secs=time.perf_counter() - t0,
        )

    def _in_temperature_cooldown(self) -> bool:
        return (self.state.action_step - self.state.last_temp_adjust_step) < self.state.temp_cooldown_steps

    def _cooldown_outcome(self, action: str, t0: float) -> ActionOutcome:
        return ActionOutcome(
            success=True,
            result={
                "action": action,
                "temperature": float(self.state.current_temperature),
                "skipped": True,
                "reason": "temperature_cooldown",
            },
            cost_secs=time.perf_counter() - t0,
        )
