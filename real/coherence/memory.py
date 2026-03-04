"""
Episodic log — the learning substrate.

The log records every cycle's state, action, and coherence outcome.
It IS the agent's memory.  Learning happens by querying this log for
patterns: what worked in situations like this one?

Consolidation during REST cycles uses three-tier selection:
    - Attractors:  highest coherence (where the agent wants to go)
    - Surprises:   highest |delta| (maximum causal signal)
    - Boundaries:  closest to GCO threshold (where choice matters most)

This is meaningfully different from keeping top-N.  A −0.15 delta is as
informative as +0.15.  Near-threshold entries are the most sensitive to
action choice.  A system that only remembers its best moments cannot
navigate.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LogEntry:
    """
    One cycle's complete record.

    Attributes
    ----------
    cycle : int
        Cycle number within the session.
    timestamp : float
        Unix timestamp when the cycle completed.
    state_before : dict
        System state snapshot before action.
    action : str
        Name of the action taken.
    action_params : dict
        Parameters passed to the action.
    state_after : dict
        System state snapshot after action.
    coherence_score : float
        Composite coherence score after action.
    dimension_scores : dict
        Individual P1–P6 dimension scores.
    delta_coherence : float
        Change in coherence from prior cycle.
    compute_cost_secs : float
        Wall-clock time the action took (ATP).
    notes : str
        Free-form annotation.
    """
    cycle: int
    timestamp: float
    state_before: Dict[str, Any]
    action: str
    action_params: Dict[str, Any]
    state_after: Dict[str, Any]
    coherence_score: float
    dimension_scores: Dict[str, float]
    delta_coherence: float = 0.0
    compute_cost_secs: float = 0.0
    notes: str = ""


class EpisodicLog:
    """
    Bounded episodic memory with three-tier consolidation.

    Parameters
    ----------
    maxlen : int
        Maximum log entries before oldest are dropped.
    """

    def __init__(self, maxlen: int = 500) -> None:
        self.log: deque[LogEntry] = deque(maxlen=maxlen)
        self.consolidated_count: int = 0

    # ── Recording ─────────────────────────────────────────────────────

    def record(self, entry: LogEntry) -> None:
        """Append a new cycle record."""
        self.log.append(entry)

    @property
    def size(self) -> int:
        return len(self.log)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self.log)

    def recent(self, n: int = 10) -> list[LogEntry]:
        """Last N entries."""
        return list(self.log)[-n:]

    # ── Querying (trail scoring) ──────────────────────────────────────

    def entries_for_action(self, action: str) -> list[LogEntry]:
        """All entries where a specific action was taken."""
        return [e for e in self.log if e.action == action]

    def mean_delta_for_action(self, action: str) -> float:
        """Average delta coherence for a given action type."""
        entries = self.entries_for_action(action)
        if not entries:
            return 0.0
        return sum(e.delta_coherence for e in entries) / len(entries)

    def mean_efficiency_for_action(self, action: str) -> float:
        """Average delta/cost for a given action type (metabolic efficiency)."""
        entries = self.entries_for_action(action)
        if not entries:
            return 0.0
        efficiencies = []
        for e in entries:
            cost = max(e.compute_cost_secs, 0.001)  # avoid division by zero
            efficiencies.append(e.delta_coherence / cost)
        return sum(efficiencies) / len(efficiencies)

    def mean_cost_for_action(self, action: str) -> float:
        """Average compute_cost_secs for a given action type.

        Returns 0.0 when the action has never been taken (selector falls
        back to no efficiency weighting in that case).
        """
        entries = self.entries_for_action(action)
        if not entries:
            return 0.0
        return sum(e.compute_cost_secs for e in entries) / len(entries)

    def self_model(self) -> dict:
        """Alias for build_self_model() — convenience accessor."""
        return self.build_self_model()


    # ── Analytical queries ─────────────────────────────────────────────
    # These power the query_memory, compare_state, and introspect actions.

    def best_actions_by_dimension(self) -> dict[str, list[tuple[str, float]]]:
        """
        For each coherence dimension, rank actions by mean contribution.

        Returns {dimension: [(action, mean_score), ...]} sorted descending.
        """
        # Collect dimension scores per action
        action_dims: dict[str, dict[str, list[float]]] = {}
        for e in self.log:
            if e.action not in action_dims:
                action_dims[e.action] = {}
            for dim, score in e.dimension_scores.items():
                action_dims[e.action].setdefault(dim, []).append(score)

        # Compute means and rank
        result: dict[str, list[tuple[str, float]]] = {}
        all_dims = set()
        for scores_by_dim in action_dims.values():
            all_dims.update(scores_by_dim.keys())

        for dim in sorted(all_dims):
            ranked = []
            for action, scores_map in action_dims.items():
                vals = scores_map.get(dim, [])
                if vals:
                    ranked.append((action, sum(vals) / len(vals)))
            ranked.sort(key=lambda x: x[1], reverse=True)
            result[dim] = ranked
        return result

    def action_trail_summary(self) -> dict[str, dict[str, Any]]:
        """
        Summary of each action's trail performance.

        Returns {action: {count, mean_delta, mean_coherence, mean_cost, efficiency}}.
        """
        trails: dict[str, list[LogEntry]] = {}
        for e in self.log:
            trails.setdefault(e.action, []).append(e)

        result = {}
        for action, entries in trails.items():
            n = len(entries)
            mean_delta = sum(e.delta_coherence for e in entries) / n
            mean_coherence = sum(e.coherence_score for e in entries) / n
            mean_cost = sum(e.compute_cost_secs for e in entries) / n
            efficiency = mean_delta / max(mean_cost, 0.001)
            result[action] = {
                "count": n,
                "mean_delta": round(mean_delta, 4),
                "mean_coherence": round(mean_coherence, 4),
                "mean_cost_secs": round(mean_cost, 5),
                "efficiency": round(efficiency, 4),
            }
        return result

    def dimension_trends(self, window: int = 10) -> dict[str, dict[str, float]]:
        """
        For each dimension, compute recent mean vs overall mean.

        Returns {dimension: {overall, recent, trend}} where trend is the
        difference (positive = improving).
        """
        all_entries = list(self.log)
        recent_entries = all_entries[-window:] if len(all_entries) >= window else all_entries

        dims: set[str] = set()
        for e in all_entries:
            dims.update(e.dimension_scores.keys())

        result = {}
        for dim in sorted(dims):
            all_vals = [e.dimension_scores.get(dim, 0) for e in all_entries]
            recent_vals = [e.dimension_scores.get(dim, 0) for e in recent_entries]
            overall = sum(all_vals) / max(len(all_vals), 1)
            recent = sum(recent_vals) / max(len(recent_vals), 1)
            result[dim] = {
                "overall": round(overall, 4),
                "recent": round(recent, 4),
                "trend": round(recent - overall, 4),
            }
        return result

    def state_comparison(self, current_state: dict) -> dict[str, Any]:
        """
        Compare current system state against historical baselines.

        Returns drift analysis for each numeric state field.
        """
        all_entries = list(self.log)
        if not all_entries:
            return {"comparison": "no_history"}

        # Collect historical state_after values
        historical: dict[str, list[float]] = {}
        for e in all_entries:
            for k, v in e.state_after.items():
                if isinstance(v, (int, float)):
                    historical.setdefault(k, []).append(v)

        result = {}
        for field_name, values in historical.items():
            hist_mean = sum(values) / len(values)
            hist_min = min(values)
            hist_max = max(values)
            current_val = current_state.get(field_name)
            if current_val is not None and isinstance(current_val, (int, float)):
                drift = current_val - hist_mean
                # Normalize drift relative to range
                rng = max(hist_max - hist_min, 0.001)
                normalized_drift = drift / rng
                result[field_name] = {
                    "current": round(current_val, 4),
                    "historical_mean": round(hist_mean, 4),
                    "historical_range": [round(hist_min, 4), round(hist_max, 4)],
                    "drift": round(drift, 4),
                    "normalized_drift": round(normalized_drift, 4),
                }
        return result

    def build_self_model(self) -> dict[str, Any]:
        """
        Self-model: what the agent can say about itself from its own log.

        Analyzes behavioral patterns, identifies strengths/weaknesses,
        and characterizes the agent's current developmental stage.
        """
        if self.size < 5:
            return {"model": "insufficient_data", "entries": self.size}

        entries = list(self.log)

        # Action distribution
        action_counts: dict[str, int] = {}
        for e in entries:
            action_counts[e.action] = action_counts.get(e.action, 0) + 1
        total_actions = sum(action_counts.values())

        # Most and least used actions
        sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
        dominant_action = sorted_actions[0][0] if sorted_actions else "none"
        # 12 actions in full vocabulary
        action_diversity = len(action_counts) / 12 if action_counts else 0

        # Coherence trajectory
        coherence_vals = [e.coherence_score for e in entries]
        first_quarter = coherence_vals[:len(coherence_vals)//4] or coherence_vals
        last_quarter = coherence_vals[-(len(coherence_vals)//4):] or coherence_vals
        trajectory = (
            sum(last_quarter) / len(last_quarter)
            - sum(first_quarter) / len(first_quarter)
        )

        # Strongest and weakest dimensions
        dim_means: dict[str, float] = {}
        for e in entries:
            for dim, score in e.dimension_scores.items():
                dim_means.setdefault(dim, [])
                dim_means[dim].append(score)
        dim_avgs = {d: sum(v)/len(v) for d, v in dim_means.items()}
        strongest = max(dim_avgs, key=dim_avgs.get) if dim_avgs else "unknown"
        weakest = min(dim_avgs, key=dim_avgs.get) if dim_avgs else "unknown"

        # Metabolic profile
        total_compute = sum(e.compute_cost_secs for e in entries)
        mean_compute = total_compute / len(entries)

        # GCO proximity — how often is the agent near the threshold?
        gco_proximate = sum(
            1 for e in entries if abs(e.coherence_score - 0.65) < 0.1
        )

        return {
            "entries_analyzed": len(entries),
            "consolidations": self.consolidated_count,
            "dominant_action": dominant_action,
            "action_diversity": round(action_diversity, 2),
            "coherence_mean": round(sum(coherence_vals) / len(coherence_vals), 4),
            "coherence_trajectory": round(trajectory, 4),
            "strongest_dimension": strongest,
            "weakest_dimension": weakest,
            "dimension_averages": {d: round(v, 4) for d, v in dim_avgs.items()},
            "total_compute_secs": round(total_compute, 4),
            "mean_compute_per_cycle": round(mean_compute, 5),
            "gco_proximate_fraction": round(gco_proximate / len(entries), 3),
        }

    # ── Consolidation ─────────────────────────────────────────────────

    def consolidate(
        self,
        keep_attractors: int = 15,
        keep_surprises: int = 15,
        keep_boundaries: int = 10,
        gco_threshold: float = 0.65,
    ) -> int:
        """
        Three-tier memory consolidation during REST.

        Retains:
          - Attractors:  top coherence scores (where the agent wants to go)
          - Surprises:   highest |delta| (maximum causal signal)
          - Boundaries:  closest to GCO threshold (where choice matters)

        Returns the number of entries pruned.
        """
        if self.size < (keep_attractors + keep_surprises + keep_boundaries):
            return 0  # Not enough entries to consolidate

        entries = list(self.log)

        # Tier 1: Attractors — highest coherence
        attractors = sorted(entries, key=lambda e: e.coherence_score, reverse=True)
        attractors = attractors[:keep_attractors]

        # Tier 2: Surprises — highest |delta| (both positive and negative)
        surprises = sorted(entries, key=lambda e: abs(e.delta_coherence), reverse=True)
        surprises = surprises[:keep_surprises]

        # Tier 3: Boundaries — closest to GCO threshold
        boundaries = sorted(entries, key=lambda e: abs(e.coherence_score - gco_threshold))
        boundaries = boundaries[:keep_boundaries]

        # Union of all three tiers (deduplicated by cycle number)
        kept_cycles = set()
        consolidated: list[LogEntry] = []
        for entry in attractors + surprises + boundaries:
            if entry.cycle not in kept_cycles:
                kept_cycles.add(entry.cycle)
                consolidated.append(entry)

        # Sort by cycle for temporal ordering
        consolidated.sort(key=lambda e: e.cycle)

        pruned = len(entries) - len(consolidated)
        self.log = deque(consolidated, maxlen=self.log.maxlen)
        self.consolidated_count += 1
        return pruned

    # ── Persistence ───────────────────────────────────────────────────

    def save(self, path: Path) -> dict:
        """Save log to JSON.  Returns a summary dict."""
        data = {
            "entries": [asdict(e) for e in self.log],
            "consolidated_count": self.consolidated_count,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {
            "entries_saved": len(self.log),
            "path": str(path),
        }

    def load(self, path: Path) -> int:
        """Load log from JSON.  Returns number of entries loaded."""
        if not path.exists():
            return 0
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        for edata in entries:
            entry = LogEntry(**edata)
            self.log.append(entry)
        self.consolidated_count = data.get("consolidated_count", 0)
        return len(entries)
