"""
World — the agent's internal relational model of its physical situation.

The World is a graph of Entities connected by Relations.  It represents
what the agent *knows* about the environment it is embedded in — hardware
sensors, filesystem terrain, memory entries, its own operational state.

This is NOT a simulation.  Every Entity should map to something real.
If the hardware is unplugged, the World should become stale and incoherent
because its sensor readings stop updating.

Provides O(1) lookups by entity id, relation id, and indexed queries
by primitive type and adjacency.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Set

from real.core.entity import Entity, EntityId
from real.core.primitives import RPPrimitive
from real.core.relation import Relation, RelationId


@dataclass
class World:
    """
    In-memory graph container for the agent's relational model.

    Maintains high-performance indexes by entity, relation, primitive,
    and adjacency to support real-time evaluation.
    """

    # ── Primary storage ───────────────────────────────────────────────
    entities:  Dict[EntityId, Entity]          = field(default_factory=dict)
    relations: Dict[RelationId, Relation]      = field(default_factory=dict)

    # ── Indexes ───────────────────────────────────────────────────────
    _by_entity:    Dict[EntityId, Set[RelationId]]    = field(default_factory=lambda: defaultdict(set))
    _by_primitive: Dict[RPPrimitive, Set[RelationId]] = field(default_factory=lambda: defaultdict(set))
    _adjacency:    Dict[EntityId, Set[EntityId]]      = field(default_factory=lambda: defaultdict(set))

    # ── Entity operations ─────────────────────────────────────────────

    def add_entity(self, entity: Entity) -> None:
        """Insert an entity.  Raises if id already exists."""
        if entity.id in self.entities:
            raise KeyError(f"Entity {entity.id!r} already exists")
        self.entities[entity.id] = entity

    def remove_entity(self, entity_id: EntityId) -> None:
        """Remove entity and all attached relations."""
        if entity_id not in self.entities:
            return
        # Remove attached relations
        for rid in list(self._by_entity.get(entity_id, [])):
            self.remove_relation(rid)
        del self.entities[entity_id]
        self._by_entity.pop(entity_id, None)
        self._adjacency.pop(entity_id, None)

    def get_entity(self, entity_id: EntityId) -> Optional[Entity]:
        """Return entity by id, or None."""
        return self.entities.get(entity_id)

    def has_entity(self, entity_id: EntityId) -> bool:
        return entity_id in self.entities

    def entities_by_kind(self, kind: str) -> list[Entity]:
        """Return all entities matching a kind."""
        return [e for e in self.entities.values() if e.kind == kind]

    def entities_by_tag(self, tag: str) -> list[Entity]:
        """Return all entities carrying a tag."""
        return [e for e in self.entities.values() if e.has_tag(tag)]

    # ── Relation operations ───────────────────────────────────────────

    def add_relation(self, relation: Relation) -> None:
        """Insert a relation.  Raises if id already exists."""
        if relation.id in self.relations:
            raise KeyError(f"Relation {relation.id!r} already exists")
        self.relations[relation.id] = relation
        self._index(relation)

    def remove_relation(self, relation_id: RelationId) -> None:
        """Remove a relation and clean up indexes."""
        rel = self.relations.pop(relation_id, None)
        if rel is not None:
            self._deindex(rel)

    def get_relation(self, relation_id: RelationId) -> Optional[Relation]:
        return self.relations.get(relation_id)

    # ── Queries ───────────────────────────────────────────────────────

    def relations_of(self, entity_id: EntityId) -> list[Relation]:
        """All relations attached to an entity (as source or target)."""
        return [
            self.relations[rid]
            for rid in self._by_entity.get(entity_id, set())
            if rid in self.relations
        ]

    def relations_by_primitive(self, primitive: RPPrimitive) -> list[Relation]:
        """All relations of a given primitive type."""
        return [
            self.relations[rid]
            for rid in self._by_primitive.get(primitive, set())
            if rid in self.relations
        ]

    def active_relations(self, primitive: Optional[RPPrimitive] = None) -> list[Relation]:
        """Active relations, optionally filtered by primitive."""
        if primitive is not None:
            return [r for r in self.relations_by_primitive(primitive) if r.active]
        return [r for r in self.relations.values() if r.active]

    def neighbors(
        self,
        entity_id: EntityId,
        primitive_filter: Optional[RPPrimitive] = None,
    ) -> list[Entity]:
        """Entities connected via relations (optionally filtered by primitive)."""
        if primitive_filter is None:
            neighbor_ids = self._adjacency.get(entity_id, set())
        else:
            neighbor_ids = set()
            for rid in self._by_entity.get(entity_id, set()):
                rel = self.relations.get(rid)
                if rel and rel.primitive == primitive_filter:
                    other = rel.target if rel.source == entity_id else rel.source
                    neighbor_ids.add(other)
        return [
            self.entities[eid]
            for eid in neighbor_ids
            if eid in self.entities
        ]

    # ── Stats ─────────────────────────────────────────────────────────

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def relation_count(self) -> int:
        return len(self.relations)

    @property
    def historical_relation_count(self) -> int:
        """Number of inactive (historical action-record) relations."""
        return sum(1 for r in self.relations.values() if not r.active)

    def summary(self) -> Dict[str, Any]:
        """Quick stats about the current world state."""
        by_prim = {
            p.value: len(self._by_primitive.get(p, set()))
            for p in RPPrimitive
        }
        return {
            "entities": self.entity_count,
            "relations": self.relation_count,
            "historical_relations": self.historical_relation_count,
            "by_primitive": by_prim,
        }

    # ── Consolidation ─────────────────────────────────────────────────

    def prune_historical(self, keep_last: int = 100) -> int:
        """
        Remove the oldest inactive (historical) relations, keeping only the
        ``keep_last`` most recent.

        Active relations (sensor, constraint, and other live relations) are
        never touched.  Only relations with ``active=False`` are candidates.

        Ordering uses the ``timestamp`` field in the relation payload when
        present (written by ActionExecutor._record_in_world).  Falls back to
        numeric extraction from ids of the form ``action_<N>`` so that older
        action records are still sorted correctly even if the payload field is
        absent (e.g. relations loaded from an old checkpoint).

        Returns
        -------
        int
            Number of relations removed.
        """
        # Collect inactive relations
        inactive = [r for r in self.relations.values() if not r.active]
        if len(inactive) <= keep_last:
            return 0  # Nothing to prune

        def _sort_key(rel: Relation) -> float:
            """Return a numeric sort key; lower = older."""
            ts = rel.payload.get("timestamp")
            if ts is not None:
                return float(ts)
            # Fallback: try to parse action_<N>
            rid = str(rel.id)
            if rid.startswith("action_"):
                try:
                    return float(rid.split("_", 1)[1])
                except (ValueError, IndexError):
                    pass
            return 0.0

        inactive_sorted = sorted(inactive, key=_sort_key)
        to_remove = inactive_sorted[: len(inactive_sorted) - keep_last]
        for rel in to_remove:
            self.remove_relation(rel.id)
        return len(to_remove)

    # ── Index maintenance ─────────────────────────────────────────────

    def _index(self, rel: Relation) -> None:
        self._by_entity[rel.source].add(rel.id)
        self._by_entity[rel.target].add(rel.id)
        self._by_primitive[rel.primitive].add(rel.id)
        self._adjacency[rel.source].add(rel.target)
        self._adjacency[rel.target].add(rel.source)

    def _deindex(self, rel: Relation) -> None:
        self._by_entity[rel.source].discard(rel.id)
        self._by_entity[rel.target].discard(rel.id)
        self._by_primitive[rel.primitive].discard(rel.id)
        # Adjacency: only remove if no other relation connects them
        other_rels = self._by_entity.get(rel.source, set()) & self._by_entity.get(rel.target, set())
        if not other_rels:
            self._adjacency[rel.source].discard(rel.target)
            self._adjacency[rel.target].discard(rel.source)

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire world state for persistence."""
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> World:
        """Restore from a serialized snapshot."""
        world = cls()
        for edata in data.get("entities", []):
            world.add_entity(Entity.from_dict(edata))
        for rdata in data.get("relations", []):
            world.add_relation(Relation.from_dict(rdata))
        return world
