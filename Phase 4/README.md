# Phase 4 - REAL Generalization

Phase 4 turns REAL from a hardware-specific implementation into a domain-agnostic learning framework.

The design keeps the same core algorithm tuple from Phase 2:

- `S`: state space
- `A`: action vocabulary
- `c`: cost model
- `O`: observation function
- `Phi`: coherence function (six dimensions)
- `H`: episodic history
- `Psi`: selector
- `Gamma`: consolidation
- `Omega`: regulatory mesh

The key change is that these are now explicit interfaces in `real_core`, with domain implementations living under `domains`.

## Folder layout

- `docs/algorithm_generalization.md` - phase framing and roadmap
- `real_core/` - reusable domain-agnostic engine and contracts
- `adapters/` - adapter base classes for observation/action/cost
- `domains/` - substrate-specific implementations (`hardware`, `repo_health`, `llm_api`)
- `experiments/` - experiment configs (including LLM trace replay)
- `tests/` - lightweight contract tests
- `memory/` - persisted cross-session summaries and optional captured traces

## Quick start

```bash
python -m unittest discover -s "Phase 4/tests" -p "test_*.py"
python "Phase 4/run_example.py"
python "Phase 4/run_experiment.py" --config "Phase 4/experiments/example_repo_health.toml"
python "Phase 4/run_experiment.py" --config "Phase 4/experiments/example_llm_api.toml"
```
