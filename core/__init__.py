"""
real.core — Core relational substrate.

Entity-Relation-World graph and the Evaluator that processes it.
This is the agent's internal model of its physical situation.
"""

from real.core.primitives import RPPrimitive
from real.core.entity import Entity, EntityId
from real.core.relation import Relation, RelationId
from real.core.world import World
from real.core.evaluator import Evaluator

__all__ = [
    "RPPrimitive",
    "Entity", "EntityId",
    "Relation", "RelationId",
    "World",
    "Evaluator",
]
