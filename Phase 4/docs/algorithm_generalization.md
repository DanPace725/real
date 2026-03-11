# Algorithm Generalization Plan

This phase lifts REAL from one concrete substrate (local hardware state + sandbox filesystem) into a reusable algorithmic core.

## Core principle

Keep the learning mechanism unchanged while swapping substrate bindings.

- Same loop: perceive -> select -> execute -> re-perceive -> score -> record -> consolidate
- Same six coherence dimensions
- Same CFAR selection family
- Same consolidation concept (attractors/surprises/boundaries)

What changes is where observations and actions come from.

## Interfaces to generalize

1. Observation adapter (`O`)
- Reads state before and after action.
- Domain-owned translation into observation dictionaries.

2. Action backend (`A`, `c`)
- Lists available actions.
- Executes action and returns result + measured cost.

3. Coherence model (`Phi`)
- Produces six dimension scores in [0,1].
- Computes composite score and status.

4. Selector (`Psi`)
- Chooses the next action from history + current options.

5. Consolidator (`Gamma`)
- Prunes/retains memory using strategy.

6. Regulatory mesh (`Omega`)
- Applies bounded cross-dimensional tilt coupling.

## Suggested milestones

- M1: Domain-agnostic engine and protocol contracts (this scaffold)
- M2: Hardware domain parity adapter matching Phase 2 behavior
- M3: Second domain adapter (repository health or dialogue state)
- M4: Cross-domain benchmark runner and config-driven experiments
- M5: Slow-layer tuner with bounded weight adaptation per session

## Acceptance criteria for Phase 4

- Same core engine can run at least two domains without engine changes.
- Each domain provides its own observation/action/coherence implementation.
- Memory and selector behavior are comparable across domains.
- Experiment config selects domain and hyperparameters without code edits.

## Future bias: LLM API agent evaluation

The preferred direction is to use REAL as an evaluation substrate for LLM agents operating through API calls.

Current status:

- `domains/llm_api/` now has a trace-shaped architecture with:
  - normalized trace event model (`trace.py`)
  - pluggable executors (`executor.py`)
  - replay mode from JSONL trace files
  - optional capture output to JSONL for generated/replayed events
- Session-level persistence is available through `real_core/session.py` and config-driven history paths.

Planned progression:

- Replace synthetic/replay executors with real API executors that emit the same `LLMApiTraceEvent` schema.
- Ingest real tool-call traces and response metadata while preserving domain contract compatibility.
- Extend cost model calibration from synthetic heuristics to provider-specific token and latency economics.
- Add comparative benchmark profiles for model/provider/prompt/tooling variants using shared REAL loop settings.

The key design constraint is stable interface shape: real API integration should be a backend swap, not an engine rewrite.
