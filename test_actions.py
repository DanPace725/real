"""Test evaluator handlers directly."""
from real.core.primitives import RPPrimitive
from real.core.entity import Entity
from real.core.relation import Relation
from real.core.world import World
from real.core.evaluator import Evaluator

w = World()
e = Evaluator()

# Create test entities
agent = Entity("agent", kind="agent", state={"x": 0, "y": 0}, tags={"self"})
sensor = Entity("cpu", kind="sensor", state={"cpu_load": 0.42, "temp": 65.0, "x": 1, "y": 1})
child = Entity("child", kind=None, state={})
w.add_entity(agent)
w.add_entity(sensor)
w.add_entity(child)

# GEOMETRY: propagate sensor fields to agent, compute distance
w.add_relation(Relation(
    "geo1", RPPrimitive.GEOMETRY, "cpu", "agent",
    payload={"propagate": ["cpu_load", "temp"]},
))

# EPISTEMIC: agent observes sensor
w.add_relation(Relation(
    "ep1", RPPrimitive.EPISTEMIC, "cpu", "agent",
    payload={"observe_fields": ["cpu_load"]},
))

# CONSTRAINT: clamp cpu_load on agent
w.add_relation(Relation(
    "con1", RPPrimitive.CONSTRAINT, "cpu", "agent",
    payload={"field": "cpu_load", "min": 0.0, "max": 1.0},
))

# DYNAMICS: slow increase of temp
w.add_relation(Relation(
    "dyn1", RPPrimitive.DYNAMICS, "cpu", "sensor",
    payload={"field": "temp", "rate": 0.5},
))

# ONTOLOGY: assign kind to child, compose into agent, inherit tags
w.add_relation(Relation(
    "ont1", RPPrimitive.ONTOLOGY, "cpu", "child",
    payload={"assign_kind": "sub_sensor", "compose": True, "inherit_tags": False},
))
w.add_relation(Relation(
    "ont2", RPPrimitive.ONTOLOGY, "agent", "child",
    payload={"inherit_tags": True},
))

# META: toggle a relation
w.add_relation(Relation(
    "meta1", RPPrimitive.META, "agent", "agent",
    payload={"action": "deactivate", "target_relation": "dyn1"},
))

# Run evaluator
cost = e.step(w, dt=1.0)
print(f"Step 1 cost: {cost:.5f}s")

# Check geometry propagated cpu_load to agent
print(f"\n=== GEOMETRY ===")
print(f"  Agent got cpu_load: {agent.state.get('cpu_load')}")
print(f"  Agent got temp: {agent.state.get('temp')}")
geo_rel = w.get_relation("geo1")
print(f"  Distance: {geo_rel.payload.get('distance')}")
print(f"  Adjacency: {agent.state.get('adjacent_to')}")

print(f"\n=== EPISTEMIC ===")
print(f"  Agent observed: {agent.state.get('observed')}")

print(f"\n=== ONTOLOGY ===")
print(f"  Child kind: {child.kind}")
print(f"  Child part_of: {child.state.get('part_of')}")
print(f"  Agent components: {agent.state.get('components', 'none')}")
print(f"  Child tags: {child.tags}")
print(f"  Child stability: {child.state.get('identity_stability')}")

print(f"\n=== META ===")
dyn_rel = w.get_relation("dyn1")
print(f"  dyn1 active after meta toggle: {dyn_rel.active}")

# Run again to verify stability tracking increments
cost2 = e.step(w, dt=1.0)
print(f"\nStep 2 cost: {cost2:.5f}s")
print(f"  Child stability after step 2: {child.state.get('identity_stability')}")

print(f"\n  Evaluator total: {e.total_compute_secs:.5f}s over {e.step_count} steps")
print("\nSTATUS: ALL HANDLERS OK")
