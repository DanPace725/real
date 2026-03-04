"""
Evaluator — processes the World graph each tick.

The evaluator iterates active relations in canonical primitive order
(GEOMETRY → CONSTRAINT → EPISTEMIC → DYNAMICS → META → ONTOLOGY)
and dispatches each to the appropriate handler.

Wall-clock timing is built in: every step() call measures real elapsed
time, which feeds compute-as-ATP — the genuine metabolic cost of
maintaining the agent's internal model.

Handlers are pluggable: pass custom handlers at construction to override
defaults.  Default handlers are minimal stubs that can be extended as
the system develops.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, Optional

from real.core.primitives import RPPrimitive
from real.core.relation import Relation
from real.core.world import World


# ── Type alias for handler functions ──────────────────────────────────
Handler = Callable[[World, Relation, float], None]


# ── Default handlers (minimal stubs) ─────────────────────────────────
# Each handler receives the world, the relation being processed, and dt.
# Handlers mutate the world in-place.

def _handle_geometry(world: World, rel: Relation, dt: float) -> None:
    """
    P3 — spatial/causal context propagation.

    Geometry relations encode adjacency, position, and causal ordering
    between entities.  The handler:

    1. Propagates position/location state from source to target if
       the payload specifies {"propagate": ["field1", "field2"]}.
    2. Computes distance metrics between entities that have position state.
    3. Tracks causal ordering — which entity was updated more recently —
       by comparing timestamps.
    4. Updates adjacency metadata on both entities.

    This is how the agent's internal model stays aligned with physical
    reality: sensor entities update from real hardware, then geometry
    relations propagate that context to the agent entity.
    """
    source = world.get_entity(rel.source)
    target = world.get_entity(rel.target)
    if not source or not target:
        return

    # 1. Propagate specified fields (e.g., sensor readings → agent)
    propagate = rel.payload.get("propagate")
    if propagate:
        for field in propagate:
            if field in source.state:
                target.state[field] = source.state[field]

    # 2. Position-based distance (if entities have x, y coordinates)
    sx = source.state.get("x")
    sy = source.state.get("y", 0)
    tx = target.state.get("x")
    ty = target.state.get("y", 0)
    if sx is not None and tx is not None:
        dist = ((sx - tx) ** 2 + (sy - ty) ** 2) ** 0.5
        rel.payload["distance"] = round(dist, 4)

    # 3. Causal ordering — track which side was updated more recently
    s_ts = source.state.get("last_updated", 0)
    t_ts = target.state.get("last_updated", 0)
    if s_ts > 0 or t_ts > 0:
        rel.payload["causal_direction"] = (
            "source_leads" if s_ts >= t_ts else "target_leads"
        )

    # 4. Adjacency metadata on entities
    source.state.setdefault("adjacent_to", set())
    target.state.setdefault("adjacent_to", set())
    if isinstance(source.state["adjacent_to"], set):
        source.state["adjacent_to"].add(target.id)
    if isinstance(target.state["adjacent_to"], set):
        target.state["adjacent_to"].add(source.id)

    # Mark last geometry update time
    import time as _time
    rel.payload["last_eval"] = _time.time()


def _handle_constraint(world: World, rel: Relation, dt: float) -> None:
    """P4 — enforce invariants and limits."""
    source = world.get_entity(rel.source)
    target = world.get_entity(rel.target)
    if not source or not target:
        return
    # Clamp: if payload specifies {field, min, max}, enforce on target
    field_name = rel.payload.get("field")
    if field_name and field_name in target.state:
        val = target.state[field_name]
        if isinstance(val, (int, float)):
            lo = rel.payload.get("min")
            hi = rel.payload.get("max")
            if lo is not None and val < lo:
                target.state[field_name] = lo
            if hi is not None and val > hi:
                target.state[field_name] = hi


def _handle_epistemic(world: World, rel: Relation, dt: float) -> None:
    """P5 — observation, visibility, information flow."""
    # Copy observed fields from source to target's 'observed' state
    source = world.get_entity(rel.source)
    target = world.get_entity(rel.target)
    if not source or not target:
        return
    fields = rel.payload.get("observe_fields")
    if fields:
        observed = target.state.setdefault("observed", {})
        for f in fields:
            if f in source.state:
                observed[f] = source.state[f]
        # Track observation freshness
        import time as _time
        observed["_last_observed"] = _time.time()


def _handle_dynamics(world: World, rel: Relation, dt: float) -> None:
    """P2 — state changes, evolution, energy flows."""
    target = world.get_entity(rel.target)
    if not target:
        return
    # Apply rate-based updates: {field, rate} → target.state[field] += rate * dt
    field_name = rel.payload.get("field")
    rate = rel.payload.get("rate")
    if field_name and rate is not None and field_name in target.state:
        val = target.state[field_name]
        if isinstance(val, (int, float)):
            target.state[field_name] = val + rate * dt


def _handle_meta(world: World, rel: Relation, dt: float) -> None:
    """P6 — rules about rules.  Activate, deactivate, or retarget relations."""
    action = rel.payload.get("action")
    target_rel_id = rel.payload.get("target_relation")
    if action and target_rel_id:
        target_rel = world.get_relation(target_rel_id)
        if target_rel:
            if action == "activate":
                target_rel.active = True
            elif action == "deactivate":
                target_rel.active = False
            elif action == "toggle":
                target_rel.toggle()


def _handle_ontology(world: World, rel: Relation, dt: float) -> None:
    """
    P1 — identity and composition management.

    Ontology relations encode "what something is" and how entities
    compose into larger wholes.  The handler:

    1. Kind propagation: if payload has {"assign_kind": "sensor"},
       update the target entity's kind.
    2. Composition: if payload has {"compose": true}, the source
       is treated as a component of the target.  The target's state
       gets a "components" set tracking its parts.
    3. Tag inheritance: if payload has {"inherit_tags": true}, the
       target inherits all tags from the source.
    4. Identity stability tracking: increments a counter on the
       entity tracking how many ticks it has maintained its current
       kind.  High stability = ontological continuity.
    """
    source = world.get_entity(rel.source)
    target = world.get_entity(rel.target)
    if not source or not target:
        return

    # 1. Kind assignment
    new_kind = rel.payload.get("assign_kind")
    if new_kind:
        old_kind = target.kind
        target.kind = new_kind
        if old_kind != new_kind:
            target.state["kind_changed_at"] = dt
            target.state["identity_stability"] = 0
        else:
            target.state["identity_stability"] = (
                target.state.get("identity_stability", 0) + 1
            )

    # 2. Composition — source is a component of target
    if rel.payload.get("compose"):
        components = target.state.setdefault("components", set())
        if isinstance(components, set):
            components.add(source.id)
        # Mark source as composed into target
        source.state["part_of"] = target.id

    # 3. Tag inheritance
    if rel.payload.get("inherit_tags"):
        for tag in source.tags:
            target.add_tag(tag)

    # 4. Identity stability (even without kind change)
    if not new_kind:
        target.state["identity_stability"] = (
            target.state.get("identity_stability", 0) + 1
        )


# ── Default handler map ──────────────────────────────────────────────

_DEFAULT_HANDLERS: Dict[RPPrimitive, Handler] = {
    RPPrimitive.GEOMETRY:   _handle_geometry,
    RPPrimitive.CONSTRAINT: _handle_constraint,
    RPPrimitive.EPISTEMIC:  _handle_epistemic,
    RPPrimitive.DYNAMICS:   _handle_dynamics,
    RPPrimitive.META:       _handle_meta,
    RPPrimitive.ONTOLOGY:   _handle_ontology,
}


# ── Evaluator ────────────────────────────────────────────────────────

class Evaluator:
    """
    Processes the World graph by dispatching active relations to handlers
    in canonical primitive order.

    Attributes
    ----------
    handlers : dict[RPPrimitive, Handler]
        Map of primitive → handler function.
    last_step_duration : float
        Wall-clock seconds taken by the most recent step().
        This IS the compute-as-ATP signal.
    total_compute_secs : float
        Cumulative wall-clock time across all steps.
    step_count : int
        Number of steps completed.
    """

    def __init__(
        self,
        handlers: Optional[Dict[RPPrimitive, Handler]] = None,
    ) -> None:
        self.handlers = {**_DEFAULT_HANDLERS, **(handlers or {})}
        self.last_step_duration: float = 0.0
        self.total_compute_secs: float = 0.0
        self.step_count: int = 0

    def step(self, world: World, dt: float = 1.0) -> float:
        """
        Run one evaluation tick.

        Processes all active relations in canonical primitive order.
        Returns the wall-clock duration of the step in seconds.
        """
        t0 = time.perf_counter()

        # Gather active relations, sort by primitive eval priority
        active = [r for r in world.relations.values() if r.active]
        active.sort(key=lambda r: r.primitive.eval_priority)

        # Dispatch each relation to its handler
        for rel in active:
            handler = self.handlers.get(rel.primitive)
            if handler:
                handler(world, rel, dt)

        elapsed = time.perf_counter() - t0
        self.last_step_duration = elapsed
        self.total_compute_secs += elapsed
        self.step_count += 1
        return elapsed

    @property
    def mean_step_cost(self) -> float:
        """Average wall-clock cost per step (metabolic efficiency indicator)."""
        if self.step_count == 0:
            return 0.0
        return self.total_compute_secs / self.step_count

    @property
    def compute_ratio(self) -> float:
        """
        Fraction of total elapsed time spent computing.
        Only meaningful if tracked alongside real wall-clock session time.
        """
        return self.total_compute_secs
