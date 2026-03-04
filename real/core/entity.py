"""
Entity — the basic unit of identity in the World graph.

An Entity is anything the agent can name, perceive, or act upon:
the agent itself, a terrain location, a sensor reading, a memory node.
Entities carry mutable state and tags for fast selection.

Entities in REAL represent *real things* — a CPU sensor, a filesystem path,
a log entry.  They are the agent's internal representation of its embedded
situation, not simulated objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


EntityId = str | int


@dataclass(eq=False)
class Entity:
    """
    Minimal entity structure.

    Attributes
    ----------
    id : EntityId
        Globally unique identifier.
    kind : str | None
        Classification (e.g., "agent", "terrain", "sensor", "memory").
    state : dict
        Arbitrary key/value map — the entity's observable properties.
    tags : set[str]
        Labels for fast filtering (e.g., "physical", "internal").
    """

    id: EntityId
    kind: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    # ── Identity ──────────────────────────────────────────────────────

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __repr__(self) -> str:
        kind = f" ({self.kind})" if self.kind else ""
        return f"Entity({self.id!r}{kind})"

    # ── State access ──────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Return state value for *key*, or *default* if missing."""
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a state value."""
        self.state[key] = value

    # ── Tags ──────────────────────────────────────────────────────────

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_tag(self, tag: str) -> None:
        self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        self.tags.discard(tag)

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Snapshot-friendly dictionary."""
        return {
            "id": self.id,
            "kind": self.kind,
            "state": dict(self.state),
            "tags": sorted(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entity:
        """Restore from a snapshot dictionary."""
        return cls(
            id=data["id"],
            kind=data.get("kind"),
            state=dict(data.get("state", {})),
            tags=set(data.get("tags", [])),
        )
