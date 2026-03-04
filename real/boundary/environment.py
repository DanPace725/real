"""
Environmental Dynamics — terrain-level event generation and decay.

Introduces exogenous environmental change that the agent must respond to
rather than only reacting to its own actions.  This closes a gap identified
in Phase 2: the terrain was purely inert, so the agent had nothing to adapt
to beyond its own prior decisions.

Grounding (E² CFA state space, B2 §1.3): some Fluctuation (F) is required
to prevent Constraint-lock — a system that never encounters exogenous pressure
cannot build genuine adaptive capacity.

Three environment operations per ``tick()``:
    - **Event generation** (every 7 cycles): writes a new event file with a
      randomly chosen type (``load_spike``, ``thermal_event``, ``process_burst``).
    - **Decay marking** (every 15 cycles): appends a ``[DECAYED]`` marker
      to the oldest three non-event terrain files.
    - **Event pruning** (every 20 cycles): removes event files older than
      50 cycles to keep the terrain bounded.

Event files are named ``event_<cycle>_<type>.txt`` and are readable by the
agent's standard ``read_terrain`` action.  The vocabulary dispatcher is
patched (in vocabulary.py) to include ``event_type`` and ``event_age_cycles``
in the result when an event file is detected.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from real.boundary.sandbox import TERRAIN_DIR


# ── Event type catalogue ─────────────────────────────────────────────────

_EVENT_TYPES: tuple[str, ...] = (
    "load_spike",
    "thermal_event",
    "process_burst",
)


class EnvironmentDynamics:
    """
    Manages terrain-level environmental events.

    Parameters
    ----------
    event_interval : int
        Generate a new event every this many cycles.
    decay_interval : int
        Mark old files as decayed every this many cycles.
    prune_interval : int
        Remove stale event files every this many cycles.
    event_max_age_cycles : int
        Event files older than this many cycles are pruned.
    decay_targets : int
        Number of non-event files to mark as decayed per decay cycle.
    seed : Optional[int]
        Random seed for reproducible test environments.
    """

    def __init__(
        self,
        event_interval: int = 7,
        decay_interval: int = 15,
        prune_interval: int = 20,
        event_max_age_cycles: int = 50,
        decay_targets: int = 3,
        seed: Optional[int] = None,
    ) -> None:
        self.event_interval = event_interval
        self.decay_interval = decay_interval
        self.prune_interval = prune_interval
        self.event_max_age_cycles = event_max_age_cycles
        self.decay_targets = decay_targets
        self._rng = random.Random(seed)
        self._recent_events: List[Dict[str, Any]] = []
        self._max_recent = 20

    # ── Public interface ──────────────────────────────────────────────────

    def tick(self, cycle: int) -> None:
        """
        Advance the environment by one cycle.

        Should be called once at the top of each agent cycle, before the
        agent selects and executes its action for that cycle.
        """
        TERRAIN_DIR.mkdir(parents=True, exist_ok=True)

        if cycle % self.event_interval == 0:
            self._generate_event(cycle)

        if cycle % self.decay_interval == 0:
            self._apply_decay(cycle)

        if cycle % self.prune_interval == 0:
            self._prune_old_events(cycle)

    def recent_events(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return the last ``n`` event payloads generated this session."""
        return list(self._recent_events[-n:])

    # ── Operations ────────────────────────────────────────────────────────

    def _generate_event(self, cycle: int) -> None:
        """Write a new event file to TERRAIN_DIR."""
        event_type = self._rng.choice(_EVENT_TYPES)
        filename = f"event_{cycle}_{event_type}.txt"
        payload: Dict[str, Any] = {
            "event_type": event_type,
            "cycle": cycle,
            "timestamp": time.time(),
            "magnitude": round(self._rng.uniform(0.3, 1.0), 3),
        }
        try:
            path = TERRAIN_DIR / filename
            lines = [
                f"[EVENT] type={event_type}",
                f"cycle={cycle}",
                f"magnitude={payload['magnitude']}",
                f"timestamp={payload['timestamp']}",
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            payload["filename"] = filename
            self._recent_events.append(payload)
            if len(self._recent_events) > self._max_recent:
                self._recent_events.pop(0)
        except OSError:
            pass  # Sandbox full or path error; silently skip

    def _apply_decay(self, cycle: int) -> None:
        """Append a [DECAYED] marker to the oldest non-event terrain files."""
        if not TERRAIN_DIR.exists():
            return
        candidates = sorted(
            (f for f in TERRAIN_DIR.iterdir()
             if f.is_file() and not f.name.startswith("event_")),
            key=lambda f: f.stat().st_mtime,
        )
        for path in candidates[: self.decay_targets]:
            try:
                existing = path.read_text(encoding="utf-8")
                if "[DECAYED]" not in existing:
                    path.write_text(existing + f"\n[DECAYED] cycle={cycle}", encoding="utf-8")
            except OSError:
                pass

    def _prune_old_events(self, cycle: int) -> None:
        """Remove event files older than event_max_age_cycles cycles."""
        if not TERRAIN_DIR.exists():
            return
        for path in list(TERRAIN_DIR.iterdir()):
            if not (path.is_file() and path.name.startswith("event_")):
                continue
            # filename format: event_<cycle>_<type>.txt
            parts = path.stem.split("_")  # ['event', '<cycle>', '<type>']
            if len(parts) >= 2:
                try:
                    event_cycle = int(parts[1])
                    if cycle - event_cycle > self.event_max_age_cycles:
                        path.unlink(missing_ok=True)
                except (ValueError, IndexError):
                    pass

    # ── Utility ───────────────────────────────────────────────────────────

    @staticmethod
    def is_event_file(filename: str) -> bool:
        """Return True if ``filename`` is an environment event file."""
        return filename.startswith("event_") and filename.endswith(".txt")

    @staticmethod
    def parse_event_file(content: str, filename: str, current_cycle: int) -> Dict[str, Any]:
        """
        Extract event metadata from file content.

        Returns a dict with at least ``event_type`` and ``event_age_cycles``.
        Safe: returns partial metadata if the file is malformed.
        """
        meta: Dict[str, Any] = {"event_type": "unknown", "event_age_cycles": 0}
        # Extract event type from filename fallback
        parts = Path(filename).stem.split("_")  # event_<cycle>_<type>
        if len(parts) >= 3:
            meta["event_type"] = parts[2]
            try:
                meta["event_age_cycles"] = current_cycle - int(parts[1])
            except (ValueError, IndexError):
                pass
        # Parse content lines for richer metadata
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("[EVENT] type="):
                meta["event_type"] = line.split("=", 1)[1]
            elif line.startswith("magnitude="):
                try:
                    meta["magnitude"] = float(line.split("=", 1)[1])
                except ValueError:
                    pass
            elif line.startswith("cycle="):
                try:
                    event_cycle = int(line.split("=", 1)[1])
                    meta["event_cycle"] = event_cycle
                    meta["event_age_cycles"] = current_cycle - event_cycle
                except ValueError:
                    pass
        return meta
