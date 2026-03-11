from __future__ import annotations

from typing import Dict, List, Protocol, Tuple

from .types import ActionOutcome, CycleEntry, DimensionScores, GCOStatus


class ObservationAdapter(Protocol):
    def observe(self, cycle: int) -> Dict[str, float]:
        """Return an observation snapshot for the current cycle."""


class ActionBackend(Protocol):
    def available_actions(self, history_size: int) -> List[str]:
        """Return currently available action names."""

    def execute(self, action: str) -> ActionOutcome:
        """Execute an action and return outcome + measured cost."""


class CoherenceModel(Protocol):
    dimension_names: Tuple[str, ...]

    def score(self, state_after: Dict[str, float], history: List[CycleEntry]) -> DimensionScores:
        """Return six-dimensional coherence scores in [0, 1]."""

    def composite(self, dimensions: DimensionScores) -> float:
        """Return composite coherence score in [0, 1]."""

    def gco_status(self, dimensions: DimensionScores, coherence: float) -> GCOStatus:
        """Return global closure status."""


class Selector(Protocol):
    def select(self, available: List[str], history: List[CycleEntry]) -> Tuple[str, str]:
        """Return (action_name, mode_name)."""


class Consolidator(Protocol):
    def consolidate(self, entries: List[CycleEntry]) -> List[CycleEntry]:
        """Return retained entries after consolidation."""


class RegulatoryMesh(Protocol):
    def apply(self, dimensions: DimensionScores) -> DimensionScores:
        """Apply bounded inter-dimensional coupling."""
