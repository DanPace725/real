# Phase 8 Admission Substrate Trace - 2026-03-16

## Intent

Move source admission one step closer to the rest of the REAL architecture by replacing a hand-tuned adaptive heuristic with a maintained local substrate that learns whether the source boundary should open or tighten.

## Hypotheses

1. The source boundary can have its own slow memory without introducing a global controller.
Result: the new `AdmissionSubstrate` updates only from source-local backlog change, source routing activity, source feedback gain, inbox load, packet age, and ATP ratio.

2. Learned admission should persist across warm starts just like other maintained structure.
Result: admission substrate state is now serialized in full-system state and in the warm-start carryover manifests used by memory and substrate sessions.

3. Learning admission may change robustness or efficiency relative to the prior queue-managed baseline.
Result: robustness stayed strong, but efficiency changed very little in the current workloads. The learned controller mainly converged to a highly open steady state.

## Implementation Notes

- added `phase8/admission.py` with `AdmissionSubstrate`
- integrated the admission substrate into `RoutingEnvironment`
- source admission now records support and velocity metrics
- warm-start manifests now carry admission substrate state
- added tests for support growth after successful source feedback and for carryover restoration

## Comparison Results

Across the `5`-seed stress suite after this change:

- overall delivered packets remained `16.0`
- overall dropped packets remained `0.0`
- overall overload events remained `0.0`
- overall mean route cost still improved on warm starts from `0.04760` cold to `0.04426` warm-full and `0.04083` warm-substrate

Admission substrate observations:

- `branch_pressure` converged to mean source admission `0.6667` packets per cycle with average admission support about `0.9563`
- `sustained_pressure` converged to mean source admission `1.0` packet per cycle with admission support saturating at `1.0`
- `detour_resilience` converged to mean source admission `0.5455` packets per cycle with average admission support about `0.9705`

## Consequence

This slice improves architectural coherence more than benchmark scores. Admission is now a true maintained boundary policy with carryover, but the current learning rule saturates quickly under easy success. The next meaningful step is to make the admission substrate differentiate between merely successful throughput and metabolically efficient throughput so it does not always drift toward maximal openness.
