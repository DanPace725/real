from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


def basic_demo_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], str, str]:
    adjacency = {
        "n0": ("n1", "n2"),
        "n1": ("n3",),
        "n2": ("n3",),
        "n3": ("sink",),
    }
    positions = {
        "n0": 0,
        "n1": 1,
        "n2": 1,
        "n3": 2,
        "sink": 3,
    }
    return adjacency, positions, "n0", "sink"


def branch_pressure_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], str, str]:
    adjacency = {
        "n0": ("n1", "n2"),
        "n1": ("n3", "n4"),
        "n2": ("n4", "n5"),
        "n3": ("sink",),
        "n4": ("sink",),
        "n5": ("sink",),
    }
    positions = {
        "n0": 0,
        "n1": 1,
        "n2": 1,
        "n3": 2,
        "n4": 2,
        "n5": 2,
        "sink": 3,
    }
    return adjacency, positions, "n0", "sink"


def branch_pressure_workload() -> Tuple[int, int, Dict[int, int]]:
    cycles = 18
    initial_packets = 6
    packet_schedule = {
        4: 2,
        8: 2,
        12: 2,
    }
    return cycles, initial_packets, packet_schedule


def sustained_pressure_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], str, str]:
    return branch_pressure_topology()


def sustained_pressure_workload() -> Tuple[int, int, Dict[int, int]]:
    cycles = 24
    initial_packets = 8
    packet_schedule = {
        3: 3,
        6: 3,
        9: 3,
        12: 3,
        16: 2,
        20: 2,
    }
    return cycles, initial_packets, packet_schedule


def detour_resilience_topology() -> tuple[Dict[str, tuple[str, ...]], Dict[str, int], str, str]:
    adjacency = {
        "n0": ("n1", "n2"),
        "n1": ("n3",),
        "n2": ("n3", "n4"),
        "n3": ("n5",),
        "n4": ("n5",),
        "n5": ("sink",),
    }
    positions = {
        "n0": 0,
        "n1": 1,
        "n2": 1,
        "n3": 2,
        "n4": 2,
        "n5": 3,
        "sink": 4,
    }
    return adjacency, positions, "n0", "sink"


def detour_resilience_workload() -> Tuple[int, int, Dict[int, int]]:
    cycles = 22
    initial_packets = 5
    packet_schedule = {
        4: 2,
        7: 1,
        11: 2,
        16: 2,
    }
    return cycles, initial_packets, packet_schedule


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    description: str
    adjacency: Dict[str, tuple[str, ...]]
    positions: Dict[str, int]
    source_id: str
    sink_id: str
    cycles: int
    initial_packets: int
    packet_schedule: Dict[int, int]
    packet_ttl: int = 8
    source_admission_policy: str = "fixed"
    source_admission_rate: int | None = None
    source_admission_min_rate: int = 1
    source_admission_max_rate: int | None = None


def phase8_scenarios() -> Dict[str, ScenarioSpec]:
    basic_adjacency, basic_positions, basic_source, basic_sink = basic_demo_topology()
    branch_adjacency, branch_positions, branch_source, branch_sink = branch_pressure_topology()
    sustained_adjacency, sustained_positions, sustained_source, sustained_sink = sustained_pressure_topology()
    detour_adjacency, detour_positions, detour_source, detour_sink = detour_resilience_topology()

    return {
        "basic_demo": ScenarioSpec(
            name="basic_demo",
            description="Small four-hop bootstrap graph for quick smoke runs.",
            adjacency=basic_adjacency,
            positions=basic_positions,
            source_id=basic_source,
            sink_id=basic_sink,
            cycles=8,
            initial_packets=2,
            packet_schedule={4: 1},
            packet_ttl=8,
            source_admission_policy="adaptive",
            source_admission_rate=1,
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        ),
        "branch_pressure": ScenarioSpec(
            name="branch_pressure",
            description="Moderate branch competition with periodic bursts.",
            adjacency=branch_adjacency,
            positions=branch_positions,
            source_id=branch_source,
            sink_id=branch_sink,
            cycles=branch_pressure_workload()[0],
            initial_packets=branch_pressure_workload()[1],
            packet_schedule=branch_pressure_workload()[2],
            packet_ttl=8,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        ),
        "sustained_pressure": ScenarioSpec(
            name="sustained_pressure",
            description="Longer overload run that tests queueing, packet aging, and warm-start stability.",
            adjacency=sustained_adjacency,
            positions=sustained_positions,
            source_id=sustained_source,
            sink_id=sustained_sink,
            cycles=sustained_pressure_workload()[0],
            initial_packets=sustained_pressure_workload()[1],
            packet_schedule=sustained_pressure_workload()[2],
            packet_ttl=7,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        ),
        "detour_resilience": ScenarioSpec(
            name="detour_resilience",
            description="Longer path with branching detours to test persistent support beyond a single bottleneck.",
            adjacency=detour_adjacency,
            positions=detour_positions,
            source_id=detour_source,
            sink_id=detour_sink,
            cycles=detour_resilience_workload()[0],
            initial_packets=detour_resilience_workload()[1],
            packet_schedule=detour_resilience_workload()[2],
            packet_ttl=8,
            source_admission_policy="adaptive",
            source_admission_min_rate=1,
            source_admission_max_rate=2,
        ),
    }
