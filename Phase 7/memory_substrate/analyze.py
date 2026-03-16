"""Phase 1 analysis: instrument the substrate and derive insights.

Processes experiment JSON logs and produces a markdown report covering:
  A. Predictive power of slow-layer state on future coherence
  B. Bistability distribution (bimodal check + threshold crossings)
  C. Maintenance pattern analysis (frequency vs outcomes)
  D. Per-dimension coupling breakdown
  E. Developmental trajectory (coherence/active/coupling over sessions)
  F. Action-outcome attribution (invest → improvement?)
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .substrate import DIMENSIONS


@dataclass
class AnalysisResult:
    predictive_power: dict
    bistability: dict
    maintenance_patterns: dict
    coupling_breakdown: dict
    trajectory: dict
    action_outcomes: dict


def load_experiment(experiment_dir: Path) -> list[dict]:
    sessions = []
    for path in sorted(experiment_dir.glob("session_*.json")):
        with open(path) as f:
            sessions.append(json.load(f))
    return sessions


def analyze_experiment(sessions: list[dict]) -> AnalysisResult:
    return AnalysisResult(
        predictive_power=_analyze_predictive_power(sessions),
        bistability=_analyze_bistability(sessions),
        maintenance_patterns=_analyze_maintenance(sessions),
        coupling_breakdown=_analyze_coupling(sessions),
        trajectory=_analyze_trajectory(sessions),
        action_outcomes=_analyze_action_outcomes(sessions),
    )


# ------------------------------------------------------------------
# A. Predictive power
# ------------------------------------------------------------------

def _analyze_predictive_power(sessions: list[dict], lookahead: int = 5) -> dict:
    """Correlation between slow-layer state and future coherence."""
    active_count_pairs = []
    per_dim_pairs = {d: [] for d in DIMENSIONS}

    for session in sessions:
        cycles = session["cycle_logs"]
        for i, cyc in enumerate(cycles):
            future_slice = cycles[i + 1 : i + 1 + lookahead]
            if len(future_slice) < 2:
                continue
            future_coherence = statistics.mean(c["coherence"] for c in future_slice)
            snap = cyc["substrate_snapshot"]
            active_count_pairs.append((snap["active_count"], future_coherence))
            for dim in DIMENSIONS:
                slow_val = snap["slow"].get(dim, 0.0)
                future_dim = statistics.mean(
                    c["dimensions"].get(dim, 0.0) for c in future_slice
                )
                per_dim_pairs[dim].append((slow_val, future_dim))

    result = {
        "active_count_correlation": _pearson([p[0] for p in active_count_pairs],
                                              [p[1] for p in active_count_pairs]),
        "active_count_n": len(active_count_pairs),
        "per_dimension": {},
    }
    for dim in DIMENSIONS:
        pairs = per_dim_pairs[dim]
        result["per_dimension"][dim] = {
            "correlation": _pearson([p[0] for p in pairs], [p[1] for p in pairs]),
            "n": len(pairs),
            "mean_slow_when_dim_high": _conditional_mean(
                pairs, lambda p: p[1] > 0.65, lambda p: p[0]
            ),
            "mean_slow_when_dim_low": _conditional_mean(
                pairs, lambda p: p[1] < 0.50, lambda p: p[0]
            ),
        }
    return result


# ------------------------------------------------------------------
# B. Bistability distribution
# ------------------------------------------------------------------

def _analyze_bistability(sessions: list[dict]) -> dict:
    all_slow_values = []
    threshold_crossings_up = 0
    threshold_crossings_down = 0

    for session in sessions:
        cycles = session["cycle_logs"]
        prev_active = {}
        for cyc in cycles:
            snap = cyc["substrate_snapshot"]
            for dim in DIMENSIONS:
                val = snap["slow"].get(dim, 0.0)
                all_slow_values.append(val)
                currently_active = snap["active"].get(dim, False)
                was_active = prev_active.get(dim, False)
                if currently_active and not was_active:
                    threshold_crossings_up += 1
                elif not currently_active and was_active:
                    threshold_crossings_down += 1
                prev_active[dim] = currently_active

    bins = _histogram(all_slow_values, n_bins=10, lo=0.0, hi=1.0)
    near_zero = sum(1 for v in all_slow_values if v < 0.05)
    above_threshold = sum(1 for v in all_slow_values if v >= 0.25)
    in_between = len(all_slow_values) - near_zero - above_threshold + \
                 sum(1 for v in all_slow_values if 0.05 <= v < 0.25)

    return {
        "total_observations": len(all_slow_values),
        "near_zero_pct": near_zero / len(all_slow_values),
        "above_threshold_pct": above_threshold / len(all_slow_values),
        "in_transition_pct": sum(1 for v in all_slow_values if 0.05 <= v < 0.25) / len(all_slow_values),
        "threshold_crossings_up": threshold_crossings_up,
        "threshold_crossings_down": threshold_crossings_down,
        "histogram": bins,
    }


# ------------------------------------------------------------------
# C. Maintenance patterns
# ------------------------------------------------------------------

def _analyze_maintenance(sessions: list[dict]) -> dict:
    session_data = []
    for session in sessions:
        cycles = session["cycle_logs"]
        total = len(cycles)
        maintains = sum(1 for c in cycles if c["action"] == "maintain")
        invests = sum(1 for c in cycles if c["action"].startswith("invest_"))
        observes = sum(1 for c in cycles if c["action"] == "observe")

        first_half_coh = statistics.mean(c["coherence"] for c in cycles[: total // 2])
        second_half_coh = statistics.mean(c["coherence"] for c in cycles[total // 2 :])

        maintain_atp = sum(c["cost"] for c in cycles if c["action"] == "maintain")
        invest_atp = sum(c["cost"] for c in cycles if c["action"].startswith("invest_"))

        session_data.append({
            "session_id": session["session_id"],
            "maintain_ratio": maintains / total,
            "invest_ratio": invests / total,
            "observe_ratio": observes / total,
            "maintain_atp": maintain_atp,
            "invest_atp": invest_atp,
            "coherence_improvement": second_half_coh - first_half_coh,
            "mean_coherence": session["mean_coherence"],
            "final_active": session["final_substrate"]["active_count"],
            "coupling": session["final_substrate"]["coupling_score"],
        })

    maintain_ratios = [s["maintain_ratio"] for s in session_data]
    coherences = [s["mean_coherence"] for s in session_data]
    couplings = [s["coupling"] for s in session_data]

    return {
        "sessions": session_data,
        "maintain_vs_coherence_corr": _pearson(maintain_ratios, coherences),
        "maintain_vs_coupling_corr": _pearson(maintain_ratios, couplings),
        "invest_vs_coherence_corr": _pearson(
            [s["invest_ratio"] for s in session_data], coherences
        ),
        "mean_maintain_ratio": statistics.mean(maintain_ratios),
        "mean_invest_ratio": statistics.mean(s["invest_ratio"] for s in session_data),
        "mean_atp_on_maintain": statistics.mean(s["maintain_atp"] for s in session_data),
        "mean_atp_on_invest": statistics.mean(s["invest_atp"] for s in session_data),
    }


# ------------------------------------------------------------------
# D. Per-dimension coupling breakdown
# ------------------------------------------------------------------

def _analyze_coupling(sessions: list[dict]) -> dict:
    dim_data = {d: {"slow_vals": [], "fast_vars": [], "fast_means": []} for d in DIMENSIONS}

    for session in sessions:
        for cyc in session["cycle_logs"]:
            snap = cyc["substrate_snapshot"]
            for dim in DIMENSIONS:
                slow_val = snap["slow"].get(dim, 0.0)
                fast_val = snap["fast"].get(dim, 0.0)
                dim_data[dim]["slow_vals"].append(slow_val)
                dim_data[dim]["fast_means"].append(fast_val)

    # Compute per-dimension coupling contribution
    result = {}
    for dim in DIMENSIONS:
        slow = dim_data[dim]["slow_vals"]
        fast = dim_data[dim]["fast_means"]

        active_slow = [s for s in slow if s >= 0.25]
        inactive_slow = [s for s in slow if s < 0.25]

        active_indices = [i for i, s in enumerate(slow) if s >= 0.25]
        inactive_indices = [i for i, s in enumerate(slow) if s < 0.25]

        fast_when_active = [fast[i] for i in active_indices] if active_indices else []
        fast_when_inactive = [fast[i] for i in inactive_indices] if inactive_indices else []

        result[dim] = {
            "active_pct": len(active_slow) / max(len(slow), 1),
            "mean_slow_when_active": statistics.mean(active_slow) if active_slow else 0,
            "mean_fast_when_active": statistics.mean(fast_when_active) if fast_when_active else 0,
            "mean_fast_when_inactive": statistics.mean(fast_when_inactive) if fast_when_inactive else 0,
            "fast_var_when_active": statistics.variance(fast_when_active) if len(fast_when_active) > 1 else 0,
            "fast_var_when_inactive": statistics.variance(fast_when_inactive) if len(fast_when_inactive) > 1 else 0,
            "observation_quality_delta": (
                (statistics.mean(fast_when_active) if fast_when_active else 0)
                - (statistics.mean(fast_when_inactive) if fast_when_inactive else 0)
            ),
        }
    return result


# ------------------------------------------------------------------
# E. Developmental trajectory
# ------------------------------------------------------------------

def _analyze_trajectory(sessions: list[dict]) -> dict:
    per_session = []
    for session in sessions:
        sid = session["session_id"]
        coh = session["mean_coherence"]
        final_coh = session["final_coherence"]
        active = session["final_substrate"]["active_count"]
        coupling = session["final_substrate"]["coupling_score"]
        gco = session["gco_counts"]
        stable_pct = gco.get("STABLE", 0) / max(sum(gco.values()), 1)

        per_session.append({
            "session": sid,
            "mean_coherence": coh,
            "final_coherence": final_coh,
            "active_count": active,
            "coupling": coupling,
            "stable_pct": stable_pct,
        })

    coherences = [s["mean_coherence"] for s in per_session]
    session_ids = [s["session"] for s in per_session]
    inflection = None
    for s in per_session:
        if s["active_count"] >= 6:
            inflection = s["session"]
            break

    return {
        "per_session": per_session,
        "coherence_trend_corr": _pearson(session_ids, coherences),
        "inflection_session": inflection,
        "early_mean_coh": statistics.mean(coherences[:5]),
        "late_mean_coh": statistics.mean(coherences[-5:]),
        "coherence_gain": statistics.mean(coherences[-5:]) - statistics.mean(coherences[:5]),
    }


# ------------------------------------------------------------------
# F. Action-outcome attribution
# ------------------------------------------------------------------

def _analyze_action_outcomes(sessions: list[dict]) -> dict:
    invest_deltas = {d: [] for d in DIMENSIONS}
    maintain_deltas = []
    observe_deltas = []

    for session in sessions:
        cycles = session["cycle_logs"]
        for i, cyc in enumerate(cycles):
            if i + 1 >= len(cycles):
                continue
            next_cyc = cycles[i + 1]
            action = cyc["action"]
            delta = next_cyc["coherence"] - cyc["coherence"]

            if action.startswith("invest_"):
                dim = action[len("invest_"):]
                if dim in DIMENSIONS:
                    dim_before = cyc["dimensions"].get(dim, 0)
                    dim_after = next_cyc["dimensions"].get(dim, 0)
                    invest_deltas[dim].append({
                        "coherence_delta": delta,
                        "dim_delta": dim_after - dim_before,
                        "slow_before": cyc["substrate_snapshot"]["slow"].get(dim, 0),
                        "slow_after": next_cyc["substrate_snapshot"]["slow"].get(dim, 0),
                    })
            elif action == "maintain":
                maintain_deltas.append(delta)
            elif action == "observe":
                observe_deltas.append(delta)

    result = {"per_dimension_invest": {}, "maintain": {}, "observe": {}}

    for dim in DIMENSIONS:
        entries = invest_deltas[dim]
        if entries:
            result["per_dimension_invest"][dim] = {
                "count": len(entries),
                "mean_coherence_delta": statistics.mean(e["coherence_delta"] for e in entries),
                "mean_dim_delta": statistics.mean(e["dim_delta"] for e in entries),
                "pct_positive_dim_delta": sum(1 for e in entries if e["dim_delta"] > 0) / len(entries),
                "mean_slow_gain": statistics.mean(e["slow_after"] - e["slow_before"] for e in entries),
            }

    if maintain_deltas:
        result["maintain"] = {
            "count": len(maintain_deltas),
            "mean_delta": statistics.mean(maintain_deltas),
            "pct_positive": sum(1 for d in maintain_deltas if d > 0) / len(maintain_deltas),
        }
    if observe_deltas:
        result["observe"] = {
            "count": len(observe_deltas),
            "mean_delta": statistics.mean(observe_deltas),
            "pct_positive": sum(1 for d in observe_deltas if d > 0) / len(observe_deltas),
        }
    return result


# ------------------------------------------------------------------
# Report generation
# ------------------------------------------------------------------

def generate_report(result: AnalysisResult, output_path: Path):
    lines = []
    _w = lines.append

    _w("# Phase 1 Analysis Report")
    _w("")
    _w("---")
    _w("")

    # A. Predictive Power
    _w("## A. Predictive Power of Slow Layer")
    _w("")
    pp = result.predictive_power
    _w(f"**Active count → future coherence (5-cycle lookahead):** r = {pp['active_count_correlation']:.3f}  (n = {pp['active_count_n']})")
    _w("")
    _w("| Dimension | Slow→Dim corr | Mean slow (dim>0.65) | Mean slow (dim<0.50) |")
    _w("|-----------|--------------|----------------------|----------------------|")
    for dim in DIMENSIONS:
        d = pp["per_dimension"][dim]
        _w(f"| {dim} | {d['correlation']:.3f} | {d['mean_slow_when_dim_high']:.3f} | {d['mean_slow_when_dim_low']:.3f} |")
    _w("")

    # B. Bistability
    _w("## B. Bistability Distribution")
    _w("")
    bi = result.bistability
    _w(f"Total slow-layer observations: {bi['total_observations']}")
    _w(f"- Near zero (<0.05): {bi['near_zero_pct']:.1%}")
    _w(f"- In transition (0.05–0.25): {bi['in_transition_pct']:.1%}")
    _w(f"- Above threshold (≥0.25): {bi['above_threshold_pct']:.1%}")
    _w(f"- Threshold crossings up: {bi['threshold_crossings_up']}")
    _w(f"- Threshold crossings down: {bi['threshold_crossings_down']}")
    _w("")
    _w("Histogram (slow-layer values, 10 bins from 0 to 1):")
    _w("")
    _w("```")
    for lo, hi, count, pct in bi["histogram"]:
        bar = "█" * int(pct * 50)
        _w(f"  [{lo:.1f}–{hi:.1f})  {bar} {pct:.1%} ({count})")
    _w("```")
    _w("")

    # C. Maintenance Patterns
    _w("## C. Maintenance Patterns")
    _w("")
    mp = result.maintenance_patterns
    _w(f"Mean maintain ratio: {mp['mean_maintain_ratio']:.1%} of cycles")
    _w(f"Mean invest ratio: {mp['mean_invest_ratio']:.1%} of cycles")
    _w(f"Mean ATP on maintain: {mp['mean_atp_on_maintain']:.3f}  |  invest: {mp['mean_atp_on_invest']:.3f}")
    _w(f"Maintain ratio ↔ coherence: r = {mp['maintain_vs_coherence_corr']:.3f}")
    _w(f"Maintain ratio ↔ coupling: r = {mp['maintain_vs_coupling_corr']:.3f}")
    _w(f"Invest ratio ↔ coherence: r = {mp['invest_vs_coherence_corr']:.3f}")
    _w("")

    # D. Coupling Breakdown
    _w("## D. Per-Dimension Coupling Breakdown")
    _w("")
    _w("| Dimension | Active % | Fast (active) | Fast (inactive) | Δ quality | Var (active) | Var (inactive) |")
    _w("|-----------|----------|---------------|-----------------|-----------|-------------|----------------|")
    for dim in DIMENSIONS:
        d = result.coupling_breakdown[dim]
        _w(f"| {dim} | {d['active_pct']:.0%} | {d['mean_fast_when_active']:.3f} | "
           f"{d['mean_fast_when_inactive']:.3f} | {d['observation_quality_delta']:+.3f} | "
           f"{d['fast_var_when_active']:.4f} | {d['fast_var_when_inactive']:.4f} |")
    _w("")

    # E. Trajectory
    _w("## E. Developmental Trajectory")
    _w("")
    tr = result.trajectory
    _w(f"Coherence trend (session ↔ coherence): r = {tr['coherence_trend_corr']:.3f}")
    _w(f"Inflection session (first all-6-active): {tr['inflection_session']}")
    _w(f"Early mean coherence (sessions 1–5): {tr['early_mean_coh']:.3f}")
    _w(f"Late mean coherence (last 5 sessions): {tr['late_mean_coh']:.3f}")
    _w(f"Coherence gain (late − early): {tr['coherence_gain']:+.3f}")
    _w("")
    _w("| Session | Coherence | Active | Coupling | STABLE % |")
    _w("|---------|-----------|--------|----------|----------|")
    for s in tr["per_session"]:
        _w(f"| {s['session']:>2} | {s['mean_coherence']:.3f} | {s['active_count']} | "
           f"{s['coupling']:.3f} | {s['stable_pct']:.0%} |")
    _w("")

    # F. Action Outcomes
    _w("## F. Action-Outcome Attribution")
    _w("")
    ao = result.action_outcomes
    if ao.get("maintain"):
        m = ao["maintain"]
        _w(f"**Maintain** (n={m['count']}): mean Δcoherence = {m['mean_delta']:+.4f}, "
           f"{m['pct_positive']:.0%} positive")
    if ao.get("observe"):
        o = ao["observe"]
        _w(f"**Observe** (n={o['count']}): mean Δcoherence = {o['mean_delta']:+.4f}, "
           f"{o['pct_positive']:.0%} positive")
    _w("")
    _w("**Invest per dimension:**")
    _w("")
    _w("| Dimension | Count | Δcoherence | Δdim score | % dim improved | Slow gain |")
    _w("|-----------|-------|------------|------------|----------------|-----------|")
    for dim in DIMENSIONS:
        if dim in ao.get("per_dimension_invest", {}):
            d = ao["per_dimension_invest"][dim]
            _w(f"| {dim} | {d['count']} | {d['mean_coherence_delta']:+.4f} | "
               f"{d['mean_dim_delta']:+.4f} | {d['pct_positive_dim_delta']:.0%} | "
               f"{d['mean_slow_gain']:+.3f} |")
    _w("")

    _w("---")
    _w("")
    _w("*Report generated by Phase 1 analysis pipeline.*")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {output_path}")


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    sx = statistics.stdev(xs)
    sy = statistics.stdev(ys)
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)


def _conditional_mean(pairs, condition, extractor) -> float:
    filtered = [extractor(p) for p in pairs if condition(p)]
    return statistics.mean(filtered) if filtered else 0.0


def _histogram(values: list[float], n_bins: int = 10, lo: float = 0.0, hi: float = 1.0):
    width = (hi - lo) / n_bins
    counts = [0] * n_bins
    for v in values:
        idx = min(int((v - lo) / width), n_bins - 1)
        idx = max(0, idx)
        counts[idx] += 1
    total = len(values)
    return [
        (lo + i * width, lo + (i + 1) * width, counts[i], counts[i] / max(total, 1))
        for i in range(n_bins)
    ]


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 — Analyze experiment data")
    parser.add_argument("input_dir", type=str, help="Path to experiment data directory")
    parser.add_argument("--output", type=str, default=None, help="Output report path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output) if args.output else input_dir / "analysis_report.md"

    print(f"Loading experiment from {input_dir}...")
    sessions = load_experiment(input_dir)
    print(f"Loaded {len(sessions)} sessions")

    print("Analyzing...")
    result = analyze_experiment(sessions)

    generate_report(result, output_path)


if __name__ == "__main__":
    main()
