# Phase 8 Operational Orientation

## Purpose

This document translates the Phase 8 vision into an executable research and engineering program without replacing the philosophy, theory, or prior implementation work that already grounds Project REAL.

It is not a new theory document. It is a bridge between:

- the E^2 and REAL framing in the repo root
- the architectural constraints in `AGENTS.md`
- the current Phase 8 routing substrate
- the next experiments required to make the project scientifically legible

## What Must Remain Intact

The following commitments are load-bearing and should not be traded away for convenience:

- REAL is not a reward-maximizing or gradient-based system. Evaluation remains endogenous and relational.
- Learning remains local, stigmergic, and metabolically constrained rather than globally optimized.
- Node agents are active participants with local perception, local ATP budgets, and local memory.
- Feedback propagates sequentially through local handoffs, not as a broadcast loss signal.
- Maintained substrate is the learned structure. Episodic traces and consolidated patterns exist to shape future local action cost.
- Transfer matters more than benchmark mimicry. The target is adaptive structural learning under scarcity, not transformer-style token performance on its home terrain.

## The Core Intent

Phase 8 should become the first clear demonstration that a network of locally allostatic REAL agents can learn a useful computational structure from sparse experience, preserve that structure in maintained substrate, and adapt it to a related task without retraining from scratch.

In operational terms, the project is trying to establish five claims:

1. A REAL substrate can compute, not just route.
2. It can learn that computation from relatively small numbers of examples.
3. The learned structure can persist as substrate rather than only as transient episode history.
4. That persisted structure can accelerate adaptation on related tasks.
5. These properties can be shown with runnable code and explicit baselines.

## What Phase 8 Has Already Accomplished

The current Phase 8 work is meaningful, but it should be understood as scaffolding rather than the final result.

- We have a native multi-agent substrate where each node wraps `RealCoreEngine`.
- Learning is local: route bias is written into edge substrate through sequential upstream feedback.
- The system now supports carryover, route-pattern promotion, queue management, adaptive admission, and admission-side substrate learning.
- We have a comparison harness for cold start, warm full carryover, and warm substrate-only carryover.
- We have demonstrated robustness improvements in routing scenarios and reduced route cost under warm starts.

This is a valid proof that the architecture can maintain local metabolism, memory, and sequential feedback in a distributed setting.

It is not yet the publishable claim.

The missing step is computational task learning with measurable sample efficiency and transfer.

## The Real Target

The target is not "match GPT-like language ability."

The target is a small but decisive result of the following form:

> A metabolically constrained REAL substrate learned a context-dependent task from sparse examples, retained useful structure across sessions, and adapted to a related variant faster than a cold start and with less retraining burden than a comparable neural baseline.

That is the sentence the codebase should now be organized to earn.

## Operational Program

### Stage A: Lock In the Current Routing Substrate as Baseline

Routing should now be treated as the substrate validation layer, not the end goal.

Required outcome:

- the current local-only routing environment remains runnable, tested, and reproducible
- cold vs warm comparisons remain available as baseline instrumentation
- future work does not violate the no-global-gradient or local-observation constraints

Why this matters:

- it proves the architecture can support local memory, ATP scarcity, and sequential feedback
- it gives us the benchmark harness pattern we will reuse for computational tasks

### Stage B: Move from Routing to Computation

The next substantive build should add content-bearing signals and local transformation actions.

Required outcome:

- packets/signals carry a small content state, not just destination information
- node actions can transform, gate, inhibit, defer, or forward content locally
- the sink/environment can score whether an output matches a target transformation
- upstream feedback still returns sequentially and locally

Recommended first task:

- sequence-contingent pattern routing or transformation with small content vectors
- the correct output depends on recent history, not only the current input

Why this task is appropriate:

- it is small enough for consumer hardware
- it cannot be solved by trivial hardcoding if the context shifts
- it activates the exact assets REAL already has: episodic traces, maintained substrate, and allostatic adaptation under cost

### Stage C: Demonstrate Sparse Learning

Once the computational task exists, the system needs a disciplined experiment around sample efficiency.

Required outcome:

- define a training protocol with small numbers of examples
- measure performance as a function of examples seen and cycles elapsed
- compare against at least one small neural baseline on the same task

Minimum evaluation set:

- cold-start REAL substrate
- warm-start REAL substrate
- substrate-only warm start
- small feedforward or recurrent baseline, depending on task structure

Primary metrics:

- examples to criterion
- cycles to criterion
- metabolic cost per successful output
- route or transformation cost over time
- stability of performance after criterion is reached

### Stage D: Demonstrate Transfer

Transfer is the central scientific differentiator and should become an explicit milestone rather than a background hope.

Required outcome:

- train on Task A to stable performance
- switch to related Task B without resetting maintained substrate
- compare adaptation speed on Task B against cold-start Task B
- compare against the neural baseline's adaptation or retraining burden

Primary transfer metrics:

- cycles to recover criterion after task switch
- examples required after switch
- retained performance on Task A or return-to-A performance
- evidence of reduced catastrophic forgetting

Interpretation rule:

- if warm carryover helps route cost but not adaptation speed, we have architectural coherence but not yet strong transfer
- if warm carryover materially reduces samples or cycles on Task B, we have the beginning of the real result

### Stage E: Let Topology Earn Itself

Topology growth should remain downstream of a working fixed-topology computational substrate.

Required outcome before growth work:

- a fixed graph can already learn and transfer a non-trivial computational task

Then, and only then:

- allow metabolically justified node budding or edge creation
- allow pruning and apoptosis for structures that do not contribute
- measure whether learned topology reduces cost or improves adaptation

This keeps us from introducing architectural complexity before we know what the task actually requires.

### Stage F: Make the Result Legible

Scientific and practical legibility should be treated as part of the build, not as cleanup at the end.

Required outcome:

- runnable demo
- reproducible comparison script
- explicit benchmark description
- concise explanation of what the architecture is claiming and what it is not claiming
- trail documents that preserve the design history and failure history

The artifact should be understandable without requiring a reader to absorb the full corpus first.

## Non-Goals

The following are attractive distractions and should not drive Phase 8 planning:

- trying to outperform transformer models at generic next-token prediction
- scaling graph size before a small graph can show computation and transfer
- adding topology growth before fixed-topology computation works
- introducing any global loss, broadcast reward, or synchronized multi-agent weight update
- optimizing demos for appearance over experimental clarity

## Working Success Criteria

Phase 8 should be considered substantively successful when all of the following are true:

- a small REAL substrate performs a context-dependent computational task, not just routing
- performance improves from sparse experience without backpropagation
- maintained substrate measurably lowers future learning burden
- warm starts outperform cold starts on related tasks in cycles, examples, or metabolic cost
- a comparable neural baseline is included
- the result is reproducible from the repo with clear docs and tests

## Immediate Build Priorities

In order:

1. Extend the routing substrate into a content-transforming substrate.
2. Define one compact context-dependent task and one related transfer variant.
3. Build the benchmark harness around sparse-example learning curves.
4. Add a neural baseline for the same task.
5. Only after that, revisit topology growth.

## Guardrails for Ongoing Work

Every substantial Phase 8 change should be checked against these questions:

- Does this preserve local-only perception and local-only learning?
- Does it preserve ATP scarcity as a real constraint rather than a decorative variable?
- Does maintained substrate become cheaper action structure, not hidden global state?
- Does the task reveal transfer, not just steady-state optimization?
- Does the comparison harness make the claim clearer?
- Does the change stay small, testable, and documented in traces?

If the answer to any of these is no, the work is probably drifting away from the actual point of the project.

## Present Orientation

The repo already contains the philosophical basis, formal specification, developmental results, and the first native-substrate scaffolding. The right move now is not to restart conceptually or to broaden the ambition. The right move is to tighten the target.

Phase 8 is best understood as the path from:

- local allostatic routing substrate

to:

- sparse-learning computational substrate

to:

- transfer-demonstrating adaptive architecture

That path preserves the philosophy, honors the existing work, and turns the vision into a program we can actually execute.
