# Phase 8 Task B Branch Context Debt Trace

## Date

2026-03-16

## Timestamp

2026-03-16T11:10:06-07:00

## Model

GPT-5 Codex

## Prompt

Ok, keep developing this mechanism

## Intent

Develop the contradiction-handling mechanism beyond branch-plus-transform debt by adding context-specific branch debt, so full carryover can back away from stale Task A branch reuse during Task B transfer without suppressing useful reuse everywhere.

## Files Touched

- `Phase 8/phase8/models.py`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/selector.py`
- `Phase 8/phase8/substrate.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/tests/test_phase8.py`
- `Phase 8/README.md`

## What Changed

- added `branch_context_debt` to local node runtime state
- returning contextual feedback now writes contradiction memory at three levels:
  - transform
  - branch plus transform
  - branch plus context
- local observation now exposes `branch_context_feedback_debt_{neighbor}`
- selector scoring now:
  - penalizes branch-context contradiction
  - reduces trust in old local history when a branch is contradiction-heavy and current context evidence is weak
  - adds a modest escape bonus for alternate branches when another branch is clearly stale in the same context
- maintenance now also sees branch-context debt, so scarce ATP is less likely to preserve a branch-context scaffold that keeps failing
- added regressions for:
  - branch-context debt buildup under committed stale behavior
  - no branch-context debt buildup without prior commitment
  - selector avoidance of a branch carrying strong context debt
  - maintenance preferring the lower-debt branch when ATP is tight

## Validation

Executed:

- `python -m unittest "Phase 8\tests\test_phase8.py"`
- `python -m py_compile "Phase 8\phase8\environment.py" "Phase 8\phase8\selector.py" "Phase 8\phase8\substrate.py" "Phase 8\phase8\models.py" "Phase 8\phase8\adapters.py" "Phase 8\tests\test_phase8.py"`
- `python "Phase 8\compare_task_transfer.py"`

All commands passed.

## Result

This pass kept the overall Task B transfer advantage for full carryover while shifting more pressure onto the stale odd-context branch.

Across 5 seeds:

- cold Task B exact matches averaged `2.2`
- warm full Task B exact matches averaged `4.4`
- warm substrate-only Task B exact matches averaged `4.4`

- cold Task B mean bit accuracy averaged `0.3889`
- warm full Task B mean bit accuracy averaged `0.4278`
- warm substrate-only Task B mean bit accuracy averaged `0.4667`

- cold `context_1` mean bit accuracy averaged `0.2500`
- warm full `context_1` mean bit accuracy averaged `0.2750`
- warm substrate-only `context_1` mean bit accuracy averaged `0.2625`

- cold wrong-transform-family counts averaged `12.6`
- warm full wrong-transform-family counts averaged `11.6`
- warm substrate-only wrong-transform-family counts averaged `10.0`

## Interpretation

This mechanism is directionally useful.

The good part is that full carryover now stays ahead of cold start on both aggregate Task B metrics and gains a small edge on the changed `context_1` branch itself.

The limitation is that substrate-only still keeps the stronger overall mean bit accuracy, and warm full still shows elevated stale-support suspicion compared with substrate-only. So this pass improved local branch retreat, but the system still lacks a strong positive notion of which branch-context pair is truly reliable in the new task.

## Immediate Next Step

- keep the branch-context debt mechanism
- add positive branch-context evidence, not just contradiction pressure, so full carryover can distinguish:
  - branch-context pairs that should be relaxed
  - branch-context pairs that should be actively preserved
- use that positive signal to cut stale-support suspicion without giving back the new Task B transfer gains
