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
- packets can now carry content payload bits, optional context flags, task ids, and transform traces
- nodes can now mutate packet payloads locally through discrete `route_transform:*` actions
- the sink can now score task packets for exact and partial bit matches and return graded sequential feedback
- Phase 8 now includes a first runnable CVT-1 Stage 1 computational scenario in the comparison and demo harness
- transform choices now have their own local slow-memory support, selector bias, and diagnostic reporting
- returned feedback now writes local transform-credit signals back onto the nodes that used those transforms, and Stage 1 transform memory can be context-sensitive
- active edge and transform supports can now be explicitly maintained, and summaries now distinguish recently maintained substrate from support that is merely lingering
- returned transform credit is now context-bound as well as transform-bound, which helps reduce warm-start interference across task contexts
- repeated local context-bound credit can now promote durable context-specific action support and reinforce the supporting edge, so substrate-only carryover inherits more of the learned task structure
- Phase 8 now includes the first explicit `Task A -> Task B` transfer harness for CVT-1 Stage 1
- Phase 8 now includes a nearby `Task C` Stage 1 variant plus a `compare_transfer_matrix.py` runner for pairwise transfer checks across `Task A`, `Task B`, and `Task C`
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
- `compare_task_transfer.py` - first Task A -> Task B transfer comparison runner
- `run_phase8_demo.py` - multi-scenario stress, comparison, and detailed trace demo
- `occupancy_baseline/` - separate traditional-NN setup for the first real-world occupancy benchmark
- `compare_occupancy_baseline.py` - single-seed or multi-seed occupancy baseline vs REAL comparison runner

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
- local observation can now expose the head packet payload without exposing sink targets or global task labels
- route-transform actions are treated as local routing history by the selector and consolidation pipeline
- routing-only packets still receive the legacy full feedback pulse, while task packets now receive feedback scaled by sink match quality
- workload runners can now inject explicit task packets via signal-spec schedules instead of only count-based routing bursts
- summaries now expose context-level task accuracy, final transform counts, and per-node transform supports
- summaries and demos now expose context-specific transform supports and per-node substrate-maintenance ratios
- selector pressure can now use transform-specific returned credit and explicit-context transform bias instead of relying only on route cost and generic edge support
- selector pressure can now prefer context-matched returned credit over generic transform credit when packets carry explicit task context
- substrate-only warm starts can now recover part of the task benefit by carrying forward promoted context-action support plus its local routing scaffold
- transfer feedback now relaxes contradictory context-transform credit, and selector history is only strongly trusted when maintained substrate still supports it
- the first Task B transfer loop now shows warm full carryover improving exact-match counts over cold start in the aggregate, but mean bit accuracy is still slightly behind cold and still needs stabilization
- transfer summaries and demos now expose per-context mismatch diagnostics, first-hop branch counts, wrong-transform counts, identity fallbacks, and heuristic stale-support suspicions
- contradictory feedback now also builds local transform-debt and reduces maintenance priority for debt-heavy context-action supports, but the first aggregate pass was mixed: it fixed some previously sticky seeds while reducing 5-seed transfer performance overall
- contradiction-debt accumulation is now gated by prior local commitment instead of firing on every mismatch, which restores a modest aggregate full-carryover advantage over cold Task B while still leaving the odd-context branch behind substrate-only carryover
- branch-specific contradiction debt now lets nodes penalize stale neighbor-plus-transform habits instead of damping whole transform families, which improves 5-seed warm-full Task B transfer over cold on both exact matches (`3.8 -> 5.0`) and mean bit accuracy (`0.4333 -> 0.4944`) and nudges warm-full `context_1` bit accuracy above cold (`0.3375 -> 0.3500`)
- branch-context contradiction debt now lets nodes back away from a stale branch in a specific context during both selection and maintenance, keeping warm full Task B ahead of cold on the current 5-seed aggregate (`2.2 -> 4.4` exact matches, `0.3889 -> 0.4278` mean bit accuracy) while nudging `context_1` bit accuracy above cold (`0.2500 -> 0.2750`)
- positive branch-context evidence now complements contradiction debt, so warm full no longer learns only by retreat; the current 5-seed Task B transfer run reaches `5.2` exact matches and `0.4722` mean bit accuracy versus cold `2.2` and `0.3722`, with `context_1` mean bit accuracy rising to `0.3500` versus cold `0.2250`
- branch-plus-transform credit now ties the preferred branch to the correct transform family more directly, pushing the current 5-seed Task B transfer run to `8.8` exact matches and `0.6333` mean bit accuracy for warm full versus cold `3.0` and `0.4445`, with `context_1` mean bit accuracy rising to `0.5500` and warm-full stale-support suspicion dropping below cold (`4.2` vs `5.6`)
- the first small transfer matrix now shows that this carryover is strong but directional:
  - `Task A -> Task B` is robustly positive
  - `Task A -> Task C` is also positive
  - `Task B -> Task A` remains mixed or slightly negative
  - `Task B -> Task C` is mildly positive
  - `Task C -> Task A` is near parity
  - `Task C -> Task B` is modestly positive but less stable

## Next likely steps

- deepen Phase 7-style pattern merging and pruning inside the connection substrate
- improve Task B transfer quality so warm full carryover beats cold on mean bit accuracy as well as exact matches
- keep strengthening carryover by promoting and maintaining context-specific transform support, not just route support
- keep the new branch-context debt path, but tune it to reduce overall stale-support suspicion under warm full carryover without losing the new `context_1` edge over cold start
- keep refining the new branch-plus-transform credit path so the gains hold under larger seed sets and more transfer variants
- use the new matrix runner to study transfer directionality instead of assuming symmetry from one successful pair
- add one more nearby variant or latent-context precursor only after the current directional transfer pattern is better understood
- add explicit neighbor inhibition effects to routing pressure
- let admission substrate learn richer tradeoffs such as latency sensitivity, not just energy efficiency
- measure specialization and path emergence over longer runs
- compare adaptive TTL and queue-management variants against the current fixed-pressure baseline
