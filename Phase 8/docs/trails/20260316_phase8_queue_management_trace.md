# Phase 8 Queue Management Trace - 2026-03-16

## Intent

Address the next visible robustness bottleneck from the prior comparison run: sustained pressure still produced local drops and overload even after selector tuning.

## Hypotheses

1. The source edge should behave like a real ecological boundary, not an infinite floodgate.
Result: adding a source ingress buffer with explicit admission pacing removed the previous sustained-pressure overload spikes without adding any global optimization loop.

2. Queue management should remain local at each node.
Result: nodes now sort only their own inboxes, prioritizing older packets before fresher arrivals. No node reads or rewrites a remote queue.

3. Better queue discipline may trade throughput collapse for latency growth.
Result: this is exactly what happened under sustained load. Drops disappeared, but mean latency rose because packets wait outside the source node instead of dying inside it.

## Implementation Notes

- added `source_buffer`, `admitted_packets`, and `max_source_backlog` to the routing environment
- introduced `prepare_cycle()` so each cycle can admit buffered source packets before node actions
- added per-node inbox prioritization based on local wait age and partial path progress
- exposed `ingress_backlog` to the source node as a local observation signal
- extended scenario specs with `source_admission_rate`
- added tests for ingress pacing and stale-packet-first routing

## Comparison Results

After queue-management changes, the `5`-seed stress run produced:

- `branch_pressure`: still `12/12` delivered with `0` drops, but overload events fell from `5` to `0` and max inbox depth dropped to `4`.
- `sustained_pressure`: improved from `22 delivered / 2 dropped / 42 overload events` to `24 delivered / 0 dropped / 0 overload events`.
- `detour_resilience`: still `12/12` delivered with `0` drops and `0` overload events.

Overall aggregate after the change:

- delivered packets increased from `15.3333` to `16.0`
- dropped packets fell from `0.6667` to `0.0`
- overload events fell from `16.0` to `0.0`
- mean route cost still improved on warm starts: `0.04760` cold to `0.04426` warm-full and `0.04063` warm-substrate

Important tradeoff:

- sustained-pressure mean latency rose to `6.4167` because ingress pacing preserves packets instead of flooding the source node

## Consequence

Queue management made the system more robust overall, not just cheaper. The next step should be making admission policy adaptive so the source boundary can respond to current metabolic conditions instead of using a fixed per-scenario rate.
