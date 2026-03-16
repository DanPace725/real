from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import json

from .models import FeedbackPulse, NodeRuntimeState, SignalPacket


def _edge_id(source_id: str, target_id: str) -> str:
    return f"{source_id}->{target_id}"


@dataclass
class RoutingEnvironment:
    adjacency: Dict[str, tuple[str, ...]]
    positions: Dict[str, int]
    source_id: str
    sink_id: str
    max_atp: float = 1.0
    rest_gain: float = 0.02
    ambient_gain: float = 0.005
    inhibit_cost: float = 0.02
    inhibit_duration: int = 1
    inbox_capacity: int = 4
    feedback_amount: float = 0.18
    packet_ttl: int = 8
    source_admission_policy: str = "fixed"
    source_admission_rate: int | None = None
    source_admission_min_rate: int = 1
    source_admission_max_rate: int | None = None

    def __post_init__(self) -> None:
        self.inboxes: Dict[str, List[SignalPacket]] = {
            node_id: [] for node_id in self.positions
        }
        self.node_states: Dict[str, NodeRuntimeState] = {
            node_id: NodeRuntimeState(
                node_id=node_id,
                position=position,
                atp=self.max_atp,
                max_atp=self.max_atp,
            )
            for node_id, position in self.positions.items()
            if node_id != self.sink_id
        }
        self.delivered_packets: List[SignalPacket] = []
        self.dropped_packets: List[SignalPacket] = []
        self.source_buffer: List[SignalPacket] = []
        self.pending_feedback: List[FeedbackPulse] = []
        self.total_injected = 0
        self.admitted_packets = 0
        self._next_packet_id = 1
        self.packet_counter = itertools.count(self._next_packet_id)
        self.current_cycle = 0
        self.overload_events = 0
        self.max_inbox_depth = 0
        self.max_source_backlog = 0
        self.last_source_admission = 0
        self.source_admission_history: List[int] = []

    def agent_ids(self) -> List[str]:
        return sorted(
            self.node_states.keys(),
            key=lambda node_id: self.positions[node_id],
        )

    def neighbors_of(self, node_id: str) -> tuple[str, ...]:
        return self.adjacency.get(node_id, ())

    def state_for(self, node_id: str) -> NodeRuntimeState:
        return self.node_states[node_id]

    def inject_signal(self, count: int = 1, cycle: int = 0) -> None:
        self.current_cycle = max(self.current_cycle, cycle)
        for _ in range(count):
            packet_number = next(self.packet_counter)
            self._next_packet_id = packet_number + 1
            packet_id = f"pkt-{packet_number}"
            self.source_buffer.append(
                SignalPacket(
                    packet_id=packet_id,
                    origin=self.source_id,
                    target=self.sink_id,
                    created_cycle=cycle,
                )
            )
            self.total_injected += 1
        self._admit_source_packets()
        self._record_inbox_pressure()

    def prepare_cycle(self, cycle: int) -> None:
        self.current_cycle = cycle
        self._admit_source_packets()
        self._prioritize_all_queues()
        self._record_inbox_pressure()

    def observe_local(self, node_id: str) -> dict[str, float]:
        state = self.state_for(node_id)
        local_packets = self.inboxes[node_id]
        local_ages = [self._packet_wait_age(packet) for packet in local_packets]
        oldest_age = max(local_ages, default=0)
        overflow = max(0, len(local_packets) - self.inbox_capacity)
        local = {
            "atp_ratio": state.atp / max(state.max_atp, 1e-9),
            "inbox_load": min(1.0, len(self.inboxes[node_id]) / max(self.inbox_capacity, 1)),
            "reward_buffer": min(1.0, state.reward_buffer / max(state.max_atp, 1e-9)),
            "neighbor_density": len(self.neighbors_of(node_id)) / max(len(self.positions) - 1, 1),
            "feedback_pending": self._feedback_pending_ratio(node_id),
            "oldest_packet_age": min(1.0, oldest_age / max(self.packet_ttl, 1)),
            "queue_pressure": min(1.0, overflow / max(self.inbox_capacity, 1)),
            "ingress_backlog": (
                min(1.0, len(self.source_buffer) / max(self.inbox_capacity, 1))
                if node_id == self.source_id
                else 0.0
            ),
            "dormant": 1.0 if state.dormant else 0.0,
        }
        sink_position = self.positions[self.sink_id]
        span = max(abs(sink_position - self.positions[self.source_id]), 1)

        for neighbor_id in self.neighbors_of(node_id):
            neighbor_position = self.positions[neighbor_id]
            progress = 1.0 - abs(sink_position - neighbor_position) / span
            local[f"progress_{neighbor_id}"] = max(0.0, min(1.0, progress))
            local[f"congestion_{neighbor_id}"] = min(
                1.0,
                len(self.inboxes[neighbor_id]) / max(self.inbox_capacity, 1),
            )
            if neighbor_id == self.sink_id:
                local[f"inhibited_{neighbor_id}"] = 0.0
            else:
                local[f"inhibited_{neighbor_id}"] = (
                    1.0 if self.state_for(neighbor_id).inhibited_for > 0 else 0.0
                )
        return local

    def route_available(self, node_id: str, neighbor_id: str, cost: float) -> bool:
        state = self.state_for(node_id)
        if state.atp + 1e-9 < cost:
            return False
        if not self.inboxes[node_id]:
            return False
        if neighbor_id != self.sink_id and self.state_for(neighbor_id).inhibited_for > 0:
            return False
        return len(self.inboxes.get(neighbor_id, [])) < self.inbox_capacity

    def inhibit_available(self, node_id: str) -> bool:
        return self.state_for(node_id).atp + 1e-9 >= self.inhibit_cost

    def rest_node(self, node_id: str) -> float:
        state = self.state_for(node_id)
        recovered = min(self.rest_gain, state.reward_buffer)
        if recovered <= 0.0:
            recovered = self.ambient_gain
        state.atp = min(state.max_atp, state.atp + recovered)
        state.reward_buffer = max(0.0, state.reward_buffer - recovered)
        state.rest_count += 1
        return recovered

    def route_signal(self, node_id: str, neighbor_id: str, cost: float) -> dict:
        if not self.route_available(node_id, neighbor_id, cost):
            return {"success": False, "cost": 0.0, "delivered": False}

        self._prioritize_inbox(node_id)
        packet = self.inboxes[node_id].pop(0)
        packet.hops.append(node_id)
        packet.edge_path.append(_edge_id(node_id, neighbor_id))
        packet.last_moved_cycle = self.current_cycle

        source_state = self.state_for(node_id)
        source_state.atp = max(0.0, source_state.atp - cost)
        source_state.routed_packets += 1

        if neighbor_id == self.sink_id:
            packet.hops.append(neighbor_id)
            packet.delivered = True
            packet.delivered_cycle = self.current_cycle
            self.delivered_packets.append(packet)
            self.pending_feedback.append(
                FeedbackPulse(
                    packet_id=packet.packet_id,
                    edge_path=list(packet.edge_path),
                    amount=self.feedback_amount,
                )
            )
            return {
                "success": True,
                "cost": cost,
                "delivered": True,
                "packet_id": packet.packet_id,
            }

        self.inboxes[neighbor_id].append(packet)
        self._prioritize_inbox(neighbor_id)
        self._record_inbox_pressure()
        return {
            "success": True,
            "cost": cost,
            "delivered": False,
            "packet_id": packet.packet_id,
        }

    def inhibit_neighbor(self, node_id: str, neighbor_id: str) -> dict:
        if neighbor_id == self.sink_id or not self.inhibit_available(node_id):
            return {"success": False, "cost": 0.0}
        source_state = self.state_for(node_id)
        source_state.atp = max(0.0, source_state.atp - self.inhibit_cost)
        target_state = self.state_for(neighbor_id)
        target_state.inhibited_for = max(target_state.inhibited_for, self.inhibit_duration)
        return {"success": True, "cost": self.inhibit_cost}

    def advance_feedback(self) -> List[dict]:
        delivered = []
        remaining = []
        for pulse in self.pending_feedback:
            edge = pulse.next_edge()
            if edge is None:
                continue
            source_id, _ = edge.split("->", 1)
            state = self.state_for(source_id)
            state.atp = min(state.max_atp, state.atp + pulse.amount)
            state.reward_buffer = min(state.max_atp, state.reward_buffer + pulse.amount)
            state.received_feedback += 1
            delivered.append(
                {
                    "packet_id": pulse.packet_id,
                    "edge": edge,
                    "node_id": source_id,
                    "amount": pulse.amount,
                }
            )
            pulse.advance()
            if not pulse.complete:
                remaining.append(pulse)
        self.pending_feedback = remaining
        return delivered

    def tick(self, cycle: int | None = None) -> None:
        if cycle is not None:
            self.current_cycle = cycle
        for state in self.node_states.values():
            if state.inhibited_for > 0:
                state.inhibited_for -= 1
        self._expire_stale_packets()
        self._admit_source_packets()
        self._prioritize_all_queues()
        self._record_inbox_pressure()

    def snapshot(self) -> dict:
        return {
            "nodes": {
                node_id: {
                    "atp": round(state.atp, 4),
                    "reward_buffer": round(state.reward_buffer, 4),
                    "inbox": len(self.inboxes[node_id]),
                    "inhibited_for": state.inhibited_for,
                    "routed_packets": state.routed_packets,
                    "received_feedback": state.received_feedback,
                }
                for node_id, state in self.node_states.items()
            },
            "delivered_packets": len(self.delivered_packets),
            "dropped_packets": len(self.dropped_packets),
            "pending_feedback": len(self.pending_feedback),
            "source_buffer": len(self.source_buffer),
            "last_source_admission": self.last_source_admission,
            "overload_events": self.overload_events,
            "max_inbox_depth": self.max_inbox_depth,
            "max_source_backlog": self.max_source_backlog,
        }

    def export_runtime_state(self) -> dict:
        return {
            "node_states": {
                node_id: asdict(state)
                for node_id, state in self.node_states.items()
            },
            "inboxes": {
                node_id: [asdict(packet) for packet in packets]
                for node_id, packets in self.inboxes.items()
            },
            "delivered_packets": [asdict(packet) for packet in self.delivered_packets],
            "pending_feedback": [asdict(pulse) for pulse in self.pending_feedback],
            "total_injected": self.total_injected,
            "admitted_packets": self.admitted_packets,
            "next_packet_id": self._next_packet_id,
            "current_cycle": self.current_cycle,
            "dropped_packets": [asdict(packet) for packet in self.dropped_packets],
            "source_buffer": [asdict(packet) for packet in self.source_buffer],
            "last_source_admission": self.last_source_admission,
            "source_admission_history": list(self.source_admission_history),
            "overload_events": self.overload_events,
            "max_inbox_depth": self.max_inbox_depth,
            "max_source_backlog": self.max_source_backlog,
        }

    def load_runtime_state(self, payload: dict) -> None:
        self._next_packet_id = int(payload.get("next_packet_id", 1))
        self.packet_counter = itertools.count(self._next_packet_id)
        self.current_cycle = int(payload.get("current_cycle", 0))

        node_states = payload.get("node_states", {})
        for node_id, state_data in node_states.items():
            if node_id not in self.node_states:
                continue
            self.node_states[node_id] = NodeRuntimeState(**state_data)

        inboxes = payload.get("inboxes", {})
        self.inboxes = {node_id: [] for node_id in self.positions}
        for node_id, packets in inboxes.items():
            self.inboxes[node_id] = [SignalPacket(**packet) for packet in packets]

        self.delivered_packets = [
            SignalPacket(**packet) for packet in payload.get("delivered_packets", [])
        ]
        self.pending_feedback = [
            FeedbackPulse(**pulse) for pulse in payload.get("pending_feedback", [])
        ]
        self.dropped_packets = [
            SignalPacket(**packet) for packet in payload.get("dropped_packets", [])
        ]
        self.source_buffer = [
            SignalPacket(**packet) for packet in payload.get("source_buffer", [])
        ]
        self.total_injected = int(payload.get("total_injected", 0))
        self.admitted_packets = int(payload.get("admitted_packets", 0))
        self.last_source_admission = int(payload.get("last_source_admission", 0))
        self.source_admission_history = [
            int(value) for value in payload.get("source_admission_history", [])
        ]
        self.overload_events = int(payload.get("overload_events", 0))
        self.max_inbox_depth = int(payload.get("max_inbox_depth", 0))
        self.max_source_backlog = int(payload.get("max_source_backlog", 0))

    def _feedback_pending_ratio(self, node_id: str) -> float:
        pending = 0
        for pulse in self.pending_feedback:
            if any(edge.startswith(f"{node_id}->") for edge in pulse.edge_path):
                pending += 1
        return min(1.0, pending / 3.0)

    def _packet_wait_age(self, packet: SignalPacket) -> int:
        anchor = packet.last_moved_cycle
        if anchor is None:
            anchor = packet.created_cycle
        return max(0, self.current_cycle - anchor)

    def _expire_stale_packets(self) -> None:
        if self.packet_ttl <= 0:
            return
        for node_id, packets in self.inboxes.items():
            kept = []
            for packet in packets:
                if self._packet_wait_age(packet) >= self.packet_ttl:
                    packet.dropped_cycle = self.current_cycle
                    packet.drop_reason = "ttl_expired"
                    self.dropped_packets.append(packet)
                    continue
                kept.append(packet)
            self.inboxes[node_id] = kept

    def _record_inbox_pressure(self) -> None:
        depths = [len(packets) for packets in self.inboxes.values()]
        if depths:
            self.max_inbox_depth = max(self.max_inbox_depth, max(depths))
        self.overload_events += sum(
            1 for depth in depths if depth > self.inbox_capacity
        )
        self.max_source_backlog = max(self.max_source_backlog, len(self.source_buffer))

    def _admit_source_packets(self) -> None:
        if self.source_id not in self.inboxes:
            return
        available_slots = max(0, self.inbox_capacity - len(self.inboxes[self.source_id]))
        if available_slots <= 0 or not self.source_buffer:
            self.last_source_admission = 0
            self.source_admission_history.append(0)
            self.max_source_backlog = max(self.max_source_backlog, len(self.source_buffer))
            return

        allowance = self._source_admission_allowance(available_slots)
        admitted = min(allowance, len(self.source_buffer))

        for _ in range(admitted):
            packet = self.source_buffer.pop(0)
            packet.last_moved_cycle = self.current_cycle
            self.inboxes[self.source_id].append(packet)
            self.admitted_packets += 1
        self.last_source_admission = admitted
        self.source_admission_history.append(admitted)
        self._prioritize_inbox(self.source_id)
        self.max_source_backlog = max(self.max_source_backlog, len(self.source_buffer))

    def _source_admission_allowance(self, available_slots: int) -> int:
        if self.source_admission_policy == "adaptive":
            return self._adaptive_source_admission_allowance(available_slots)

        allowance = available_slots
        if self.source_admission_rate is not None:
            allowance = min(allowance, max(0, self.source_admission_rate))
        return allowance

    def _adaptive_source_admission_allowance(self, available_slots: int) -> int:
        source_state = self.state_for(self.source_id)
        if source_state.dormant:
            return 0

        observation = self.observe_local(self.source_id)
        backlog = len(self.source_buffer)
        atp_ratio = observation.get("atp_ratio", 0.0)
        inbox_load = observation.get("inbox_load", 0.0)
        reward_ratio = observation.get("reward_buffer", 0.0)
        oldest_age = observation.get("oldest_packet_age", 0.0)
        feedback_pending = observation.get("feedback_pending", 0.0)

        allowance = self.source_admission_min_rate if source_state.atp > 0.0 else 0

        if backlog > self.inbox_capacity:
            allowance += 1
        if atp_ratio >= 0.75 and inbox_load <= 0.25:
            allowance += 1
        if reward_ratio >= 0.15 and feedback_pending > 0.0 and inbox_load <= 0.5:
            allowance += 1

        if inbox_load >= 0.75:
            allowance -= 1
        if oldest_age >= 0.60:
            allowance -= 1
        if atp_ratio <= 0.25:
            allowance -= 1

        ceiling = self.source_admission_max_rate
        if ceiling is None:
            ceiling = self.inbox_capacity

        return max(0, min(allowance, available_slots, ceiling))

    def _prioritize_all_queues(self) -> None:
        for node_id in self.node_states:
            self._prioritize_inbox(node_id)

    def _prioritize_inbox(self, node_id: str) -> None:
        packets = self.inboxes.get(node_id)
        if not packets or len(packets) < 2:
            return
        packets.sort(
            key=lambda packet: (
                -self._packet_wait_age(packet),
                -len(packet.edge_path),
                packet.created_cycle,
                packet.packet_id,
            )
        )


class NativeSubstrateSystem:
    """Small Phase 8 scaffold for local-routing experiments."""

    def __init__(
        self,
        adjacency: Dict[str, Iterable[str]],
        positions: Dict[str, int],
        source_id: str,
        sink_id: str,
        *,
        max_atp: float = 1.0,
        selector_seed: int | None = None,
        packet_ttl: int = 8,
        source_admission_policy: str = "fixed",
        source_admission_rate: int | None = None,
        source_admission_min_rate: int = 1,
        source_admission_max_rate: int | None = None,
    ) -> None:
        from .node_agent import NodeAgent

        normalized = {
            node_id: tuple(neighbor_ids)
            for node_id, neighbor_ids in adjacency.items()
        }
        self.environment = RoutingEnvironment(
            adjacency=normalized,
            positions=positions,
            source_id=source_id,
            sink_id=sink_id,
            max_atp=max_atp,
            packet_ttl=packet_ttl,
            source_admission_policy=source_admission_policy,
            source_admission_rate=source_admission_rate,
            source_admission_min_rate=source_admission_min_rate,
            source_admission_max_rate=source_admission_max_rate,
        )
        self.global_cycle = 0
        self.session_start_cycle = 0
        self.agents = {
            node_id: NodeAgent(
                node_id=node_id,
                neighbor_ids=normalized.get(node_id, ()),
                environment=self.environment,
                selector_seed=None if selector_seed is None else selector_seed + index,
            )
            for index, node_id in enumerate(self.environment.agent_ids())
        }

    def inject_signal(self, count: int = 1) -> None:
        self.environment.inject_signal(count=count, cycle=self.global_cycle)

    def run_global_cycle(self) -> dict[str, object]:
        self.global_cycle += 1
        self.environment.prepare_cycle(self.global_cycle)
        cycle_entries = {}
        for node_id in self.environment.agent_ids():
            cycle_entries[node_id] = self.agents[node_id].step()
        for packet in self.environment.delivered_packets:
            if packet.delivered_cycle is None:
                packet.delivered_cycle = self.global_cycle
        feedback = self.environment.advance_feedback()
        self.environment.tick(self.global_cycle)
        return {
            "cycle": self.global_cycle,
            "entries": cycle_entries,
            "feedback": feedback,
            "snapshot": self.environment.snapshot(),
        }

    def summarize(self) -> dict[str, object]:
        delivered = self.environment.delivered_packets
        mean_latency = (
            sum(
                max(0, (packet.delivered_cycle or self.global_cycle) - packet.created_cycle)
                for packet in delivered
            ) / len(delivered)
            if delivered
            else 0.0
        )
        mean_hops = (
            sum(len(packet.edge_path) for packet in delivered) / len(delivered)
            if delivered
            else 0.0
        )
        remaining_inboxes = sum(len(packets) for packets in self.environment.inboxes.values())
        node_atp_total = sum(
            state.atp for state in self.environment.node_states.values()
        )
        node_reward_total = sum(
            state.reward_buffer for state in self.environment.node_states.values()
        )
        dropped = self.environment.dropped_packets
        all_entries = [
            entry
            for agent in self.agents.values()
            for entry in agent.engine.memory.entries
        ]
        route_entries = [entry for entry in all_entries if entry.action.startswith("route:")]
        mean_route_cost = (
            sum(entry.cost_secs for entry in route_entries) / len(route_entries)
            if route_entries
            else 0.0
        )
        total_action_cost = sum(entry.cost_secs for entry in all_entries)
        session_cycles = max(1, self.global_cycle - self.session_start_cycle)
        return {
            "cycles": self.global_cycle,
            "injected_packets": self.environment.total_injected,
            "delivered_packets": len(delivered),
            "delivery_ratio": round(
                len(delivered) / max(self.environment.total_injected, 1),
                4,
            ),
            "dropped_packets": len(dropped),
            "drop_ratio": round(
                len(dropped) / max(self.environment.total_injected, 1),
                4,
            ),
            "remaining_inboxes": remaining_inboxes,
            "pending_feedback": len(self.environment.pending_feedback),
            "source_buffer": len(self.environment.source_buffer),
            "mean_latency": round(mean_latency, 4),
            "mean_hops": round(mean_hops, 4),
            "node_atp_total": round(node_atp_total, 4),
            "node_reward_total": round(node_reward_total, 4),
            "mean_route_cost": round(mean_route_cost, 5),
            "total_action_cost": round(total_action_cost, 5),
            "admitted_packets": self.environment.admitted_packets,
            "mean_source_admission": round(
                self.environment.admitted_packets / session_cycles,
                4,
            ),
            "last_source_admission": self.environment.last_source_admission,
            "overload_events": self.environment.overload_events,
            "max_inbox_depth": self.environment.max_inbox_depth,
            "max_source_backlog": self.environment.max_source_backlog,
            "active_edges": {
                node_id: agent.substrate.active_neighbors()
                for node_id, agent in self.agents.items()
            },
            "pattern_counts": {
                node_id: len(agent.substrate.constraint_patterns)
                for node_id, agent in self.agents.items()
            },
            "supports": {
                node_id: {
                    neighbor_id: round(agent.substrate.support(neighbor_id), 4)
                    for neighbor_id in agent.neighbor_ids
                }
                for node_id, agent in self.agents.items()
            },
        }

    def run_workload(
        self,
        *,
        cycles: int,
        initial_packets: int,
        packet_schedule: Dict[int, int] | None = None,
    ) -> dict[str, object]:
        self.inject_signal(count=initial_packets)
        schedule = dict(packet_schedule or {})
        reports = []
        for cycle_index in range(1, cycles + 1):
            scheduled = schedule.get(cycle_index, 0)
            if scheduled > 0:
                self.inject_signal(count=scheduled)
            reports.append(self.run_global_cycle())
        return {
            "reports": reports,
            "summary": self.summarize(),
        }

    def save_carryover(self, root_dir: str | Path) -> Path:
        target = Path(root_dir)
        target.mkdir(parents=True, exist_ok=True)
        nodes_dir = target / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)

        for node_id, agent in self.agents.items():
            agent.save_carryover(nodes_dir / f"{node_id}.json")

        manifest = {
            "global_cycle": self.global_cycle,
            "environment": self.environment.export_runtime_state(),
            "agent_ids": list(self.agents.keys()),
        }
        manifest_path = target / "system_state.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest_path

    def save_memory_carryover(self, root_dir: str | Path) -> Path:
        target = Path(root_dir)
        target.mkdir(parents=True, exist_ok=True)
        nodes_dir = target / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)
        for node_id, agent in self.agents.items():
            agent.save_carryover(nodes_dir / f"{node_id}.json")

        manifest = {
            "global_cycle": self.global_cycle,
            "agent_ids": list(self.agents.keys()),
        }
        manifest_path = target / "memory_state.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest_path

    def save_substrate_carryover(self, root_dir: str | Path) -> Path:
        target = Path(root_dir)
        target.mkdir(parents=True, exist_ok=True)
        nodes_dir = target / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)
        for node_id, agent in self.agents.items():
            agent.save_substrate_carryover(nodes_dir / f"{node_id}.json")

        manifest = {
            "global_cycle": self.global_cycle,
            "agent_ids": list(self.agents.keys()),
        }
        manifest_path = target / "substrate_state.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest_path

    def load_memory_carryover(self, root_dir: str | Path) -> bool:
        target = Path(root_dir)
        manifest_path = target / "memory_state.json"
        if not manifest_path.exists():
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.global_cycle = int(manifest.get("global_cycle", 0))
        self.session_start_cycle = self.global_cycle
        nodes_dir = target / "nodes"
        for node_id, agent in self.agents.items():
            agent.load_carryover(nodes_dir / f"{node_id}.json")
        return True

    def load_substrate_carryover(self, root_dir: str | Path) -> bool:
        target = Path(root_dir)
        manifest_path = target / "substrate_state.json"
        if not manifest_path.exists():
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.global_cycle = int(manifest.get("global_cycle", 0))
        self.session_start_cycle = self.global_cycle
        nodes_dir = target / "nodes"
        for node_id, agent in self.agents.items():
            agent.load_substrate_carryover(nodes_dir / f"{node_id}.json")
        return True

    def load_carryover(self, root_dir: str | Path) -> bool:
        target = Path(root_dir)
        manifest_path = target / "system_state.json"
        if not manifest_path.exists():
            return False

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.global_cycle = int(manifest.get("global_cycle", 0))
        self.session_start_cycle = self.global_cycle
        self.environment.load_runtime_state(manifest.get("environment", {}))

        nodes_dir = target / "nodes"
        for node_id, agent in self.agents.items():
            agent.load_carryover(nodes_dir / f"{node_id}.json")
        return True
