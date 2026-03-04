# REAL — Relationally Embedded AI Learning

A thermodynamically grounded learning system where an AI agent evaluates itself endogenously through the six relational primitives, embedded in real hardware constraints.

## What This Is

REAL is an architecture for AI that learns through genuine physical embedding rather than external reward signals (RLHF). The agent operates within a sandbox on your real hardware — reading actual CPU load, memory pressure, and thermal state — and evaluates its own coherence across six dimensions derived from the E² (Essence of Existence) framework.

**The key distinction**: the agent's world model is an internal representation of its real physical situation, not a simulation. If you unplug the hardware, the agent breaks.

## Architecture

```
real/
├── core/              # Relational substrate
│   ├── primitives.py      RPPrimitive enum (P1-P6)
│   ├── entity.py          Entity dataclass
│   ├── relation.py        Relation dataclass
│   ├── world.py           World graph (agent's internal model)
│   └── evaluator.py       6-phase tick dispatch + compute-as-ATP
├── coherence/         # Endogenous evaluation
│   ├── engine.py          P1-P6 scoring from real hardware
│   ├── memory.py          Episodic log + 3-tier consolidation
│   └── biases.py          Founding biases + TCL constants
├── agent/             # Agent loop
│   ├── loop.py            Main cycle (perceive→select→execute→evaluate→record)
│   ├── selector.py        CFAR exploration/exploitation
│   └── session.py         Cross-session developmental tracking
└── boundary/          # Physical boundary
    ├── sandbox.py         Filesystem + OS access (the agent's skin)
    └── vocabulary.py      Actions + metabolic tiers
```

## How It Works

Each cycle the agent:
1. **Reads real system state** via psutil (CPU, memory, thermal)
2. **Selects an action** using CFAR-based exploration/exploitation
3. **Executes through the sandbox** against the real OS
4. **Reads system state again** to measure consequences
5. **Scores coherence** across P1-P6 dimensions from real hardware
6. **Updates its internal world model** (relational graph)
7. **Records** the cycle in its episodic log
8. **Consolidates** memory during rest (attractors + surprises + boundaries)

Over multiple sessions, the agent develops: early sessions show volatile coherence and high exploration; later sessions show stable trails and efficient operation.

## Running

```bash
# Requires Python 3.10+ and psutil
pip install psutil

# Run with defaults (50 cycles, 1s interval)
python -m real

# Customize
python -m real --cycles 100 --interval 0.5

# Quiet mode
python -m real --cycles 50 --quiet
```

## Key Design Decisions

- **Compute-as-ATP**: Wall-clock time per tick is measured. More relations in the world graph = more expensive evaluation. The agent pays real metabolic cost for complexity.
- **No RLHF**: Evaluation is endogenous. The coherence engine asks "am I maintaining coherent operation?" — not "did a human like my output?"
- **Tilt-only coupling**: Founding biases shift weight between dimensions (additive) without restructuring the scoring function (parametric). This respects the TCL parametric wall.
- **Three-tier consolidation**: Memory keeps attractors (goals), surprises (learning signal), and boundaries (decision points) — not just top-N scores.
- **Designed incapacity**: The sandbox is architecturally constrained. Fork-bombing isn't prohibited — it's not implemented.

## Origins

Phase 2 of the Relationally Embedded AI Learning project. Synthesizes:
- **coherenceengine**: endogenous evaluation, CFAR selection, episodic memory
- **rplang**: Entity-Relation-World graph, primitive dispatch, relational substrate
- **macl/TCL**: operating window constants (viability floor, chaos ceiling, parametric wall)
- **E² framework**: six relational primitives, GCO, AVIA developmental staging
