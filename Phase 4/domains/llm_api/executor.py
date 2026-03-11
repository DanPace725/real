from __future__ import annotations

import random
import time
from dataclasses import replace
from typing import Protocol

from .trace import LLMApiTraceEvent, TraceReplayBuffer


class LLMActionExecutor(Protocol):
    def execute(self, action: str) -> LLMApiTraceEvent:
        """Execute one action and return a normalized trace event."""


class SyntheticLLMExecutor:
    """Synthetic executor that emulates API call outcomes and telemetry."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def execute(self, action: str) -> LLMApiTraceEvent:
        r = self.rng
        now = time.time()

        if action == "plan_prompt":
            req = r.randint(80, 180)
            resp = r.randint(40, 120)
            latency = r.uniform(120, 260)
            quality = r.uniform(0.55, 0.72)
            success = True
            used_tool = False
            delta = 0.03
        elif action == "call_fast":
            req = r.randint(120, 320)
            resp = r.randint(80, 380)
            latency = r.uniform(180, 550)
            quality = r.uniform(0.50, 0.78)
            success = r.random() > 0.08
            used_tool = False
            delta = 0.0
        elif action == "call_reasoned":
            req = r.randint(400, 1100)
            resp = r.randint(400, 1700)
            latency = r.uniform(450, 1400)
            quality = r.uniform(0.62, 0.92)
            success = r.random() > 0.06
            used_tool = False
            delta = 0.01
        elif action == "run_tool":
            req = r.randint(180, 600)
            resp = r.randint(150, 700)
            latency = r.uniform(550, 1800)
            quality = r.uniform(0.45, 0.88)
            success = r.random() > 0.14
            used_tool = True
            delta = 0.02
        elif action == "self_check":
            req = r.randint(140, 500)
            resp = r.randint(120, 450)
            latency = r.uniform(220, 800)
            quality = r.uniform(0.58, 0.86)
            success = r.random() > 0.04
            used_tool = False
            delta = 0.06
        elif action == "retry":
            req = r.randint(160, 500)
            resp = r.randint(130, 450)
            latency = r.uniform(260, 1000)
            quality = r.uniform(0.50, 0.85)
            success = r.random() > 0.10
            used_tool = r.random() < 0.35
            delta = 0.02
        else:  # rest
            req = r.randint(8, 20)
            resp = r.randint(2, 20)
            latency = r.uniform(40, 120)
            quality = r.uniform(0.55, 0.70)
            success = True
            used_tool = False
            delta = 0.01

        error_type = "" if success else "simulated_failure"
        return LLMApiTraceEvent(
            action=action,
            timestamp=now,
            request_tokens=req,
            response_tokens=resp,
            latency_ms=latency,
            success=success,
            used_tool=used_tool,
            quality=quality,
            error_type=error_type,
            trace_completeness_delta=delta,
            metadata={"source": "synthetic"},
        )


class ReplayLLMExecutor:
    """Replay executor that sources events from a pre-recorded trace buffer."""

    def __init__(self, replay: TraceReplayBuffer) -> None:
        self.replay = replay

    def execute(self, action: str) -> LLMApiTraceEvent:
        event = self.replay.next_for_action(action)
        # Preserve trace payload while stamping local replay metadata.
        metadata = dict(event.metadata)
        metadata["source"] = "replay"
        metadata["requested_action"] = action
        return replace(event, timestamp=time.time(), metadata=metadata)
