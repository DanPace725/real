from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence


@dataclass
class LLMApiTraceEvent:
    """Normalized trace event for one LLM API-oriented agent action."""

    action: str
    timestamp: float
    request_tokens: int
    response_tokens: int
    latency_ms: float
    success: bool
    used_tool: bool
    quality: float
    error_type: str = ""
    trace_completeness_delta: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return max(0, self.request_tokens) + max(0, self.response_tokens)

    def to_dict(self) -> Dict[str, object]:
        return {
            "action": self.action,
            "timestamp": self.timestamp,
            "request_tokens": self.request_tokens,
            "response_tokens": self.response_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "used_tool": self.used_tool,
            "quality": self.quality,
            "error_type": self.error_type,
            "trace_completeness_delta": self.trace_completeness_delta,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "LLMApiTraceEvent":
        return cls(
            action=str(data.get("action", "unknown")),
            timestamp=float(data.get("timestamp", time.time())),
            request_tokens=int(data.get("request_tokens", 0)),
            response_tokens=int(data.get("response_tokens", 0)),
            latency_ms=float(data.get("latency_ms", 0.0)),
            success=bool(data.get("success", False)),
            used_tool=bool(data.get("used_tool", False)),
            quality=float(data.get("quality", 0.0)),
            error_type=str(data.get("error_type", "")),
            trace_completeness_delta=float(data.get("trace_completeness_delta", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


class JSONLTraceRecorder:
    """Append-only JSONL recorder for emitted trace events."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: LLMApiTraceEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), separators=(",", ":")) + "\n")


def load_trace_events(path: Path) -> List[LLMApiTraceEvent]:
    if not path.exists():
        raise FileNotFoundError(f"Trace input not found: {path}")

    events: List[LLMApiTraceEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                continue
            events.append(LLMApiTraceEvent.from_dict(data))

    if not events:
        raise ValueError(f"Trace file contains no events: {path}")

    return events


class TraceReplayBuffer:
    """Provides trace events in sequence, optionally action-matched and looped."""

    def __init__(
        self,
        events: Sequence[LLMApiTraceEvent],
        *,
        strict_action_match: bool = False,
        loop: bool = True,
    ) -> None:
        if not events:
            raise ValueError("TraceReplayBuffer requires at least one event")
        self._events = list(events)
        self._cursor = 0
        self.strict_action_match = strict_action_match
        self.loop = loop

    @classmethod
    def from_jsonl(
        cls,
        path: Path,
        *,
        strict_action_match: bool = False,
        loop: bool = True,
    ) -> "TraceReplayBuffer":
        return cls(
            load_trace_events(path),
            strict_action_match=strict_action_match,
            loop=loop,
        )

    def next_for_action(self, requested_action: str) -> LLMApiTraceEvent:
        if not self.strict_action_match:
            return self._pop_next()

        start = self._cursor
        while True:
            event = self._pop_next()
            if event.action == requested_action:
                return event
            if not self.loop and self._cursor >= len(self._events):
                break
            if self.loop and self._cursor == start:
                break

        raise RuntimeError(
            f"Replay trace exhausted without matching action '{requested_action}'"
        )

    def _pop_next(self) -> LLMApiTraceEvent:
        if not self.loop and self._cursor >= len(self._events):
            raise RuntimeError("Replay trace exhausted")

        idx = self._cursor % len(self._events)
        event = self._events[idx]
        self._cursor += 1
        return event
