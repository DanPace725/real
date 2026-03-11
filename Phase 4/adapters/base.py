from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from real_core.types import ActionOutcome


@dataclass
class CostModel:
    """Optional shared cost model abstraction for domain actions."""

    def estimate(self, action: str) -> float:
        return 0.0


class BaseObservationAdapter:
    def observe(self, cycle: int) -> Dict[str, float]:
        raise NotImplementedError


class BaseActionBackend:
    def available_actions(self, history_size: int) -> List[str]:
        raise NotImplementedError

    def execute(self, action: str) -> ActionOutcome:
        raise NotImplementedError
