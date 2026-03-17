# 2026-03-16 - GPT-5 Codex - Phase 8 Latent Evidence Channel Trace

## Intent

Instrument latent-context evidence by channel so we can distinguish whether cold hidden `Task A` confidence collapse is coming from:

- source route evidence,
- source feedback evidence,
- downstream route evidence,
- or downstream feedback evidence.

## Files Updated

- `Phase 8/phase8/environment.py`
- `Phase 8/analyze_transfer_timecourse.py`
- `Phase 8/tests/test_phase8.py`

## What Changed

- Extended `LatentTaskState` to keep channel-separated evidence ledgers:
  - `source_route`
  - `downstream_route`
  - `source_feedback`
  - `downstream_feedback`
- Preserved the original combined latent evidence path while adding per-channel:
  - context evidence
  - transform evidence
  - channel confidence
  - channel dominant context estimate
- Wired route and feedback recording so trackers now know whether a signal came from the source node or a downstream node.
- Extended the latent timecourse analyzer to capture:
  - source route confidence
  - source feedback confidence
  - downstream mean route confidence
  - downstream mean feedback confidence
  - and the same final-cycle summary metrics.
- Added tests covering:
  - route/feedback channel separation in tracker snapshots
  - latent timecourse summaries with the new channel fields

## Validation

- `python -m unittest tests.test_phase8 -q`
- `python -m py_compile phase8\\environment.py analyze_transfer_timecourse.py tests\\test_phase8.py`
- inline `analyze_latent_context_timecourse(...)` on cold hidden `cvt1_task_a_stage1` over seeds:
  - `13, 23, 37, 51, 79`

## Main Findings

### 1. The cold hidden `Task A` collapse is mostly a source-side collapse, not a downstream one

Final five-seed aggregate:

- with source sequence:
  - `final_latent_context_confidence`: `0.49919`
  - `final_effective_context_confidence`: `0.37388`
  - `final_source_route_context_confidence`: `0.46962`
  - `final_source_feedback_context_confidence`: `0.72945`
  - `final_downstream_route_context_confidence`: `0.66213`
  - `final_downstream_feedback_context_confidence`: `0.69001`

- without source sequence:
  - `final_latent_context_confidence`: `0.86355`
  - `final_effective_context_confidence`: `0.86355`
  - `final_source_route_context_confidence`: `0.80425`
  - `final_source_feedback_context_confidence`: `0.91981`
  - `final_downstream_route_context_confidence`: `0.64686`
  - `final_downstream_feedback_context_confidence`: `0.6869`

Difference (`with source` minus `without source`):

- `source_route_context_confidence`: `-0.33463`
- `source_feedback_context_confidence`: `-0.19036`
- `downstream_route_context_confidence`: `+0.01527`
- `downstream_feedback_context_confidence`: `+0.00311`
- `final_effective_context_confidence`: `-0.48967`

Interpretation:

- Downstream confidence is basically unchanged.
- The major collapse is happening inside the source tracker itself.
- The strongest hit is to **source route evidence**, with a smaller but still real hit to **source feedback evidence**.

### 2. The source-sequence adapter helps early stability but weakens long-run source commitment

Earlier timecourse results already showed:

- pre-effective instability drops a lot with source sequence.

The new channel split clarifies the cost:

- the source starts clean,
- but its own route evidence ends up less decisive by the end of the run,
- and its own feedback evidence is also less decisive than the no-source-sequence baseline.

Interpretation:

- The source-sequence adapter is not mainly being “overruled by downstream nodes.”
- It is producing a source policy that stays too mixed over time, even after early ambiguity is reduced.

## Conclusion

The main remaining bottleneck for cold hidden `Task A` is now much clearer:

- not delayed latent context formation,
- not downstream tracker disagreement,
- but **source-side evidence dilution over time**.

The next tuning target should therefore be the source tracker or source selector feedback loop itself, especially:

- how source route evidence decays,
- how source feedback reinforces or fails to reinforce the early source-sequence-guided hypothesis,
- and whether source route evidence is getting spread too evenly across both Task A-compatible transform families.

## Suggested Next Step

- Add a source-only latent commitment retune:
  - preserve early source-sequence stabilization,
  - but strengthen persistence when source route evidence and source feedback agree,
  - and reduce source-side mixing between Task A-compatible transforms once one family begins receiving reciprocal feedback.
