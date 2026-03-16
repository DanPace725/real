"""Two-layer memory substrate with bistable dynamics.

Fast layer: volatile, free reads, updated each cycle from observation.
Slow layer: persistent, costly writes, decays unless actively maintained.
Bistability from threshold dynamics: below threshold, accelerated decay
pulls entries toward zero; above threshold, slow decay is manageable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

DIMENSIONS = (
    "continuity",
    "vitality",
    "contextual_fit",
    "differentiation",
    "accountability",
    "reflexivity",
)

INVEST_INCREMENT = 0.20
MAX_PATTERNS = 12
PATTERN_DECAY = 0.015
PATTERN_MATCH_THRESHOLD = 0.35
PATTERN_REFRESH = 0.10
MERGE_SIMILARITY_THRESHOLD = 0.70
MERGE_ALPHA = 0.3


@dataclass
class ConstraintPattern:
    """A compressed multi-dimensional signature promoted from experience.

    Positive-valence patterns represent recognized attractors (familiar
    good configurations). Negative-valence patterns represent recognized
    decline trajectories (configurations that preceded incoherence).

    Strength decays each tick and is refreshed when matched. Patterns
    that stop being recognized fade out naturally.
    """
    dim_scores: dict[str, float]
    dim_trends: dict[str, float]
    valence: float
    strength: float
    coherence_level: float
    match_count: int = 0
    source: str = "attractor"

    def match_score(
        self, current_dims: dict[str, float], current_trends: dict[str, float]
    ) -> float:
        if not self.dim_scores:
            return 0.0
        score_diffs = []
        trend_diffs = []
        for d in DIMENSIONS:
            score_diffs.append(
                abs(current_dims.get(d, 0.5) - self.dim_scores.get(d, 0.5))
            )
            trend_diffs.append(
                abs(current_trends.get(d, 0.0) - self.dim_trends.get(d, 0.0))
            )
        mean_score_diff = sum(score_diffs) / len(score_diffs)
        mean_trend_diff = sum(trend_diffs) / len(trend_diffs)
        score_sim = max(0.0, 1.0 - mean_score_diff * 5.0)
        trend_sim = max(0.0, 1.0 - mean_trend_diff * 15.0)
        return score_sim * 0.65 + trend_sim * 0.35

    def to_dict(self) -> dict:
        return {
            "dim_scores": self.dim_scores,
            "dim_trends": self.dim_trends,
            "valence": self.valence,
            "strength": self.strength,
            "coherence_level": self.coherence_level,
            "match_count": self.match_count,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConstraintPattern":
        return cls(**data)


@dataclass
class SubstrateConfig:
    slow_decay: float = 0.03
    bistable_threshold: float = 0.25
    write_base_cost: float = 0.15
    maintain_base_cost: float = 0.03
    neighbor_discount: float = 0.12
    coupling_window: int = 20
    accelerated_decay_factor: float = 3.0
    baseline_fast_variance: float = 0.08
    velocity_alpha: float = 0.30


@dataclass
class MemorySubstrate:
    config: SubstrateConfig = field(default_factory=SubstrateConfig)
    fast: dict[str, float] = field(default_factory=dict)
    slow: dict[str, float] = field(default_factory=dict)
    slow_age: dict[str, int] = field(default_factory=dict)
    slow_velocity: dict[str, float] = field(default_factory=dict)
    constraint_patterns: list[ConstraintPattern] = field(default_factory=list)
    pattern_match_pos: float = 0.0
    pattern_match_neg: float = 0.0
    pattern_dim_modulation: dict[str, float] = field(default_factory=dict)
    _slow_prior: dict[str, float] = field(default_factory=dict, repr=False)
    _fast_history: list[dict[str, float]] = field(
        default_factory=list, repr=False
    )
    _dim_history: list[dict[str, float]] = field(
        default_factory=list, repr=False
    )

    def __post_init__(self):
        for dim in DIMENSIONS:
            self.fast.setdefault(dim, 0.0)
            self.slow.setdefault(dim, 0.0)
            self.slow_age.setdefault(dim, 0)
            self.slow_velocity.setdefault(dim, 0.0)
            self._slow_prior.setdefault(dim, 0.0)

    # ------------------------------------------------------------------
    # Core tick: decay and record
    # ------------------------------------------------------------------

    def tick(self):
        """Advance one cycle: decay unmaintained slow entries, update velocity
        EMA, record fast snapshot.

        Velocity tracks the net change per cycle (invest + maintain - decay).
        Negative velocity = eroding support. Positive = growing/maintained.
        """
        for dim in DIMENSIONS:
            val = self.slow[dim]
            if val <= 0:
                continue
            decay = self.config.slow_decay
            if val < self.config.bistable_threshold:
                decay *= self.config.accelerated_decay_factor
            self.slow[dim] = max(0.0, val - decay)
            self.slow_age[dim] += 1

        alpha = self.config.velocity_alpha
        for dim in DIMENSIONS:
            delta = self.slow[dim] - self._slow_prior.get(dim, 0.0)
            self.slow_velocity[dim] = (
                alpha * delta + (1.0 - alpha) * self.slow_velocity.get(dim, 0.0)
            )
            self._slow_prior[dim] = self.slow[dim]

        self._decay_patterns()

        self._fast_history.append(dict(self.fast))
        if len(self._fast_history) > self.config.coupling_window:
            self._fast_history.pop(0)

    def update_fast(self, observation: dict[str, float]):
        """Overwrite fast layer from environment observation."""
        for dim in DIMENSIONS:
            if dim in observation:
                self.fast[dim] = observation[dim]

    # ------------------------------------------------------------------
    # Slow-layer write and maintain
    # ------------------------------------------------------------------

    def write_slow(self, key: str, atp_budget: float) -> Optional[float]:
        """Invest in slow-layer entry. Returns ATP consumed, or None if
        the budget is insufficient."""
        cost = self.write_cost(key)
        if atp_budget < cost:
            return None
        self.slow[key] = min(1.0, self.slow[key] + INVEST_INCREMENT)
        self.slow_age[key] = 0
        return cost

    def maintain_slow(self, key: str, atp_budget: float) -> Optional[float]:
        """Maintain one active entry, restoring twice the per-tick decay.
        Returns cost or None."""
        if self.slow[key] <= 0:
            return None
        cost = self.maintain_cost(key)
        if atp_budget < cost:
            return None
        self.slow[key] = min(1.0, self.slow[key] + self.config.slow_decay * 2)
        self.slow_age[key] = 0
        return cost

    def maintain_all(self, atp_budget: float) -> float:
        """Maintain every active entry. Returns total ATP consumed."""
        total = 0.0
        for dim in DIMENSIONS:
            if self.is_active(dim):
                cost = self.maintain_slow(dim, atp_budget - total)
                if cost is not None:
                    total += cost
        return total

    # ------------------------------------------------------------------
    # Cost functions (history-dependent via neighbor discount)
    # ------------------------------------------------------------------

    def write_cost(self, key: str) -> float:
        """Cost to invest, reduced by active neighbors."""
        base = self.config.write_base_cost
        neighbors = sum(
            1 for d in DIMENSIONS if d != key and self.is_active(d)
        )
        discount = min(neighbors * self.config.neighbor_discount, 0.60)
        return base * (1.0 - discount)

    def maintain_cost(self, key: str) -> float:
        """Cost to maintain, reduced by active neighbors."""
        base = self.config.maintain_base_cost
        neighbors = sum(
            1 for d in DIMENSIONS if d != key and self.is_active(d)
        )
        discount = min(neighbors * self.config.neighbor_discount, 0.50)
        return base * (1.0 - discount)

    # ------------------------------------------------------------------
    # Bistability and coupling queries
    # ------------------------------------------------------------------

    def is_active(self, key: str) -> bool:
        return self.slow.get(key, 0.0) >= self.config.bistable_threshold

    def active_count(self) -> int:
        return sum(1 for d in DIMENSIONS if self.is_active(d))

    def coupling_score(self) -> float:
        """How well does the slow layer reduce fast-layer variance.

        For each active dimension, measure the variance reduction compared
        to a baseline. High slow value + large variance reduction = strong
        coupling. This captures the actual mechanism: the slow layer
        stabilizes observation, not shifts its level.
        """
        if len(self._fast_history) < 3:
            return 0.0
        total = 0.0
        active = 0
        baseline_var = self.config.baseline_fast_variance
        for dim in DIMENSIONS:
            slow_val = self.slow.get(dim, 0.0)
            if slow_val < self.config.bistable_threshold:
                continue
            active += 1
            fast_vals = [h.get(dim, 0.0) for h in self._fast_history]
            fast_var = (
                statistics.variance(fast_vals)
                if len(fast_vals) > 1
                else baseline_var
            )
            reduction = max(0.0, 1.0 - fast_var / max(baseline_var, 1e-6))
            total += slow_val * reduction
        return total / max(active, 1)

    # ------------------------------------------------------------------
    # Constraint patterns: recognition from accumulated experience
    # ------------------------------------------------------------------

    def update_dim_context(self, dim_scores: dict[str, float]):
        """Called by the engine each cycle with scored dimension values.
        Maintains a rolling window for trend computation and pattern matching."""
        self._dim_history.append(dict(dim_scores))
        if len(self._dim_history) > self.config.coupling_window:
            self._dim_history.pop(0)
        self._match_patterns()

    def current_dim_trends(self) -> dict[str, float]:
        """Compute per-dimension score trends over the recent window."""
        if len(self._dim_history) < 4:
            return {d: 0.0 for d in DIMENSIONS}
        recent = self._dim_history[-6:]
        half = len(recent) // 2
        first_half = recent[:half]
        second_half = recent[half:]
        trends = {}
        for d in DIMENSIONS:
            early = sum(h.get(d, 0.5) for h in first_half) / max(len(first_half), 1)
            late = sum(h.get(d, 0.5) for h in second_half) / max(len(second_half), 1)
            trends[d] = late - early
        return trends

    def _match_patterns(self):
        """Check current dimension state against all stored constraint patterns.

        Computes per-dimension modulation: each matching pattern contributes
        to the dimensions where its signature is distinctive.  Positive
        patterns sharpen the dimensions they score highly on; negative
        patterns add noise to the dimensions they score weakly on.

        Also maintains the legacy scalar pattern_match_pos / pattern_match_neg
        for snapshot logging.
        """
        zero_mod = {d: 0.0 for d in DIMENSIONS}
        if not self.constraint_patterns or len(self._dim_history) < 3:
            self.pattern_match_pos = 0.0
            self.pattern_match_neg = 0.0
            self.pattern_dim_modulation = zero_mod
            return

        current_dims = self._dim_history[-1]
        current_trends = self.current_dim_trends()
        pos_scalar = neg_scalar = 0.0
        dim_mod = {d: 0.0 for d in DIMENSIONS}

        for p in self.constraint_patterns:
            score = p.match_score(current_dims, current_trends)
            if score < PATTERN_MATCH_THRESHOLD:
                continue
            p.match_count += 1
            p.strength = min(1.0, p.strength + PATTERN_REFRESH)
            weighted = score * p.strength

            if p.valence > 0:
                pos_scalar += weighted * p.valence
            else:
                neg_scalar += weighted * abs(p.valence)

            for d in DIMENSIONS:
                dim_score = p.dim_scores.get(d, 0.5)
                if p.valence > 0:
                    prominence = max(0.0, dim_score - 0.5)
                    dim_mod[d] += weighted * p.valence * prominence * 0.25
                else:
                    deficit = max(0.0, 0.5 - dim_score)
                    dim_mod[d] += weighted * p.valence * deficit * 0.40

        for d in DIMENSIONS:
            dim_mod[d] = max(-0.20, min(0.20, dim_mod[d]))

        self.pattern_match_pos = min(pos_scalar, 1.0)
        self.pattern_match_neg = min(neg_scalar, 1.0)
        self.pattern_dim_modulation = dim_mod

    def add_pattern(self, pattern: ConstraintPattern):
        """Add a constraint pattern with diversity enforcement.

        If a same-polarity pattern with high similarity already exists,
        merge via EMA rather than adding a duplicate.  When genuinely
        novel and at capacity, prune the most redundant pattern (the one
        whose nearest neighbor is closest) to maximise state-space
        coverage.
        """
        for existing in self.constraint_patterns:
            if existing.valence * pattern.valence <= 0:
                continue
            sim = existing.match_score(pattern.dim_scores, pattern.dim_trends)
            if sim >= MERGE_SIMILARITY_THRESHOLD:
                a = MERGE_ALPHA
                for d in DIMENSIONS:
                    existing.dim_scores[d] += a * (
                        pattern.dim_scores.get(d, 0.5) - existing.dim_scores[d]
                    )
                    existing.dim_trends[d] += a * (
                        pattern.dim_trends.get(d, 0.0) - existing.dim_trends[d]
                    )
                existing.coherence_level += a * (
                    pattern.coherence_level - existing.coherence_level
                )
                existing.strength = min(1.0, existing.strength + 0.05)
                return

        self.constraint_patterns.append(pattern)
        if len(self.constraint_patterns) > MAX_PATTERNS:
            self._prune_most_redundant()

    def _prune_most_redundant(self):
        """Remove the pattern that is most redundant — the one whose
        nearest neighbor is most similar.  Among ties, drop the weaker."""
        n = len(self.constraint_patterns)
        if n <= MAX_PATTERNS:
            return
        worst_idx = 0
        worst_nn_sim = -1.0
        worst_strength = float("inf")
        for i, pi in enumerate(self.constraint_patterns):
            best_sim = 0.0
            for j, pj in enumerate(self.constraint_patterns):
                if i == j:
                    continue
                sim = pi.match_score(pj.dim_scores, pj.dim_trends)
                if sim > best_sim:
                    best_sim = sim
            if (best_sim > worst_nn_sim
                    or (best_sim == worst_nn_sim
                        and pi.strength < worst_strength)):
                worst_nn_sim = best_sim
                worst_strength = pi.strength
                worst_idx = i
        self.constraint_patterns.pop(worst_idx)

    def _decay_patterns(self):
        """Decay pattern strength each tick. Prune dead patterns."""
        for p in self.constraint_patterns:
            p.strength = max(0.0, p.strength - PATTERN_DECAY)
        self.constraint_patterns = [
            p for p in self.constraint_patterns if p.strength > 0.02
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_slow(self) -> dict:
        """Serialize slow layer for cross-session persistence."""
        return {
            "slow": dict(self.slow),
            "slow_age": dict(self.slow_age),
            "slow_velocity": dict(self.slow_velocity),
            "patterns": [p.to_dict() for p in self.constraint_patterns],
        }

    def load_slow(self, data: dict):
        """Restore slow layer from saved state."""
        for dim in DIMENSIONS:
            self.slow[dim] = data["slow"].get(dim, 0.0)
            self.slow_age[dim] = data["slow_age"].get(dim, 0)
            self.slow_velocity[dim] = data.get("slow_velocity", {}).get(dim, 0.0)
            self._slow_prior[dim] = self.slow[dim]
        self.constraint_patterns = [
            ConstraintPattern.from_dict(p)
            for p in data.get("patterns", [])
        ]

    def snapshot(self) -> dict:
        """Full state snapshot for logging."""
        return {
            "fast": dict(self.fast),
            "slow": dict(self.slow),
            "slow_age": dict(self.slow_age),
            "slow_velocity": dict(self.slow_velocity),
            "active": {d: self.is_active(d) for d in DIMENSIONS},
            "active_count": self.active_count(),
            "coupling_score": self.coupling_score(),
            "pattern_count": len(self.constraint_patterns),
            "pattern_match_pos": self.pattern_match_pos,
            "pattern_match_neg": self.pattern_match_neg,
            "pattern_dim_modulation": dict(self.pattern_dim_modulation),
        }
