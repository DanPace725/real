"""ATP budget sweep: find where metabolic scarcity produces interesting dynamics.

Tests a range of per-session budgets from tight to generous, measuring how
coherence, substrate health, forced rests, and action allocation change.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

_phase4_root = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_phase4_root) not in sys.path:
    sys.path.insert(0, str(_phase4_root))

from .substrate import DIMENSIONS
from .real_integration import SubstrateEngine, SubstrateSessionSummary
from .run_integration import (
    SignalDomainObserver,
    SignalDomainActions,
    SignalDomainCoherence,
)


def run_budget_level(
    budget: float,
    seeds: List[int],
    sessions_per_seed: int = 10,
    cycles: int = 50,
) -> List[SubstrateSessionSummary]:
    all_summaries = []

    for seed in seeds:
        carried_slow = None
        for sid in range(1, sessions_per_seed + 1):
            s_seed = seed + sid
            engine = SubstrateEngine(
                observer=SignalDomainObserver(seed=s_seed),
                actions=SignalDomainActions(seed=s_seed),
                coherence=SignalDomainCoherence(),
                seed=s_seed,
                session_budget=budget,
            )
            if carried_slow is not None:
                engine.load_substrate(carried_slow)

            summary = engine.run_session(cycles=cycles)
            summary.session_id = sid
            all_summaries.append(summary)
            carried_slow = engine.save_substrate()

    return all_summaries


def summarize(summaries: List[SubstrateSessionSummary]) -> dict:
    coherences = [s.mean_coherence for s in summaries]
    actives = [s.final_substrate["active_count"] for s in summaries]
    couplings = [s.final_substrate["coupling_score"] for s in summaries]
    spent = [s.atp_spent for s in summaries]
    forced = [s.forced_rest_cycles for s in summaries]

    total_gco = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
    total_actions: Dict[str, int] = {}
    for s in summaries:
        for k, v in s.gco_counts.items():
            total_gco[k] += v
        for a, c in s.action_counts.items():
            total_actions[a] = total_actions.get(a, 0) + c

    total_cycles = max(sum(total_gco.values()), 1)
    total_acts = max(sum(total_actions.values()), 1)

    domain_share = sum(
        v for a, v in total_actions.items()
        if not a.startswith("invest_") and a != "maintain_substrate"
    ) / total_acts
    invest_share = sum(
        v for a, v in total_actions.items() if a.startswith("invest_")
    ) / total_acts
    maintain_share = total_actions.get("maintain_substrate", 0) / total_acts
    rest_share = total_actions.get("rest", 0) / total_acts

    return {
        "coherence_mean": statistics.mean(coherences),
        "coherence_std": statistics.stdev(coherences) if len(coherences) > 1 else 0,
        "active_mean": statistics.mean(actives),
        "coupling_mean": statistics.mean(couplings),
        "stable_rate": total_gco["STABLE"] / total_cycles,
        "critical_rate": total_gco["CRITICAL"] / total_cycles,
        "atp_spent_mean": statistics.mean(spent),
        "forced_rest_mean": statistics.mean(forced),
        "domain_action_share": domain_share,
        "invest_share": invest_share,
        "maintain_share": maintain_share,
        "rest_share": rest_share,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ATP Budget Sweep")
    parser.add_argument(
        "--budgets", type=float, nargs="+",
        default=[0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 5.0, 100.0],
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 137, 256])
    parser.add_argument("--sessions", type=int, default=10)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 80)
    print("  ATP Budget Sweep")
    print("=" * 80)
    print(f"  Budgets: {args.budgets}")
    print(f"  Seeds: {args.seeds}   Sessions/seed: {args.sessions}")
    print()

    results = {}
    for budget in args.budgets:
        label = f"{budget:.1f}" if budget < 100 else "inf"
        print(f"  Budget {label:>5} ATP ...", end="", flush=True)
        summaries = run_budget_level(
            budget=budget,
            seeds=args.seeds,
            sessions_per_seed=args.sessions,
            cycles=args.cycles,
        )
        s = summarize(summaries)
        results[label] = s
        print(
            f"  coh={s['coherence_mean']:.3f}  "
            f"active={s['active_mean']:.1f}  "
            f"coupling={s['coupling_mean']:.3f}  "
            f"STABLE={s['stable_rate']:.0%}  "
            f"spent={s['atp_spent_mean']:.2f}  "
            f"forced_rest={s['forced_rest_mean']:.1f}  "
            f"invest={s['invest_share']:.0%}  "
            f"maintain={s['maintain_share']:.0%}  "
            f"domain={s['domain_action_share']:.0%}"
        )

    # Summary table
    print()
    print("-" * 80)
    header = (
        f"  {'Budget':>6}  {'Coher':>6}  {'Active':>6}  {'Coupl':>6}  "
        f"{'STABLE':>6}  {'Spent':>6}  {'FRest':>5}  "
        f"{'Invest':>6}  {'Maint':>6}  {'Domain':>6}  {'Rest':>6}"
    )
    print(header)
    print("-" * 80)
    for label, s in results.items():
        print(
            f"  {label:>6}  "
            f"{s['coherence_mean']:>6.3f}  "
            f"{s['active_mean']:>6.1f}  "
            f"{s['coupling_mean']:>6.3f}  "
            f"{s['stable_rate']:>5.0%}  "
            f"{s['atp_spent_mean']:>6.2f}  "
            f"{s['forced_rest_mean']:>5.1f}  "
            f"{s['invest_share']:>5.0%}  "
            f"{s['maintain_share']:>5.0%}  "
            f"{s['domain_action_share']:>5.0%}  "
            f"{s['rest_share']:>5.0%}"
        )
    print("-" * 80)

    if args.output:
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "budget_sweep.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to {out}/budget_sweep.json")


if __name__ == "__main__":
    main()
