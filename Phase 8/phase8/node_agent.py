from __future__ import annotations

import random
import sys
from pathlib import Path

_PHASE4_ROOT = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_PHASE4_ROOT) not in sys.path:
    sys.path.insert(0, str(_PHASE4_ROOT))

from real_core.engine import RealCoreEngine
from real_core.session_state import SessionStateStore

from .adapters import (
    LocalNodeActionBackend,
    LocalNodeCoherenceModel,
    LocalNodeMemoryBinding,
    LocalNodeObservationAdapter,
)
from .consolidation import Phase8ConsolidationPipeline
from .environment import RoutingEnvironment
from .selector import Phase8Selector
from .substrate import ConnectionSubstrate


class NodeAgent:
    """Phase 8 node wrapper around the generalized REAL core."""

    def __init__(
        self,
        node_id: str,
        neighbor_ids: tuple[str, ...],
        environment: RoutingEnvironment,
        *,
        selector_seed: int | None = None,
        carryover_path: str | Path | None = None,
    ) -> None:
        self.node_id = node_id
        self.neighbor_ids = tuple(neighbor_ids)
        self.environment = environment
        self.substrate = ConnectionSubstrate(self.neighbor_ids)

        rng = random.Random(selector_seed)
        selector = Phase8Selector(
            environment=environment,
            node_id=node_id,
            substrate=self.substrate,
            rng=rng,
        )

        observer = LocalNodeObservationAdapter(environment, node_id)
        actions = LocalNodeActionBackend(
            environment,
            node_id,
            self.neighbor_ids,
            self.substrate,
        )
        coherence = LocalNodeCoherenceModel()
        pipeline = Phase8ConsolidationPipeline()
        binding = LocalNodeMemoryBinding(
            environment=environment,
            node_id=node_id,
            neighbor_ids=self.neighbor_ids,
            substrate=self.substrate,
            rng=rng,
        )
        state_store = (
            SessionStateStore(Path(carryover_path))
            if carryover_path is not None
            else None
        )

        self.engine = RealCoreEngine(
            observer=observer,
            actions=actions,
            coherence=coherence,
            selector=selector,
            substrate=self.substrate,
            consolidation_pipeline=pipeline,
            memory_binding=binding,
            domain_name=f"phase8.node.{node_id}",
            session_state_store=state_store,
            session_budget=float("inf"),
        )
        self.cycle = 0

    @property
    def atp(self) -> float:
        return self.environment.state_for(self.node_id).atp

    def step(self):
        self.cycle += 1
        entry = self.engine.run_cycle(self.cycle)
        if entry.action == "rest" and len(self.engine.memory.entries) >= 8:
            self.engine._run_consolidation()
        return entry

    def save_carryover(self, path: str | Path) -> None:
        state_store = SessionStateStore(Path(path))
        state_store.save(self.engine.export_carryover())

    def load_carryover(self, path: str | Path) -> bool:
        state_store = SessionStateStore(Path(path))
        payload = state_store.load()
        if payload is None:
            return False
        self.engine.load_carryover(payload)
        self.cycle = max((entry.cycle for entry in self.engine.memory.entries), default=0)
        return True

    def save_substrate_carryover(self, path: str | Path) -> None:
        carryover = self.engine.export_carryover()
        carryover.episodic_entries = []
        state_store = SessionStateStore(Path(path))
        state_store.save(carryover)

    def load_substrate_carryover(self, path: str | Path) -> bool:
        state_store = SessionStateStore(Path(path))
        payload = state_store.load()
        if payload is None:
            return False
        payload.episodic_entries = []
        self.engine.load_carryover(payload)
        self.engine.memory.entries = []
        self.cycle = 0
        return True
