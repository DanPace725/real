from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .interfaces import ActionBackend, CoherenceModel, ObservationAdapter
from .memory import EpisodicMemory
from .mesh import TiltRegulatoryMesh
from .selector import CFARSelector
from .session import SessionHistory
from .types import CycleEntry


@dataclass
class SessionSummary:
    cycles: int
    mean_coherence: float
    final_coherence: float
    gco_counts: Dict[str, int]
    session_id: int | None = None


class RealCoreEngine:
    """Domain-agnostic REAL engine for generalized Phase 4 runs."""

    def __init__(
        self,
        observer: ObservationAdapter,
        actions: ActionBackend,
        coherence: CoherenceModel,
        selector: Optional[CFARSelector] = None,
        mesh: Optional[TiltRegulatoryMesh] = None,
        memory: Optional[EpisodicMemory] = None,
        domain_name: str = "unknown",
        session_history: Optional[SessionHistory] = None,
    ) -> None:
        self.observer = observer
        self.actions = actions
        self.coherence = coherence
        self.selector = selector or CFARSelector()
        self.mesh = mesh or TiltRegulatoryMesh()
        self.memory = memory or EpisodicMemory(maxlen=500)
        self.domain_name = domain_name
        self.session_history = session_history
        self._prior_coherence: Optional[float] = None

    def run_cycle(self, cycle: int) -> CycleEntry:
        before = self.observer.observe(cycle)
        available = self.actions.available_actions(len(self.memory.entries))
        action, mode = self.selector.select(available, self.memory.entries)
        outcome = self.actions.execute(action)
        after = self.observer.observe(cycle)

        raw_dimensions = self.coherence.score(after, self.memory.entries)
        dimensions = self.mesh.apply(raw_dimensions)
        coherence = self.coherence.composite(dimensions)
        delta = 0.0 if self._prior_coherence is None else coherence - self._prior_coherence
        self._prior_coherence = coherence
        gco = self.coherence.gco_status(dimensions, coherence)

        entry = CycleEntry(
            cycle=cycle,
            action=action,
            mode=mode,
            state_before=before,
            state_after=after,
            dimensions=dimensions,
            coherence=coherence,
            delta=delta,
            gco=gco,
            cost_secs=outcome.cost_secs,
        )
        self.memory.record(entry)
        return entry

    def run_session(self, cycles: int = 50, consolidate_on_action: str = "rest") -> SessionSummary:
        counts = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        coherence_sum = 0.0

        for i in range(1, cycles + 1):
            entry = self.run_cycle(i)
            counts[entry.gco.value] += 1
            coherence_sum += entry.coherence

            if entry.action == consolidate_on_action and len(self.memory.entries) > 40:
                self.memory.consolidate_three_tier()

        final = self.memory.entries[-1].coherence if self.memory.entries else 0.0
        mean = coherence_sum / max(1, cycles)
        summary = SessionSummary(
            cycles=cycles,
            mean_coherence=mean,
            final_coherence=final,
            gco_counts=counts,
            session_id=None,
        )

        if self.session_history is not None:
            record = self.session_history.append(
                domain=self.domain_name,
                cycles=summary.cycles,
                mean_coherence=summary.mean_coherence,
                final_coherence=summary.final_coherence,
                gco_counts=summary.gco_counts,
            )
            summary.session_id = record.session_id

        return summary
