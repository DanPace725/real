"""Diagnostic: track constraint pattern accumulation across sessions."""
import sys

from .substrate import SubstrateConfig
from .run_integration import (
    SignalDomainObserver, SignalDomainActions, SignalDomainCoherence,
)
from .real_integration import SubstrateEngine


def main():
    all_summaries = []
    carried_session = None

    print(f"{'Sess':>4}  {'Coh':>6}  {'Pat':>3}  {'Pos':>3}  {'Neg':>3}  "
          f"{'M+':>5}  {'M-':>5}  {'Maint%':>6}  {'Act':>3}  {'Coupl':>6}  {'Mem':>3}")
    print("-" * 78)

    for s in range(1, 21):
        s_seed = 42 + s
        engine = SubstrateEngine(
            observer=SignalDomainObserver(seed=s_seed),
            actions=SignalDomainActions(seed=s_seed),
            coherence=SignalDomainCoherence(),
            substrate_config=SubstrateConfig(), seed=s_seed,
            session_budget=5.0,
        )
        if carried_session is not None:
            engine.load_session(carried_session)

        summary = engine.run_session(cycles=50, consolidate_on="rest")
        all_summaries.append(summary)
        carried_session = engine.save_session()
        snap = engine.substrate.snapshot()
        patterns = engine.substrate.constraint_patterns
        pos = [p for p in patterns if p.valence > 0]
        neg = [p for p in patterns if p.valence < 0]
        maint = summary.action_counts.get("maintain_substrate", 0)
        maint_pct = maint / 50 * 100

        mem_count = len(engine.memory.entries)
        print(
            f"{s:4d}  {summary.mean_coherence:.3f}  {len(patterns):3d}  "
            f"{len(pos):3d}  {len(neg):3d}  "
            f"{snap['pattern_match_pos']:.3f}  {snap['pattern_match_neg']:.3f}  "
            f"{maint_pct:5.1f}%  {snap['active_count']:3d}  "
            f"{snap['coupling_score']:.3f}  {mem_count:3d}"
        )

    print("\n--- Pattern details at end ---")
    dims_short = ["cont", "vita", "ctxf", "diff", "acct", "refl"]
    header = "     val   str  matches  src        " + "  ".join(f"{d:>5}" for d in dims_short)
    print(header)
    print("  " + "-" * len(header))
    from .substrate import DIMENSIONS as _DIMS
    for i, p in enumerate(engine.substrate.constraint_patterns):
        scores_str = "  ".join(f"{p.dim_scores.get(d, 0.5):.2f}" for d in _DIMS)
        print(
            f"  [{i:>2}] {p.valence:+.1f}  {p.strength:.2f}  "
            f"{p.match_count:>6}  {p.source:<9}  {scores_str}"
        )

    print("\n--- Per-dimension modulation (last cycle) ---")
    mod = engine.substrate.pattern_dim_modulation
    if mod:
        print("  " + "  ".join(f"{d[:4]:>6}" for d in _DIMS))
        print("  " + "  ".join(f"{mod.get(d, 0.0):+.3f}" for d in _DIMS))
    else:
        print("  (no modulation data)")

    print("\n--- Pairwise similarity (top-5 most similar pairs) ---")
    pairs = []
    for i in range(len(engine.substrate.constraint_patterns)):
        for j in range(i + 1, len(engine.substrate.constraint_patterns)):
            pi = engine.substrate.constraint_patterns[i]
            pj = engine.substrate.constraint_patterns[j]
            sim = pi.match_score(pj.dim_scores, pj.dim_trends)
            pairs.append((i, j, sim))
    pairs.sort(key=lambda x: x[2], reverse=True)
    for i, j, sim in pairs[:5]:
        print(f"  [{i}]-[{j}]  similarity={sim:.3f}")

    print("\n--- Phase comparison: early (1-5) vs late (16-20) ---")
    early_coh = [all_summaries[i] for i in range(min(5, len(all_summaries)))]
    late_coh = [all_summaries[i] for i in range(max(0, len(all_summaries)-5), len(all_summaries))]
    early_mean = sum(s.mean_coherence for s in early_coh) / max(len(early_coh), 1)
    late_mean = sum(s.mean_coherence for s in late_coh) / max(len(late_coh), 1)
    early_maint = sum(s.action_counts.get("maintain_substrate", 0) for s in early_coh) / (50 * max(len(early_coh), 1)) * 100
    late_maint = sum(s.action_counts.get("maintain_substrate", 0) for s in late_coh) / (50 * max(len(late_coh), 1)) * 100
    print(f"  Early coherence: {early_mean:.3f}   maintenance: {early_maint:.1f}%")
    print(f"  Late  coherence: {late_mean:.3f}   maintenance: {late_maint:.1f}%")
    print(f"  Gain:            {late_mean - early_mean:+.3f}   maintenance: {late_maint - early_maint:+.1f}%")


if __name__ == "__main__":
    main()
