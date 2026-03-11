from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from real_core.types import ActionOutcome, CycleEntry, DimensionScores, GCOStatus

from .executor import LLMActionExecutor, ReplayLLMExecutor, SyntheticLLMExecutor
from .trace import JSONLTraceRecorder, LLMApiTraceEvent, TraceReplayBuffer


@dataclass
class LLMApiRuntimeState:
    """Runtime state built from trace-shaped API events."""

    rng: random.Random
    total_calls: int = 0
    failures: int = 0
    retries: int = 0
    last_event: LLMApiTraceEvent | None = None
    trace_completeness: float = 0.70

    def apply_event(self, event: LLMApiTraceEvent) -> None:
        self.total_calls += 1
        if not event.success:
            self.failures += 1
        if event.action == "retry":
            self.retries += 1
        self.last_event = event
        self.trace_completeness = max(
            0.0,
            min(1.0, self.trace_completeness + float(event.trace_completeness_delta)),
        )

    def snapshot(self, cycle: int) -> Dict[str, float]:
        event = self.last_event
        if event is None:
            total_tokens = 300
            latency_ms = 450.0
            used_tool = False
            quality = 0.60
        else:
            total_tokens = event.total_tokens
            latency_ms = event.latency_ms
            used_tool = event.used_tool
            quality = event.quality

        error_rate = self.failures / max(1, self.total_calls)
        retry_pressure = self.retries / max(1, self.total_calls)
        return {
            "cycle": float(cycle),
            "token_load": min(1.0, total_tokens / 5000.0),
            "latency_ratio": min(1.0, latency_ms / 3000.0),
            "error_rate": min(1.0, error_rate),
            "retry_pressure": min(1.0, retry_pressure),
            "tool_usage": 1.0 if used_tool else 0.0,
            "response_quality": max(0.0, min(1.0, quality)),
            "trace_completeness": self.trace_completeness,
        }


class LLMApiObservationAdapter:
    """Observation adapter backed by trace-shaped runtime state."""

    def __init__(self, state: LLMApiRuntimeState, observation_noise: float = 0.01) -> None:
        self.state = state
        self.observation_noise = max(0.0, observation_noise)

    def observe(self, cycle: int) -> Dict[str, float]:
        obs = self.state.snapshot(cycle)
        if self.observation_noise > 0:
            jitter = self.state.rng.uniform(-self.observation_noise, self.observation_noise)
            obs["response_quality"] = max(0.0, min(1.0, obs["response_quality"] + jitter))
        return obs


class LLMApiActionBackend:
    """Action backend using pluggable executors and optional trace recording."""

    _ACTIONS = [
        "plan_prompt",
        "call_fast",
        "call_reasoned",
        "run_tool",
        "self_check",
        "retry",
        "rest",
    ]

    def __init__(
        self,
        state: LLMApiRuntimeState,
        executor: LLMActionExecutor,
        recorder: JSONLTraceRecorder | None = None,
    ) -> None:
        self.state = state
        self.executor = executor
        self.recorder = recorder

    def available_actions(self, history_size: int) -> List[str]:
        if history_size < 4:
            return ["plan_prompt", "call_fast", "rest"]
        if history_size < 10:
            return ["plan_prompt", "call_fast", "call_reasoned", "self_check", "rest"]
        return list(self._ACTIONS)

    def execute(self, action: str) -> ActionOutcome:
        t0 = time.perf_counter()
        try:
            event = self.executor.execute(action)
        except RuntimeError as exc:
            event = LLMApiTraceEvent(
                action=action,
                timestamp=time.time(),
                request_tokens=0,
                response_tokens=0,
                latency_ms=1.0,
                success=False,
                used_tool=False,
                quality=0.0,
                error_type="replay_exhausted",
                trace_completeness_delta=-0.02,
                metadata={"error": str(exc), "source": "fallback"},
            )

        self.state.apply_event(event)
        if self.recorder is not None:
            self.recorder.append(event)

        elapsed = time.perf_counter() - t0
        cost_secs = elapsed + (event.total_tokens / 100000.0) + (event.latency_ms / 10000.0)
        return ActionOutcome(
            success=event.success,
            result={
                "requested_action": action,
                **event.to_dict(),
            },
            cost_secs=cost_secs,
        )


@dataclass
class LLMApiCoherenceModel:
    """Maps API telemetry signals to REAL six-dimensional coherence."""

    dimension_names: Tuple[str, ...] = (
        "continuity",
        "vitality",
        "contextual_fit",
        "differentiation",
        "accountability",
        "reflexivity",
    )

    def score(self, state_after: Dict[str, float], history: List[CycleEntry]) -> DimensionScores:
        token_load = state_after.get("token_load", 0.1)
        latency_ratio = state_after.get("latency_ratio", 0.1)
        error_rate = state_after.get("error_rate", 0.0)
        retry_pressure = state_after.get("retry_pressure", 0.0)
        tool_usage = state_after.get("tool_usage", 0.0)
        quality = state_after.get("response_quality", 0.6)
        trace = state_after.get("trace_completeness", 0.7)

        if len(history) < 4:
            continuity = 0.5
        else:
            window = history[-8:]
            tokens = [e.state_after.get("token_load", token_load) for e in window]
            lats = [e.state_after.get("latency_ratio", latency_ratio) for e in window]
            continuity = max(0.0, min(1.0, 1.0 - (_variance(tokens) + _variance(lats)) * 10.0))

        vitality = 1.0 - ((token_load - 0.35) ** 2) / 0.20
        vitality = max(0.0, min(1.0, vitality - 0.30 * retry_pressure))

        contextual_fit = max(0.0, min(1.0, 0.75 * quality + 0.25 * tool_usage))
        differentiation = max(0.0, min(1.0, 1.0 - error_rate))
        accountability = max(0.0, min(1.0, trace))

        recent = history[-12:]
        if len(recent) < 4:
            reflexivity = 0.3
        else:
            dips = 0
            switches = 0
            recoveries = 0
            for i in range(1, len(recent)):
                if recent[i - 1].delta < -0.015:
                    dips += 1
                    if recent[i].action != recent[i - 1].action:
                        switches += 1
                        if recent[i].delta > 0:
                            recoveries += 1
            switch_rate = switches / max(1, dips)
            recovery_rate = recoveries / max(1, switches)
            reflexivity = max(0.0, min(1.0, 0.45 * switch_rate + 0.55 * recovery_rate))

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


def make_llm_api_bundle(
    *,
    seed: int | None = None,
    mode: str = "synthetic",
    trace_input_path: str | Path | None = None,
    trace_output_path: str | Path | None = None,
    strict_action_match: bool = False,
    loop_replay: bool = True,
    observation_noise: float = 0.01,
) -> tuple[LLMApiObservationAdapter, LLMApiActionBackend, LLMApiCoherenceModel]:
    rng = random.Random(seed)
    state = LLMApiRuntimeState(rng=rng)

    mode_normalized = mode.strip().lower()
    if mode_normalized == "replay":
        if trace_input_path is None:
            raise ValueError("llm_api replay mode requires trace_input_path")
        replay = TraceReplayBuffer.from_jsonl(
            Path(trace_input_path),
            strict_action_match=strict_action_match,
            loop=loop_replay,
        )
        executor: LLMActionExecutor = ReplayLLMExecutor(replay)
    elif mode_normalized == "synthetic":
        executor = SyntheticLLMExecutor(rng=rng)
    else:
        raise ValueError(f"Unsupported llm_api mode '{mode}'. Use synthetic or replay.")

    recorder = JSONLTraceRecorder(Path(trace_output_path)) if trace_output_path else None

    return (
        LLMApiObservationAdapter(state=state, observation_noise=observation_noise),
        LLMApiActionBackend(state=state, executor=executor, recorder=recorder),
        LLMApiCoherenceModel(),
    )


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / len(values)
