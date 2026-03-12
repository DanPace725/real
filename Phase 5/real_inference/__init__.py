"""Phase 5 inference-domain adapter scaffolding for REAL M1/M2."""

from .adapter import InferenceActionBackend, InferenceObservationAdapter, InferenceRuntimeState
from .coherence import InferenceCoherenceModel
from .hooks import InferenceSnapshot, build_snapshot
from .live import LiveLoopConfig, LiveSegmentObservationAdapter
from .m2 import DEFAULT_MODEL_NAME_MAP, M2RunConfig, run_m2_minimal_session
from .offline import OfflineReplayObservationAdapter, load_m0_observations

__all__ = [
    "InferenceActionBackend",
    "InferenceObservationAdapter",
    "InferenceRuntimeState",
    "InferenceCoherenceModel",
    "InferenceSnapshot",
    "build_snapshot",
    "LiveLoopConfig",
    "LiveSegmentObservationAdapter",
    "M2RunConfig",
    "DEFAULT_MODEL_NAME_MAP",
    "run_m2_minimal_session",
    "OfflineReplayObservationAdapter",
    "load_m0_observations",
]
