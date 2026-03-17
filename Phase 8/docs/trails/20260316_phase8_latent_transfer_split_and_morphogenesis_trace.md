# 2026-03-16 - GPT-5 Codex - Latent transfer split timecourse and latent morphogenesis benchmark

## Context

After splitting source-side hidden-context handling between cold runs and unseen-task warm transfer, the next goals were:

1. verify with timecourse diagnostics that the split was helping for the expected reasons, and
2. run the morphogenesis benchmark against hidden-context endpoints to see whether topology growth helps or hurts when context must be inferred.

## Implementation

- Added a switchable `latent_transfer_split_enabled` path to [environment.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/phase8/environment.py) and threaded it through [compare_cold_warm.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/compare_cold_warm.py) system construction.
- Extended [analyze_transfer_timecourse.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/analyze_transfer_timecourse.py) with:
  - latent transfer warm-start timecourse collection,
  - split-disabled vs split-enabled aggregation,
  - runtime-aligned effective-context threshold accounting.
- Extended [compare_morphogenesis.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/compare_morphogenesis.py) so it can run fixed-vs-growth comparisons on latent-context workloads and latent transfer, instead of only visible-context workloads.
- Added a regression test in [test_phase8.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/tests/test_phase8.py) to ensure the transfer split can be disabled cleanly.

## Verification

- `python -m unittest tests.test_phase8 -q` -> `Ran 88 tests ... OK`
- `python -m py_compile analyze_transfer_timecourse.py compare_morphogenesis.py phase8\environment.py phase8\selector.py tests\test_phase8.py` -> success

## Results

### Latent transfer split timecourse (`Task A -> Task B`, hidden context)

Split enabled minus split disabled:

- final bit accuracy: `+0.02082`
- final exact matches: `+0.75`
- pre-effective instability events: `-0.41666`
- low-confidence cycle count: `-0.16667`

Interpretation:

- The cold-vs-transfer split helps latent transfer in the intended regime.
- The gain is not coming from stronger final source certainty. Final effective/source confidence is actually a bit lower with the split on.
- The likely win mechanism is reduced early instability and better warm-start flexibility before commitment hardens.

### Latent morphogenesis benchmark (`compare_morphogenesis.py`, hidden context)

Cold hidden `Task A`:

- fixed: `4.4` exact, `0.5167` bit accuracy
- growth: `3.4` exact, `0.5000` bit accuracy
- growth win rate: `0.4`

Cold hidden `Task B`:

- fixed: `4.4` exact, `0.5167` bit accuracy
- growth: `4.4` exact, `0.5000` bit accuracy
- growth win rate: `0.4`

Hidden `Task A -> Task B` transfer:

- fixed: `8.2` exact, `0.6444` bit accuracy
- growth: `5.8` exact, `0.5722` bit accuracy
- earned growth transfer rate: `1.0`
- growth transfer win rate: `0.4`

Energy/value readout:

- dynamic nodes were usually utilized and often positive in node value,
- but dynamic net energy stayed negative on average,
- action cost increased meaningfully even when route cost improved slightly.

Interpretation:

- Under latent-context pressure, morphogenesis currently helps efficiency a little (`mean_route_cost` improves) but hurts task performance overall, especially on warm transfer.
- The network can make and use new structure under hidden context, but that structure is still too metabolically expensive and too semantically noisy during context inference.
- The strongest next hypothesis is to suppress or heavily gate budding while latent context is unresolved or during the unseen-task transfer adaptation window.
