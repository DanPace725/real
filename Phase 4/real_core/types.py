from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

DimensionScores = Dict[str, float]


class GCOStatus(str, Enum):
    STABLE = "STABLE"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class ActionOutcome:
    success: bool
    result: Dict[str, Any] = field(default_factory=dict)
    cost_secs: float = 0.0


@dataclass
class CycleEntry:
    cycle: int
    action: str
    mode: str
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    dimensions: DimensionScores
    coherence: float
    delta: float
    gco: GCOStatus
    cost_secs: float
