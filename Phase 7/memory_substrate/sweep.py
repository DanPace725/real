"""Parameter sweep and closure test for Phase 1 instrumentation.

Runs experiments across parameter variations to answer:
  - How does decay rate affect dynamics?
  - How does budget pressure change behavior?
  - How does the bistable threshold affect establishment difficulty?
  - Does the system recover from mid-session perturbation?
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .runner import SessionRunner, SessionLog
from .substrate import DIMENSIONS, SubstrateConfig, MemorySubstrate


@dataclass
class SweepResult:
    label: str
    config: dict
    mean_coherence: float
    final_coherence: float
    stable_pct: float
    mean_active: float
    mean_coupling: float
    sessions: list[SessionLog]


def run_sweep(
    param_name: str,
    values: list,
    base_config: Optional[SubstrateConfig] = None,
    sessions: int = 15,
    cycles: int = 50,
    budget: float = 5.0,
    seed: int = 42,
) -> list[SweepResult]:
    results = []
    base = base_config or SubstrateConfig()

    for val in values:
        config = SubstrateConfig(
            slow_decay=base.slow_decay,
            bistable_threshold=base.bistable_threshold,
            write_base_cost=base.write_base_cost,
            maintain_base_cost=base.maintain_base_cost,
            neighbor_discount=base.neighbor_discount,
            coupling_window=base.coupling_window,
            accelerated_decay_factor=base.accelerated_decay_factor,
        )

        run_budget = budget
        if param_name == "slow_decay":
            config.slow_decay = val
        elif param_name == "bistable_threshold":
            config.bistable_threshold = val
        elif param_name == "budget":
            run_budget = val
        elif param_name == "accelerated_decay_factor":
            config.accelerated_decay_factor = val
        elif param_name == "maintain_base_cost":
            config.maintain_base_cost = val

        runner = SessionRunner(
            substrate_config=config,
            cycles_per_session=cycles,
            session_budget=run_budget,
            seed=seed,
            carry_slow_layer=True,
        )
        logs = runner.run_experiment(sessions=sessions)

        coherences = [l.mean_coherence for l in logs]
        couplings = [l.final_substrate["coupling_score"] for l in logs]
        actives = [l.final_substrate["active_count"] for l in logs]
        total_gco = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
        for l in logs:
            for k, v in l.gco_counts.items():
                total_gco[k] += v
        total_cycles = sum(total_gco.values())

        results.append(SweepResult(
            label=f"{param_name}={val}",
            config={param_name: val, "budget": run_budget},
            mean_coherence=statistics.mean(coherences),
            final_coherence=logs[-1].final_coherence,
            stable_pct=total_gco["STABLE"] / max(total_cycles, 1),
            mean_active=statistics.mean(actives),
            mean_coupling=statistics.mean(couplings),
            sessions=logs,
        ))

    return results


# ------------------------------------------------------------------
# Self-reinforcing closure test
# ------------------------------------------------------------------

def run_closure_test(
    seed: int = 42,
    build_sessions: int = 8,
    test_sessions: int = 8,
    cycles: int = 50,
    budget: float = 5.0,
    dims_to_perturb: int = 3,
) -> dict:
    """Build slow layer across sessions, then perturb half the dims to zero.
    Observe whether the agent rebuilds them faster with active neighbors."""

    config = SubstrateConfig()
    runner = SessionRunner(
        substrate_config=config,
        cycles_per_session=cycles,
        session_budget=budget,
        seed=seed,
        carry_slow_layer=True,
    )

    # Phase A: build up all dimensions
    build_logs = []
    for i in range(1, build_sessions + 1):
        log = runner.run_session(session_id=i)
        build_logs.append(log)

    pre_perturbation = dict(runner._carried_slow["slow"])

    # Perturb: zero out N dimensions
    perturbed_dims = list(DIMENSIONS)[:dims_to_perturb]
    kept_dims = list(DIMENSIONS)[dims_to_perturb:]
    for dim in perturbed_dims:
        runner._carried_slow["slow"][dim] = 0.0
        runner._carried_slow["slow_age"][dim] = 0

    post_perturbation = dict(runner._carried_slow["slow"])

    # Phase B: observe recovery
    recovery_logs = []
    for i in range(build_sessions + 1, build_sessions + test_sessions + 1):
        log = runner.run_session(session_id=i)
        recovery_logs.append(log)

    # Analyze recovery: how quickly do perturbed dims get re-established?
    recovery_session = None
    for log in recovery_logs:
        snap = log.final_substrate
        all_recovered = all(snap["active"].get(d, False) for d in perturbed_dims)
        if all_recovered and recovery_session is None:
            recovery_session = log.session_id

    # Track per-dimension recovery across sessions
    dim_recovery = {d: [] for d in DIMENSIONS}
    for log in recovery_logs:
        for cyc in log.cycle_logs:
            for dim in DIMENSIONS:
                dim_recovery[dim].append(cyc.substrate_snapshot["slow"].get(dim, 0.0))

    return {
        "perturbed_dims": perturbed_dims,
        "kept_dims": kept_dims,
        "pre_perturbation": pre_perturbation,
        "post_perturbation": post_perturbation,
        "recovery_session": recovery_session,
        "build_coherence": statistics.mean(l.mean_coherence for l in build_logs),
        "recovery_coherence": statistics.mean(l.mean_coherence for l in recovery_logs),
        "recovery_trajectory": [
            {
                "session": log.session_id,
                "coherence": log.mean_coherence,
                "active": log.final_substrate["active_count"],
                "coupling": log.final_substrate["coupling_score"],
                "perturbed_status": {
                    d: log.final_substrate["active"].get(d, False)
                    for d in perturbed_dims
                },
            }
            for log in recovery_logs
        ],
    }


# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------

def generate_sweep_report(
    sweeps: dict[str, list[SweepResult]],
    closure: dict,
    output_path: Path,
):
    lines = []
    _w = lines.append

    _w("# Phase 1 — Sensitivity & Closure Analysis")
    _w("")
    _w("---")

    for param_name, results in sweeps.items():
        _w(f"## Sweep: {param_name}")
        _w("")
        _w("| Value | Coherence | STABLE % | Active | Coupling |")
        _w("|-------|-----------|----------|--------|----------|")
        for r in results:
            val = r.config[param_name]
            _w(f"| {val} | {r.mean_coherence:.3f} | {r.stable_pct:.0%} | "
               f"{r.mean_active:.1f} | {r.mean_coupling:.3f} |")
        _w("")

        # Interpretation
        coherences = [r.mean_coherence for r in results]
        best_idx = coherences.index(max(coherences))
        _w(f"**Best coherence:** {results[best_idx].label} ({max(coherences):.3f})")
        _w("")

    _w("## Self-Reinforcing Closure Test")
    _w("")
    _w(f"Perturbed dimensions: {', '.join(closure['perturbed_dims'])}")
    _w(f"Kept dimensions: {', '.join(closure['kept_dims'])}")
    _w(f"Build phase coherence: {closure['build_coherence']:.3f}")
    _w(f"Recovery phase coherence: {closure['recovery_coherence']:.3f}")
    _w(f"Full recovery session: {closure['recovery_session']}")
    _w("")
    _w("Pre-perturbation slow layer:")
    _w("")
    for dim in DIMENSIONS:
        _w(f"  {dim}: {closure['pre_perturbation'].get(dim, 0):.3f}")
    _w("")
    _w("Recovery trajectory:")
    _w("")
    _w("| Session | Coherence | Active | Coupling | Perturbed recovered |")
    _w("|---------|-----------|--------|----------|---------------------|")
    for r in closure["recovery_trajectory"]:
        recovered = sum(1 for v in r["perturbed_status"].values() if v)
        total = len(r["perturbed_status"])
        _w(f"| {r['session']} | {r['coherence']:.3f} | {r['active']} | "
           f"{r['coupling']:.3f} | {recovered}/{total} |")
    _w("")

    _w("---")
    _w("")
    _w("*Generated by Phase 1 sensitivity sweep.*")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Sweep report written to {output_path}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 — Parameter sweep")
    parser.add_argument("--output", type=str, default="experiment_data/sweeps")
    parser.add_argument("--sessions", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  Phase 1 — Sensitivity Sweep")
    print("=" * 64)

    sweeps = {}

    print("\n--- Decay rate sweep ---")
    sweeps["slow_decay"] = run_sweep(
        "slow_decay", [0.01, 0.02, 0.03, 0.05],
        sessions=args.sessions, seed=args.seed,
    )

    print("\n--- Budget sweep ---")
    sweeps["budget"] = run_sweep(
        "budget", [2.0, 3.5, 5.0, 7.0],
        sessions=args.sessions, seed=args.seed,
    )

    print("\n--- Bistable threshold sweep ---")
    sweeps["bistable_threshold"] = run_sweep(
        "bistable_threshold", [0.15, 0.25, 0.35, 0.45],
        sessions=args.sessions, seed=args.seed,
    )

    print("\n--- Accelerated decay factor sweep ---")
    sweeps["accelerated_decay_factor"] = run_sweep(
        "accelerated_decay_factor", [1.5, 3.0, 5.0, 8.0],
        sessions=args.sessions, seed=args.seed,
    )

    print("\n--- Self-reinforcing closure test ---")
    closure = run_closure_test(seed=args.seed)

    report_path = output_dir / "sweep_report.md"
    generate_sweep_report(sweeps, closure, report_path)

    # Save raw data
    raw = {
        "sweeps": {
            name: [
                {
                    "label": r.label,
                    "config": r.config,
                    "mean_coherence": r.mean_coherence,
                    "stable_pct": r.stable_pct,
                    "mean_active": r.mean_active,
                    "mean_coupling": r.mean_coupling,
                }
                for r in results
            ]
            for name, results in sweeps.items()
        },
        "closure": {
            k: v for k, v in closure.items()
            if k != "recovery_trajectory"
        },
    }
    raw["closure"]["recovery_trajectory"] = closure["recovery_trajectory"]
    with open(output_dir / "sweep_data.json", "w") as f:
        json.dump(raw, f, indent=2)


if __name__ == "__main__":
    main()
