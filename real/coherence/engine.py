"""
Coherence Engine — endogenous P1–P6 scoring.

Computes a composite coherence score from REAL system state.  Every
dimension maps to one of the six relational primitives and is measured
from actual hardware readings via psutil.

The coherence score IS the evaluation function.  No external reward,
no supervisor, no labeled data.  The agent's only question is:
"am I maintaining coherent operation?"

GCO (Global Closure Operator) status: all six dimensions simultaneously
above threshold → the system has stabilized into self-consistent operation.

Designed with a pluggable scorer interface so cognitive-level scorers
can be added alongside system-level scorers as the architecture develops.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass
from typing import Dict, Optional, Callable

from real.coherence.biases import (
    FOUNDING_BIASES,
    THRESHOLDS,
    select_weights,
)
from real.coherence.regulatory_mesh import RegulatoryMesh


# ── System State Vector ──────────────────────────────────────────────
# Ground layer of the perceptual stack.  Reads real hardware state.

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


@dataclass
class SystemState:
    """
    Real system state read from hardware sensors.

    Every field comes from actual OS/hardware readings.
    If psutil is unavailable, returns conservative defaults.
    """
    timestamp: float = 0.0
    cpu_freq_ratio: float = 0.5       # current_freq / max_freq
    cpu_temp_ratio: float = 0.0       # current_temp / max_safe_temp
    cpu_load_avg: float = 0.0         # average CPU utilization [0, 1]
    memory_used_ratio: float = 0.0    # used / total
    memory_pressure: float = 0.0      # swap_used / swap_total
    process_count: int = 0            # number of running processes
    uptime_this_session: float = 0.0  # seconds since session start
    cycle_number: int = 0

    @classmethod
    def read(cls, cycle_number: int = 0, session_start: float = 0.0) -> "SystemState":
        """Read real system state.  Falls back to defaults without psutil."""
        now = time.time()
        if not _PSUTIL:
            return cls(
                timestamp=now,
                cpu_freq_ratio=0.5,
                cpu_load_avg=0.1,
                memory_used_ratio=0.5,
                process_count=50,
                uptime_this_session=now - session_start if session_start else 0,
                cycle_number=cycle_number,
            )

        # CPU frequency
        freq = psutil.cpu_freq()
        freq_ratio = (freq.current / freq.max) if (freq and freq.max > 0) else 0.5

        # CPU temperature (platform-dependent)
        temp_ratio = 0.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for entries in temps.values():
                    for t in entries:
                        if t.current > 0 and t.high and t.high > 0:
                            temp_ratio = max(temp_ratio, t.current / t.high)
        except (AttributeError, NotImplementedError):
            pass

        # CPU load
        cpu_load = psutil.cpu_percent(interval=0.05) / 100.0

        # Memory
        mem = psutil.virtual_memory()
        mem_ratio = mem.percent / 100.0
        swap = psutil.swap_memory()
        swap_ratio = (swap.percent / 100.0) if swap.total > 0 else 0.0

        # Processes
        proc_count = len(psutil.pids())

        return cls(
            timestamp=now,
            cpu_freq_ratio=freq_ratio,
            cpu_temp_ratio=temp_ratio,
            cpu_load_avg=cpu_load,
            memory_used_ratio=mem_ratio,
            memory_pressure=swap_ratio,
            process_count=proc_count,
            uptime_this_session=now - session_start if session_start else 0,
            cycle_number=cycle_number,
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "cpu_freq_ratio": self.cpu_freq_ratio,
            "cpu_temp_ratio": self.cpu_temp_ratio,
            "cpu_load_avg": self.cpu_load_avg,
            "memory_used_ratio": self.memory_used_ratio,
            "memory_pressure": self.memory_pressure,
            "process_count": self.process_count,
            "uptime": self.uptime_this_session,
            "cycle": self.cycle_number,
        }


# ── Scorer type ──────────────────────────────────────────────────────
# Each dimension scorer takes SystemState + optional history and
# returns a float in [0, 1].  This interface allows cognitive-level
# scorers to be added later.

DimensionScorer = Callable[["CoherenceEngine", SystemState], float]


# ── Coherence Engine ─────────────────────────────────────────────────

class CoherenceEngine:
    """
    Endogenous evaluation across six relational primitive dimensions.

    Scores are computed from real hardware state.  The composite score
    is a weighted average using the current founding bias profile.
    """

    # Dimension names, ordered by primitive
    DIMENSIONS = [
        "continuity",        # P1 Ontological
        "vitality",          # P2 Dynamical
        "contextual_fit",    # P3 Geometric/Causal
        "differentiation",   # P4 Symmetric/Constraint
        "accountability",    # P5 Epistemic
        "reflexivity",       # P6 Meta
    ]

    def __init__(self) -> None:
        self.session_start = time.time()
        self.cycle_number: int = 0
        self.prior_score: Optional[float] = None
        self._recent_states: list[SystemState] = []
        self._max_recent: int = 20
        self._log = None  # EpisodicLog reference, set by agent loop
        self._mesh = RegulatoryMesh(enabled=True)

    @property
    def mesh_enabled(self) -> bool:
        """Toggle the TCL regulatory mesh on/off (useful for A/B testing)."""
        return self._mesh.enabled

    @mesh_enabled.setter
    def mesh_enabled(self, value: bool) -> None:
        self._mesh.enabled = value

    def set_log(self, log) -> None:
        """Wire in the episodic log for reflexivity scoring."""
        self._log = log

    def read_state(self) -> SystemState:
        """Read real system state and track history."""
        state = SystemState.read(
            cycle_number=self.cycle_number,
            session_start=self.session_start,
        )
        self._recent_states.append(state)
        if len(self._recent_states) > self._max_recent:
            self._recent_states.pop(0)
        return state

    # ── Individual dimension scorers ──────────────────────────────────
    # Each returns a float in [0, 1].  Higher = more coherent.

    def score_continuity(self, state: SystemState) -> float:
        """
        P1 Ontological: Is operational identity stable over time?

        Measured as low variance in resource usage over recent history.
        High variance = ontological instability.  A new system with no
        history scores moderate.
        """
        if len(self._recent_states) < 3:
            return 0.5  # insufficient history

        loads = [s.cpu_load_avg for s in self._recent_states]
        mems = [s.memory_used_ratio for s in self._recent_states]

        load_var = _variance(loads)
        mem_var = _variance(mems)

        # Low variance → high continuity
        combined_var = (load_var + mem_var) / 2.0
        return max(0.0, min(1.0, 1.0 - combined_var * 10))

    def score_vitality(self, state: SystemState) -> float:
        """
        P2 Dynamical: Is energy expenditure productive?

        Inverted parabola: both idle (load ≈ 0) and fully loaded (≈ 1)
        are low vitality.  Productive middle range is optimal.
        Penalizes memory pressure as metabolic waste.

        CPU load is smoothed over the last 5 readings to prevent short
        bursts (e.g. digest_log hashing) from causing a single-cycle
        vitality spike that distorts selection and trail learning.
        """
        # Rolling mean over up to 5 recent states (Phase 3d: metabolic smoothing)
        if len(self._recent_states) >= 2:
            window = self._recent_states[-5:]
            load = _mean([s.cpu_load_avg for s in window])
        else:
            load = state.cpu_load_avg

        # Peak vitality at load ≈ 0.4
        vitality = 1.0 - ((load - 0.4) ** 2) / 0.25
        vitality = max(0.0, min(1.0, vitality))

        # Penalize memory pressure (always from current state — no smoothing)
        pressure_penalty = state.memory_pressure * 0.3
        return max(0.0, vitality - pressure_penalty)

    def score_contextual_fit(self, state: SystemState) -> float:
        """
        P3 Geometric/Causal: Is behavior appropriate to environment?

        Thermal state is the primary signal.  If temperature data is
        unavailable, use CPU frequency as a thermal proxy: when the chip
        throttles under load, freq/load ratio drops.
        """
        if state.cpu_temp_ratio > 0:
            # Direct thermal reading available
            return max(0.0, 1.0 - state.cpu_temp_ratio)
        else:
            # Thermal proxy: frequency under load
            load = max(state.cpu_load_avg, 0.1)
            proxy = state.cpu_freq_ratio / load
            # Clamp to [0, 1] — high proxy = chip not throttling = good fit
            return max(0.0, min(1.0, proxy * 0.7))

    def score_differentiation(self, state: SystemState) -> float:
        """
        P4 Symmetric/Constraint: Are process boundaries intact?

        Uses process count variance across recent history rather than
        swap pressure snapshot (fixing the known calibration issue from
        the original coherence engine).
        """
        if len(self._recent_states) < 3:
            return 0.5

        proc_counts = [s.process_count for s in self._recent_states]
        proc_var = _variance(proc_counts)

        # Normalize: typical process count variance.  Low variance = stable
        # boundaries.  Very high variance = boundary breakdown.
        normalized = proc_var / max(1.0, _mean(proc_counts))
        score = max(0.0, min(1.0, 1.0 - normalized * 5))

        # Also penalize swap pressure as constraint violation
        swap_penalty = state.memory_pressure * 0.2
        return max(0.0, score - swap_penalty)

    def score_accountability(self, state: SystemState) -> float:
        """
        P5 Epistemic: Is there causal traceability?

        Based on log maturity and recent action diversity.  An agent
        that rarely varies its actions has low epistemic signal.
        """
        # Score scales with available history (more history = more accountable)
        history_score = min(1.0, len(self._recent_states) / self._max_recent)
        return history_score * 0.8 + 0.2  # Floor at 0.2

    def score_reflexivity(self, state: SystemState) -> float:
        """
        P6 Meta: Can the system revise patterns after negative outcomes?

        Measures three components of actual reflexive capacity:

        1. Action revision: after a coherence dip (negative delta),
           did the agent switch to a different action next cycle?
        2. Recovery signal: after switching, did coherence improve?
        3. Introspection depth: has introspect been triggered?

        These are measured from the episodic log, not from hardware state.
        The reflexivity scorer is the only scorer that reads the log —
        because meta-level evaluation IS about the agent's own behavior.
        """
        if not self._log or self._log.size < 5:
            return 0.3  # Limited capacity to revise without data

        entries = self._log.recent(15)

        # Component 1: Action revision rate after dips
        # Count cycles where delta was negative AND the agent switched actions
        dips = 0
        revisions = 0
        for i in range(1, len(entries)):
            if entries[i-1].delta_coherence < -0.02:
                dips += 1
                if entries[i].action != entries[i-1].action:
                    revisions += 1

        revision_rate = revisions / max(dips, 1) if dips > 0 else 0.5

        # Component 2: Recovery after revision
        # When the agent DID switch after a dip, did coherence improve?
        recoveries = 0
        recovery_attempts = 0
        for i in range(1, len(entries)):
            if (entries[i-1].delta_coherence < -0.02
                    and entries[i].action != entries[i-1].action):
                recovery_attempts += 1
                if entries[i].delta_coherence > 0:
                    recoveries += 1

        recovery_rate = recoveries / max(recovery_attempts, 1) if recovery_attempts > 0 else 0.3

        # Component 3: Introspection depth
        # Has the agent used introspect? More uses = more meta-awareness.
        introspect_count = sum(1 for e in self._log.entries if e.action == "introspect")
        introspect_score = min(1.0, introspect_count / 5.0)

        # Weighted combination
        score = (
            revision_rate * 0.4
            + recovery_rate * 0.35
            + introspect_score * 0.25
        )
        return max(0.0, min(1.0, score))

    # ── Composite scoring ─────────────────────────────────────────────

    def score_all(self, state: SystemState) -> Dict[str, float]:
        """Score all six dimensions and apply the TCL regulatory mesh.

        Raw scores are computed independently per dimension, then the
        RegulatoryMesh applies tilt coupling between adjacent primitive
        pairs.  GCO status and composite scoring operate on the
        mesh-adjusted values.
        """
        raw = {
            "continuity":       self.score_continuity(state),
            "vitality":         self.score_vitality(state),
            "contextual_fit":   self.score_contextual_fit(state),
            "differentiation":  self.score_differentiation(state),
            "accountability":   self.score_accountability(state),
            "reflexivity":      self.score_reflexivity(state),
        }
        return self._mesh.apply(raw)

    def composite_score(
        self,
        dimensions: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Weighted average across dimensions."""
        if weights is None:
            weights = select_weights(
                cycle=self.cycle_number,
                thermal_ratio=self._recent_states[-1].cpu_temp_ratio
                if self._recent_states else 0.0,
            )
        total = 0.0
        weight_sum = 0.0
        for dim, score in dimensions.items():
            w = weights.get(dim, 0.15)
            total += score * w
            weight_sum += w
        return total / max(weight_sum, 0.001)

    def gco_status(self, dimensions: Dict[str, float]) -> str:
        """
        Global Closure Operator status.

        STABLE:     all dimensions above GCO threshold
        PARTIAL:    composite above threshold but not all dimensions
        DEGRADED:   composite below threshold
        CRITICAL:   composite below rest trigger
        """
        threshold = THRESHOLDS["gco_threshold"]
        rest_trigger = THRESHOLDS["rest_trigger"]
        composite = self.composite_score(dimensions)

        all_above = all(v >= threshold for v in dimensions.values())
        if all_above and composite >= threshold:
            return "STABLE"
        elif composite >= threshold:
            return "PARTIAL"
        elif composite >= rest_trigger:
            return "DEGRADED"
        else:
            return "CRITICAL"

    # ── Cycle management ──────────────────────────────────────────────

    def advance_cycle(self) -> None:
        """Increment cycle counter."""
        self.cycle_number += 1


# ── Utility functions ─────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / len(values)
