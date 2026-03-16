from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

_PHASE4_ROOT = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_PHASE4_ROOT) not in sys.path:
    sys.path.insert(0, str(_PHASE4_ROOT))

from real_core.consolidation import BasicConsolidationPipeline
from real_core.patterns import ConstraintPattern
from real_core.types import CycleEntry

from .substrate import ConnectionSubstrate


@dataclass
class Phase8ConsolidationPipeline(BasicConsolidationPipeline):
    """Promotes routing attractors into edge-local maintained substrate."""

    support_seed_value: float = 0.32
    pattern_strength: float = 0.45
    min_route_uses: int = 2
    positive_delta_floor: float = 0.0
    negative_delta_floor: float = -0.02

    def consolidate(
        self,
        entries: List[CycleEntry],
        substrate=None,
    ) -> List[CycleEntry]:
        retained = super().consolidate(entries, substrate)
        if isinstance(substrate, ConnectionSubstrate):
            self._promote_route_patterns(entries, substrate)
        return retained

    def _promote_route_patterns(
        self,
        entries: List[CycleEntry],
        substrate: ConnectionSubstrate,
    ) -> None:
        route_entries = [entry for entry in entries if entry.action.startswith("route:")]
        if len(route_entries) < self.min_route_uses:
            return

        grouped: Dict[str, List[CycleEntry]] = {}
        for entry in route_entries:
            neighbor_id = entry.action.split(":", 1)[1]
            if neighbor_id not in substrate.neighbor_ids:
                continue
            grouped.setdefault(neighbor_id, []).append(entry)

        if not grouped:
            return

        promoted_positive: List[str] = []
        for neighbor_id, neighbor_entries in grouped.items():
            if len(neighbor_entries) < self.min_route_uses:
                continue

            mean_delta = sum(entry.delta for entry in neighbor_entries) / len(neighbor_entries)
            mean_coherence = sum(entry.coherence for entry in neighbor_entries) / len(neighbor_entries)
            support_bias = 0.85 if mean_delta >= self.positive_delta_floor else 0.25
            if mean_delta >= self.positive_delta_floor:
                promoted_positive.append(neighbor_id)
                if substrate.support(neighbor_id) < self.support_seed_value:
                    substrate.seed_support((neighbor_id,), value=self.support_seed_value)
                pattern = self._build_pattern(
                    substrate=substrate,
                    focus_neighbor=neighbor_id,
                    valence=min(1.0, 0.4 + max(0.0, mean_delta) * 8.0),
                    strength=self.pattern_strength,
                    coherence_level=mean_coherence,
                    focus_value=support_bias,
                    source="route_attractor",
                )
                self._merge_or_append_pattern(substrate, pattern)
            elif mean_delta <= self.negative_delta_floor:
                pattern = self._build_pattern(
                    substrate=substrate,
                    focus_neighbor=neighbor_id,
                    valence=-0.55,
                    strength=self.pattern_strength * 0.8,
                    coherence_level=mean_coherence,
                    focus_value=0.10,
                    source="route_trough",
                )
                self._merge_or_append_pattern(substrate, pattern)

        if len(promoted_positive) > 1:
            substrate.seed_support(promoted_positive, value=self.support_seed_value)

    def _build_pattern(
        self,
        substrate: ConnectionSubstrate,
        focus_neighbor: str,
        *,
        valence: float,
        strength: float,
        coherence_level: float,
        focus_value: float,
        source: str,
    ) -> ConstraintPattern:
        dim_scores = {}
        dim_trends = substrate.current_dim_trends()
        for neighbor_id in substrate.neighbor_ids:
            key = substrate.edge_key(neighbor_id)
            if neighbor_id == focus_neighbor:
                dim_scores[key] = focus_value
                dim_trends[key] = max(dim_trends.get(key, 0.0), 0.08 if valence > 0 else -0.08)
            else:
                dim_scores[key] = 0.25 if valence > 0 else 0.55
                dim_trends[key] = dim_trends.get(key, 0.0)
        return ConstraintPattern(
            dim_scores=dim_scores,
            dim_trends=dim_trends,
            valence=valence,
            strength=strength,
            coherence_level=coherence_level,
            source=source,
        )

    def _merge_or_append_pattern(
        self,
        substrate: ConnectionSubstrate,
        pattern: ConstraintPattern,
    ) -> None:
        for existing in substrate.constraint_patterns:
            if existing.valence * pattern.valence <= 0:
                continue
            similarity = existing.match_score(pattern.dim_scores, pattern.dim_trends)
            if similarity >= 0.75:
                existing.match_count += 1
                existing.strength = min(1.0, existing.strength + 0.08)
                existing.coherence_level = (
                    existing.coherence_level * 0.7 + pattern.coherence_level * 0.3
                )
                return
        substrate.add_pattern(pattern)
