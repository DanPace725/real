"""A/B comparison: REAL engine with vs without memory substrate.

Condition A (substrate): Full SubstrateEngine with all wrappers.
Condition B (baseline): Same REAL cycle, same domain, no substrate.

Both conditions share:
  - Identical domain adapters (same seeds per session)
  - Same CFAR selector parameters
  - Same TiltRegulatoryMesh
  - Same EpisodicMemory and consolidation
  - Same number of sessions and cycles

The only difference is whether the substrate layer is present.
"""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_phase4_root = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_phase4_root) not in sys.path:
    sys.path.insert(0, str(_phase4_root))

from real_core.types import ActionOutcome, CycleEntry, DimensionScores, GCOStatus
from real_core.memory import EpisodicMemory
from real_core.mesh import TiltRegulatoryMesh
from real_core.selector import CFARSelector

from .substrate import DIMENSIONS
from .real_integration import (
    SubstrateEngine,
    DEFAULT_DOMAIN_ATP,
    DEFAULT_DOMAIN_ATP_FALLBACK,
)
from .run_integration import (
    SignalDomainObserver,
    SignalDomainActions,
    SignalDomainCoherence,
)


# ------------------------------------------------------------------
# Baseline engine: REAL cycle without substrate
# ------------------------------------------------------------------

@dataclass
class SessionSummary:
    session_id: int
    cycles: int
    mean_coherence: float
    final_coherence: float
    gco_counts: Dict[str, int]
    action_counts: Dict[str, int]
    dim_means: Dict[str, float]
    coherence_trajectory: List[float]
    observation_variances: Dict[str, float]


class BaselineEngine:
    """Standard REAL cycle without substrate wrappers.
    Supports an optional ATP budget using the same domain cost table
    as SubstrateEngine, so both conditions face the same metabolic rules."""

    def __init__(
        self, observer, actions, coherence, seed=None,
        session_budget: float = float("inf"),
    ):
        self.observer = observer
        self.actions = actions
        self.coherence = coherence
        self.selector = CFARSelector()
        self.mesh = TiltRegulatoryMesh()
        self.memory = EpisodicMemory(maxlen=500)
        self._prior_coherence: Optional[float] = None
        self.session_budget = session_budget
        self.atp_remaining = session_budget

    def _action_atp(self, action: str) -> float:
        return DEFAULT_DOMAIN_ATP.get(action, DEFAULT_DOMAIN_ATP_FALLBACK)

    def run_cycle(self, cycle: int) -> CycleEntry:
        before = self.observer.observe(cycle)
        all_available = self.actions.available_actions(len(self.memory.entries))
        affordable = [
            a for a in all_available
            if self._action_atp(a) <= self.atp_remaining + 1e-9
        ]
        if not affordable:
            affordable = ["rest"]
        action, mode = self.selector.select(affordable, self.memory.entries)
        outcome = self.actions.execute(action)
        atp_cost = self._action_atp(action)
        self.atp_remaining = max(0.0, self.atp_remaining - atp_cost)
        after = self.observer.observe(cycle)

        raw_dims = self.coherence.score(after, self.memory.entries)
        dims = self.mesh.apply(raw_dims)
        coherence_val = self.coherence.composite(dims)
        delta = (
            0.0 if self._prior_coherence is None
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
        return entry

    def run_session(self, cycles: int = 50) -> SessionSummary:
        self.atp_remaining = self.session_budget
        gco_counts = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        coherence_sum = 0.0
        action_counts: Dict[str, int] = {}
        dim_sums: Dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        coherence_traj: List[float] = []
        obs_per_dim: Dict[str, List[float]] = {d: [] for d in DIMENSIONS}

        for i in range(1, cycles + 1):
            entry = self.run_cycle(i)
            gco_counts[entry.gco.value] += 1
            coherence_sum += entry.coherence
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            coherence_traj.append(entry.coherence)
            for d in DIMENSIONS:
                dim_sums[d] += entry.dimensions.get(d, 0.0)
                obs_per_dim[d].append(entry.state_after.get(d, 0.5))

            if entry.action == "rest" and len(self.memory.entries) > 40:
                self.memory.consolidate_three_tier()

        n = max(1, cycles)
        dim_means = {d: dim_sums[d] / n for d in DIMENSIONS}
        obs_vars = {
            d: statistics.variance(obs_per_dim[d]) if len(obs_per_dim[d]) > 1 else 0.0
            for d in DIMENSIONS
        }

        return SessionSummary(
            session_id=0,
            cycles=cycles,
            mean_coherence=coherence_sum / n,
            final_coherence=self.memory.entries[-1].coherence if self.memory.entries else 0.0,
            gco_counts=gco_counts,
            action_counts=action_counts,
            dim_means=dim_means,
            coherence_trajectory=coherence_traj,
            observation_variances=obs_vars,
        )


# ------------------------------------------------------------------
# Substrate engine adapter: extract matching metrics
# ------------------------------------------------------------------

def run_substrate_session(seed: int, cycles: int) -> SessionSummary:
    """Run one session with substrate and extract comparable metrics."""
    engine = SubstrateEngine(
        observer=SignalDomainObserver(seed=seed),
        actions=SignalDomainActions(seed=seed),
        coherence=SignalDomainCoherence(),
        seed=seed,
    )
    return _run_substrate_engine(engine, cycles)


def _run_substrate_engine(engine: SubstrateEngine, cycles: int) -> SessionSummary:
    gco_counts = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
    coherence_sum = 0.0
    action_counts: Dict[str, int] = {}
    dim_sums: Dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    coherence_traj: List[float] = []
    obs_per_dim: Dict[str, List[float]] = {d: [] for d in DIMENSIONS}

    for i in range(1, cycles + 1):
        entry = engine.run_cycle(i)
        gco_counts[entry.gco.value] += 1
        coherence_sum += entry.coherence
        action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
        coherence_traj.append(entry.coherence)
        for d in DIMENSIONS:
            dim_sums[d] += entry.dimensions.get(d, 0.0)
            obs_per_dim[d].append(entry.state_after.get(d, 0.5))

        if entry.action == "rest" and len(engine.memory.entries) > 40:
            engine.memory.consolidate_three_tier()
            engine._promote_patterns()

    n = max(1, cycles)
    dim_means = {d: dim_sums[d] / n for d in DIMENSIONS}
    obs_vars = {
        d: statistics.variance(obs_per_dim[d]) if len(obs_per_dim[d]) > 1 else 0.0
        for d in DIMENSIONS
    }

    return SessionSummary(
        session_id=0,
        cycles=cycles,
        mean_coherence=coherence_sum / n,
        final_coherence=engine.memory.entries[-1].coherence if engine.memory.entries else 0.0,
        gco_counts=gco_counts,
        action_counts=action_counts,
        dim_means=dim_means,
        coherence_trajectory=coherence_traj,
        observation_variances=obs_vars,
    )


# ------------------------------------------------------------------
# A/B comparison
# ------------------------------------------------------------------

@dataclass
class ConditionResult:
    name: str
    sessions: List[SessionSummary]

    @property
    def mean_coherence(self) -> float:
        return statistics.mean(s.mean_coherence for s in self.sessions)

    @property
    def coherence_std(self) -> float:
        vals = [s.mean_coherence for s in self.sessions]
        return statistics.stdev(vals) if len(vals) > 1 else 0.0

    @property
    def stable_rate(self) -> float:
        total = sum(sum(s.gco_counts.values()) for s in self.sessions)
        stable = sum(s.gco_counts.get("STABLE", 0) for s in self.sessions)
        return stable / max(total, 1)

    @property
    def critical_rate(self) -> float:
        total = sum(sum(s.gco_counts.values()) for s in self.sessions)
        critical = sum(s.gco_counts.get("CRITICAL", 0) for s in self.sessions)
        return critical / max(total, 1)

    def dim_mean(self, dim: str) -> float:
        return statistics.mean(s.dim_means.get(dim, 0.0) for s in self.sessions)

    def obs_var_mean(self, dim: str) -> float:
        return statistics.mean(s.observation_variances.get(dim, 0.0) for s in self.sessions)

    def gco_distribution(self) -> Dict[str, float]:
        total = sum(sum(s.gco_counts.values()) for s in self.sessions)
        agg = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        for s in self.sessions:
            for k, v in s.gco_counts.items():
                agg[k] += v
        return {k: v / max(total, 1) for k, v in agg.items()}

    def coherence_by_session_third(self) -> Dict[str, float]:
        n = len(self.sessions)
        if n < 3:
            return {"all": self.mean_coherence}
        third = n // 3
        early = statistics.mean(s.mean_coherence for s in self.sessions[:third])
        mid = statistics.mean(s.mean_coherence for s in self.sessions[third:2*third])
        late = statistics.mean(s.mean_coherence for s in self.sessions[2*third:])
        return {"early": early, "mid": mid, "late": late}


def run_ab(
    seeds: List[int],
    sessions_per_seed: int = 15,
    cycles: int = 50,
    budget: float = float("inf"),
) -> tuple:
    baseline_all = []
    substrate_all = []
    budget_label = f"{budget:.1f}" if budget < 1e6 else "unlimited"

    for seed in seeds:
        print(f"\n  Seed {seed}:")
        print(f"    Baseline ({budget_label} ATP) ...", end="", flush=True)
        for sid in range(1, sessions_per_seed + 1):
            s_seed = seed + sid
            engine = BaselineEngine(
                observer=SignalDomainObserver(seed=s_seed),
                actions=SignalDomainActions(seed=s_seed),
                coherence=SignalDomainCoherence(),
                session_budget=budget,
            )
            summary = engine.run_session(cycles=cycles)
            summary.session_id = sid
            baseline_all.append(summary)
        print(f" done ({len(baseline_all)} sessions)")

        print(f"    Substrate ({budget_label} ATP) ...", end="", flush=True)
        carried_session = None
        for sid in range(1, sessions_per_seed + 1):
            s_seed = seed + sid
            engine = SubstrateEngine(
                observer=SignalDomainObserver(seed=s_seed),
                actions=SignalDomainActions(seed=s_seed),
                coherence=SignalDomainCoherence(),
                seed=s_seed,
                session_budget=budget,
            )
            if carried_session is not None:
                engine.load_session(carried_session)

            sub_summary = _run_substrate_engine(engine, cycles)
            sub_summary.session_id = sid
            substrate_all.append(sub_summary)
            carried_session = engine.save_session()
        print(f" done ({len(substrate_all)} sessions)")

    return (
        ConditionResult("baseline", baseline_all),
        ConditionResult("substrate", substrate_all),
    )


def print_comparison(baseline: ConditionResult, substrate: ConditionResult):
    sep = "-" * 72

    print()
    print("=" * 72)
    print("  A/B COMPARISON: Baseline vs Substrate")
    print("=" * 72)
    print(
        f"  Samples: {len(baseline.sessions)} baseline, "
        f"{len(substrate.sessions)} substrate sessions"
    )

    # Overall coherence
    print()
    print(sep)
    print("  COHERENCE")
    print(sep)
    diff = substrate.mean_coherence - baseline.mean_coherence
    pct = diff / max(baseline.mean_coherence, 1e-6) * 100
    print(f"    Baseline:  {baseline.mean_coherence:.4f} (sd {baseline.coherence_std:.4f})")
    print(f"    Substrate: {substrate.mean_coherence:.4f} (sd {substrate.coherence_std:.4f})")
    print(f"    Delta:     {diff:+.4f} ({pct:+.1f}%)")

    # Trajectory
    b_thirds = baseline.coherence_by_session_third()
    s_thirds = substrate.coherence_by_session_third()
    print()
    print("    Trajectory (early / mid / late sessions):")
    if "early" in b_thirds:
        print(
            f"      Baseline:  {b_thirds['early']:.4f} -> "
            f"{b_thirds['mid']:.4f} -> {b_thirds['late']:.4f}"
        )
        print(
            f"      Substrate: {s_thirds['early']:.4f} -> "
            f"{s_thirds['mid']:.4f} -> {s_thirds['late']:.4f}"
        )
        b_gain = b_thirds["late"] - b_thirds["early"]
        s_gain = s_thirds["late"] - s_thirds["early"]
        print(f"      Baseline gain:  {b_gain:+.4f}")
        print(f"      Substrate gain: {s_gain:+.4f}")

    # GCO
    print()
    print(sep)
    print("  GCO DISTRIBUTION")
    print(sep)
    b_gco = baseline.gco_distribution()
    s_gco = substrate.gco_distribution()
    print(f"    {'':>16}  {'STABLE':>8}  {'PARTIAL':>8}  {'DEGRADED':>8}  {'CRITICAL':>8}")
    print(
        f"    {'Baseline':>16}  {b_gco['STABLE']:>7.1%}  {b_gco['PARTIAL']:>7.1%}  "
        f"{b_gco['DEGRADED']:>7.1%}  {b_gco['CRITICAL']:>7.1%}"
    )
    print(
        f"    {'Substrate':>16}  {s_gco['STABLE']:>7.1%}  {s_gco['PARTIAL']:>7.1%}  "
        f"{s_gco['DEGRADED']:>7.1%}  {s_gco['CRITICAL']:>7.1%}"
    )

    # Per-dimension
    print()
    print(sep)
    print("  PER-DIMENSION COHERENCE SCORES")
    print(sep)
    print(f"    {'Dimension':>18}  {'Baseline':>10}  {'Substrate':>10}  {'Delta':>10}")
    for d in DIMENSIONS:
        bv = baseline.dim_mean(d)
        sv = substrate.dim_mean(d)
        print(f"    {d:>18}  {bv:>10.4f}  {sv:>10.4f}  {sv - bv:>+10.4f}")

    # Observation variance
    print()
    print(sep)
    print("  OBSERVATION VARIANCE (lower = clearer signal)")
    print(sep)
    print(f"    {'Dimension':>18}  {'Baseline':>10}  {'Substrate':>10}  {'Reduction':>10}")
    for d in DIMENSIONS:
        bv = baseline.obs_var_mean(d)
        sv = substrate.obs_var_mean(d)
        red = (1.0 - sv / max(bv, 1e-6)) * 100 if bv > 0 else 0.0
        print(f"    {d:>18}  {bv:>10.4f}  {sv:>10.4f}  {red:>+9.1f}%")

    print()
    print(sep)
    print("  ACTION PROFILES")
    print(sep)
    b_actions: Dict[str, int] = {}
    s_actions: Dict[str, int] = {}
    for s in baseline.sessions:
        for a, c in s.action_counts.items():
            b_actions[a] = b_actions.get(a, 0) + c
    for s in substrate.sessions:
        for a, c in s.action_counts.items():
            s_actions[a] = s_actions.get(a, 0) + c

    b_total = max(sum(b_actions.values()), 1)
    s_total = max(sum(s_actions.values()), 1)

    all_actions = sorted(set(list(b_actions.keys()) + list(s_actions.keys())))
    domain_actions = [a for a in all_actions if not a.startswith("invest_") and a != "maintain_substrate"]
    substrate_actions = [a for a in all_actions if a.startswith("invest_") or a == "maintain_substrate"]

    print("    Domain actions:")
    for a in domain_actions:
        bc = b_actions.get(a, 0)
        sc = s_actions.get(a, 0)
        print(f"      {a:>22}  baseline={bc/b_total:>5.1%}  substrate={sc/s_total:>5.1%}")

    if substrate_actions:
        print("    Substrate actions:")
        for a in substrate_actions:
            sc = s_actions.get(a, 0)
            print(f"      {a:>22}  substrate={sc/s_total:>5.1%}")

    print()
    print("=" * 72)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A/B: Baseline vs Substrate")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 137, 256, 512, 999])
    parser.add_argument("--sessions", type=int, default=15)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--budget", type=float, default=float("inf"),
                        help="Per-session ATP budget (default: unlimited)")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    budget_label = f"{args.budget:.1f} ATP" if args.budget < 1e6 else "unlimited"
    print("=" * 72)
    print("  A/B Comparison: REAL Engine -- Baseline vs Memory Substrate")
    print("=" * 72)
    print(f"  Seeds: {args.seeds}")
    print(f"  Sessions per seed: {args.sessions}   Cycles: {args.cycles}")
    print(f"  ATP budget: {budget_label}")
    print(f"  Total sessions per condition: {len(args.seeds) * args.sessions}")

    baseline, substrate = run_ab(
        seeds=args.seeds,
        sessions_per_seed=args.sessions,
        cycles=args.cycles,
        budget=args.budget,
    )
    print_comparison(baseline, substrate)

    if args.output:
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        for cond in [baseline, substrate]:
            data = {
                "condition": cond.name,
                "mean_coherence": cond.mean_coherence,
                "coherence_std": cond.coherence_std,
                "stable_rate": cond.stable_rate,
                "gco": cond.gco_distribution(),
                "trajectory": cond.coherence_by_session_third(),
                "dim_means": {d: cond.dim_mean(d) for d in DIMENSIONS},
                "obs_variance": {d: cond.obs_var_mean(d) for d in DIMENSIONS},
                "n_sessions": len(cond.sessions),
            }
            with open(out / f"{cond.name}_summary.json", "w") as f:
                json.dump(data, f, indent=2)
        print(f"\n  Results saved to {out}/")


if __name__ == "__main__":
    main()
