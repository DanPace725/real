from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .environment import NativeSubstrateSystem
from .models import SignalPacket
from .occupancy import OccupancyEpisode, OccupancyPacketSpec

OCCUPANCY_EXECUTION_SINK_ID = 'sink'
DEFAULT_CYCLES_PER_TIMESTEP = 4
DEFAULT_DRAIN_CYCLES = 12
DEFAULT_FEEDBACK_AMOUNT = 0.05


@dataclass(frozen=True)
class OccupancyEpisodeResult:
    example_index: int
    label: int
    predicted_label: int
    correct: bool
    decision_counts: Dict[str, int]
    delivered_packets: int
    dropped_packets: int
    routed_packets: int
    cycles_used: int
    feedback_events: int
    feedback_amount: float



def occupancy_execution_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], str, str]:
    adjacency = {
        'src_temperature': ('thermal',),
        'src_humidity': ('thermal', 'mixed_context'),
        'src_light': ('illumination', 'mixed_context'),
        'src_co2': ('air_quality', 'mixed_context'),
        'src_humidity_ratio': ('air_quality', 'thermal'),
        'thermal': ('evidence_occ', 'evidence_empty'),
        'illumination': ('evidence_occ', 'evidence_empty'),
        'air_quality': ('evidence_occ', 'evidence_empty'),
        'mixed_context': ('evidence_occ', 'evidence_empty'),
        'evidence_occ': (OCCUPANCY_EXECUTION_SINK_ID,),
        'evidence_empty': (OCCUPANCY_EXECUTION_SINK_ID,),
        OCCUPANCY_EXECUTION_SINK_ID: (),
    }
    positions = {
        'src_temperature': 0,
        'src_humidity': 0,
        'src_light': 0,
        'src_co2': 0,
        'src_humidity_ratio': 0,
        'thermal': 1,
        'illumination': 1,
        'air_quality': 1,
        'mixed_context': 1,
        'evidence_occ': 2,
        'evidence_empty': 2,
        OCCUPANCY_EXECUTION_SINK_ID: 3,
    }
    return adjacency, positions, 'src_temperature', OCCUPANCY_EXECUTION_SINK_ID



def build_occupancy_execution_system(*, selector_seed: int | None = 0) -> NativeSubstrateSystem:
    adjacency, positions, source_id, sink_id = occupancy_execution_topology()
    return NativeSubstrateSystem(
        adjacency=adjacency,
        positions=positions,
        source_id=source_id,
        sink_id=sink_id,
        selector_seed=selector_seed,
        source_sequence_context_enabled=False,
        latent_transfer_split_enabled=False,
    )



def _make_packet(system: NativeSubstrateSystem, spec: OccupancyPacketSpec, *, cycle: int) -> SignalPacket:
    packet_number = next(system.environment.packet_counter)
    packet_id = f'pkt-{packet_number}'
    return SignalPacket(
        packet_id=packet_id,
        origin=spec.source_id,
        target=system.environment.sink_id,
        created_cycle=cycle,
        input_bits=list(spec.signal.input_bits),
        payload_bits=list(spec.signal.payload_bits or spec.signal.input_bits),
        context_bit=spec.signal.context_bit,
        task_id=spec.signal.task_id,
        target_bits=list(spec.signal.target_bits or []),
    )



def inject_occupancy_timestep(
    system: NativeSubstrateSystem,
    packet_specs: Sequence[OccupancyPacketSpec],
    *,
    cycle: int,
) -> list[str]:
    packet_ids: list[str] = []
    for spec in packet_specs:
        packet = _make_packet(system, spec, cycle=cycle)
        packet.last_moved_cycle = cycle
        system.environment.inboxes[spec.source_id].append(packet)
        system.environment.total_injected += 1
        system.environment._prioritize_inbox(spec.source_id)
        packet_ids.append(packet.packet_id)
    system.environment._record_inbox_pressure()
    return packet_ids



def _decision_node(packet: SignalPacket) -> str | None:
    if not packet.edge_path:
        return None
    last_edge = packet.edge_path[-1]
    if '->' not in last_edge:
        return None
    source_id, _ = last_edge.split('->', 1)
    return source_id



def _packet_decision_label(packet: SignalPacket) -> int | None:
    decision_node = _decision_node(packet)
    if decision_node == 'evidence_occ':
        return 1
    if decision_node == 'evidence_empty':
        return 0
    return None



def _feedback_events_for_packet(
    packet: SignalPacket,
    *,
    label: int,
    feedback_amount: float,
) -> list[dict[str, object]]:
    packet_label = _packet_decision_label(packet)
    if packet_label is None or packet_label != label:
        return []
    events: list[dict[str, object]] = []
    transforms = list(packet.transform_trace)
    for reverse_index, edge in enumerate(reversed(packet.edge_path)):
        source_id, _ = edge.split('->', 1)
        transform_index = len(transforms) - 1 - reverse_index
        transform_name = transforms[transform_index] if 0 <= transform_index < len(transforms) else 'identity'
        events.append(
            {
                'node_id': source_id,
                'edge': edge,
                'transform': transform_name,
                'context_bit': packet.context_bit,
                'context_promotion_ready': packet.context_bit is not None,
                'amount': feedback_amount,
                'bit_match_ratio': 1.0,
            }
        )
    return events



def _apply_feedback_events(system: NativeSubstrateSystem, events: Sequence[dict[str, object]]) -> None:
    for event in events:
        node_id = str(event['node_id'])
        amount = float(event['amount'])
        state = system.environment.state_for(node_id)
        state.atp = min(state.max_atp, state.atp + amount)
        state.reward_buffer = min(state.max_atp, state.reward_buffer + amount)
        state.received_feedback += 1
        state.last_feedback_amount = amount
        state.last_match_ratio = float(event.get('bit_match_ratio', 0.0))
    for node_id, agent in system.agents.items():
        local_events = [event for event in events if event.get('node_id') == node_id]
        if local_events:
            agent.absorb_feedback(local_events)



def run_occupancy_episode(
    system: NativeSubstrateSystem,
    episode: OccupancyEpisode,
    *,
    cycles_per_timestep: int = DEFAULT_CYCLES_PER_TIMESTEP,
    drain_cycles: int = DEFAULT_DRAIN_CYCLES,
    feedback_amount: float = DEFAULT_FEEDBACK_AMOUNT,
) -> OccupancyEpisodeResult:
    start_cycle = system.global_cycle
    tracked_packet_ids: list[str] = []
    delivered_before = len(system.environment.delivered_packets)
    dropped_before = len(system.environment.dropped_packets)

    for timestep_packets in episode.timestep_packets:
        cycle = system.global_cycle + 1
        tracked_packet_ids.extend(inject_occupancy_timestep(system, timestep_packets, cycle=cycle))
        for _ in range(cycles_per_timestep):
            system.run_global_cycle()

    packet_id_set = set(tracked_packet_ids)
    for _ in range(drain_cycles):
        delivered_now = {
            packet.packet_id
            for packet in system.environment.delivered_packets[delivered_before:]
            if packet.packet_id in packet_id_set
        }
        dropped_now = {
            packet.packet_id
            for packet in system.environment.dropped_packets[dropped_before:]
            if packet.packet_id in packet_id_set
        }
        if len(delivered_now) + len(dropped_now) >= len(packet_id_set):
            break
        system.run_global_cycle()

    delivered_packets = [
        packet
        for packet in system.environment.delivered_packets[delivered_before:]
        if packet.packet_id in packet_id_set
    ]
    dropped_packets = [
        packet
        for packet in system.environment.dropped_packets[dropped_before:]
        if packet.packet_id in packet_id_set
    ]

    decision_counts = {'evidence_occ': 0, 'evidence_empty': 0}
    for packet in delivered_packets:
        decision_node = _decision_node(packet)
        if decision_node in decision_counts:
            decision_counts[decision_node] += 1

    feedback_events: list[dict[str, object]] = []
    if feedback_amount > 0.0:
        for packet in delivered_packets:
            feedback_events.extend(
                _feedback_events_for_packet(
                    packet,
                    label=episode.label,
                    feedback_amount=feedback_amount,
                )
            )
        if feedback_events:
            _apply_feedback_events(system, feedback_events)

    predicted_label = 1 if decision_counts['evidence_occ'] > decision_counts['evidence_empty'] else 0
    cycles_used = system.global_cycle - start_cycle
    return OccupancyEpisodeResult(
        example_index=episode.example_index,
        label=episode.label,
        predicted_label=predicted_label,
        correct=predicted_label == episode.label,
        decision_counts=decision_counts,
        delivered_packets=len(delivered_packets),
        dropped_packets=len(dropped_packets),
        routed_packets=len(packet_id_set),
        cycles_used=cycles_used,
        feedback_events=len(feedback_events),
        feedback_amount=sum(float(event['amount']) for event in feedback_events),
    )



def summarize_occupancy_results(results: Iterable[OccupancyEpisodeResult]) -> dict[str, float]:
    result_list = list(results)
    total = len(result_list)
    correct = sum(1 for result in result_list if result.correct)
    delivered = sum(result.delivered_packets for result in result_list)
    dropped = sum(result.dropped_packets for result in result_list)
    cycles = sum(result.cycles_used for result in result_list)
    occ_votes = sum(result.decision_counts['evidence_occ'] for result in result_list)
    empty_votes = sum(result.decision_counts['evidence_empty'] for result in result_list)
    feedback_events = sum(result.feedback_events for result in result_list)
    feedback_amount = sum(result.feedback_amount for result in result_list)
    return {
        'episodes': float(total),
        'accuracy': correct / max(total, 1),
        'mean_delivered_packets': delivered / max(total, 1),
        'mean_dropped_packets': dropped / max(total, 1),
        'mean_cycles_used': cycles / max(total, 1),
        'mean_occ_votes': occ_votes / max(total, 1),
        'mean_empty_votes': empty_votes / max(total, 1),
        'mean_feedback_events': feedback_events / max(total, 1),
        'mean_feedback_amount': feedback_amount / max(total, 1),
    }
