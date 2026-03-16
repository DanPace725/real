from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

_PHASE4_ROOT = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_PHASE4_ROOT) not in sys.path:
    sys.path.insert(0, str(_PHASE4_ROOT))

from real_core.substrate import MemorySubstrate, SubstrateConfig
from real_core.patterns import ConstraintPattern
from real_core.types import DimensionScores, SubstrateSnapshot


@dataclass
class ConnectionSubstrateConfig:
    fire_base_cost: float = 0.05
    fire_floor_cost: float = 0.01
    fire_discount_scale: float = 0.04
    write_base_cost: float = 0.14
    maintain_base_cost: float = 0.03
    slow_decay: float = 0.025
    bistable_threshold: float = 0.25
    neighbor_discount: float = 0.08
    accelerated_decay_factor: float = 2.5
    velocity_alpha: float = 0.30


class ConnectionSubstrate:
    """Edge-local memory substrate for a single node agent."""

    def __init__(
        self,
        neighbor_ids: Iterable[str],
        config: ConnectionSubstrateConfig | None = None,
    ) -> None:
        self.neighbor_ids = tuple(neighbor_ids)
        self.config = config or ConnectionSubstrateConfig()
        self._edge_keys = {
            neighbor_id: self._edge_key(neighbor_id)
            for neighbor_id in self.neighbor_ids
        }
        self._inner = MemorySubstrate(
            config=SubstrateConfig(
                keys=tuple(self._edge_keys.values()),
                slow_decay=self.config.slow_decay,
                bistable_threshold=self.config.bistable_threshold,
                write_base_cost=self.config.write_base_cost,
                maintain_base_cost=self.config.maintain_base_cost,
                neighbor_discount=self.config.neighbor_discount,
                accelerated_decay_factor=self.config.accelerated_decay_factor,
                velocity_alpha=self.config.velocity_alpha,
            )
        )

    @staticmethod
    def _edge_key(neighbor_id: str) -> str:
        return f"edge:{neighbor_id}"

    def support(self, neighbor_id: str) -> float:
        return self._inner.slow.get(self._edge_keys[neighbor_id], 0.0)

    def velocity(self, neighbor_id: str) -> float:
        return self._inner.slow_velocity.get(self._edge_keys[neighbor_id], 0.0)

    @property
    def dim_history(self) -> List[DimensionScores]:
        return self._inner.dim_history

    @dim_history.setter
    def dim_history(self, value: List[DimensionScores]) -> None:
        self._inner.dim_history = value

    @property
    def constraint_patterns(self) -> List[ConstraintPattern]:
        return self._inner.constraint_patterns

    def use_cost(self, neighbor_id: str) -> float:
        support = self.support(neighbor_id)
        discounted = self.config.fire_base_cost - self.config.fire_discount_scale * support
        return max(self.config.fire_floor_cost, discounted)

    def edge_key(self, neighbor_id: str) -> str:
        return self._edge_keys[neighbor_id]

    def edge_scores(self) -> Dict[str, float]:
        return {
            neighbor_id: self.support(neighbor_id)
            for neighbor_id in self.neighbor_ids
        }

    def is_active_connection(self, neighbor_id: str) -> bool:
        return self._inner.is_active(self._edge_keys[neighbor_id])

    def active_neighbors(self) -> List[str]:
        return [
            neighbor_id
            for neighbor_id in self.neighbor_ids
            if self.is_active_connection(neighbor_id)
        ]

    def write_cost(self, neighbor_id: str) -> float:
        return self._inner.write_cost(self._edge_keys[neighbor_id])

    def maintain_cost(self, neighbor_id: str) -> float:
        return self._inner.maintain_cost(self._edge_keys[neighbor_id])

    def invest_connection(self, neighbor_id: str, atp_budget: float) -> float | None:
        key = self._edge_keys[neighbor_id]
        cost = self._inner.write_cost(key)
        if atp_budget < cost:
            return None
        self._inner.slow[key] = min(1.0, self._inner.slow[key] + 0.20)
        self._inner.slow_age[key] = 0
        return cost

    def maintain_connections(self, atp_budget: float) -> float:
        total = 0.0
        for neighbor_id in self.active_neighbors():
            key = self._edge_keys[neighbor_id]
            cost = self._inner.maintain_cost(key)
            if atp_budget - total < cost:
                continue
            self._inner.slow[key] = min(
                1.0,
                self._inner.slow[key] + self._inner.config.slow_decay * 2.0,
            )
            self._inner.slow_age[key] = 0
            total += cost
        return total

    def update_fast(self, observation: dict[str, float]) -> None:
        self._inner.update_fast(observation)

    def update_dim_context(self, dim_scores: DimensionScores) -> None:
        self._inner.update_dim_context(dim_scores)

    def current_dim_trends(self) -> Dict[str, float]:
        if len(self._inner.dim_history) < 4:
            return {key: 0.0 for key in self._edge_keys.values()}

        recent = self._inner.dim_history[-6:]
        half = len(recent) // 2
        first_half = recent[:half]
        second_half = recent[half:]

        trends = {}
        for key in self._edge_keys.values():
            early = sum(item.get(key, 0.0) for item in first_half) / max(len(first_half), 1)
            late = sum(item.get(key, 0.0) for item in second_half) / max(len(second_half), 1)
            trends[key] = late - early
        return trends

    def seed_support(self, neighbor_ids: Iterable[str], value: float = 0.25) -> None:
        self._inner.seed_support(
            [self._edge_keys[neighbor_id] for neighbor_id in neighbor_ids if neighbor_id in self._edge_keys],
            value=value,
        )

    def add_pattern(self, pattern: ConstraintPattern) -> None:
        self._inner.constraint_patterns.append(pattern)

    def tick(self) -> None:
        self._inner.tick()

    def snapshot(self) -> SubstrateSnapshot:
        snapshot = self._inner.snapshot()
        snapshot.metadata["neighbor_ids"] = list(self.neighbor_ids)
        snapshot.metadata["active_neighbors"] = self.active_neighbors()
        return snapshot

    def save_state(self) -> SubstrateSnapshot:
        snapshot = self._inner.save_state()
        snapshot.metadata["neighbor_ids"] = list(self.neighbor_ids)
        snapshot.metadata["active_neighbors"] = self.active_neighbors()
        return snapshot

    def load_state(self, snapshot: SubstrateSnapshot) -> None:
        self._inner.load_state(snapshot)
