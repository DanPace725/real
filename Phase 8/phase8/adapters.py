from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .environment import RoutingEnvironment
from .substrate import ConnectionSubstrate


class LocalNodeObservationAdapter:
    def __init__(
        self,
        environment: RoutingEnvironment,
        node_id: str,
    ) -> None:
        self.environment = environment
        self.node_id = node_id

    def observe(self, cycle: int) -> Dict[str, float]:
        return self.environment.observe_local(self.node_id)


class LocalNodeActionBackend:
    def __init__(
        self,
        environment: RoutingEnvironment,
        node_id: str,
        neighbor_ids: Tuple[str, ...],
        substrate: ConnectionSubstrate,
    ) -> None:
        self.environment = environment
        self.node_id = node_id
        self.neighbor_ids = neighbor_ids
        self.substrate = substrate

    def available_actions(self, history_size: int) -> List[str]:
        actions = ["rest"]
        local_inbox = len(self.environment.inboxes[self.node_id])
        for neighbor_id in self.neighbor_ids:
            route_cost = self.substrate.use_cost(neighbor_id)
            if self.environment.route_available(self.node_id, neighbor_id, route_cost):
                actions.append(f"route:{neighbor_id}")
            neighbor_congestion = len(self.environment.inboxes.get(neighbor_id, []))
            if (
                local_inbox > 0
                and neighbor_congestion >= self.environment.inbox_capacity
                and self.environment.inhibit_available(self.node_id)
                and neighbor_id != self.environment.sink_id
            ):
                actions.append(f"inhibit:{neighbor_id}")
        return actions

    def execute(self, action: str):
        from real_core.types import ActionOutcome

        if action == "rest":
            recovered = self.environment.rest_node(self.node_id)
            return ActionOutcome(
                success=True,
                result={"action": action, "recovered_atp": recovered},
                cost_secs=0.0,
            )

        if action.startswith("route:"):
            neighbor_id = action.split(":", 1)[1]
            cost = self.substrate.use_cost(neighbor_id)
            result = self.environment.route_signal(self.node_id, neighbor_id, cost)
            return ActionOutcome(
                success=bool(result["success"]),
                result=result,
                cost_secs=float(result["cost"]),
            )

        if action.startswith("inhibit:"):
            neighbor_id = action.split(":", 1)[1]
            result = self.environment.inhibit_neighbor(self.node_id, neighbor_id)
            return ActionOutcome(
                success=bool(result["success"]),
                result=result,
                cost_secs=float(result["cost"]),
            )

        return ActionOutcome(success=False, result={"action": action}, cost_secs=0.0)


@dataclass
class LocalNodeCoherenceModel:
    dimension_names: Tuple[str, ...] = (
        "continuity",
        "vitality",
        "contextual_fit",
        "differentiation",
        "accountability",
        "reflexivity",
    )

    def score(self, state_after: Dict[str, float], history: List[object]) -> Dict[str, float]:
        atp_ratio = state_after.get("atp_ratio", 0.0)
        inbox_load = state_after.get("inbox_load", 0.0)
        reward_buffer = state_after.get("reward_buffer", 0.0)
        oldest_packet_age = state_after.get("oldest_packet_age", 0.0)
        queue_pressure = state_after.get("queue_pressure", 0.0)
        ingress_backlog = state_after.get("ingress_backlog", 0.0)

        continuity = 0.4 + 0.6 * atp_ratio - 0.12 * queue_pressure
        vitality = max(
            0.0,
            min(
                1.0,
                0.25
                + 0.45 * inbox_load
                + 0.35 * reward_buffer
                - 0.18 * oldest_packet_age
                - 0.10 * ingress_backlog,
            ),
        )

        progress_values = [
            value
            for key, value in state_after.items()
            if key.startswith("progress_")
        ]
        contextual_fit = max(progress_values) if progress_values else 0.5

        route_actions = [
            entry.action.split(":", 1)[1]
            for entry in history[-10:]
            if entry.action.startswith("route:")
        ]
        if not route_actions:
            differentiation = 0.35
        else:
            counts = {}
            for neighbor_id in route_actions:
                counts[neighbor_id] = counts.get(neighbor_id, 0) + 1
            specialization = max(counts.values()) / max(len(route_actions), 1)
            differentiation = max(0.2, min(1.0, specialization))

        accountability = min(
            1.0,
            0.2 + 0.07 * len(history) - 0.15 * queue_pressure - 0.08 * ingress_backlog,
        )

        if len(history) < 4:
            reflexivity = 0.30
        else:
            recent = history[-8:]
            revision_attempts = 0
            recoveries = 0
            for index in range(1, len(recent)):
                prior = recent[index - 1]
                current = recent[index]
                if prior.delta < -0.02:
                    revision_attempts += 1
                    if current.action != prior.action and current.delta > 0:
                        recoveries += 1
            reflexivity = (
                recoveries / revision_attempts
                if revision_attempts > 0
                else 0.45
            )

        return {
            "continuity": max(0.0, min(1.0, continuity)),
            "vitality": vitality,
            "contextual_fit": max(0.0, min(1.0, contextual_fit)),
            "differentiation": max(0.0, min(1.0, differentiation)),
            "accountability": max(0.0, min(1.0, accountability)),
            "reflexivity": max(0.0, min(1.0, reflexivity)),
        }

    def composite(self, dimensions: Dict[str, float]) -> float:
        return sum(dimensions.values()) / max(1, len(dimensions))

    def gco_status(self, dimensions: Dict[str, float], coherence: float):
        from real_core.types import GCOStatus

        if coherence < 0.35:
            return GCOStatus.CRITICAL
        if coherence < 0.60:
            return GCOStatus.DEGRADED
        if all(value >= 0.60 for value in dimensions.values()):
            return GCOStatus.STABLE
        return GCOStatus.PARTIAL


@dataclass
class LocalNodeMemoryBinding:
    environment: RoutingEnvironment
    node_id: str
    neighbor_ids: Tuple[str, ...]
    substrate: ConnectionSubstrate
    noise_scale: float = 0.14
    rng: random.Random = field(default_factory=random.Random)

    def modulate_observation(
        self,
        raw_obs: Dict[str, float],
        substrate,
        cycle: int,
    ) -> Dict[str, float]:
        modulated = dict(raw_obs)
        for neighbor_id in self.neighbor_ids:
            support = self.substrate.support(neighbor_id)
            clarity = max(0.15, min(0.95, 0.20 + support * 0.75))
            for prefix in ("progress", "congestion"):
                key = f"{prefix}_{neighbor_id}"
                if key not in modulated:
                    continue
                jitter = self.rng.gauss(0.0, self.noise_scale * (1.0 - clarity))
                modulated[key] = max(0.0, min(1.0, modulated[key] + jitter))
            modulated[f"support_{neighbor_id}"] = support
            modulated[f"support_velocity_{neighbor_id}"] = self.substrate.velocity(neighbor_id)
        return modulated

    def extra_actions(self, substrate, history: List[object]):
        from real_core.types import MemoryActionSpec

        actions = []
        state = self.environment.state_for(self.node_id)
        local_inbox = len(self.environment.inboxes[self.node_id])
        if state.atp > 0.0 and local_inbox == 0:
            for neighbor_id in self.neighbor_ids:
                cost = self.substrate.write_cost(neighbor_id)
                if cost <= state.atp + 1e-9:
                    actions.append(
                        MemoryActionSpec(
                            action=f"invest:{neighbor_id}",
                            estimated_cost=cost,
                        )
                    )
            maintain_cost = sum(
                self.substrate.maintain_cost(neighbor_id)
                for neighbor_id in self.substrate.active_neighbors()
            )
            if maintain_cost > 0.0 and maintain_cost <= state.atp + 1e-9:
                actions.append(
                    MemoryActionSpec(
                        action="maintain_edges",
                        estimated_cost=maintain_cost,
                    )
                )
        return actions

    def estimate_memory_action_cost(self, action: str, substrate) -> float | None:
        if action == "maintain_edges":
            return sum(
                self.substrate.maintain_cost(neighbor_id)
                for neighbor_id in self.substrate.active_neighbors()
            )
        if action.startswith("invest:"):
            neighbor_id = action.split(":", 1)[1]
            return self.substrate.write_cost(neighbor_id)
        return None

    def execute_memory_action(self, action: str, substrate):
        from real_core.types import ActionOutcome

        state = self.environment.state_for(self.node_id)
        if action == "maintain_edges":
            spent = self.substrate.maintain_connections(state.atp)
            if spent <= 0.0:
                return ActionOutcome(success=False, cost_secs=0.0)
            state.atp = max(0.0, state.atp - spent)
            return ActionOutcome(
                success=True,
                result={"maintained_edges": self.substrate.active_neighbors()},
                cost_secs=spent,
            )

        if action.startswith("invest:"):
            neighbor_id = action.split(":", 1)[1]
            spent = self.substrate.invest_connection(neighbor_id, state.atp)
            if spent is None:
                return ActionOutcome(success=False, cost_secs=0.0)
            state.atp = max(0.0, state.atp - spent)
            return ActionOutcome(
                success=True,
                result={"invested_neighbor": neighbor_id},
                cost_secs=spent,
            )

        return None

    def substrate_health_signal(
        self,
        substrate,
        state_after: Dict[str, float],
        history: List[object],
    ) -> Dict[str, float]:
        total = max(len(self.neighbor_ids), 1)
        active_ratio = len(self.substrate.active_neighbors()) / total
        mean_support = sum(
            self.substrate.support(neighbor_id)
            for neighbor_id in self.neighbor_ids
        ) / total
        return {
            "continuity": 0.4 + 0.6 * active_ratio,
            "contextual_fit": 0.35 + 0.65 * mean_support,
            "reflexivity": 0.3 + 0.7 * active_ratio,
        }
