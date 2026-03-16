from __future__ import annotations

import json
import shutil
import uuid
from statistics import mean

from compare_cold_warm import ROOT, SCENARIOS, build_system
from evaluate_transfer_asymmetry import DEFAULT_SEEDS, _runtime_commitment


TASK_A = "cvt1_task_a_stage1"
TASK_B = "cvt1_task_b_stage1"
BALANCE_STRONG_MARGIN = 0.5
BALANCE_SUSTAIN_CYCLES = 3


def _route_neighbor(action: str) -> str | None:
    if action.startswith("route_transform:"):
        parts = action.split(":")
        if len(parts) == 3:
            return parts[1]
        return None
    if action.startswith("route:"):
        return action.split(":", 1)[1]
    return None


def _route_transform(action: str) -> str:
    if action.startswith("route_transform:"):
        parts = action.split(":")
        if len(parts) == 3:
            return parts[2]
    if action.startswith("route:"):
        return "identity"
    return ""


def _overall_stat(summary: dict[str, object], field: str) -> float:
    return float(summary.get("task_diagnostics", {}).get("overall", {}).get(field, 0.0))


def _context_stat(summary: dict[str, object], context_key: str, field: str) -> float:
    return float(
        summary.get("task_diagnostics", {})
        .get("contexts", {})
        .get(context_key, {})
        .get(field, 0.0)
    )


def _run_training(seed: int, scenario_name: str):
    scenario = SCENARIOS[scenario_name]
    system = build_system(seed, scenario_name)
    system.run_workload(
        cycles=scenario.cycles,
        initial_packets=scenario.initial_packets,
        packet_schedule=scenario.packet_schedule,
        initial_signal_specs=scenario.initial_signal_specs,
        signal_schedule_specs=scenario.signal_schedule_specs,
    )
    return system


def _balance_signal(credit: float, debt: float) -> tuple[float, float]:
    total = credit + debt
    balance = credit - debt
    if total <= 1e-9:
        return round(balance, 5), 0.0
    return round(balance, 5), round(balance / total, 5)


def _first_sustained_cycle(
    records: list[dict[str, float]],
    field: str,
    *,
    threshold: float,
    sustain_cycles: int = BALANCE_SUSTAIN_CYCLES,
) -> int | None:
    if sustain_cycles <= 0:
        sustain_cycles = 1
    last_start = len(records) - sustain_cycles + 1
    for start_index in range(max(0, last_start)):
        window = records[start_index : start_index + sustain_cycles]
        if len(window) < sustain_cycles:
            continue
        if all(float(item[field]) >= threshold for item in window):
            return int(window[0]["cycle"])
    return None


def _selector_cycle_summary(entries: dict[str, object]) -> dict[str, object]:
    route_branch_counts: dict[str, int] = {}
    route_transform_counts: dict[str, int] = {}
    route_mode_counts: dict[str, int] = {}
    branch_transform_counts: dict[str, int] = {}
    route_coherence_total = 0.0
    route_delta_total = 0.0
    route_count = 0
    rest_count = 0
    invest_count = 0

    for entry in entries.values():
        if entry is None:
            continue
        action = str(entry.action)
        if action == "rest":
            rest_count += 1
            continue
        if action.startswith("invest:") or action == "maintain_edges":
            invest_count += 1
            continue
        neighbor_id = _route_neighbor(action)
        if neighbor_id is None:
            continue
        route_count += 1
        route_branch_counts[neighbor_id] = route_branch_counts.get(neighbor_id, 0) + 1
        transform_name = _route_transform(action)
        route_transform_counts[transform_name] = route_transform_counts.get(transform_name, 0) + 1
        branch_transform_key = f"{neighbor_id}:{transform_name}"
        branch_transform_counts[branch_transform_key] = (
            branch_transform_counts.get(branch_transform_key, 0) + 1
        )
        mode_name = str(entry.mode)
        route_mode_counts[mode_name] = route_mode_counts.get(mode_name, 0) + 1
        route_coherence_total += float(entry.coherence)
        route_delta_total += float(entry.delta)

    return {
        "route_count": route_count,
        "rest_count": rest_count,
        "invest_count": invest_count,
        "route_branch_counts": route_branch_counts,
        "route_transform_counts": route_transform_counts,
        "route_mode_counts": route_mode_counts,
        "branch_transform_counts": branch_transform_counts,
        "mean_route_coherence": round(route_coherence_total / max(route_count, 1), 5),
        "mean_route_delta": round(route_delta_total / max(route_count, 1), 5),
    }


def _aggregate_selector_window(cycle_records: list[dict[str, object]]) -> dict[str, object]:
    route_branch_counts: dict[str, int] = {}
    route_transform_counts: dict[str, int] = {}
    route_mode_counts: dict[str, int] = {}
    branch_transform_counts: dict[str, int] = {}
    total_route = 0
    total_rest = 0
    total_invest = 0
    coherence_values: list[float] = []
    delta_values: list[float] = []

    for record in cycle_records:
        total_route += int(record.get("route_count", 0))
        total_rest += int(record.get("rest_count", 0))
        total_invest += int(record.get("invest_count", 0))
        coherence_values.append(float(record.get("mean_route_coherence", 0.0)))
        delta_values.append(float(record.get("mean_route_delta", 0.0)))
        for key, value in dict(record.get("route_branch_counts", {})).items():
            route_branch_counts[key] = route_branch_counts.get(key, 0) + int(value)
        for key, value in dict(record.get("route_transform_counts", {})).items():
            route_transform_counts[key] = route_transform_counts.get(key, 0) + int(value)
        for key, value in dict(record.get("route_mode_counts", {})).items():
            route_mode_counts[key] = route_mode_counts.get(key, 0) + int(value)
        for key, value in dict(record.get("branch_transform_counts", {})).items():
            branch_transform_counts[key] = branch_transform_counts.get(key, 0) + int(value)

    def _shares(counts: dict[str, int], total: int) -> dict[str, float]:
        if total <= 0:
            return {}
        return {
            key: round(value / total, 5)
            for key, value in sorted(counts.items())
        }

    top_branch_transforms = sorted(
        branch_transform_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:5]

    return {
        "cycles_in_window": len(cycle_records),
        "total_route_actions": total_route,
        "total_rest_actions": total_rest,
        "total_invest_actions": total_invest,
        "route_branch_counts": dict(sorted(route_branch_counts.items())),
        "route_branch_shares": _shares(route_branch_counts, total_route),
        "route_transform_counts": dict(sorted(route_transform_counts.items())),
        "route_transform_shares": _shares(route_transform_counts, total_route),
        "route_mode_counts": dict(sorted(route_mode_counts.items())),
        "route_mode_shares": _shares(route_mode_counts, total_route),
        "top_branch_transform_counts": [
            {"branch_transform": key, "count": value}
            for key, value in top_branch_transforms
        ],
        "mean_route_coherence": round(mean(coherence_values), 5) if coherence_values else 0.0,
        "mean_route_delta": round(mean(delta_values), 5) if delta_values else 0.0,
    }


def _timeline_summary(records: list[dict[str, float]]) -> dict[str, float | None]:
    branch_debt_values = [record["branch_context_debt_total"] for record in records]
    context_branch_debt_values = [
        record["context_branch_transform_debt_total"] for record in records
    ]
    combined_balance_values = [record["combined_context_balance_total"] for record in records]
    combined_margin_values = [record["combined_context_balance_margin"] for record in records]

    peak_branch_debt = max(branch_debt_values, default=0.0)
    peak_context_branch_debt = max(context_branch_debt_values, default=0.0)
    min_combined_balance = min(combined_balance_values, default=0.0)
    min_combined_margin = min(combined_margin_values, default=0.0)

    peak_branch_cycle = next(
        (
            record["cycle"]
            for record in records
            if record["branch_context_debt_total"] == peak_branch_debt
        ),
        None,
    )
    peak_context_branch_cycle = next(
        (
            record["cycle"]
            for record in records
            if record["context_branch_transform_debt_total"] == peak_context_branch_debt
        ),
        None,
    )
    min_combined_balance_cycle = next(
        (
            record["cycle"]
            for record in records
            if record["combined_context_balance_total"] == min_combined_balance
        ),
        None,
    )
    min_combined_margin_cycle = next(
        (
            record["cycle"]
            for record in records
            if record["combined_context_balance_margin"] == min_combined_margin
        ),
        None,
    )

    branch_half_relief_cycle = None
    if peak_branch_cycle is not None and peak_branch_debt > 0.0:
        half_level = peak_branch_debt * 0.5
        for record in records:
            if record["cycle"] <= peak_branch_cycle:
                continue
            if record["branch_context_debt_total"] <= half_level:
                branch_half_relief_cycle = record["cycle"]
                break

    context_branch_half_relief_cycle = None
    if peak_context_branch_cycle is not None and peak_context_branch_debt > 0.0:
        half_level = peak_context_branch_debt * 0.5
        for record in records:
            if record["cycle"] <= peak_context_branch_cycle:
                continue
            if record["context_branch_transform_debt_total"] <= half_level:
                context_branch_half_relief_cycle = record["cycle"]
                break

    negative_balance_cycles = [
        int(record["cycle"])
        for record in records
        if float(record["combined_context_balance_total"]) < 0.0
    ]

    final = records[-1] if records else {}
    return {
        "peak_branch_context_debt_total": round(peak_branch_debt, 5),
        "peak_branch_context_debt_cycle": peak_branch_cycle,
        "branch_context_debt_auc": round(sum(branch_debt_values), 5),
        "branch_context_half_relief_cycle": branch_half_relief_cycle,
        "peak_context_branch_transform_debt_total": round(peak_context_branch_debt, 5),
        "peak_context_branch_transform_debt_cycle": peak_context_branch_cycle,
        "context_branch_transform_debt_auc": round(sum(context_branch_debt_values), 5),
        "context_branch_transform_half_relief_cycle": context_branch_half_relief_cycle,
        "combined_context_balance_auc": round(sum(combined_balance_values), 5),
        "combined_context_balance_margin_auc": round(sum(combined_margin_values), 5),
        "min_combined_context_balance_total": round(min_combined_balance, 5),
        "min_combined_context_balance_cycle": min_combined_balance_cycle,
        "min_combined_context_balance_margin": round(min_combined_margin, 5),
        "min_combined_context_balance_margin_cycle": min_combined_margin_cycle,
        "negative_combined_balance_cycle_count": len(negative_balance_cycles),
        "first_negative_combined_balance_cycle": (
            negative_balance_cycles[0] if negative_balance_cycles else None
        ),
        "last_negative_combined_balance_cycle": (
            negative_balance_cycles[-1] if negative_balance_cycles else None
        ),
        "first_positive_combined_balance_cycle": _first_sustained_cycle(
            records,
            "combined_context_balance_total",
            threshold=0.0,
            sustain_cycles=1,
        ),
        "first_strong_combined_balance_cycle": _first_sustained_cycle(
            records,
            "combined_context_balance_margin",
            threshold=BALANCE_STRONG_MARGIN,
            sustain_cycles=BALANCE_SUSTAIN_CYCLES,
        ),
        "final_branch_context_debt_total": round(
            float(final.get("branch_context_debt_total", 0.0)),
            5,
        ),
        "final_context_branch_transform_debt_total": round(
            float(final.get("context_branch_transform_debt_total", 0.0)),
            5,
        ),
        "final_branch_context_credit_total": round(
            float(final.get("branch_context_credit_total", 0.0)),
            5,
        ),
        "final_context_branch_transform_credit_total": round(
            float(final.get("context_branch_transform_credit_total", 0.0)),
            5,
        ),
        "final_combined_context_balance_total": round(
            float(final.get("combined_context_balance_total", 0.0)),
            5,
        ),
        "final_combined_context_balance_margin": round(
            float(final.get("combined_context_balance_margin", 0.0)),
            5,
        ),
        "final_mean_bit_accuracy": round(float(final.get("mean_bit_accuracy", 0.0)), 5),
        "final_exact_matches": int(final.get("exact_matches", 0)),
    }


def _run_transfer_timeline(seed: int, train_scenario: str, transfer_scenario: str) -> dict[str, object]:
    training_system = _run_training(seed, train_scenario)

    base_dir = ROOT / "tests_tmp" / f"timecourse_{uuid.uuid4().hex}"
    full_dir = base_dir / "full"
    full_dir.mkdir(parents=True, exist_ok=True)
    try:
        training_system.save_memory_carryover(full_dir)

        variants = {}
        for label, warm in (("cold", False), ("warm_full", True)):
            system = build_system(seed, transfer_scenario)
            if warm:
                system.load_memory_carryover(full_dir)

            scenario = SCENARIOS[transfer_scenario]
            if scenario.initial_signal_specs:
                system.inject_signal_specs(scenario.initial_signal_specs)
            elif scenario.initial_packets > 0:
                system.inject_signal(count=scenario.initial_packets)

            records = []
            for cycle in range(1, scenario.cycles + 1):
                scheduled_specs = (scenario.signal_schedule_specs or {}).get(cycle)
                if scheduled_specs:
                    system.inject_signal_specs(scheduled_specs)
                else:
                    scheduled = scenario.packet_schedule.get(cycle, 0)
                    if scheduled > 0:
                        system.inject_signal(count=scheduled)
                report = system.run_global_cycle()
                summary = system.summarize()
                commitment = _runtime_commitment(system)
                branch_balance, branch_margin = _balance_signal(
                    commitment["branch_context_credit_total"],
                    commitment["branch_context_debt_total"],
                )
                context_branch_balance, context_branch_margin = _balance_signal(
                    commitment["context_branch_transform_credit_total"],
                    commitment["context_branch_transform_debt_total"],
                )
                combined_credit = (
                    commitment["branch_context_credit_total"]
                    + commitment["context_branch_transform_credit_total"]
                )
                combined_debt = (
                    commitment["branch_context_debt_total"]
                    + commitment["context_branch_transform_debt_total"]
                )
                combined_balance, combined_margin = _balance_signal(
                    combined_credit,
                    combined_debt,
                )
                selector_summary = _selector_cycle_summary(report["entries"])
                records.append(
                    {
                        "cycle": cycle,
                        "exact_matches": int(summary["exact_matches"]),
                        "mean_bit_accuracy": round(float(summary["mean_bit_accuracy"]), 5),
                        "wrong_transform_family": round(
                            _overall_stat(summary, "wrong_transform_family"),
                            5,
                        ),
                        "stale_context_support_suspicions": round(
                            _overall_stat(summary, "stale_context_support_suspicions"),
                            5,
                        ),
                        "context_1_mean_bit_accuracy": round(
                            _context_stat(summary, "context_1", "mean_bit_accuracy"),
                            5,
                        ),
                        "branch_context_credit_total": commitment["branch_context_credit_total"],
                        "branch_context_debt_total": commitment["branch_context_debt_total"],
                        "branch_context_balance_total": branch_balance,
                        "branch_context_balance_margin": branch_margin,
                        "context_branch_transform_credit_total": commitment[
                            "context_branch_transform_credit_total"
                        ],
                        "context_branch_transform_debt_total": commitment[
                            "context_branch_transform_debt_total"
                        ],
                        "context_branch_transform_balance_total": context_branch_balance,
                        "context_branch_transform_balance_margin": context_branch_margin,
                        "combined_context_balance_total": combined_balance,
                        "combined_context_balance_margin": combined_margin,
                        "route_count": selector_summary["route_count"],
                        "rest_count": selector_summary["rest_count"],
                        "invest_count": selector_summary["invest_count"],
                        "route_branch_counts": selector_summary["route_branch_counts"],
                        "route_transform_counts": selector_summary["route_transform_counts"],
                        "route_mode_counts": selector_summary["route_mode_counts"],
                        "branch_transform_counts": selector_summary["branch_transform_counts"],
                        "mean_route_coherence": selector_summary["mean_route_coherence"],
                        "mean_route_delta": selector_summary["mean_route_delta"],
                    }
                )
            variants[label] = {
                "timeline": records,
                "summary": _timeline_summary(records),
            }
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    return {
        "seed": seed,
        "train_scenario": train_scenario,
        "transfer_scenario": transfer_scenario,
        "cold": variants["cold"],
        "warm_full": variants["warm_full"],
    }


def _mean_or_none(values: list[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return round(mean(present), 5)


def _aggregate_variant(records: list[dict[str, object]], label: str) -> dict[str, object]:
    per_cycle = []
    cycle_count = len(records[0][label]["timeline"]) if records else 0
    for index in range(cycle_count):
        cycle_records = [record[label]["timeline"][index] for record in records]
        per_cycle.append(
            {
                "cycle": int(cycle_records[0]["cycle"]),
                "mean_exact_matches": round(mean(item["exact_matches"] for item in cycle_records), 5),
                "mean_bit_accuracy": round(mean(item["mean_bit_accuracy"] for item in cycle_records), 5),
                "mean_context_1_bit_accuracy": round(
                    mean(item["context_1_mean_bit_accuracy"] for item in cycle_records),
                    5,
                ),
                "mean_wrong_transform_family": round(
                    mean(item["wrong_transform_family"] for item in cycle_records),
                    5,
                ),
                "mean_stale_context_support_suspicions": round(
                    mean(item["stale_context_support_suspicions"] for item in cycle_records),
                    5,
                ),
                "mean_branch_context_credit_total": round(
                    mean(item["branch_context_credit_total"] for item in cycle_records),
                    5,
                ),
                "mean_branch_context_debt_total": round(
                    mean(item["branch_context_debt_total"] for item in cycle_records),
                    5,
                ),
                "mean_branch_context_balance_total": round(
                    mean(item["branch_context_balance_total"] for item in cycle_records),
                    5,
                ),
                "mean_branch_context_balance_margin": round(
                    mean(item["branch_context_balance_margin"] for item in cycle_records),
                    5,
                ),
                "mean_context_branch_transform_credit_total": round(
                    mean(item["context_branch_transform_credit_total"] for item in cycle_records),
                    5,
                ),
                "mean_context_branch_transform_debt_total": round(
                    mean(item["context_branch_transform_debt_total"] for item in cycle_records),
                    5,
                ),
                "mean_context_branch_transform_balance_total": round(
                    mean(item["context_branch_transform_balance_total"] for item in cycle_records),
                    5,
                ),
                "mean_context_branch_transform_balance_margin": round(
                    mean(item["context_branch_transform_balance_margin"] for item in cycle_records),
                    5,
                ),
                "mean_combined_context_balance_total": round(
                    mean(item["combined_context_balance_total"] for item in cycle_records),
                    5,
                ),
                "mean_combined_context_balance_margin": round(
                    mean(item["combined_context_balance_margin"] for item in cycle_records),
                    5,
                ),
            }
        )

    summaries = [record[label]["summary"] for record in records]
    negative_cycle_records = [
        cycle_record
        for record in records
        for cycle_record in record[label]["timeline"]
        if float(cycle_record["combined_context_balance_total"]) < 0.0
    ]
    return {
        "timeline": per_cycle,
        "aggregate_summary": {
            "avg_peak_branch_context_debt_total": round(
                mean(item["peak_branch_context_debt_total"] for item in summaries),
                5,
            ),
            "avg_peak_branch_context_debt_cycle": _mean_or_none(
                [item["peak_branch_context_debt_cycle"] for item in summaries]
            ),
            "avg_branch_context_debt_auc": round(
                mean(item["branch_context_debt_auc"] for item in summaries),
                5,
            ),
            "avg_branch_context_half_relief_cycle": _mean_or_none(
                [item["branch_context_half_relief_cycle"] for item in summaries]
            ),
            "avg_peak_context_branch_transform_debt_total": round(
                mean(item["peak_context_branch_transform_debt_total"] for item in summaries),
                5,
            ),
            "avg_peak_context_branch_transform_debt_cycle": _mean_or_none(
                [item["peak_context_branch_transform_debt_cycle"] for item in summaries]
            ),
            "avg_context_branch_transform_debt_auc": round(
                mean(item["context_branch_transform_debt_auc"] for item in summaries),
                5,
            ),
            "avg_context_branch_transform_half_relief_cycle": _mean_or_none(
                [item["context_branch_transform_half_relief_cycle"] for item in summaries]
            ),
            "avg_combined_context_balance_auc": round(
                mean(item["combined_context_balance_auc"] for item in summaries),
                5,
            ),
            "avg_combined_context_balance_margin_auc": round(
                mean(item["combined_context_balance_margin_auc"] for item in summaries),
                5,
            ),
            "avg_min_combined_context_balance_total": round(
                mean(item["min_combined_context_balance_total"] for item in summaries),
                5,
            ),
            "avg_min_combined_context_balance_cycle": _mean_or_none(
                [item["min_combined_context_balance_cycle"] for item in summaries]
            ),
            "avg_min_combined_context_balance_margin": round(
                mean(item["min_combined_context_balance_margin"] for item in summaries),
                5,
            ),
            "avg_min_combined_context_balance_margin_cycle": _mean_or_none(
                [item["min_combined_context_balance_margin_cycle"] for item in summaries]
            ),
            "avg_negative_combined_balance_cycle_count": round(
                mean(item["negative_combined_balance_cycle_count"] for item in summaries),
                5,
            ),
            "avg_first_negative_combined_balance_cycle": _mean_or_none(
                [item["first_negative_combined_balance_cycle"] for item in summaries]
            ),
            "avg_last_negative_combined_balance_cycle": _mean_or_none(
                [item["last_negative_combined_balance_cycle"] for item in summaries]
            ),
            "avg_first_positive_combined_balance_cycle": _mean_or_none(
                [item["first_positive_combined_balance_cycle"] for item in summaries]
            ),
            "avg_first_strong_combined_balance_cycle": _mean_or_none(
                [item["first_strong_combined_balance_cycle"] for item in summaries]
            ),
            "avg_final_branch_context_debt_total": round(
                mean(item["final_branch_context_debt_total"] for item in summaries),
                5,
            ),
            "avg_final_context_branch_transform_debt_total": round(
                mean(item["final_context_branch_transform_debt_total"] for item in summaries),
                5,
            ),
            "avg_final_branch_context_credit_total": round(
                mean(item["final_branch_context_credit_total"] for item in summaries),
                5,
            ),
            "avg_final_context_branch_transform_credit_total": round(
                mean(item["final_context_branch_transform_credit_total"] for item in summaries),
                5,
            ),
            "avg_final_combined_context_balance_total": round(
                mean(item["final_combined_context_balance_total"] for item in summaries),
                5,
            ),
            "avg_final_combined_context_balance_margin": round(
                mean(item["final_combined_context_balance_margin"] for item in summaries),
                5,
            ),
            "avg_final_mean_bit_accuracy": round(
                mean(item["final_mean_bit_accuracy"] for item in summaries),
                5,
            ),
            "avg_final_exact_matches": round(
                mean(item["final_exact_matches"] for item in summaries),
                5,
            ),
        },
        "negative_balance_selector_summary": _aggregate_selector_window(negative_cycle_records),
    }


def analyze_transfer_timecourse(*, seeds: tuple[int, ...] = DEFAULT_SEEDS) -> dict[str, object]:
    a_to_b = [_run_transfer_timeline(seed, TASK_A, TASK_B) for seed in seeds]
    b_to_a = [_run_transfer_timeline(seed, TASK_B, TASK_A) for seed in seeds]

    aggregate_a_to_b_cold = _aggregate_variant(a_to_b, "cold")
    aggregate_a_to_b_warm = _aggregate_variant(a_to_b, "warm_full")
    aggregate_b_to_a_cold = _aggregate_variant(b_to_a, "cold")
    aggregate_b_to_a_warm = _aggregate_variant(b_to_a, "warm_full")

    return {
        "seeds": list(seeds),
        "pairs": {
            f"{TASK_A}->{TASK_B}": {
                "cold": aggregate_a_to_b_cold,
                "warm_full": aggregate_a_to_b_warm,
                "results": a_to_b,
            },
            f"{TASK_B}->{TASK_A}": {
                "cold": aggregate_b_to_a_cold,
                "warm_full": aggregate_b_to_a_warm,
                "results": b_to_a,
            },
        },
        "warm_full_delta_b_to_a_minus_a_to_b": {
            "avg_peak_branch_context_debt_total": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_peak_branch_context_debt_total"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_peak_branch_context_debt_total"],
                5,
            ),
            "avg_branch_context_debt_auc": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_branch_context_debt_auc"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_branch_context_debt_auc"],
                5,
            ),
            "avg_branch_context_half_relief_cycle": (
                None
                if aggregate_b_to_a_warm["aggregate_summary"]["avg_branch_context_half_relief_cycle"] is None
                or aggregate_a_to_b_warm["aggregate_summary"]["avg_branch_context_half_relief_cycle"] is None
                else round(
                    aggregate_b_to_a_warm["aggregate_summary"]["avg_branch_context_half_relief_cycle"]
                    - aggregate_a_to_b_warm["aggregate_summary"]["avg_branch_context_half_relief_cycle"],
                    5,
                )
            ),
            "avg_peak_context_branch_transform_debt_total": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_peak_context_branch_transform_debt_total"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_peak_context_branch_transform_debt_total"],
                5,
            ),
            "avg_context_branch_transform_debt_auc": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_context_branch_transform_debt_auc"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_context_branch_transform_debt_auc"],
                5,
            ),
            "avg_context_branch_transform_half_relief_cycle": (
                None
                if aggregate_b_to_a_warm["aggregate_summary"]["avg_context_branch_transform_half_relief_cycle"] is None
                or aggregate_a_to_b_warm["aggregate_summary"]["avg_context_branch_transform_half_relief_cycle"] is None
                else round(
                    aggregate_b_to_a_warm["aggregate_summary"]["avg_context_branch_transform_half_relief_cycle"]
                    - aggregate_a_to_b_warm["aggregate_summary"]["avg_context_branch_transform_half_relief_cycle"],
                    5,
                )
            ),
            "avg_combined_context_balance_auc": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_combined_context_balance_auc"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_combined_context_balance_auc"],
                5,
            ),
            "avg_combined_context_balance_margin_auc": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_combined_context_balance_margin_auc"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_combined_context_balance_margin_auc"],
                5,
            ),
            "avg_negative_combined_balance_cycle_count": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_negative_combined_balance_cycle_count"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_negative_combined_balance_cycle_count"],
                5,
            ),
            "avg_first_strong_combined_balance_cycle": (
                None
                if aggregate_b_to_a_warm["aggregate_summary"]["avg_first_strong_combined_balance_cycle"] is None
                or aggregate_a_to_b_warm["aggregate_summary"]["avg_first_strong_combined_balance_cycle"] is None
                else round(
                    aggregate_b_to_a_warm["aggregate_summary"]["avg_first_strong_combined_balance_cycle"]
                    - aggregate_a_to_b_warm["aggregate_summary"]["avg_first_strong_combined_balance_cycle"],
                    5,
                )
            ),
            "avg_final_combined_context_balance_total": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_final_combined_context_balance_total"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_final_combined_context_balance_total"],
                5,
            ),
            "avg_final_combined_context_balance_margin": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_final_combined_context_balance_margin"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_final_combined_context_balance_margin"],
                5,
            ),
            "avg_final_mean_bit_accuracy": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_final_mean_bit_accuracy"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_final_mean_bit_accuracy"],
                5,
            ),
            "avg_final_exact_matches": round(
                aggregate_b_to_a_warm["aggregate_summary"]["avg_final_exact_matches"]
                - aggregate_a_to_b_warm["aggregate_summary"]["avg_final_exact_matches"],
                5,
            ),
        },
    }


def main() -> None:
    print(json.dumps(analyze_transfer_timecourse(), indent=2))


if __name__ == "__main__":
    main()
