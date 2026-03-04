"""
The Six Relational Primitives — the irreducible interaction vocabulary.

Derived from the E² (Essence of Existence) framework.  Every relation in
the system is tagged with exactly one primitive, and the evaluator dispatches
to the corresponding handler.  The primitives are jointly sufficient and
individually irreducible: removing any one collapses the system's capacity
to model reality.

Evaluation order follows the canonical 6-phase tick from the RPE:
    GEOMETRY → CONSTRAINT → EPISTEMIC → DYNAMICS → META → CLOSURE
"""

from enum import Enum
from typing import Final


class RPPrimitive(str, Enum):
    """
    The six relational primitives that tag every relation.

    P1  ONTOLOGY    identity, composition, categorization — "what exists"
    P2  DYNAMICS    change, influence, processes — "how it evolves"
    P3  GEOMETRY    adjacency, topology, causal/temporal ordering — "where/when"
    P4  CONSTRAINT  invariants, limits, boundaries — "what's allowed"
    P5  EPISTEMIC   observation, visibility, information — "what's knowable"
    P6  META        transformations on relations — "how rules compose"
    """

    ONTOLOGY   = "ontology"
    DYNAMICS   = "dynamics"
    GEOMETRY   = "geometry"
    CONSTRAINT = "constraint"
    EPISTEMIC  = "epistemic"
    META       = "meta"

    @property
    def description(self) -> str:
        """Human-friendly description of this primitive."""
        return _DESCRIPTIONS[self]

    @property
    def eval_priority(self) -> int:
        """Canonical evaluation order (lower = earlier in the tick)."""
        return _EVAL_ORDER[self]


# ── Descriptions ──────────────────────────────────────────────────────────

_DESCRIPTIONS: Final[dict["RPPrimitive", str]] = {
    RPPrimitive.ONTOLOGY:   "Identity, composition, categorization",
    RPPrimitive.DYNAMICS:   "Change, influence, processes",
    RPPrimitive.GEOMETRY:   "Adjacency, topology, causal/temporal ordering",
    RPPrimitive.CONSTRAINT: "Invariants, limits, allowed/forbidden regions",
    RPPrimitive.EPISTEMIC:  "Observation, visibility, information/entropy",
    RPPrimitive.META:       "Transformations on relations",
}

# ── Canonical evaluation order (RPE 6-phase tick) ────────────────────────
# GEOMETRY first (spatial/causal context before anything else),
# CONSTRAINT second (enforce invariants), EPISTEMIC third (what's visible),
# DYNAMICS fourth (state changes), META fifth (rules about rules),
# then a final closure pass.

_EVAL_ORDER: Final[dict["RPPrimitive", int]] = {
    RPPrimitive.GEOMETRY:   0,
    RPPrimitive.CONSTRAINT: 1,
    RPPrimitive.EPISTEMIC:  2,
    RPPrimitive.DYNAMICS:   3,
    RPPrimitive.META:       4,
    RPPrimitive.ONTOLOGY:   5,   # ontological updates last (identity settled)
}
