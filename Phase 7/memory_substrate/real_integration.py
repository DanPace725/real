"""Phase 3: Wire substrate into the REAL tuple.

Provides substrate-aware wrappers for each REAL component:
  - SubstrateObservationAdapter: modulates observation quality by slow-layer state
  - SubstrateActionBackend: adds invest/maintain actions to the vocabulary
  - SubstrateCoherenceModel: feeds substrate health into reflexivity
  - SubstrateCFARSelector: GUIDED mode targets slow-layer gaps
  - SubstrateEngine: orchestrates substrate within the REAL cycle
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_phase4_root = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_phase4_root) not in sys.path:
    sys.path.insert(0, str(_phase4_root))

from real_core.types import ActionOutcome, CycleEntry, DimensionScores, GCOStatus
from real_core.memory import EpisodicMemory
from real_core.mesh import TiltRegulatoryMesh
from real_core.selector import CFARSelector, SelectionMode

from .substrate import (
    DIMENSIONS, MemorySubstrate, SubstrateConfig, INVEST_INCREMENT,
    ConstraintPattern,
)


# ------------------------------------------------------------------
# Observation wrapper: slow layer modulates epistemic access
# ------------------------------------------------------------------

class SubstrateObservationAdapter:
    """Wraps any observation adapter. Degrades observation quality for
    dimensions without slow-layer support (adds noise). Dimensions with
    strong slow-layer infrastructure see the environment more clearly.

    Trajectory-aware: negative velocity (decaying support) reduces clarity
    even before the threshold crossing. The agent experiences the world
    becoming harder to read as infrastructure erodes — making decay
    perceptible through the observation function, not through engineered
    rules about when to maintain.
    """

    def __init__(
        self,
        inner,
        substrate: MemorySubstrate,
        noise_scale: float = 0.12,
        base_clarity: float = 0.35,
        velocity_sensitivity: float = 3.0,
        seed: Optional[int] = None,
    ):
        self.inner = inner
        self.substrate = substrate
        self.noise_scale = noise_scale
        self.base_clarity = base_clarity
        self.velocity_sensitivity = velocity_sensitivity
        self.rng = random.Random(seed)

    def observe(self, cycle: int) -> Dict[str, float]:
        raw = self.inner.observe(cycle)
        modulated = {}
        for key, value in raw.items():
            if key in DIMENSIONS:
                support = self.substrate.slow.get(key, 0.0)
                is_active = self.substrate.is_active(key)
                velocity = self.substrate.slow_velocity.get(key, 0.0)

                clarity = self.base_clarity + (0.65 * support if is_active else 0.0)

                if velocity < 0:
                    decay_penalty = min(0.25, abs(velocity) * self.velocity_sensitivity)
                    clarity -= decay_penalty

                clarity += self.substrate.pattern_dim_modulation.get(key, 0.0)

                clarity = max(0.10, min(clarity, 0.97))
                noise = self.rng.gauss(0, self.noise_scale * (1.0 - clarity))
                modulated[key] = max(0.0, min(1.0, value + noise))
            else:
                modulated[key] = value
        return modulated


# ------------------------------------------------------------------
# Action wrapper: adds invest/maintain to the vocabulary
# ------------------------------------------------------------------

DEFAULT_DOMAIN_ATP = {
    "rest": 0.00,
    "scan": 0.03,
    "introspect": 0.06,
}
DEFAULT_DOMAIN_ATP_FALLBACK = 0.02


class SubstrateActionBackend:
    """Wraps any action backend. Adds substrate investment and maintenance
    actions to the vocabulary. Every action has an explicit ATP cost used
    for budget tracking."""

    def __init__(
        self,
        inner,
        substrate: MemorySubstrate,
        domain_atp_costs: Optional[Dict[str, float]] = None,
    ):
        self.inner = inner
        self.substrate = substrate
        self.domain_atp = domain_atp_costs or dict(DEFAULT_DOMAIN_ATP)

    def available_actions(self, history_size: int) -> List[str]:
        base = self.inner.available_actions(history_size)
        extra = []
        if self.substrate.active_count() > 0:
            extra.append("maintain_substrate")
        for dim in DIMENSIONS:
            if self.substrate.slow.get(dim, 0.0) < 0.85:
                extra.append(f"invest_{dim}")
        return base + extra

    def estimate_atp(self, action: str) -> float:
        """Estimated ATP cost before execution."""
        if action == "maintain_substrate":
            return sum(
                self.substrate.maintain_cost(d)
                for d in DIMENSIONS if self.substrate.is_active(d)
            )
        if action.startswith("invest_"):
            dim = action[len("invest_"):]
            if dim in DIMENSIONS:
                return self.substrate.write_cost(dim)
            return float("inf")
        return self.domain_atp.get(action, DEFAULT_DOMAIN_ATP_FALLBACK)

    def execute(self, action: str) -> ActionOutcome:
        if action == "maintain_substrate":
            atp = self.substrate.maintain_all(atp_budget=100.0)
            return ActionOutcome(
                success=atp > 0,
                result={"atp_spent": atp, "maintained": self.substrate.active_count()},
                cost_secs=atp,
            )
        if action.startswith("invest_"):
            dim = action[len("invest_"):]
            if dim not in DIMENSIONS:
                return ActionOutcome(success=False, cost_secs=0.0)
            cost = self.substrate.write_slow(dim, atp_budget=100.0)
            if cost is not None:
                return ActionOutcome(
                    success=True,
                    result={"dimension": dim, "atp_spent": cost,
                            "new_value": self.substrate.slow[dim]},
                    cost_secs=cost,
                )
            return ActionOutcome(success=False, cost_secs=0.0)
        outcome = self.inner.execute(action)
        atp = self.domain_atp.get(action, DEFAULT_DOMAIN_ATP_FALLBACK)
        return ActionOutcome(
            success=outcome.success,
            result=outcome.result,
            cost_secs=atp,
        )


# ------------------------------------------------------------------
# Coherence wrapper: substrate health feeds into scoring
# ------------------------------------------------------------------

class SubstrateCoherenceModel:
    """Wraps any coherence model. Adds substrate health as a second-order
    signal feeding into reflexivity. Also adjusts observation-dependent
    dimensions based on substrate coupling quality."""

    def __init__(
        self,
        inner,
        substrate: MemorySubstrate,
        substrate_weight: float = 0.25,
    ):
        self.inner = inner
        self.substrate = substrate
        self.substrate_weight = substrate_weight

    @property
    def dimension_names(self):
        return self.inner.dimension_names

    def score(
        self, state_after: Dict[str, float], history: List[CycleEntry]
    ) -> DimensionScores:
        base = self.inner.score(state_after, history)

        coupling = self.substrate.coupling_score()
        active_ratio = self.substrate.active_count() / len(DIMENSIONS)
        health = (coupling * 0.6 + active_ratio * 0.4)

        w = self.substrate_weight
        if "reflexivity" in base:
            base["reflexivity"] = base["reflexivity"] * (1 - w) + health * w

        return base

    def composite(self, dimensions: DimensionScores) -> float:
        return self.inner.composite(dimensions)

    def gco_status(
        self, dimensions: DimensionScores, coherence: float
    ) -> GCOStatus:
        return self.inner.gco_status(dimensions, coherence)


# ------------------------------------------------------------------
# Selector: pass-through to CFAR — substrate actions in vocabulary
# ------------------------------------------------------------------

class SubstrateCFARSelector:
    """Thin wrapper around CFARSelector. Does not override selection logic.

    Substrate actions (invest_*, maintain_substrate) are in the action
    vocabulary via SubstrateActionBackend. The CFAR selector discovers
    them through FLUCTUATION, learns their value through trail data in
    CONSTRAINT mode, and targets weak dimensions in GUIDED mode. No
    hardcoded investment policy — the agent learns organically whether
    infrastructure investment pays off at the current budget level.
    """

    def __init__(
        self,
        inner: CFARSelector,
        substrate: MemorySubstrate,
    ):
        self.inner = inner
        self.substrate = substrate

    def select(
        self, available: List[str], history: List[CycleEntry]
    ) -> Tuple[str, str]:
        return self.inner.select(available, history)


# ------------------------------------------------------------------
# Substrate Engine: REAL cycle with substrate integration
# ------------------------------------------------------------------

@dataclass
class SubstrateSessionSummary:
    session_id: int
    cycles: int
    mean_coherence: float
    final_coherence: float
    gco_counts: Dict[str, int]
    final_substrate: dict
    action_counts: Dict[str, int]
    atp_spent: float = 0.0
    atp_budget: float = 0.0
    forced_rest_cycles: int = 0


class SubstrateEngine:
    """REAL engine with integrated memory substrate and metabolic budget.

    Extends the standard cycle with:
      - Substrate-modulated observation (O depends on slow layer)
      - Substrate actions in the vocabulary (invest, maintain)
      - Substrate health in coherence scoring (Phi includes substrate)
      - Substrate decay each cycle (slow layer ticks)
      - Substrate persistence across sessions
      - Per-session ATP budget (actions filtered by affordability)
    """

    def __init__(
        self,
        observer,
        actions,
        coherence,
        substrate_config: Optional[SubstrateConfig] = None,
        selector: Optional[CFARSelector] = None,
        mesh: Optional[TiltRegulatoryMesh] = None,
        memory: Optional[EpisodicMemory] = None,
        seed: Optional[int] = None,
        session_budget: float = float("inf"),
        domain_atp_costs: Optional[Dict[str, float]] = None,
    ):
        self.substrate = MemorySubstrate(
            config=substrate_config or SubstrateConfig()
        )

        self.observer = SubstrateObservationAdapter(
            observer, self.substrate, seed=seed
        )
        self.actions = SubstrateActionBackend(
            actions, self.substrate, domain_atp_costs=domain_atp_costs,
        )
        self.coherence = SubstrateCoherenceModel(coherence, self.substrate)

        base_selector = selector or CFARSelector()
        self.selector = SubstrateCFARSelector(base_selector, self.substrate)

        self.mesh = mesh or TiltRegulatoryMesh()
        self.memory = memory or EpisodicMemory(maxlen=500)
        self._prior_coherence: Optional[float] = None

        self.session_budget = session_budget
        self.atp_remaining = session_budget
        self._atp_spent = 0.0
        self._forced_rest = 0

    def _affordable_actions(self, all_actions: List[str]) -> List[str]:
        """Filter to actions the agent can afford right now."""
        affordable = [
            a for a in all_actions
            if self.actions.estimate_atp(a) <= self.atp_remaining + 1e-9
        ]
        if not affordable:
            affordable = ["rest"]
            self._forced_rest += 1
        return affordable

    def run_cycle(self, cycle: int) -> CycleEntry:
        before = self.observer.observe(cycle)

        all_actions = self.actions.available_actions(len(self.memory.entries))
        affordable = self._affordable_actions(all_actions)
        action, mode = self.selector.select(affordable, self.memory.entries)
        outcome = self.actions.execute(action)

        atp_cost = outcome.cost_secs
        self.atp_remaining = max(0.0, self.atp_remaining - atp_cost)
        self._atp_spent += atp_cost

        after = self.observer.observe(cycle)

        raw_dims = self.coherence.score(after, self.memory.entries)
        dims = self.mesh.apply(raw_dims)
        coherence_val = self.coherence.composite(dims)
        delta = (
            0.0
            if self._prior_coherence is None
            else coherence_val - self._prior_coherence
        )
        self._prior_coherence = coherence_val
        gco = self.coherence.gco_status(dims, coherence_val)

        entry = CycleEntry(
            cycle=cycle,
            action=action,
            mode=mode,
            state_before=before,
            state_after=after,
            dimensions=dims,
            coherence=coherence_val,
            delta=delta,
            gco=gco,
            cost_secs=atp_cost,
        )
        self.memory.record(entry)

        self.substrate.update_dim_context(dims)
        self.substrate.update_fast(after)
        self.substrate.tick()

        return entry

    def _promote_patterns(self):
        """Extract constraint patterns from recent episodic history and
        promote them to the substrate. Called after consolidation.

        Positive patterns: windows of sustained high coherence.
        Negative patterns: the state at the start of coherence decline
        sequences — the configuration the agent should learn to recognize
        before the decline completes.
        """
        entries = self.memory.entries
        if len(entries) < 12:
            return

        recent = entries[-min(40, len(entries)):]
        mean_coh = sum(e.coherence for e in recent) / len(recent)

        high = [e for e in recent if e.coherence > max(mean_coh + 0.05, 0.70)]
        if len(high) >= 4:
            sig = {}
            trends = {}
            for d in DIMENSIONS:
                vals = [e.dimensions.get(d, 0.5) for e in high]
                sig[d] = sum(vals) / len(vals)
                if len(vals) >= 3:
                    half = len(vals) // 2
                    trends[d] = (
                        sum(vals[half:]) / max(len(vals) - half, 1)
                        - sum(vals[:half]) / max(half, 1)
                    )
                else:
                    trends[d] = 0.0
            self.substrate.add_pattern(ConstraintPattern(
                dim_scores=sig, dim_trends=trends,
                valence=0.8, strength=0.5,
                coherence_level=sum(e.coherence for e in high) / len(high),
                source="attractor",
            ))

        low = [e for e in recent if e.coherence < max(mean_coh - 0.08, 0.55)]
        if len(low) >= 3:
            sig = {}
            trends = {}
            for d in DIMENSIONS:
                vals = [e.dimensions.get(d, 0.5) for e in low]
                sig[d] = sum(vals) / len(vals)
                if len(vals) >= 3:
                    half = len(vals) // 2
                    trends[d] = (
                        sum(vals[half:]) / max(len(vals) - half, 1)
                        - sum(vals[:half]) / max(half, 1)
                    )
                else:
                    trends[d] = 0.0
            self.substrate.add_pattern(ConstraintPattern(
                dim_scores=sig, dim_trends=trends,
                valence=-0.6, strength=0.4,
                coherence_level=sum(e.coherence for e in low) / len(low),
                source="trough",
            ))

    def run_session(
        self, cycles: int = 50, consolidate_on: str = "rest"
    ) -> SubstrateSessionSummary:
        self.atp_remaining = self.session_budget
        self._atp_spent = 0.0
        self._forced_rest = 0

        counts = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        coherence_sum = 0.0
        action_counts: Dict[str, int] = {}

        for i in range(1, cycles + 1):
            entry = self.run_cycle(i)
            counts[entry.gco.value] += 1
            coherence_sum += entry.coherence
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1

            if entry.action == consolidate_on and len(self.memory.entries) > 40:
                self.memory.consolidate_three_tier()
                self._promote_patterns()

        final = self.memory.entries[-1].coherence if self.memory.entries else 0.0
        mean = coherence_sum / max(1, cycles)

        return SubstrateSessionSummary(
            session_id=0,
            cycles=cycles,
            mean_coherence=mean,
            final_coherence=final,
            gco_counts=counts,
            final_substrate=self.substrate.snapshot(),
            action_counts=action_counts,
            atp_spent=self._atp_spent,
            atp_budget=self.session_budget,
            forced_rest_cycles=self._forced_rest,
        )

    def save_substrate(self) -> dict:
        return self.substrate.save_slow()

    def load_substrate(self, data: dict):
        self.substrate.load_slow(data)

    def save_session(self) -> dict:
        """Save full cross-session state: substrate + consolidated memory +
        dimension context.  The consolidated memory gives the next session's
        CFAR selector trail data from cycle 1; the dimension context lets
        pattern matching activate immediately."""
        entries = []
        for e in self.memory.entries:
            gco_val = e.gco.value if hasattr(e.gco, "value") else str(e.gco)
            entries.append({
                "cycle": e.cycle,
                "action": e.action,
                "mode": e.mode,
                "state_before": e.state_before,
                "state_after": e.state_after,
                "dimensions": dict(e.dimensions),
                "coherence": e.coherence,
                "delta": e.delta,
                "gco": gco_val,
                "cost_secs": e.cost_secs,
            })
        return {
            "substrate": self.substrate.save_slow(),
            "consolidated_memory": entries,
            "dim_history": list(self.substrate._dim_history),
            "prior_coherence": self._prior_coherence,
        }

    def load_session(self, data: dict):
        """Restore full cross-session state.  Seeds memory, dimension context,
        and prior coherence so the new session starts warm."""
        self.substrate.load_slow(data["substrate"])

        if "consolidated_memory" in data and data["consolidated_memory"]:
            entries = []
            for d in data["consolidated_memory"]:
                gco = d["gco"]
                if isinstance(gco, str):
                    gco = GCOStatus(gco)
                entries.append(CycleEntry(
                    cycle=d["cycle"],
                    action=d["action"],
                    mode=d["mode"],
                    state_before=d["state_before"],
                    state_after=d["state_after"],
                    dimensions=d["dimensions"],
                    coherence=d["coherence"],
                    delta=d["delta"],
                    gco=gco,
                    cost_secs=d["cost_secs"],
                ))
            self.memory.entries = entries

        if "dim_history" in data:
            self.substrate._dim_history = [
                dict(h) for h in data["dim_history"]
            ]
            self.substrate._match_patterns()

        if "prior_coherence" in data:
            self._prior_coherence = data["prior_coherence"]
