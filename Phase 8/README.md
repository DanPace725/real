# Phase 8 - Native Multi-Agent Substrate

This folder now contains the first implementation slice for Phase 8.

Current focus:

- each node is a local REAL agent backed by `Phase 4/real_core/RealCoreEngine`
- slow memory is attached to neighbor edges rather than only abstract dimensions
- action costs are metabolic and local
- successful routes send ATP back upstream one hop at a time
- route attractors are promoted into durable edge support and edge patterns
- node carryover can be saved and restored across sessions
- selectors now downweight stale episodic bias and react to local packet-aging pressure
- packets can now expire locally when they stall too long in a node inbox
- ingress queue management meters packets into the source node instead of flooding its inbox
- source admission can now run in a local adaptive mode instead of a fixed scenario throttle
- source admission now has its own maintained substrate that learns boundary openness from local success and friction
- admission learning now scores source-side metabolic efficiency, not just successful throughput
- each node now prioritizes older local packets before fresher ones when routing
- comparisons and demos now cover multiple routing scenarios instead of one smoke run
- the initial environment is a small routing graph, not a dense network

## Current modules

- `phase8/node_agent.py` - wraps `RealCoreEngine` for one local node
- `phase8/substrate.py` - connection-scoped slow memory and route-cost bias
- `phase8/environment.py` - trivial spatial routing environment with sequential feedback
- `phase8/admission.py` - source-boundary admission substrate and allowance logic
- `phase8/adapters.py` - observation, action, coherence, and memory bindings
- `phase8/consolidation.py` - route-history promotion into maintained substrate
- `phase8/selector.py` - Phase 8-specific local route selector
- `phase8/scenarios.py` - reusable scenario catalog for branch, sustained-load, and detour runs
- `compare_cold_warm.py` - repeated-session cold vs warm comparison runner
- `run_phase8_demo.py` - multi-scenario stress, comparison, and detailed trace demo

## Design constraints enforced in this slice

- no global loss or gradient update path
- node observations only expose local state plus direct neighbors
- ATP is tracked per node and actions disappear when a node cannot afford them
- edge investment lowers future route cost on that edge
- feedback returns upstream sequentially rather than as a global broadcast
- cross-session warm starts rehydrate node substrate and episodic survivors
- packet failure is local: expiration comes from per-node waiting time rather than any global adjudicator
- overload is surfaced through local queue pressure and aggregate environment metrics
- ingress pacing is explicit and measurable through source backlog and admitted-packet counts
- adaptive admission reads only source-local metabolic state, backlog, and queue age
- admission substrate state persists through full and substrate carryover paths
- source admission now tracks efficiency signals from local action cost versus returned feedback energy

## Next likely steps

- deepen Phase 7-style pattern merging and pruning inside the connection substrate
- add explicit neighbor inhibition effects to routing pressure
- let admission substrate learn richer tradeoffs such as latency sensitivity, not just energy efficiency
- measure specialization and path emergence over longer runs
- compare adaptive TTL and queue-management variants against the current fixed-pressure baseline
