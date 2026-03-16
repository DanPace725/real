from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import json

from .admission import AdmissionSubstrate
from .models import FeedbackPulse, NodeRuntimeState, SignalPacket, SignalSpec

TRANSFORM_NAMES = ("identity", "rotate_left_1", "xor_mask_1010", "xor_mask_0101")
TASK_CONTEXT_MATCH_FLOOR = 0.75
DEBT_ACTIVATION_CREDIT = 0.30
DEBT_ACTIVATION_CONTEXT_CREDIT = 0.22
DEBT_ACTIVATION_EXISTING = 0.18


def _edge_id(source_id: str, target_id: str) -> str:
    return f"{source_id}->{target_id}"


def _normalize_transform_name(transform_name: str | None) -> str:
    return str(transform_name or "identity")


def _context_credit_key(transform_name: str, context_bit: int) -> str:
    return f"{transform_name}:context_{int(context_bit)}"


def _branch_debt_key(neighbor_id: str, transform_name: str) -> str:
    return f"{neighbor_id}:{transform_name}"


def _context_branch_debt_key(neighbor_id: str, transform_name: str, context_bit: int) -> str:
    return f"{neighbor_id}:{transform_name}:context_{int(context_bit)}"


def _branch_context_debt_key(neighbor_id: str, context_bit: int) -> str:
    return f"{neighbor_id}:context_{int(context_bit)}"


def _apply_transform(bits: Sequence[int], transform_name: str | None) -> List[int]:
    transform = _normalize_transform_name(transform_name)
    payload = [1 if int(bit) else 0 for bit in bits]
    if transform == "identity":
        return list(payload)
    if transform == "rotate_left_1":
        if not payload:
            return []
        return payload[1:] + payload[:1]
    if transform == "xor_mask_1010":
        mask = [1, 0, 1, 0]
        return [payload[index] ^ mask[index] for index in range(min(len(payload), len(mask)))]
    if transform == "xor_mask_0101":
        mask = [0, 1, 0, 1]
        return [payload[index] ^ mask[index] for index in range(min(len(payload), len(mask)))]
    raise ValueError(f"Unsupported transform '{transform}'")


def _target_bits_for_task(
    input_bits: Sequence[int],
    *,
    context_bit: int | None,
    task_id: str | None,
) -> List[int] | None:
    if not input_bits or task_id is None or context_bit is None:
        return None
    if task_id == "task_a":
        transform = "rotate_left_1" if context_bit == 0 else "xor_mask_1010"
        return _apply_transform(input_bits, transform)
    if task_id == "task_b":
        transform = "rotate_left_1" if context_bit == 0 else "xor_mask_0101"
        return _apply_transform(input_bits, transform)
    if task_id == "task_c":
        transform = "xor_mask_1010" if context_bit == 0 else "xor_mask_0101"
        return _apply_transform(input_bits, transform)
    return None


def _expected_transform_for_task(
    task_id: str | None,
    context_bit: int | None,
) -> str | None:
    if task_id is None or context_bit is None:
        return None
    if task_id == "task_a":
        return "rotate_left_1" if context_bit == 0 else "xor_mask_1010"
    if task_id == "task_b":
        return "rotate_left_1" if context_bit == 0 else "xor_mask_0101"
    if task_id == "task_c":
        return "xor_mask_1010" if context_bit == 0 else "xor_mask_0101"
    return None


def _bit_match_ratio(observed_bits: Sequence[int], target_bits: Sequence[int]) -> float:
    if not target_bits:
        return 0.0
    matched = 0
    for observed, target in zip(observed_bits, target_bits):
        matched += 1 if int(observed) == int(target) else 0
    return matched / max(len(target_bits), 1)


def _quality_scaled_credit(bit_match_ratio: float, *, floor: float = TASK_CONTEXT_MATCH_FLOOR) -> float:
    quality = max(0.0, min(1.0, bit_match_ratio))
    if quality <= floor:
        return 0.0
    return min(1.0, (quality - floor) / max(1.0 - floor, 1e-9))


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
        self.admission_substrate = AdmissionSubstrate()
        self._source_cycle_start_feedback = 0
        self._source_cycle_start_routed = 0
        self._source_cycle_start_backlog = 0
        self._source_cycle_action_cost = 0.0
        self.last_source_efficiency = 0.0
        self.source_efficiency_history: List[float] = []

    def agent_ids(self) -> List[str]:
        return sorted(
            self.node_states.keys(),
            key=lambda node_id: self.positions[node_id],
        )

    def neighbors_of(self, node_id: str) -> tuple[str, ...]:
        return self.adjacency.get(node_id, ())

    def state_for(self, node_id: str) -> NodeRuntimeState:
        return self.node_states[node_id]

    def create_packet(
        self,
        *,
        cycle: int,
        input_bits: Sequence[int] | None = None,
        payload_bits: Sequence[int] | None = None,
        context_bit: int | None = None,
        task_id: str | None = None,
        target_bits: Sequence[int] | None = None,
    ) -> SignalPacket:
        packet_number = next(self.packet_counter)
        self._next_packet_id = packet_number + 1
        packet_id = f"pkt-{packet_number}"
        return SignalPacket(
            packet_id=packet_id,
            origin=self.source_id,
            target=self.sink_id,
            created_cycle=cycle,
            input_bits=list(input_bits or payload_bits or []),
            payload_bits=list(payload_bits or input_bits or []),
            context_bit=context_bit,
            task_id=task_id,
            target_bits=list(target_bits or []),
        )

    def inject_packets(
        self,
        packets: Iterable[SignalPacket],
        *,
        cycle: int | None = None,
    ) -> None:
        if cycle is not None:
            self.current_cycle = max(self.current_cycle, cycle)
        for packet in packets:
            self.source_buffer.append(packet)
            self.total_injected += 1
        self._admit_source_packets()
        self._record_inbox_pressure()

    def inject_signal(
        self,
        count: int = 1,
        cycle: int = 0,
        *,
        packet_payloads: Sequence[Sequence[int]] | None = None,
        context_bits: Sequence[int | None] | None = None,
        task_id: str | None = None,
    ) -> None:
        self.current_cycle = max(self.current_cycle, cycle)
        payloads = list(packet_payloads or [])
        contexts = list(context_bits or [])
        if payloads and len(payloads) != count:
            raise ValueError("packet_payloads length must match count")
        if contexts and len(contexts) != count:
            raise ValueError("context_bits length must match count")

        packets = []
        for index in range(count):
            payload_bits = payloads[index] if payloads else None
            context_bit = contexts[index] if contexts else None
            packets.append(
                self.create_packet(
                    cycle=cycle,
                    input_bits=payload_bits,
                    payload_bits=payload_bits,
                    context_bit=context_bit,
                    task_id=task_id,
                )
            )
        self.inject_packets(packets, cycle=cycle)

    def prepare_cycle(self, cycle: int) -> None:
        self.current_cycle = cycle
        source_state = self.state_for(self.source_id)
        self._source_cycle_start_feedback = source_state.received_feedback
        self._source_cycle_start_routed = source_state.routed_packets
        self._source_cycle_start_backlog = len(self.source_buffer)
        self._source_cycle_action_cost = 0.0
        self._admit_source_packets()
        self._prioritize_all_queues()
        self._record_inbox_pressure()

    def observe_local(self, node_id: str) -> dict[str, float]:
        state = self.state_for(node_id)
        local_packets = self.inboxes[node_id]
        local_ages = [self._packet_wait_age(packet) for packet in local_packets]
        oldest_age = max(local_ages, default=0)
        overflow = max(0, len(local_packets) - self.inbox_capacity)
        head_packet = local_packets[0] if local_packets else None
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
            "has_packet": 1.0 if head_packet is not None else 0.0,
            "head_transform_depth": (
                min(1.0, len(head_packet.transform_trace) / 4.0)
                if head_packet is not None
                else 0.0
            ),
            "head_has_context": (
                1.0 if head_packet is not None and head_packet.context_bit is not None else 0.0
            ),
            "head_context_bit": (
                float(head_packet.context_bit)
                if head_packet is not None and head_packet.context_bit is not None
                else 0.0
            ),
            "last_feedback_amount": min(
                1.0,
                state.last_feedback_amount / max(self.feedback_amount, 1e-9),
            ),
            "last_match_ratio": min(1.0, max(0.0, state.last_match_ratio)),
            "dormant": 1.0 if state.dormant else 0.0,
        }
        payload_bits = head_packet.payload_bits if head_packet is not None else []
        for index in range(4):
            local[f"payload_bit_{index}"] = (
                float(payload_bits[index]) if index < len(payload_bits) else 0.0
            )
        for transform_name in TRANSFORM_NAMES:
            local[f"feedback_credit_{transform_name}"] = min(
                1.0,
                max(0.0, state.transform_credit.get(transform_name, 0.0)),
            )
            local[f"feedback_debt_{transform_name}"] = min(
                1.0,
                max(0.0, state.transform_debt.get(transform_name, 0.0)),
            )
            context_credit = 0.0
            context_debt = 0.0
            if head_packet is not None and head_packet.context_bit is not None:
                context_credit = state.context_transform_credit.get(
                    _context_credit_key(transform_name, int(head_packet.context_bit)),
                    0.0,
                )
                context_debt = state.context_transform_debt.get(
                    _context_credit_key(transform_name, int(head_packet.context_bit)),
                    0.0,
                )
            local[f"context_feedback_credit_{transform_name}"] = min(
                1.0,
                max(0.0, context_credit),
            )
            local[f"context_feedback_debt_{transform_name}"] = min(
                1.0,
                max(0.0, context_debt),
            )
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
            for transform_name in TRANSFORM_NAMES:
                branch_credit = state.branch_transform_credit.get(
                    _branch_debt_key(neighbor_id, transform_name),
                    0.0,
                )
                branch_debt = state.branch_transform_debt.get(
                    _branch_debt_key(neighbor_id, transform_name),
                    0.0,
                )
                context_branch_credit = 0.0
                context_branch_debt = 0.0
                if head_packet is not None and head_packet.context_bit is not None:
                    context_branch_credit = state.context_branch_transform_credit.get(
                        _context_branch_debt_key(
                            neighbor_id,
                            transform_name,
                            int(head_packet.context_bit),
                        ),
                        0.0,
                    )
                    context_branch_debt = state.context_branch_transform_debt.get(
                        _context_branch_debt_key(
                            neighbor_id,
                            transform_name,
                            int(head_packet.context_bit),
                        ),
                        0.0,
                    )
                local[f"branch_feedback_credit_{neighbor_id}_{transform_name}"] = min(
                    1.0,
                    max(0.0, branch_credit),
                )
                local[f"branch_feedback_debt_{neighbor_id}_{transform_name}"] = min(
                    1.0,
                    max(0.0, branch_debt),
                )
                local[f"context_branch_feedback_credit_{neighbor_id}_{transform_name}"] = min(
                    1.0,
                    max(0.0, context_branch_credit),
                )
                local[f"context_branch_feedback_debt_{neighbor_id}_{transform_name}"] = min(
                    1.0,
                    max(0.0, context_branch_debt),
                )
            branch_context_debt = 0.0
            branch_context_credit = 0.0
            if head_packet is not None and head_packet.context_bit is not None:
                branch_context_credit = state.branch_context_credit.get(
                    _branch_context_debt_key(neighbor_id, int(head_packet.context_bit)),
                    0.0,
                )
                branch_context_debt = state.branch_context_debt.get(
                    _branch_context_debt_key(neighbor_id, int(head_packet.context_bit)),
                    0.0,
                )
            local[f"branch_context_feedback_credit_{neighbor_id}"] = min(
                1.0,
                max(0.0, branch_context_credit),
            )
            local[f"branch_context_feedback_debt_{neighbor_id}"] = min(
                1.0,
                max(0.0, branch_context_debt),
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

    def score_packet(self, packet: SignalPacket) -> float:
        target_bits = _target_bits_for_task(
            packet.input_bits,
            context_bit=packet.context_bit,
            task_id=packet.task_id,
        )
        if target_bits is None:
            packet.target_bits = []
            packet.matched_target = None
            packet.bit_match_ratio = None
            packet.feedback_award = self.feedback_amount
            return self.feedback_amount

        packet.target_bits = list(target_bits)
        packet.bit_match_ratio = _bit_match_ratio(packet.payload_bits, packet.target_bits)
        packet.matched_target = packet.bit_match_ratio >= 1.0 - 1e-9
        packet.feedback_award = self.feedback_amount * packet.bit_match_ratio
        return packet.feedback_award

    def route_signal(
        self,
        node_id: str,
        neighbor_id: str,
        cost: float,
        *,
        transform_name: str | None = None,
    ) -> dict:
        if not self.route_available(node_id, neighbor_id, cost):
            return {"success": False, "cost": 0.0, "delivered": False}

        self._prioritize_inbox(node_id)
        packet = self.inboxes[node_id].pop(0)
        transform = _normalize_transform_name(transform_name)
        packet.payload_bits = _apply_transform(packet.payload_bits, transform)
        packet.transform_trace.append(transform)
        packet.hops.append(node_id)
        packet.edge_path.append(_edge_id(node_id, neighbor_id))
        packet.last_moved_cycle = self.current_cycle

        source_state = self.state_for(node_id)
        source_state.atp = max(0.0, source_state.atp - cost)
        source_state.routed_packets += 1
        if node_id == self.source_id:
            self._source_cycle_action_cost += cost

        if neighbor_id == self.sink_id:
            packet.hops.append(neighbor_id)
            packet.delivered = True
            packet.delivered_cycle = self.current_cycle
            feedback_award = self.score_packet(packet)
            self.delivered_packets.append(packet)
            if feedback_award > 0.0:
                self.pending_feedback.append(
                    FeedbackPulse(
                        packet_id=packet.packet_id,
                        edge_path=list(packet.edge_path),
                        amount=feedback_award,
                        transform_path=list(packet.transform_trace),
                        context_bit=packet.context_bit,
                        bit_match_ratio=float(packet.bit_match_ratio or 0.0),
                        matched_target=bool(packet.matched_target),
                    )
                )
            return {
                "success": True,
                "cost": cost,
                "delivered": True,
                "packet_id": packet.packet_id,
                "transform": transform,
                "feedback_award": feedback_award,
            }

        self.inboxes[neighbor_id].append(packet)
        self._prioritize_inbox(neighbor_id)
        self._record_inbox_pressure()
        return {
            "success": True,
            "cost": cost,
            "delivered": False,
            "packet_id": packet.packet_id,
            "transform": transform,
        }

    def inhibit_neighbor(self, node_id: str, neighbor_id: str) -> dict:
        if neighbor_id == self.sink_id or not self.inhibit_available(node_id):
            return {"success": False, "cost": 0.0}
        source_state = self.state_for(node_id)
        source_state.atp = max(0.0, source_state.atp - self.inhibit_cost)
        if node_id == self.source_id:
            self._source_cycle_action_cost += self.inhibit_cost
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
            source_id, neighbor_id = edge.split("->", 1)
            state = self.state_for(source_id)
            state.atp = min(state.max_atp, state.atp + pulse.amount)
            state.reward_buffer = min(state.max_atp, state.reward_buffer + pulse.amount)
            state.received_feedback += 1
            state.last_feedback_amount = pulse.amount
            state.last_match_ratio = pulse.bit_match_ratio
            transform_name = pulse.next_transform() or "identity"
            credit_signal = min(1.0, pulse.amount / max(self.feedback_amount, 1e-9))
            prior_credit = state.transform_credit.get(transform_name, 0.0)
            prior_debt = state.transform_debt.get(transform_name, 0.0)
            branch_key = _branch_debt_key(neighbor_id, transform_name)
            if pulse.context_bit is None:
                state.transform_credit[transform_name] = min(
                    1.0,
                    0.55 * prior_credit + 0.45 * credit_signal,
                )
                state.branch_transform_credit[branch_key] = min(
                    1.0,
                    0.55 * state.branch_transform_credit.get(branch_key, 0.0)
                    + 0.45 * credit_signal,
                )
                state.transform_debt[transform_name] = max(0.0, prior_debt * 0.65)
            else:
                context_key = _context_credit_key(transform_name, int(pulse.context_bit))
                context_branch_key = _context_branch_debt_key(
                    neighbor_id,
                    transform_name,
                    int(pulse.context_bit),
                )
                branch_context_key = _branch_context_debt_key(
                    neighbor_id,
                    int(pulse.context_bit),
                )
                prior_context_credit = state.context_transform_credit.get(context_key, 0.0)
                prior_branch_credit = state.branch_transform_credit.get(branch_key, 0.0)
                prior_context_branch_credit = state.context_branch_transform_credit.get(
                    context_branch_key,
                    0.0,
                )
                prior_context_debt = state.context_transform_debt.get(context_key, 0.0)
                prior_branch_debt = state.branch_transform_debt.get(branch_key, 0.0)
                prior_context_branch_debt = state.context_branch_transform_debt.get(
                    context_branch_key,
                    0.0,
                )
                prior_branch_context_credit = state.branch_context_credit.get(
                    branch_context_key,
                    0.0,
                )
                prior_branch_context_debt = state.branch_context_debt.get(
                    branch_context_key,
                    0.0,
                )
                match_ratio = max(0.0, min(1.0, pulse.bit_match_ratio))
                if match_ratio < TASK_CONTEXT_MATCH_FLOOR:
                    contradiction = (
                        TASK_CONTEXT_MATCH_FLOOR - match_ratio
                    ) / max(TASK_CONTEXT_MATCH_FLOOR, 1e-9)
                    residual_generic = 0.10 * credit_signal
                    residual_context = 0.05 * credit_signal
                    state.transform_credit[transform_name] = min(
                        1.0,
                        max(
                            residual_generic,
                            prior_credit * max(0.15, 0.58 - 0.24 * contradiction),
                        ),
                    )
                    state.context_transform_credit[context_key] = min(
                        1.0,
                        max(
                            residual_context,
                            prior_context_credit * max(0.05, 0.32 - 0.18 * contradiction),
                        ),
                    )
                    state.branch_transform_credit[branch_key] = min(
                        1.0,
                        max(
                            residual_context,
                            prior_branch_credit * max(0.08, 0.40 - 0.20 * contradiction),
                        ),
                    )
                    state.context_branch_transform_credit[context_branch_key] = min(
                        1.0,
                        max(
                            residual_context,
                            prior_context_branch_credit
                            * max(0.04, 0.28 - 0.16 * contradiction),
                        ),
                    )
                    state.branch_context_credit[branch_context_key] = min(
                        1.0,
                        max(
                            residual_context,
                            prior_branch_context_credit
                            * max(0.06, 0.34 - 0.20 * contradiction),
                        ),
                    )
                    debt_signal = max(contradiction, 1.0 - match_ratio)
                    stale_commitment = max(
                        prior_credit,
                        prior_context_credit,
                        prior_branch_credit,
                        prior_context_branch_credit,
                        prior_branch_context_credit,
                        prior_debt,
                        prior_context_debt,
                    )
                    if (
                        prior_credit >= DEBT_ACTIVATION_CREDIT
                        or prior_context_credit >= DEBT_ACTIVATION_CONTEXT_CREDIT
                        or prior_branch_credit >= DEBT_ACTIVATION_CONTEXT_CREDIT
                        or prior_context_branch_credit >= DEBT_ACTIVATION_CONTEXT_CREDIT
                        or prior_branch_context_credit >= DEBT_ACTIVATION_CONTEXT_CREDIT
                        or prior_debt >= DEBT_ACTIVATION_EXISTING
                        or prior_context_debt >= DEBT_ACTIVATION_EXISTING
                        or prior_branch_debt >= DEBT_ACTIVATION_EXISTING
                        or prior_context_branch_debt >= DEBT_ACTIVATION_EXISTING
                        or prior_branch_context_debt >= DEBT_ACTIVATION_EXISTING
                    ):
                        state.transform_debt[transform_name] = min(
                            1.0,
                            0.70 * prior_debt + 0.30 * debt_signal,
                        )
                        state.context_transform_debt[context_key] = min(
                            1.0,
                            0.55 * prior_context_debt + 0.45 * debt_signal,
                        )
                        state.branch_transform_debt[branch_key] = min(
                            1.0,
                            0.65 * prior_branch_debt + 0.35 * debt_signal,
                        )
                        state.context_branch_transform_debt[context_branch_key] = min(
                            1.0,
                            0.50 * prior_context_branch_debt + 0.50 * debt_signal,
                        )
                        state.branch_context_debt[branch_context_key] = min(
                            1.0,
                            0.45 * prior_branch_context_debt + 0.55 * debt_signal,
                        )
                    else:
                        mild_decay = max(0.0, 0.55 - 0.20 * stale_commitment)
                        state.transform_debt[transform_name] = max(
                            0.0,
                            prior_debt * mild_decay,
                        )
                        state.context_transform_debt[context_key] = max(
                            0.0,
                            prior_context_debt * max(0.45, mild_decay - 0.05),
                        )
                        state.branch_transform_debt[branch_key] = max(
                            0.0,
                            prior_branch_debt * 0.60,
                        )
                        state.context_branch_transform_debt[context_branch_key] = max(
                            0.0,
                            prior_context_branch_debt * 0.55,
                        )
                        state.branch_context_debt[branch_context_key] = max(
                            0.0,
                            prior_branch_context_debt * 0.52,
                        )
                else:
                    quality_credit = _quality_scaled_credit(match_ratio)
                    generic_mix = 0.18 + 0.12 * quality_credit
                    context_mix = 0.42 + 0.23 * quality_credit
                    branch_mix = 0.30 + 0.18 * quality_credit
                    context_branch_mix = 0.46 + 0.24 * quality_credit
                    branch_context_mix = 0.34 + 0.24 * quality_credit
                    effective_credit = 0.55 * credit_signal + 0.45 * quality_credit
                    state.transform_credit[transform_name] = min(
                        1.0,
                        (1.0 - generic_mix) * prior_credit + generic_mix * effective_credit,
                    )
                    state.context_transform_credit[context_key] = min(
                        1.0,
                        (1.0 - context_mix) * prior_context_credit + context_mix * effective_credit,
                    )
                    state.branch_transform_credit[branch_key] = min(
                        1.0,
                        (1.0 - branch_mix) * prior_branch_credit + branch_mix * effective_credit,
                    )
                    state.context_branch_transform_credit[context_branch_key] = min(
                        1.0,
                        (1.0 - context_branch_mix) * prior_context_branch_credit
                        + context_branch_mix * effective_credit,
                    )
                    state.branch_context_credit[branch_context_key] = min(
                        1.0,
                        (1.0 - branch_context_mix) * prior_branch_context_credit
                        + branch_context_mix * effective_credit,
                    )
                    state.transform_debt[transform_name] = max(
                        0.0,
                        prior_debt * max(0.10, 0.55 - 0.30 * quality_credit),
                    )
                    state.context_transform_debt[context_key] = max(
                        0.0,
                        prior_context_debt * max(0.05, 0.45 - 0.35 * quality_credit),
                    )
                    state.branch_transform_debt[branch_key] = max(
                        0.0,
                        prior_branch_debt * max(0.10, 0.55 - 0.35 * quality_credit),
                    )
                    state.context_branch_transform_debt[context_branch_key] = max(
                        0.0,
                        prior_context_branch_debt * max(0.05, 0.40 - 0.35 * quality_credit),
                    )
                    state.branch_context_debt[branch_context_key] = max(
                        0.0,
                        prior_branch_context_debt * max(0.04, 0.38 - 0.30 * quality_credit),
                    )
            delivered.append(
                {
                    "packet_id": pulse.packet_id,
                    "edge": edge,
                    "node_id": source_id,
                    "amount": pulse.amount,
                    "transform": transform_name,
                    "context_bit": pulse.context_bit,
                    "bit_match_ratio": pulse.bit_match_ratio,
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
            state.last_feedback_amount *= 0.85
            state.last_match_ratio *= 0.90
            for transform_name in list(state.transform_credit.keys()):
                state.transform_credit[transform_name] *= 0.92
                if state.transform_credit[transform_name] < 1e-4:
                    del state.transform_credit[transform_name]
            for transform_name in list(state.transform_debt.keys()):
                state.transform_debt[transform_name] *= 0.90
                if state.transform_debt[transform_name] < 1e-4:
                    del state.transform_debt[transform_name]
            for key in list(state.context_transform_credit.keys()):
                state.context_transform_credit[key] *= 0.94
                if state.context_transform_credit[key] < 1e-4:
                    del state.context_transform_credit[key]
            for key in list(state.branch_transform_credit.keys()):
                state.branch_transform_credit[key] *= 0.93
                if state.branch_transform_credit[key] < 1e-4:
                    del state.branch_transform_credit[key]
            for key in list(state.context_branch_transform_credit.keys()):
                state.context_branch_transform_credit[key] *= 0.95
                if state.context_branch_transform_credit[key] < 1e-4:
                    del state.context_branch_transform_credit[key]
            for key in list(state.context_transform_debt.keys()):
                state.context_transform_debt[key] *= 0.92
                if state.context_transform_debt[key] < 1e-4:
                    del state.context_transform_debt[key]
            for key in list(state.branch_transform_debt.keys()):
                state.branch_transform_debt[key] *= 0.90
                if state.branch_transform_debt[key] < 1e-4:
                    del state.branch_transform_debt[key]
            for key in list(state.context_branch_transform_debt.keys()):
                state.context_branch_transform_debt[key] *= 0.91
                if state.context_branch_transform_debt[key] < 1e-4:
                    del state.context_branch_transform_debt[key]
            for key in list(state.branch_context_debt.keys()):
                state.branch_context_debt[key] *= 0.92
                if state.branch_context_debt[key] < 1e-4:
                    del state.branch_context_debt[key]
            for key in list(state.branch_context_credit.keys()):
                state.branch_context_credit[key] *= 0.94
                if state.branch_context_credit[key] < 1e-4:
                    del state.branch_context_credit[key]
        self._update_admission_substrate()
        self._expire_stale_packets()
        self._admit_source_packets()
        self._prioritize_all_queues()
        self._record_inbox_pressure()

    def snapshot(self) -> dict:
        scored_packets = [
            packet for packet in self.delivered_packets if packet.bit_match_ratio is not None
        ]
        exact_matches = sum(1 for packet in scored_packets if packet.matched_target)
        partial_matches = sum(
            1
            for packet in scored_packets
            if packet.bit_match_ratio is not None and 0.0 < packet.bit_match_ratio < 1.0
        )
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
            "source_admission_support": round(self.admission_substrate.support, 4),
            "source_admission_velocity": round(self.admission_substrate.velocity, 4),
            "last_source_efficiency": round(self.last_source_efficiency, 4),
            "exact_matches": exact_matches,
            "partial_matches": partial_matches,
            "mean_bit_accuracy": round(
                sum(packet.bit_match_ratio for packet in scored_packets)
                / max(len(scored_packets), 1),
                4,
            ),
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
            "admission_substrate": self.admission_substrate.export_state(),
            "last_source_efficiency": self.last_source_efficiency,
            "source_efficiency_history": list(self.source_efficiency_history),
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
        self.admission_substrate = AdmissionSubstrate.from_state(
            payload.get("admission_substrate")
        )
        self.last_source_efficiency = float(payload.get("last_source_efficiency", 0.0))
        self.source_efficiency_history = [
            float(value) for value in payload.get("source_efficiency_history", [])
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

        ceiling = self.source_admission_max_rate
        if ceiling is None:
            ceiling = self.inbox_capacity

        return self.admission_substrate.allowance(
            available_slots=available_slots,
            backlog_pressure=min(1.0, backlog / max(self.inbox_capacity, 1)),
            atp_ratio=atp_ratio,
            reward_ratio=reward_ratio,
            inbox_load=inbox_load,
            oldest_age=oldest_age,
            feedback_pending=feedback_pending,
            min_rate=self.source_admission_min_rate,
            max_rate=ceiling,
        )

    def _update_admission_substrate(self) -> None:
        if self.source_admission_policy != "adaptive":
            return
        observation = self.observe_local(self.source_id)
        source_state = self.state_for(self.source_id)
        feedback_gained = source_state.received_feedback - self._source_cycle_start_feedback
        routed_packets = source_state.routed_packets - self._source_cycle_start_routed
        feedback_energy = max(0.0, feedback_gained) * self.feedback_amount
        action_cost = max(0.0, self._source_cycle_action_cost)
        net_energy = feedback_energy - action_cost
        update = self.admission_substrate.update(
            backlog_before=self._source_cycle_start_backlog,
            backlog_after=len(self.source_buffer),
            admitted=self.last_source_admission,
            routed_packets=max(0, routed_packets),
            feedback_gained=max(0, feedback_gained),
            action_cost=action_cost,
            feedback_energy=feedback_energy,
            net_energy=net_energy,
            inbox_load=observation.get("inbox_load", 0.0),
            oldest_age=observation.get("oldest_packet_age", 0.0),
            atp_ratio=observation.get("atp_ratio", 0.0),
        )
        self.last_source_efficiency = update["efficiency_signal"]
        self.source_efficiency_history.append(self.last_source_efficiency)

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

    def inject_signal_specs(self, signal_specs: Iterable[SignalSpec]) -> None:
        packets = [
            self.environment.create_packet(
                cycle=self.global_cycle,
                input_bits=spec.input_bits,
                payload_bits=spec.payload_bits,
                context_bit=spec.context_bit,
                task_id=spec.task_id,
            )
            for spec in signal_specs
        ]
        self.environment.inject_packets(packets, cycle=self.global_cycle)

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
        for node_id, agent in self.agents.items():
            local_feedback = [
                event for event in feedback if event.get("node_id") == node_id
            ]
            if local_feedback:
                agent.absorb_feedback(local_feedback)
        self.environment.tick(self.global_cycle)
        return {
            "cycle": self.global_cycle,
            "entries": cycle_entries,
            "feedback": feedback,
            "snapshot": self.environment.snapshot(),
        }

    def summarize(self) -> dict[str, object]:
        delivered = self.environment.delivered_packets
        scored_packets = [
            packet for packet in delivered if packet.bit_match_ratio is not None
        ]
        context_breakdown = {}
        transform_counts = {}
        task_diagnostics = self._task_diagnostics(scored_packets)
        for packet in scored_packets:
            context_key = f"context_{packet.context_bit}"
            stats = context_breakdown.setdefault(
                context_key,
                {"count": 0, "exact_matches": 0, "bit_accuracy_total": 0.0},
            )
            stats["count"] += 1
            stats["exact_matches"] += 1 if packet.matched_target else 0
            stats["bit_accuracy_total"] += float(packet.bit_match_ratio or 0.0)
            if packet.transform_trace:
                transform_key = packet.transform_trace[-1]
                transform_counts[transform_key] = transform_counts.get(transform_key, 0) + 1
        for stats in context_breakdown.values():
            stats["mean_bit_accuracy"] = round(
                stats["bit_accuracy_total"] / max(stats["count"], 1),
                4,
            )
            del stats["bit_accuracy_total"]
        exact_matches = sum(1 for packet in scored_packets if packet.matched_target)
        partial_matches = sum(
            1
            for packet in scored_packets
            if packet.bit_match_ratio is not None and 0.0 < packet.bit_match_ratio < 1.0
        )
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
        route_entries = [
            entry
            for entry in all_entries
            if entry.action.startswith("route:") or entry.action.startswith("route_transform:")
        ]
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
            "source_admission_support": round(self.environment.admission_substrate.support, 4),
            "source_admission_velocity": round(self.environment.admission_substrate.velocity, 4),
            "mean_source_efficiency": round(
                sum(self.environment.source_efficiency_history)
                / max(len(self.environment.source_efficiency_history), 1),
                4,
            ),
            "last_source_efficiency": round(self.environment.last_source_efficiency, 4),
            "exact_matches": exact_matches,
            "partial_matches": partial_matches,
            "mean_bit_accuracy": round(
                sum(packet.bit_match_ratio for packet in scored_packets)
                / max(len(scored_packets), 1),
                4,
            ),
            "mean_feedback_award": round(
                sum(packet.feedback_award for packet in delivered) / max(len(delivered), 1),
                4,
            ),
            "overload_events": self.environment.overload_events,
            "max_inbox_depth": self.environment.max_inbox_depth,
            "max_source_backlog": self.environment.max_source_backlog,
            "context_breakdown": context_breakdown,
            "final_transform_counts": transform_counts,
            "task_diagnostics": task_diagnostics,
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
            "action_supports": {
                node_id: {
                    neighbor_id: {
                        transform_name: round(
                            agent.substrate.action_support(neighbor_id, transform_name),
                            4,
                        )
                        for transform_name in ("identity", "rotate_left_1", "xor_mask_1010", "xor_mask_0101")
                    }
                    for neighbor_id in agent.neighbor_ids
                }
                for node_id, agent in self.agents.items()
            },
            "context_action_supports": {
                node_id: {
                    neighbor_id: {
                        f"context_{context_bit}": {
                            transform_name: round(
                                agent.substrate.action_support(
                                    neighbor_id,
                                    transform_name,
                                    context_bit,
                                ),
                                4,
                            )
                            for transform_name in ("identity", "rotate_left_1", "xor_mask_1010", "xor_mask_0101")
                        }
                        for context_bit in (0, 1)
                    }
                    for neighbor_id in agent.neighbor_ids
                }
                for node_id, agent in self.agents.items()
            },
            "substrate_maintenance": {
                node_id: {
                    key: round(value, 4)
                    for key, value in agent.substrate.maintenance_metrics().items()
                }
                for node_id, agent in self.agents.items()
            },
        }

    def _task_diagnostics(self, scored_packets: Sequence[SignalPacket]) -> dict[str, object]:
        diagnostics: dict[str, object] = {
            "packets_evaluated": len(scored_packets),
            "contexts": {},
            "overall": {
                "exact_matches": 0,
                "partial_matches": 0,
                "zero_matches": 0,
                "identity_fallbacks": 0,
                "wrong_transform_family": 0,
                "stale_context_support_suspicions": 0,
                "branch_counts": {},
                "mismatch_branch_counts": {},
                "final_transform_counts": {},
                "mismatch_transform_counts": {},
            },
        }
        overall = diagnostics["overall"]
        for packet in scored_packets:
            context_key = f"context_{packet.context_bit}"
            expected_transform = _expected_transform_for_task(packet.task_id, packet.context_bit)
            final_transform = packet.transform_trace[-1] if packet.transform_trace else "identity"
            first_hop = self._packet_first_hop(packet)
            stats = diagnostics["contexts"].setdefault(
                context_key,
                {
                    "count": 0,
                    "expected_transform": expected_transform,
                    "exact_matches": 0,
                    "partial_matches": 0,
                    "zero_matches": 0,
                    "identity_fallbacks": 0,
                    "wrong_transform_family": 0,
                    "stale_context_support_suspicions": 0,
                    "mean_bit_accuracy_total": 0.0,
                    "final_transform_counts": {},
                    "mismatch_transform_counts": {},
                    "branch_counts": {},
                    "mismatch_branch_counts": {},
                },
            )
            stats["count"] += 1
            stats["mean_bit_accuracy_total"] += float(packet.bit_match_ratio or 0.0)
            self._increment_count(stats["final_transform_counts"], final_transform)
            self._increment_count(overall["final_transform_counts"], final_transform)
            self._increment_count(stats["branch_counts"], first_hop)
            self._increment_count(overall["branch_counts"], first_hop)

            bit_match_ratio = float(packet.bit_match_ratio or 0.0)
            if packet.matched_target:
                stats["exact_matches"] += 1
                overall["exact_matches"] += 1
            elif bit_match_ratio > 0.0:
                stats["partial_matches"] += 1
                overall["partial_matches"] += 1
            else:
                stats["zero_matches"] += 1
                overall["zero_matches"] += 1

            if not packet.matched_target:
                self._increment_count(stats["mismatch_transform_counts"], final_transform)
                self._increment_count(overall["mismatch_transform_counts"], final_transform)
                self._increment_count(stats["mismatch_branch_counts"], first_hop)
                self._increment_count(overall["mismatch_branch_counts"], first_hop)
                if final_transform == "identity":
                    stats["identity_fallbacks"] += 1
                    overall["identity_fallbacks"] += 1
                if expected_transform is not None and final_transform != expected_transform:
                    stats["wrong_transform_family"] += 1
                    overall["wrong_transform_family"] += 1
                    if self._suspect_stale_context_support(
                        packet,
                        expected_transform=expected_transform,
                        final_transform=final_transform,
                        first_hop=first_hop,
                    ):
                        stats["stale_context_support_suspicions"] += 1
                        overall["stale_context_support_suspicions"] += 1

        for stats in diagnostics["contexts"].values():
            stats["mean_bit_accuracy"] = round(
                stats["mean_bit_accuracy_total"] / max(stats["count"], 1),
                4,
            )
            del stats["mean_bit_accuracy_total"]
        diagnostics["admission"] = {
            "mean_source_admission": round(
                self.environment.admitted_packets
                / max(1, self.global_cycle - self.session_start_cycle),
                4,
            ),
            "max_source_backlog": self.environment.max_source_backlog,
            "mean_latency": round(
                sum(
                    max(0, (packet.delivered_cycle or self.global_cycle) - packet.created_cycle)
                    for packet in scored_packets
                )
                / max(len(scored_packets), 1),
                4,
            ),
            "overload_events": self.environment.overload_events,
        }
        return diagnostics

    @staticmethod
    def _increment_count(counter: dict[str, int], key: str) -> None:
        counter[key] = counter.get(key, 0) + 1

    def _packet_first_hop(self, packet: SignalPacket) -> str:
        if not packet.edge_path:
            return "none"
        edge = packet.edge_path[0]
        if "->" not in edge:
            return "none"
        source_id, neighbor_id = edge.split("->", 1)
        if source_id != self.environment.source_id:
            return "none"
        return neighbor_id

    def _suspect_stale_context_support(
        self,
        packet: SignalPacket,
        *,
        expected_transform: str,
        final_transform: str,
        first_hop: str,
    ) -> bool:
        if (
            packet.context_bit is None
            or first_hop == "none"
            or self.environment.source_id not in self.agents
        ):
            return False
        source_agent = self.agents[self.environment.source_id]
        if first_hop not in source_agent.neighbor_ids:
            return False
        chosen_support = source_agent.substrate.action_support(
            first_hop,
            final_transform,
            packet.context_bit,
        )
        expected_support = source_agent.substrate.action_support(
            first_hop,
            expected_transform,
            packet.context_bit,
        )
        return chosen_support > expected_support + 0.05

    def run_workload(
        self,
        *,
        cycles: int,
        initial_packets: int,
        packet_schedule: Dict[int, int] | None = None,
        initial_signal_specs: Sequence[SignalSpec] | None = None,
        signal_schedule_specs: Dict[int, Sequence[SignalSpec]] | None = None,
    ) -> dict[str, object]:
        if initial_signal_specs:
            self.inject_signal_specs(initial_signal_specs)
        elif initial_packets > 0:
            self.inject_signal(count=initial_packets)
        schedule = dict(packet_schedule or {})
        signal_schedule = dict(signal_schedule_specs or {})
        reports = []
        for cycle_index in range(1, cycles + 1):
            scheduled_specs = signal_schedule.get(cycle_index)
            if scheduled_specs:
                self.inject_signal_specs(scheduled_specs)
            else:
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
            "admission_substrate": self.environment.admission_substrate.export_state(),
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
            "admission_substrate": self.environment.admission_substrate.export_state(),
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
        self.environment.admission_substrate = AdmissionSubstrate.from_state(
            manifest.get("admission_substrate")
        )
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
        self.environment.admission_substrate = AdmissionSubstrate.from_state(
            manifest.get("admission_substrate")
        )
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
