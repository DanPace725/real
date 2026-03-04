"""
Action selector — CFAR-based exploration/exploitation with dimension guidance.

Uses a Constraint-Fluctuation-Attention-Resolution strategy to balance
exploration (novel actions) against exploitation (known-good trails).

Three operational modes:
    FLUCTUATION:  high exploration — random action, weighted by diversity
    CONSTRAINT:   trail following — pick action with best trail score
    GUIDED:       dimension targeting — pick action that improves the
                  weakest coherence dimension, closing the feedback loop

Mode switching is driven by recent coherence deltas: if coherence is
improving, exploit the trail.  If stagnant or declining, either fluctuate
or use guided mode to target the specific dimension pulling the score down.
"""

from __future__ import annotations

import random
from enum import Enum
from typing import Optional

from real.coherence.memory import EpisodicLog
from real.boundary.vocabulary import ActionDef, VOCABULARY


class SelectionMode(str, Enum):
    FLUCTUATION = "fluctuation"
    CONSTRAINT = "constraint"
    GUIDED = "guided"


class ActionSelector:
    """
    CFAR-based action selection with dimension guidance.

    Parameters
    ----------
    exploration_rate : float
        Base probability of choosing FLUCTUATION mode. Decays as
        the agent develops (more log entries = more trail data).
    stagnation_window : int
        Number of recent cycles to check for improvement.
    stagnation_threshold : float
        If mean recent delta is below this, switch to FLUCTUATION.
    guided_threshold : int
        Minimum log entries before GUIDED mode activates.
    """

    def __init__(
        self,
        exploration_rate: float = 0.40,
        stagnation_window: int = 5,
        stagnation_threshold: float = 0.005,
        guided_threshold: int = 12,
    ) -> None:
        self.base_exploration_rate = exploration_rate
        self.stagnation_window = stagnation_window
        self.stagnation_threshold = stagnation_threshold
        self.guided_threshold = guided_threshold
        self._weakest_dim: Optional[str] = None  # last identified weakest

    def select(
        self,
        available: list[ActionDef],
        log: EpisodicLog,
    ) -> tuple[ActionDef, SelectionMode]:
        """
        Select the next action and report the selection mode.

        Returns (action_def, mode).
        """
        if not available:
            raise ValueError("No actions available")

        mode = self._choose_mode(log)

        if mode == SelectionMode.FLUCTUATION:
            action = self._fluctuate(available, log)
        elif mode == SelectionMode.GUIDED:
            action = self._guided(available, log)
        else:
            action = self._exploit(available, log)

        return action, mode

    def _choose_mode(self, log: EpisodicLog) -> SelectionMode:
        """Decide between exploration, exploitation, and guided targeting."""
        if log.size < 3:
            return SelectionMode.FLUCTUATION  # Too early to exploit

        # Decay exploration rate with log maturity
        maturity = min(1.0, log.size / 100)
        current_rate = self.base_exploration_rate * (1.0 - maturity * 0.6)

        # Check for stagnation
        recent = log.recent(self.stagnation_window)
        stagnating = False
        if len(recent) >= self.stagnation_window:
            mean_delta = sum(e.delta_coherence for e in recent) / len(recent)
            if abs(mean_delta) < self.stagnation_threshold:
                stagnating = True
                current_rate = min(0.8, current_rate + 0.3)

        # Roll for exploration vs exploitation
        roll = random.random()
        if roll < current_rate:
            return SelectionMode.FLUCTUATION

        # When not exploring and we have enough data, use GUIDED 30% of the time
        # GUIDED is most valuable when stagnating — target the bottleneck
        if log.size >= self.guided_threshold:
            guided_chance = 0.45 if stagnating else 0.25
            if random.random() < guided_chance:
                return SelectionMode.GUIDED

        return SelectionMode.CONSTRAINT

    def _fluctuate(self, available: list[ActionDef], log: EpisodicLog) -> ActionDef:
        """
        Exploration: choose with diversity weighting.

        Actions that have been used less frequently get higher weight,
        preventing the agent from fixating on a narrow repertoire.
        """
        # Count how often each action has been used
        usage = {}
        for entry in log.entries:
            usage[entry.action] = usage.get(entry.action, 0) + 1

        # Weight inversely to usage (unused actions get max weight)
        max_usage = max(usage.values()) if usage else 1
        weights = []
        for a in available:
            count = usage.get(a.name, 0)
            weight = max(1, max_usage - count + 1)
            weights.append(weight)

        return random.choices(available, weights=weights, k=1)[0]

    def _exploit(self, available: list[ActionDef], log: EpisodicLog) -> ActionDef:
        """
        Exploitation: choose the action with the best trail score.

        Trail score = mean delta coherence for this action.
        Actions with no trail history get a moderate default to
        encourage eventual sampling.
        """
        best_score = -float("inf")
        best_action = available[0]

        for a in available:
            trail_score = log.mean_delta_for_action(a.name)
            if trail_score == 0.0 and log.entries_for_action(a.name):
                # Tried but neutral — slightly negative to prefer untried
                trail_score = -0.001

            if trail_score == 0.0:
                # Never tried — give moderate default
                trail_score = 0.01

            if trail_score > best_score:
                best_score = trail_score
                best_action = a

        return best_action

    def _guided(self, available: list[ActionDef], log: EpisodicLog) -> ActionDef:
        """
        Dimension-guided selection: target the weakest coherence dimension.

        1. Find the dimension with the lowest recent mean score
        2. Find which available action historically improves that dimension most
        3. Select that action

        This closes the introspect → selector feedback loop:
        the agent's coherence analysis directly steers future behavior.
        """
        # Step 1: Find the weakest dimension
        trends = log.dimension_trends(window=8)
        if not trends:
            return self._exploit(available, log)  # fallback

        weakest_dim = min(trends, key=lambda d: trends[d]["recent"])
        self._weakest_dim = weakest_dim

        # Step 2: Find which action most improves the weakest dimension
        rankings = log.best_actions_by_dimension()
        dim_rankings = rankings.get(weakest_dim, [])

        if not dim_rankings:
            return self._exploit(available, log)  # fallback

        # Build a set of available action names for quick lookup
        available_names = {a.name for a in available}
        available_by_name = {a.name: a for a in available}

        # Pick the highest-ranked available action for this dimension
        for action_name, score in dim_rankings:
            if action_name in available_names:
                return available_by_name[action_name]

        # No match — fall back to trail-based exploit
        return self._exploit(available, log)

