# Phase 8 Robustness Trace - 2026-03-16

## Intent

Make Phase 8 more substantive than a single happy-path routing demo by:

- tuning the selector against stale episodic bias
- adding a local packet-aging failure mode
- surfacing overload and drop metrics
- expanding comparison and demo coverage across multiple scenarios

## Hypotheses

1. Packet failure can remain fully local.
Result: adding per-node packet TTL based on local wait time gave us explicit drops without introducing any global arbitration path.

2. Selector pressure-awareness should preserve throughput while using substrate bias more carefully.
Result: the tuned selector kept delivered-packet counts flat across all tested cold and warm runs while still lowering route cost.

3. A stronger demo should expose stress behavior, not just a smoke-run success case.
Result: the new scenario catalog now shows moderate branching, sustained overload, and detour routing with the same node-local mechanics.

## Implementation Notes

- extended `SignalPacket` with movement and drop metadata
- added local packet aging, drop tracking, overload counts, and max queue depth to the routing environment
- exposed `oldest_packet_age` and `queue_pressure` in local observation only
- taught the Phase 8 selector to reduce exploration and prioritize routes under packet-aging pressure
- added sustained-pressure and detour-resilience scenarios
- upgraded the comparison runner and demo to report scenario-level aggregates
- added tests for packet expiration and strict-TTL summary reporting

## Comparison Results

Across `5` seeds on the upgraded comparison suite:

- `branch_pressure`: cold, warm-full, and warm-substrate all delivered `12/12` packets with zero drops. Warm-full reduced mean route cost from `0.04810` to `0.04475`; warm-substrate reduced it further to `0.04364`.
- `sustained_pressure`: all modes delivered `22` packets and dropped `2` packets on average, with mean route cost improving from `0.04867` cold to `0.04694` warm-full and `0.04289` warm-substrate. Overload stayed high at `42` events on average, so this is now a visible bottleneck rather than a hidden one.
- `detour_resilience`: all modes delivered `12/12` packets with zero drops. Mean route cost fell from `0.04540` cold to `0.03936` warm-full and `0.03317` warm-substrate. Warm-substrate also improved mean remaining ATP from `4.4190` to `4.6626`.

Overall aggregate:

- delivered packets stayed flat at `15.3333`
- mean latency stayed flat at `3.5404`
- mean route cost improved from `0.04739` cold to `0.04368` warm-full and `0.03990` warm-substrate
- average dropped packets remained `0.6667`, concentrated in the sustained-pressure scenario

## Consequence

The system is now more honest about stress. Warm starts are stable and cheaper, but they are not yet reducing drops or overload under sustained pressure. The next robustness move should target queue management or adaptive pressure handling rather than more route-cost bias alone.
