"""
real.coherence — Endogenous evaluation system.

Scores the agent's operational health across the six relational primitives
using real hardware metrics.  No external reward signal.
"""

from real.coherence.engine import CoherenceEngine
from real.coherence.memory import EpisodicLog, LogEntry
from real.coherence.biases import FOUNDING_BIASES, TCL_CONSTANTS

__all__ = [
    "CoherenceEngine",
    "EpisodicLog", "LogEntry",
    "FOUNDING_BIASES", "TCL_CONSTANTS",
]
