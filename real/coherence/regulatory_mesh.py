"""
TCL Regulatory Mesh — inter-dimensional tilt coupling.

Implements the tilt coupling layer described in the Phase 3 plan.  After
the six coherence dimensions are scored independently, the mesh applies
small additive adjustments (tilts) from stronger dimensions to weaker
adjacent ones — without restructuring any scoring function.

Coupling pairs (source → target) are derived from the E² primitive
adjacency structure:

    P1 Ontological (continuity)      →  P5 Epistemic (accountability)
        Stable identity enables causal traceability.
        A system that persists coherently can be held accountable.

    P2 Dynamical (vitality)          →  P6 Meta (reflexivity)
        Productive energy use enables behavioral revision.
        A system operating in its productive range has capacity for
        self-modification that an exhausted or idle system does not.

    P3 Geometric/Causal (contextual_fit)  →  P4 Constraint (differentiation)
        Appropriate environmental embedding enables boundary integrity.
        A system aware of its context can maintain its own constraints.

Coupling only activates when the SOURCE dimension is above the TCL
viability floor (0.757).  Below that floor the source itself is not
stable enough to lend energy to another dimension.

The tilt magnitude is bounded by the parametric wall (0.289), keeping
the operation firmly in tilt territory — never reshape.

All coupling is additive and one-directional.  The mesh is idempotent
when all dimensions are already equal or when the source is below floor.
"""

from __future__ import annotations

from typing import Dict

from real.coherence.biases import TCL_CONSTANTS


# ── Coupling table ─────────────────────────────────────────────────────────
# Each entry: (source_dim, target_dim)
# Derived from E² categorical primitive adjacency (see module docstring).

_COUPLING_PAIRS: tuple[tuple[str, str], ...] = (
    ("continuity",    "accountability"),   # P1 → P5
    ("vitality",      "reflexivity"),      # P2 → P6
    ("contextual_fit", "differentiation"), # P3 → P4
)


class RegulatoryMesh:
    """
    Applies tilt coupling between adjacent coherence dimensions.

    Instantiate once per ``CoherenceEngine`` and call ``apply()`` after
    ``score_all()`` returns the raw dimension dict.

    Parameters
    ----------
    enabled : bool
        Toggle the mesh on/off.  When False, ``apply()`` returns its
        input unchanged.  Useful for A/B comparison tests.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._viability_floor: float = TCL_CONSTANTS["viability_floor"]
        self._parametric_wall: float  = TCL_CONSTANTS["parametric_wall"]

    def apply(self, dimensions: Dict[str, float]) -> Dict[str, float]:
        """
        Return a copy of ``dimensions`` with tilt coupling applied.

        The original dict is not mutated.

        For each coupling pair ``(source, target)``:
          - Skip if source ≤ viability_floor (source is not stable enough).
          - Skip if target ≥ source (target needs no help).
          - Apply:  target += (source − target) × parametric_wall
          - Cap:    target ≤ source  (never overshoot the source).

        Returns
        -------
        dict[str, float]
            Adjusted dimension scores (all values remain in [0, 1]).
        """
        if not self.enabled:
            return dict(dimensions)

        result = dict(dimensions)

        for src_key, tgt_key in _COUPLING_PAIRS:
            src = result.get(src_key, 0.0)
            tgt = result.get(tgt_key, 0.0)

            # Only couple when source is above the viability floor
            if src <= self._viability_floor:
                continue

            # Only couple when the gap is positive (source stronger than target)
            gap = src - tgt
            if gap <= 0.0:
                continue

            tilt = gap * self._parametric_wall
            new_tgt = tgt + tilt

            # Hard cap: target cannot exceed source
            new_tgt = min(new_tgt, src)
            # Clamp to [0, 1] for safety
            new_tgt = max(0.0, min(1.0, new_tgt))

            result[tgt_key] = new_tgt

        return result

    def coupling_summary(self, before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
        """
        Return the delta applied by the mesh for each dimension.
        Useful for logging and debugging.
        """
        return {
            dim: round(after.get(dim, 0.0) - before.get(dim, 0.0), 6)
            for dim in after
        }

    def __repr__(self) -> str:
        return (
            f"RegulatoryMesh(enabled={self.enabled}, "
            f"floor={self._viability_floor}, "
            f"wall={self._parametric_wall})"
        )
