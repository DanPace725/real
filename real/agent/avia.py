"""
AVIA Developmental Stage Tracker.

Tracks the agent's current developmental stage across sessions, using
behavioural thresholds derived from the accumulated session history.

Stage names borrow from the E² framework's AVIA (Adaptation via
Informational Abstraction) concept, which describes how systems generate
higher-order abstractions as they hit complexity ceilings.  At the REAL
agent's scale the analogous concept is the accumulation of *earned*
behavioural milestones — the agent demonstrating, not being granted,
each stage.  The stages are descriptive checkpoints, not capability gates.

Stages (in order):
    AWAKE       — orienting; few sessions or low mean coherence
    VIGILANT    — stable baseline established; CFAR trails emerging
    INTERACTIVE — self-modification visible; reflexivity measurable
    ADAPTIVE    — self-sustaining developmental trajectory confirmed
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from real.agent.session import SessionLogger
    from real.coherence.memory import EpisodicLog

# Total distinct actions in the vocabulary (used for diversity ratio).
# Read dynamically from the registry so this stays correct when actions are added.
from real.boundary.vocabulary import VOCABULARY as _VOCABULARY
_VOCABULARY_SIZE: int = len(_VOCABULARY)


class AVIAStage(Enum):
    """Developmental stage of the REAL agent."""
    AWAKE       = "AWAKE"
    VIGILANT    = "VIGILANT"
    INTERACTIVE = "INTERACTIVE"
    ADAPTIVE    = "ADAPTIVE"

    @property
    def ordinal(self) -> int:
        return list(AVIAStage).index(self)


# ── Threshold definitions ──────────────────────────────────────────────────

@dataclass(frozen=True)
class StageThresholds:
    """Numeric thresholds for each stage transition."""
    # AWAKE → VIGILANT
    vigilant_min_sessions: int   = 3
    vigilant_min_coherence: float = 0.65
    vigilant_min_reflexivity: float = 0.60

    # VIGILANT → INTERACTIVE
    interactive_min_sessions: int = 8
    interactive_min_reflexivity: float = 0.75
    interactive_min_diversity: float = 0.80   # 80% of vocabulary used

    # INTERACTIVE → ADAPTIVE
    adaptive_min_reflexivity: float = 0.85
    adaptive_min_diversity: float = 1.00      # full vocabulary used
    adaptive_min_coherence: float  = 0.80


_DEFAULT_THRESHOLDS = StageThresholds()


# ── Tracker ────────────────────────────────────────────────────────────────

class AVIATracker:
    """
    Determines and tracks the agent's developmental stage.

    Designed to be called once per session close.  Reads aggregated
    statistics from the session history and episodic log to decide
    whether a stage transition has been earned.

    The tracker is purely observational — it does not gate capabilities.
    """

    def __init__(self, thresholds: StageThresholds = _DEFAULT_THRESHOLDS) -> None:
        self.thresholds = thresholds
        self.stage: AVIAStage = AVIAStage.AWAKE
        self._prev_stage: Optional[AVIAStage] = None
        self._last_metrics: Dict[str, Any] = {}

    # ── Stage computation ──────────────────────────────────────────────────

    def advance(
        self,
        session_logger: "SessionLogger",
        log: "EpisodicLog",
    ) -> AVIAStage:
        """
        Re-evaluate and (if warranted) advance the current stage.

        Parameters
        ----------
        session_logger : SessionLogger
            Provides cross-session aggregate statistics.
        log : EpisodicLog
            Provides reflexivity and diversity data from the episodic log.

        Returns
        -------
        AVIAStage
            The (possibly updated) current stage.
        """
        self._prev_stage = self.stage

        metrics = self._compute_metrics(session_logger, log)
        self._last_metrics = metrics

        new_stage = self._evaluate(metrics)

        # Stages only advance, never regress — a developmental arc is
        # permanent even if a single session underperforms.
        if new_stage.ordinal > self.stage.ordinal:
            self.stage = new_stage

        return self.stage

    def _compute_metrics(
        self,
        session_logger: "SessionLogger",
        log: "EpisodicLog",
    ) -> Dict[str, Any]:
        """Collect the raw numbers needed for stage evaluation."""
        sessions = session_logger.sessions
        n_sessions = len(sessions)

        # Mean coherence across all *completed* sessions
        mean_coherence = (
            sum(s.mean_coherence for s in sessions) / n_sessions
            if n_sessions else 0.0
        )

        # Whether GCO STABLE was ever achieved
        ever_stable = any(s.gco_stable_count > 0 for s in sessions)

        # Action diversity: distinct actions used across ALL sessions
        all_actions: set[str] = set()
        for s in sessions:
            all_actions.update(s.action_distribution.keys())
        diversity = len(all_actions) / _VOCABULARY_SIZE if _VOCABULARY_SIZE else 0.0

        # Reflexivity: read from episodic log's self-model if available
        reflexivity = 0.0
        try:
            model = log.self_model()
            reflexivity = model.get("reflexivity", 0.0)
        except Exception:
            # EpisodicLog may not have enough data yet — treat as 0
            reflexivity = 0.0

        return {
            "n_sessions": n_sessions,
            "mean_coherence": mean_coherence,
            "ever_stable": ever_stable,
            "action_diversity": diversity,
            "reflexivity": reflexivity,
        }

    def _evaluate(self, m: Dict[str, Any]) -> AVIAStage:
        """Determine the highest stage the metrics justify."""
        t = self.thresholds

        # Check from highest to lowest — return first stage that passes
        if (
            m["reflexivity"]       >= t.adaptive_min_reflexivity
            and m["action_diversity"] >= t.adaptive_min_diversity
            and m["mean_coherence"]   >= t.adaptive_min_coherence
        ):
            return AVIAStage.ADAPTIVE

        if (
            m["n_sessions"]        >= t.interactive_min_sessions
            and m["reflexivity"]   >= t.interactive_min_reflexivity
            and m["action_diversity"] >= t.interactive_min_diversity
        ):
            return AVIAStage.INTERACTIVE

        if (
            m["n_sessions"]        >= t.vigilant_min_sessions
            and m["mean_coherence"]  >= t.vigilant_min_coherence
            and m["reflexivity"]   >= t.vigilant_min_reflexivity
        ):
            return AVIAStage.VIGILANT

        return AVIAStage.AWAKE

    # ── Reporting ──────────────────────────────────────────────────────────

    @property
    def advanced_this_session(self) -> bool:
        """True if a stage transition occurred on the last advance() call."""
        return self._prev_stage is not None and self._prev_stage != self.stage

    def stage_summary(self) -> Dict[str, Any]:
        """Return a dict suitable for logging or dashboard display."""
        return {
            "stage": self.stage.value,
            "advanced": self.advanced_this_session,
            "metrics": dict(self._last_metrics),
            "thresholds": {
                "vigilant": {
                    "min_sessions": self.thresholds.vigilant_min_sessions,
                    "min_coherence": self.thresholds.vigilant_min_coherence,
                    "min_reflexivity": self.thresholds.vigilant_min_reflexivity,
                },
                "interactive": {
                    "min_sessions": self.thresholds.interactive_min_sessions,
                    "min_reflexivity": self.thresholds.interactive_min_reflexivity,
                    "min_diversity": self.thresholds.interactive_min_diversity,
                },
                "adaptive": {
                    "min_reflexivity": self.thresholds.adaptive_min_reflexivity,
                    "min_diversity": self.thresholds.adaptive_min_diversity,
                    "min_coherence": self.thresholds.adaptive_min_coherence,
                },
            },
        }

    def __repr__(self) -> str:
        m = self._last_metrics
        return (
            f"AVIATracker(stage={self.stage.value}, "
            f"sessions={m.get('n_sessions', 0)}, "
            f"coherence={m.get('mean_coherence', 0):.3f}, "
            f"reflexivity={m.get('reflexivity', 0):.3f}, "
            f"diversity={m.get('action_diversity', 0):.0%})"
        )
