from .substrate import MemorySubstrate, SubstrateConfig, ConstraintPattern, DIMENSIONS
from .environment import SignalEnvironment, TestCoherenceModel
from .agent import SubstrateAgent
from .runner import SessionRunner
from .dashboard import generate_dashboard, compute_signals
from .real_integration import (
    SubstrateObservationAdapter,
    SubstrateActionBackend,
    SubstrateCoherenceModel,
    SubstrateCFARSelector,
    SubstrateEngine,
)
