# Phase 8 Balance-Conditioned Selector Trace

## Date

2026-03-16

## Timestamp

2026-03-16T12:30:29.3197940-07:00

## Model

GPT-5 Codex

## Prompt

Add a balance-conditioned selector diagnostic so we can see which branch and transform decisions are being made while the system is in its negative-balance basin.

## Inputs Reviewed

- `Phase 8/analyze_transfer_timecourse.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/docs/trails/20260316_phase8_transfer_balance_trace.md`

## Work Completed

- Extended `Phase 8/analyze_transfer_timecourse.py` so each transfer cycle now captures selector-side action summaries from `report["entries"]`.
- Added negative-balance window aggregation for:
  - route branch counts and shares
  - route transform counts and shares
  - route mode counts and shares
  - top branch-transform pairs
  - mean route coherence
  - mean route delta

## Main Findings

### 1. The negative-balance basin is still overwhelmingly guided, not exploratory

Negative-balance route mode shares:

- `Task A -> Task B`
  - `guided`: `0.98485`
  - `fluctuation`: `0.01515`

- `Task B -> Task A`
  - `guided`: `0.97531`
  - `fluctuation`: `0.02469`

Interpretation:

- The selector is not “wandering” its way through the contradiction basin.
- Even in negative-balance conditions, the system is acting mostly through established guided preferences.
- That means the basin is behaviorally structured, not just noisy.

### 2. `Task B -> Task A` keeps selecting a broader, more conflicted transform mix

Negative-balance transform shares:

- `Task A -> Task B`
  - `xor_mask_1010`: `0.56061`
  - `xor_mask_0101`: `0.30303`
  - `rotate_left_1`: `0.13636`

- `Task B -> Task A`
  - `xor_mask_0101`: `0.37037`
  - `rotate_left_1`: `0.35802`
  - `xor_mask_1010`: `0.27160`

Interpretation:

- `Task A -> Task B` has a dominant transform family even while under conflict.
- `Task B -> Task A` is much more split across incompatible transform families.
- This is a strong candidate explanation for the deeper negative-balance basin: under contradiction, the system is not converging cleanly on the new transform regime.

### 3. The problematic selector pattern is branch-transform mixing, not pure branch collapse

Top negative-balance branch-transform pairs:

- `Task A -> Task B`
  - `sink:xor_mask_1010` (`19`)
  - `n2:xor_mask_0101` (`10`)
  - `n1:xor_mask_1010` (`7`)

- `Task B -> Task A`
  - `sink:rotate_left_1` (`13`)
  - `sink:xor_mask_0101` (`12`)
  - `n2:rotate_left_1` (`10`)
  - `n1:xor_mask_0101` (`7`)
  - `n5:xor_mask_1010` (`7`)

Interpretation:

- The negative-balance basin in `Task B -> Task A` is not one stale branch dominating everything.
- It is a richer conflict pattern: multiple branch-transform pairings remain active at once.
- That fits the earlier balance result. The system is carrying more structured contradiction, not merely repeating a single bad habit.

### 4. Under conflict, `Task B -> Task A` still looks locally “reasonable”

Negative-balance route summary:

- `Task A -> Task B`
  - `mean_route_coherence`: `0.51264`
  - `mean_route_delta`: `0.00864`

- `Task B -> Task A`
  - `mean_route_coherence`: `0.67540`
  - `mean_route_delta`: `0.01060`

Interpretation:

- This is an important warning sign.
- During the deeper contradiction basin, `Task B -> Task A` still produces higher local coherence and slightly better local delta than `Task A -> Task B`.
- So the selector can remain locally satisfied while the global branch-transform balance is still worse.
- That is exactly the kind of proxy-validity concern the GPT-5.2 review warned about.

## Conclusion

The balance-conditioned selector view surfaces a sharper explanation for the asymmetry:

- `Task B -> Task A` is not failing because the selector becomes random.
- It is failing because guided behavior remains active across a broader competing set of branch-transform habits while the system is under contradiction.
- The deeper negative-balance basin is therefore tied to structured selector conflict, not to a loss of control.

This suggests the next improvement should target conflict arbitration among guided branch-transform candidates during mid-transfer contradiction, rather than simply increasing exploration or speeding debt decay further.

## Validation

- `python -m py_compile analyze_transfer_timecourse.py`
- Inline 12-seed aggregate run via `python -`

## Next Steps

- Add a branch-transform competition diagnostic keyed to negative-balance cycles so we can see whether one or two candidate actions should be explicitly down-weighted sooner when multiple guided options remain active under contradiction.
