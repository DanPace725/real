# REAL Phase 2 — Progress Report

## Overview

Phase 2 synthesized concepts from three prior projects (coherenceengine, rplang, macl/TCL) into a working embedded AI learning system. The agent operates on real hardware, evaluates itself endogenously through six relational primitives, and has demonstrated measurable developmental progression across 20 sessions (~1,500 cycles).

## Architecture (16 source files)

```
real/
├── core/                  # Relational substrate
│   ├── primitives.py          6 primitives (P1 Ontology → P6 Meta)
│   ├── entity.py              Entity dataclass with state, tags, kind
│   ├── relation.py            Typed directional links between entities
│   ├── world.py               Indexed graph container (entities + relations)
│   └── evaluator.py           6-phase tick dispatch + compute-as-ATP
├── coherence/             # Endogenous evaluation
│   ├── engine.py              P1-P6 scoring from real hardware (psutil)
│   ├── memory.py              Episodic log + 3-tier consolidation
│   └── biases.py              Founding biases + TCL operating window
├── agent/                 # Agent loop
│   ├── loop.py                8-phase cycle (perceive→act→evaluate→record)
│   ├── selector.py            3-mode CFAR selector (F/C/G)
│   └── session.py             Cross-session developmental tracking
└── boundary/              # Physical boundary
    ├── sandbox.py             Filesystem + OS access (the agent's skin)
    └── vocabulary.py          14 actions across 5 metabolic tiers
```

## Key Design Decisions

**Compute-as-ATP.** Wall-clock time per evaluator tick is measured. More relations = more expensive evaluation. The agent pays real metabolic cost for complexity.

**No RLHF.** Evaluation is endogenous. The coherence engine asks "am I maintaining coherent operation?" — not "did a human like my output?"

**Tilt-only coupling.** Founding biases shift weight between dimensions (additive) without restructuring the scoring function (parametric). Respects the TCL parametric wall.

**Three-tier consolidation.** Memory keeps attractors (goals), surprises (learning signals), and boundaries (decision points) — not just top-N scores.

**Designed incapacity.** The sandbox is architecturally constrained. Fork-bombing isn't prohibited — it's not implemented.

---

## Implementation Timeline

### Phase 2a — Core Build
- Relational substrate: Entity → Relation → World → Evaluator
- Coherence engine: P1-P6 hardware scorers + GCO status
- Agent loop: 8-phase causal ordering with real system readings
- Boundary: Sandbox + 9-action vocabulary
- Smoke test: 20 cycles, all systems nominal

### Phase 2b — Action Implementations
- `query_memory`: pattern search over episodic log (trails, dimension rankings, trends)
- `compare_state`: current vs historical state drift analysis
- `introspect`: self-model from log analysis, persisted to sandbox
- 5 analytical methods added to EpisodicLog

### Phase 2c — Evaluator Handlers
All 6 handlers implemented (were stubs):
- **Geometry (P3):** field propagation, distance computation, causal ordering, adjacency tracking
- **Ontology (P1):** kind assignment, composition hierarchy, tag inheritance, identity stability
- **Epistemic (P5):** observation with freshness timestamps
- **Dynamics (P2):** rate-based state updates
- **Constraint (P4):** field clamping
- **Meta (P6):** relation activation/deactivation/toggling

### Phase 2d — Closing the Feedback Loop
The critical architectural change. Before this, coherence hovered at ~0.80 and the agent never reached STABLE GCO.

**Deepened reflexivity scorer:** measures actual behavioral revision after coherence dips (action switch rate, recovery success rate, introspection usage). Replaced a thin scorer that only checked CPU load variance.

**3-mode selector (GUIDED):** when the selector enters GUIDED mode, it identifies the weakest coherence dimension from recent log data and picks the action that historically improves that specific dimension. Output shows as `G` with the targeted dimension in brackets:
```
[  1] G introspect       → 0.594  GCO:DEGRADED  [vitality]
[  8] G shallow_scan     → 0.736  GCO:PARTIAL   [accountability]
```

**Result:** Reflexivity jumped from 0.567 → 0.857. GCO STABLE went from 0 cycles to 50/100 in a single session.

### Phase 2e — Costly Actions
Two actions with genuinely different metabolic profiles:

**`digest_log` (CPU-bound):** serializes episodic log, runs iterative SHA-256 hashing. Iterations scale with log size (5000 + 500/entry). Stores compact digest as terrain marker. The metabolic cost of "digesting" experience.

**`sort_terrain` (I/O-bound):** reads all terrain files, sorts by timestamp/size, rewrites with order prefix. Genuine disk I/O work with a different coherence impact than CPU-bound work.

### Phase 2f — Dashboard
`dashboard.py` reads session history, episodic log, and self-model, generates an interactive HTML dashboard with Chart.js (coherence trends, dimension bars, GCO distribution, action/tier usage, self-model stats).

---

## Developmental Results

### First 10 Sessions (before feedback loop, ~800 cycles)

| Metric | Range |
|---|---|
| Mean coherence | 0.785 – 0.828 |
| GCO STABLE | **0** |
| Exploration | 36% – 60% |
| Reflexivity | 0.549 – 0.567 |
| Dominant behavior | `list_terrain` (environmental scanning) |

The system was coasting in a flat basin. Actions didn't meaningfully impact coherence. The reflexivity scorer was returning a fixed 0.4/0.6 value.

### Next 10 Sessions (after feedback loop + costly actions, ~775 cycles)

| Metric | Range |
|---|---|
| Mean coherence | 0.708 – **0.879** |
| GCO STABLE | 1 – **50** per session |
| Exploration | 18% – 56% |
| Reflexivity | **0.857** |
| Dominant behavior | `digest_log`, `introspect` (self-processing) |

### What Changed

1. **GCO breakthrough.** Session 4 achieved 50 STABLE cycles (all 6 dimensions simultaneously above threshold). This never happened in the first 10 sessions.

2. **Behavioral shift.** The agent moved from "look around a lot" (reflex: 47/100) to "process what I've seen" (spawn: 27/50, build: 39/100). `digest_log` became dominant — the agent prefers CPU-intensive work on its own experience over cheap environmental scans.

3. **Exploration convergence.** Dropped from 56% to 24% as trails solidified. The CFAR selector correctly exploits when trails are strong.

4. **Reflexivity ceiling broken.** 0.567 → 0.857. The deepened scorer measures whether the agent *actually revises behavior* after negative outcomes, and the agent does — it switches actions after dips and those switches produce recovery.

5. **100% action diversity.** All 14 actions used, including both SPAWN tier actions.

### Agent Self-Model (auto-generated by introspect)

```
Dominant action: mark_terrain
Action diversity: 100%
Coherence mean: 0.8629
Coherence trajectory: +0.2469
Strongest dimension: contextual_fit (0.999)
Weakest dimension: vitality (0.777)
Reflexivity: 0.857
GCO proximity: 19%
Total compute: 0.628s
```

### Current Bottleneck

`vitality` (0.777) is now the weakest dimension. It measures productive energy expenditure via an inverted parabola peaking at ~40% CPU load. The agent's heavy use of `digest_log` (which is CPU-intensive) may be pushing load patterns away from the vitality sweet spot. The GUIDED selector is already targeting this dimension.

---

## Sandbox Footprint

After 20 sessions:
- **200 terrain files** (113 digest markers + 87 terrain marks)
- **48 KB** episodic log (with consolidation keeping it bounded)
- **30 KB** world checkpoint
- **9 KB** session history
- **28 consolidation events** (memory pruning working correctly)

---

## Open Questions for Phase 3

1. **Relation pruning.** The World graph grows unbounded with action-record relations. Should consolidate like the episodic log.

2. **AVIA staging.** Currently implicit. Explicit developmental stages (AWAKE → VIGILANT → INTERACTIVE → ADAPTIVE) with different vocabulary unlocks and scorer profiles would give structure to the arc.

3. **Level 1 regulatory mesh.** TCL constants exist but tilt-coupled inter-dimensional dynamics aren't implemented yet.

4. **Vitality plateau.** The agent's preference for `digest_log` creates a metabolic pattern that may conflict with vitality scoring. Does the agent need to learn metabolic budgeting?

5. **Environmental richness.** The terrain is still mostly inert. Richer environmental dynamics would give the agent more to respond to.
