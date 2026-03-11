"""Trace-shaped LLM API domain for Phase 4 generalized REAL core."""

from .adapter import (
    LLMApiActionBackend,
    LLMApiCoherenceModel,
    LLMApiObservationAdapter,
    make_llm_api_bundle,
)
from .trace import LLMApiTraceEvent, TraceReplayBuffer, JSONLTraceRecorder

__all__ = [
    "LLMApiActionBackend",
    "LLMApiCoherenceModel",
    "LLMApiObservationAdapter",
    "LLMApiTraceEvent",
    "TraceReplayBuffer",
    "JSONLTraceRecorder",
    "make_llm_api_bundle",
]
