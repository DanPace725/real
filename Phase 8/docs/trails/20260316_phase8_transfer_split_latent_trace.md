# 2026-03-16 - GPT-5 Codex - Phase 8 latent cold-vs-transfer split

## Context

We had improved cold hidden-context performance by making source-side latent commitment more persistent and mass-calibrated, but that same change reduced warm `Task A -> Task B` latent transfer flexibility. The next hypothesis was that cold hidden runs and unseen-task transfer runs should not share the same source-side latent control regime.

## Changes

- Added explicit transfer-window observation fields in [environment.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/phase8/environment.py):
  - `transfer_adaptation_phase`
  - `transfer_hidden_unseen_task`
  - `effective_context_threshold`
- Raised the effective latent-context threshold during the source-side unseen-task transfer window so warm starts do not lock into an inferred context as quickly as cold starts.
- Updated [selector.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/phase8/selector.py) so the source:
  - explores more during the hidden unseen-task transfer window,
  - dampens source-sequence hint strength during that window,
  - keeps anti-identity and task-family pressure intact,
  - slightly reduces pre-effective route drive so early transfer does not overcommit before enough evidence has accumulated.
- Added tests in [test_phase8.py](C:/Users/nscha/Coding/Relationally%20Embedded%20Allostatic%20Learning/Phase%202/Phase%208/tests/test_phase8.py) for:
  - transfer adaptation observation exposure,
  - transfer-specific selector exploration boost.

## Results

Verification:

- `python -m unittest tests.test_phase8 -q` -> `Ran 87 tests ... OK`
- `python -m py_compile phase8\environment.py phase8\selector.py tests\test_phase8.py` -> success

Latent benchmark aggregate with `source_sequence_context_enabled=True`:

- Cold hidden `Task A`: `4.4` exact, `0.5167` bit accuracy
- Cold hidden `Task B`: `4.4` exact, `0.5167` bit accuracy
- Hidden `Task A -> Task B` transfer: `8.2` exact, `0.6444` bit accuracy

Interpretation:

- The cold hidden gains from the stronger source commitment were preserved.
- Warm latent transfer improved substantially and now exceeds the visible transfer aggregate on this benchmark slice.
- The split appears to matter most at the source observation/selector boundary, not only inside the latent tracker.
