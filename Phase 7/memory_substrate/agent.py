"""Simple coherence-reactive agent for Phase 0 substrate testing.

Selects actions based on current coherence, slow-layer state, and
remaining ATP budget. Uses a lightweight explore/invest/maintain/observe
policy — not a full CFAR selector — to keep the focus on substrate
dynamics rather than selector sophistication.

Priority order:
  1. Maintain entries that are close to falling below bistable threshold
  2. Invest in new dimensions (the primary value-creating action)
  3. Observe (keep the coherence model fed)
  4. Rest (when budget is depleted)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .substrate import DIMENSIONS, MemorySubstrate

OBSERVE_COST = 0.015
EXPLORE_COST = 0.03
REST_COST = 0.0

MAINTENANCE_MARGIN = 0.08


@dataclass
class SubstrateAgent:
    substrate: MemorySubstrate
    session_budget: float = 5.0
    budget_remaining: float = 0.0
    exploration_rate: float = 0.20
    rng: random.Random = field(default_factory=random.Random)

    coherence: float = 0.0
    dimensions: dict[str, float] = field(default_factory=dict)
    action_history: list[str] = field(default_factory=list)

    def reset_budget(self):
        self.budget_remaining = self.session_budget

    def available_actions(self) -> list[str]:
        actions = ["observe", "rest", "explore", "maintain"]
        for dim in DIMENSIONS:
            actions.append(f"invest_{dim}")
        return actions

    def select_action(self) -> str:
        if self.budget_remaining < OBSERVE_COST:
            return "rest"

        if self.rng.random() < self.exploration_rate:
            return self._random_affordable()

        # URGENT: maintain entries about to fall below bistable threshold
        if self._needs_urgent_maintenance() and self._can_afford_maintain():
            return "maintain"

        # INVEST: build new slow-layer infrastructure on weak dimensions
        invest_target = self._pick_invest_target()
        if invest_target is not None:
            return f"invest_{invest_target}"

        # NON-URGENT MAINTAIN: top up entries that are decaying but not critical
        if self.substrate.active_count() > 0 and self._any_decaying():
            if self._can_afford_maintain():
                return "maintain"

        return "observe"

    def execute_action(self, action: str) -> float:
        """Execute and return ATP cost."""
        if action == "rest":
            return REST_COST
        if action == "observe":
            self.budget_remaining -= OBSERVE_COST
            return OBSERVE_COST
        if action == "explore":
            self.budget_remaining -= EXPLORE_COST
            return EXPLORE_COST
        if action == "maintain":
            cost = self.substrate.maintain_all(self.budget_remaining)
            self.budget_remaining -= cost
            return cost
        if action.startswith("invest_"):
            dim = action[len("invest_"):]
            cost = self.substrate.write_slow(dim, self.budget_remaining)
            if cost is not None:
                self.budget_remaining -= cost
                return cost
            return 0.0
        return 0.0

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------

    def _needs_urgent_maintenance(self) -> bool:
        """True if any active entry is within MAINTENANCE_MARGIN of threshold."""
        threshold = self.substrate.config.bistable_threshold
        for dim in DIMENSIONS:
            if self.substrate.is_active(dim):
                if self.substrate.slow[dim] < threshold + MAINTENANCE_MARGIN:
                    return True
        return False

    def _any_decaying(self) -> bool:
        """True if any active entry has aged since last maintenance."""
        for dim in DIMENSIONS:
            if self.substrate.is_active(dim) and self.substrate.slow_age[dim] > 2:
                return True
        return False

    def _pick_invest_target(self) -> str | None:
        """Pick the best dimension to invest in, or None."""
        if not self.dimensions:
            return None

        candidates = []
        for dim in DIMENSIONS:
            dim_score = self.dimensions.get(dim, 0)
            slow_val = self.substrate.slow.get(dim, 0.0)
            cost = self.substrate.write_cost(dim)

            if cost > self.budget_remaining:
                continue

            if not self.substrate.is_active(dim) and dim_score < 0.65:
                candidates.append((dim, dim_score, slow_val))
            elif self.substrate.is_active(dim) and slow_val < 0.50:
                candidates.append((dim, dim_score, slow_val))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def _random_affordable(self) -> str:
        affordable = [
            a
            for a in self.available_actions()
            if self._estimated_cost(a) <= self.budget_remaining
        ]
        return self.rng.choice(affordable) if affordable else "rest"

    def _can_afford_maintain(self) -> bool:
        total = sum(
            self.substrate.maintain_cost(d)
            for d in DIMENSIONS
            if self.substrate.is_active(d)
        )
        return self.budget_remaining >= total

    def _estimated_cost(self, action: str) -> float:
        if action == "rest":
            return REST_COST
        if action == "observe":
            return OBSERVE_COST
        if action == "explore":
            return EXPLORE_COST
        if action == "maintain":
            return sum(
                self.substrate.maintain_cost(d)
                for d in DIMENSIONS
                if self.substrate.is_active(d)
            )
        if action.startswith("invest_"):
            dim = action[len("invest_"):]
            return self.substrate.write_cost(dim)
        return 0.0
