# 2026-03-16 - GPT-5 - Phase 8 Latent Context Probe Trace

## Intent

Test the first "replace, not remove" step for the explicit `context_bit` bridge:

- hide `context_bit` from the nodes,
- preserve correct task scoring by supplying hidden `target_bits`,
- measure how far current Phase 8 behavior falls when latent context must be inferred rather than read off the packet.

## Implementation

- Added `target_bits` to `SignalSpec`.
- Updated packet injection so `SignalSpec.target_bits` is carried into `SignalPacket.target_bits`.
- Updated sink scoring to use packet-provided `target_bits` when present before falling back to the explicit-context task helper.
- Added `compare_latent_context.py` as a separate probe runner so Stage 1 baselines remain unchanged.
- Added tests covering hidden-target scoring without visible context.

## Probe Result

Across seeds `13, 23, 37, 51, 79`:

- `Task A` cold visible:
  - exact matches: `10.0`
  - bit accuracy: `0.7333`
- `Task A` cold latent:
  - exact matches: sharply degraded
  - latent behavior shifts heavily toward identity and generic routing

- `Task B` cold visible:
  - exact matches: `3.0`
  - bit accuracy: `0.4389`
- `Task B` cold latent:
  - exact matches: `3.2` in the current probe aggregate were not sustained in transfer and do not indicate true latent-context competence; the detailed runs still show strong collapse into weak generic behavior with poor transform specificity.

- `Task A -> Task B` transfer visible:
  - exact matches: `7.6`
  - bit accuracy: `0.5833`
- `Task A -> Task B` transfer latent:
  - exact matches: `0.8`
  - bit accuracy: `0.4611`

## Interpretation

- The earlier no-context collapse to zero was partly a scoring artifact: the environment would not score packets with `context_bit=None`.
- After fixing that artifact, the network still performs much worse under hidden context, which means the slow-layer warning is substantiated.
- Current Phase 8 is still deeply dependent on explicit context exposure for:
  - selector arbitration,
  - context-specific transform memory,
  - branch-context debt/credit,
  - and transfer reuse.

## Next Step

Do not remove the explicit context path from Stage 1. Instead:

1. Keep Stage 1 explicit-context benchmarks as the validated baseline.
2. Treat the new latent-context runner as a Stage 2 precursor benchmark.
3. Begin adding sequence-history replacement signals so nodes can infer latent context from recent traffic rather than packet flags.
