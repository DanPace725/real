# real_inference (M1/M2 Scaffold)

This folder now supports both M1 and M2 workflows.

## Files

- `hooks.py`: compact inference snapshot builders
- `adapter.py`: bounded intervention actions and runtime state
- `coherence.py`: six-dimension coherence mapping
- `offline.py`: replay saved M0 metrics as observations (offline M1 test)
- `live.py`: generate live TransformerLens segments between engine observations
- `m2.py`: one-call M2 minimal loop runner with standardized artifact output

## Modes

1. **M1 offline replay**
   - Fast interface and scoring validation from saved `metrics_raw.jsonl` files

2. **M1 live loop**
   - Live generation + observation + action plumbing through `RealCoreEngine`

3. **M2 minimal REAL loop**
   - Single competing prompt session
   - Real interventions (`observe`, `rest`, bounded temperature shifts, `inject_prefix`)
   - Artifacts written to `experiments/m2/minimal/<tag>/`
   - Success check: GCO variation across cycles

## Entry Points

- Notebook: `notebooks/02_real_loop_minimal.ipynb`
- CLI: `tools/run_m2_minimal.py`
