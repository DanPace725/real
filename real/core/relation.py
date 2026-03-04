"""
Relation — a typed, directional link between two Entities.

Every relation is tagged with one of the six relational primitives and
carries a payload of parameters.  Relations are the agent's vocabulary
for describing *what is happening* in its environment and *what it did*.

Examples:
    Relation("r1", GEOMETRY,   "agent",    "terrain_a", {"position": [0,0]})
    Relation("r2", DYNAMICS,   "cpu_sensor","agent",    {"cpu_load": 0.42})
    Relation("r3", EPISTEMIC,  "agent",    "log_42",   {"action": "introspect"})
    Relation("r4", CONSTRAINT, "agent",    "agent",    {"mode": "rest"})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from real.core.entity import EntityId
from real.core.primitives import RPPrimitive


RelationId = str | int


@dataclass
class Relation:
    """
    A directional, typed link between two entities.

    Attributes
    ----------
    id : RelationId
        Globally unique identifier.
    primitive : RPPrimitive
        Which of the six primitives this relation enacts.
    source : EntityId
        Origin entity.
    target : EntityId
        Destination entity.
    payload : dict
        Arbitrary parameters — semantics depend on the primitive handler.
    active : bool
        Toggle without deleting.  Inactive relations are skipped by the
        evaluator but preserved in the graph for history.
    """

    id: RelationId
    primitive: RPPrimitive
    source: EntityId
    target: EntityId
    payload: Dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def __repr__(self) -> str:
        state = "" if self.active else " [inactive]"
        return (
            f"Relation({self.id!r}, {self.primitive.value}, "
            f"{self.source!r} → {self.target!r}{state})"
        )

    # ── Control ───────────────────────────────────────────────────────

    def toggle(self, value: bool | None = None) -> None:
        """Toggle or explicitly set the active flag."""
        self.active = (not self.active) if value is None else bool(value)

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "primitive": self.primitive.value,
            "source": self.source,
            "target": self.target,
            "payload": dict(self.payload),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Relation:
        return cls(
            id=data["id"],
            primitive=RPPrimitive(data["primitive"]),
            source=data["source"],
            target=data["target"],
            payload=dict(data.get("payload", {})),
            active=bool(data.get("active", True)),
        )
