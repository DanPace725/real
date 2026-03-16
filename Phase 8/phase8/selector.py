from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

from .environment import RoutingEnvironment
from .substrate import ConnectionSubstrate


@dataclass
class Phase8Selector:
    """Local selector tuned for routing pressure and substrate bias."""

    environment: RoutingEnvironment
    node_id: str
    substrate: ConnectionSubstrate
    rng: random.Random = field(default_factory=random.Random)
    exploration_rate: float = 0.10
    recency_half_life: float = 6.0
    rest_atp_threshold: float = 0.12
    maintain_velocity_threshold: float = -0.015

    def select(self, available: List[str], history: List[object]) -> Tuple[str, str]:
        if not available:
            raise ValueError("No available actions")

        route_actions = [action for action in available if action.startswith("route:")]
        invest_actions = [action for action in available if action.startswith("invest:")]
        maintain_actions = [action for action in available if action == "maintain_edges"]
        rest_available = "rest" in available

        local_inbox = len(self.environment.inboxes[self.node_id])
        state = self.environment.state_for(self.node_id)
        observation = self.environment.observe_local(self.node_id)
        urgency = max(
            observation.get("oldest_packet_age", 0.0),
            observation.get("queue_pressure", 0.0),
            observation.get("ingress_backlog", 0.0),
        )

        if local_inbox > 0 and route_actions:
            if self.rng.random() < self._local_exploration_rate(history, local_inbox, urgency):
                return self._sample_routes(route_actions, history), "fluctuation"
            return self._best_route(route_actions, history), "guided"

        if state.atp <= self.rest_atp_threshold and rest_available:
            return "rest", "constraint"

        if maintain_actions and self._needs_maintenance():
            return "maintain_edges", "guided"

        if invest_actions:
            if self.rng.random() < 0.25:
                return self._best_invest(invest_actions, history), "guided"

        if rest_available:
            return "rest", "constraint"

        if invest_actions:
            return self._best_invest(invest_actions, history), "constraint"

        return available[0], "constraint"

    def _local_exploration_rate(
        self,
        history: List[object],
        local_inbox: int,
        urgency: float,
    ) -> float:
        maturity = min(1.0, len(history) / 24.0)
        pressure_discount = min(0.06, local_inbox * 0.02)
        urgency_discount = min(0.05, urgency * 0.08)
        return max(
            0.01,
            self.exploration_rate * (1.0 - 0.7 * maturity) - pressure_discount - urgency_discount,
        )

    def _best_route(self, route_actions: List[str], history: List[object]) -> str:
        scored = [(self._score_route(action, history), action) for action in route_actions]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _sample_routes(self, route_actions: List[str], history: List[object]) -> str:
        scores = [max(0.01, self._score_route(action, history) + 1.0) for action in route_actions]
        return self.rng.choices(route_actions, weights=scores, k=1)[0]

    def _best_invest(self, invest_actions: List[str], history: List[object]) -> str:
        scored = [(self._score_invest(action, history), action) for action in invest_actions]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _score_route(self, action: str, history: List[object]) -> float:
        neighbor_id = action.split(":", 1)[1]
        observation = self.environment.observe_local(self.node_id)

        recent_delta = self._recency_weighted_mean(history, action, field="delta", default=0.0)
        recent_coherence = self._recency_weighted_mean(history, action, field="coherence", default=0.5)
        support = self.substrate.support(neighbor_id)
        support_velocity = self.substrate.velocity(neighbor_id)
        progress = observation.get(f"progress_{neighbor_id}", 0.0)
        congestion = observation.get(f"congestion_{neighbor_id}", 0.0)
        inhibited = observation.get(f"inhibited_{neighbor_id}", 0.0)
        urgency = observation.get("oldest_packet_age", 0.0)
        queue_pressure = observation.get("queue_pressure", 0.0)
        ingress_backlog = observation.get("ingress_backlog", 0.0)
        cost_ratio = self.substrate.use_cost(neighbor_id) / max(self.substrate.config.fire_base_cost, 1e-9)
        stale_penalty = self._stale_bias_penalty(history, action)

        score = (
            0.50 * recent_delta
            + 0.18 * recent_coherence
            + 0.30 * support
            + 0.24 * progress
            + 0.08 * support_velocity
            + 0.20 * urgency
            + 0.10 * ingress_backlog
            - 0.22 * congestion
            - 0.18 * cost_ratio
            - 0.35 * inhibited
            - 0.12 * queue_pressure * congestion
            - stale_penalty
        )
        return score

    def _score_invest(self, action: str, history: List[object]) -> float:
        neighbor_id = action.split(":", 1)[1]
        observation = self.environment.observe_local(self.node_id)
        recent_route_delta = self._recency_weighted_mean(history, f"route:{neighbor_id}", field="delta", default=0.0)
        progress = observation.get(f"progress_{neighbor_id}", 0.0)
        congestion = observation.get(f"congestion_{neighbor_id}", 0.0)
        support_gap = 1.0 - self.substrate.support(neighbor_id)
        cost_ratio = self.substrate.write_cost(neighbor_id) / max(self.substrate.config.write_base_cost, 1e-9)
        return (
            0.30 * progress
            + 0.28 * support_gap
            + 0.22 * max(0.0, recent_route_delta)
            - 0.10 * congestion
            - 0.18 * cost_ratio
        )

    def _needs_maintenance(self) -> bool:
        for neighbor_id in self.substrate.active_neighbors():
            if self.substrate.velocity(neighbor_id) <= self.maintain_velocity_threshold:
                return True
        return False

    def _recency_weighted_mean(
        self,
        history: List[object],
        action: str,
        *,
        field: str,
        default: float,
    ) -> float:
        entries = [entry for entry in history if entry.action == action]
        if not entries:
            return default

        current_cycle = max(entry.cycle for entry in history)
        weighted_total = 0.0
        total_weight = 0.0
        for entry in entries[-24:]:
            age = max(0, current_cycle - entry.cycle)
            weight = 0.5 ** (age / max(self.recency_half_life, 1e-9))
            weighted_total += weight * float(getattr(entry, field))
            total_weight += weight
        if total_weight <= 0.0:
            return default
        return weighted_total / total_weight

    def _stale_bias_penalty(self, history: List[object], action: str) -> float:
        entries = [entry for entry in history if entry.action == action]
        if not entries:
            return 0.0
        current_cycle = max(entry.cycle for entry in history)
        latest = max(entry.cycle for entry in entries)
        age = max(0, current_cycle - latest)
        if age <= self.recency_half_life:
            return 0.0
        return min(0.18, 0.02 * (age - self.recency_half_life))
