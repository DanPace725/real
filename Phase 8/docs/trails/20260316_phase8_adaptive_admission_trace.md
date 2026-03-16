# Phase 8 Adaptive Admission Trace - 2026-03-16

## Intent

Replace the fixed source-ingress throttle with a local admission controller so the source boundary can meter packets from its own metabolic state instead of relying on a per-scenario constant.

## Hypotheses

1. Admission can be adaptive without violating Phase 8 locality.
Result: the new controller reads only source-local ATP, reward buffer, inbox load, local packet age, feedback presence, and the source backlog.

2. The admission controller should preserve the queue-management gains from the prior slice.
Result: across all tested scenarios and seeds, delivery stayed flat, dropped packets stayed at `0`, and overload events stayed at `0`.

3. Adaptive control may reduce latency relative to fixed pacing.
Result: not yet. In the current workloads, the adaptive controller converged on effective admission rates similar to the prior hand-tuned settings, so latency stayed unchanged.

## Implementation Notes

- added `source_admission_policy`, `source_admission_min_rate`, and `source_admission_max_rate`
- implemented an adaptive controller that opens admission under healthy ATP and backlog, and tightens under high local queue age, high inbox load, or low ATP
- added session-correct admission metrics so warm-start runs are not distorted by prior global cycle counts
- switched Phase 8 scenarios to adaptive admission mode
- added tests for adaptive opening and dormancy-based closure

## Comparison Results

After switching the scenarios to adaptive admission:

- `branch_pressure`: still `12/12` delivered, `0` drops, `0` overload events, with mean source admission `0.6667` packets per cycle
- `sustained_pressure`: still `24/24` delivered, `0` drops, `0` overload events, with mean source admission `1.0` packet per cycle
- `detour_resilience`: still `12/12` delivered, `0` drops, `0` overload events, with mean source admission `0.5455` packets per cycle

Overall aggregate:

- delivered packets remained `16.0`
- dropped packets remained `0.0`
- overload events remained `0.0`
- mean route cost still improved on warm starts from `0.04747` cold to `0.04423` warm-full and `0.04077` warm-substrate

## Consequence

This slice upgraded the architecture more than the raw metrics. Admission is now locally controlled rather than scenario-scripted. The next meaningful step is to let the controller learn from substrate and feedback history instead of using a hand-tuned heuristic, because the current adaptive rule is robust but not yet more efficient than the fixed policy it replaced.
