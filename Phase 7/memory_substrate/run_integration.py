"""Phase 3 integration test: REAL engine with memory substrate.

Provides a minimal signal domain implementing Phase 4 protocols, then
runs the SubstrateEngine to demonstrate that the substrate modulates
REAL behavior: observation quality, action selection, and coherence
scoring all change based on slow-layer state.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_phase4_root = Path(__file__).resolve().parents[2] / "Phase 4"
if str(_phase4_root) not in sys.path:
    sys.path.insert(0, str(_phase4_root))

from real_core.types import ActionOutcome, CycleEntry, DimensionScores, GCOStatus

from .substrate import DIMENSIONS, SubstrateConfig
from .real_integration import SubstrateEngine


# ------------------------------------------------------------------
# Minimal signal domain (Phase 4 protocol-compatible)
# ------------------------------------------------------------------

class SignalDomainObserver:
    """Six-channel signal environment implementing ObservationAdapter."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._cycle = 0
        self._context_val = 0.5
        self._context_shift = self.rng.randint(15, 25)
        self._walk = 0.5
        self._ramp = 0

    def observe(self, cycle: int) -> Dict[str, float]:
        self._cycle = cycle
        c = cycle
        signals = {}

        signals["continuity"] = 0.5 + 0.4 * math.sin(2 * math.pi * c / 40)

        phase = (c % 30) / 30
        signals["vitality"] = 1.0 - abs(2 * phase - 1)

        if c >= self._context_shift:
            self._context_val = self.rng.uniform(0.2, 0.8)
            self._context_shift = c + self.rng.randint(15, 25)
        signals["contextual_fit"] = self._context_val

        pert = self.rng.gauss(0, 0.2) if self.rng.random() < 0.08 else 0.0
        signals["differentiation"] = max(0.0, min(1.0, 0.6 + pert))

        self._ramp = (self._ramp + 1) % 20
        signals["accountability"] = self._ramp / 20

        self._walk = max(0.15, min(0.85, self._walk + self.rng.gauss(0, 0.05)))
        signals["reflexivity"] = self._walk

        return signals


class SignalDomainActions:
    """Basic domain actions implementing ActionBackend."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def available_actions(self, history_size: int) -> List[str]:
        return ["scan", "rest", "introspect"]

    def execute(self, action: str) -> ActionOutcome:
        if action == "scan":
            return ActionOutcome(success=True, cost_secs=0.05)
        if action == "rest":
            return ActionOutcome(success=True, cost_secs=0.0)
        if action == "introspect":
            return ActionOutcome(success=True, cost_secs=0.15)
        return ActionOutcome(success=False, cost_secs=0.0)


class SignalDomainCoherence:
    """Coherence model for the signal domain implementing CoherenceModel."""

    dimension_names = DIMENSIONS

    def score(
        self, state_after: Dict[str, float], history: List[CycleEntry]
    ) -> DimensionScores:
        recent = history[-10:] if history else []
        dims: Dict[str, float] = {}

        if len(recent) >= 3:
            vars_ = []
            for d in DIMENSIONS:
                vals = [e.state_after.get(d, 0.5) for e in recent]
                vars_.append(statistics.variance(vals) if len(vals) > 1 else 0.1)
            dims["continuity"] = max(0.0, min(1.0, 1.0 - statistics.mean(vars_) * 5))
        else:
            dims["continuity"] = 0.40

        if len(recent) >= 3:
            actions = [e.action for e in recent]
            unique = len(set(actions)) / max(len(actions), 1)
            dims["vitality"] = max(0.0, min(1.0, 4 * unique * (1 - unique) + 0.2))
        else:
            dims["vitality"] = 0.40

        if len(recent) >= 3:
            scores = []
            for d in DIMENSIONS:
                vals = [e.state_after.get(d, 0.5) for e in recent[-5:]]
                trend = statistics.mean(vals)
                dev = abs(state_after.get(d, 0.5) - trend)
                scores.append(max(0.0, 1.0 - dev * 3))
            dims["contextual_fit"] = statistics.mean(scores)
        else:
            dims["contextual_fit"] = 0.40

        if len(recent) >= 5:
            actions = [e.action for e in recent[-15:]] if len(history) >= 5 else []
            unique = len(set(actions))
            dims["differentiation"] = min(1.0, unique / max(len(actions) * 0.4, 1))
        else:
            dims["differentiation"] = 0.40

        if len(recent) >= 5:
            traceable = checked = 0
            for i in range(max(0, len(history) - 12), len(history)):
                e = history[i]
                if e.action.startswith("invest_"):
                    target = e.action[len("invest_"):]
                    if target in DIMENSIONS and i + 2 < len(history):
                        bv = [history[j].state_after.get(target, 0.5)
                              for j in range(max(0, i - 2), i)]
                        av = [history[j].state_after.get(target, 0.5)
                              for j in range(i + 1, min(i + 3, len(history)))]
                        if bv and av:
                            imp = statistics.mean(av) - statistics.mean(bv)
                            traceable += 1 if imp > -0.05 else 0
                            checked += 1
            dims["accountability"] = (
                min(1.0, 0.30 + 0.70 * (traceable / max(checked, 1)))
                if checked > 0 else 0.40
            )
        else:
            dims["accountability"] = 0.40

        if len(recent) >= 5:
            dips = switches = 0
            for i in range(1, min(len(recent), 10)):
                idx = len(recent) - i
                if recent[idx].delta < -0.03:
                    dips += 1
                    if idx + 1 < len(recent) and recent[idx + 1].action != recent[idx].action:
                        switches += 1
            dims["reflexivity"] = (
                min(1.0, 0.30 + 0.70 * (switches / max(dips, 1)))
                if dips > 0 else 0.50
            )
        else:
            dims["reflexivity"] = 0.40

        return dims

    def composite(self, dimensions: DimensionScores) -> float:
        if not dimensions:
            return 0.0
        return sum(dimensions.values()) / len(dimensions)

    def gco_status(
        self, dimensions: DimensionScores, coherence: float
    ) -> GCOStatus:
        if coherence < 0.40:
            return GCOStatus.CRITICAL
        if coherence < 0.58:
            return GCOStatus.DEGRADED
        if coherence >= 0.72 and all(v >= 0.50 for v in dimensions.values()):
            return GCOStatus.STABLE
        return GCOStatus.PARTIAL


# ------------------------------------------------------------------
# Experiment runner
# ------------------------------------------------------------------

def run_experiment(
    sessions: int = 15,
    cycles: int = 50,
    seed: int = 42,
    carry_slow: bool = True,
    output_dir: Optional[Path] = None,
) -> list:
    carried_session = None
    logs = []

    for sid in range(1, sessions + 1):
        s_seed = seed + sid

        engine = SubstrateEngine(
            observer=SignalDomainObserver(seed=s_seed),
            actions=SignalDomainActions(seed=s_seed),
            coherence=SignalDomainCoherence(),
            seed=s_seed,
        )

        if carried_session is not None:
            engine.load_session(carried_session)

        summary = engine.run_session(cycles=cycles)
        summary.session_id = sid

        if carry_slow:
            carried_session = engine.save_session()

        logs.append(summary)

        top_actions = sorted(
            summary.action_counts.items(), key=lambda x: x[1], reverse=True
        )[:4]
        actions_str = ", ".join(f"{a}={c}" for a, c in top_actions)
        print(
            f"  Session {sid:>2}:  "
            f"coherence={summary.mean_coherence:.3f}  "
            f"final={summary.final_coherence:.3f}  "
            f"active={summary.final_substrate['active_count']}  "
            f"coupling={summary.final_substrate['coupling_score']:.3f}  "
            f"GCO={summary.gco_counts}  "
            f"[{actions_str}]"
        )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        for log in logs:
            data = {
                "session_id": log.session_id,
                "cycles": log.cycles,
                "mean_coherence": log.mean_coherence,
                "final_coherence": log.final_coherence,
                "gco_counts": log.gco_counts,
                "final_substrate": log.final_substrate,
                "action_counts": log.action_counts,
            }
            path = output_dir / f"session_{log.session_id:03d}.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

    return logs


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 3 — REAL + Substrate Integration Test"
    )
    parser.add_argument("--sessions", type=int, default=15)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-carry", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 68)
    print("  Phase 3 — REAL Engine + Memory Substrate Integration")
    print("=" * 68)
    print(
        f"  Sessions: {args.sessions}   Cycles: {args.cycles}   "
        f"Carry slow: {not args.no_carry}"
    )
    print()

    output_dir = Path(args.output) if args.output else None
    logs = run_experiment(
        sessions=args.sessions,
        cycles=args.cycles,
        seed=args.seed,
        carry_slow=not args.no_carry,
        output_dir=output_dir,
    )

    print()
    print("-" * 68)
    coherences = [l.mean_coherence for l in logs]
    couplings = [l.final_substrate["coupling_score"] for l in logs]
    actives = [l.final_substrate["active_count"] for l in logs]
    print(
        f"  Coherence: {min(coherences):.3f} – {max(coherences):.3f}  "
        f"(mean {sum(coherences)/len(coherences):.3f})"
    )
    print(
        f"  Coupling:  {min(couplings):.3f} – {max(couplings):.3f}  "
        f"(mean {sum(couplings)/len(couplings):.3f})"
    )
    print(
        f"  Active:    {min(actives)} – {max(actives)}  "
        f"(mean {sum(actives)/len(actives):.1f})"
    )
    total_gco = {"STABLE": 0, "PARTIAL": 0, "DEGRADED": 0, "CRITICAL": 0}
    for l in logs:
        for k, v in l.gco_counts.items():
            total_gco[k] += v
    total_cycles = sum(total_gco.values())
    print(
        "  GCO: "
        + "  ".join(f"{k}={v/total_cycles:.0%}" for k, v in total_gco.items())
    )
    print("-" * 68)


if __name__ == "__main__":
    main()
