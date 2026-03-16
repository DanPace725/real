# Phase 8 CVT-1 Spec Trace

## Date

2026-03-16

## Timestamp

Not recorded in the original trace pass.

## Model

GPT-5 Codex

## Prompt

After writing the orientation document, create the concrete spec for the first content-bearing computational experiment.

## Inputs Reviewed

- `Phase 8/operational_orientation.md`
- `Phase 8/vision.md`
- `Phase 8/AGENTS.md`
- `Phase 8/phase8/environment.py`
- `Phase 8/phase8/models.py`
- `Phase 8/phase8/node_agent.py`
- `Phase 8/phase8/adapters.py`
- `Phase 8/phase8/scenarios.py`

## Design Choice

The spec defines a single first experiment called CVT-1, short for Contextual Vector Transform.

The task was deliberately chosen to be:

- small
- sequence-dependent
- benchmarkable
- compatible with the existing Phase 8 routing substrate

## Core Decision

The experiment is split into two stages.

- Stage 1 uses an explicit context bit on the packet to validate content transforms, sink scoring, and sequential feedback.
- Stage 2 removes the explicit context bit so the system must rely more heavily on episodic history and maintained substrate.

This keeps the first implementation loop small without giving up the stronger long-term target.

## Operational Result

Created `Phase 8/first_computational_experiment_spec.md`.

The document defines:

- the exact task family
- Task A and Task B
- packet schema changes
- node observation requirements
- local transform action vocabulary
- sink scoring and feedback policy
- benchmark protocol
- module-level implementation slices
- testing and success criteria

## Immediate Implication

The next code step should be Slice 1 of the spec:

- extend packet models to carry payload and task metadata
- preserve current routing behavior while preparing for transform actions
