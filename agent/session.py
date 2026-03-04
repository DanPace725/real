"""
Session logger — cross-session developmental tracking.

Records aggregate statistics for each session.  Over multiple sessions,
the developmental arc becomes visible:
    - Early sessions: high exploration, volatile coherence, few tier 3+ actions
    - Middle sessions: trail emergence, stabilizing scores, vocabulary expansion
    - Mature sessions: efficient exploitation, high coherence, reflexive actions

This is AVIA progression made measurable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class SessionRecord:
    """
    Aggregate statistics for one session.

    Written on session close.
    """
    session_id: int
    start_time: float
    end_time: float = 0.0
    total_cycles: int = 0
    mean_coherence: float = 0.0
    final_coherence: float = 0.0
    gco_stable_count: int = 0
    gco_partial_count: int = 0
    gco_degraded_count: int = 0
    gco_critical_count: int = 0
    total_compute_secs: float = 0.0
    action_distribution: Dict[str, int] = field(default_factory=dict)
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    consolidation_count: int = 0
    exploration_ratio: float = 0.0    # fraction of cycles in FLUCTUATION mode


class SessionLogger:
    """
    Manages session history for cross-session developmental tracking.
    """

    def __init__(self, history_path: Path) -> None:
        self.history_path = history_path
        self.sessions: list[SessionRecord] = []
        self._load()

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def latest(self) -> SessionRecord | None:
        return self.sessions[-1] if self.sessions else None

    def new_session(self) -> SessionRecord:
        """Start a new session record."""
        session = SessionRecord(
            session_id=self.session_count + 1,
            start_time=time.time(),
        )
        self.sessions.append(session)
        return session

    def close_session(self, record: SessionRecord) -> None:
        """Finalize and save session record."""
        record.end_time = time.time()
        self._save()

    def developmental_summary(self) -> Dict[str, Any]:
        """
        Cross-session metrics showing the developmental arc.
        """
        if not self.sessions:
            return {"sessions": 0}

        return {
            "sessions": len(self.sessions),
            "total_cycles": sum(s.total_cycles for s in self.sessions),
            "coherence_trend": [s.mean_coherence for s in self.sessions],
            "exploration_trend": [s.exploration_ratio for s in self.sessions],
            "vocabulary_growth": [len(s.action_distribution) for s in self.sessions],
            "compute_trend": [s.total_compute_secs for s in self.sessions],
        }

    # ── Persistence ───────────────────────────────────────────────────

    def _save(self) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(s) for s in self.sessions]
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not self.history_path.exists():
            return
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sdata in data:
                self.sessions.append(SessionRecord(**sdata))
        except (json.JSONDecodeError, TypeError):
            pass
