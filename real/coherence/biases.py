"""
Founding biases and TCL operating window constants.

Founding biases are the initial field curvature — weight presets that
shape the agent's evaluation before it has learned anything.  They are
tilt-coupled (additive, not parametric) per TCL design constraints.

TCL constants define the operating window for stable laminated dynamics:
    - Viability floor:  minimum coupling for oscillation to exist
    - Chaos ceiling:    maximum before delay destabilizes
    - Parametric wall:  hard ceiling on reshape coupling
"""

from typing import Final


# ── TCL Operating Window Constants ────────────────────────────────────
# Derived from Temporal Constraint Lamination (macl repo).
# These constrain inter-layer coupling in the laminated architecture.

TCL_CONSTANTS: Final[dict[str, float]] = {
    "viability_floor":   0.757,    # √(2·z_eff / 3) — minimum tilt coupling
    "chaos_ceiling":     0.930,    # √(z_eff + ε) — maximum before delay destabilizes
    "parametric_wall":   0.289,    # 1/(2√3) — hard ceiling on reshape coupling
}

# The viable operating range for additive (tilt) coupling is narrow:
# only ~23% of the floor value.  This is a structural constraint, not
# a tuning parameter.


# ── Coherence Thresholds ──────────────────────────────────────────────

THRESHOLDS: Final[dict[str, float]] = {
    "gco_threshold":          0.65,    # composite score above this = approaching closure
    "rest_trigger":           0.40,    # composite score below this = enter rest cycle
    "thermal_stress_trigger": 0.80,    # thermal ratio above this = thermal stress mode
    "early_cycle_count":      20,      # cycles before switching from early to default weights
}


# ── Founding Biases (tilt-only field curvature) ───────────────────────
# Three weight profiles for different operational states.
# Weights determine relative importance of each P-dimension in the
# composite coherence score.  Sum to ~1.0 within each profile.

FOUNDING_BIASES: Final[dict[str, dict[str, float]]] = {

    # Thermal stress: contextual fit matters most — ignoring your actual
    # environment when hot is the most dangerous mistake.
    "thermal_stress": {
        "continuity":       0.10,
        "vitality":         0.15,
        "contextual_fit":   0.35,
        "differentiation":  0.15,
        "accountability":   0.15,
        "reflexivity":      0.10,
    },

    # Early cycles: exploration weighted.  System hasn't established
    # identity yet — vitality and accountability should dominate.
    "early_cycles": {
        "continuity":       0.10,
        "vitality":         0.25,
        "contextual_fit":   0.15,
        "differentiation":  0.15,
        "accountability":   0.25,
        "reflexivity":      0.10,
    },

    # Default: balanced with slight emphasis on continuity (stable identity)
    # and vitality (productive energy use).
    "default": {
        "continuity":       0.20,
        "vitality":         0.20,
        "contextual_fit":   0.15,
        "differentiation":  0.15,
        "accountability":   0.15,
        "reflexivity":      0.15,
    },
}


def select_weights(
    cycle: int,
    thermal_ratio: float = 0.0,
) -> dict[str, float]:
    """
    Select the appropriate weight profile based on current state.

    This is a lookup — not a computation.  The founding biases are
    tilt-only: they shift which dimension matters, without restructuring
    the scoring function itself (respecting the TCL parametric wall).
    """
    if thermal_ratio > THRESHOLDS["thermal_stress_trigger"]:
        return dict(FOUNDING_BIASES["thermal_stress"])
    elif cycle < THRESHOLDS["early_cycle_count"]:
        return dict(FOUNDING_BIASES["early_cycles"])
    else:
        return dict(FOUNDING_BIASES["default"])
