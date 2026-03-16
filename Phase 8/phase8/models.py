from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SignalPacket:
    packet_id: str
    origin: str
    target: str
    created_cycle: int
    hops: List[str] = field(default_factory=list)
    edge_path: List[str] = field(default_factory=list)
    delivered: bool = False
    delivered_cycle: int | None = None
    last_moved_cycle: int | None = None
    dropped_cycle: int | None = None
    drop_reason: str | None = None


@dataclass
class FeedbackPulse:
    packet_id: str
    edge_path: List[str]
    amount: float
    cursor: int = 0

    def next_edge(self) -> str | None:
        reverse_index = len(self.edge_path) - 1 - self.cursor
        if reverse_index < 0:
            return None
        return self.edge_path[reverse_index]

    def advance(self) -> None:
        self.cursor += 1

    @property
    def complete(self) -> bool:
        return self.cursor >= len(self.edge_path)


@dataclass
class NodeRuntimeState:
    node_id: str
    position: int
    atp: float
    max_atp: float
    reward_buffer: float = 0.0
    inhibited_for: int = 0
    routed_packets: int = 0
    received_feedback: int = 0
    rest_count: int = 0

    @property
    def dormant(self) -> bool:
        return self.atp <= 0.0
